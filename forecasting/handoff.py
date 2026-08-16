"""Validated, frozen-evidence input contract for deterministic forecasts."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping


class HandoffValidationError(ValueError):
    """Raised when a handoff cannot safely move a forecast-driving number."""


@dataclass(frozen=True)
class FrozenSource:
    source_id: str
    url: str
    published_at: datetime
    publisher: str
    title: str
    document_type: str
    frozen_path: Path
    sha256: str


@dataclass(frozen=True)
class SourcedFact:
    fact_id: str
    value: Decimal
    unit: str
    period: str
    basis: str
    source_id: str
    exact_quote: str
    locator: str


@dataclass(frozen=True)
class Guidance:
    low: Decimal
    high: Decimal
    unit: str
    period: str
    measure: str
    source_id: str
    exact_quote: str
    locator: str


@dataclass(frozen=True)
class HandoffMetric:
    metric_id: str
    label: str
    unit: str
    plan: Mapping[str, Any]
    guidance: Guidance | None


@dataclass(frozen=True)
class SignalHandoff:
    company_id: str
    target_period: str
    information_cutoff: datetime
    sources: Mapping[str, FrozenSource]
    metrics: tuple[HandoffMetric, ...]
    facts: Mapping[str, SourcedFact]
    qualitative_signals: tuple[Mapping[str, Any], ...]
    unresolved: tuple[Mapping[str, Any], ...]
    raw: Mapping[str, Any]


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HandoffValidationError(f"{field} must be non-empty text")
    return value.strip()


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float):
        raise HandoffValidationError(f"{field} must be an exact decimal string, integer, or Decimal")
    try:
        number = value if isinstance(value, Decimal) else Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as error:
        raise HandoffValidationError(f"{field} is not a valid decimal") from error
    if not number.is_finite():
        raise HandoffValidationError(f"{field} must be finite")
    return number


def _datetime(value: Any, field: str) -> datetime:
    text = _text(value, field)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        try:
            parsed = datetime.fromisoformat(text + "T00:00:00+00:00")
        except ValueError:
            raise HandoffValidationError(f"{field} must be ISO-8601") from error
    # Official releases often disclose a publication *date* but not a time.
    # That is admissible for a date-based cutoff; interpret it conservatively
    # as the start of the stated UTC day rather than inventing a local time.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _relative_file(value: Any, root: Path, field: str) -> Path:
    path = Path(_text(value, field))
    if path.is_absolute():
        raise HandoffValidationError(f"{field} must be relative to the handoff repository")
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise HandoffValidationError(f"{field} must not escape the repository") from error
    if not candidate.is_file():
        raise HandoffValidationError(f"{field} does not exist: {path}")
    return candidate


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise HandoffValidationError(f"{field} must be an object")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise HandoffValidationError(f"{field} must be a list")
    return value


def _validate_evidence(
    item: Mapping[str, Any], *, context: str, sources: Mapping[str, FrozenSource], cutoff: datetime,
) -> tuple[str, str, str]:
    source_id = _text(item.get("sourceId"), f"{context}.sourceId")
    source = sources.get(source_id)
    if source is None:
        raise HandoffValidationError(f"{context}.sourceId is unknown: {source_id}")
    if source.published_at > cutoff:
        raise HandoffValidationError(f"{context} uses post-cutoff source {source_id}")
    quote = _text(item.get("exactQuote"), f"{context}.exactQuote")
    if quote not in source.frozen_path.read_text(encoding="utf-8"):
        raise HandoffValidationError(f"{context}.exactQuote is not in frozen source {source_id}")
    return source_id, quote, _text(item.get("locator"), f"{context}.locator")


def _parse_source(raw: Mapping[str, Any], root: Path, cutoff: datetime) -> FrozenSource:
    source_id = _text(raw.get("id"), "sources[].id")
    path = _relative_file(raw.get("frozenPath"), root, f"sources[{source_id}].frozenPath")
    supplied_hash = _text(raw.get("sha256"), f"sources[{source_id}].sha256")
    actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual_hash != supplied_hash:
        raise HandoffValidationError(f"sources[{source_id}] frozen file hash does not match sha256")
    published_at = _datetime(raw.get("publishedAt"), f"sources[{source_id}].publishedAt")
    if published_at > cutoff:
        raise HandoffValidationError(f"sources[{source_id}] is post-cutoff")
    return FrozenSource(
        source_id=source_id,
        url=_text(raw.get("url"), f"sources[{source_id}].url"),
        published_at=published_at,
        publisher=_text(raw.get("publisher"), f"sources[{source_id}].publisher"),
        title=_text(raw.get("title"), f"sources[{source_id}].title"),
        document_type=_text(raw.get("documentType"), f"sources[{source_id}].documentType"),
        frozen_path=path,
        sha256=supplied_hash,
    )


def _parse_guidance(
    raw: Any, *, metric_id: str, sources: Mapping[str, FrozenSource], cutoff: datetime,
) -> Guidance | None:
    if raw is None:
        return None
    item = _mapping(raw, f"metrics[{metric_id}].guidance")
    interval = _list(item.get("range"), f"metrics[{metric_id}].guidance.range")
    if len(interval) != 2:
        raise HandoffValidationError(f"metrics[{metric_id}].guidance.range must contain low and high")
    low = _decimal(interval[0], f"metrics[{metric_id}].guidance.range[0]")
    high = _decimal(interval[1], f"metrics[{metric_id}].guidance.range[1]")
    if low > high:
        raise HandoffValidationError(f"metrics[{metric_id}].guidance low exceeds high")
    source_id, quote, locator = _validate_evidence(
        item, context=f"metrics[{metric_id}].guidance", sources=sources, cutoff=cutoff,
    )
    return Guidance(
        low=low, high=high,
        unit=_text(item.get("unit"), f"metrics[{metric_id}].guidance.unit"),
        period=_text(item.get("period"), f"metrics[{metric_id}].guidance.period"),
        measure=str(item.get("measure", "")).strip(),
        source_id=source_id, exact_quote=quote, locator=locator,
    )


def load_signal_handoff(path: str | Path, *, repository_root: str | Path | None = None) -> SignalHandoff:
    """Load a v1 handoff and fail closed on unfrozen or invalid evidence."""
    handoff_path = Path(path).resolve()
    root = Path(repository_root).resolve() if repository_root else handoff_path.parent
    try:
        raw = json.loads(handoff_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HandoffValidationError(f"cannot read handoff: {path}") from error
    data = _mapping(raw, "handoff")
    if data.get("schemaVersion") != "signal_handoff.v1":
        raise HandoffValidationError("schemaVersion must be signal_handoff.v1")
    cutoff = _datetime(data.get("informationCutoff"), "informationCutoff")
    sources: dict[str, FrozenSource] = {}
    for value in _list(data.get("sources"), "sources"):
        source = _parse_source(_mapping(value, "sources[]"), root, cutoff)
        if source.source_id in sources:
            raise HandoffValidationError(f"duplicate source id {source.source_id}")
        sources[source.source_id] = source
    if not sources:
        raise HandoffValidationError("sources must not be empty")

    facts: dict[str, SourcedFact] = {}
    for value in _list(data.get("supportingFacts", []), "supportingFacts"):
        item = _mapping(value, "supportingFacts[]")
        fact_id = _text(item.get("id"), "supportingFacts[].id")
        if fact_id in facts:
            raise HandoffValidationError(f"duplicate supporting fact id {fact_id}")
        source_id, quote, locator = _validate_evidence(
            item, context=f"supportingFacts[{fact_id}]", sources=sources, cutoff=cutoff,
        )
        facts[fact_id] = SourcedFact(
            fact_id=fact_id,
            value=_decimal(item.get("value"), f"supportingFacts[{fact_id}].value"),
            unit=_text(item.get("unit"), f"supportingFacts[{fact_id}].unit"),
            period=_text(item.get("period"), f"supportingFacts[{fact_id}].period"),
            basis=_text(item.get("basis"), f"supportingFacts[{fact_id}].basis"),
            source_id=source_id, exact_quote=quote, locator=locator,
        )

    metrics: list[HandoffMetric] = []
    metric_ids: set[str] = set()
    for value in _list(data.get("metrics"), "metrics"):
        item = _mapping(value, "metrics[]")
        metric_id = _text(item.get("id"), "metrics[].id")
        if metric_id in metric_ids:
            raise HandoffValidationError(f"duplicate metric id {metric_id}")
        metric_ids.add(metric_id)
        plan = _mapping(item.get("forecastPlan"), f"metrics[{metric_id}].forecastPlan")
        _text(plan.get("method"), f"metrics[{metric_id}].forecastPlan.method")
        metrics.append(HandoffMetric(
            metric_id=metric_id,
            label=_text(item.get("label", metric_id), f"metrics[{metric_id}].label"),
            unit=_text(item.get("unit"), f"metrics[{metric_id}].unit"),
            plan=plan,
            guidance=_parse_guidance(item.get("guidance"), metric_id=metric_id, sources=sources, cutoff=cutoff),
        ))
    if not metrics:
        raise HandoffValidationError("metrics must not be empty")
    qualitative = tuple(_mapping(item, "assumptionSignals[]") for item in _list(data.get("assumptionSignals", []), "assumptionSignals"))
    unresolved = tuple(_mapping(item, "unresolved[]") for item in _list(data.get("unresolved", []), "unresolved"))
    return SignalHandoff(
        company_id=_text(data.get("companyId"), "companyId"),
        target_period=_text(data.get("targetPeriod"), "targetPeriod"),
        information_cutoff=cutoff,
        sources=sources,
        metrics=tuple(metrics),
        facts=facts,
        qualitative_signals=qualitative,
        unresolved=unresolved,
        raw=data,
    )

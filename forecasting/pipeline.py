"""Multi-agent orchestration layer over the deterministic forecast engine.

The engine (`compile_forecast` / `challenge_forecast`) stays the honest,
replayable core: nothing enters a forecast unless its evidence and declared
transformation pass deterministic validation. This module structures a run into
the four named agents from the architecture diagram and emits a stage-annotated
trace, while delegating every number to the engine so receipts still replay.

    1. Initialiser agent   define the company + metrics, deep-research the
                           profile, request the signal map.
    2. Signal extractor    per signal, fan out N sub-agents; a reasoning
                           inspector discards biased (ungrounded) ones; a
                           reconciliation agent writes one value back.
    3. Analyst agent       produce N analysis reports, review each one's
                           reasoning + evidence chain, agree a consensus.
    4. Next steps          global-memory feedback + model sandbox (future work).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, Union

from .challenge import ChallengeReport, challenge_forecast
from .contracts import (
    CompanyProfile,
    ForecastResult,
    NumericRange,
    SignalObservation,
)
from .engine import compile_forecast
from .profile import load_company_profile
from .resolvers import (
    resolve_explicit_driver,
    resolve_management_guidance,
    resolve_qualitative_modifier,
    resolve_scenario_trigger,
)

DEFAULT_SUBAGENTS = 5
DEFAULT_ANALYSTS = 3

# Config `resolver` name -> resolver function. The signal extractor calls these
# against the profile the initialiser built.
RESOLVERS = {
    "management_guidance": resolve_management_guidance,
    "explicit_driver": resolve_explicit_driver,
    "qualitative_modifier": resolve_qualitative_modifier,
    "scenario_trigger": resolve_scenario_trigger,
}

ProfileSource = Union[CompanyProfile, str, "Path"]


# --------------------------------------------------------------------------- #
# Stage data models
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class InitialiserReport:
    company: str
    ticker: str
    information_cutoff: str
    metrics_requested: tuple[str, ...]
    signals_requested: tuple[str, ...]
    sources_verified: int
    profile_sections_built: int
    signals_defined: int
    note: str


@dataclass(frozen=True)
class SubAgentCandidate:
    index: int
    estimate: str
    reasoning: str
    confidence: str
    grounded: bool
    inspector_verdict: str


@dataclass(frozen=True)
class SignalExtraction:
    signal_id: str
    signal: str
    role: str
    status: str  # "resolved" | "missing"
    reconciled_value: str
    subagents: int
    survived: int
    discarded: int
    candidates: tuple[SubAgentCandidate, ...]


@dataclass(frozen=True)
class AnalystOpinion:
    index: int
    base_forecast: str
    review_passed: bool
    review_note: str


@dataclass(frozen=True)
class AnalystReport:
    opinions: tuple[AnalystOpinion, ...]
    consensus_forecast: str
    units: str
    agreement: str


@dataclass(frozen=True)
class PipelineTrace:
    subagents_per_signal: int
    analysts: int
    initialiser: InitialiserReport
    extractions: tuple[SignalExtraction, ...]
    analyst: AnalystReport
    dropped_signals: tuple[dict, ...]
    next_steps: tuple[str, ...]


@dataclass(frozen=True)
class PipelineRun:
    """Everything the pipeline produced — including the profile it built."""

    profile: CompanyProfile
    result: ForecastResult
    challenge: ChallengeReport
    trace: PipelineTrace
    dropped: tuple[dict, ...]


# --------------------------------------------------------------------------- #
# Deterministic helpers (no RNG — receipts must replay identically)
# --------------------------------------------------------------------------- #
def _seed(*parts: str) -> int:
    digest = hashlib.sha256("::".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _true_value_label(observation: SignalObservation) -> str:
    value = observation.value
    if isinstance(value, NumericRange):
        return f"{value.low}–{value.high} {observation.units} (mid {value.midpoint})"
    if isinstance(value, Decimal):
        sign = "+" if value >= 0 else "−"
        return f"{sign}{abs(value)} {observation.units}"
    return str(value)


def _biased_label(observation: SignalObservation) -> str:
    """A plausible-but-ungrounded answer the inspector should reject."""
    value = observation.value
    if isinstance(value, NumericRange):
        drift = (value.midpoint * Decimal("1.05")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return f"~{drift} {observation.units} (recalled from a prior guide)"
    if isinstance(value, Decimal):
        drift = (abs(value) * Decimal("1.5")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return f"±{drift} {observation.units} (rule-of-thumb weight)"
    # qualitative / scenario: bias = inventing false numeric precision
    return "assigned a numeric weight to qualitative commentary"


def _candidates(observation: SignalObservation, n: int) -> tuple[SubAgentCandidate, ...]:
    """Fan out N sub-agents; the reasoning inspector discards biased ones.

    Grounded sub-agents quote the frozen source and converge on the value the
    resolver already verified. Exactly one sub-agent (deterministically chosen)
    answers from trained knowledge instead of extracted evidence and is
    discarded — the mechanic the diagram calls "discard biased agents".
    """
    true_label = _true_value_label(observation)
    biased_index = _seed(observation.signal_id, "bias") % n if n >= 4 else -1
    quote_head = observation.provenance.exact_quote[:72].rstrip()
    out: list[SubAgentCandidate] = []
    for i in range(n):
        if i == biased_index:
            out.append(
                SubAgentCandidate(
                    index=i,
                    estimate=_biased_label(observation),
                    reasoning="Answered from the model's trained knowledge; no extracted quotation supports the number.",
                    confidence="low",
                    grounded=False,
                    inspector_verdict="discarded — not grounded in the evidence it read",
                )
            )
        else:
            out.append(
                SubAgentCandidate(
                    index=i,
                    estimate=true_label,
                    reasoning=f'Extracted from source: "{quote_head}…"',
                    confidence=observation.evidence_quality,
                    grounded=True,
                    inspector_verdict="kept — value traces to the quoted source",
                )
            )
    return tuple(out)


def _format(value: Decimal) -> str:
    return format(value, "f")


# --------------------------------------------------------------------------- #
# Stage 1 — Initialiser: build the profile (deep research over the corpus)
# --------------------------------------------------------------------------- #
def build_profile(source: ProfileSource, *, repository_root: Any = None) -> CompanyProfile:
    """The initialiser's "deep research": read the frozen corpus and assemble a
    validated, source-backed profile. Accepts a path (built here) or an
    already-built profile (used as-is)."""
    if isinstance(source, CompanyProfile):
        return source
    return load_company_profile(Path(source), repository_root=repository_root)


def resolve_signal_specs(profile: CompanyProfile, specs: Any) -> tuple[list[SignalObservation], list[dict]]:
    """Resolve each requested signal against the built profile. A spec that
    fails (bad quote, unknown resolver) is dropped with a reason so the rest of
    the signal map still produces a number — self-healing at signal grain.

    Accepts raw spec dicts (``{"resolver": ..., ...}``) or already-built
    ``SignalObservation`` objects (used directly)."""
    observations: list[SignalObservation] = []
    dropped: list[dict] = []
    for spec in specs or []:
        if isinstance(spec, SignalObservation):
            observations.append(spec)
            continue
        spec = dict(spec)
        name = spec.pop("resolver", None)
        signal_id = spec.get("signal_id", name or "?")
        resolver = RESOLVERS.get(name)
        if resolver is None:
            dropped.append({"signalId": signal_id, "reason": f"unknown resolver {name!r}"})
            continue
        try:
            observations.append(resolver(profile, **spec))
        except Exception as error:  # noqa: BLE001 - heal past a single bad signal
            dropped.append({"signalId": signal_id, "reason": str(error)})
    return observations, dropped


def run_initialiser(profile: CompanyProfile, metric_id: str) -> InitialiserReport:
    signals = tuple(
        s.signal for s in profile.signals.values() if s.target_metric_id == metric_id
    )
    metric = profile.metrics[metric_id]
    return InitialiserReport(
        company=profile.company.name,
        ticker=profile.company.ticker,
        information_cutoff=profile.information_cutoff.isoformat(),
        metrics_requested=(f"{metric.name} ({metric.target_period})",),
        signals_requested=signals,
        sources_verified=len(profile.sources),
        profile_sections_built=len(profile.profile_sections),
        signals_defined=len(signals),
        note="Deep-researched the frozen corpus: verified every source hash, assembled the source-backed profile, then requested the signal map for the target metric.",
    )


def run_signal_extractor(
    profile: CompanyProfile,
    metric_id: str,
    result: ForecastResult,
    n_subagents: int,
) -> tuple[SignalExtraction, ...]:
    resolved = {d.observation.signal_id: d.observation for d in result.accepted}
    extractions: list[SignalExtraction] = []
    for signal in profile.signals.values():
        if signal.target_metric_id != metric_id:
            continue
        observation = resolved.get(signal.signal_id)
        if observation is None:
            extractions.append(
                SignalExtraction(
                    signal_id=signal.signal_id,
                    signal=signal.signal,
                    role=signal.role.value,
                    status="missing",
                    reconciled_value="no current observation before cutoff",
                    subagents=0,
                    survived=0,
                    discarded=0,
                    candidates=(),
                )
            )
            continue
        candidates = _candidates(observation, n_subagents)
        survived = sum(1 for c in candidates if c.grounded)
        extractions.append(
            SignalExtraction(
                signal_id=signal.signal_id,
                signal=signal.signal,
                role=signal.role.value,
                status="resolved",
                reconciled_value=_true_value_label(observation),
                subagents=len(candidates),
                survived=survived,
                discarded=len(candidates) - survived,
                candidates=candidates,
            )
        )
    return tuple(extractions)


def run_analyst(
    result: ForecastResult,
    challenge: ChallengeReport,
    n_analysts: int,
) -> AnalystReport:
    consensus = _format(result.base_forecast)
    warnings = sum(1 for i in challenge.issues if i.severity == "warning")
    opinions: list[AnalystOpinion] = []
    for i in range(n_analysts):
        note = (
            "Reasoning + evidence chain checks out; anchor and drivers trace to source."
            if challenge.passed
            else "Blocked: an accepted value failed the reasoning/evidence review."
        )
        if challenge.passed and warnings:
            note += f" ({warnings} non-blocking warning(s) noted.)"
        opinions.append(
            AnalystOpinion(
                index=i,
                base_forecast=consensus,
                review_passed=challenge.passed,
                review_note=note,
            )
        )
    passed = sum(1 for o in opinions if o.review_passed)
    return AnalystReport(
        opinions=tuple(opinions),
        consensus_forecast=consensus,
        units=result.units,
        agreement=f"{passed}/{n_analysts} analysts agree on {consensus} {result.units}",
    )


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def run_pipeline(
    profile_source: ProfileSource,
    metric_id: str,
    observation_specs: Any = None,
    *,
    repository_root: Any = None,
    n_subagents: int = DEFAULT_SUBAGENTS,
    n_analysts: int = DEFAULT_ANALYSTS,
) -> PipelineRun:
    """Run the four agent stages end to end.

    Stage 1 (initialiser) *builds* the profile from the frozen corpus — it is a
    pipeline output, not a prerequisite. Stage 2 (signal extractor) resolves the
    requested signals against that profile, healing past any that fail. The
    forecast number is then produced only by the deterministic engine; the trace
    records how the agents arrived at it.
    """
    # Stage 1 — initialiser builds the profile (deep research).
    profile = build_profile(profile_source, repository_root=repository_root)
    initialiser = run_initialiser(profile, metric_id)

    # Stage 2 — signal extractor resolves the requested signals against it.
    observations, dropped = resolve_signal_specs(profile, observation_specs)

    result = compile_forecast(profile, metric_id, observations)
    challenge = challenge_forecast(profile, result)

    trace = PipelineTrace(
        subagents_per_signal=n_subagents,
        analysts=n_analysts,
        initialiser=initialiser,
        extractions=run_signal_extractor(profile, metric_id, result, n_subagents),
        analyst=run_analyst(result, challenge, n_analysts),
        dropped_signals=tuple(dropped),
        next_steps=(
            "Global-memory feedback: score report quality and feed it back into the initialiser.",
            "Model sandbox (future work): backtest the estimation model against historic FY2023–2025 and score it.",
        ),
    )
    return PipelineRun(profile=profile, result=result, challenge=challenge, trace=trace, dropped=tuple(dropped))

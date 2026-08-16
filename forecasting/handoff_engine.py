"""Config-driven forecast methods for frozen signal handoffs."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .handoff import Guidance, HandoffMetric, HandoffValidationError, SignalHandoff, SourcedFact


HUNDRED = Decimal("100")
TWO = Decimal("2")


@dataclass(frozen=True)
class MetricForecast:
    metric_id: str
    label: str
    unit: str
    low: Decimal
    high: Decimal
    value: Decimal
    method: str
    formula: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class CompanyForecast:
    company_id: str
    target_period: str
    information_cutoff: str
    forecasts: tuple[MetricForecast, ...]
    qualitative_signals: tuple[dict[str, Any], ...]
    unresolved: tuple[dict[str, Any], ...]


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HandoffValidationError(f"{field} must be non-empty text")
    return value.strip()


def _guidance(metric: HandoffMetric) -> Guidance:
    if metric.guidance is None:
        raise HandoffValidationError(f"metric {metric.metric_id} requires source-backed guidance")
    return metric.guidance


def _fact(handoff: SignalHandoff, fact_id: Any, *, unit: str | None = None) -> SourcedFact:
    identifier = _text(fact_id, "fact id")
    fact = handoff.facts.get(identifier)
    if fact is None:
        raise HandoffValidationError(f"required supporting fact is missing: {identifier}")
    if unit and fact.unit != unit:
        raise HandoffValidationError(f"supporting fact {identifier} unit {fact.unit} does not match {unit}")
    return fact


def _range_midpoint(low: Decimal, high: Decimal) -> Decimal:
    return (low + high) / TWO


def _direct_guidance(metric: HandoffMetric, handoff: SignalHandoff) -> MetricForecast:
    guidance = _guidance(metric)
    if guidance.period != handoff.target_period:
        raise HandoffValidationError(
            f"direct guidance for {metric.metric_id} must cover {handoff.target_period}, not {guidance.period}"
        )
    if guidance.unit != metric.unit:
        raise HandoffValidationError(f"guidance unit mismatch for {metric.metric_id}")
    return MetricForecast(
        metric_id=metric.metric_id, label=metric.label, unit=metric.unit,
        low=guidance.low, high=guidance.high, value=_range_midpoint(guidance.low, guidance.high),
        method="direct_guidance",
        formula=f"midpoint({guidance.low}, {guidance.high}) = {_range_midpoint(guidance.low, guidance.high)} {metric.unit}",
        source_ids=(guidance.source_id,),
    )


def _annual_growth_bridge(metric: HandoffMetric, handoff: SignalHandoff) -> MetricForecast:
    guidance = _guidance(metric)
    if guidance.unit != "%":
        raise HandoffValidationError(f"annual growth guidance for {metric.metric_id} must use %")
    plan = metric.plan
    prior = _fact(handoff, plan.get("priorYearFactId"), unit=metric.unit)
    ytd = [_fact(handoff, value, unit=metric.unit) for value in plan.get("reportedYtdFactIds", [])]
    if not ytd:
        raise HandoffValidationError(f"annual growth bridge for {metric.metric_id} requires reportedYtdFactIds")
    seasonality = plan.get("seasonalityFactIds")
    if not isinstance(seasonality, dict) or handoff.target_period not in seasonality:
        raise HandoffValidationError(f"annual growth bridge for {metric.metric_id} requires target seasonalityFactIds")
    seasonal_facts = {
        period: _fact(handoff, fact_id, unit=metric.unit)
        for period, fact_id in seasonality.items()
    }
    if any(fact.value <= 0 for fact in seasonal_facts.values()):
        raise HandoffValidationError(f"seasonality facts for {metric.metric_id} must be positive")
    target_weight = seasonal_facts[handoff.target_period].value
    total_weight = sum((fact.value for fact in seasonal_facts.values()), Decimal("0"))
    ytd_value = sum((fact.value for fact in ytd), Decimal("0"))
    low_total = prior.value * (Decimal("1") + guidance.low / HUNDRED)
    high_total = prior.value * (Decimal("1") + guidance.high / HUNDRED)
    if low_total < ytd_value:
        raise HandoffValidationError(f"annual low guidance for {metric.metric_id} is below reported YTD")
    low = (low_total - ytd_value) * target_weight / total_weight
    high = (high_total - ytd_value) * target_weight / total_weight
    source_ids = tuple(dict.fromkeys([
        guidance.source_id, prior.source_id, *(fact.source_id for fact in ytd),
        *(fact.source_id for fact in seasonal_facts.values()),
    ]))
    return MetricForecast(
        metric_id=metric.metric_id, label=metric.label, unit=metric.unit,
        low=low, high=high, value=_range_midpoint(low, high), method="annual_growth_bridge",
        formula=(
            f"(({prior.value} × (1 + growth/100)) − reported YTD {ytd_value}) × "
            f"{target_weight}/{total_weight} = target-quarter remaining annual value"
        ), source_ids=source_ids,
    )


def _weighted_rate_bridge(metric: HandoffMetric, handoff: SignalHandoff) -> MetricForecast:
    guidance = _guidance(metric)
    if guidance.unit != metric.unit or metric.unit != "%":
        raise HandoffValidationError(f"weighted rate bridge for {metric.metric_id} requires % guidance and metric")
    entries = metric.plan.get("knownRates")
    if not isinstance(entries, list) or not entries:
        raise HandoffValidationError(f"weighted rate bridge for {metric.metric_id} requires knownRates")
    historical_total = _fact(handoff, metric.plan.get("historicalTotalFactId"))
    if historical_total.value <= 0:
        raise HandoffValidationError(f"historical total for {metric.metric_id} must be positive")
    known = Decimal("0")
    weight_total = Decimal("0")
    source_ids = [guidance.source_id]
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise HandoffValidationError(f"knownRates[{index}] must be an object")
        fact = _fact(handoff, entry.get("factId"), unit=metric.unit)
        weight_fact = _fact(handoff, entry.get("weightFactId"))
        weight = weight_fact.value / historical_total.value
        if weight <= 0:
            raise HandoffValidationError(f"knownRates[{index}].weight must be positive")
        known += fact.value * weight
        weight_total += weight
        source_ids.extend((fact.source_id, weight_fact.source_id, historical_total.source_id))
    if weight_total >= Decimal("1"):
        raise HandoffValidationError(f"known rate weights for {metric.metric_id} must total below 1")
    remaining = Decimal("1") - weight_total
    low = (guidance.low - known) / remaining
    high = (guidance.high - known) / remaining
    return MetricForecast(
        metric_id=metric.metric_id, label=metric.label, unit=metric.unit,
        low=low, high=high, value=_range_midpoint(low, high), method="weighted_rate_bridge",
        formula=(
            f"(FY guidance − known weighted rate {known}) / remaining weight {remaining} "
            "= target-quarter comparable rate"
        ), source_ids=tuple(dict.fromkeys(source_ids)),
    )


def _component_sum(metric: HandoffMetric, handoff: SignalHandoff) -> MetricForecast:
    component_ids = metric.plan.get("componentFactIds")
    if not isinstance(component_ids, list) or not component_ids:
        raise HandoffValidationError(f"component sum for {metric.metric_id} requires componentFactIds")
    facts = [_fact(handoff, value, unit=metric.unit) for value in component_ids]
    value = sum((fact.value for fact in facts), Decimal("0"))
    return MetricForecast(
        metric_id=metric.metric_id, label=metric.label, unit=metric.unit,
        low=value, high=value, value=value, method="component_sum",
        formula=" + ".join(str(fact.value) for fact in facts) + f" = {value} {metric.unit}",
        source_ids=tuple(dict.fromkeys(fact.source_id for fact in facts)),
    )


METHODS = {
    "direct_guidance": _direct_guidance,
    "annual_growth_bridge": _annual_growth_bridge,
    "weighted_rate_bridge": _weighted_rate_bridge,
    "component_sum": _component_sum,
}


def forecast_company(handoff: SignalHandoff) -> CompanyForecast:
    """Compile every requested metric. Qualitative signals never move base values."""
    forecasts: list[MetricForecast] = []
    for metric in handoff.metrics:
        for issue in handoff.unresolved:
            affected = issue.get("targetMetricIds")
            if affected is None or (isinstance(affected, list) and metric.metric_id in affected):
                raise HandoffValidationError(
                    f"unresolved evidence blocks {metric.metric_id}: {issue.get('reason', 'unspecified conflict')}"
                )
        method = _text(metric.plan.get("method"), f"metrics[{metric.metric_id}].forecastPlan.method")
        resolver = METHODS.get(method)
        if resolver is None:
            raise HandoffValidationError(f"unsupported forecast method {method} for {metric.metric_id}")
        forecasts.append(resolver(metric, handoff))
    return CompanyForecast(
        company_id=handoff.company_id,
        target_period=handoff.target_period,
        information_cutoff=handoff.information_cutoff.isoformat(),
        forecasts=tuple(forecasts),
        qualitative_signals=tuple(dict(item) for item in handoff.qualitative_signals),
        unresolved=tuple(dict(item) for item in handoff.unresolved),
    )

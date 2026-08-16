"""The required inputs and allowed methods for the twelve challenge metrics.

This is a planning catalogue, not a source of values. A run must still supply
the referenced frozen, source-backed facts in its signal handoff.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricModelTemplate:
    metric_label: str
    allowed_methods: tuple[str, ...]
    required_line_items: tuple[str, ...]


CATALOG: dict[str, tuple[MetricModelTemplate, ...]] = {
    "HD": (
        MetricModelTemplate("Net sales", ("direct_guidance", "annual_growth_bridge"), (
            "prior-year full-year net sales", "reported FY2026 YTD net sales",
            "prior-year remaining-quarter net sales", "FY2026 sales guidance",
        )),
        MetricModelTemplate("Adjusted diluted EPS", ("direct_guidance", "annual_growth_bridge"), (
            "prior-year full-year adjusted diluted EPS", "reported FY2026 YTD adjusted diluted EPS",
            "prior-year remaining-quarter adjusted diluted EPS", "FY2026 adjusted EPS guidance",
        )),
        MetricModelTemplate("Comparable sales, total company", ("direct_guidance", "weighted_rate_bridge"), (
            "reported FY2026 comparable sales", "prior-year quarterly sales weights",
            "prior-year full-year sales", "FY2026 comparable sales guidance",
        )),
    ),
    "ADI": (
        MetricModelTemplate("Revenue", ("direct_guidance", "annual_growth_bridge"), (
            "next-quarter revenue guidance", "reported revenue", "segment revenue",
        )),
        MetricModelTemplate("Adjusted diluted EPS", ("direct_guidance", "annual_growth_bridge"), (
            "next-quarter adjusted EPS guidance", "adjusted operating expense", "tax rate", "diluted shares",
        )),
        MetricModelTemplate("Adjusted gross margin", ("direct_guidance", "weighted_rate_bridge"), (
            "next-quarter adjusted gross-margin guidance", "pricing and mix", "underutilisation charges",
        )),
    ),
    "HAS": (
        MetricModelTemplate("Net fees", ("direct_guidance", "annual_growth_bridge", "component_sum"), (
            "regional net fees", "temporary and permanent fee growth", "reported year-to-date net fees",
        )),
        MetricModelTemplate("Pre-exceptional basic EPS", ("direct_guidance", "annual_growth_bridge"), (
            "pre-exceptional operating profit", "net finance charge", "effective tax rate", "weighted average shares",
        )),
        MetricModelTemplate("Pre-exceptional operating profit", ("direct_guidance", "annual_growth_bridge", "component_sum"), (
            "net fees", "conversion rate", "structural cost savings", "reported year-to-date operating profit",
        )),
    ),
    "DE": (
        MetricModelTemplate("Worldwide net sales and revenues", ("direct_guidance", "annual_growth_bridge", "component_sum"), (
            "segment net sales guidance", "financial services income", "reported year-to-date sales",
        )),
        MetricModelTemplate("Diluted EPS (GAAP)", ("direct_guidance", "annual_growth_bridge"), (
            "net income guidance", "effective tax rate", "diluted weighted average shares",
        )),
        MetricModelTemplate("Production & Precision Ag operating profit", ("direct_guidance", "annual_growth_bridge", "component_sum"), (
            "Production & Precision Ag sales", "segment operating-margin guidance", "price and volume impacts",
        )),
    ),
}


def model_templates(company_id: str) -> tuple[MetricModelTemplate, ...]:
    """Return the required targets for a configured company, or fail explicitly."""
    try:
        return CATALOG[company_id]
    except KeyError as error:
        raise ValueError(f"no forecasting model catalogue for {company_id}") from error

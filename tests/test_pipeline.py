from __future__ import annotations

import unittest
from pathlib import Path

from forecasting import build_pipeline_receipt, load_company_profile, run_pipeline
from forecasting.resolvers import (
    resolve_management_guidance,
    resolve_qualitative_modifier,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "adi-fy2026q2-earnings-release"


def _observations(profile):
    anchor = resolve_management_guidance(
        profile,
        signal_id="adi_revenue_guidance",
        source_id=SOURCE_ID,
        exact_quote=(
            "For the third quarter of fiscal 2026, we are forecasting revenue of "
            "$3.9 billion, +/- $100 million."
        ),
        locator="Outlook for the Third Quarter of Fiscal Year 2026, first paragraph",
        low="3800",
        high="4000",
        units="USDm",
        period="FY2026Q3",
    )
    bookings = resolve_qualitative_modifier(
        profile,
        signal_id="adi_b2b_bookings",
        source_id=SOURCE_ID,
        exact_quote=(
            "We continued to see growing demand in the second quarter with record "
            "bookings across our B2B markets of Industrial, Automotive, and Communications"
        ),
        locator="Management quotations, CFO statement",
        assessment="Constructive bookings; no calibrated increment.",
        period="FY2026Q3",
    )
    return [anchor, bookings]


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = load_company_profile(
            ROOT / "examples" / "adi_profile.json", repository_root=ROOT
        )

    def test_reconciles_to_engine_number_and_records_stages(self) -> None:
        run_result = run_pipeline(
            self.profile, "ADI_REVENUE_FY2026Q3", _observations(self.profile)
        )
        result, challenge, trace = run_result.result, run_result.challenge, run_result.trace
        self.assertTrue(challenge.passed)
        # The signal extractor runs a Tavily web-search stage (offline fallback here).
        self.assertEqual(trace.evidence_search["provider"], "tavily")
        self.assertTrue(trace.evidence_search["queries"])
        # The initialiser built the profile as a pipeline output.
        self.assertGreater(trace.initialiser.sources_verified, 0)
        self.assertGreater(trace.initialiser.profile_sections_built, 0)
        # The consensus is exactly the deterministic engine's number.
        self.assertEqual(trace.analyst.consensus_forecast, str(result.base_forecast))
        # Every resolved signal keeps at least one grounded sub-agent...
        resolved = [e for e in trace.extractions if e.status == "resolved"]
        self.assertTrue(resolved)
        self.assertTrue(all(e.survived >= 1 for e in resolved))
        # ...and the reasoning inspector discards at least one biased sub-agent.
        self.assertTrue(any(e.discarded >= 1 for e in trace.extractions))
        self.assertEqual(len(trace.analyst.opinions), trace.analysts)

    def test_builds_profile_from_a_path(self) -> None:
        # A path source is built by the initialiser inside the pipeline.
        run_result = run_pipeline(
            ROOT / "examples" / "adi_profile.json",
            "ADI_REVENUE_FY2026Q3",
            [{
                "resolver": "management_guidance",
                "signal_id": "adi_revenue_guidance",
                "source_id": SOURCE_ID,
                "exact_quote": "For the third quarter of fiscal 2026, we are forecasting revenue of $3.9 billion, +/- $100 million.",
                "locator": "Outlook for the Third Quarter of Fiscal Year 2026, first paragraph",
                "low": "3800",
                "high": "4000",
                "units": "USDm",
                "period": "FY2026Q3",
            }],
            repository_root=ROOT,
        )
        self.assertEqual(str(run_result.result.base_forecast), "3900")
        self.assertGreater(run_result.trace.initialiser.sources_verified, 0)

    def test_is_deterministic(self) -> None:
        def receipt():
            r = run_pipeline(self.profile, "ADI_REVENUE_FY2026Q3", _observations(self.profile))
            return build_pipeline_receipt(r.profile, r.result, r.challenge, r.trace)

        self.assertEqual(receipt(), receipt())


if __name__ == "__main__":
    unittest.main()

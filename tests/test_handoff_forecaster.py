from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from forecasting.handoff import HandoffValidationError, load_signal_handoff
from forecasting.handoff_engine import forecast_company


QUOTE = "Management issued the disclosed guidance used in this example."


class HandoffForecasterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source_path = self.root / "results.md"
        self.source_path.write_text(QUOTE, encoding="utf-8")
        self.source_hash = hashlib.sha256(self.source_path.read_bytes()).hexdigest()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _source(self) -> dict:
        return {
            "id": "results",
            "url": "https://example.com/results",
            "publishedAt": "2026-05-20",
            "publisher": "Example Co",
            "title": "Results",
            "documentType": "earnings_release",
            "frozenPath": "results.md",
            "sha256": self.source_hash,
        }

    def _fact(self, fact_id: str, value: str, *, unit: str = "USDm", period: str = "FY2026") -> dict:
        return {
            "id": fact_id,
            "value": value,
            "unit": unit,
            "period": period,
            "basis": "reported",
            "sourceId": "results",
            "exactQuote": QUOTE,
            "locator": "Outlook",
        }

    def _handoff(self, metrics: list[dict], facts: list[dict] | None = None) -> dict:
        return {
            "schemaVersion": "signal_handoff.v1",
            "companyId": "EX",
            "targetPeriod": "FY2026Q2",
            "informationCutoff": "2026-06-01T00:00:00+00:00",
            "status": "ready_for_assumptions",
            "sources": [self._source()],
            "metrics": metrics,
            "supportingFacts": facts or [],
            "assumptionSignals": [],
            "unresolved": [],
        }

    def _metric(self, metric_id: str, unit: str, plan: dict, guidance: dict) -> dict:
        return {
            "id": metric_id,
            "label": metric_id,
            "unit": unit,
            "guidance": {**guidance, "sourceId": "results", "exactQuote": QUOTE, "locator": "Outlook"},
            "forecastPlan": plan,
        }

    def _forecast(self, payload: dict):
        path = self.root / "handoff.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        handoff = load_signal_handoff(path, repository_root=self.root)
        return forecast_company(handoff)

    def test_direct_guidance_uses_the_disclosed_midpoint(self) -> None:
        metric = self._metric(
            "revenue", "USDm", {"method": "direct_guidance"},
            {"range": ["3800", "4000"], "unit": "USDm", "period": "FY2026Q2"},
        )

        result = self._forecast(self._handoff([metric]))

        forecast = result.forecasts[0]
        self.assertEqual(forecast.value, Decimal("3900"))
        self.assertEqual(forecast.low, Decimal("3800"))
        self.assertEqual(forecast.high, Decimal("4000"))
        self.assertIn("midpoint", forecast.formula)

    def test_annual_growth_bridge_reconciles_ytd_and_remaining_seasonality(self) -> None:
        metric = self._metric(
            "net_sales", "USDm",
            {
                "method": "annual_growth_bridge",
                "priorYearFactId": "fy2025_sales",
                "reportedYtdFactIds": ["q1_sales"],
                "remainingPeriodWeights": {"FY2026Q2": "0.30", "FY2026Q3": "0.50"},
            },
            {"range": ["5", "15"], "unit": "%", "period": "FY2026", "measure": "sales growth"},
        )
        facts = [
            self._fact("fy2025_sales", "1000", period="FY2025"),
            self._fact("q1_sales", "200", period="FY2026Q1"),
        ]

        result = self._forecast(self._handoff([metric], facts))

        forecast = result.forecasts[0]
        self.assertEqual(forecast.low, Decimal("318.75"))
        self.assertEqual(forecast.high, Decimal("356.25"))
        self.assertEqual(forecast.value, Decimal("337.50"))
        self.assertIn("remaining annual value", forecast.formula)

    def test_weighted_rate_bridge_does_not_treat_percentages_as_additive_levels(self) -> None:
        metric = self._metric(
            "comparable_sales", "%",
            {
                "method": "weighted_rate_bridge",
                "knownRates": [{"factId": "q1_comps", "weight": "0.20"}],
            },
            {"range": ["2", "4"], "unit": "%", "period": "FY2026", "measure": "comparable sales growth"},
        )
        facts = [self._fact("q1_comps", "1", unit="%", period="FY2026Q1")]

        result = self._forecast(self._handoff([metric], facts))

        forecast = result.forecasts[0]
        self.assertEqual(forecast.low, Decimal("2.25"))
        self.assertEqual(forecast.high, Decimal("4.75"))
        self.assertEqual(forecast.value, Decimal("3.50"))

    def test_component_sum_requires_all_declared_components(self) -> None:
        metric = {
            "id": "segment_total", "label": "Segment total", "unit": "USDm",
            "forecastPlan": {"method": "component_sum", "componentFactIds": ["a", "b"]},
        }
        result = self._forecast(self._handoff([metric], [self._fact("a", "10"), self._fact("b", "12")]))

        self.assertEqual(result.forecasts[0].value, Decimal("22"))

    def test_rejects_a_source_that_is_not_frozen_and_hashed(self) -> None:
        metric = self._metric(
            "revenue", "USDm", {"method": "direct_guidance"},
            {"range": ["3800", "4000"], "unit": "USDm", "period": "FY2026Q2"},
        )
        payload = self._handoff([metric])
        del payload["sources"][0]["sha256"]
        path = self.root / "bad.json"
        path.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaises(HandoffValidationError):
            load_signal_handoff(path, repository_root=self.root)


if __name__ == "__main__":
    unittest.main()

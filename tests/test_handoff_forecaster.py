from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from forecasting.handoff import HandoffValidationError, load_signal_handoff
from forecasting.handoff_engine import forecast_company
from forecasting.handoff_receipt import build_company_forecast_payload, build_handoff_receipt
from forecasting.model_catalog import model_templates


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
            "review": {"status": "passed"},
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
                "seasonalityFactIds": {"FY2026Q2": "fy2025_q2_sales", "FY2026Q3": "fy2025_q3_sales"},
            },
            {"range": ["5", "15"], "unit": "%", "period": "FY2026", "measure": "sales growth"},
        )
        facts = [
            self._fact("fy2025_sales", "1000", period="FY2025"),
            self._fact("q1_sales", "200", period="FY2026Q1"),
            self._fact("fy2025_q2_sales", "30", period="FY2025Q2"),
            self._fact("fy2025_q3_sales", "50", period="FY2025Q3"),
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
                "knownRates": [{"factId": "q1_comps", "weightFactId": "fy2025_q1_sales"}],
                "historicalTotalFactId": "fy2025_sales",
            },
            {"range": ["2", "4"], "unit": "%", "period": "FY2026", "measure": "comparable sales growth"},
        )
        facts = [
            self._fact("q1_comps", "1", unit="%", period="FY2026Q1"),
            self._fact("fy2025_q1_sales", "200", period="FY2025Q1"),
            self._fact("fy2025_sales", "1000", period="FY2025"),
        ]

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

    def test_requires_a_passed_evidence_review(self) -> None:
        metric = self._metric(
            "revenue", "USDm", {"method": "direct_guidance"},
            {"range": ["3800", "4000"], "unit": "USDm", "period": "FY2026Q2"},
        )
        payload = self._handoff([metric])
        payload["review"] = {"status": "incomplete"}
        path = self.root / "bad-review.json"
        path.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaisesRegex(HandoffValidationError, "review.status"):
            load_signal_handoff(path, repository_root=self.root)

    def test_receipt_preserves_exact_decimals_while_workbook_payload_is_numeric(self) -> None:
        metric = self._metric(
            "revenue", "USDm", {"method": "direct_guidance"},
            {"range": ["3800.1", "4000.2"], "unit": "USDm", "period": "FY2026Q2"},
        )
        path = self.root / "handoff.json"
        path.write_text(json.dumps(self._handoff([metric])), encoding="utf-8")
        handoff = load_signal_handoff(path, repository_root=self.root)
        result = forecast_company(handoff)

        receipt = build_handoff_receipt(handoff, result)
        payload = build_company_forecast_payload(result)

        self.assertEqual(receipt["forecasts"][0]["value"], "3900.15")
        self.assertEqual(payload["forecasts"][0]["value_decimal"], "3900.15")
        self.assertIsInstance(payload["forecasts"][0]["value"], float)

    def test_unresolved_evidence_blocks_a_affected_metric(self) -> None:
        metric = self._metric(
            "revenue", "USDm", {"method": "direct_guidance"},
            {"range": ["3800", "4000"], "unit": "USDm", "period": "FY2026Q2"},
        )
        payload = self._handoff([metric])
        payload["unresolved"] = [{"targetMetricIds": ["revenue"], "reason": "conflicting guidance"}]

        with self.assertRaisesRegex(HandoffValidationError, "unresolved evidence"):
            self._forecast(payload)

    def test_catalogue_covers_three_target_metrics_per_challenge_company(self) -> None:
        for company_id in ("HD", "ADI", "HAS", "DE"):
            self.assertEqual(len(model_templates(company_id)), 3)

    def test_cli_writes_workbook_payload_and_replayable_receipt(self) -> None:
        metric = self._metric(
            "revenue", "USDm", {"method": "direct_guidance"},
            {"range": ["3800", "4000"], "unit": "USDm", "period": "FY2026Q2"},
        )
        handoff_path = self.root / "handoff.json"
        output_path = self.root / "forecasts" / "EX.json"
        receipt_path = self.root / "receipts" / "EX.json"
        handoff_path.write_text(json.dumps(self._handoff([metric])), encoding="utf-8")

        completed = subprocess.run(
            [
                sys.executable, "-m", "forecasting.cli", "--company", "EX",
                "--input", str(handoff_path), "--output", str(output_path),
                "--receipt", str(receipt_path), "--repository-root", str(self.root),
            ],
            text=True, capture_output=True, check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(output_path.read_text())["forecasts"][0]["value_decimal"], "3900")
        self.assertEqual(json.loads(receipt_path.read_text())["schemaVersion"], "forecast_receipt.v1")


if __name__ == "__main__":
    unittest.main()

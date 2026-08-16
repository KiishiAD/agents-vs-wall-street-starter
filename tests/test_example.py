from __future__ import annotations

import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import example


class ExampleRunTests(unittest.TestCase):
    def test_runs_real_adi_example_and_writes_provenance_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "adi-receipt.json"

            result, report, pipeline = example.run(output)

            self.assertEqual(result.base_range.low, Decimal("3800"))
            self.assertEqual(result.base_forecast, Decimal("3900"))
            self.assertEqual(result.base_range.high, Decimal("4000"))
            self.assertTrue(report.passed)
            receipt = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(receipt["company"]["ticker"], "ADI")
            self.assertEqual(receipt["forecast"]["baseForecast"], "3900")
            self.assertEqual(
                receipt["sources"][0]["url"],
                "https://www.sec.gov/Archives/edgar/data/6281/000000628126000050/adi2q26exhibit991earnings.htm",
            )
            self.assertIn(
                "we are forecasting revenue of $3.9 billion",
                receipt["decisions"]["accepted"][0]["observation"]["provenance"]["exactQuote"],
            )

            # The pipeline trace records the four agent stages and reconciles to
            # the same deterministic number the engine produced.
            self.assertEqual(pipeline.analyst.consensus_forecast, "3900")
            self.assertEqual(pipeline.subagents_per_signal, 5)
            self.assertTrue(all(e.survived >= 1 for e in pipeline.extractions if e.status == "resolved"))
            self.assertTrue(any(e.discarded >= 1 for e in pipeline.extractions))
            block = receipt["pipeline"]
            self.assertEqual(block["initialiser"]["ticker"], "ADI")
            self.assertEqual(block["analyst"]["consensusForecast"], "3900")
            self.assertEqual(len(block["nextSteps"]), 2)


if __name__ == "__main__":
    unittest.main()

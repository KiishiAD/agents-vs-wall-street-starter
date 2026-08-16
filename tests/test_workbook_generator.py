from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import openpyxl

from workbook_generator.cli import WorkbookGenerationError, write_workbook


class WorkbookGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.template = self.root / "template.xlsx"
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Summary"
        sheet.append(["Metric", "Units", "FY2026Q2"])
        sheet.append(["Net sales", "USDm", None])
        sheet.append(["Adjusted diluted EPS", "USD / share", None])
        sheet.append(["Comparable sales, total company", "%", None])
        workbook.save(self.template)
        self.forecast = {
            "schema_version": "company_forecast.v1", "company_id": "HD", "target_period": "FY2026Q2",
            "forecasts": [
                {"metric": "Net sales", "units": "USDm", "value": 47550.0},
                {"metric": "Adjusted diluted EPS", "units": "USD / share", "value": 4.71},
                {"metric": "Comparable sales, total company", "units": "%", "value": 0.5},
            ],
        }

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_writes_only_matching_summary_forecast_cells(self) -> None:
        output = write_workbook(
            company_id="HD", forecast=self.forecast, template=self.template, output=self.root / "HD.xlsx",
        )
        sheet = openpyxl.load_workbook(output)["Summary"]
        self.assertEqual(sheet["C2"].value, 47550.0)
        self.assertEqual(sheet["C3"].value, 4.71)
        self.assertEqual(sheet["C4"].value, 0.5)

    def test_refuses_metric_label_mismatch(self) -> None:
        self.forecast["forecasts"][0]["metric"] = "Revenue"
        with self.assertRaises(WorkbookGenerationError):
            write_workbook(company_id="HD", forecast=self.forecast, template=self.template, output=self.root / "HD.xlsx")


if __name__ == "__main__":
    unittest.main()

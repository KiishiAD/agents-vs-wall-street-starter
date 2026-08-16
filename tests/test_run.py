from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import run

ROOT = Path(__file__).resolve().parents[1]


def _base_job() -> dict:
    config = json.loads((ROOT / "forecasts.json").read_text(encoding="utf-8"))
    job = copy.deepcopy(config["jobs"][0])
    job["trace"] = None  # never touch the real dashboard trace from tests
    return job


class RunResilienceTests(unittest.TestCase):
    def _run(self, jobs, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "cfg.json"
            cfg.write_text(json.dumps({"jobs": jobs}), encoding="utf-8")
            return run.run(cfg, out_dir=Path(tmp), retries=0, **kwargs)

    def test_healthy_job_returns_the_number(self) -> None:
        (row,) = self._run([_base_job()])
        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["base"], "3900")
        self.assertTrue(row["challengePassed"])

    def test_bad_signal_is_dropped_and_run_degrades(self) -> None:
        job = _base_job()
        job["observations"][1]["exact_quote"] = "NOT IN THE SOURCE"  # a modifier
        (row,) = self._run([job])
        self.assertEqual(row["status"], "degraded")
        self.assertEqual(row["base"], "3900")  # still forecasts from the anchor
        self.assertEqual(len(row["droppedSignals"]), 1)

    def test_one_failed_job_does_not_stop_the_batch(self) -> None:
        bad = _base_job()
        bad["id"] = "bad"
        bad["observations"][0]["exact_quote"] = "NOT IN THE SOURCE"  # kill the anchor
        good = _base_job()
        good["id"] = "good"
        rows = self._run([bad, good])
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(by_id["bad"]["status"], "failed")
        self.assertIn("anchor", by_id["bad"]["error"])
        self.assertEqual(by_id["good"]["status"], "ok")
        self.assertEqual(by_id["good"]["base"], "3900")

    def test_parallel_preserves_order_and_isolation(self) -> None:
        jobs = []
        for i in range(4):
            job = _base_job()
            job["id"] = f"job{i}"
            jobs.append(job)
        rows = self._run(jobs, workers=4)
        self.assertEqual([r["id"] for r in rows], ["job0", "job1", "job2", "job3"])
        self.assertTrue(all(r["status"] == "ok" for r in rows))


if __name__ == "__main__":
    unittest.main()

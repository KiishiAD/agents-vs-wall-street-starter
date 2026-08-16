#!/usr/bin/env python3
"""Assemble forecasts.json from the per-company job fragments in build/.

Each initialiser agent writes build/jobs-<TICKER>.json (a JSON array of job
objects). This merges them with the base ADI revenue job into the top-level
forecasts.json the runner consumes. Idempotent; deduplicates by job id.

    python3 scripts/build_forecasts_config.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
CONFIG = ROOT / "forecasts.json"
CUTOFF = "2026-08-16T17:15:00+01:00"

# The ADI revenue job is the original worked example; keep it wired to its
# dashboard trace. Company fragments (build/jobs-*.json) supply the rest.
BASE_JOBS = [
    {
        "id": "adi-revenue",
        "profile": "examples/adi_profile.json",
        "metric": "ADI_REVENUE_FY2026Q3",
        "trace": "dashboard/server/traces/analog-devices.json",
        "observations": [
            {
                "resolver": "management_guidance",
                "signal_id": "adi_revenue_guidance",
                "source_id": "adi-fy2026q2-earnings-release",
                "exact_quote": "For the third quarter of fiscal 2026, we are forecasting revenue of $3.9 billion, +/- $100 million.",
                "locator": "Outlook for the Third Quarter of Fiscal Year 2026, first paragraph",
                "low": "3800",
                "high": "4000",
                "units": "USDm",
                "period": "FY2026Q3",
            },
            {
                "resolver": "qualitative_modifier",
                "signal_id": "adi_b2b_bookings",
                "source_id": "adi-fy2026q2-earnings-release",
                "exact_quote": "We continued to see growing demand in the second quarter with record bookings across our B2B markets of Industrial, Automotive, and Communications",
                "locator": "Management quotations, CFO statement",
                "assessment": "Bookings are constructive, but the release does not provide a calibrated revenue increment.",
                "period": "FY2026Q3",
            },
            {
                "resolver": "qualitative_modifier",
                "signal_id": "adi_q3_demand_outlook",
                "source_id": "adi-fy2026q2-earnings-release",
                "exact_quote": "These positive demand signals are reflected in our outlook for continued strong growth in the third quarter.",
                "locator": "Management quotations, CFO statement",
                "assessment": "Management expects continued strong Q3 growth; retain as range context only.",
                "period": "FY2026Q3",
            },
        ],
    }
]

# Order fragments so the config reads company-by-company.
FRAGMENTS = ["jobs-HD.json", "jobs-ADI.json", "jobs-HAS.json", "jobs-DE.json"]


def main() -> int:
    jobs: list[dict] = []
    seen: set[str] = set()

    def add(job: dict) -> None:
        jid = job.get("id")
        if not jid or jid in seen:
            return
        seen.add(jid)
        jobs.append(job)

    for job in BASE_JOBS:
        add(job)

    found = []
    for name in FRAGMENTS:
        path = BUILD / name
        if not path.is_file():
            continue
        try:
            fragment = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            print(f"skip {name}: invalid JSON ({error})")
            continue
        entries = fragment if isinstance(fragment, list) else fragment.get("jobs", [])
        for job in entries:
            add(job)
        found.append(f"{name} (+{len(entries)})")

    CONFIG.write_text(
        json.dumps({"informationCutoff": CUTOFF, "jobs": jobs}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {CONFIG.name} with {len(jobs)} job(s)")
    print("fragments merged:", ", ".join(found) if found else "none yet")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

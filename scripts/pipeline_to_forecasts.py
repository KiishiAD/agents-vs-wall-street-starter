#!/usr/bin/env python3
"""Bridge the multi-agent pipeline output into the workbook forecast format.

Runs the full pipeline (run.py over forecasts.json), maps each metric to the
exact companies.json label, and writes evaluation/forecasts.pipeline.json in the
same shape write_workbooks.py consumes. Also prints a reconciliation against the
researched central case in evaluation/forecasts.json so the two are comparable.

    python3 scripts/pipeline_to_forecasts.py            # write + reconcile
    python3 scripts/pipeline_to_forecasts.py --quiet    # write only
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # ensure the root run.py wins over scripts/run/

import run  # noqa: E402 - the pipeline runner (root run.py)
COMPANIES = ROOT / "challenge" / "companies.json"
RESEARCHED = ROOT / "evaluation" / "forecasts.json"
OUT = ROOT / "evaluation" / "forecasts.pipeline.json"

# Pipeline metric id -> (ticker, exact companies.json label).
METRIC_LABEL = {
    "HD_NET_SALES_FY2026Q2": ("HD", "Net sales"),
    "HD_ADJ_EPS_FY2026Q2": ("HD", "Adjusted diluted EPS"),
    "HD_COMP_SALES_FY2026Q2": ("HD", "Comparable sales, total company"),
    "ADI_REVENUE_FY2026Q3": ("ADI", "Revenue"),
    "ADI_ADJ_EPS_FY2026Q3": ("ADI", "Adjusted diluted EPS"),
    "ADI_ADJ_GROSS_MARGIN_FY2026Q3": ("ADI", "Adjusted gross margin"),
    "HAS_NET_FEES_FY2026": ("HAS", "Net fees"),
    "HAS_PREEXC_BASIC_EPS_FY2026": ("HAS", "Pre-exceptional basic EPS"),
    "HAS_PREEXC_OP_PROFIT_FY2026": ("HAS", "Pre-exceptional operating profit"),
    "DE_NET_SALES_REV_FY2026Q3": ("DE", "Worldwide net sales and revenues"),
    "DE_DILUTED_EPS_GAAP_FY2026Q3": ("DE", "Diluted EPS (GAAP)"),
    "DE_PPA_OP_PROFIT_FY2026Q3": ("DE", "Production & Precision Ag operating profit"),
}


def build() -> dict:
    rows = run.run(ROOT / "forecasts.json", workers=1)
    out: dict[str, dict] = {}
    for row in rows:
        if row.get("status") == "failed":
            continue
        mapping = METRIC_LABEL.get(row.get("metric", ""))
        if not mapping:
            continue
        ticker, label = mapping
        company = out.setdefault(ticker, {"_basis": "Multi-agent pipeline consensus over the frozen corpus; every value has a provenance receipt in build/."})
        company[label] = float(row["base"])
    return out


def reconcile(pipeline: dict) -> None:
    researched = json.loads(RESEARCHED.read_text()) if RESEARCHED.exists() else {}
    companies = json.loads(COMPANIES.read_text())["companies"]
    print("\n  pipeline vs researched central case")
    print("  " + "-" * 74)
    print(f"  {'metric':44} {'pipeline':>12} {'researched':>12}")
    for c in companies:
        ticker = c["ticker"].split(":")[-1]
        for m in c["metrics"]:
            label = m["label"]
            p = pipeline.get(ticker, {}).get(label)
            r = researched.get(ticker, {}).get(label)
            ps = "—" if p is None else f"{p:,.4g}"
            rs = "—" if r is None else f"{r:,.4g}"
            flag = "" if (p is None or r is None or abs(p - r) <= 1e-9 * max(1, abs(r))) else "  ≠"
            print(f"  {ticker+'/'+label:44.44} {ps:>12} {rs:>12}{flag}")
    print("  " + "-" * 74)


def main(argv: list[str]) -> int:
    pipeline = build()
    OUT.write_text(json.dumps(pipeline, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    total = sum(len([k for k in v if not k.startswith("_")]) for v in pipeline.values())
    print(f"wrote {OUT.relative_to(ROOT)} — {total}/12 metrics")
    if "--quiet" not in argv:
        reconcile(pipeline)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

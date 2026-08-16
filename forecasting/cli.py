"""CLI: validated compact handoff -> workbook-facing forecasts + full receipt."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .handoff import load_signal_handoff
from .handoff_engine import forecast_company
from .handoff_receipt import build_company_forecast_payload, write_handoff_receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile a frozen signal handoff into deterministic forecasts")
    parser.add_argument("--company", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--receipt")
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    handoff = load_signal_handoff(args.input, repository_root=args.repository_root)
    if handoff.company_id != args.company:
        raise SystemExit(f"handoff company {handoff.company_id} does not match --company {args.company}")
    result = forecast_company(handoff)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build_company_forecast_payload(result), indent=2, sort_keys=True) + "\n")
    receipt = Path(args.receipt) if args.receipt else output.with_suffix(".receipt.json")
    write_handoff_receipt(handoff, result, receipt)
    print(json.dumps({"company": args.company, "forecasts": len(result.forecasts), "output": str(output), "receipt": str(receipt)}))


if __name__ == "__main__":
    main()

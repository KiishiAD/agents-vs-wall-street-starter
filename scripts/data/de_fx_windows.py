#!/usr/bin/env python3
"""
Average FRED daily FX rates over Deere fiscal-quarter windows and compute the
year-over-year translation move for each currency.

All rates are converted to a common orientation: USD PER UNIT OF FOREIGN
CURRENCY.  A positive yoy % therefore means the foreign currency APPRECIATED
against the dollar, which TRANSLATES DEERE'S FOREIGN REVENUE UP.

Standard library only.  Reads the fred_*.csv files already downloaded.
"""
import csv
import json
import os
import sys

SCRATCH = ("/private/tmp/claude-501/-Users-cor/"
           "c1ddf24f-b1cc-482f-9e47-45cae42bbce1/scratchpad")

# series -> (currency, orientation)
#   "usd_per_fx"  : quoted as USD per 1 unit of the foreign currency
#   "fx_per_usd"  : quoted as foreign-currency units per 1 USD (needs inverting)
SERIES = {
    "DEXUSEU": ("EUR", "usd_per_fx"),
    "DEXUSUK": ("GBP", "usd_per_fx"),
    "DEXUSAL": ("AUD", "usd_per_fx"),
    "DEXBZUS": ("BRL", "fx_per_usd"),
    "DEXINUS": ("INR", "fx_per_usd"),
    "DEXCAUS": ("CAD", "fx_per_usd"),
    "DEXMXUS": ("MXN", "fx_per_usd"),
    "DEXCHUS": ("CNY", "fx_per_usd"),
    "DEXJPUS": ("JPY", "fx_per_usd"),
    "DEXSDUS": ("SEK", "fx_per_usd"),
    "DEXSZUS": ("CHF", "fx_per_usd"),
    "DEXKOUS": ("KRW", "fx_per_usd"),
    "DEXSFUS": ("ZAR", "fx_per_usd"),
}

# Deere fiscal-quarter windows, (start, end) inclusive, from the period-end
# dates stated in the 10-Q/10-K filings in the corpus.
WINDOWS = {
    "FY2026Q3": ("2026-05-04", "2026-08-02"),
    "FY2025Q3": ("2025-04-28", "2025-07-27"),
    "FY2026Q2": ("2026-02-02", "2026-05-03"),
    "FY2025Q2": ("2025-01-27", "2025-04-27"),
    "FY2026Q1": ("2025-11-03", "2026-02-01"),
    "FY2025Q1": ("2024-10-28", "2025-01-26"),
}


def load(series):
    path = os.path.join(SCRATCH, "fred_%s.csv" % series)
    obs = {}
    with open(path, newline="") as fh:
        r = csv.reader(fh)
        header = next(r)
        for row in r:
            if len(row) < 2:
                continue
            d, v = row[0], row[1].strip()
            if v in ("", "."):
                continue          # FRED holiday / no-quote day: skipped, not zeroed
            try:
                obs[d] = float(v)
            except ValueError:
                continue
    return obs


def window_avg(obs, lo, hi, orientation):
    vals = [v for d, v in obs.items() if lo <= d <= hi]
    if not vals:
        return None, 0
    if orientation == "fx_per_usd":
        vals = [1.0 / v for v in vals]
    return sum(vals) / len(vals), len(vals)


def main():
    out = {}
    for series, (ccy, orient) in SERIES.items():
        obs = load(series)
        rec = {"series": series, "currency": ccy, "orientation_native": orient,
               "windows": {}}
        for name, (lo, hi) in WINDOWS.items():
            avg, n = window_avg(obs, lo, hi, orient)
            rec["windows"][name] = {"avg_usd_per_fx": avg, "n_obs": n,
                                    "start": lo, "end": hi}
        for q in ("Q1", "Q2", "Q3"):
            cur = rec["windows"]["FY2026" + q]["avg_usd_per_fx"]
            pri = rec["windows"]["FY2025" + q]["avg_usd_per_fx"]
            rec.setdefault("yoy_pct", {})[q] = (
                None if (cur is None or pri is None or pri == 0)
                else 100.0 * (cur / pri - 1.0))
        out[ccy] = rec
    json.dump(out, sys.stdout, indent=1)


if __name__ == "__main__":
    main()

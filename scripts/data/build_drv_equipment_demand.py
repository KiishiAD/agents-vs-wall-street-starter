#!/usr/bin/env python3
"""
build_drv_equipment_demand.py

Assembles the DIRECT EQUIPMENT DEMAND panel for the Deere (DE) forecasting
dataset from three upstream extractions:

  1. AEM US Ag Tractor and Combine Report  (unit retail sales + field
     inventory)                       -> fetch_aem_tractor_combine.py
  2. FRED / BLS farm-machinery price indices
                                      -> fetch_fred_equipment_ppi.py
  3. Sandhills Global market reports (used-equipment value trends)
                                      -> fetch_sandhills_used_values.py

Emits the tidy-long CSV required by the project spec:
  series_id,period_end,fiscal_year,fiscal_quarter,value,units,source_type,source,notes

All external (non-Deere) series use the CALENDAR year in fiscal_year, per
spec.  Monthly observations carry the calendar quarter in fiscal_quarter;
period_end always identifies the month unambiguously.

Standard library only.
"""

import calendar
import csv
import datetime as dt
import json
import os
import sys
from collections import defaultdict

HDR = ["series_id", "period_end", "fiscal_year", "fiscal_quarter", "value",
       "units", "source_type", "source", "notes"]

AEM_BOILERPLATE = (
    "AEM US Ag Tractor and Combine Report; preliminary retail unit sales "
    "reported by AEM member manufacturers, 50 states + DC. AEM states the "
    "data are partly estimates subject to revision and cover most but not "
    "all manufacturers.")


def eom(y, m):
    return dt.date(y, m, calendar.monthrange(y, m)[1]).isoformat()


def cq(m):
    return "Q%d" % ((m - 1) // 3 + 1)


# --------------------------------------------------------------- AEM series

# AEM table row -> (series_id for MONTHLY/ANNUAL units, extra note)
UNIT_SERIES = {
    "tractor_2wd_100hp_plus": (
        "us_tractor_unit_sales_100hp_plus",
        "AEM category '2WD 100+ HP'. EXCLUDES 4WD (articulated) tractors, "
        "which are all high-horsepower -- see us_tractor_unit_sales_4wd and "
        "us_tractor_unit_sales_large_total for the combined large-tractor "
        "aggregate. This is the single best public proxy for Deere "
        "Production & Precision Ag end demand."),
    "tractor_total": (
        "us_tractor_unit_sales_total",
        "AEM 'Total Farm Tractors' = all 2WD horsepower classes + 4WD. "
        "Dominated by sub-40 HP units, which map to Small Ag & Turf, not "
        "Production & Precision Ag."),
    "combine_sp": (
        "us_combine_unit_sales",
        "AEM 'Self-Propelled Combines', all sizes. Maps directly to Deere "
        "Production & Precision Ag harvesting."),
    "tractor_4wd": (
        "us_tractor_unit_sales_4wd",
        "AEM '4WD Farm Tractors' (articulated). Low volume, high value; all "
        "units are well above 100 HP."),
    "tractor_2wd_lt40hp": (
        "us_tractor_unit_sales_under40hp",
        "AEM '2WD < 40 HP'. Compact tractors -- Small Ag & Turf read, and a "
        "consumer/housing-sensitive series rather than a row-crop one."),
    "tractor_2wd_40to100hp": (
        "us_tractor_unit_sales_40to100hp",
        "AEM '2WD 40 < 100 HP'. Utility tractors, mostly Small Ag & Turf."),
    "tractor_2wd_total": (
        "us_tractor_unit_sales_2wd_total",
        "AEM 'Total 2WD Farm Tractors' (all horsepower classes, excl. 4WD)."),
}

# categories used for the derived months-of-supply series
MOS_SERIES = {
    "tractor_2wd_100hp_plus": "us_dealer_new_inventory_months_100hp_plus",
    "tractor_total": "us_dealer_new_inventory_months",
    "combine_sp": "us_dealer_new_inventory_months_combines",
}


def load_aem(path):
    """Collapse duplicate observations of the same period into one value.

    A given (key, year, month) is reported many times: once as the
    current-year column of that month's own report, and again as the
    prior-year comparative in the following year's report (by which point AEM
    has revised it).  We keep the LATEST-VINTAGE value -- the revised figure,
    which is what a model fitted on history should see -- and record the
    first-print value in the notes when the two differ.
    """
    raw = json.load(open(path))
    buckets = defaultdict(list)
    for o in raw:
        buckets[(o["key"], o["kind"], o["year"], o["month"])].append(o)

    out = {}
    for k, obs in buckets.items():
        # report vintage "YYYY-MM"; higher == later publication
        obs = sorted(obs, key=lambda o: o["report"])
        first, last = obs[0], obs[-1]
        vals = {round(o["value"], 3) for o in obs}
        note = ""
        if len(vals) > 1:
            note = ("REVISED: AEM first printed %s, latest vintage (%s report) "
                    "is %s; spread across %d vintages = %s."
                    % (fmt(first["value"]), last["report"], fmt(last["value"]),
                       len(obs), fmt(max(vals) - min(vals))))
        out[k] = dict(value=last["value"], source=last["source"],
                      vintage=last["report"], note=note, n=len(obs))
    return out


def fmt(v):
    if v is None:
        return ""
    if abs(v - round(v)) < 1e-9:
        return "%d" % round(v)
    return ("%.3f" % v).rstrip("0").rstrip(".")


def build_aem_rows(aem):
    rows = []
    # ---- monthly unit sales
    monthly = defaultdict(dict)   # key -> {(y,m): rec}
    for (key, kind, y, m), rec in aem.items():
        if kind == "month":
            monthly[key][(y, m)] = rec

    for key, (sid, extra) in UNIT_SERIES.items():
        for (y, m), rec in sorted(monthly.get(key, {}).items()):
            notes = AEM_BOILERPLATE + " " + extra
            if rec["note"]:
                notes += " " + rec["note"]
            rows.append([sid, eom(y, m), y, cq(m), fmt(rec["value"]), "count",
                         "vendor", rec["source"], notes])

    # ---- derived: combined large tractors (2WD 100+ HP plus 4WD)
    a, b = monthly.get("tractor_2wd_100hp_plus", {}), monthly.get("tractor_4wd", {})
    for ym in sorted(set(a) & set(b)):
        y, m = ym
        v = a[ym]["value"] + b[ym]["value"]
        rows.append(["us_tractor_unit_sales_large_total", eom(y, m), y, cq(m),
                     fmt(v), "count", "inference", a[ym]["source"],
                     AEM_BOILERPLATE + " DERIVED = AEM 2WD 100+ HP + AEM 4WD "
                     "farm tractors. This is the 'large tractor' aggregate the "
                     "trade press and sell-side normally quote and is the "
                     "closest unit-level analogue to Deere's North American "
                     "large-ag franchise."])

    # ---- annual totals: the December report's YTD column
    for key, (sid, extra) in UNIT_SERIES.items():
        for (k2, kind, y, m), rec in sorted(aem.items()):
            if k2 != key or kind != "ytd" or m != 12:
                continue
            notes = (AEM_BOILERPLATE + " " + extra +
                     " Full calendar-year total, from the December report's "
                     "year-to-date column.")
            if rec["note"]:
                notes += " " + rec["note"]
            rows.append([sid, "%d-12-31" % y, y, "FY", fmt(rec["value"]),
                         "count", "vendor", rec["source"], notes])

    # ---- field / dealer inventory in units, and months of supply
    inv = defaultdict(dict)
    for (key, kind, y, m), rec in aem.items():
        if kind == "inventory":
            inv[key][(y, m)] = rec

    for key, sid in MOS_SERIES.items():
        iv, mv = inv.get(key, {}), monthly.get(key, {})
        # raw inventory level in units
        for (y, m), rec in sorted(iv.items()):
            rows.append([sid.replace("_months", "_units"), eom(y, m), y, cq(m),
                         fmt(rec["value"]), "count", "vendor", rec["source"],
                         AEM_BOILERPLATE + " NEW-equipment dealer/field "
                         "inventory in units at the START of the report month "
                         "(AEM 'Beginning Inventory'; the pre-2011 Flash "
                         "Reports label the same column 'U.S. Field "
                         "Inventory'). Covers new machines in the dealer "
                         "channel only -- used inventory is NOT included."])
        # months of supply = inventory / trailing-12m average monthly retail
        for (y, m) in sorted(iv):
            hist = []
            yy, mm = y, m
            for _ in range(12):
                mm -= 1
                if mm == 0:
                    mm, yy = 12, yy - 1
                if (yy, mm) in mv:
                    hist.append(mv[(yy, mm)]["value"])
            if len(hist) < 12:
                continue
            avg = sum(hist) / 12.0
            if avg <= 0:
                continue
            rows.append([sid, eom(y, m), y, cq(m), "%.2f" % (iv[(y, m)]["value"] / avg),
                         "ratio", "inference", iv[(y, m)]["source"],
                         "DERIVED months of supply = AEM beginning new-unit "
                         "field inventory divided by the average monthly "
                         "retail unit sales of the preceding 12 months. Uses "
                         "a trailing-12m denominator rather than the current "
                         "month because US tractor retail sales are strongly "
                         "seasonal. Requires 12 prior monthly observations, so "
                         "it is blank wherever the monthly series has a gap. "
                         "NEW equipment only. " + AEM_BOILERPLATE])
    return rows


# ---------------------------------------------------------- Sandhills series

SH_CAT = {
    "high_hp_tractors": ("high-horsepower (100+ hp row-crop and 4WD) "
                         "tractors", "us_used_high_hp_tractor"),
    "combines": ("self-propelled combines", "us_used_combine"),
    "tractors_all": ("the used tractor market as a whole on TractorHouse "
                     "(dominated by high-horsepower row-crop units)",
                     "us_used_tractor"),
    "compact_utility_tractors": ("compact and utility tractors",
                                 "us_used_compact_utility_tractor"),
    "farm_equipment_all": ("used farm equipment overall",
                           "us_used_farm_equipment"),
}
SH_METRIC = {"auction": "auction_value", "asking": "asking_value",
             "inventory": "inventory"}


def build_sandhills_rows(path):
    if not os.path.exists(path):
        return []
    recs = json.load(open(path))
    rows = []
    base_note = ("Sandhills Global monthly market report (TractorHouse / "
                 "Machinery Trader), the Sandhills Equipment Value Index "
                 "family. Sandhills publishes only PERCENTAGE CHANGES free of "
                 "charge -- the EVI level itself is a paid product -- so these "
                 "are changes, not levels. Extracted from the press-release "
                 "prose by regex; sign inferred from the surrounding "
                 "directional wording.")
    for r in recs:
        cat_desc, cat_sid = SH_CAT[r["category"]]
        met = SH_METRIC[r["metric"]]
        for suffix, val, kind in (("mom_pct", r["mom_pct"], "month over month"),
                                  ("yoy_pct", r["yoy_pct"], "year over year")):
            if val is None:
                continue
            sid = "%s_%s_%s" % (cat_sid, met, suffix)
            rows.append([sid, eom(r["year"], r["month"]), r["year"],
                         cq(r["month"]), fmt(val), "percent", "vendor",
                         r["source"],
                         "%s change in Sandhills %s for %s. %s"
                         % (kind.capitalize(), met.replace("_", " "),
                            cat_desc, base_note)])
    return rows


def build_used_index(sh_rows):
    """Chain the used-tractor and used-combine auction M/M changes into an
    index level (first available month = 100).  Explicitly an inference."""
    out = []
    for cat_sid, label in (("us_used_tractor", "used high-horsepower tractors"),
                           ("us_used_combine", "used self-propelled combines")):
        sid_in = "%s_auction_value_mom_pct" % cat_sid
        pts = sorted((r[1], float(r[4]), r[7]) for r in sh_rows
                     if r[0] == sid_in)
        if len(pts) < 6:
            continue
        # only chain across CONSECUTIVE months; a gap breaks the chain
        lvl, prev = 100.0, None
        for period_end, pct, src in pts:
            y, m, _ = (int(x) for x in period_end.split("-"))
            if prev is not None:
                gap = (y - prev[0]) * 12 + (m - prev[1])
                if gap != 1:
                    # restart the chain rather than silently interpolate
                    lvl = 100.0
            else:
                gap = None
            if prev is not None and gap == 1:
                lvl *= (1.0 + pct / 100.0)
            prev = (y, m)
            suffix = "" if cat_sid == "us_used_tractor" else "_combines"
            out.append(["idx_used_equipment_values" + suffix, period_end, y,
                        cq(m), "%.2f" % lvl, "index", "inference", src,
                        "DERIVED index of %s auction values, built by chain-"
                        "linking the month-over-month percentage changes "
                        "Sandhills publishes. Base = 100.00 at the first month "
                        "of each unbroken run of consecutive monthly "
                        "observations; the chain RESTARTS at 100 after any gap "
                        "in the source releases, so compare levels only within "
                        "a run. Not a Sandhills-published index level."
                        % label])
    return out


# --------------------------------------------------------------------- main

def main():
    scratch = os.environ.get("BUILD_SCRATCH", ".")
    out_csv = sys.argv[1]

    rows = []

    aem_json = os.path.join(scratch, "aem_raw_observations.json")
    if os.path.exists(aem_json):
        rows += build_aem_rows(load_aem(aem_json))
    else:
        print("WARNING: no AEM extraction at %s" % aem_json, file=sys.stderr)

    fred_csv = os.path.join(scratch, "fred_ppi.csv")
    if os.path.exists(fred_csv):
        with open(fred_csv) as fh:
            rd = csv.reader(fh)
            next(rd)
            rows += [r for r in rd]
    else:
        print("WARNING: no FRED extraction at %s" % fred_csv, file=sys.stderr)

    sh_rows = build_sandhills_rows(os.path.join(scratch, "sandhills.json"))
    rows += sh_rows
    rows += build_used_index(sh_rows)

    def sort_key(r):
        return (r[0], r[1], r[3] != "FY")
    rows.sort(key=sort_key)

    # drop exact duplicates
    seen, dedup = set(), []
    for r in rows:
        k = (r[0], r[1], r[3])
        if k in seen:
            continue
        seen.add(k)
        dedup.append(r)

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    with open(out_csv, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(HDR)
        w.writerows(dedup)

    print("wrote %d rows -> %s" % (len(dedup), out_csv))
    per = defaultdict(list)
    for r in dedup:
        per[r[0]].append(r[1])
    for sid in sorted(per):
        d = sorted(per[sid])
        print("  %-46s n=%4d  %s .. %s" % (sid, len(d), d[0], d[-1]))


if __name__ == "__main__":
    main()

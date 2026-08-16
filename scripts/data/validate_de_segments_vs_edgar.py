#!/usr/bin/env python3
"""
Independent validation of data/deere/de_segments_modern.csv against SEC EDGAR.

The offline corpus is the primary source. This script re-derives the same segment
figures from a genuinely independent channel -- the XBRL "Financial Report" R-files
that EDGAR renders from each 10-Q/10-K instance document -- and reports agreement.

Note: data.sec.gov's companyconcept/companyfacts APIs expose only NON-dimensional
facts, so segment-dimensioned values are not retrievable there. The R-files are the
keyless way to reach dimensioned segment facts.

Standard library only.
"""

import csv
import html
import json
import os
import re
import sys
import time
import urllib.request

UA = "AgentsVsWallStreet cor@salomo.io"
CIK = "0000315189"
CSV_PATH = "/Users/cor/Documents/projects/agents-vs-wall-street-starter/data/deere/de_segments_modern.csv"

SEGS = {
    "Production & Precision Agriculture (PPA)": "de_ppa",
    "Production and precision agriculture": "de_ppa",
    "Small Agriculture & Turf (SAT)": "de_sat",
    "Small agriculture and turf": "de_sat",
    "Construction & Forestry (CF)": "de_cf",
    "Construction and forestry": "de_cf",
}


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        b = r.read()
    time.sleep(0.25)
    return b if binary else b.decode("utf-8", "replace")


def rfile_text(html_text):
    t = re.sub(r"<[^>]+>", "\n", html_text)
    t = html.unescape(t)
    out = []
    for line in t.split("\n"):
        s = line.strip().replace(" ", " ")
        if s:
            out.append(s)
    return out


def to_num(s):
    s = s.replace("$", "").replace(",", "").strip()
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


NON_SEG_CONTEXTS = {
    "Operating Segment", "Intersegment", "Net Sales", "Finance and Interest Income",
    "Other Income", "Financial Services (FS)", "Financial services",
    "Segment Reconciling Items", "Corporate, Non-Segment", "Reconciling Items",
    "Corporate and Other", "Equipment Operations", "Operating Segments",
    "Material Reconciling Items",
}


def parse_r_segment(lines):
    """Yield (segment_label, metric, [values in column order])."""
    cur_seg = None
    cur_ctx = None
    i = 0
    res = []
    while i < len(lines):
        s = lines[i]
        base = s.split(" | ")[0].strip()
        if base in SEGS:
            cur_seg = SEGS[base]
            cur_ctx = s
            i += 1
            continue
        if cur_seg and s in ("Net Sales and Revenues", "Net Sales and Revenues:"):
            i += 1
            continue
        if cur_seg and s in ("Segment operating profit", "Operating profit"):
            vals = []
            j = i + 1
            while j < len(lines) and to_num(lines[j]) is not None:
                vals.append(to_num(lines[j]))
                j += 1
            res.append((cur_seg, "operating_profit", cur_ctx, vals))
            i = j
            continue
        if cur_seg and s in ("Net sales and revenues", "Net sales"):
            vals = []
            j = i + 1
            while j < len(lines) and to_num(lines[j]) is not None:
                vals.append(to_num(lines[j]))
                j += 1
            res.append((cur_seg, "net_sales", cur_ctx, vals))
            i = j
            continue
        # A new dimension context that is NOT one of our segments ends the current block.
        # Row labels (e.g. 'Intersegment income', 'Cost of sales') must NOT reset it, so
        # only genuine context headers do: any line containing ' | ', or one of the known
        # non-segment axis members.
        if (" | " in s and base not in SEGS) or s in NON_SEG_CONTEXTS:
            cur_seg = None
        i += 1
    return res


MONTHS = {m[:3]: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}


def parse_col_dates(lines):
    """Column header dates, in order, from the R-file preamble."""
    dates = []
    for s in lines[:60]:
        m = re.fullmatch(r"([A-Z][a-z]{2})\.?\s+(\d{1,2}),\s+(\d{4})", s)
        if m:
            dates.append(f"{m.group(3)}-{MONTHS[m.group(1)]:02d}-{int(m.group(2)):02d}")
    return dates


def n_three_month_cols(lines, ndates):
    """R-files list every '<N> Months Ended' group label first, then all the column
    dates. Returns how many leading date columns belong to the 3-month group."""
    groups = [s for s in lines[:60] if re.fullmatch(r"\d+ Months Ended", s)]
    if not groups or groups[0] != "3 Months Ended":
        return 0
    # Deere's quarterly reports always present exactly two 3-month columns
    # (current quarter and prior-year quarter) before any YTD or instant columns.
    return min(2, ndates)


def main():
    subs = json.loads(get(f"https://data.sec.gov/submissions/CIK{CIK}.json"))
    r = subs["filings"]["recent"]
    targets = []
    for form, fdate, acc, rep in zip(r["form"], r["filingDate"],
                                     r["accessionNumber"], r["reportDate"]):
        if form in ("10-Q", "10-K"):
            targets.append((form, fdate, acc.replace("-", ""), rep))

    # load our CSV
    ours = {}
    with open(CSV_PATH) as fh:
        for row in csv.DictReader(fh):
            if row["units"] != "USDm" or row["fiscal_quarter"] == "FY":
                continue
            ours[(row["series_id"], row["period_end"])] = float(row["value"])

    checked = agree = n_filings = 0
    mismatches = []
    covered = set()

    for form, fdate, acc, rep in targets:
        base = f"https://www.sec.gov/Archives/edgar/data/315189/{acc}"
        try:
            fsx = get(base + "/FilingSummary.xml")
        except Exception as e:
            print(f"  skip {form} {fdate}: {e}", file=sys.stderr)
            continue
        cands = []
        for m in re.finditer(r"<Report[^>]*>(.*?)</Report>", fsx, re.S):
            b = m.group(1)
            sn = re.search(r"<ShortName>(.*?)</ShortName>", b)
            fn = re.search(r"<HtmlFileName>(.*?)</HtmlFileName>", b)
            if not sn or not fn:
                continue
            name = html.unescape(sn.group(1))
            if not re.search(r"segment", name, re.I) or "(Details)" not in name:
                continue
            if re.search(r"number of|other disclosur|additional|asset|geograph", name, re.I):
                continue
            cands.append(fn.group(1))
        chosen = None
        for rfile in cands:
            try:
                lines = rfile_text(get(f"{base}/{rfile}"))
            except Exception as e:
                print(f"  skip {form} {fdate} {rfile}: {e}", file=sys.stderr)
                continue
            dates = parse_col_dates(lines)
            n3 = n_three_month_cols(lines, len(dates))
            if not dates or n3 == 0:
                continue
            rows = parse_r_segment(lines)
            if len({r[0] for r in rows if r[1] == "operating_profit"}) >= 3:
                chosen = rfile
                break
        if chosen is None:
            continue
        # Pick, per (segment, metric), the single correct dimension context.
        #   post-ASU 2023-07: external net sales = '<Seg> | Net Sales | Operating Segment'
        #                     operating profit   = '<Seg> | Operating Segment'
        #   pre-ASU:          both live on the bare '<Seg>' context
        PREF = {"net_sales": [frozenset({"Net Sales", "Operating Segment"}),
                              frozenset({"Net Sales"}), frozenset()],
                "operating_profit": [frozenset({"Operating Segment"}), frozenset()]}
        best = {}
        for seg, metric, ctx, vals in rows:
            dims = frozenset(p.strip() for p in ctx.split("|")[1:])
            pref = PREF[metric]
            if dims not in pref:
                continue
            rank = pref.index(dims)
            k = (seg, metric)
            if k not in best or rank < best[k][0]:
                best[k] = (rank, vals)
        n_filings += 1
        for (seg, metric), (_, vals) in sorted(best.items()):
            for k in range(min(n3, len(vals), len(dates))):
                pe = dates[k]
                sid = f"{seg}_{metric}"
                if (sid, pe) not in ours:
                    continue
                checked += 1
                covered.add((sid, pe))
                if abs(ours[(sid, pe)] - vals[k]) < 0.5:
                    agree += 1
                else:
                    mismatches.append((form, fdate, sid, pe, ours[(sid, pe)], vals[k]))

    print(f"filings with a usable 3-month segment R-file: {n_filings}")
    print(f"EDGAR R-file cross-check: {agree}/{checked} values agree "
          f"({len(covered)} distinct series-period cells covered)")
    for m in mismatches:
        print("  MISMATCH:", m)
    per = {}
    for sid, pe in covered:
        per.setdefault(sid, []).append(pe)
    for sid in sorted(per):
        d = sorted(per[sid])
        print(f"  {sid}: {len(d)} periods {d[0]} .. {d[-1]}")


if __name__ == "__main__":
    main()

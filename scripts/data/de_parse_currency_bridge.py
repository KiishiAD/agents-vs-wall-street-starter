#!/usr/bin/env python3
"""
Parse Deere & Company disclosed currency-translation effects out of the frozen
offline corpus (10-Q / 10-K / 8-K / slide-deck markdown).

Two disclosure families are captured, and they are NEVER mixed:

  A) MD&A "Currency translation" / "Currency translation impact on Net sales"
     rows.  Stated in PERCENTAGE POINTS of the year-over-year NET SALES change.
     Scope = segment (PPA / SAT / CF, or legacy A&T) or geography split
     (worldwide equipment ops / U.S. & Canada / outside U.S. & Canada).

  B) Slide-deck earnings-call waterfall "Currency" bars.  USDm, and they apply
     to OPERATING PROFIT, not to net sales.

Blank cells in the MD&A tables mean Deere disclosed no material effect (the
figure rounds to zero at 1pp granularity).  They are emitted as period entries
with value None so downstream code can decide -- they are never coerced to 0
silently, and never dropped without a trace.

Standard library only.
"""
import json
import os
import re
import sys

CORPUS = "/Users/cor/Documents/projects/agents-vs-wall-street-starter/challenge/offline-data/deere"

ZW = dict.fromkeys(map(ord, "​‌‍﻿­"), None)


def clean(s):
    s = s.translate(ZW)
    s = s.replace(" ", " ").replace("–", "-").replace("—", "-")
    s = s.replace("&amp;", "&")
    return re.sub(r"\s+", " ", s).strip()


def split_row(line):
    line = line.strip()
    if not line.startswith("|"):
        return None
    cells = line.split("|")
    if cells and cells[0].strip() == "":
        cells = cells[1:]
    if cells and cells[-1].strip() == "":
        cells = cells[:-1]
    return [clean(c) for c in cells]


def is_sep(cells):
    return bool(cells) and all(
        re.fullmatch(r":?-{2,}:?", c or "") for c in cells if c != "")


def iter_tables(lines):
    i, n = 0, len(lines)
    while i < n:
        if split_row(lines[i]) is None:
            i += 1
            continue
        start = i
        rows = []
        while i < n:
            cells = split_row(lines[i])
            if cells is None:
                break
            if not is_sep(cells):
                rows.append((i, cells))
            i += 1
        if rows:
            yield start, rows


NUM = re.compile(r"^[+-]?\$?\s*\(?\s*\$?\s*\d[\d,]*(?:\.\d+)?\s*%?\s*\)?$")


def parse_num(c):
    if c is None:
        return None
    t = c.strip()
    if t in ("", "-", "--", "N/A", "*", "$"):
        return None
    if not NUM.match(t):
        return None
    neg = t.lstrip().startswith("-") or (t.startswith("(") and t.endswith(")"))
    t = re.sub(r"[()$,%+\-\s]", "", t)
    if t == "":
        return None
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


# ---------------------------------------------------------------- scope map
# ORDER MATTERS: geography qualifiers before the generic catch-alls, and the
# "small" ag test before the plain ag test.
SCOPE_PATTERNS = [
    (r"outside\s+u\.?s\.?\s*(and|&)\s*canada", "OUTSIDE_US_CANADA"),
    (r"^u\.?s\.?\s*(and|&)\s*canada", "US_CANADA"),
    (r"production\s*(and|&)\s*precision\s*ag", "PPA"),
    (r"small\s*ag(riculture)?\s*(and|&)\s*turf", "SAT"),
    (r"construction\s*(and|&)\s*forestry", "CF"),
    (r"^agriculture\s*(and|&)\s*turf", "AT_LEGACY"),
    (r"worldwide net sales", "WW_EQUIP"),
    (r"^worldwide\b", "WW_EQUIP"),
    (r"equipment operations", "WW_EQUIP"),
]


def scope_of(label):
    low = label.lower().strip(": ")
    for pat, code in SCOPE_PATTERNS:
        if re.search(pat, low):
            return code
    return None


CURRENCY_ROW = re.compile(r"^currency translation\b", re.I)
PERIOD_HDR = re.compile(r"(three|six|nine|twelve)\s+months\s+ended", re.I)


def table_period_count(rows):
    """How many distinct reporting periods do this table's columns cover?"""
    seen = []
    for _ln, cells in rows[:3]:
        for c in cells:
            m = PERIOD_HDR.search(c)
            if m:
                key = m.group(1).lower()
                if key not in seen:
                    seen.append(key)
    return seen


def split_periods(cells, nperiods):
    """Map a currency row's numeric cells onto its reporting periods.

    The corpus tables are ragged (zero-width padding cells vary row to row), so
    column indices are unreliable.  What IS reliable is that the periods run
    left to right in equal-width blocks, so the row body is cut into nperiods
    contiguous blocks and each block contributes at most one number.
    """
    body = cells[1:]
    if nperiods <= 1:
        vals = [parse_num(c) for c in body]
        vals = [v for v in vals if v is not None]
        return [vals[-1] if vals else None]
    out = []
    width = len(body) / float(nperiods)
    for k in range(nperiods):
        lo, hi = int(round(k * width)), int(round((k + 1) * width))
        vals = [parse_num(c) for c in body[lo:hi]]
        vals = [v for v in vals if v is not None]
        out.append(vals[-1] if vals else None)
    return out


SKIP_TABLE = re.compile(
    r"comprehensive income|retained earnings|total equity|unrealized|hedg|"
    r"noncontrolling|accumulated other", re.I)

HEADING = re.compile(r"^[#*\s]*([A-Za-z][^|]*?)[*\s:]*$")


def context_scope(lines, start):
    """Fall back to the nearest preceding heading/sentence naming a segment."""
    for j in range(start - 1, max(-1, start - 12), -1):
        raw = clean(lines[j])
        if not raw or raw.startswith("|"):
            continue
        m = HEADING.match(raw)
        if not m:
            continue
        s = scope_of(m.group(1))
        if s:
            return s, m.group(1)[:70]
    return None, None


def file_meta(fn):
    m = re.match(r"^(\d{4}-\d{2}-\d{2})__de-us-\d{8}-(q[1-4]|fy)-([a-z0-9-]+?)__", fn)
    if not m:
        return None
    return {"published": m.group(1), "qtag": m.group(2), "kind": m.group(3)}


def parse_filing(path):
    fn = os.path.basename(path)
    meta = file_meta(fn)
    if meta is None:
        return []
    lines = open(path, encoding="utf-8").read().split("\n")
    out = []
    for start, rows in iter_tables(lines):
        labels = [r[1][0] if r[1] else "" for r in rows]
        joined = " || ".join(labels)
        if "urrency translation" not in joined:
            continue
        if SKIP_TABLE.search(joined):
            continue

        periods = table_period_count(rows)
        nper = max(1, len(periods))

        scope = None
        ctx_scope, ctx_label = context_scope(lines, start)
        net_sales = None

        for ln, cells in rows:
            first = cells[0] if cells else ""
            s = scope_of(first)
            if s:
                scope = s
            if re.match(r"^net sales", first, re.I):
                nums = [parse_num(c) for c in cells[1:]]
                nums = [v for v in nums if v is not None]
                if nums:
                    net_sales = nums[0]

            if CURRENCY_ROW.match(first):
                vals = split_periods(cells, nper)
                if all(v is None for v in vals) and "" == "":
                    pass  # keep: a wholly blank row is still a disclosure
                out.append({
                    "file": fn,
                    "line": ln + 1,
                    "published": meta["published"],
                    "qtag": meta["qtag"],
                    "kind": meta["kind"],
                    "scope": scope or ctx_scope,
                    "scope_from": "row" if scope else ("context" if ctx_scope else None),
                    "context_label": ctx_label,
                    "label": first,
                    "periods": periods or ["fy"],
                    "values": vals,
                    "net_sales_current": net_sales,
                    "raw": cells,
                })
    return out


# --------------------------------------------------- slide operating-profit

SEG_SLIDE = [
    (r"production\s*&?\s*precision\s*ag", "PPA"),
    (r"small\s*ag\s*&\s*turf", "SAT"),
    (r"construction\s*&\s*forestry", "CF"),
]
CUR_BULLET = re.compile(r"currency[\"'’]?\s*(?:with a value of|:)?\s*"
                        r"[\"'’]?\s*\(?\$?\(?(-?[\d,]+)\)?", re.I)


def parse_slide(path):
    fn = os.path.basename(path)
    text = open(path, encoding="utf-8").read()
    lines = text.split("\n")
    out = []
    cur_seg = None
    for i, raw in enumerate(lines):
        l = clean(raw)
        low = l.lower()
        hdr = None
        for pat, code in SEG_SLIDE:
            if re.search(r"^#*\s*\**\s*" + pat, low):
                hdr = code
        if hdr:
            cur_seg = hdr
            continue
        if "currency" not in low or cur_seg is None:
            continue
        if "waterfall" not in low and "operating profit" not in low and "- currency" not in low:
            continue
        # pull "Currency" with an adjacent signed dollar amount
        for m in re.finditer(r'[Cc]urrency"?\s*(?:bar)?\s*(?:with a value of|:)?\s*'
                             r'"?\(?\$?\(?(-?\$?[\d,]+)\)?"?', l):
            tok = m.group(1)
            seg_txt = l[max(0, m.start() - 40):m.start()]
            neg = "(" in l[m.start():m.start() + 30].split(tok)[0]
            v = parse_num(tok.replace("$", ""))
            if v is None:
                continue
            if neg:
                v = -abs(v)
            out.append({"file": fn, "line": i + 1, "segment": cur_seg,
                        "value": v, "snippet": l[max(0, m.start() - 60):m.start() + 40]})
            break
    return out


def main():
    res = {"mdna": [], "slides": []}
    fdir = os.path.join(CORPUS, "filings")
    for fn in sorted(os.listdir(fdir)):
        if fn.endswith(".md"):
            res["mdna"].extend(parse_filing(os.path.join(fdir, fn)))
    sdir = os.path.join(CORPUS, "slides")
    for fn in sorted(os.listdir(sdir)):
        if fn.endswith(".md"):
            res["slides"].extend(parse_slide(os.path.join(sdir, fn)))
    json.dump(res, sys.stdout, indent=1)


if __name__ == "__main__":
    main()

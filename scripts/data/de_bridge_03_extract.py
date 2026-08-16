#!/usr/bin/env python3
"""
Step 2 of the Deere operating-profit-bridge pipeline.

Parse the segment operating-profit WATERFALL BRIDGE out of the OCR'd earnings
slide decks and force every bridge to reconcile against endpoints extracted
independently from the 8-K segment tables (step 1).

Why this is not a simple regex job
----------------------------------
The bridge charts are OCR'd, and the transcription is lossy in five distinct
ways, each of which corrupts a naive read:

  (a) the deck is rendered in FOUR different shapes across 2020-2026 --
      keyed JSON, parallel label/value ARRAYS, a list of {category,value}
      objects, and English prose;
  (b) in the array shape every label is emitted before every value, and the two
      arrays appear in either order, so reading by character position pairs the
      LAST label with the FIRST value -- a silent full reversal of the bridge;
  (c) in the array shape the label order itself is sometimes permuted relative
      to the chart (2Q2022 PPA lists "Price" before "Volume/Mix");
  (d) in prose, a short label ("Other") can sit closer to the PREVIOUS bar's
      number than to its own, so nearest-neighbour pairing shifts the whole tail;
  (e) a component bar is sometimes silently DROPPED, or two labels share one
      number ("two bars labeled SA&G/R&D and Special Items both with $0").

Strategy
--------
1. Shape-detect, then pair INSIDE the shape (index pairing for arrays, key
   pairing for keyed JSON/objects, ORDER-PRESERVING alignment for prose).
2. Validate against the 8-K: the slide's own opening/closing bars must equal the
   8-K's prior-year and current-year segment operating profit, and

       opening + SUM(components) == closing

3. If exactly one canonical component is missing, assign the arithmetic residual
   to it and flag it.  Otherwise REJECT the segment-quarter.

Limits of the arithmetic test, stated honestly: the sum is invariant to a
PERMUTATION of components, so the sum test catches dropped / duplicated /
mis-signed values but cannot by itself catch a label swap.  That is exactly why
step 1 is shape-aware and why the endpoint identity check is applied separately.

Output: <scratch>/de_bridge_parsed.json  + reconciliation report on stdout.
stdlib only.
"""
import json
import os
import re
import sys
from collections import Counter

SLIDES = "/Users/cor/Documents/projects/agents-vs-wall-street-starter/challenge/offline-data/deere/slides"
SCRATCH = "/private/tmp/claude-501/-Users-cor/c1ddf24f-b1cc-482f-9e47-45cae42bbce1/scratchpad"
ENDPOINTS = os.path.join(SCRATCH, "de_segment_op_profit.json")
OUT = os.path.join(SCRATCH, "de_bridge_parsed.json")

CANON = ["volume_mix", "price", "currency", "warranty", "production_costs",
         "sag_rd", "special_items", "other"]
EXTRA = ["voluntary_separation", "impairment"]
ALLCOMP = CANON + EXTRA

LABEL_PATTERNS = [
    ("volume_mix", r"volume\s*[/_]?\s*mix"),
    ("production_costs", r"production[\s_]*costs?"),
    ("sag_rd", r"sa\s*&?\s*_?\s*g\s*[/_]?\s*r\s*&?\s*_?\s*d|s,?\s*a\s*&\s*g"),
    ("special_items", r"special[\s_]*items?"),
    ("voluntary_separation", r"voluntary[\s_]*separation"),
    ("impairment", r"impairments?"),
    ("warranty", r"warranty(?:\s*(?:costs?|expenses?))?"),
    ("currency", r"currency"),
    ("price", r"price(?:\s*realization)?"),
    ("other", r"\bother\b"),
]
LABEL_RE = re.compile("|".join(f"(?P<{k}>{v})" for k, v in LABEL_PATTERNS), re.I)
QLAB_RE = re.compile(r"\b([1-4])\s?Q[\s_]?((?:20)?\d{2})\b", re.I)

MONEY_RE = re.compile(r"""
    (?P<open>\()?\s*(?P<sign1>[-+])?\s*\$\s*(?P<sign2>-)?
    (?P<num>\d{1,3}(?:,\d{3})*|\d+)\s*(?P<tail>\$)?\s*(?P<close>\))?
""", re.X)

NEG_CUE = re.compile(r"(decreas\w+|declin\w+|reduc\w+|\bdown\b|\blower\b|negative)"
                     r"(\s+\S+){0,7}\s*(of|by|to)?\s*[\"']?$", re.I)


def clean(t):
    t = (t.replace("&quot;", '"').replace("&amp;", "&")
          .replace("&#39;", "'").replace("​", ""))
    # strip markdown blockquote prefixes so JSON fences parse as JSON
    return re.sub(r"(?m)^>\s?", "", t)


def money_value(s, m):
    num = int(m.group("num").replace(",", ""))
    neg = bool(m.group("open") and m.group("close"))
    if m.group("sign1") == "-" or m.group("sign2") == "-":
        neg = True
    if not neg and NEG_CUE.search(s[max(0, m.start() - 90):m.start()]):
        neg = True
    return -num if neg else num


def money_tokens(s):
    return [{"start": m.start(), "end": m.end(), "value": money_value(s, m)}
            for m in MONEY_RE.finditer(s)]


def parse_money_str(tok):
    m = MONEY_RE.search(tok)
    if m:
        return money_value(tok, m)
    mm = re.match(r"^\(?\s*([-+]?)(\d[\d,]*)\s*\)?$", tok.strip())
    if not mm:
        return None
    v = int(mm.group(2).replace(",", ""))
    return -v if (mm.group(1) == "-" or tok.strip().startswith("(")) else v


def label_key(text):
    m = LABEL_RE.search(text)
    if not m:
        return None
    for k, _ in LABEL_PATTERNS:
        if m.group(k) is not None:
            return k
    return None


def slot_tokens(s):
    """Ordered list of bridge slots: components plus the two quarter endpoints."""
    out = []
    for m in LABEL_RE.finditer(s):
        for k, _ in LABEL_PATTERNS:
            if m.group(k) is not None:
                out.append({"start": m.start(), "end": m.end(), "key": k})
                break
    for m in QLAB_RE.finditer(s):
        out.append({"start": m.start(), "end": m.end(), "key": "__QTR__"})
    out.sort(key=lambda d: d["start"])
    ded = []
    for t in out:
        if ded and t["start"] < ded[-1]["end"]:
            continue
        ded.append(t)
    return ded


# ------------------------------------------------------------------ JSON shapes
def json_arrays(blk):
    """Pull every quoted-string array; align a LABEL array to a VALUE array by
    index.  Handles either array order and multi-line arrays."""
    arrs = []
    for m in re.finditer(r'"([A-Za-z_ ]{1,24})"\s*:\s*\[([^\[\]]*)\]', blk, re.S):
        items = re.findall(r'"([^"]*)"', m.group(2))
        if len(items) < 5:
            continue
        nval = sum(1 for i in items if parse_money_str(i) is not None)
        nlab = sum(1 for i in items if label_key(i) or QLAB_RE.search(i))
        arrs.append({"name": m.group(1), "items": items,
                     "kind": "value" if nval > nlab else "label",
                     "n": len(items)})
    labs = [a for a in arrs if a["kind"] == "label"]
    vals = [a for a in arrs if a["kind"] == "value"]
    for la in labs:
        for va in vals:
            if la["n"] != va["n"]:
                continue
            if sum(1 for i in la["items"] if label_key(i)) < 4:
                continue
            comps, ends = {}, []
            for l, v in zip(la["items"], va["items"]):
                x = parse_money_str(v)
                if x is None:
                    continue
                if QLAB_RE.search(l) and not label_key(l):
                    ends.append(x)
                    continue
                k = label_key(l)
                if k:
                    comps.setdefault(k, x)
            if len(comps) >= 5:
                return comps, ends
    return None, None


OBJ_RE = re.compile(r'\{[^{}]*"(?:category|period|label|name)"\s*:\s*"([^"]*)"'
                    r'[^{}]*"value"\s*:\s*"([^"]*)"[^{}]*\}', re.S)


def json_objects(blk):
    hits = OBJ_RE.findall(blk)
    if len(hits) < 5:
        return None, None
    comps, ends = {}, []
    for lab, v in hits:
        x = parse_money_str(v)
        if x is None:
            continue
        if QLAB_RE.search(lab) and not label_key(lab):
            ends.append(x)
            continue
        k = label_key(lab)
        if k:
            comps.setdefault(k, x)
    return (comps, ends) if len(comps) >= 5 else (None, None)


def json_keyed(blk):
    comps, ends = {}, []
    for m in re.finditer(r'"([^"]{2,40})"\s*:\s*"([^"]{1,20})"', blk):
        k, v = m.group(1), m.group(2)
        x = parse_money_str(v)
        if x is None or re.search(r"net[\s_]*sales|^sales", k, re.I):
            continue
        kk = label_key(k)
        if kk and not QLAB_RE.search(k):
            comps.setdefault(kk, x)
        elif QLAB_RE.search(k) and re.search(r"profit|^op", k, re.I):
            ends.append(x)
    return (comps, ends) if len(comps) >= 5 else (None, None)


# ---------------------------------------------------------------------- prose
def prose_aligned(blk, opening, closing):
    """ORDER-PRESERVING alignment.  Deere prose always narrates the waterfall
    left to right, alternating slot and number, so the i-th slot owns the i-th
    number.  A leading net-sales chart can inject extra numbers, so we slide the
    value window until the quarter slots land exactly on the 8-K endpoints."""
    slots = slot_tokens(blk)
    vals = money_tokens(blk)
    n = len(slots)
    if n < 6 or len(vals) < n:
        return None, None
    for off in range(0, len(vals) - n + 1):
        window = vals[off:off + n]
        ends = [window[i]["value"] for i, s in enumerate(slots) if s["key"] == "__QTR__"]
        if not ends:
            continue
        if opening not in ends and closing not in ends:
            continue
        comps = {}
        bad = False
        for s, v in zip(slots, window):
            if s["key"] == "__QTR__":
                continue
            if s["key"] in comps:
                bad = True
                break
            comps[s["key"]] = v["value"]
        if bad or len(comps) < 5:
            continue
        if opening + sum(comps.values()) == closing:
            return comps, ends
    return None, None


def prose_greedy(blk):
    """Fallback: gap-based greedy pairing that PREFERS the number following the
    label, so a short trailing label cannot steal the previous bar's number."""
    slots = slot_tokens(blk)
    vals = money_tokens(blk)
    if not slots or not vals:
        return {}, []
    cand = []
    for si, s in enumerate(slots):
        for vi, v in enumerate(vals):
            if v["start"] >= s["end"]:
                d = v["start"] - s["end"]
            else:
                d = (s["start"] - v["end"]) + 40      # directional penalty
            cand.append((d, si, vi))
    cand.sort()
    us, uv, pairs = set(), set(), {}
    for d, si, vi in cand:
        if si in us or vi in uv or d > 320:
            continue
        us.add(si)
        uv.add(vi)
        pairs[si] = vi
    comps, ends = {}, []
    for si, vi in pairs.items():
        if slots[si]["key"] == "__QTR__":
            ends.append(vals[vi]["value"])
        else:
            comps.setdefault(slots[si]["key"], vals[vi]["value"])
    return comps, ends


def parse_block(blk, opening, closing):
    for name, fn in (("json_objects", json_objects),
                     ("json_arrays", json_arrays),
                     ("json_keyed", json_keyed)):
        c, e = fn(blk)
        if c:
            return name, c, e
    c, e = prose_aligned(blk, opening, closing)
    if c:
        return "prose_aligned", c, e
    return "prose_greedy", *prose_greedy(blk)


# ---------------------------------------------------------------- block finder
ANCHOR_RE = re.compile(r"volume\s*[/_]?\s*mix", re.I)
SEG_HINTS = [
    (re.compile(r"production\s*(&|and)\s*precision\s*ag", re.I), "PPA"),
    (re.compile(r"small\s*ag(riculture)?\s*(&|and)\s*turf", re.I), "SAT"),
    (re.compile(r"construction\s*(&|and)\s*forestry", re.I), "CF"),
    (re.compile(r"agriculture\s*(&|and)\s*turf", re.I), "AT"),
]


def segment_hint(text, pos):
    best = None
    for pat, key in SEG_HINTS:
        for m in pat.finditer(text, 0, pos):
            if best is None or m.start() > best[0]:
                best = (m.start(), key)
    return best[1] if best else None


def find_blocks(text):
    out = []
    for m in ANCHOR_RE.finditer(text):
        lo = text.rfind("\n\n", max(0, m.start() - 3000), m.start())
        lo = 0 if lo < 0 else lo + 2
        hi, cur = m.end(), m.end()
        for _ in range(8):
            nxt = text.find("\n\n", cur)
            nxt = len(text) if nxt < 0 else nxt
            hi, cur = nxt, nxt + 2
            look = text[hi:hi + 300]
            if re.search(r"\n#{1,6} |\*Image:|!\[|Image Description", look):
                break
            if not re.search(r"\$|profit|financially_relevant|\]", look):
                break
        out.append((m.start(), lo, min(hi, lo + 5000)))
    merged = []
    for pos, lo, hi in out:
        if merged and lo <= merged[-1][2]:
            merged[-1] = (merged[-1][0], min(merged[-1][1], lo), max(merged[-1][2], hi))
        else:
            merged.append((pos, lo, hi))
    return merged


def deck_period(fn, text):
    m = re.search(r'period:\s*"([^"]+)"', text)
    if m:
        mm = re.match(r"([1-4])Q\s*(\d{4})", m.group(1))
        if mm:
            return int(mm.group(2)), int(mm.group(1))
    y, mo = int(fn[:4]), int(fn[5:7])
    q = {2: 1, 5: 2, 6: 2, 8: 3, 11: 4, 12: 4}.get(mo)
    return (y, q) if q else (None, None)


def main():
    endpoints = json.load(open(ENDPOINTS))
    results, rejects = [], []

    for fn in sorted(os.listdir(SLIDES)):
        raw = clean(open(os.path.join(SLIDES, fn), encoding="utf-8").read())
        fy, fq = deck_period(fn, raw)
        if not fy:
            continue
        key = f"{fy}Q{fq}"
        ep = endpoints.get(key)
        if not ep:
            continue
        segs = {k: v for k, v in ep.items() if not k.startswith("_")}
        seen = set()

        for pos, lo, hi in find_blocks(raw):
            blk = raw[lo:hi]
            hint = segment_hint(raw, pos)
            order = ([hint] if hint in segs else []) + [s for s in segs if s != hint]
            best = None
            for seg in order:
                if seg in seen:
                    continue
                o, c = segs[seg]["pri"], segs[seg]["cur"]
                shape, comps, ends = parse_block(blk, o, c)
                comps = {k: v for k, v in comps.items() if k in ALLCOMP}
                if len(comps) < 5:
                    continue
                resid = c - o - sum(comps.values())
                missing = [x for x in CANON if x not in comps]
                if resid == 0:
                    tier = 0
                elif len(missing) == 1:
                    tier = 1
                else:
                    continue
                cand = (tier, seg, shape, comps, ends,
                        missing[0] if tier == 1 else None)
                if best is None or cand[0] < best[0]:
                    best = cand
                if tier == 0:
                    break
            if best is None:
                shape, comps, ends = parse_block(blk, 0, 0)
                rejects.append({"file": fn, "period": key, "hint": hint,
                                "shape": shape, "parsed": comps,
                                "sum": sum(comps.values()) if comps else None,
                                "reason": "no segment reconciles"})
                continue
            tier, seg, shape, comps, ends, filled = best
            o, c = segs[seg]["pri"], segs[seg]["cur"]
            comps = dict(comps)
            if filled:
                comps[filled] = c - o - sum(comps.values())
            seen.add(seg)
            ep_ok = None
            if ends:
                ep_ok = (o in ends and c in ends) if len(ends) >= 2 else \
                        (o in ends or c in ends)
            results.append({
                "file": fn, "fiscal_year": fy, "fiscal_quarter": fq,
                "segment": seg, "segment_hint": hint, "shape": shape,
                "opening": o, "closing": c, "components": comps,
                "recovered_component": filled,
                "residual": c - o - sum(comps.values()),
                "slide_endpoints_agree": ep_ok, "tier": tier})

        for seg in segs:
            if seg not in seen:
                rejects.append({"file": fn, "period": key, "segment": seg,
                                "reason": "no reconciling bridge block"})

    json.dump({"bridges": results, "rejects": rejects}, open(OUT, "w"), indent=1)

    print(f"reconciled bridge-quarters: {len(results)}")
    print("by segment:", dict(Counter(r["segment"] for r in results)))
    print("by OCR shape:", dict(Counter(r["shape"] for r in results)))
    print("exact (residual 0, nothing recovered):",
          sum(1 for r in results if r["tier"] == 0))
    print("one component recovered from arithmetic residual:",
          sum(1 for r in results if r["recovered_component"]))
    print("slide endpoints agree with 8-K:",
          dict(Counter(str(r["slide_endpoints_agree"]) for r in results)))
    print(f"\nrejects: {len(rejects)}")
    for r in rejects:
        print("  REJECT", r.get("period"), r.get("segment", r.get("hint")),
              r["reason"], r.get("shape", ""), r.get("parsed", ""))
    print()
    for r in sorted(results, key=lambda x: (x["fiscal_year"], x["fiscal_quarter"], x["segment"])):
        chk = r["opening"] + sum(r["components"].values())
        print(f"{'OK ' if chk == r['closing'] else 'BAD'} {r['fiscal_year']}Q{r['fiscal_quarter']} "
              f"{r['segment']:3} {r['shape']:14} {r['opening']:>6} -> {r['closing']:>6} "
              f"rec={str(r['recovered_component']):16} " +
              " ".join(f"{k[:4]}={r['components'].get(k)}" for k in CANON))


if __name__ == "__main__":
    sys.exit(main())

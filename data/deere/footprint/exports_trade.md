# Deere: export flows and cross-border production

Companion to `exports_trade.csv`. Built 2026-08-16, before Deere reports FY2026 Q3 on
2026-08-20. **No Q3 FY2026 actuals exist and none are used here.**

This file answers one question: **how does activity at a Deere plant in one country turn into
revenue booked in another?** The geographic revenue matrix tells you where the *customers* are.
It does not tell you where the *machines were built*. Export flows are the bridge, and without
that bridge a plant-level employment signal cannot be pointed at a geographic revenue line.

---

## 1. Bottom line

**The export bridge is real but narrow. It runs almost entirely to Canada.**

US machinery exports send **47–60% of every dollar to Canada** across all four HS codes. Deere
has no meaningful ag or construction *assembly* in Canada, so Canadian revenue is almost purely
machines built in US plants and trucked north. Everywhere else, Deere builds locally: 45 factory
locations outside the US and Canada, against 23 owned inside it.

That structural claim makes a falsifiable prediction, and the data confirms it:

| Deere revenue line | vs US HS exports | n | r |
|---|---|---|---|
| **Canada** | exports **to Canada**, HS 8432+8433 | 6 | **+0.994** |
| **Canada** | exports **to Canada**, HS 8429 | 6 | **+0.967** |
| **Canada** | exports **to Canada**, HS 8701 | 6 | +0.775 |
| Outside US & Canada | exports to world, HS 8432+8433 | 8 | +0.329 |
| Outside US & Canada | exports to world, HS 8429 | 9 | +0.117 |
| Outside US & Canada | exports to world, HS 8432+8433+8701 | 6 | +0.388 |

**Read the contrast, not the levels.** With n=6 an r of +0.99 is one or two points doing all the
work and is *not* evidence of a reliable relationship on its own. What is meaningful is that the
*same* export series is strongly related to Canadian revenue and essentially unrelated to
rest-of-world revenue — exactly what Deere's disclosed footprint predicts. The correlation is
weak where local plants serve local demand and strong where they do not.

**Practical consequence for the employment-signal thesis:** US plant headcount maps to
*US + Canada* shipments, which is roughly 60% of Deere revenue (FY2025: US $23,974m + Canada
$3,735m = $27,709m of $45,684m). It does **not** map to Western Europe, Latin America or
Asia revenue. To read those, you need headcount at the German, Brazilian and Indian plants.

---

## 2. Where Deere builds versus where it sells

Deere's own words (FY2025 10-K, Item 1):

> Our global manufacturing footprint allows us whenever possible to produce our products close to
> the markets where they are sold. For example, most of our large agricultural equipment is
> assembled in the U.S. for our U.S. customers.

Counts and capital, both from the 10-K:

| Measure | Value | Source |
|---|---|---|
| Owned factory locations, US & Canada | 23 (+4 leased) | FY2025 10-K Item 2 |
| Factory locations outside US & Canada | 45 | FY2025 10-K Item 2 |
| Countries hosting those 45 | Argentina, Austria, Brazil, China, Finland, France, Germany, India, Israel, Italy, Mexico, Netherlands, New Zealand, Spain | FY2023/FY2024 10-K (FY2025 drops the list) |
| Property & equipment, US | $4,198m | FY2025 10-K |
| Property & equipment, Germany | $1,435m | FY2025 10-K |
| Property & equipment, other countries | $2,446m | FY2025 10-K |

The property-by-country series (FY2013–FY2025, in the CSV) contains one structural break worth
knowing: **Germany's book value roughly doubled between FY2017 ($598m) and FY2018 ($1,164m)** on
the Wirtgen acquisition. That is why roadbuilding revenue is booked heavily in Europe and why the
Construction & Forestry segment is the most import-exposed of the three — and, as it turns out,
why CF absorbed **50%** of Deere's IEEPA tariff refund.

Deere's own import-dependence disclosure, which is a directly trackable series:

| Date | "…of our domestic sales are assembled in the U.S." | Source |
|---|---|---|
| 2025-05-15 | nearly **80%** | Q2 FY2025 10-Q |
| 2025-08-14 | nearly **80%** | Q3 FY2025 10-Q |
| 2025-11-26 | nearly **80%** | FY2025 10-K |
| 2026-02-19 | nearly **75%** | Q1 FY2026 10-Q |
| 2026-05-28 | *sentence removed* | Q2 FY2026 10-Q |

A 5-point drop in domestic assembly share, then the disclosure disappearing entirely, is worth
flagging. It is consistent with a higher imported share of US sales (Deere names Europe, Mexico,
India and Japan as the import sources) and it raises tariff exposure per dollar of US revenue.
It is **not** proof of anything on its own — the withdrawal of a voluntary sentence has many
innocent explanations — but it is the kind of change a durable tracker should catch.

---

## 3. US export flows by HS code

US exports to the world, FOB, USD bn (UN Comtrade, reporter USA):

| Year | 8432 soil-prep | 8433 harvesting | 8701 tractors\* | 8429 construction |
|---|---|---|---|---|
| 2012 | 1.12 | 4.61 | 8.11 | 8.31 |
| 2015 | 0.65 | 3.32 | 5.08 | 4.59 |
| 2016 | 0.61 | 2.92 | 3.97 | 3.53 |
| 2019 | — | 3.20 | 6.02 | 4.19 |
| 2020 | 0.56 | 2.85 | 3.98 | 3.49 |
| 2022 | 0.88 | 4.84 | 6.30 | 4.94 |
| 2023 | 0.89 | 5.27 | 7.92 | 5.88 |
| 2024 | 0.69 | 4.20 | 6.59 | 4.82 |
| 2025 | 0.63 | 3.91 | 4.88 | — |

**2024 → 2025: 8432 −9%, 8433 −7%, 8701 −26%.** The industry was exporting materially less
machinery through 2025, consistent with the ag downcycle Deere is guiding to (PPA −5 to −10% in
FY2026).

Destination mix, 2024, USD bn:

| HS | Canada | EU-27 | Australia | Mexico | Brazil | Canada share |
|---|---|---|---|---|---|---|
| 8432 | 0.42 | 0.07 | 0.04 | 0.03 | 0.02 | **60%** |
| 8433 | 1.98 | 0.60 | 0.43 | 0.34 | 0.32 | **47%** |
| 8701 | 3.97 | 0.55 | 0.75 | 0.49 | 0.15 | **60%** |
| 8429 | 2.83 | 0.27 | 0.42 | 0.50 | 0.06 | **59%** |

Brazil and the EU are strikingly small destinations for *US* machinery exports — because Deere
(and its competitors) build there. Deere's Latin America revenue was $5,607m in FY2025; total US
exports of all four HS codes to Brazil were about $0.55bn in 2024 **for the entire industry**.
Latin American revenue is overwhelmingly Brazilian-built.

---

## 4. This is a sector proxy, not a Deere measure

**These HS codes cover the whole industry.** Every US-based exporter is in the same series and
none of them can be separated out. Nothing in this dataset is Deere-only.

Known contaminants by code:

- **HS 8432** (soil prep, planters, seeders) — AGCO (White Planters, Sunflower), CNH
  (Case IH Early Riser), Kinze, Great Plains/Landoll, Vermeer. Deere is the share leader in US
  planters but this is a crowded, heavily short-line category.
- **HS 8433** (harvesting, threshing, mowers) — AGCO (Gleaner, Massey combines), CNH
  (Case IH Axial-Flow, New Holland), Claas of America (Omaha-built combines exported from the
  US), Kubota and Toro in the mower sub-headings. Note 8433 also contains **lawn mowers**
  (8433.11/8433.19), which map to Deere's Small Ag & Turf segment rather than Production Ag —
  the code mixes two different Deere segments.
- **HS 8701 (largest contamination risk)** — this heading includes **road tractors for
  semi-trailers** (8701.21–8701.29), i.e. highway trucks, alongside agricultural tractors
  (8701.91–8701.95). The $6.59bn 2024 figure is **not** mostly farm tractors. Freightliner,
  Peterbilt, Kenworth and Mack sit inside this number. **Do not read HS 8701 at the 4-digit
  level as an agriculture signal.** Any serious use of this code needs HS6 detail
  (8701.91–8701.95 only), which this build does not have — see gaps below.
- **HS 8429** (dozers, graders, excavators, loaders) — **Caterpillar dominates**, plus Komatsu
  America, Volvo CE, Terex, Bobcat/Doosan. Deere CF is a minority of this flow. The +0.967
  Canada correlation for 8429 is therefore best read as "US construction-machinery output tracks
  Canadian demand", which Deere participates in, not as a Deere-specific measure.

Kubota's US exports are modest (it mainly *imports* into the US from Japan and Thailand), so it
contaminates the *import* side more than the export side.

---

## 5. Tariffs and trade policy, 2025–2026

2026 is an unusually eventful policy year and several events land **inside the Q3 FY2026 window
(4 May – 2 Aug 2026)**. Deere's own filings corroborate the key ones.

### Timeline

| Date | Event | In Q3 window? |
|---|---|---|
| 2025-08-18 | Steel/aluminium derivative duty scope expanded to more HTS codes | no |
| 2026-02-20 | **Supreme Court invalidates IEEPA tariffs** (6–3) | no |
| 2026-02-24 | Section 122: 10% additional ad valorem on all imports, as IEEPA replacement | no |
| 2026-03-04 | CIT orders CBP to liquidate/reliquidate without IEEPA duties | no |
| 2026-04-06 | **Section 232 derivative duty extended to ag machinery (HS 8432, 8433) at 25%** (Proc. 11021) | no |
| 2026-04-20 | CBP opens CAPE refund process, phase 1 | no |
| **2026-05-07** | **CIT strikes down the Section 122 10% baseline as ultra vires** | **yes (day 4)** |
| **2026-06-08** | **Section 232 ag machinery rate cut 25% → 15%**, through 2027-12-31 | **yes** |
| **2026-06-29** | CAPE phase 2 opens (reconciliation, AD/CVD, finally-liquidated entries) | **yes** |
| **2026-07-31** | CBP: 17.69m entries liquidated, ~$128.68bn refunds accepted for processing | **yes** |
| 2026-08-04 | CBP status declaration filed with CIT | no (Q4) |

### Deere's disclosed tariff economics

| Period | Direct incremental tariff cost | Source |
|---|---|---|
| Q2 FY2025 | ~$95m | Q2 FY2025 10-Q |
| 9M FY2025 | ~$300m (implies ~$205m in Q3 FY2025) | Q3 FY2025 10-Q |
| FY2025 | ~$600m (implies ~$300m in Q4 FY2025) | FY2025 10-K |
| Q1 FY2026 | $361m gross | Q1 FY2026 10-Q |
| H1 FY2026 | **$372m net** of a **$272m** IEEPA recovery | Q2 FY2026 10-Q |

Backing out Q2 FY2026: gross H1 = 372 + 272 = $644m, so **gross Q2 ≈ $283m** and **net Q2 ≈
$11m**. The $272m recovery was allocated **20% PPA / 30% SAT / 50% CF**.

### What this means for Q3 FY2026

Three things pushed the *net* tariff line favourably during Q3, and they compound:

1. The **Section 122 10% baseline died on 7 May**, three days into the quarter — so Q3 carried
   essentially none of it, against a Q1 that was fully exposed.
2. The **ag machinery Section 232 rate halved** (25% → 15%) from 8 June, covering roughly the
   last eight weeks of the quarter.
3. **CAPE phases 2 and 3 opened during the quarter**, and Deere's Q2 claim was explicitly
   described as a first-phase filing. Additional recoveries in Q3 are plausible.

**Direction, not magnitude.** Deere's gross tariff cost in Q3 FY2026 was very likely well below
Q1's $361m, and there is a real chance of a further recovery credit. Against a Q3 FY2025
comparative of roughly $205m of tariff cost, the year-on-year *cost* comparison should be
favourable. I am deliberately not putting a number on it: the refund amount depends on Deere's
own entry-level filings, which are not public, and the government has appealed the CIT refund
order to the Federal Circuit, so recognised recoveries carry reversal risk.

**Retaliation side.** Deere is "a net exporter of agriculture and turf equipment from the U.S.",
so foreign retaliation hits its export prices and margins rather than its input costs. Through
2026 the retaliation picture eased — notably China suspended retaliatory tariffs on US goods and
resumed soybean purchases, which supports US farm income and therefore ag equipment demand with
a lag. This is a demand tailwind for FY2027 rather than a Q3 FY2026 shipment effect.

---

## 6. Coverage, gaps and honesty

### What is in the CSV

744 rows, 62 series. By `source_type`: 641 trade-data, 96 filing, 8 news, 2 company-site (counts
shift slightly with each refresh as trade data is topped up).

- `us_exports_hs{8432,8433,8701,8429}` — annual world totals, 2012–2025 (12–14 years per code)
- `us_exports_hs*_{canada,mexico,brazil,germany,eu27,australia,argentina,united_kingdom,china}`
  — annual by destination
- `us_exports_hs8432` — **monthly**, 2012-01 to 2022-05
- `de_property_equipment_{united_states,germany,other_countries}` — FY2013–FY2025
- `de_net_sales_{us_canada,outside_us_canada}` — FY2013–FY2021
- `de_net_sales_canada` — FY2019–FY2025
- `de_domestic_assembly_share`, `de_tariff_direct_cost`, `de_tariff_recovery*`,
  `de_factory_count_*`
- `us_sec232_ag_machinery_tariff_rate`, `us_sec122_baseline_tariff_rate`, `us_cape_refund_phase`,
  `us_ieepa_*`

### Real gaps — not filled with estimates

- **Monthly data covers only HS 8432, and only to 2022-05.** The UN Comtrade public tier enforces
  an hourly call-volume quota and each request returns exactly one period; the monthly series for
  8433/8701/8429 needs roughly 300 more calls than one quota window allows. **The quarterly
  correlation therefore did not run (n=0)** and every correlation reported here is annual. A
  top-up job is scripted and queued; see "How to refresh".
- **No HS6 detail.** HS 8701 at 4 digits is contaminated by highway truck tractors and I could
  not separate 8701.91–8701.95. This is the single most important gap: the tractor series as
  published should not be used as an agriculture indicator.
- **Brazil and India reporter series are absent.** They were third in the fetch queue and the
  quota ran out first. Requested by the task; not delivered.
- **A few annual years are missing** per code (8432 2019, 8701 2014/2021, 8429 2025, all codes
  2026) where Comtrade had not published or the call did not land. Missing years are absent rows,
  never zeros.
- **2026 trade data is not yet available** at all, so there is no export read on the Q3 window
  itself. The Q3 inference above rests on policy dates and Deere's own disclosures, not on
  observed 2026 trade flows.
- **Fiscal/calendar mismatch.** Deere's fiscal year ends late October; export data is calendar.
  The annual correlations align FY to the calendar year it mostly overlaps, a ~2 month offset.
  This alone justifies scepticism about the precise r values.
- **Plant-to-market assignment is not disclosed.** Deere never publishes which plant serves which
  market. The mapping in section 2 is inferred from the 10-K's "produce close to the markets"
  language plus the factory country list — it is directionally sound and specifically unproven.

### Sample sizes, stated plainly

Every correlation here has **n between 4 and 9**. None would survive a significance test worth
the name. They are reported because the *pattern across them* (Canada strong, rest-of-world weak)
matches an independently-known structural fact, not because any single coefficient is reliable.

---

## 7. How to refresh (durable tracker)

Two scripts, both in `scripts/data/`:

```bash
# 1. Fetch. Respects the Comtrade hourly quota; caches every response on disk so
#    re-runs are free. --only {annual,monthly,foreign} spends a quota window deliberately.
python3 de_fetch_comtrade_machinery.py --cache ./ctcache --out ./comtrade_raw.jsonl \
    --start-year 2012 --end-year 2026 --only monthly --workers 3 --min-interval 1.1

# 2. Build the CSV and re-run the correlations.
python3 de_build_exports_trade.py --comtrade ./comtrade_raw.jsonl \
    --partners ./partnerAreas.json --corpus-rows ./de_exports_trade_corpus_rows.csv \
    --geo-matrix ../../data/deere/de_geo_matrix.csv \
    --out ../../data/deere/footprint/exports_trade.csv --diag ./corr_diag.txt
```

Operational notes learned the hard way:

- The public tier returns **HTTP 429** under burst and **HTTP 403 "Out of call volume quota"**
  when the hourly budget is gone. **A rejected 429 still spends quota**, so aggressive retrying is
  self-defeating: pace requests with `--min-interval` instead of racing. `Retry-After` on the 403
  tells you exactly when to resume.
- Exponential backoff is wrong here. The 429 window clears in about a second; exponential backoff
  turns that into minutes of idle waiting and cost a ~4x slowdown before it was fixed.
- Getting a **Census API key** (free, `api.census.gov/data/key_signup.html`) would remove all of
  this: the Census timeseries endpoint returns many months and all destinations in a single call
  and is the better long-run source. It was unavailable in this run.

Priorities for the next refresh, in order:

1. Monthly 8433/8701/8429 for 2019–2026 → run the quarterly correlation properly (n≈23).
2. HS6 breakout of 8701.91–8701.95 to de-contaminate the tractor series.
3. Brazil and India reporter flows.
4. After 2026 trade data publishes, check whether the Q3 policy changes show up in observed flows.

### Sources

- UN Comtrade public preview API — <https://comtradeapi.un.org>
- Deere filings corpus, `challenge/offline-data/deere/filings/` (10-Ks FY2015–FY2025, 10-Qs
  through Q2 FY2026)
- [NDSU ARPC, temporary tariff relief for agricultural machinery](https://www.arpc-ndsu.com/post/temporary-tariff-relief-for-agricultural-machinery)
- [White & Case, Section 122 tariff](https://www.whitecase.com/insight-alert/trump-administration-imposes-10-section-122-tariff-plan-replace-ieepa-tariffs)
- [Miller Nash, IEEPA and Section 122 struck down](https://www.millernash.com/firm-news/news/tariffs-in-flux-ieepa-and-section-122-struck-down-section-232-duties-expand)
- [Skadden, tariff refund mechanism](https://www.skadden.com/insights/publications/2026/03/tariff-refund-mechanism-takes-shape)
- [Cato, IEEPA refunds update](https://www.cato.org/blog/ieepa-refunds-update-good-progress-still-ways-go)

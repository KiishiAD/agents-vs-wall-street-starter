---
name: company-profile
description: Build lightweight company profiles as structured JSON.
version: 0.1.0
author: Kaylan, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Finance, Company-Research, Forecasting, JSON]
    related_skills: []
---

# Company Profile Skill

## Mission

Build a lightweight, company-specific profile that explains how a company operates, reports, and is economically influenced. The profile is an orientation layer for a later worker that will define metric-specific forecasting signals.

Return one machine-readable JSON object. Make the profile specific enough to distinguish the company and its industry, but stop before detailed evidence extraction, signal selection, modelling, scenarios, or forecasting.

## Core principles

1. **Company-specific, not boilerplate.** Include only information that materially improves understanding of this company.
2. **Structured, not rigid.** Populate a stable common core and use flexible arrays for industry- and company-specific concepts.
3. **Lightweight by default.** Use the smallest authoritative source set that can satisfy the profile contract.
4. **Metric-aware, not metric-led.** Optional target metrics may change emphasis, but they must not turn profile construction into signal research.
5. **Repository first.** Prefer the supplied historical corpus, then use public research only for a material unresolved gap.
6. **Evidence-grounded.** Inspect every source recorded in the source log. Never treat a search result or snippet as a reviewed source.
7. **Explicit uncertainty.** Use `null`, empty arrays, and gap records rather than inventing missing facts.
8. **JSON only.** The final response must contain valid JSON with no Markdown fence, preamble, commentary, or trailing text.

## Boundaries

This skill must not:

- select, score, weight, or combine forecasting signals;
- collect detailed evidence for potential signals;
- extract long historical financial series;
- calculate forecasts, scenarios, valuations, or price targets;
- build detailed segment, margin, EPS, or accounting models;
- perform exhaustive competitor, macroeconomic, political, or regulatory research;
- write to a workbook or submission template;
- provide investment recommendations;
- fill fields with generic risk boilerplate merely for completeness;
- present assumptions, interpretations, or unsupported search snippets as reported facts.

The profile should explain **what may matter and where later workers may need to look**. It should not determine **what the final signals are or what they imply for the forecast**.

## Input contract

### Required inputs

```json
{
  "company": {
    "name": "Example Company",
    "ticker": "EXM"
  },
  "as_of_date": "2026-08-16"
}
```

Required rules:

- `company.name` must be non-empty.
- `company.ticker` should be supplied when available. If name or ticker is ambiguous, require an exchange, jurisdiction, or other reliable identifier.
- `as_of_date` must be an ISO `YYYY-MM-DD` date and acts as the default research cutoff.
- Do not use information published after the effective research cutoff.

### Optional inputs

```json
{
  "company": {
    "name": "Example Company",
    "ticker": "EXM",
    "exchange": "LSE",
    "jurisdiction": "United Kingdom"
  },
  "as_of_date": "2026-08-16",
  "research_cutoff": "2026-08-14",
  "target_period": "FY2026",
  "target_metrics": [
    {
      "label": "Net fees",
      "units": "GBPm"
    }
  ],
  "source_policy": {
    "repository_first": true,
    "public_research_allowed": true
  }
}
```

Defaults:

- `research_cutoff` defaults to `as_of_date`.
- `target_period` defaults to `null`.
- `target_metrics` defaults to `[]`.
- `source_policy.repository_first` defaults to `true`.
- `source_policy.public_research_allowed` defaults to `true`.
- The skill must work when no target metrics are supplied.

### Input failure behaviour

Return `status: "error"` rather than guessing when:

- the company cannot be identified unambiguously;
- the required company name or cutoff is missing;
- the cutoff is invalid;
- supplied identifiers refer to conflicting entities.

Use an error such as:

```json
{
  "code": "AMBIGUOUS_COMPANY",
  "message": "The supplied identity matches multiple public companies.",
  "required_information": ["ticker", "exchange"]
}
```

## Metric-specific adaptation

Treat target metrics as relevance hints. First construct the general company profile, then decide whether a metric warrants additional emphasis.

### Generic metrics

Typical characteristics:

- company-wide standard financial-statement measure;
- not restricted to a segment, geography, customer type, or operational definition;
- broadly driven by the entire company.

Examples include total revenue, total net income, and total diluted EPS.

Behaviour:

- do not open an additional source by default;
- do not broaden research;
- rely on the general profile;
- add either no metric lens or a minimal lens explaining why no special treatment is needed.

### Moderately specific metrics

Typical characteristics:

- company-defined or adjusted measure;
- operational KPI;
- measure with a non-obvious definition or accounting basis;
- measure whose meaning depends on the company's business model.

Examples include adjusted gross margin, comparable sales, and net fees.

Behaviour:

- search the selected core sources for the exact term and close variants;
- establish the company definition, scope, basis, units, and reporting frequency where available;
- identify only the business areas required to understand the metric;
- do not automatically open an additional source.

### Highly specific metrics

Typical characteristics:

- limited to a named segment or geography;
- company-defined operating measure with narrow scope;
- dependent on a particular channel, product, customer group, or accounting convention.

Examples include segment operating profit and regional operating KPIs.

Behaviour:

- search the core sources first;
- permit one additional official source if the definition or scope remains materially unresolved;
- add stronger emphasis to relevant segment, geography, reporting, and operating-model context;
- stop before historical extraction, signal selection, or modelling.

### Metric lens constraints

A metric lens may contain only:

- supplied metric label;
- specificity and the reason for that classification;
- company definition where available;
- scope, units, accounting basis, and reporting frequency;
- relevant business areas;
- additional profile emphasis;
- unresolved definition questions.

It must not contain:

- candidate signal scores or weights;
- detailed evidence records;
- historical values;
- forecast assumptions;
- scenarios or forecasts.

## Research policy

### Source hierarchy

Prefer sources in this order:

1. latest annual report or equivalent authoritative filing;
2. latest quarterly, half-year, or full-year results filing;
3. filed earnings release or official trading update;
4. official investor presentation;
5. earnings-call prepared remarks;
6. earnings-call Q&A;
7. other official company, regulator, or exchange material;
8. credible public secondary source.

Never cite or rely on a search snippet as if the underlying source was reviewed.

### Repository-first discovery

When a supplied corpus contains a company index, inspect that index before searching individual documents. Use document metadata—publication date, type, reporting period, and title—to shortlist sources.

Do not select documents merely because they are newest. Exclude by default:

- voting-rights notices;
- routine director or shareholder transaction notices;
- daily buyback logs;
- proxy voting materials;
- AGM voting results;
- duplicate copies of the same disclosure;
- minor administrative announcements;
- conference appearances that add no material company context.

### Default source set

Select no more than three core repository documents:

1. **Latest annual report:** stable business model, products, customers, segments, geographies, fiscal context, accounting, and structural exposures.
2. **Latest results release or trading update:** current structure, guidance practices, business changes, and current conditions.
3. **Latest useful earnings call or investor presentation:** management framing, operational drivers, cyclicality, seasonality, and company-specific concepts.

Permit one optional repository document only when:

- a highly specific metric remains undefined;
- material segment or geographic scope remains unclear;
- a major acquisition, disposal, or reorganization makes the annual report stale;
- an essential reporting convention cannot otherwise be established.

A generic metric must not, by itself, trigger an additional source.

### Public research

Public research is a fallback, not the default expansion path.

Use it only when:

- identity cannot otherwise be resolved;
- a material corporate change occurred after the latest useful repository source but before the cutoff;
- a required profile field remains materially unresolved;
- a highly specific metric needs an official definition unavailable in the corpus;
- a central external exposure cannot be understood from company materials.

Limits:

- use no public sources by default;
- use at most two public sources;
- prefer official company, regulator, or exchange sources;
- perform one targeted public-research pass;
- record the reviewed page URL, not a search-results URL;
- do not start broad industry or macroeconomic research.

### Lightweight research budget

Default ceilings:

| Resource | Limit |
|---|---:|
| Core repository documents | 3 |
| Optional repository document | 1 |
| Public sources | 0 by default; maximum 2 |
| Targeted corpus searches | Approximately 6–10 |
| Gap-resolution passes | 1 |
| Extracted source material | Approximately 12,000–18,000 tokens |
| Final JSON | Approximately 2,000–3,500 tokens |
| Source-log entries | Usually 3–6 |
| Target runtime | Approximately 8–12 minutes |

These are ceilings, not targets. Finish earlier when the contract is already satisfied.

## Materiality test

Include an item only if it materially helps answer at least one of these questions:

1. How does the company generate revenue or earnings?
2. How is the company operationally organized?
3. How does it define and report financial performance?
4. What causes its business economics to vary?
5. What company-specific concept may matter to later signal discovery?
6. What material external exposure shapes the business?
7. What context is necessary to understand a supplied specific metric?

Exclude:

- generic risk language with no clear company connection;
- exhaustive product, legal-entity, or country lists;
- immaterial subsidiaries or markets;
- detailed executive biographies;
- governance details unrelated to company operation;
- detailed historical figures not needed for orientation;
- generic macroeconomic commentary without a clear transmission mechanism;
- unsupported market-share claims;
- speculative signal ideas.

## Procedure

### Step 1: Validate and normalize the request

- Validate required inputs.
- Normalize obvious company-name and ticker formatting without changing the entity.
- Resolve identity using the supplied exchange or jurisdiction where necessary.
- Set the effective research cutoff.
- Preserve the original target metric labels and units.

Completion criterion: one company and one cutoff are unambiguous, or return `status: "error"`.

### Step 2: Classify target-metric specificity

For each supplied metric, classify it as `generic`, `moderate`, or `high`. Record a concise reason based on scope, company-specific terminology, accounting basis, segment/geographic restriction, and reporting practice.

Do not classify a metric as specific merely because its label is unfamiliar. Verify whether the company defines it specially.

Completion criterion: every supplied metric has a justified classification, even if a generic metric ultimately receives no lens.

### Step 3: Build a source plan from metadata

- Inspect the company index or equivalent source inventory.
- Identify the latest useful annual report before the cutoff.
- Identify the latest useful results release or trading update before the cutoff.
- Identify the latest useful call or presentation before the cutoff.
- Remove duplicate or administratively irrelevant candidates.
- Add an optional fourth document only if permitted by the gap or metric rules.

Completion criterion: the smallest defensible source set has been selected before substantive extraction begins.

### Step 4: Extract only orientation-level information

Search selected documents for:

- business model, products, services, customers, channels, and end markets;
- segments, geographies, and material operating footprint;
- fiscal calendar, reporting currency, accounting basis, adjusted measures, and company terminology;
- broad revenue, cost, margin, earnings, capital-intensity, and working-capital drivers;
- cyclicality, seasonality, and timing factors;
- guidance cadence, metrics, format, and characteristics;
- material industry, macroeconomic, political, geographic, regulatory, currency, commodity, and technology exposures;
- exact supplied metric terms when moderate or highly specific.

Do not extract full documents or detailed historical series. Capture concise facts and relationships sufficient to populate the JSON contract.

Completion criterion: each required section has been considered and is either supported, explicitly unknown, or not materially applicable.

### Step 5: Apply the materiality and company-specificity filter

For every proposed item:

- confirm it is supported by an inspected source;
- confirm it materially improves company orientation;
- remove generic statements that could describe most companies;
- consolidate duplicates;
- retain only the principal products, customers, segments, geographies, drivers, and exposures;
- move unresolved material questions to `uncertainties_and_gaps`.

Completion criterion: the retained content is recognizably specific to the company and contains no filler added solely to populate fields.

### Step 6: Resolve material gaps once

Run one bounded follow-up pass only when a missing item would materially impair the profile or a highly specific metric lens.

- Search the selected corpus more narrowly first.
- Open the optional fourth repository source if justified.
- Use at most two public sources if the repository cannot resolve the gap and public research is allowed.
- Stop after the single follow-up pass.

Completion criterion: the gap is resolved, or it is explicitly recorded without further research recursion.

### Step 7: Reconcile conflicts and changing definitions

When sources disagree:

1. compare publication dates and reporting periods;
2. distinguish current structure from historical structure;
3. distinguish GAAP from adjusted measures;
4. distinguish different segment, geographic, and customer definitions;
5. prefer formal filings for accounting definitions;
6. prefer newer official materials for current organization and guidance practice;
7. record unresolved conflicts in `uncertainties_and_gaps`.

Never silently combine inconsistent definitions.

Completion criterion: every material conflict is either resolved transparently or recorded as unresolved.

### Step 8: Construct the JSON profile

Populate the exact top-level contract below. Keep all top-level keys present. Use `null` for an unknown scalar and `[]` for no supported array items. Add a gap record when missing information is material.

Completion criterion: the output conforms to the contract, contains no unsupported facts, and remains within the lightweight output budget.

### Step 9: Determine status

Set:

- `complete` when the lightweight contract is materially satisfied;
- `partial` when the profile is useful but a material field or definition remains unresolved after the bounded follow-up pass;
- `error` when required inputs or company identity cannot be resolved.

Completeness does not require every optional array to contain an item. It requires every section to have been considered and handled honestly.

### Step 10: Verify and return

Run the verification checklist at the end of this skill. Then return the JSON object only.

## Output contract

Return all of these top-level keys in this order:

```json
{
  "schema_version": "0.1.0",
  "status": "complete",
  "profile_metadata": {
    "as_of_date": "2026-08-16",
    "research_cutoff": "2026-08-16",
    "profile_depth": "lightweight",
    "target_period": null,
    "target_metrics_supplied": [],
    "source_policy": "repository_first_public_allowed"
  },
  "company_identity": {
    "legal_name": null,
    "common_name": null,
    "ticker": null,
    "exchange": null,
    "jurisdiction": null,
    "headquarters": null,
    "reporting_currency": null,
    "industry": null,
    "company_description": null
  },
  "business_model": {
    "summary": null,
    "revenue_model": [],
    "products_and_services": [],
    "customer_groups": [],
    "distribution_channels": []
  },
  "operating_structure": {
    "segments": [],
    "geographies": [],
    "operating_footprint": []
  },
  "reporting_context": {
    "fiscal_year_end": null,
    "reporting_frequency": null,
    "accounting_standard": null,
    "reporting_currency": null,
    "fiscal_calendar_notes": [],
    "important_accounting_conventions": [],
    "company_defined_terms": [],
    "adjusted_measures_used": []
  },
  "financial_drivers": {
    "revenue_drivers": [],
    "cost_drivers": [],
    "margin_drivers": [],
    "earnings_drivers": [],
    "capital_intensity": "unknown",
    "working_capital_characteristics": []
  },
  "cyclicality_and_seasonality": {
    "cyclicality": null,
    "cycle_sensitivity": "unknown",
    "seasonal_patterns": [],
    "important_timing_factors": []
  },
  "guidance_practices": {
    "provides_guidance": null,
    "usual_cadence": null,
    "metrics_commonly_guided": [],
    "guidance_format": [],
    "guidance_characteristics": []
  },
  "external_exposures": [],
  "metric_lenses": [],
  "company_specific_factors": [],
  "sources": [],
  "uncertainties_and_gaps": [],
  "errors": []
}
```

## Nested object contracts

### Target metric input

```json
{
  "label": "Revenue",
  "units": "USDm"
}
```

### Product or service

```json
{
  "name": "Product or service category",
  "description": "Concise description",
  "importance": "primary"
}
```

Allowed `importance`: `primary`, `secondary`, `emerging`, `unknown`.

### Customer group

```json
{
  "name": "Customer group",
  "description": "Who buys and why"
}
```

### Segment

```json
{
  "name": "Reported segment",
  "description": "What the segment contains",
  "materiality": "primary"
}
```

### Geography

```json
{
  "name": "Region",
  "role": "Major market or operating region",
  "materiality": "primary"
}
```

Allowed `materiality`: `high`, `moderate`, `low`, `primary`, `secondary`, `unknown` as appropriate to the object. Use one consistent vocabulary within each array.

### Company-defined term

```json
{
  "term": "Comparable sales",
  "definition": "Company definition where available"
}
```

### External exposure

```json
{
  "category": "macroeconomic",
  "exposure": "Housing-market activity",
  "description": "How and why the company is exposed",
  "materiality": "high"
}
```

Preferred `category`: `industry`, `macroeconomic`, `political`, `geographic`, `regulatory`, `currency`, `commodity`, `technology`, or `other`.

Allowed `materiality`: `high`, `moderate`, `low`, `unknown`.

### Metric lens

```json
{
  "input_metric": "Segment operating profit",
  "specificity": "high",
  "specificity_reason": "The metric is restricted to a named operating segment.",
  "company_definition": null,
  "scope": "Named operating segment",
  "accounting_basis": null,
  "units": "USDm",
  "reporting_frequency": "quarterly",
  "relevant_business_areas": [],
  "additional_profile_emphasis": [],
  "unresolved_questions": []
}
```

Allowed `specificity`: `generic`, `moderate`, `high`.

A generic supplied metric may be omitted from `metric_lenses` when no additional company-specific context is necessary; it must still appear in `profile_metadata.target_metrics_supplied`.

### Company-specific factor

```json
{
  "name": "Company-specific concept",
  "category": "operating_model",
  "description": "What makes the concept distinctive",
  "potential_relevance": "Why a later signal worker may need to understand it",
  "materiality": "high"
}
```

Keep `category` flexible. Allowed `materiality`: `high`, `moderate`, `low`, `unknown`.

`potential_relevance` must remain a broad explanatory relationship. It must not nominate, score, or quantify a forecast signal.

### Source log entry

```json
{
  "source_id": "SRC-001",
  "title": "Annual Report 2025",
  "source_type": "annual_report",
  "publisher": "Example Company",
  "publication_date": "2026-03-01",
  "reporting_period": "FY2025",
  "location": "repository path or reviewed public URL",
  "used_for": [
    "business_model",
    "operating_structure",
    "reporting_context"
  ]
}
```

Requirements:

- assign unique IDs in order: `SRC-001`, `SRC-002`, and so on;
- include only inspected sources;
- use a repository-relative path for corpus sources;
- use the reviewed page URL for public sources;
- use `used_for` to name the top-level sections supported;
- do not list duplicate copies of the same disclosure unless they materially differ.

### Uncertainty or gap

```json
{
  "topic": "Geographic revenue definition",
  "issue": "The reviewed sources do not establish whether geography is based on billing location or end demand.",
  "importance": "moderate",
  "suggested_follow_up": "Check geographic footnotes if this becomes relevant to a selected signal."
}
```

Allowed `importance`: `high`, `moderate`, `low`.

### Error

```json
{
  "code": "INVALID_INPUT",
  "message": "Required input is missing or invalid.",
  "required_information": []
}
```

## Writing and compression rules

- Prefer compact arrays of distinct items over long narrative paragraphs.
- Keep the company description to one or two sentences.
- Keep each driver or exposure concise and causal: state how it relates to the company.
- Include principal products, customers, segments, and geographies, not exhaustive lists.
- Avoid repeating the same concept in several sections. Put it in the most natural section and reference it indirectly elsewhere only when necessary.
- Do not include detailed percentages or historical figures unless one is indispensable to understanding company structure or terminology.
- Preserve company-defined terminology rather than replacing it with generic financial language.
- Distinguish geography by customer location, billing location, destination, or operations when the source does so.
- Distinguish reported and adjusted measures.
- Do not infer the absence of an exposure merely because selected sources do not discuss it.

## Stop conditions

Stop researching when:

- identity and cutoff are resolved;
- business model and revenue model are understandable;
- principal products/services and customer groups are captured;
- material segments and geographies are captured or explicitly unavailable;
- fiscal and reporting context is established;
- broad financial drivers are captured;
- material cyclicality and seasonality are described;
- guidance practice is described or marked unknown;
- material external exposures are captured;
- supplied metrics have received proportional treatment;
- sources are logged;
- material unresolved questions are recorded;
- further research would mainly add detail rather than alter the profile's usefulness.

Do not continue merely because research budget remains.

## Final verification checklist

Before returning the output, verify:

### Input and identity

- [ ] Company identity is unambiguous.
- [ ] The effective cutoff is explicit.
- [ ] Every source was published on or before the cutoff.
- [ ] Original target metric labels and units are preserved.

### Research discipline

- [ ] Repository materials were considered first.
- [ ] The source set is authoritative, relevant, and non-duplicative.
- [ ] No more than three core and one optional repository document were used without an explicit exception.
- [ ] Public research was used only for a material gap and stayed within the two-source limit.
- [ ] Every source-log entry was actually inspected and used.

### Profile quality

- [ ] Content is recognizably specific to the company and industry.
- [ ] Generic boilerplate and immaterial detail were removed.
- [ ] Stable facts and current context were not confused.
- [ ] Reporting periods, currencies, scopes, and accounting bases are not mixed.
- [ ] Company-defined terms are preserved.
- [ ] Unknown or conflicting information is explicit.
- [ ] No unsupported precise claim, figure, or market-share statement was added.

### Metric proportionality

- [ ] Each metric was classified using definition and scope, not unfamiliarity alone.
- [ ] Generic metrics did not trigger unnecessary research.
- [ ] Specific metrics received only the additional context needed to understand them.
- [ ] No metric lens contains signals, weights, historical extraction, assumptions, or forecasts.

### Output integrity

- [ ] Output is valid JSON.
- [ ] All required top-level keys are present in the required order.
- [ ] `schema_version` is `0.1.0`.
- [ ] `status` is `complete`, `partial`, or `error`.
- [ ] Unknown scalar values are `null`, not fabricated text.
- [ ] Unsupported arrays are empty rather than padded.
- [ ] Source IDs are unique.
- [ ] Final JSON is approximately 2,000–3,500 tokens unless a justified exception is recorded.
- [ ] There is no Markdown fence, preamble, explanation, or text after the JSON.

If any check fails, correct the profile before returning it. If the failure cannot be corrected within the bounded research policy, return `partial` with a gap or `error` with a structured error record.

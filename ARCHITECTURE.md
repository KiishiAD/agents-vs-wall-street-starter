# How the signal agent works

The signal agent turns source-backed evidence into a forecast that can be checked later.

It uses models to find useful passages and propose structured claims. It uses deterministic code to decide whether evidence is valid, do the arithmetic, and create the forecast receipt. A model never gets to invent a source, choose a numerical weight, or write a workbook value directly.

## The flow

```text
Company and metric definitions
        ↓
Find and freeze sources
        ↓
Build a company profile
        ↓
Create a signal map for each metric
        ↓
Collect evidence only for approved signals
        ↓
Validate, review and combine accepted observations
        ↓
Base forecast, scenarios and provenance receipt
```

## 1. Find and freeze sources

`npm run research:profiles` runs research for the four companies in parallel. It searches nine topics: business model, products, segments, fiscal calendar, revenue and cost drivers, accounting, guidance, seasonality, and external exposures.

Tavily search results are only leads. The agent extracts selected pages and freezes their content locally. Each frozen source records its URL, title, publisher, Tavily request ID, publication time, local file path, and SHA-256 hash.

Sources published after the information cutoff, or sources with no publication date, are kept for audit but cannot affect a forecast.

## 2. Build a company profile

The profile is a short, source-backed description of the company. Every claim must cite a frozen source and include an exact quotation that exists in that source.

The profile is context for the next step. It does not put numbers into a forecast by itself.

## 3. Create a signal map

Each forecast metric needs three to seven material signals and exactly one anchor.

- An **anchor** is the starting point, usually direct management guidance.
- A **driver** is a quantified fact that can change the forecast through a declared formula.
- A **modifier** is useful qualitative context. It explains the range but never gets a made-up numerical weight.
- A **scenario trigger** is a conditional risk. It changes only a stated upside or downside scenario, not the base forecast.
- A **constraint** is an accounting check, such as an identity that must hold.

Every signal declares the metric, period, units, accounting basis, evidence needed, formula, freshness rule, and correlation group. The correlation group stops closely related evidence from being counted twice.

## 4. Collect only approved evidence

After the signal map passes validation, `npm run research:signals` searches only for the declared evidence requirements. Broad news or model memory cannot quietly become a forecast input.

An observation is accepted only when its source is admissible, its exact quote matches the frozen source, and its period, units, and accounting basis match the target metric. Forecast numbers are kept as decimal strings until the compiler uses `Decimal` arithmetic.

## 5. Review and validate

Before handoff, deterministic checks reject bad evidence: missing or post-cutoff dates, changed source files, unsupported quotes, wrong units, wrong periods, wrong accounting basis, duplicate drivers, arbitrary weights, and invalid decimal values.

An independent no-web reviewer receives only the frozen source manifest, supplied excerpts, cutoff, audit record, and proposed claims. It can flag unsupported claims or suspected look-ahead. An error finding—or an unavailable review—blocks `forecast_input.v2`.

The reviewer cannot prove what a model learned in training. It can only check whether the proposed output can be reconstructed from the supplied evidence.

## 6. Make the forecast

The compiler uses a visible calculation:

```text
anchor
+ accepted quantitative driver adjustments
= base forecast
```

Modifiers remain qualitative. Scenario triggers produce explicit conditional scenarios. Constraints are checked after calculation.

If evidence is missing or invalid, the signal is rejected and the declared anchor or baseline stays unchanged.

The compact `signal_handoff.v1` moves verified facts, guidance, qualitative
signals, and frozen sources into the forecasting engine. The engine uses only a
declared Decimal formula: direct guidance, an annual-to-quarter bridge using
sourced historical seasonality, a weighted percentage bridge, or an explicit
component sum. It writes a workbook-facing value and a separate receipt. A
qualitative signal never changes the base value, and unresolved evidence blocks
the affected metric.

## What is saved

Every forecast-driving value keeps this chain:

```text
source URL + frozen file + SHA-256
        ↓
exact quotation
        ↓
typed observation
        ↓
approved signal definition
        ↓
validation decision
        ↓
Decimal formula and forecast result
```

This makes each accepted adjustment replayable and each rejected adjustment explainable.

## Limits

The system can still miss relevant evidence or make an inaccurate forecast. Its guarantee is narrower: invalid or unverifiable evidence cannot silently move a number, and accepted evidence has a traceable path into the calculation.

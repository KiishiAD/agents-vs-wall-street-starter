# Deterministic forecasting engine

The forecasting engine consumes a compact `signal_handoff.v1` file and produces:

- `company_forecast.v1`: the three numeric values used by the workbook writer; and
- `forecast_receipt.v1`: the source, formula, range, and accepted qualitative context for every value.

Run it with:

```bash
python3 -m forecasting.cli \
  --company HD \
  --input handoffs/HD.json \
  --output forecasts/HD.json \
  --receipt receipts/HD.json
```

For a complete all-company, workbook-producing run, place `HD.json`, `ADI.json`,
`HAS.json`, and `DE.json` in `handoffs/` and run:

```bash
python3 -m pipeline.run --handoff-dir handoffs
```

## Input contract

The compact signal output remains the centre of the input: `metrics`,
`assumptionSignals`, `sources`, and `unresolved`. For a number to drive a
forecast, enrich its source record with `publisher`, `title`, `documentType`,
`frozenPath`, and `sha256`; enrich the fact or guidance with `exactQuote` and
`locator`. The engine verifies the file hash, publication date, cutoff, and
quotation before using it. The handoff must also carry `review: {"status":
"passed"}` from the evidence-bound look-ahead review. A date-only publication
record is rejected when it falls on the information-cutoff date, because its
publication time is uncertain.

Each metric includes a declarative `forecastPlan`. Supported methods are:

- `direct_guidance`: midpoint of target-period management guidance;
- `annual_growth_bridge`: apply annual growth guidance to a sourced prior-year
  total, subtract sourced reported YTD, then allocate the sourced remaining
  amount using prior-period line-item seasonality;
- `weighted_rate_bridge`: derive a remaining percentage rate from annual
  guidance and sourced historical sales weights; and
- `component_sum`: add explicitly sourced components with matching units.

All arithmetic is `Decimal`. Historical weights are derived from frozen
historical facts; the handoff cannot provide an arbitrary numerical weight.
Qualitative signals are copied to the receipt but cannot move the base case.
Any unresolved unscoped issue, or issue that names a target metric, blocks that
metric rather than silently producing a forecast.

`forecasting/model_catalog.py` documents the required supporting line items and
allowed methods for all twelve challenge targets. It contains no values and is
not a substitute for source-backed handoff evidence.

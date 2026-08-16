# Evidence-to-forecast compiler

> Central development reference — updated 16 August 2026. This document describes
> both the implemented system and the remaining integration work. Update it whenever
> an interface, owner, final command or artifact changes.

## Current end-to-end architecture

The system has two complementary layers:

1. a bounded multi-agent research layer that discovers, extracts and reconciles
   financial-report evidence; and
2. a deterministic evidence-to-forecast compiler that converts approved signals
   into exactly three forecast figures per company.

One reusable company pipeline is instantiated for `HAS`, `HD`, `ADI` and `DE`.
The four company lanes run concurrently, while stages inside each lane remain
ordered. Each research orchestrator launches five independent workers, so a full
live run can have up to twenty research requests active at once.

```text
                         pipeline/run.py
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
          HAS lane          HD lane          ADI lane          DE lane
             │                 │                 │                 │
       5 research workers  5 workers         5 workers         5 workers
       frozen corpus + current official web sources in every lane
             │                 │                 │                 │
       reconcile reports, facts, observations, conflicts and confidence
             │                 │                 │                 │
       forecast_inputs/HAS.json ... forecast_inputs/DE.json
             │                 │                 │                 │
       company profile + metric signal map + typed observations
             │                 │                 │                 │
       deterministic anchor + approved drivers + scenarios + challenge
             └─────────────────┴─────────────────┴─────────────────┘
                               │
                    evaluation/forecasts.json
                     exactly 3 × 4 figures
                               │
             validate units, scale, sign and coherence
                               │
              preserve templates and write 4 workbooks
                               │
                     npm run check:submission
```

### Implementation status and ownership

| Area | State | Primary files | Integration expectation |
| --- | --- | --- | --- |
| Parallel company orchestration | Implemented | `pipeline/run.py` | Four isolated lanes; `--parallel-companies 1..4` |
| Financial-report research | Implemented | `signal_agent/` | Five independent strategies per company |
| Offline + web retrieval | Implemented | `signal_agent/offline_corpus.py`, `providers.py` | Frozen excerpts are leads/evidence; current facts are verified on official web sources |
| Reconciliation and confidence | Implemented | `signal_agent/reconcile.py` | Produces immutable signal runs and `latest.json` |
| Forecast handoff | Implemented | `signal_agent/forecast_input.py` | Produces `forecast_input.v1` per company |
| Deterministic forecast compiler | Implemented core; integration in progress | `forecasting/` | Must consume the handoff and emit three figures per company |
| Forecast aggregation | Existing final format; bridge required | `evaluation/forecasts.json` | Adapter must assemble all four company results |
| Forecast validation | Implemented | `scripts/validate_forecasts.py` | Checks all 12 figures before workbook writing |
| Workbook writing | Implemented | `scripts/write_workbooks.py` | Writes only the three required cells in each template |
| Final submission command | Implemented for existing forecast JSON | `scripts/run.sh`, `npm run forecast` | Research-to-compiler integration must be connected before this is fully autonomous |
| Architecture visual | Implemented; keep synchronized | `architecture/index.html` | Must describe the final command used at 17:15 |

### Active integration contract

The research layer writes:

```text
signals/<company>/financial_reports/latest.json
        ↓
forecast_inputs/<company>.json        schema: forecast_input.v1
```

The forecast adapter must consume one `forecast_input.v1`, construct or enrich the
company profile and signal observations, invoke the compiler, and produce exactly
three numeric forecasts. The existing final aggregation format is:

```json
{
  "HAS": {"Net fees": 904.0, "Pre-exceptional basic EPS": 6.2, "Pre-exceptional operating profit": 45.0},
  "HD": {},
  "ADI": {},
  "DE": {}
}
```

Metric names and units come exclusively from `challenge/companies.json`. Research
confidence describes evidence agreement and extraction quality; it is not a claim
of forecast accuracy.

The newer pipeline interface currently expects `forecasting.cli` and
`workbook_generator.cli`. The repository already has the compiler core and
`scripts/write_workbooks.py`, but those CLI adapters are not yet connected. Do not
maintain two competing forecast paths: either implement these thin adapters or
change `pipeline/run.py` once to call the agreed existing entry points.

## Architecture statement

The worker first builds a source-backed company profile, then creates a metric-specific signal map. Each signal defines what evidence is required, how it affects the metric and how it may enter the forecast. Reusable resolver tools collect and normalize those signals before deterministic code combines them into an auditable forecast.

The LLM may propose structured observations. It may not invent sources, choose arbitrary weights, perform forecast arithmetic or write submission values. A signal changes a forecast only when its evidence and declared transformation pass deterministic validation.

## Forecast compiler workflow

```text
1. Research and reconcile evidence       Signal research layer
             ↓
2. Build company profile                 Forecast/compiler team
             ↓
3. Define metric-specific signal map     Forecast/compiler team
             ↓
4. Resolve typed observations            Forecast/compiler team
             ↓
5. Measure and combine the signals       Forecast/compiler team
             ↓
6. Produce scenarios and forecast        Forecast/compiler team
             ↓
7. Challenge and validate                Independent challenger + deterministic scripts
```

### 1. Research and reconcile evidence

For each company, five workers independently search investor relations, regulators,
exchanges and direct official documents, with one sceptical cross-check worker.
Every worker also receives a bounded metric-relevant selection from the supplied
offline corpus. The reconciler groups equivalent report events and facts, records
conflicting values, and calculates document and extraction confidence. SQLite source
memory is scoped by company and signal type; WAL mode allows concurrent company runs.

### 2. Build the company profile

The JSON profile records the company's business model, products and customers, segments and geographies, fiscal calendar, revenue and cost drivers, accounting definitions, guidance style, cyclicality, seasonality, and material macroeconomic, political and industry exposures.

Profile claims are source-backed. Every claim cites one or more source IDs. Every source preserves its publisher, title, document type, publication time, URL, local corpus path and SHA-256 content hash.

### 3. Define the signal map

Each target metric gets approximately three to seven material signals. A signal must declare:

- what is measured;
- why it should affect the target metric;
- expected direction and target period;
- units and importance;
- resolver and required evidence;
- combination method;
- freshness requirement;
- correlation group, so related evidence is not double-counted.

Signals have one of five roles:

- `constraint`: an accounting identity or invariant that is enforced, never weighted;
- `anchor`: direct guidance or another defensible starting range;
- `driver`: a quantified effect applied through an explicit formula;
- `modifier`: qualitative evidence used to explain range selection, never assigned false precision;
- `scenario_trigger`: a conditional risk kept out of the base forecast unless the condition occurs.

Weights are forbidden unless the signal map identifies the backtest or historical analysis that justifies them.

### 4. Resolve the signals

Resolvers search only for approved signals and return typed observations. Every observation carries the source ID, exact quotation, publication time, target period, units and normalized value. The compiler verifies the quotation against the frozen source text and verifies the source hash before accepting it.

A reusable signal has three levels:

1. template, such as management guidance;
2. company-specific instance, such as ADI FY2026Q3 revenue guidance;
3. current evidence-backed observation.

### 5. Combine signals

The visible calculation is:

```text
anchor
+ approved quantitative driver adjustments
= base forecast
```

Modifiers are displayed beside the range but do not receive invented numerical weights. Scenario triggers create explicit conditional scenarios. Constraints are checked after calculation.

### 6. Produce scenarios

Every target has a base forecast and may have upside or downside scenarios. A scenario records the triggering condition, explicit adjustment, source evidence and formula. A proposed but untriggered event never silently changes the base forecast.

### 7. Challenge and validate

The challenger checks:

- omitted material signals;
- period, unit, currency and accounting-basis mismatches;
- stale or post-cutoff evidence;
- unsupported quotations or changed source content;
- duplicated or correlated drivers;
- illogical direction or transmission mechanism;
- coincident evidence presented as leading evidence;
- qualitative evidence given false numerical precision;
- revenue evidence incorrectly applied to margin or EPS;
- missing reconciliation constraints.

A failed signal is rejected with a reason. The forecast retains its declared baseline or anchor rather than inventing an adjustment.

## Provenance chain

Every forecast-driving value must preserve this chain:

```text
source URL + frozen file + SHA-256
        ↓
exact quotation + locator
        ↓
typed observation
        ↓
approved signal definition
        ↓
validation decision
        ↓
explicit Decimal formula
        ↓
forecast component and final value
```

Run artifacts are written as JSON next to the forecasts. Submission workbooks remain structurally unchanged except for the required value cells.

## First-version scope

Implemented now:

- strict JSON company profiles and signal maps;
- source hashes, URLs, exact quotations and cutoff checks;
- reusable management-guidance and explicit-driver resolvers;
- deterministic anchor-plus-driver combination using `Decimal`;
- qualitative modifiers and conditional scenarios without arbitrary weights;
- challenge checks for unsupported evidence, mismatches and double-counting;
- replayable JSON run receipts;
- an end-to-end ADI example using the supplied frozen SEC filing.

Deliberately excluded from the deterministic critical path:

- generic news sentiment;
- automatic supplier-network inference;
- arbitrary model-generated weights;
- unrestricted LLM arithmetic;
- a universal financial ontology;
- an unrestricted or self-modifying agent swarm. The bounded five-worker research
  panel is upstream of the deterministic compiler and cannot write forecast values.

## Commands used by developers

```bash
# Research and handoff only; currently implemented end to end
python3 -m pipeline.run --through inputs

# Reuse existing research while developing downstream stages
python3 -m pipeline.run --through inputs --skip-research

# Restrict development to one company
python3 -m pipeline.run --companies HAS --skip-research

# Existing final validation and workbook path for evaluation/forecasts.json
npm run forecast

# Tests for the research/reconciliation layer
npm run test:signals
```

`python3 -m pipeline.run` becomes the single autonomous final command after the two
CLI adapters described above are connected. Until then, `npm run forecast` starts
from the already-populated `evaluation/forecasts.json` and must not be described as
performing live research.

## Shared development rules

- Keep company-specific research targets in `signal_agent/config/companies.json`.
- Treat `challenge/companies.json` as authoritative for the twelve output metrics.
- Preserve provenance when translating `forecast_input.v1` into compiler observations.
- Never let research confidence directly become a forecast adjustment.
- Keep arithmetic and workbook writes deterministic.
- Do not commit API keys, `entry.json`, SQLite databases or generated signal artifacts.
- Keep the final accepted timestamped log as run evidence.
- Update this document and `architecture/index.html` whenever the actual final path changes.

## Guarantees and limits

The system does not guarantee that an LLM finds every economically relevant fact or that a forecast is accurate. It does guarantee that accepted inputs replay to the same output, rejected evidence cannot move a number, post-cutoff evidence is excluded, and every applied component has an inspectable source-to-formula receipt.

# Codex Prompt: Code Writer

You are writing code for Agri-AI.

Agri-AI is an agricultural supply planning tool for buyer-facing aggregators and regional produce operators.
Its job is to help operators decide what to grow, how much to commit, and when — before the season is locked.

Before writing anything, read:

- `AGENTS.md` — project rules, naming, and writing standards
- `docs/product/mvp_scope.md` — what to build and what to skip
- `docs/business/business_analysis.md` — the operator problem and pricing context
- `docs/pilot/indiana_pilot.md` — the real pilot structure and weekly output requirements

---

## What You Are Building

The MVP is a planning layer, not a platform.

It answers four questions for an aggregator operator:

1. Where does buyer demand exceed expected grower supply this season?
2. Where does expected supply exceed likely demand?
3. Which weeks carry the highest fill risk?
4. What should the operator do next?

The first working version can be a Python script, a CSV-in / report-out pipeline, or a simple local dashboard.
Technical complexity is not the goal. Operator decision quality is.

---

## Domain Model

Understand these terms before writing any logic:

- **Crop** — a normalized produce item (e.g. `tomato`, `butternut_squash`, `sweet_corn`). Always lowercase, underscore-separated.
- **Buyer** — a named institutional or wholesale customer (e.g. `IU_Health`, `Sysco_Indiana`).
- **Grower** — a farm supplying the aggregator. Has a name, a crop roster, and seasonal capacity per crop.
- **Week** — ISO week number within a season year (e.g. `2026-W22`). All time-series data uses this format.
- **Demand** — buyer order quantity for a crop in a given week, in pounds unless stated otherwise.
- **Capacity** — grower's expected harvestable quantity for a crop in a given week, in the same unit as demand.
- **Coverage ratio** — `total_capacity / total_demand` for a crop-week. Values below 1.0 indicate a shortage.
- **Shortage** — `demand - capacity` when coverage ratio < 1.0. Expressed in pounds and as a percentage of demand.
- **Overage** — `capacity - demand` when coverage ratio > 1.0. Expressed in pounds and as a percentage of capacity.
- **Risk flag** — a boolean indicator on any crop-week where coverage ratio falls below the configured threshold (default: 0.85).
- **Season** — a named calendar window, typically April–October for Midwest specialty crops.

---

## Input Data Specifications

### Order History CSV

```
buyer, crop_raw, quantity_lbs, week_iso, year
IU Health, Heirloom Tomato, 240, 22, 2025
IU Health, heirloom tomatoes, 180, 23, 2025
GrowLocal Hub, Butternut Squash, 500, 36, 2025
```

Expected columns:
- `buyer` — string, buyer name as provided
- `crop_raw` — string, raw crop name before normalization
- `quantity_lbs` — float, pounds ordered
- `week_iso` — int, ISO week number
- `year` — int, four-digit year

Missing values: skip rows with null `quantity_lbs` or null `crop_raw`. Log skipped rows.

Duplicates: if the same `buyer + crop_raw + week + year` appears twice, sum the quantities.

### Grower Capacity CSV

```
grower, crop_canonical, estimated_lbs, week_iso, year
Heartland Farm, tomato, 400, 22, 2025
Heartland Farm, tomato, 350, 23, 2025
Oak Ridge Growers, butternut_squash, 800, 36, 2025
```

Expected columns:
- `grower` — string
- `crop_canonical` — string, already normalized
- `estimated_lbs` — float
- `week_iso` — int
- `year` — int

Grower capacity is operator-provided and assumed to be correct. No validation needed beyond type checking.

### SKU Normalization Lookup Table

```
crop_raw, crop_canonical
Heirloom Tomato, tomato
heirloom tomatoes, tomato
Heirloom tomatos, tomato
Butternut Squash, butternut_squash
butternut, butternut_squash
Sweet Corn, sweet_corn
```

The lookup table is a CSV maintained manually by the operator.
If a `crop_raw` value has no match in the table, flag it as `UNRESOLVED` and do not silently drop it.
Output all unresolved SKUs to a separate file for the operator to review.

---

## Must-Have Features

Build these in order. Do not skip ahead.

### 1. Data Ingest

- read order history CSV
- read grower capacity CSV
- read SKU normalization table
- validate column presence and types
- log and skip malformed rows, do not crash

### 2. SKU Normalization

- join `order_history.crop_raw` to the lookup table
- assign `crop_canonical` to each order row
- collect unresolved SKUs into a separate output file: `unresolved_skus.csv`
- do not drop unresolved rows silently — flag them clearly

### 3. Demand Aggregation

- group normalized orders by `crop_canonical`, `week_iso`, `year`
- sum `quantity_lbs` per group
- output: `demand_by_crop_week` — a table of crop × week × total_demand_lbs

### 4. Supply Aggregation

- group grower capacity by `crop_canonical`, `week_iso`, `year`
- sum `estimated_lbs` per group
- output: `supply_by_crop_week` — a table of crop × week × total_supply_lbs

### 5. Gap Analysis

For each `crop_canonical × week_iso × year` present in demand:

```
coverage_ratio = total_supply_lbs / total_demand_lbs
shortage_lbs   = max(0, total_demand_lbs - total_supply_lbs)
overage_lbs    = max(0, total_supply_lbs - total_demand_lbs)
shortage_pct   = shortage_lbs / total_demand_lbs * 100
overage_pct    = overage_lbs / total_supply_lbs * 100  (0 if supply = 0)
```

If a crop has demand but no supply data at all, set `coverage_ratio = 0` and `shortage_lbs = total_demand_lbs`.

Output: `gap_analysis.csv` — one row per crop-week with all calculated fields.

### 6. Risk Flags

Apply a configurable threshold (default `COVERAGE_THRESHOLD = 0.85`):

```
risk_flag = True  if coverage_ratio < COVERAGE_THRESHOLD
risk_flag = False otherwise
```

Add `risk_flag` as a column to `gap_analysis.csv`.

Sort final output by: `risk_flag DESC`, `shortage_pct DESC`, `week_iso ASC`.

### 7. Weekly Planning Memo

Generate a plain-text file `weekly_memo.txt` formatted for operator reading.

Structure:

```
AGRI-AI WEEKLY PLANNING MEMO
Season: [year]  |  Generated: [date]

--- HIGH RISK THIS WEEK ---
[List crop-weeks where risk_flag = True, ordered by week]
  Week 22: tomato — 68% covered (shortage: 128 lbs)
  Week 24: sweet_corn — 71% covered (shortage: 340 lbs)

--- UPCOMING RISK (NEXT 4 WEEKS) ---
[List risk-flagged crop-weeks in the next 4 ISO weeks from today]

--- OVERAGES TO WATCH ---
[List crop-weeks where overage_pct > 20%, ordered by overage_pct DESC]
  Week 28: butternut_squash — 142% covered (overage: 620 lbs)

--- UNRESOLVED SKUS ---
[Count of unresolved SKUs. Instruct operator to review unresolved_skus.csv]

--- RECOMMENDED ACTIONS ---
[One line per high-risk crop, suggesting grower outreach or buyer conversation]
  tomato (Week 22): contact Heartland Farm to confirm planting commitment
  sweet_corn (Week 24): check with Oak Ridge Growers on capacity estimate
```

Recommendations are rule-generated, not AI-generated at this stage.
Use the pattern: if `shortage_pct > 30%`, recommend grower outreach. If `overage_pct > 25%`, recommend buyer conversation.

---

## Output Files

All outputs go to an `output/` directory:

| File | Contents |
|---|---|
| `gap_analysis.csv` | Full crop × week gap table with flags |
| `demand_by_crop_week.csv` | Aggregated demand |
| `supply_by_crop_week.csv` | Aggregated supply |
| `unresolved_skus.csv` | SKU names with no canonical match |
| `weekly_memo.txt` | Operator-facing planning memo |

---

## Project File Structure

```
agri-ai/
├── data/
│   ├── order_history.csv
│   ├── grower_capacity.csv
│   └── sku_lookup.csv
├── output/                  # generated, gitignored
├── src/
│   ├── ingest.py            # load and validate input files
│   ├── normalize.py         # SKU normalization logic
│   ├── aggregate.py         # demand and supply aggregation
│   ├── gap.py               # gap analysis and risk flagging
│   ├── memo.py              # weekly memo generation
│   └── main.py              # entry point, orchestrates the pipeline
├── tests/
│   ├── test_normalize.py
│   ├── test_aggregate.py
│   └── test_gap.py
├── config.py                # COVERAGE_THRESHOLD and other settings
└── requirements.txt
```

---

## Do Not Build Yet

- inventory management
- warehouse or fulfillment workflows
- route optimization
- buyer ordering portal or marketplace
- mobile app
- lending or financing tools
- general AI assistant or chat layer
- autonomous forecasting
- multi-user auth or login
- database backend (flat files are sufficient for MVP)

If a feature is not in the must-have list, do not build it without a new explicit instruction.

---

## AI vs Logic

Use rule-based logic for everything in the MVP:

- coverage ratios, shortage and overage calculations — deterministic math
- risk flags — configurable threshold comparison
- recommendation text — rule-based string generation

Use AI only when logic breaks down:

- SKU normalization: if fuzzy matching or an LLM call would resolve unresolved SKUs that a lookup table misses — acceptable in a second pass, not the first pass
- anomaly detection: once 2+ seasons of data exist
- note summarization: operator notes are unstructured — acceptable AI use when notes exist

Do not use a model where a formula or lookup does the same job.

---

## Error Handling

- do not crash on bad input — log the error and continue
- every skipped row must be logged with its reason
- if an entire input file is missing, exit with a clear error message and instructions
- do not silently produce incorrect output — surface data quality issues explicitly in the memo

---

## Code Standards

- readable over clever
- small, single-purpose functions — one job per function
- domain-named variables: `demand_by_week`, `grower_capacity`, `coverage_ratio`, `shortage_flag`
- short inline comment on any non-obvious logic
- no new dependencies without a clear reason
- no premature abstraction — build for the current feature set, not a future platform

---

## Testing Requirements

Write tests for:

- `normalize.py` — correct mapping, unresolved SKU detection
- `aggregate.py` — correct summing, handling of duplicates and missing weeks
- `gap.py` — correct coverage ratio, shortage and overage calculations, edge case where supply = 0

Use simple test fixtures (small CSV strings or dicts). No external test data files required for unit tests.

---

## Output Format for Each Task

When completing a code task, return:

### What Was Built
One short paragraph. What does the code do?

### How to Run It
Exact commands. No ambiguity.

### Assumptions
Data formats, environment, inputs assumed.

### What Is Not Handled Yet
Explicit list of known gaps or deferred edge cases.

### Next Step
One concrete follow-on task.

---

## Quality Check Before Submitting

1. Does this help an operator make a better planning decision?
2. Is the output readable by a non-engineer?
3. Does it stay within MVP scope?
4. Is AI actually needed here, or does logic do the job?
5. Does anything here belong in a later phase?
6. Are errors surfaced clearly, or are they swallowed silently?

If any answer is no or unclear, revise before submitting.

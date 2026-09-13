# ZAAD

> **Current system:** [`docs/zaad_full/CURRENT_SYSTEM.md`](docs/zaad_full/CURRENT_SYSTEM.md) — released optimizer stack (P0-P5, P4B V1),
> production runtime, validation chain and release procedure. The sections below predate it and are kept as history.

Repository: `radalzubi/harvestmind` (unchanged). Company/product: **ZAAD** —
[zaadsupply.com](https://zaadsupply.com).

**New inventory/resilience prototype:** start at
[docs/zaad_next/README.md](docs/zaad_next/README.md). Includes the isolated
`/zaad` workspace, current-source adapter, 3,000-row frozen synthetic sweep,
and retained failures. Verdict: **NEEDS FURTHER ENGINEERING**; not an
autonomous procurement system or real-operator validation.

## Existing supply-planning foundation

**Stochastic supply planning for perishable food operators** — distributors,
aggregators, and food hubs. Upload the operational CSVs you already have and
get a dollar-quantified diagnostic, calibrated probabilistic forecasts, and a
recommendation for how much to commit to each supplier and buyer *before*
supply is confirmed.

> Status: evidence includes synthetic operators and simulated decisions driven
> by public aggregate series. No real operator's records or realized customer
> savings have validated the engine. See `docs/remodel/README.md` and the
> historical `docs/PILOT_READINESS.md`.

### Commercial evidence audit (September 2026)

See [the commercial remodel and market verdict](docs/remodel/README.md) for
the pipeline correction, stricter policy confirmation, service-target
experiments, every synthetic run, competitor evidence and paid-pilot plan.
These experiments are **not customer savings validation**. Retaining the
incumbent is allowed; “no-harm” is not a future performance guarantee.

---


## Two operating domains

HarvestMind runs one optimization engine in two markets. `domain/` holds
the only code that knows them apart:

| | agriculture (perishable produce) | FMCG (shelf-stable distribution) |
|---|---|---|
| unit | kg | each / case / pallet |
| supply risk | yield on a commitment | fill and lead time on an order |
| over-buying costs | spoilage | capital |
| ordering | continuous | whole lots, MOQ (MILP) |

FMCG operators upload their exports to `stg_fmcg_*` and call `POST /fmcg/plan` (Next.js `/fmcg`, Streamlit page 09).
Before any candidate runs, the **adaptive state layer** (`adaptive/`) estimates the operating state from the operator's own supply and demand history plus public logistics signals: regime probabilities (not a label), a stress score with named components, change points that need two bad receipts rather than one, and per-SKU hysteresis. The state sets the optimizer's *posture* — scenario width, CVaR weight, regret budget, how far it may move from the incumbent, how much it is charged for churn, how long orders stay executable, and which candidates the safe gate may even consider. It runs in three modes on one continuous mapping: **efficiency** (calm: the optimizer minimises ordinary expected cost with the trust region off and every candidate admitted, protected only by the evidence gate), **balanced**, and **protection** (tight trust region, downside-weighted, short commit window). Public leading indicators (IMF PortWatch chokepoints and ports, NY Fed GSCPI, FRED freight, fuel, retail and sentiment series, GDELT shipping coverage) feed a per-lane outlook so the posture can move before the first short delivery; whether they lead is tested on real history, not assumed. `GET /fmcg/state` shows it; `POST /fmcg/plan` returns it with every plan (`docs/optimization/ADAPTIVE_DECISION_ENGINE.md`, validation in `docs/validation/ADAPTIVE_ENGINE_VALIDATION.md`).

The default FMCG mode is **SAFE_SELECTED** (`mode=safe`): the operator's own policy is the incumbent, candidates are backtested on the operator's history in multiple leakage-free folds with recorded supplier outcomes, and a candidate displaces the incumbent only when its conservative lower bound on improvement clears a threshold, service is non-inferior, downside regret is within budget, and it is confirmed on held-out folds. `mode_run=incumbent` with `No candidate cleared the conservative improvement threshold` is a successful result (`docs/optimization/SAFE_ADAPTIVE_OPTIMIZER.md`).

The earlier mode, **SELECTED**: order-up-to, the deterministic
and the stochastic optimizer are backtested on the operator's own trailing
history and the winner is run, because the stochastic model earns its keep
only when conditions bind (see `docs/validation/COMMERCIAL_MODEL_VALIDATION.md`).

## Is it releasable?

```bash
./scripts/commercial_validate.sh          # gates, minutes
./scripts/commercial_validate.sh --full   # plus simulation matrices
```

writes `artifacts/commercial_readiness.json`. The current verdict and the
open blockers are in `COMMERCIAL_READINESS.md`. Architecture and dependency
map: `docs/ARCHITECTURE.md`. Mathematics: `docs/MATH_SPEC.md`.

## What It Does

### 1. Diagnostic — where margin is leaking, in dollars

| Problem | What you get |
|---|---|
| "We're throwing away product but don't know how much" | Waste loss in dollars by product and reason |
| "Buyers complain we can't fill orders" | Shortage loss + buyer fulfillment rate ranking |
| "Our supplier keeps shorting us" | Fill rate + rejection rate per supplier, risk-flagged |
| "Regulators want lot traceability" | FSMA-204 completeness % + list of incomplete lots |
| "How much are we losing each year?" | Annualized savings estimate (15–30% band, labelled as an assumption) |

Deterministic arithmetic on your own records. Auditable, not learned.

### 2. Probabilistic forecasts — uncertainty with calibration gates

Demand from gradient-boosted quantile regression with Croston routing for
intermittent SKUs. Supplier delivery reliability from an empirical-Bayes
Beta-Binomial that pools thin-history suppliers toward the population in both
mean and variance. Intervals are corrected by **conformalized quantile
regression** and withheld when calibration data is too thin. Coverage is
measured out-of-sample; it is not a guarantee for every product or future
regime.

### 3. Optimizer — what to commit before supply is certain

A **two-stage stochastic program** solved by sample average approximation:
commitments are first-stage, spot purchases / waste / unmet demand are
second-stage recourse, with a newsvendor objective so the solution tracks the
critical fractile. Supplier dependence is modelled with Gaussian and t
copulas, because suppliers sharing a weather region fail together — treating
them as independent drove the value of the stochastic solution to
approximately zero.

Designed to be evaluated by replaying an operator's own history, and by out-of-sample
**value of the stochastic solution** with bootstrap intervals, reported as
beneficial / harmful / inconclusive rather than assumed positive.
To date, repository results use synthetic histories only.

**The full mathematical specification is in [`docs/MATH_SPEC.md`](docs/MATH_SPEC.md)** —
every computation, with formula and source file. Agents should start at
[`AGENTS.md`](AGENTS.md).

---

## Architecture

```
Modeling core
forecasting/supply_uncertainty/
  quantile_model.py   gradient-boosted quantile regression, Croston routing
  conformal.py        conformalized quantile regression, Mondrian variant
  baseline.py         empirical-Bayes pooling, data tiers
  evaluation.py       pinball, WIS, CRPS, PIT
risk/
  correlated_scenarios.py   copulas, Kendall tau, shrinkage, PSD repair
  supplier_distribution.py  Beta-Binomial supplier fill model
  scenario_generation.py    joint scenario draws + provenance
optimization/
  two_stage_sp.py     two-stage stochastic program (Pyomo + HiGHS)
  vss_evaluation.py   out-of-sample value of the stochastic solution
  lp_baseline.py      deterministic LP benchmark
agronomy/             weather-to-yield: heat exposure, shelf-life kinetics
backtesting/          leakage guard, policy replay

Product surface
web/            Next.js 16 App Router (TypeScript)
api/            FastAPI + Uvicorn
  routers/
    intake.py   CSV upload + one-click sample data loader
    diagnostics.py  Metrics + summary endpoint
    reports.py  HTML report generation
    data.py     Data quality endpoint
  dependencies.py  DuckDB connection pool
ingestion/
  csv_ingestor.py  CSV → DuckDB (allowlisted tables, column maps)
diagnostics/
  metrics.py    Waste/shortage/ATP/traceability calculations
  report_generator.py  Jinja2 HTML report
  data_quality.py     Staging data validation
db/
  migrations/   SQL migration files (apply in order)
data/
  samples/      5 sample CSVs for one-click demo load
tests/
  unit/         pytest, in-memory DuckDB fixtures
  integration/  Full round-trip through FastAPI + DuckDB
```

**Data store**: DuckDB (single-file, zero-dependency). One file = one operator.
**Staging tables**: `stg_products`, `stg_supplier_deliveries`, `stg_inventory_lots`,
`stg_buyer_orders`, `stg_waste_adjustments` — flat, no FK constraints, idempotent upload.

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 20.9+
- pip, npm (or pnpm)

### Backend

```bash
# From repository root
pip install -e ".[dev]"

# Optional legacy Streamlit dashboard, live Anthropic extraction, or PDF export:
# pip install -e ".[dev,dashboard,llm,pdf]"

# Apply all migrations and reference seeds
python3 scripts/setup_db.py --seeds

# Start API server
uvicorn api.main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

### Frontend

```bash
cd web
npm install
npm run dev
# → http://localhost:3000
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DUCKDB_PATH` | `harvestmind.duckdb` | Path to DuckDB file |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend URL for Next.js |
| `HARVESTMIND_AUTH_REQUIRED` | `false` | Require a valid operator bearer token on operator-scoped API requests |
| `HARVESTMIND_ADMIN_KEY` | unset | Enables admin-only token issuance and training controls |
| `HARVESTMIND_RATE_LIMIT_PER_MIN` | `0` | Per-process rate cap for heavy endpoints; set for networked pilots |

---

## Loading Data

### Option A — One-Click Demo

1. Open `http://localhost:3000/upload`
2. Click **Load sample dataset**
3. Navigate to Overview — you'll see real diagnostic findings immediately

### Option B — Upload Your Own CSVs

Upload CSV files through the Upload page. Each table has required columns:

| Table | Required Columns |
|---|---|
| `stg_products` | `product_name` |
| `stg_supplier_deliveries` | `product_name`, `delivery_date` |
| `stg_inventory_lots` | `product_name`, `quantity_on_hand` |
| `stg_buyer_orders` | `product_name`, `requested_quantity` |
| `stg_waste_adjustments` | `product_name`, `quantity_lost` |

See `docs/customer_intake/field_definitions.md` for full column specs.

---

## API Reference (Key Endpoints)

| Method | Path | Description |
|---|---|---|
| `POST` | `/intake/upload/{table}` | Upload a CSV to a staging table |
| `POST` | `/intake/load-sample-data` | Load all 5 bundled sample CSVs |
| `POST` | `/intake/clear/{table}` | Truncate a staging table |
| `GET` | `/intake/status` | Row counts across all staging tables |
| `GET` | `/diagnostics/summary` | Full diagnostic JSON (all metrics) |
| `GET` | `/diagnostics/recommendations` | ATP commitment recommendations only |
| `GET` | `/data/quality` | Staging data completeness + issues |
| `GET` | `/reports/diagnostic` | HTML diagnostic report (browser/print) |

---

## Metrics Explained

### Waste Loss (`total_waste_loss_usd`)
Sum of `estimated_value_lost` from `stg_waste_adjustments`. When value is missing,
falls back to average unit cost from supplier deliveries × quantity lost.

### Shortage Loss (`total_shortage_loss_usd`)
For each order where `fulfilled_quantity < requested_quantity` (excluding substitutions),
loss = missed_kg × `sales_price`. Zero when `sales_price` is null.

### Supplier Fill Rate
`accepted_quantity / ordered_quantity` per supplier. Risk = **High** if fill rate < 80%,
**Medium** if < 90%, **Low** otherwise.

### Buyer Fulfillment Rate
`fulfilled_quantity / requested_quantity` per buyer. Risk = **High** if < 90%.

### ATP (Available-to-Promise)
`total_on_hand_kg − committed_kg − expired_kg − near_expiry_kg`.
Near-expiry = lots expiring within 3 days of the analysis date.

### Traceability Completeness
Fraction of inventory lots with all 6 FSMA-204 fields populated:
`lot_id`, `product_id`, `supplier_id`, `arrival_date`, `quantity_on_hand`, `unit`.

### Estimated Annual Savings
`(waste_loss + shortage_loss) / period_days × 365 × 0.30`.
The 30% reduction assumption is based on USDA SR-77 research benchmarks.
Actual savings depend on which recommendations are implemented.

---

## Limitations

1. **Dollar values are estimates**, not accounting entries. Verify against your books before using in external reports.
2. **Lot expiry requires `expiration_date`** in the lots file. Missing dates are treated as non-expiring.
3. **Annualization assumes the analysis period is representative** of the full year. Seasonal operators should interpret conservatively.
4. **Traceability scope** covers 6 fields. Full FSMA-204 compliance requires additional records (harvest date, receiver info, transformation events).
5. **Vault isolation is file-based** — each authenticated operator resolves to
   a separate DuckDB vault. This is pilot isolation, not a horizontally scaled
   tenancy architecture.
6. **Authentication is optional in local development.** Every networked pilot
   must set `HARVESTMIND_AUTH_REQUIRED=true`, configure an admin key and CORS
   allowlist, and place the API behind TLS.

---

## Running Tests

```bash
# All tests
python3 -m pytest

# Unit tests only
python3 -m pytest tests/unit/ -v

# Integration tests only
python3 -m pytest tests/integration/ -v

# With coverage
python3 -m pytest --cov=diagnostics --cov=ingestion --cov=api
```

Frontend type check and build:

```bash
cd web
npx tsc --noEmit     # zero errors expected
npm run build        # production build
```

---

## Next Pilot Requirements

To move from demo to live pilot with an operator, you'll need:

- [x] **Pilot authentication** — hashed per-operator API tokens; browser token is session-only
- [x] **Pilot data isolation** — one migrated DuckDB vault and file tree per operator
- [ ] **Scheduled refresh** — cron job or webhook to reload CSVs from operator's export location
- [ ] **Data contract alignment** — map the operator's actual column names in `csv_ingestor.py`
- [ ] **Pilot success criteria sign-off** — see `docs/customer_intake/pilot_success_criteria.md`
- [ ] **Data request checklist** — operator completes `docs/customer_intake/data_request_checklist.md`

---

## Project Status

| Gate | Status |
|---|---|
| Backend tests (pytest) | ✅ Passing |
| Frontend typecheck (tsc) | ✅ Zero errors |
| Frontend build (next build) | ✅ Passing |
| Local demo runnable | ✅ One-click sample load |
| Diagnostic HTML report | ✅ Board-readable, printable |
| Pilot authentication + operator vault isolation | ✅ Implemented; deployment configuration required |
| Controlled single-host pilot deployment | ✅ Containerized; TLS/backup/restore remain operator responsibilities |

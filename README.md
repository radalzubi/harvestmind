# HarvestMind

**Perishable produce diagnostic platform** for food hubs, aggregators, and distributors.
Upload your operational CSVs, get a board-ready report showing waste loss, shortage risk,
available-to-promise by product, and FSMA-204 traceability gaps — in under two minutes.

---

## What It Does

| Problem | HarvestMind Diagnosis |
|---|---|
| "We're throwing away product but don't know how much" | Waste loss in dollars by product and reason |
| "Buyers complain we can't fill orders" | Shortage loss + buyer fulfillment rate ranking |
| "Our supplier keeps shorting us" | Fill rate + rejection rate per supplier, risk-flagged |
| "Regulators want lot traceability" | FSMA-204 completeness % + list of incomplete lots |
| "How much are we losing each year?" | Annualized savings estimate with 30% reduction assumption |

---

## Architecture

```
web/            Next.js 15 App Router (TypeScript)
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
- Node.js 18+
- pip, npm (or pnpm)

### Backend

```bash
# From repository root
pip install -e ".[dev]"

# Apply database migrations
python3 scripts/apply_migrations.py   # or: duckdb harvestmind.duckdb < db/migrations/010_diagnostic_staging.sql

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
5. **Single-tenant by design** — one DuckDB file per operator. No multi-tenant data isolation yet.
6. **No authentication** on the current API. Deploy behind a VPN or reverse proxy before sharing externally.

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

- [ ] **Authentication** — API key or session auth before exposing to external users
- [ ] **Multi-tenant isolation** — separate DuckDB paths per partner, or schema-per-tenant
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
| Authentication | ❌ Not yet implemented |
| Production deployment | ❌ Not yet configured |

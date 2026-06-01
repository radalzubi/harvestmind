# HarvestMind — Folder Map

Plain-English guide to what every folder in this repo is. Read this first.

HarvestMind is two things in one repo: a **Python backend + diagnostic engine**,
and a **Next.js frontend**. They run independently.

---

## The two apps

| Folder | What it is | Language |
|---|---|---|
| `web/` | **Frontend.** The Next.js dashboard operators see in the browser. Deployed to Vercel (root directory = `web`). | TypeScript / React |
| `api/` | **Backend API.** FastAPI server. Endpoints for CSV upload, diagnostics, reports, data quality. Run with `uvicorn api.main:app --reload`. | Python |

---

## The engine (Python packages)

| Folder | What it is |
|---|---|
| `dashboard/lib/` | **Diagnostic metrics engine.** The core math: waste loss, shortage loss, supplier reliability, buyer fulfillment, traceability, available-to-promise. `diagnostic_metrics.py` is the heart of the product. |
| `risk/` | **Risk modeling layer (the model upgrade).** Hierarchical supplier fill-rate distributions, shelf-life decay, the unified safe-commit recommendation, and the scenario generator that feeds the optimizer. |
| `optimization/` | **The optimizer.** Two-stage stochastic program, robust LP, CVaR, scenario reduction. Decides safe supply commitments under uncertainty. |
| `backtesting/` | **Proof harness.** Rolling-origin backtest with leakage protection, ROI calculator, and the old-vs-new policy comparison that quantifies avoided loss. |
| `ingestion/` | **CSV intake.** `csv_ingestor.py` maps messy operator CSVs into the staging tables, with column-name aliasing. |
| `forecasting/` | Demand/supply forecasting models. |
| `synthetic/` | Synthetic data generators (for testing and demos). |
| `reports/` | **Report generation.** Jinja2 templates + generators for the diagnostic HTML report, audit packages, ROI report. |
| `diagnostics/` | (if present) Report generator + data-quality checker helpers. |

---

## Data and config

| Folder / file | What it is |
|---|---|
| `db/migrations/` | SQL schema migrations. Apply in order. `010_diagnostic_staging.sql` creates the 5 staging tables. |
| `data/samples/` | **The 5 sample CSVs** used for the one-click demo (products, supplier deliveries, inventory lots, buyer orders, waste). |
| `data_contracts/` | Real-data templates + partner guide for what operators should send. |
| `harvestmind.duckdb` | **Live local database** (gitignored). Regenerate by applying migrations + loading sample data. |
| `pyproject.toml` | Python package definition + dependencies. |
| `Makefile` | Common commands. |
| `.env.example` | Environment variable template. |
| `.streamlit/` | Streamlit config (legacy dashboard prototype). |

---

## Tests and scripts

| Folder | What it is |
|---|---|
| `tests/unit/` | Unit tests for the engine, risk layer, report, shelf-life, supplier distribution, policy comparison. |
| `tests/integration/` | Full round-trip tests (CSV upload → DuckDB → diagnostics through the API). |
| `scripts/` | One-off and operational scripts (migrations, master runs, validation). |

---

## Documentation

| Folder | What it is |
|---|---|
| `docs/demo_verification.md` | 10-step local demo checklist. |
| `docs/customer_intake/` | What to ask operators for: data request checklist, field definitions, pilot success criteria. |
| `docs/outreach/` | The outreach packet: advisor memo, deck, demo script, professor + operator emails, pilot offer, prospect list, validation sprint, plus `version_b_venture_track/` for funding conversations. |
| `README.md` | Setup, architecture, metrics, limitations, pilot requirements. |
| `SECURITY.md` | Security notes. |
| `STRUCTURE.md` | This file. |

---

## What gets generated (not in git, safe to delete)

| Item | Regenerate with |
|---|---|
| `web/node_modules/` | `cd web && npm install` |
| `web/.next/` | `cd web && npm run build` |
| `harvestmind.egg-info/` | `pip install -e .` |
| `__pycache__/`, `.pytest_cache/`, `.ruff_cache/` | run tests / lint |
| `harvestmind.duckdb` | apply migrations + load sample data |
| `_archive_cleanup_review/` | archived old generated outputs (see CLEANUP_CHANGELOG.md inside) |

---

## Run it

```bash
# Backend
pip install -e ".[dev]"
uvicorn api.main:app --reload          # http://localhost:8000

# Frontend (after npm install)
cd web && npm install && npm run dev   # http://localhost:3000

# Tests
python3 -m pytest                      # 333 passing
cd web && npx tsc --noEmit             # 0 errors
```

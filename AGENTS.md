# AGENTS.md

Entry point for coding agents (Codex, Claude Code, etc.) working in this
repository. Read this before making changes.

## What this is

A stochastic supply-planning engine for midstream perishable food operators
(distributors, aggregators, food hubs). It ingests the CSV exports an operator
already has and produces three things:

1. **Diagnostic** — dollar figures for waste, shortage, supplier fill and
   rejection, buyer fulfillment, and available-to-promise. Deterministic
   arithmetic, auditable, not learned.
2. **Probabilistic forecasts** — demand and supplier delivery reliability,
   with calibrated uncertainty rather than point estimates.
3. **Optimizer** — a two-stage stochastic program that recommends how much to
   commit to each supplier and buyer before supply is confirmed.

## Quick start

```bash
make setup        # pip install -e ".[dev]", create DB, generate synthetic data
make test         # pytest tests/ -v
make demo         # end-to-end run on the synthetic operator
```

Manual equivalent:

```bash
pip install -e ".[dev]"
python3 scripts/setup_db.py --seeds
python3 synthetic/generate_pilot_dataset.py
python3 -m pytest -q
```

Requires **Python >= 3.11**. Node 18+ only if you touch `web/`.

Copy `.env.example` to `.env` if you need non-default settings. Defaults work
out of the box: DuckDB single-file backend, HiGHS solver, no cloud
credentials required. **No paid API, live weather service, GPU, or network
call is needed to run the test suite.**

## Commands

| Task | Command |
|---|---|
| Install | `pip install -e ".[dev]"` |
| Full test suite | `python3 -m pytest -q` |
| With coverage | `make test-cov` |
| Lint (must pass CI) | `python3 -m ruff check .` |
| API server | `make serve` (uvicorn, port 8000, `/docs` for Swagger) |
| Frontend | `cd web && npm install && npm run dev` (port 3000) |
| Backtest | `make backtest` |

Ruff is **pinned to 0.15.12** in `pyproject.toml` so CI and local cannot
disagree. Do not bump it casually.

## Layout

```
Modeling core (the differentiated work)
  forecasting/supply_uncertainty/   probabilistic forecasts
    quantile_model.py   gradient-boosted quantile regression, Croston routing
    conformal.py        conformalized quantile regression, Mondrian variant
    baseline.py         empirical-Bayes pooling, data tiers
    evaluation.py       pinball, WIS, CRPS, PIT
    contract.py         ProbabilisticForecast type + validation
  risk/
    correlated_scenarios.py   copulas, Kendall tau, shrinkage, PSD repair
    supplier_distribution.py  Beta-Binomial supplier fill model
    scenario_generation.py    joint scenario draws + provenance
  optimization/
    two_stage_sp.py     two-stage stochastic program (Pyomo + HiGHS)
    vss_evaluation.py   out-of-sample value of the stochastic solution
    lp_baseline.py      deterministic LP benchmark
    gamma_robust_lp.py  Bertsimas-Sim robust variant
  agronomy/             weather-to-yield: heat exposure, shelf-life kinetics
  backtesting/          leakage guard, policy replay

Product surface
  api/                  FastAPI (routers: intake, diagnostics, reports, data)
  web/                  Next.js 16 App Router (TypeScript)
  dashboard/            Streamlit + diagnostic metric implementations
  ingestion/            CSV -> DuckDB, allowlisted tables
  db/migrations/        SQL migrations, apply in order
  synthetic/            calibrated synthetic operator generator
  tests/unit, tests/integration
```

`docs/MATH_SPEC.md` is the authoritative description of every computation,
formula by formula, with the source file for each. **Read it before changing
anything in the modeling core.** `docs/research/supply_uncertainty_review.md`
covers the underlying literature.

## Invariants — do not break these

These encode bugs that were found and fixed. Reintroducing them is a
regression even if tests still pass.

1. **Fail closed, never silently degrade.** When a requested model cannot be
   supported, raise. Independent-scenario fallback happens only when a policy
   explicitly sets `on_failure="independent"`, and is then recorded in
   diagnostics as `fallback_applied` with the reason.
2. **Never catch broad exceptions on the modeling path.** `except Exception`
   converting a database fault or a programming defect into an
   apparently-valid result is the specific failure this codebase guards
   against. `ScenarioDataError` (infrastructure) is never governed by
   `on_failure`; generic `ValueError` is deliberately not caught.
3. **Validate operator-facing policy fields.** `SupplyRiskPolicy.__post_init__`
   rejects non-finite t-copula `df` and sufficiency thresholds below 1,
   because both silently disabled fail-closed behaviour.
4. **Provenance on every run.** Which dependence model, which seed, whether a
   fallback was taken. Diagnostics go to a caller-supplied per-call sink, never
   module-global state (that was unsafe under concurrent requests).
5. **Seed precedence.** `effective_seed = policy.seed if policy.enabled else
   seed`, resolved once, and the seed actually used is always what gets
   reported.
6. **Refuse rather than fabricate a guarantee.** The conformal calibrator
   returns `+inf` when calibration data is too thin to support the requested
   coverage. The correlation estimator refuses when pairwise overlap is
   insufficient rather than labelling a mostly-defaulted matrix "estimated".
7. **The leakage guard fails closed.** A missing date column raises rather
   than passing silently.
8. **Report unfavourable results.** Out-of-sample VSS is classified
   beneficial / harmful / inconclusive, never assumed positive.

## Honesty rules for this project

- Do not fabricate citations, DOIs, benchmark numbers, data availability,
  package capabilities, or statistical guarantees.
- All validation to date is on a **calibrated synthetic operator** (~$8M, 28
  products, 52 weeks). No real operator data has touched any layer. Do not
  describe results as validated on real data.
- Do not put real or mock operator data into any database used for training.
- Keep assumptions labelled as assumptions. The 15-30% savings recovery band
  is sourced from USDA SR-77 and is explicitly not measured.

## CI

`.github/workflows/ci.yml` runs on pull requests:

- **pytest** — full suite with coverage, uploads the coverage artifact
- **ruff** — blocking on the files the PR changes, non-blocking repo-wide
  debt report
- **next build** — only when `web/` changes

All three must be green before merge. Current baseline: **1035 tests passing,
81% coverage.**

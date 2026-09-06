# AGENTS.md

Entry point for coding agents (Codex, Claude Code, etc.) working in this
repository. Read this before making changes.

## TWO PROJECTS, ONE ENGINE

This repository serves **two separate projects** that share the
mathematical core and nothing else. Read `docs/projects/README.md` before
working on either, and do not mix their materials or their claims.

**Project A — Agriculture (US).** Midwest perishable operators. The
uncertainty is weather-driven yield, correlated across growers sharing a
region. All outreach in `docs/outreach/` is Project A only.

**Project B — Commercial distribution (Jordan first).** The uncertainty is
route and transit disruption: Aqaba by sea, road freight from and through
Saudi Arabia, overland via Syria and Iraq. Those routes are SUBSTITUTES, so
a scenario hitting one must leave the others alone. Project B needs the
route tagging, the disruption scenarios and the multi-period model that
Project A does not.

Weather correlation and route correlation are different covariance
structures. Do not conflate them, and do not quote one project's validation
results in the other's materials.

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
- Evidence includes **synthetic operators** and simulated decisions driven by
  public aggregate demand/port series. No real operator data or realized
  customer savings have validated the engine. Label the input and decision
  evidence separately; do not call aggregate-proxy replay operator validation.
- Do not put real or mock operator data into any database used for training.
- Keep assumptions labelled as assumptions. The 15-30% savings recovery band
  is sourced from USDA SR-77 and is explicitly not measured.

## CI

### Commercial audit invariants (September 2026)

- Read `docs/remodel/ROOT_CAUSE.md` and MATH_SPEC §28 before extending the
  commercial policy path. Dated pipeline must reach every planner.
- Planner-visible expected open POs and private realized future receipts are
  different data. Never expose eventual fill/arrival to the next review before
  it is observed. Supplier training events must be dated by availability.
- Nested folds use only dated prior supply evidence and standardized stock,
  not a reconstruction using current stock or later demand. Rebase event dates.
- Confirmation repeats cost, service, regret, completeness and solver-quality
  gates. A relaxed or unusable live solve cannot be promoted.
- The state-evidence bypass is experimental and defaults off. The service
  frontier is an experimental candidate, not an automatic service reduction.
- Aggregate horizon service can borrow from future periods; the separate
  per-period variant is stricter but still only expected service, not OTIF.
- Historical reports remain historical. Use the causal evidence directory in
  `docs/remodel/` and retain failed/rejected experiments with explicit labels.

`.github/workflows/ci.yml` runs on pull requests:

- **pytest** — full suite with coverage, uploads the coverage artifact
- **ruff** — blocking on the files the PR changes, non-blocking repo-wide
  debt report
- **next build** — only when `web/` changes

All three must be green before merge. Latest local commercial audit:
**1393 passed, 1 skipped**. Coverage was not remeasured in that audit; the
earlier 81% figure belongs to its earlier test baseline, not this one.

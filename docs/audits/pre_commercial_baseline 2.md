# Pre-commercial baseline

Recorded before any change on branch `commercial-readiness/fmcg-agriculture`,
at commit `657ddae` (tip of `feat/commercial-real-data-validation`, which
stacks PRs #14 and #16 on `main`). Every number below was produced by the
commands listed; nothing is estimated. Raw outputs: `artifacts/baseline/`.

Environment: macOS 25.3, CPython 3.14, HiGHS via `appsi_highs`, no Docker
daemon available on this machine.

## Tests

`python -m pytest tests/ -q --cov=optimization --cov=forecasting --cov=risk --cov=backtesting --cov=ingestion --cov=api --cov=synthetic`

| metric | value |
|---|---|
| passed | **1,111** |
| failed | 0 |
| skipped | 0 (7 conditional skip/xfail markers exist; none triggered locally) |
| xfailed | 0 |
| wall time | 59 s |
| coverage, listed packages | **83%** |

Zero-coverage modules in critical packages: `backtesting/service_metrics.py`,
`backtesting/waste_metrics.py`, `ingestion/nass_quickstats_fetcher.py`,
`synthetic/generate_pilot_dataset.py`, `synthetic/realistic_operator_sim.py`.
Lowest covered live modules: `backtesting/procurement_metrics.py` 39%,
`api/dependencies.py` 58% (the auth layer), `ingestion/pipeline.py` 62%.

No property-based tests exist; `hypothesis` was not installed.

## Lint, types, static security

| tool | result |
|---|---|
| ruff 0.15.12 | **165 errors** (90 E402 from the `sys.path.insert` script idiom, 35 F401, 14 F541, 9 E701, 6 E702, 5 F841, 4 E741, 2 E712) |
| mypy (optimization, risk, backtesting, api, ingestion) | **68 errors** (25 arg-type, 17 index, 12 assignment); not part of dev extras or CI |
| bandit MEDIUM+ (non-test packages) | **24** — 22× B608 string-built SQL, 2× B324 MD5 |
| TODO/FIXME | 2 |

mypy, bandit, semgrep and pyright were not installed and are not run by CI.

## Builds

| target | result |
|---|---|
| Next.js `web/` (`next build --webpack`) | **pass**, all routes static |
| Streamlit `dashboard/` | not built (script app; imported by tests) |
| Docker | **not verifiable** — no daemon on this host; `Dockerfile` and `compose.pilot.yml` exist |
| DB migrations | 12 SQL files under `db/migrations/`, DuckDB, applied by `scripts/setup_db.py`; 31 tables |

## Dependencies

`pip-audit` over the full interpreter reports 22 vulnerable packages. Restricted
to the project's own 115-package dependency closure: **11 packages, 70
advisories**. Decisive detail: **9 of the 11 are already pinned to a fixed
version in `pyproject.toml`; the local environment is simply stale.**

| package | installed | pyproject floor | fix available |
|---|---|---|---|
| starlette | 1.0.0 | >=1.6.0 | yes |
| python-multipart | 0.0.27 | >=0.0.32 | yes — this parses uploads |
| fastapi | 0.136.1 | >=0.141.1 | yes |
| urllib3 | 2.6.3 | >=2.7.0 | yes |
| idna | 3.11 | >=3.15 | yes |
| click | 8.3.1 | >=8.3.3 | yes |
| Pillow | 12.2.0 | >=12.3.0 | yes |
| pydantic-settings | 2.14.0 | >=2.15.0 | yes |
| gitpython | 3.1.49 | >=3.1.58 | **floor too low**: PYSEC-2026-3785..88 need 3.1.59 |
| tornado | 6.5.5 | >=6.5.7 | **floor too low**: 6.5.8 needed |
| cryptography | 46.0.7 | *(transitive, unpinned)* | 50.0.0 |
| weasyprint | 68.1 | >=69.0 | no fix published for PYSEC-2026-3412 |

CI installs fresh from `pyproject.toml`, so CI does not carry the first eight.
`anthropic` (the `[llm]` extra) is not installed locally.

## Secrets

- Working tree: no key-shaped strings, no tracked `.env`, no tracked caches,
  DBs, or `.DS_Store`.
- Git history: one hit, `.env.example` in commit `38eeac9`, a
  `postgresql://user:********@localhost` placeholder with the literal
  username `user`. **Informational**, not a credential.
- A `tests/unit/test_no_secrets_committed.py` guard already exists.
- Largest tracked file: `data/external/portwatch/chokepoint_daily.csv`, 8.6 MB
  (public IMF data, committed deliberately for reproducibility).

## Authentication and tenancy, as found

- Auth is bearer/API-key token → `operator_id`, tokens stored as SHA-256,
  constant-time compare, rotation and suspension supported.
- Isolation is **physical**: one DuckDB file per operator ("vault"), selected
  by `DBManager`. No shared table carries a tenant column; the
  `org_id`/`tenant` grep across all migrations returns nothing.
- **`HARVESTMIND_AUTH_REQUIRED` defaults to `false`.** In that mode the
  `?operator_id=` query parameter selects any vault with no credential.
  Documented as dev-only; nothing prevents a networked deployment shipping
  with the default. Recorded as a finding for the security pass.
- Frontend stores the token in `sessionStorage`, sends `Authorization:
  Bearer`; no `dangerouslySetInnerHTML` or `innerHTML` in `web/src`.

## Optimizer, as found

- `TwoStageStochasticLP` (single period) and `MultiPeriodStochasticLP`
  (ordering schedule, random lead times, holding, decay, optional inventory
  cap). Both pure LPs: continuous quantities, no MOQ, no case/pallet rounding.
- `newsvendor_objective` defaults to **False**, which the source itself labels
  "the original flat / double-count path". `benchmark_suite.py` and
  `risk/scenario_generation.py` opt into `True`; **`backtesting/rolling_origin_engine.py:370` and `scripts/demo_run.py` run on the default.**
- Weights are completed and normalised (`_normalized_weights`).
- Duals imported for supply-capacity shadow prices.
- Solver status is checked but only `optimal`/`locallyOptimal` is handled;
  infeasible, unbounded and timeout paths return an empty schedule without a
  distinct failure mode.
- `backtesting/leakage_guard.py` enforces a cutoff on wrapped frames; the
  engine still passes some frames around it (to be audited).
- Forecasting: LightGBM global model, hierarchical reconciliation,
  Croston/SBA/TSB intermittent models, MASE/RMSSE/coverage/Winkler evaluator,
  conformal supply quantiles.

## Domain model, as found

Single domain. Perishable-produce vocabulary (`demand_kg`, `capacity_kg`,
`waste`, `shelf_life`, `harvest`) runs through the optimizer, schemas,
API and both frontends. Project B (commercial) exists as separate simulators
(`synthetic/commercial/`), a route-tagged disruption overlay
(`risk/disruption_scenarios.py`) and validation scripts, all driving the same
optimizer with per-product cost dictionaries. There is no domain enum,
policy object, or configuration switch.

## Known defects carried in

From this repository's own reports: five harness defects previously moved a
headline (settlement scoring committed-as-delivered, fill-blind LP baseline,
peak-only evaluation folds, per-supplier mean lead times, horizon shorter
than lead time); four more were found and fixed in the real-data validation
(unbounded inventory, model/scorer disposal mismatch, outcome-selecting guard,
straw-man naive baseline). `docs/specs/FULL_SIMULATION_SWEEP.md` carries a
correction notice and its numbers are not quotable.

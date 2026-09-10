# ZAAD repository consolidation plan

Answer to "what exactly should become the canonical ZAAD repository lineage?", from the read-only
audit of 2026-09-10 (`docs/ZAAD_RELEASE_LEDGER.md` carries the ancestry and CI facts). No merge, close,
delete, rebase, push or deploy was performed.

## 1. Canonical lineage

**The optimizer lineage is the canonical code lineage**: `claude/zaad-cycle-stock-p1` at `12db66c`
(P1 frozen; contains P0 `2e30721`, PR #38 `e8e2398` and, by strict ancestry, every commit of PRs #16
through #38). It is created as `zaad/canonical` from that SHA without rebase, so every frozen SHA stays
reachable. The site lineage (`adaptive/decision-engine`, 12 web commits) and `main` (5 commits: Project B
synthetic generator, agent docs, the #26-#28 frontend change) are merged INTO it, never the other way,
and it then becomes the base of one pull request to `main`.

Why not `adaptive/decision-engine` or `main`: both lack 87 to 157 optimizer commits and the two
frozen states; `main` also lacks the site work that Vercel serves. Why not a squash: the freeze SHAs,
the evidence commits and the pre-registrations must remain addressable.

## 2. Port / merge order (each step has a validation and a rollback point)

| step | action | validation | rollback point |
|---|---|---|---|
| 0 | local tags `p0-frozen` = `2e30721`, `p1-frozen-product` = `f7e1e62`, `p1-frozen` = `12db66c` (push with the branches when authorized) | `git tag --contains` | tags |
| 1 | push `claude/zaad-industry-standard-v8` (nine P0 commits) and `claude/zaad-cycle-stock-p1`; open the P1 PR against #38's branch so the chain stays linear on GitHub | CI on the P1 PR: pytest green expected; mypy red (19, debt) and ruff repo-wide known | none needed (push only) |
| 2 | create `zaad/canonical` from `12db66c` | `git rev-list --count 12db66c..zaad/canonical` = 0 | branch pointer |
| 3 | merge `origin/adaptive/decision-engine` into `zaad/canonical` (conflicts only under `web/`: take the site lineage's `web/` wholesale, it is newer and is what Vercel serves) | `web`: `npm ci && npm run build`; python: `pytest tests/unit -q` (~2 min), `PYTHONPATH=. python3 -m scripts.p1_invariants` (720 / 720), the P1 suites in `tests/unit/test_zaad_*`, and one `p1_horizon_benchmark --fixtures B_fixed_order_cost_replace_sold --tag identity_step3` (5 min) bit-identical to `horizon52_cycle_B.jsonl.gz`; no matrix rerun | tag `consolidation-step3` before the merge |
| 4 | fix the site lineage's CI defects on `zaad/canonical` (three bandit Medium findings, the mypy failures that are not the optimizer's 19) | `bandit -ll` on the CI package list, `mypy` count back to 19, then the 19 addressed as a separate typed-debt commit (no behaviour change; P1 identity check as in step 3) | tag `consolidation-step4` |
| 5 | merge `origin/main` into `zaad/canonical` (conflicts: `web/` between #26-#28 and the site lineage; `docs/`; `synthetic/`). Decision required from the owner: which frontend is production (the ledger records Vercel on `adaptive/decision-engine`); keep Project B's synthetic generator and docs | as step 3 plus `docker compose -f compose.pilot.yml config -q` | tag `consolidation-step5` |
| 6 | open ONE PR `zaad/canonical` -> `main` titled "ZAAD canonical lineage: P0 and P1 frozen, site merged"; CI must be green apart from documented, ticketed debt | full CI | the PR itself |
| 7 | after that PR merges: close #16, #17, #18, #20, #21, #23, #24, #25, #30, #31, #32, #33, #35, #36, #37, #38 as superseded (their content is on `main`); repoint Vercel to `main` (or to `zaad/canonical` until then), then close #19 | Vercel preview of `main` green | Vercel previous deployment |
| 8 | Network Twin (#39): rebase-free merge of its three web commits into `zaad/canonical` only after the `/api/zaad_full` contract is declared stable and the twin's illustrative scenario engine is labelled and separated from optimizer output (it already is a labelled demo adapter) | `web` build, the twin's contract tests | tag `consolidation-step8` |

P2 does not start anywhere in this table.

## 3. PRs to close as superseded (after step 7 only)

#16, #17, #18, #20, #21, #23, #24, #25, #30, #31, #32, #33, #35, #36, #37, #38; then #19 once Vercel no
longer depends on its branch. #39 stays open as a deferred feature.

## 4. Duplicate / dead-code map (classification; nothing deleted now)

| item | what it is | class |
|---|---|---|
| `zaad/full/` (30 files, 8.1k lines) | the frozen P0 + P1 optimizer: contracts, model, planner, ownership, lotsizing, terminal, settlement, evaluation, replay, jobs, shadow | KEEP (canonical) |
| `zaad/engine.py`, `zaad/allocation.py`, `zaad/forecast.py`, `zaad/signals.py`, `zaad/intake.py`, `zaad/demo.py`, `zaad/contracts.py`, `api/routers/zaad.py` | the first ZAAD engine (finite-policy search) and its bounded API and CSV-bundle intake | DEPRECATE (superseded by `zaad/full`; keep until the FMCG intake is rewired) |
| `optimization/` (18 files: LP baseline, two-stage SP, SAA bounds, CVaR, VSS / EVPI, policies) | HarvestMind-era optimizer library used by `adaptive/` and `api/routers/planning.py` | DEPRECATE for purchasing decisions; KEEP the VSS / EVPI and SAA helpers as diagnostics until ported |
| `adaptive/` (10 files) | the PR #19 state layer (signals -> state -> posture) | PORT: its screen / posture ideas already exist in `zaad/full/screen.py`; keep until the API routes that use it are retired |
| `api/routers/fmcg.py` | FMCG planning API with its own solve on `stg_fmcg_*` tables | PORT to `zaad/full` (build a `Request` from the staging tables) |
| `api/routers/planning.py`, `backtest.py`, `forecasts.py`, `training.py`, `pool.py`, `fsma.py`, `assistant.py` | HarvestMind pilot surface | UNKNOWN (product decision); naming DEPRECATE |
| `dashboard/` (26 files) | HarvestMind Streamlit shell | DEPRECATE (the Next site is the product surface) |
| `docs/zaad_full/evidence` (117 MB), `docs/remodel/evidence` (11 MB), `docs/zaad_next/evidence` (6 MB) | frozen evidence | KEEP (never delete; consider git-lfs only for new records) |
| `.coverage 2` .. `.coverage 6` (340 KB, tracked) | generated coverage databases | DELETE LATER (add to `.gitignore`) |
| `data/external/portwatch/chokepoint_daily.csv` (8.2 MB) | real external dataset in the tree | UNKNOWN: move to tenant / feature storage or LFS |
| `artifacts/*.json` (2.7 MB) | adaptive transition validation outputs | KEEP as evidence, DELETE LATER from the package path |
| HarvestMind naming (168 files: `api/main.py`, `api/dependencies.py`, routers, `dashboard/lib`, `infrastructure`, `scripts`, tests, outreach docs) | old public name | DEPRECATE in code paths (rename module docstrings / app titles in one mechanical commit after step 5); KEEP in historical docs |
| `zaad/contracts.py` vs `zaad/full/contracts.py` vs `api/models/schemas.py` | three schema families | KEEP `zaad/full/contracts.py` as the optimizer contract; the API schema wraps it; the old one goes with the old engine |

Repository size: worktree 228 MB, shared `.git` 79 MB, tracked content 136 MB under `docs` (jsonl 65 MB,
gz 34 MB, json 30 MB, csv 18 MB), 471 tracked jsonl / json / csv files.

## 5. Real-data intake architecture (what exists, what is missing)

Existing path: CSV upload (`api/routers/intake.py`: size and column validation into `stg_*` tables, LLM
extraction sessions with operator confirmation; `ingestion/csv_ingestor.py`, `column_mapper.py`,
`validators.py`, `anonymize.py`; `data_contracts/real_data_templates` for orders, order lines,
deliveries, waste events with pandera schemas) -> tenant-isolated storage (`db/migrations` 001-015:
dimensions products / suppliers / locations / lanes / buyers / contracts, facts orders / order lines /
deliveries / purchase orders / inventory snapshots / lots / waste events / market prices / weather /
yields, FMCG staging `stg_fmcg_{skus, suppliers, orders, purchase_orders, receipts, inventory,
promotions, economics}`, planning outputs, lineage columns, supplier origin; `db/vault_storage.py`,
`db/operator_registry.py`, `api/routers/access.py`, `zaad/full/jobs.py` with `test_tenant_isolation.py`)
-> forecasting / calibration (`forecasting/`, and inside the optimizer `zaad/full/worlds.py`:
`history_series` -> `forecast_all` -> `draw`, the compact calibrated representation) -> compact planning
state (`zaad/full/contracts.Request`: history series, sources with declared fill and lead
distributions, terms, calendars, stresses) -> optimizer (`zaad/full/planner.plan`). External risk
signals (NOAA, Open-Meteo, USDM, ENSO, NASS, USDA AMS fetchers) feed `risk/`, not the optimizer.

| data type | intake | storage | consumed by `zaad/full` |
|---|---|---|---|
| sales history / customer orders | yes (orders, order lines, `stg_fmcg_orders`) | `fact_orders`, `fact_order_lines` | as `Request.history` (built by fixtures / API payloads only) |
| inventory history | `stg_fmcg_inventory`, `stg_inventory_lots` | `fact_inventory_snapshot`, `fact_lots` | as `Request.stock` (payload) |
| purchase orders / receipts | `stg_fmcg_purchase_orders`, `stg_fmcg_receipts` | `fact_purchase_orders`, `fact_deliveries` | pending arrivals in the payload; **fill / lead fitting from receipts is missing** (declared per source today) |
| supplier master / terms | `stg_fmcg_suppliers`, `stg_fmcg_economics`, supplier origin | `dim_suppliers`, `dim_contracts` | `Source`, `SupplierTerms`, `Terms` in the payload |
| SKU / product master | `stg_products`, `stg_fmcg_skus` | `dim_products` | `Sku` in the payload |
| waste / expiry | waste events template, `stg_waste_adjustments` | `fact_waste_events` | shelf life per SKU; realised waste not fed back |
| location / network | - | `dim_locations`, `dim_logistics_lanes` | `Location`, lanes in the payload |
| prices / costs | `stg_fmcg_economics` | `fact_market_prices` | unit prices in `Source` |
| promotions | `stg_fmcg_promotions` | staging only | **not consumed** |
| external risk signals | fetchers | `fact_weather_obs`, external sources | `risk/` only; ZAAD takes declared stresses |

Missing (must be built, not redesigned): one builder `tenant tables -> zaad.full.contracts.Request`
(today no code outside fixtures and API payloads constructs a `Request`; the FMCG router has its own
solve); supplier fill and lead fitting from receipts; promotion-aware demand history; a feedback of
realised waste. Exists only on `main`: the Project B synthetic generator (#14). Rule: raw histories stay
in tenant storage and calibration layers; the optimizer keeps consuming the compact `Request`.

## 6. Do-not-merge list

PR #39 (deferred), any PR into `main` before step 6, any branch that is not `zaad/canonical` after step 2,
`web/` changes from `main` #26-#28 without the production-frontend decision, P2 work of any kind.

## 7. Deferred work

Typed debt (19 mypy errors) as a no-behaviour commit with the P1 identity check; ruff debt in older P1
scripts and tests; renaming HarvestMind in code paths; git-lfs or archival for new evidence records; the
`Request` builder from tenant tables; fill / lead fitting; promotion history; Network Twin integration;
holdout4 remains frozen and unrun until a new validation cycle is authorized.

## 8. First three actions

1. Authorize the pushes of `claude/zaad-industry-standard-v8` and `claude/zaad-cycle-stock-p1` (ledger).
2. Create `zaad/canonical` from `12db66c` and tag the three frozen SHAs.
3. Merge `origin/adaptive/decision-engine` into `zaad/canonical` (web only) and run the step-3 validation.

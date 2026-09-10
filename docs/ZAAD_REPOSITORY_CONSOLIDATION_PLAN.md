# ZAAD repository consolidation plan

First written 2026-09-10 from the read-only audit after the P1 freeze; updated the same day at the end of
the canonical integration pass (`zaad/canonical`). What was planned, what was done, and what remains.

## 1. Canonical lineage (done)

`zaad/canonical` was created from `56e998f` (P1 frozen at `12db66c` plus the consolidation documents),
without rebase, so `2e30721`, `f7e1e62` and `12db66c` stay reachable and tagged. The site lineage
(`origin/adaptive/decision-engine`) and `main` were merged INTO it (`28d9839`, `0fbd8ee`); the old
optimizer PR stack was neither merged nor recreated: its accepted descendants are already in the
lineage. Frozen tree `zaad/full` `7cd0f5ab` is unchanged by the merges.

## 2. Integration steps: planned -> done

| step | planned | done |
|---|---|---|
| 0 | local tags | `p0-frozen`, `p1-frozen-product`, `p1-frozen`, `pre-canonical-integration` |
| 1 | push the frozen branches | **not done: push not authorized** (commands in the checklist) |
| 2 | create `zaad/canonical` | done from `56e998f` |
| 3 | merge the site lineage | done, clean (`28d9839`); frontend typechecks and builds |
| 4 | fix the site lineage's CI defects and the typed debt | bandit: the three medium findings of the site lineage are absent from the canonical packages (the lineage fixed them after `2820a69`); mypy: 19 -> 0 with identity evidence (`3263aff`) |
| 5 | merge `main` | done (`0fbd8ee`); frontend decision recorded below |
| 6 | canonical PR to `main` | **not done: requires the push** |
| 7 | close superseded PRs, repoint Vercel | **not done: requires authorization** |
| 8 | Network Twin | deferred, untouched |

Frontend decision recorded: the site lineage's `web/` is authoritative (SEO metadata, canonical host,
`/how-it-works`, the workspace entry); main's #28 was an earlier copy of the same components whose only
unique lines were older titles, i18n strings and hero CSS. Vercel production tracks
`adaptive/decision-engine`; the canonical branch contains everything it serves.

## 3. What the integration added (not in any lineage before)

* `zaad/full/workspace.py`: tenant staging tables -> frozen `Request` (the missing link), with fitted
  supplier fill and lead (sample size, provenance, fallbacks), a leakage guard and compact dimensions.
* `/api/zaad/network/request/from-workspace` and `/plan/from-workspace`; `/fmcg/plan?mode=canonical`.
* `api.dependencies.legacy_planners_enabled`: one planning engine outside dev unless enabled explicitly.
* `scripts/zaad_canonical_regression.py` (frozen P0 / P1 identity in minutes), `scripts/zaad_workspace_smoke.py`.
* Canonical CI (`.github/workflows/ci.yml`), ESLint for the site, the hygiene and brand fixes.

## 4. API consolidation

| entrypoint | class | note |
|---|---|---|
| `/api/zaad/network/*` (`api/routers/zaad_full.py`) | KEEP, canonical | frozen P1 planner: plan, shadow ledger, jobs, workspace path |
| `/fmcg/plan?mode=canonical`, `/fmcg/status`, `/fmcg/readiness`, `/fmcg/state` | KEEP | purchase plan on the canonical engine; readiness and state are data diagnostics |
| `/fmcg/plan` legacy modes (safe, adaptive, stochastic, deterministic, order_up_to, incumbent, anchored) | DEPRECATE | served only while legacy planners are enabled |
| `/api/zaad/plan`, `/api/zaad/demo`, `/api/zaad/schema` (first engine) | DEPRECATE | gated the same way; page kept at `/zaad/legacy` |
| `/planning/run` | DEPRECATE (already marked) | HarvestMind pilot |
| `/jobs/*` (diagnostic jobs, PDF report), `/reports/*`, `/intake/*`, `/data/*`, `/access/*`, `/admin/*` | KEEP | product surfaces around the optimizer |
| `/backtest`, `/forecasts`, `/training`, `/pool`, `/fsma`, `/assistant`, `/diagnostics` | KEEP (product decision pending) | HarvestMind pilot surfaces, not competing planners |

REMOVE LATER (after the purchase-plan and network pages have no legacy consumer and one release has
run with legacy planners off): the first engine (`zaad/engine.py`, `zaad/{allocation,forecast,signals,
intake,demo,contracts}.py`, `api/routers/zaad.py`), the safe-selector modes of `fmcg.py` and the parts of
`optimization/`, `backtesting/` and `adaptive/` only they use.

## 5. Database / schema

Canonical schema for the ZAAD product: the operator vault (one DuckDB per operator, every migration
applied at creation by `scripts/setup_db.py`), with the FMCG staging family `stg_fmcg_{skus, orders,
purchase_orders, receipts, inventory, promotions, suppliers, economics}` (migrations 013-015) as the
intake contract the adapter reads, the planning-output tables (006) and the lineage columns (011).
Legacy / deprecated tables kept as-is: the produce-era staging tables (`stg_products`,
`stg_supplier_deliveries`, `stg_inventory_lots`, `stg_buyer_orders`, `stg_waste_adjustments`) and the
HarvestMind fact / dimension families (001-005, 007-010, 012), which the pilot surfaces and the first
engine still read. No migration was deleted or rewritten; tenant isolation is preserved (vault per
operator; `tests/unit/test_tenant_isolation.py`, `tests/integration/test_zaad_jobs.py`).

## 6. Duplicate / dead-code map (classification unchanged; actions taken)

| item | class | action in this pass |
|---|---|---|
| `zaad/full/` | KEEP (canonical) | untouched apart from `workspace.py` and the typed-debt commit |
| first ZAAD engine + `api/routers/zaad.py` | DEPRECATE | gated; page moved to `/zaad/legacy` |
| `optimization/`, `adaptive/`, `backtesting/` safe selector | DEPRECATE for purchasing | still imported by the legacy modes; lint-clean |
| `api/routers/fmcg.py` | PORT | `mode=canonical` implemented; legacy modes gated |
| `dashboard/` | DEPRECATE | excluded from the blocking lint scope |
| `docs/zaad_full/evidence` (117 MB) and the other evidence directories | KEEP | untouched; new records gzipped |
| `.coverage 2..6` | DELETE | removed and ignored |
| `data/external/portwatch/chokepoint_daily.csv` (8.2 MB) | UNKNOWN | left in place; see the artifact policy |
| HarvestMind naming | DEPRECATE in code paths | health service renamed; env-variable names (`HARVESTMIND_*`), logger names and internal module docstrings kept (configuration, not public); historical docs untouched |

## 7. Artifact storage policy (new evidence)

Frozen evidence stays in git and is never rewritten. New benchmark records are gzipped jsonl under
`docs/zaad_full/evidence/<phase>/closure/`; a record larger than ~10 MB compressed should go to git-lfs
or an object store with its SHA-256 recorded in the closeout instead of the repository. Generated
outputs (`.coverage*`, `coverage.xml`, `htmlcov/`, `.next/`) are ignored.

## 8. Deferred (not in this pass)

Repointing the two legacy consumers and removing the legacy engines; the 21 ESLint warnings; the
HarvestMind names in configuration and internal modules; git-lfs for future evidence; the
`data/external` dataset placement; PostgreSQL / production storage for vaults; Network Twin integration
(its clean integration point: after the canonical PR merges and `/api/zaad/network` is declared
stable, merge `claude/zaad-network-twin-v1` (three web commits) with its illustrative scenario engine
kept a labelled demo adapter); P2.

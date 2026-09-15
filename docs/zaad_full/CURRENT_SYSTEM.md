# ZAAD — current system (read this first)

**Status line (2026-09-15):** production runtime is `d2a3cb5` (Fly `zaad-api` v27, image
`canonical-d2a3cb5`, digest `sha256:2d5f2b5a…`) = the Operating Product V1 + V2 merge `458fcaf` plus
PR #83's planner orchestration (one ordered solver lease, honest queue); Vercel production from the
same tree. Every operating surface and the proposal loop are verified in production and stay
responsive while a plan runs; **the plan path is BLOCKED at the product's default scope**: on a
rested `shared-cpu-2x` machine 1, 2 and 5 products complete inside their caps (4.6 s, 29 s, 138 s)
and the 10-product default reaches TIMEOUT at 450 s with no throttling, while consecutive solves
exhaust the shared CPU's burst balance and throttle the whole machine for up to an hour
(`PRODUCTION_SOLVE_PERFORMANCE_RECOVERY.md`). No V2 runtime tag exists. `main` is production plus
docs; the release ledger's current-state table records the exact difference. **Continuing this work:
read [`HANDOFF_PLANNER_RECOVERY_2026-09-15.md`](HANDOFF_PLANNER_RECOVERY_2026-09-15.md) first.**

## What is released

| phase | capability | released at | authoritative record |
|---|---|---|---|
| P0 | protection / recovery (calibrated, false-protection guarded) | `2e30721` frozen; canonical line `11f5459` | `evidence/v8/P0_CLOSEOUT.md` |
| P1 | purchasing economics (cycle stock, terminal valuation) | `f7e1e62` / `12db66c`; released with the canonical line | `evidence/p1/P1_CLOSEOUT.md` |
| P2 | multi-echelon network | Fly v16 `5ca3772` | `evidence/p2/P2_CLOSEOUT.md` |
| Sector physics | commercial / produce / meat-seafood physics | Fly v16 `5ca3772` | `evidence/sectors/SECTOR_PHYSICS_CLOSEOUT.md` |
| P3 | sourcing portfolio | Fly v17 `0de6850`, perf closure v18 `61a3e75` | `evidence/p3/P3_CLOSEOUT.md`, `evidence/p3/perf_closure/` |
| P4 | adaptive recourse | `8c813ac`; perf closure `6b58764` (Fly v21) | `evidence/p4/` |
| P5 | ATP / scarce-supply allocation | `2fc7b50` (Fly v22, `p5-release-runtime`) | `evidence/p5/release_audit/P5_RELEASE_AUDIT.md` |
| P4B V1 | open PO / commitment intervention (KEEP / DEFER / EXPEDITE / REDUCE / CANCEL / SPLIT) | `1851f40` (Fly v23, `p4b-v1-release-runtime`) | `evidence/p4b/release_audit/P4B_RELEASE_AUDIT.md` |
| Operating product V1 + V2 | inventory, purchase orders, proposal evaluation and export, governance, closed loop, readiness, amendment counterfactual, transfers, bulk | `458fcaf` merged; Fly v26 `canonical-458fcaf`; **production plan path BLOCKED on shared-cpu-2x** (no runtime tag) | `OPERATING_PRODUCT_V1.md`, `OPERATING_PRODUCT_V2.md`, `FABLE_V1_AUDIT.md`, `FABLE_V2_RELEASE_AUDIT.md` |

Not started (each needs its own authorization): P4B V2 (node-indexed amendments), P6, P7, P8, P9.

**Merged and deployed 2026-09-15, plan path blocked in production: the operating product** (V1
audited and corrected, V2 built on the same branch — PR #81, merge `458fcaf`, Fly v26
`canonical-458fcaf`, Vercel production from the merge). It adds no optimizer behaviour: after the V1
audited checkpoint no file under `zaad/` changed, and the only `zaad/` file in the whole release is
`zaad/full/jobs.py` (job ownership, leases and purposes; the frozen regression passed on it and in
CI). Every surface and the whole proposal loop were verified on production; the default 10-product
plan timed out on the `shared-cpu-2x` machine, so **no runtime tag exists yet**. The recovery pass
of 2026-09-15 (`PRODUCTION_SOLVE_PERFORMANCE_RECOVERY.md`) separated the two causes: the shared
CPU's burst budget (one plan spends it; everything after runs at 6.25 % — the day's TIMEOUTs and
40–80 s reads) and the planner's own scaling at ten products jointly (more than 450 s of one
unthrottled core: the joint escalation solve and the per-service confirmation ladder). Two owner
decisions unblock it: a dedicated CPU (`performance-2x`, spend) and the default scope or cap
(product policy); the ledger records both with the measurements. Architecture records: [`OPERATING_PRODUCT_V1.md`](OPERATING_PRODUCT_V1.md)
and [`OPERATING_PRODUCT_V2.md`](OPERATING_PRODUCT_V2.md); audits: [`FABLE_V1_AUDIT.md`](FABLE_V1_AUDIT.md)
and [`FABLE_V2_RELEASE_AUDIT.md`](FABLE_V2_RELEASE_AUDIT.md). ZAAD still sends nothing to a supplier;
exports are files; external status is human-recorded.
The Network Twin shipped with the frontend rebuild, built on the canonical engine rather than PR #39's
superseded `/fmcg` path. Engineering is pausing new optimizer phases until stronger operator evidence exists.

Validation status: **engineering-validated on synthetic and demo-scale states; not real-data validated.** No customer
savings claim is established by this repository.

## Where the code is

* `zaad/full/` — the canonical optimizer: contracts, model (one joint MILP on HiGHS), settlement ledger, economics,
  planner (candidates, selector, gates), workspace adapter, replay. Frozen mathematics: change only with a frozen
  regression pass.
* `zaad/meio/` (P2), `zaad/sectors/`, `zaad/sourcing/` (P3), `zaad/recourse/` (P4), `zaad/atp/` (P5),
  `zaad/commitments/` (P4B) — phase layers on the same engine; each is absent from the report unless declared.
* `api/routers/zaad_full.py` (`/api/zaad/network/*`: plan, from-workspace, jobs, shadow), `zaad_atp.py`; `api/dependencies.py`
  (auth, tenant, legacy gate). Everything else under `api/` and the packages `adaptive backtesting dashboard domain
  forecasting infrastructure ingestion optimization pool reports risk synthetic training ...` is the legacy HarvestMind
  platform: still mounted, gated where it plans (`ZAAD_LEGACY_PLANNERS=0` in production), not the optimizer.
* `web/` — the Next.js site and workspace (Vercel, production branch `main`). The workspace is
  four surfaces — Home, Decisions, Network, Data — over one read of the operator's vault; planning
  runs on the asynchronous jobs path because a solve takes minutes. `FRONTEND_UX_REBUILD.md` is the
  record of how it is built and what it deliberately does not claim.
* `db/migrations/` — 27 idempotent migrations applied by `scripts/setup_db.py` (023–027 are the operating product's own tables and columns, also applied lazily by `api/product/drafts.py::ensure_tables`).

## How it is validated (the frozen chain)

`scripts/zaad_canonical_regression.py` and `scripts/p1_invariants.py` run in CI on every change. Before a release:
`p2_benchmark` + `p2_decision_compare` against `evidence/p2/p2_perf_closure.jsonl` (1,720 / 1,720 reviews),
`sector_benchmark` against `sector_perf_closure` (416 / 416), `p3_benchmark` against `p3_perf_closure` (2,304 / 2,304),
`p1_p0_arms <arm>` + `p1_ownership_compare router_cycle <arm>` (120 / 120), the P3 shared-MOV snapshot identity,
the phase matrices (`p4_*`, `p5_*`, `p4b_*` benchmark / adversarial / profile), the full pytest suite, ruff, mypy,
bandit, pip-audit, gitleaks, Docker build, frontend build. The P4B release audit's `chain.sh` is the current
worked example (`evidence/p4b/release_audit/`). A review that hits a solver time limit under load is rerun alone
before it is judged.

## How it is released

Freeze tags (`<phase>-frozen-product`, `<phase>-frozen`), one release PR, CI green on the tested head, merge commit,
deploy from a clean detached checkout of the merge SHA (`fly deploy -a zaad-api --image-label canonical-<sha>
--strategy rolling --yes`), production smoke from the same checkout, log inspection, then `<phase>-release-runtime`.
Never move a historical tag. The ledger (`../ZAAD_RELEASE_LEDGER.md`) is the record of every release.

## Reading order for a new engineer

1. this file; 2. `../cofounder/00_START_HERE.md` (product and operating rules); 3. `OPTIMIZER_PRODUCT_STRATEGY_AND_INDUSTRY_ROADMAP.md`;
4. the latest release audit (`evidence/p4b/release_audit/P4B_RELEASE_AUDIT.md`) for how a change is proven;
5. `MATHEMATICAL_MODEL.md` and `ARCHITECTURE.md` for the model; 6. `REPOSITORY_CLEANUP_AUDIT.md` for what every
directory is and why it is kept; 7. `FRONTEND_UX_REBUILD.md` for the product surface and its honesty rules. Everything under `evidence/` and the other `docs/` directories is historical
evidence: trustworthy as a record, not a statement of the current system.

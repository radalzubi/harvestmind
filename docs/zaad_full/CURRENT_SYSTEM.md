# ZAAD — current system (read this first)

**Status line (2026-09-26):** production runtime is `c7ec175` (Fly `zaad-api` **v38**, image `canonical-c7ec175`, digest
`sha256:f469b54d…`) = the frontier-decomposition runtime `328a294` + **security hardening pass** (PR #96: tenant, role, worker and
input boundaries hardened with a `tests/security` CI shard; no optimizer or product-behaviour change; scorecard PASS WITH LIMITATIONS —
the committed NTDCO access code still needs rotating by the owner, tokens do not expire, no full offboarding). Runtime tag
`zaad-security-hardening-runtime`. Fly machine unchanged — `docs/security/SECURITY_REVIEW_2026_09.md`. Superseded status line: production runtime was `328a294` (Fly `zaad-api` **v37**, image `canonical-328a294`, digest
`sha256:a8c9333c…`) = the sentinel-cleanup runtime `6b8e38d` + **frontier oracle decomposition** (PR #95: the per-service frontier
oracle solved on the exact connected components of the built model with witness skips — identical frontier and decisions, the
50-product frontier 592 → 8 s, plan 784 → 158 s; production 25-product planner DONE in 306 s where it timed out before). Runtime tag
`zaad-frontier-decomposition-runtime`. Fly machine unchanged — `FRONTIER_ORACLE_DECOMPOSITION.md`. Superseded status line: production runtime was `6b8e38d` (Fly `zaad-api` **v36**, image `canonical-6b8e38d`, digest
`sha256:a2902398…`) = the Diagnostic V3.1 runtime `0cad5de` + **optimizer sentinel cleanup** (PR #94: an undeclared warehouse capacity or
opening cash balance is an absent constraint in the contract, the model, the settlement and the adapters — never a 10⁹
placeholder; the linkage rows take a flow-derived bound; the objective is the plan's economics; declared values and the frozen
gates untouched). Runtime tag `zaad-sentinel-cleanup-runtime`. Fly machine unchanged — `OPTIMIZER_SENTINEL_CLEANUP.md`. Superseded status line: production runtime was `0cad5de` (Fly `zaad-api` **v35**, image `canonical-0cad5de`, digest
`sha256:117dc421…`) = the Diagnostic V3 runtime `d0edf15` + **Diagnostic V3.1** (PR #93: the replay completes at wide scope — the
reconstructed rule scaled to declared shared capacity; a labelled STUDY SELECTION of the replayed products; same-snapshot
decision-change accounting, settlement basis by leg, operating regimes; the certified symmetry reduction shipped default-off
with its proof and its measured cost). Runtime tag `zaad-diagnostic-v3.1-runtime`. Fly machine unchanged; the optimizer's default path is
untouched — `DIAGNOSTIC_V3_1_REPLAY_SCALE.md`. Superseded status line: production runtime was `d0edf15` (Fly `zaad-api` **v34**, image `canonical-d0edf15`, digest
`sha256:7a820f00…`) = the Diagnostic report V2 runtime `e512a62` + **Diagnostic V3** (PR #91 `03bcf2c` + PR #92: the simple policy
benchmark and ZAAD's historical decision replay kept apart — the production planner re-run at every weekly decision date on
a truth reconstructed from the operator's records, three legs through one settlement, explicit counterfactual labels, a
lookahead attestation, one canonical provenance ledger with consistency checks). Runtime tag `zaad-diagnostic-v3-runtime`. Fly machine
unchanged; the optimizer is untouched — `DIAGNOSTIC_V3_OPTIMIZER_REPLAY.md`. Superseded status line: production runtime was `e512a62` (Fly `zaad-api` **v32**, image `canonical-e512a62`, digest
`sha256:9c7c6ab1…`) = the Enterprise Analytics V1 runtime `172d808` + **Diagnostic report V2** (PR #89 + #90: the free
diagnostic's run lifecycle — queued with a position, running with real stages, timed out / cancelled as explicit states,
reconnect after refresh, no duplicate work — and a consulting-grade report built from deterministic structured findings,
rendered identically as PDF and in the app). Runtime tag `zaad-diagnostic-report-v2-runtime`. Fly machine unchanged; the
optimizer is untouched — `DIAGNOSTIC_REPORT_V2_IMPLEMENTATION.md`. Superseded status line: production runtime was `172d808` (Fly `zaad-api` **v30**, image `canonical-172d808`, digest
`sha256:79f598a2…`) = the performance-pass runtime `914c5c3` + **Enterprise Analytics V1** (PR #88: the governed semantic
layer, the typed query engine over the vault, Explore, saved analyses, dashboards, Ask ZAAD behind a provider boundary,
the optimizer hand-off, one destination registry with the command centre and device-aware shortcuts, and the NTDCO
Diagnostics fix — vault migrations now replay on first open). Runtime tag `zaad-enterprise-analytics-v1-runtime`. Fly machine unchanged
(`shared-cpu-2x`, 2 GB); the optimizer is untouched — `ENTERPRISE_ANALYTICS_V1_IMPLEMENTATION.md`. Superseded status
line: production runtime was `914c5c3` (Fly `zaad-api` **v29**, image
`canonical-914c5c3`, digest `sha256:bfe6177f…`) = the V2.1A runtime `13dde49` + the **full performance pass**
(PR #86: the frontier oracle's discarded cost phase removed exactly, gzip on the API, the workspace's
independent reads started in parallel, benchmark tooling; `Request.fefo_symmetry_scope` merged
default-off). Fly machine unchanged (`shared-cpu-2x`, 2 GB). Rested on that machine the 8- and 10-product
plans now complete (208 s / 213 s; both timed out before); repeated use is still throttled by the shared
CPU's burst balance — `ZAAD_FULL_PERFORMANCE_PASS.md`. Superseded status line: production runtime was `13dde49` (Fly `zaad-api` v28, image
`canonical-13dde49`, digest `sha256:374b4e91…`) = the Operating Product V1 + V2 (`458fcaf`) + the
planner orchestration fix (PR #83) + **V2.1A Insights** (PR #84: server-side aggregations, the latest
completed plan read back, five value registers, engine connectivity matrix, one complete DEMO
company); Vercel production from the same tree. Every operating surface, the proposal loop and the
Insights section are verified in production (release smoke 24 / 24). **The plan path is still
BLOCKED at the product's default scope** (10 products exceed the 450 s cap even unthrottled; the
shared CPU's burst budget throttles consecutive solves — `PRODUCTION_SOLVE_PERFORMANCE_RECOVERY.md`,
two owner decisions pending in `HANDOFF_PLANNER_RECOVERY_2026-09-15.md`). Runtime tag for V2.1A:
`zaad-operating-product-v2.1a-runtime` (see the ledger); no V2 planner tag. `main` is production plus
docs; the release ledger's current-state table records the exact difference. **Continuing this work:
read the ledger's "Exact next action".**

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
| Operating product V2.1A — Insights | Insights section (Overview, Demand, Inventory, Supply & suppliers, Service & customers, Decisions & value, Perishability when declared): server-side aggregation of the operator's records, the latest completed plan read back, drill-downs, chart → action and action → insights links, five value registers, engine connectivity matrix; the DEMO company and its API-driven loop | `13dde49` merged (PR #84, tested head `2901ee9`, CI 35011852846 13 / 13); Fly v28 `canonical-13dde49`; production smoke 24 / 24 | `OPERATING_PRODUCT_V2_1_INSIGHTS.md`, `FABLE_V2_1_RELEASE_AUDIT.md` |

| Frontier oracle decomposition | the per-service frontier oracle (`min p_i Σ unmet_i` on the mean world, read after the decision into `service_frontier` / reliability classification) built once and solved per service on the exact connected component of the constraint matrix; witness skips (incumbent projection / base proxy / deterministic candidate serving in full); `FRONTIER_MODE` (`component` / `monolithic`); `orchestration.frontier` telemetry; `frontier_profile.py` | `328a294` (PR #95, tested head `14ba8f4`, CI 35882180173); Fly v37 `canonical-328a294`; tag `zaad-frontier-decomposition-runtime` | `FRONTIER_ORACLE_DECOMPOSITION.md` |
| Optimizer sentinel cleanup | undeclared location capacity and capital represented as absent constraints (`None`) rather than 10⁹: no volume rows / capacity bounds, flow-derived big-M for the depleted / FEFO / direct-first rows, no cash columns without a declared balance (working-capital charge on payments = the released objective minus its constant); adapters declare `None`; `formulation_audit.py`; the 25–50-product false abstentions gone, objective at economic scale | `6b8e38d` (PR #94, tested head `e09b854`, CI 35831587816); Fly v36 `canonical-6b8e38d`; tag `zaad-sentinel-cleanup-runtime` | `OPTIMIZER_SENTINEL_CLEANUP.md` |
| Diagnostic V3.1 | replay scale pass: the reconstructed rule scaled to declared shared supplier capacity (rule leg and declared incumbent), STUDY SELECTION scope rule, engine / scope-rule env, same-snapshot decision-change accounting, settlement basis by leg and metric, operating regimes; `fefo_symmetry_scope="certified"` (exact tie certificate or fallback; default `network`; frozen gates identical; measured too costly to be the engine); profile and owner decisions recorded | `0cad5de` (PR #93, tested head `9c46fc2`, CI 35665692963); Fly v35 `canonical-0cad5de`; tag `zaad-diagnostic-v3.1-runtime` | `DIAGNOSTIC_V3_1_REPLAY_SCALE.md` |
| Diagnostic V3 | simple policy benchmark (fixed rules, unchanged `safe_select`) kept apart from ZAAD's historical decision replay (`zaad/full/historical.py`: the production planner at every weekly decision date on a reconstructed truth; actual-orders and reconstructed-rule legs; MEASURED / INFERRED / SIMULATED / ASSUMED settlement labels; attestation; deterministic replay confidence); report V3 with computed intersections and one provenance ledger with consistency checks | `d0edf15` (PR #91 `03bcf2c` + PR #92; tested heads `4177b9c` / `0ecb5a2`); Fly v34 `canonical-d0edf15`; tag `zaad-diagnostic-v3-runtime` | `DIAGNOSTIC_V3_OPTIMIZER_REPLAY.md` |
| Diagnostic report V2 | diagnostic job lifecycle (queued / running with real stages / done / failed / timed_out / cancelled, FIFO solver slot, hard timeout, cancel, persistence, `GET /jobs/latest`, `report.json`); additive summary evidence; deterministic structured findings; consulting-style PDF and the same report in-app; indeterminate animated run view with reconnect and no duplicate work | `e88c660` (PR #89, tested head `eceed3f`, CI 35236930051) + `e512a62` (PR #90, tested head `b2ff8c8`, CI 35239397661); Fly v32 `canonical-e512a62`; tag `zaad-diagnostic-report-v2-runtime` | `DIAGNOSTIC_REPORT_V2_IMPLEMENTATION.md` |
| Enterprise Analytics V1 | governed semantic layer (38 contracts, 23 dimensions, join graph), typed query engine with a DuckDB adapter, dataset versions, Explore, saved analyses, dashboards, Ask ZAAD (provider-neutral, rules planner, validated model candidates), signals, optimizer hand-off, command centre and shortcuts; NTDCO vault migration-on-open | `172d808` merged (PR #88, tested head `5b9784d`, CI 35180417835); Fly v30 `canonical-172d808`; tag `zaad-enterprise-analytics-v1-runtime` | `ENTERPRISE_ANALYTICS_V1_IMPLEMENTATION.md`, `ENTERPRISE_ANALYTICS_V1_API.md` |

| Full performance pass | frontier oracle phase one only (exact), `fefo_symmetry_scope` request field (default = released), gzip, parallel workspace reads, benchmark tooling; no default scope / cap / gap / semantics change; Fly unchanged | `914c5c3` merged (PR #86); Fly v29 `canonical-914c5c3`; tag `zaad-full-performance-pass-runtime`; rested production 8 / 10 products DONE 208 / 213 s | `ZAAD_FULL_PERFORMANCE_PASS.md` |

Not started (each needs its own authorization): P4B V2 (node-indexed amendments), P6, P7, P8, P9; analytics phases beyond V1 (row-level scopes, multi-fact queries, warehouse adapters, external identity).

Architecture only, not built: the enterprise analytics and AI exploration blueprint (Insights → Explore → Ask ZAAD on one governed semantic layer) — `ENTERPRISE_ANALYTICS_ARCHITECTURE.md`, `SEMANTIC_LAYER_ARCHITECTURE.md`, `ASK_ZAAD_AI_ANALYTICS_ARCHITECTURE.md` (2026-09-16); its phases A1–A11 each need their own authorization.

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
  three groups of surfaces — Home, Decisions, Inventory, Purchase orders | Insights, Network,
  Diagnostics, History | Upload, Data — the operating surfaces over bounded server-side reads of
  the operator's records, Home / Decisions / Network over one read of the planning request (gzip
  since the performance pass), Insights over server-side aggregations; planning runs on the
  asynchronous jobs path because a solve takes minutes. `FRONTEND_UX_REBUILD.md` is the
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

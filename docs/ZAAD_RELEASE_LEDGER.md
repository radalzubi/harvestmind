# ZAAD release ledger

## Current state (2026-09-26, security hardening pass released) — the only section that describes NOW

| item | value |
|---|---|
| production runtime | `c7ec175dee778b5587b89306e6207f29037c5774` = `Merge PR #96: fix(security): Full-stack hardening pass — tenant, role, worker and input boundaries` (tested head `e98d63b`, CI 36206321621 14 / 14) on the frontier-decomposition runtime `328a294` (+ its docs commits). Fly `zaad-api` **v38**, image `canonical-c7ec175`, digest `sha256:f469b54dabe857a63dbbec8814b0cf1b1a6e730357a09765093c048e32cd40bf`, deploy-api run 36207679737; machine `0804e0dfd1e948` `shared-cpu-2x` / 2 GB **unchanged**; Vercel production `dpl_5gViqAxP7QKhU3974x7TersghCCK` from `c7ec175` |
| production health | release smoke on v29 **24 / 24**; rested probes on v29: 1 / 2 / 5 / 8 / 10 products DONE 4.4 / 30.4 / 133.7 / 208.4 / 212.6 s (8 and 10 timed out on v28), reads in their idle band, steal ≤ 5.5 s; a plan spends ~265 s of the burst balance, so a second plan within ~35 min runs throttled (`ZAAD_FULL_PERFORMANCE_PASS.md` §10) |
| current `main` | = production `c7ec175` plus the post-merge docs commit |
| RELEASED | P0 … P4B V1 (as before); Operating Product V1 + V2 (deployed, plan path blocked — no V2 planner tag); **Operating Product V2.1A Insights** (tag `zaad-operating-product-v2.1a-runtime` = `13dde49`); **full performance pass** (tag `zaad-full-performance-pass-runtime` = `914c5c3`); **Enterprise Analytics V1** (tag `zaad-enterprise-analytics-v1-runtime` = `172d808`); **Diagnostic report V2** (tag `zaad-diagnostic-report-v2-runtime` = `e512a62`); **Diagnostic V3** (tag `zaad-diagnostic-v3-runtime` = `d0edf15`); **Diagnostic V3.1** (tag `zaad-diagnostic-v3.1-runtime` = `0cad5de`); **optimizer sentinel cleanup** (tag `zaad-sentinel-cleanup-runtime` = `6b8e38d`); **frontier oracle decomposition** (tag `zaad-frontier-decomposition-runtime` = `328a294`); **security hardening pass** (tag `zaad-security-hardening-runtime` = `c7ec175`, PASS WITH LIMITATIONS — `docs/security/SECURITY_REVIEW_2026_09.md` §16) |
| DEFERRED | the workspace read's Python-side construction cost at 10 k+ products (3.6 s / 14 s scoped to 200); a compact display read + server-side plan submission by scope; reconciling the per-MILP budget with the job cap; exposing CPU steal on Diagnostics; P4 adaptive recourse visuals |
| REJECTED | component-wise decomposition; MIP gap 1e-4 / 1e-3; HiGHS thread changes; warm-start policy change; SQL-side SKU scoping of the workspace read (exact, not the cost); raising the cap or lowering the default scope without the owner |
| NOT STARTED | P4B V2, P6, P7, P8, P9 — each needs its own authorization |
| owner decisions pending | (0) **rotate the committed NTDCO access code** (SEC-001; the value is public in git history) and decide on token expiry / tenant offboarding (`SECURITY_REVIEW_2026_09.md` §16); (1) `fefo_symmetry_scope="all"` on the product path — exact, 5 products 135 → 5 s, 8 / 10 → ~181 s local; moves an equal-cost tie on frozen fixture T (`ZAAD_FULL_PERFORMANCE_PASS.md` §5 E5); (2) `solver_mip_gap` 1e-5 — 8 products 226 → 4 s local with tolerance-level differences (E7); (3) the machine: `fly scale vm performance-2x --memory 4096 -a zaad-api` (+$52.56 / month) for repeated use — the rested default plan now fits its cap, sustained use does not; (4) the V2 planner runtime tag: the handoff's two-in-a-row proof on v29 after (3) or on a rested machine |
| tags that never move | `p0-frozen`, `p1-frozen-product`, `p1-frozen`, `pre-canonical-integration`, `sector-physics-release-runtime`, `p3-performance-closure-runtime`, `p4-release-runtime`, `p4-performance-closure-runtime`, `p5-frozen-product`, `p5-frozen`, `p5-release-runtime`, `p4b-v1-frozen-product`, `p4b-v1-frozen`, `p4b-v1-release-runtime`, `zaad-post-p4b-cleanup-runtime`, `frontend-rebuild-runtime`, **`zaad-operating-product-v2.1a-runtime`**; no `zaad-operating-product-v2-runtime` (withheld until the planner passes) |
| current entry point | `docs/zaad_full/CURRENT_SYSTEM.md` |
| CI | one workflow (`.github/workflows/ci.yml`): 14 jobs (a `security` shard runs `tests/security`), `cancel-in-progress` per branch (a docs push cancels a running PR run; the `pull_request` event re-runs it); `deploy-api.yml` deploys an exact SHA to Fly from a GitHub runner (secret `FLY_API_TOKEN`, 30-day token created 2026-09-15); Markdown-only pushes do not run CI; branch protection unavailable on this plan |

## Security hardening pass — tenant, role, worker and input boundaries (2026-09-26)

| item | value |
|---|---|
| branch / PR | `security/full-stack-hardening`, PR #96 (from `bdb570b`) |
| tested head | `e98d63b` (CI 36206321621, 14 / 14 — the new `security` shard included) |
| merge | `c7ec175dee778b5587b89306e6207f29037c5774` |
| deploy | Fly v38 `canonical-c7ec175`, digest `sha256:f469b54dabe857a63dbbec8814b0cf1b1a6e730357a09765093c048e32cd40bf` (36207679737); Vercel production `dpl_5gViqAxP7QKhU3974x7TersghCCK` from `c7ec175`; **Fly machine unchanged** |
| runtime tag | `zaad-security-hardening-runtime` = `c7ec175` (old tags untouched) |
| what changed | 38 recorded findings (2 CRITICAL, 7 HIGH, 14 MEDIUM, 15 LOW, 0 INFORMATIONAL; SEC-038 LOW open, SEC-001's rotation owner-side) — the confirmed ones fixed with regression tests in `tests/security/` (217 tests, CI shard): Fly-Client-IP as the address of record + failed-auth throttle; `capability()` gates on every mutation (`runPlanner`, `runDiagnostic`; VIEWER read-only); per-job HMAC worker token and a 404 for the internal routes through the proxy; tenant-bound, id-validated extraction sessions; body-size limits; schema routes 404 in production; API security headers and a site CSP; access page strips and validates the token; CSV formula escaping; PDF escaping; registry 0600 + atomic + flocked; 12-char minimum access codes; error and log redaction; self-serve caps; deploy workflow pinned and allow-listed. No optimizer, service, ledger or product-behaviour change (frozen regression PASS) |
| open | SEC-001 rotation (owner); tokens never expire; no full offboarding; extractor sees raw identifiers; no Python lockfile; solver shares the API machine; SEC-038 LOW (previous tenant's recents key after a sign-in by link) |
| production QA | throwaway workspaces only; `SECURITY_REVIEW_2026_09.md` §16 |
| record | `docs/security/SECURITY_REVIEW_2026_09.md` |

## Frontier oracle decomposition — the per-service frontier on exact model components (2026-09-23)

| item | value |
|---|---|
| branch / PR | `perf/frontier-oracle-decomposition`, PR #95 (from `b9d28cc`) |
| tested head | `14ba8f4` (CI 35882180173, 13 / 13) |
| merge | `328a294a00c7e5349685be0cc54a09e4cde9a4ff` |
| deploy | Fly v37 `canonical-328a294`, digest `sha256:a8c9333cce05bd3c2a2d342dc4ac39969ed620fa038c46047b4ef44c722e1da7` (35885104825); Vercel production `dpl_DoNrfbM7DpccU3FFGiUyGJ9HKRnW` from `328a294`; **Fly machine unchanged** |
| runtime tag | `zaad-frontier-decomposition-runtime` = `328a294` (old tags untouched) |
| what changed | `zaad/full/frontier.py` + `model.solve(frontier_services=, frontier_witnesses=)` + `planner.FRONTIER_MODE`: the per-service frontier oracle builds the mean-world model once, partitions its constraint matrix into exact connected components (from the rows the builder produced) and solves each service's phase-one minimum on its own component; a service a deterministic witness already serves in full is at its frontier without a solve; the released loop stays callable as `monolithic`; `scripts/frontier_profile.py`; `orchestration.frontier` telemetry in the report |
| optimizer | frontier values identical wherever the released solve proved its optimum (the two 50-product services whose released solve hit its cap now carry the proven optimum instead of an incumbent's fill); decisions identical on every request and on 86 / 86 replay dates; frozen canonical regression PASS; `solver_mip_gap`, scenarios, floors, gates, tie-breaks, `fefo_symmetry_scope` untouched |
| effect | sample 50 products: frontier 592 → 8 s, plan 784 → 158 s, RSS 1.9 → 1.0 GB; replay 50 × 8 104 → 32 min (3.1 → 1.6 GB); 25 products plan 169 → 117 s; production 25-product planner DONE in 306 s (was TIMEOUT at 788 s). No gain on cash-coupled requests (one component); the joint solves' 1e-6 proofs remain the cost everywhere else |
| production QA | throwaway workspaces only; `FRONTIER_ORACLE_DECOMPOSITION.md` §20 |
| record | `docs/zaad_full/FRONTIER_ORACLE_DECOMPOSITION.md` |

## Optimizer sentinel cleanup — undeclared capacity and capital are absent constraints, not 10⁹ (2026-09-23)

| item | value |
|---|---|
| branch / PR | `fix/optimizer-sentinel-cleanup`, PR #94 (from `34221d4`) |
| tested head | `e09b854` (CI 35831587816, 13 / 13) |
| merge | `6b8e38d59b5aef262e32a6d34e2c10c356ec23ac` |
| deploy | Fly v36 `canonical-6b8e38d`, digest `sha256:a2902398184b9a65aa74542e4c8000e1238bf4afc7c2383a340b130aefbf7ba1` (35834091598); Vercel production `dpl_AxcC9XfyaytWybAZzvjgSHj8pMiw` from `6b8e38d`; **Fly machine unchanged** |
| runtime tag | `zaad-sentinel-cleanup-runtime` = `6b8e38d` (old tags untouched) |
| what changed | `Location.capacity_volume`, `Liquidity.opening_cash` / `credit_limit` may be `None` = no constraint; `model.py`: no volume rows or capacity bounds for such a location, flow-derived stock bound as the big-M of the depleted / FEFO / direct-first rows and as the inventory column bound, the allocation rows' own bounds for the priority rows; no cash / debt columns without an opening balance and the working-capital charge on each period's payments (the released objective minus its plan-independent constant); settlement, rule projection, economics, replay carry-forward and the network view follow; the workspace adapters declare `None` instead of `1e9` / `1e7`; `scripts/formulation_audit.py` |
| optimizer | declared values keep the released formulation verbatim; frozen canonical regression identical; the certified symmetry path and `solver_mip_gap` untouched |
| effect | the 25–50-product requests that HiGHS declared infeasible in floating point (and the planner abstained on) are evaluated; the objective is the plan's economics instead of ≈ −5 × 10⁷ of placeholder; the same 1e-6 gap is an honest, tighter proof; replays decide identically where both formulations ran and cost their real solve time |
| production QA | throwaway demo workspaces only; `OPTIMIZER_SENTINEL_CLEANUP.md` §19 |
| record | `docs/zaad_full/OPTIMIZER_SENTINEL_CLEANUP.md` |

## Diagnostic V3.1 — scale the rolling optimizer replay without changing optimization semantics (2026-09-21)

| item | value |
|---|---|
| branch / PR | `feat/diagnostic-v3.1-replay-scale`, PR #93 (from `9c5519c`) |
| tested head | `9c46fc2` (CI 35665692963, 13 / 13) |
| merge | `0cad5dec1c5906d8a03c7671a245de5cc4efd6a0` |
| deploy | Fly v35 `canonical-0cad5de`, digest `sha256:117dc421258aa763720372ecb962723141fbe284dc9b6d6243cc01a2cab00439` (35667130197); Vercel production `dpl_G6PQvzhHghC9zxnQtXY9JUnnyWNn` from `0cad5de`; **Fly machine unchanged** |
| runtime tag | `zaad-diagnostic-v3.1-runtime` = `0cad5de` (old tags untouched) |
| what changed | `zaad/full/model.py` + `contracts.py`: `fefo_symmetry_scope="certified"` (the symmetry-reduced formulation accepted per solve only under an exact tie certificate, otherwise the released formulation; default `"network"` untouched; frozen gates identical with the path forced); `zaad/full/historical.py`: the reconstructed rule scaled to declared shared supplier capacity (rule leg and declared incumbent), STUDY SELECTION scope rule (`window_value`), engine / scope-rule parameters, same-snapshot decision-change accounting, settlement basis by leg, operating regimes; `api/routers/jobs.py` env `HARVESTMIND_REPLAY_FEFO` / `HARVESTMIND_REPLAY_SCOPE_RULE`; report / PDF / UI sections; `scripts/replay_profile.py` |
| optimizer | released formulation and search path unchanged by default; the certified path is proven decision-equivalent (certificate or fallback) and is not enabled anywhere |
| findings recorded for the owner | the certificate costs more than it saves on the replay's requests (§5 of the record); the unbounded warehouse-capacity placeholder makes 25–50-product requests numerically infeasible (§3.3); the unbounded opening-cash placeholder sets the 1e-6 gap at ≈ 50 cost units (§3.2) |
| production QA | throwaway demo workspaces `op_9246979a` / `op_ddbd8a22` only; record §8 |
| record | `docs/zaad_full/DIAGNOSTIC_V3_1_REPLAY_SCALE.md` |

## Diagnostic V3 — policy benchmark separated from a rolling replay of the ZAAD optimizer (2026-09-18)

| item | value |
|---|---|
| branches / PRs | `feat/diagnostic-v3-optimizer-replay` PR #91 (from `521ed68`); `fix/replay-partial-prefix-cache` PR #92 (from `03bcf2c`) |
| tested heads | `4177b9c` (CI 35363075037, 13 / 13); `0ecb5a2` (CI 35368689123, 13 / 13 after one re-run of the known solver-lease timing race) |
| merges | `03bcf2c2fbf9c80a2829cb812bdbf7b9b6e4782b`; `d0edf15309573ad97ea30dec4fcfb3ac2445e0bd` |
| deploys | Fly v33 `canonical-03bcf2c` (35364778824); Fly v34 `canonical-d0edf15`, digest `sha256:7a820f007d0760faa6faea5f3eeffe9d30b005212a48200b8c487040cd7059de` (35370542365); Vercel production `dpl_GXAAN52UJ4FK6UEXSZt8MrrsUEpd` from `d0edf15`; **Fly machine unchanged** |
| runtime tag | `zaad-diagnostic-v3-runtime` = `d0edf15` (old tags untouched) |
| what changed | `zaad/full/historical.py` (rolling replay of `zaad.full.planner.plan` at every weekly decision date on a truth reconstructed from the operator's records; actual-orders and reconstructed-rule legs through the same settlement; MEASURED / INFERRED / SIMULATED / ASSUMED settlement labels; lookahead attestation; deterministic replay confidence; recorded decisions served in the budget-stop re-run), `api/routers/jobs.py` (stage `replaying`, budget, never fails the diagnostic), `reports/diagnostic_v3.py` (benchmark framing, replay section, synthesis findings, one canonical provenance ledger with consistency checks), report builder / PDF / UI sections, `api.ts` types |
| optimizer | untouched (planner, model, replay loop, settlement, optimization, risk, backtesting unchanged; frozen regression green on every head) |
| production QA | throwaway demo workspaces `op_9246979a` / `op_ddbd8a22` only; `DIAGNOSTIC_V3_OPTIMIZER_REPLAY.md` §7 |
| record | `docs/zaad_full/DIAGNOSTIC_V3_OPTIMIZER_REPLAY.md` |

## Diagnostic report V2 — run lifecycle + consulting-grade report (2026-09-17)

| item | value |
|---|---|
| branch / PR | `feat/diagnostic-report-consulting`, PR #89 (from `ed2d15c`); wording follow-ups `fix/diagnostic-report-wording`, PR #90 |
| tested heads | `eceed3f` (CI 35236930051, 13 / 13 after one re-run of a pre-existing solver-lease test race); `b2ff8c8` (CI 35239397661, 13 / 13) |
| merges | `e88c660c47e0d79a9d5c7c5c6bd698ae93d8eafa` (PR #89); `e512a62a4ab5299d9e6efc64e02a82b88da39166` (PR #90) |
| deploy | Fly v31 `canonical-e88c660` (run 35238653172), then v32 `canonical-e512a62`, digest `sha256:9c7c6ab1abc87bcf549291e4c4fd5d2a0fbf0d97d4cb8f297d7e7ad18f5390cd` (run 35240675975); Vercel production from `e512a62`; **Fly machine unchanged** |
| runtime tag | `zaad-diagnostic-report-v2-runtime` = `e512a62` (old tags untouched) |
| what changed | `api/routers/jobs.py` (queued / running with real stages / done / failed / timed_out / cancelled, FIFO solver slot with queue position, hard timeout, cancel, persistence of every terminal state, `GET /jobs/latest`, `GET /jobs/{id}/report.json`), `api/worker.py` (stage forwarding, stop on cancel); `reports/diagnostic_summary.py` (additive evidence), `reports/diagnostic_findings.py` (deterministic structured findings), `reports/diagnostic_pdf.py`; web `lib/diagnostic/lifecycle.ts`, `components/diagnostic/DiagnosticRun.tsx`, `DiagnosticReport.tsx`, `/start` |
| optimizer | untouched (no file under `zaad/full`, `optimization`, `risk`, `backtesting` changed; frozen regression green on both tested heads) |
| gates | ruff, mypy, bandit, pip-audit, gitleaks, docker, frontend typecheck / lint / tests / build, six pytest shards, frozen regression |
| production QA | demo workspace `op_428f8767` only; lifecycle, isolation, PDF and browser walk in `DIAGNOSTIC_REPORT_V2_IMPLEMENTATION.md` §7 |
| record | `docs/zaad_full/DIAGNOSTIC_REPORT_V2_IMPLEMENTATION.md` |

## Enterprise Analytics V1 (2026-09-17)

| item | value |
|---|---|
| branch / PR | `feat/enterprise-analytics-v1`, PR #88 (from `ea08a93`) |
| tested head | `5b9784d`, CI run 35180417835, 13 / 13 (earlier heads: a stray test import and unmarked literal SQL for bandit, both fixed) |
| merge | `172d808a37e9bc619e5d7e8fd82c8f0076c88371`; `main` was `ea08a93` |
| deploy | Fly v30 `canonical-172d808`, digest `sha256:79f598a2a236d2479ab19e0522707c9f0e4ae08c2c3a906e950f62dc46411560`, deploy-api run 35181157905; Vercel production from `172d808`; **Fly machine unchanged** |
| runtime tag | `zaad-enterprise-analytics-v1-runtime` = `172d808` (old tags untouched; the V2 planner runtime tag stays withheld) |
| what changed | `api/analytics/*` (semantic registry, contracts, validator, planner, DuckDB adapter, results, freshness, cache, saved objects, exports, Ask ZAAD, signals, hand-off, Insights bridge), `api/routers/zaad_analytics.py`, migration 028, seven analytics capabilities in governance; web Explore / Dashboards / Ask ZAAD / Settings → Shortcuts, one destination registry, command centre; `db_manager` migration-on-open; `diagnostics` supplier-master guards |
| optimizer | untouched (no file under `zaad/full`, `optimization`, `risk` changed; canonical regression and P1 invariants green on the tested head) |
| gates | ruff, mypy, bandit, pip-audit, gitleaks, docker, frontend typecheck / lint / tests / build, six pytest shards, frozen regression |
| scale | 150 / 10k / 50k products: worst median 25 / 609 / 167 ms, payloads < 13 KB (`docs/zaad_full/evidence/analytics/analytics_scale.json`) |
| demo loop | `scripts/analytics_demo_walk.py` DEMO WALK OK locally and in production (`ENTERPRISE_ANALYTICS_V1_IMPLEMENTATION.md` §8, §10) |
| record | `docs/zaad_full/ENTERPRISE_ANALYTICS_V1_IMPLEMENTATION.md`, `ENTERPRISE_ANALYTICS_V1_API.md` |
| verdict | see the implementation record §11 |

## Full performance pass (2026-09-16)

| item | value |
|---|---|
| branch / PR | `perf/zaad-full-performance-pass`, PR #86 |
| tested head | `e563800`, CI run 35104491427, 13 / 13 (earlier heads: one gitleaks false positive on an image tag written as app:tag, resolved with exact fingerprints in `.gitleaksignore`; one flaky pass of the solver-lease unit test under CI load, green on every later head) |
| merge | `914c5c33b8c9bc92a098b60ac2248613a31e788a`, tree `99d43e2` identical to the tested head; `main` was `b818fd3` |
| deploy | Fly v29 `canonical-914c5c3`, digest `sha256:bfe6177f866969e819847fd37f80f010ea533fa19ede73abd2b9236b1a12125b`, deploy-api run 35105475528; Vercel production from `914c5c3`; **Fly machine unchanged** |
| runtime tag | `zaad-full-performance-pass-runtime` = `914c5c3` (the V2 planner runtime tag stays withheld) |
| what changed | frontier oracle phase one only (`solve(service_only=True)`, PROVEN DECISION-EQUIVALENT); `Request.fefo_symmetry_scope` default `network` (NO SEMANTIC IMPACT; `all` is the owner's); gzip on the API; the workspace provider starts its independent reads beside the planning read; benchmark tooling (`production_solve_benchmark` stage / phase attribution, MPS dump, request overrides, structure-only; `milp_replay`, `production_machine_sampler`, `workspace_scale_qa`, `plan_report_compare`) |
| root causes | (1) FEFO indicator symmetry on single-location requests (91 % of integer columns; joint phase one 66 s → 0.08 s without it); (2) the phase-two cost proof at MIP gap 1e-6 on a 4.5e7 objective (90 s per joint solve); (3) the frontier oracle's discarded cost phase (57 % of an 8-product plan) |
| before / after (production, rested) | 8 products TIMEOUT 405 s → DONE 208 s; 10 products TIMEOUT 450 s → DONE 213 s; 1 / 2 / 5 products unchanged (4.4 / 30.4 / 133.7 s); reads in their idle band during every solve; solver RSS ≤ 648 MB |
| decision equivalence | reports and plan shapes identical at 1–5 products; canonical PASS; P1 invariants 720; same-machine identity vs unchanged `main`: P2 1,720 / 1,720, sector 416 / 416, P3 2,304 / 2,304, P0 arm 118 / 120 (cell 21's two time-limited reviews vary run to run on the same code) |
| gates | ruff, mypy (153 files), bandit, pip-audit, gitleaks, docker, frontend typecheck / lint / 101 tests / build, pytest shards |
| record | `docs/zaad_full/ZAAD_FULL_PERFORMANCE_PASS.md`; addendum §15 of `PRODUCTION_SOLVE_PERFORMANCE_RECOVERY.md` |
| verdict | **ZAAD FULL PERFORMANCE PASS — RELEASE PASS**; Fly recommendation **B — YES FOR RELIABILITY** |

Every section below this line is historical: it records the state at the time it was written and is not
updated retroactively. "Next action" sentences inside historical sections are superseded by this table.

Source of truth for what is frozen, where it lives, and what may move next. First written 2026-09-10
after the P1 freeze; updated the same day at the end of the canonical integration pass. Update this
file whenever a freeze, a push, a merge or a Vercel change happens.

## Frontend rebuild, Network Twin and landing uplift (2026-09-14)

| item | value |
|---|---|
| branch | `feat/zaad-frontend-network-twin` |
| PR | #80 (one authoritative implementation PR) |
| tested head | `6371d75` |
| merge | ``e0fecdc` (merge commit; tree byte-identical to the tested head `a54f3fa`)` |
| CI | run `34804750031`, 13/13 green on the tested head |
| frontend deployment | Vercel from `main` (production branch), verified live |
| backend deployment | Fly `zaad-api` v25, image `canonical-e0fecdc`, deployed from a clean detached checkout of the merge SHA — required because `api/routers/zaad_full.py` changed |
| runtime tag | ``frontend-rebuild-runtime`` |
| scope | product UX, frontend, and one additive read-only API projection. No optimizer mathematics, economics, decisions, tenant behaviour or API semantics changed. |

**What shipped.** Four workspace surfaces (Home, Decisions, Network, Data) replace seven
destinations, with a bottom tab bar on a phone. One Decision shape answers the same seven questions
whatever phase produced it, in three disclosure layers. The Digital Network Twin ships on the
canonical engine — PR #39's `/fmcg` adapter was discarded because those legacy planning modes answer
410 in production. The public site is repositioned as the decision layer for imported supply, with a
company-quote flow.

**One backend addition**, `GET /api/zaad/network/directory`: declared supplier and location master
data the compact planning contract drops, read from the caller's own vault. No planner, no pricing,
no inference. Not rate limited, for the reason job status reads never have been.

**What the work established about the released engine**, recorded because it shaped the product and
is not a frontend limitation:

* a bounded eight-product network solve measures ~108 s, so planning is a job rather than a page
  load, and the product uses the released asynchronous jobs path for every plan;
* `/plan/from-workspace` has no size gate and will run for many minutes on a large catalogue, while
  `/jobs` refuses more than 200 products, 400 sources or 200 services — so a large workspace is
  planned over a stated selection, never silently;
* one planner slot per API process: a long run makes a concurrent interactive plan answer 429;
* the canonical contract carries no site coordinates, so a multi-site workspace is not placed on the
  map and the map says so.

**Gates.** Frontend typecheck, lint, 58 unit tests, production build; backend pytest, ruff, mypy,
bandit, pip-audit, gitleaks, Docker; frozen canonical regression and P1 invariants pass. CI now runs
the frontend tests. Twelve defects were found by browser QA against a live 150-product workspace and
fixed before merge; they are listed with a heuristic self-review in
`docs/zaad_full/FRONTEND_UX_REBUILD.md`.

**Not started, unchanged:** P4B V2, P6, P7, P8, P9 — each needs its own authorization.

## Frozen milestones (immutable)

| layer | verdict | SHA | tag (local) |
|---|---|---|---|
| P0 solver completeness / recovery | SOLVER COMPLETENESS / RECOVERY LOGIC — PASS AND FROZEN | `2e30721` | `p0-frozen` |
| P1 product code | P1 CYCLE-STOCK / PURCHASING ECONOMICS — PASS AND FROZEN | `f7e1e62` | `p1-frozen-product` |
| P1 final freeze (evidence) | same verdict; the P1 freeze point | `12db66c` | `p1-frozen` |
| post-freeze consolidation / documentation state | not a freeze | `56e998f` | `pre-canonical-integration` |

`12db66c` is the P1 frozen milestone; `56e998f` is the post-freeze documentation state (it adds only the
three consolidation documents). Neither is relabelled by the integration.

## Canonical branch

`zaad/canonical`, created from `56e998f` (the frozen P1 lineage plus the consolidation documents) and
carrying the integration in logical commits:

| commit | content |
|---|---|
| `28d9839` | merge of the site lineage `origin/adaptive/decision-engine` (`c941c64`): the twelve web commits Vercel serves (#22, #29, #34); clean merge, no python change |
| `0fbd8ee` | merge of `origin/main` (`865b701`): Project B synthetic generator (identical to the lineage's own copy), the workspace / agent documents (#15), the #26 / #27 net-zero pair; the 21 web conflicts of #28 resolved to the site lineage |
| `073d702` | the customer-data path (`zaad/full/workspace.py`), the canonical workspace endpoints, the legacy-planner gate, the purchase-plan page on the canonical engine, tests and smoke |
| `3263aff` | typed debt of the decision core (no behaviour change) and JSON-safe shortfall fields |
| `d7f76cf` | canonical CI gates, the fast frozen regression, security and hygiene closure, ESLint |
| closeout commit (this file) | source-of-truth documents |

Frozen optimizer tree: `zaad/full` at `12db66c` has tree hash `7cd0f5ab`; the two merges left it
byte-identical; `073d702` adds `workspace.py` beside it; `3263aff` changes annotations, three local
names and the report's representation of an infinite shortfall (None), with the identity evidence
below. Optimizer behaviour is frozen and verified, not assumed.

## Integrity evidence after integration

* `scripts/zaad_canonical_regression.py`: B, T, Q, A twelve-review rolling replays (seed 41001)
  reproduce the first twelve reviews of the freeze record `closure/horizon52_cycle.jsonl.gz` order for
  order and status for status; P0 cell 15 reproduces the isolation arm `closure/p0_arm_router_cycle.json`
  review by review (state, candidate sets, selection, status, recovery mode, feasibility, chosen plan,
  final P0 purchases), every review protection-owned. PASS at `d7f76cf`.
* B alone on the freeze benchmark after the typing edits: costs and orders bit-identical to
  `closure/horizon52_cycle_B.jsonl.gz` (`closure/identity_typing.jsonl.gz`).
* P1 invariants: 720 / 720, byte-identical checks to the freeze record.
* Python suite on the canonical tree: 1,810 passed, 2 skipped (1,532 unit at the freeze plus the
  integration suites and 12 new tests); 71 P1 principle tests pass.

## Lineages (git ancestry, `origin` fetched 2026-09-10)

Common base `11f06e9` on `main`. Optimizer lineage: `main@11f06e9` -> #16 -> #17 -> #18 -> #19
(`adaptive/decision-engine@2820a69`) -> #20 -> #21 -> #23 -> #24 -> #25 -> #30 -> #31 -> #32 -> #33 ->
#35 -> #36 -> #37 -> #38 (`e8e2398`) -> P0 `2e30721` (+9 local) -> P1 `12db66c` (+26 local) -> `56e998f`;
every step contains its parent completely. Site lineage: `adaptive/decision-engine@c941c64` =
`2820a69` + 12 web commits (Vercel production per `81f141e` and the session record). `main`: five
commits (#14, #15, #26, #27, #28). Network Twin: `adaptive` + 3 web commits (PR #39). The canonical
branch now contains all three lineages; PR #39 is not merged.

## Integrated product surfaces

* API (`api/main.py`, title "Zaad Supply API", health service `zaad-api`): canonical planning engine
  = the frozen P1 optimizer under `/api/zaad/network` (`/plan`, `/shadow`, `/jobs`, and the workspace
  path `/request/from-workspace`, `/plan/from-workspace`); `/fmcg/plan` defaults to `mode=canonical`
  and serves the purchase-plan page from the same engine. Superseded engines (the first ZAAD engine
  under `/api/zaad`, the safe-selector modes of `/fmcg/plan`) are served only while legacy planners
  are enabled: dev by default, off in pilot / staging / prod unless `ZAAD_LEGACY_PLANNERS=1` (410 with
  the canonical pointer). No autonomous purchase order anywhere; approval stays with the operator.
* Customer-data path: operator files -> `api/routers/intake.py` (validated upload into the operator's
  own DuckDB vault, `stg_fmcg_*`) -> `zaad/full/workspace.py` (weekly normalisation, fitted supplier
  fill and lead with sample sizes and provenance, shipment observations, opening stock, open orders,
  promotions, pack structure and order-level economics) -> `zaad.full.contracts.Request` -> the frozen
  planner -> the purchase-plan rows. Verified on a synthetic, schema-realistic workspace: 192k raw rows
  become a 61 KB request for three SKUs (156 demand observations, 180 shipment observations, six open
  orders); 428k rows for the 150-SKU distributor. No raw table reaches the MILP.
* Web (`web/`): the site lineage (SEO, /how-it-works, homepage), the workspace (upload, data quality,
  purchase plan on the canonical engine, state, reports), the network workspace at `/zaad/network`;
  the first engine's page redirects and is kept at `/zaad/legacy`. Public surfaces say ZAAD.

## CI (workflow `.github/workflows/ci.yml` at `d7f76cf`; local run of every gate)

| gate | status on the canonical tree |
|---|---|
| pytest (unit + integration) | 1,810 passed, 2 skipped |
| ruff, canonical scope (all but `docs/`, `dashboard/`, `scripts/p1_*.py`) | clean |
| mypy (`optimization risk backtesting api ingestion domain adaptive zaad/full`) | clean, 135 files |
| bandit `-ll` on the canonical packages | 0 medium, 0 high |
| pip-audit | clean after refreshing urllib3, weasyprint (pin raised to 70.0 for CVE-2026-55073) and tornado locally; the ignore of PYSEC-2026-3412 remains documented |
| secret scan | gitleaks job added to CI; local bounded regex scan clean; `.env` untracked (`test_no_secrets_committed`) |
| zaad frozen regression + invariants + workspace smoke | PASS / 720 / OK |
| frontend typecheck, ESLint, production build, npm audit (prod) | clean / 0 errors, 21 warnings kept visible / builds / 0 vulnerabilities |
| Docker image build and smoke | defined in CI (health, fail-closed, no open legacy planner in prod); not run locally (no Docker on this machine) |

Remaining, documented debt: ruff in `docs/` evidence snippets, `dashboard/` (deprecated HarvestMind
Streamlit shell) and the frozen P1 diagnostic scripts; the 21 ESLint warnings (React 19
set-state-in-effect patterns in the site lineage, one `any`); the pip-audit ignore.

## Deprecated code paths (kept, not served by default)

`zaad/engine.py` and its bounded API `api/routers/zaad.py` (first engine), the safe-selector modes of
`api/routers/fmcg.py`, `optimization/` (HarvestMind-era LP / SP library still imported by the legacy
modes and `adaptive/`), `dashboard/` (Streamlit shell), `api/routers/planning.py` (`/run` deprecated).
Removal is a later step, after the legacy modes have no consumer (`docs/ZAAD_REPOSITORY_CONSOLIDATION_PLAN.md`).

## PR dispositions

| PR | disposition | safe to close after the canonical PR merges? |
|---|---|---|
| #16, #17, #18, #20, #21, #23, #24, #25, #30, #31, #33, #35, #36, #37 | SUPERSEDED (content contained in the canonical branch by ancestry) | yes |
| #32 holdout3 | HISTORICAL NEGATIVE RESULT / EVIDENCE ONLY (holdout failed; evidence contained) | yes, with a closing note pointing at the evidence |
| #38 V8 industry standard | SUPERSEDED (origin at `e8e2398`, nine commits behind the P0 freeze) | yes, after the push carries `2e30721` |
| #19 adaptive decision engine (site, Vercel production) | CANONICAL SITE SOURCE until Vercel is repointed; content merged | after Vercel tracks `main` or `zaad/canonical` |
| #39 Network Twin V1 | DEFERRED, untouched | no |

Dispositions executed 2026-09-10 after the merge of #40 (see "Release line closed"): the listed PRs are closed, no branch was deleted.

## Untouched

Validation7 and Validation8 (not present as directories), `docs/zaad_full/evidence/v4/holdout4` (frozen,
unrun), PR #39 / `claude/zaad-network-twin-v1`, Vercel, every other worktree. P2 NOT STARTED.


## Release gate status (2026-09-10, end of the release-engineering pass)

* Preflight at `3bbb07c`: branch `zaad/canonical`, clean tree, `12db66c` and `2e30721` ancestors;
  frozen regression re-run PASS (B, T, Q, A twelve-review identity; P0 cell 15 identity).
* Remote: `origin` has no `zaad/canonical`, no tags, and `claude/zaad-industry-standard-v8` at
  `e8e2398` (nine commits behind the P0 freeze); `main` at `865b701`, fully contained in the canonical
  branch (176 commits ahead, 0 behind). The token has push and workflow scope; branch protection is not
  available on the private plan.
* **Push authorization was not explicit in the session, so nothing was pushed, no PR was opened, no PR
  was closed, Vercel was not touched.** The exact commands are in
  `docs/ZAAD_POST_P1_INTEGRATION_CHECKLIST.md`; the PR body is `docs/ZAAD_CANONICAL_PR.md`.
* Every open PR head except #39 is an ancestor of `zaad/canonical` (re-verified).


## Remote release gate (2026-09-10, authorized pass)

Pushed and verified on origin: `claude/zaad-industry-standard-v8` -> `2e30721`, `claude/zaad-cycle-stock-p1`
-> `56e998f`, tags `p0-frozen`=`2e30721`, `p1-frozen-product`=`f7e1e62`, `p1-frozen`=`12db66c`,
`pre-canonical-integration`=`56e998f`, and `zaad/canonical`. Canonical PR: **#40**
(https://github.com/radalzubi/harvestmind/pull/40), `zaad/canonical` -> `main`, **merged 2026-09-10 11:57 UTC**
(merge commit `f7ff600`, no squash) from head `9a8d266` (= `7cf0431` + this ledger).

Remote CI on PR #40, job by job (the workflow of `.github/workflows/ci.yml`):

| run | head | pytest | ruff | mypy | security | secret scan | frozen regression | docker | frontend |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `653b86c` | cancelled by run 2 | pass | **fail** (highspy 1.15 alias) | pass | **fail** (403: pull-requests read) | **fail** (label variance on cell 15) | **fail** (compose needs the admin-key placeholder; image smoke itself passed) | pass |
| 2 | `1ca2eb9` | cancelled at the 30-min budget (an unbounded 60-SKU plan under coverage) | pass | pass | pass | **fail** (one historical presigned-URL key id) | pass | **pass** | pass |
| 3 | `4bc8c4a` | **fail**: 1,809 passed, 1 failed (`test_no_obvious_secrets_in_tracked_files` on the literal key id in `.gitleaks.toml`) | pass | pass | pass | pass | pass | pass | pass |
| 4 | `7cf0431`, `9a8d266` | not started (billing) | not started | not started | not started | not started | not started | not started | not started |
| 4 rerun ([34462761422](https://github.com/radalzubi/harvestmind/actions/runs/34462761422)) | `9a8d266` | **pass**: 1,810 passed, 2 skipped (36 min) | pass | pass | pass | pass | **pass** | **pass** | pass |

Run 4 (three attempts, and the push-triggered run on the same commit) did not schedule a single job:
GitHub annotated every job "The job was not started because recent account payments have failed or
your spending limit needs to be increased" (private repository; runs 1-3 consumed about 116
job-minutes). The owner restored Actions billing and raised the budget; the rerun of the latest PR
run (`gh run rerun 34462761422`, head `9a8d266`, identical code to `7cf0431`) scheduled every job and
every job passed. The stale "not started" check runs of the push-triggered run on the same commit were
left as they are (the pull-request run is the gate; the merge commit got its own run on `main`).

Docker on GitHub (runs 2 and 3, real evidence): the image builds from a clean checkout, the API imports
and starts, `/health` reports service `zaad-api` with `auth_enforced` true under `HARVESTMIND_ENV=prod`,
anonymous job listing is 401, the legacy demo endpoint is not open, and `compose.pilot.yml` validates.

Fixes made for CI (`1ca2eb9`, `4bc8c4a`, `7cf0431`; none touches optimizer behaviour): the deprecated
highspy status alias read defensively (`zaad/full/model.py`), `highspy>=1.14,<1.16` (decisions
reproduced on 1.14.0 locally and 1.15.1 on GitHub), the P0 anchor of the frozen regression applying the
recorded decision semantics (candidate-label variance under time limits reported, never accepted as a
decision change), `pull-requests: read` for gitleaks, the compose validation placeholder, a bounded
canonical purchase-plan test (`skus`, `max_solve_seconds` on `/fmcg/plan?mode=canonical`), a 45-minute
pytest budget, and the scoped gitleaks allowlist.

Frozen regression on GitHub (highspy 1.15.1, two-core runner): B, T, Q, A identical to the freeze record;
P0 cell 15 identical on state, candidate sets, status, recovery mode, feasible set and final purchases,
with three equal-plan label swaps reported as timeout variance.

CodeQL (`.github/workflows/codeql.yml`, added at `5895f18`, never run on `main`) fails on every run of
this repository at the analyze/upload step with "Resource not accessible by integration": code scanning
is not enabled for this private repository (the repository's security settings are empty and the
code-scanning API answers 403 "Code scanning is not enabled"). ENVIRONMENT DEFECT outside the
repository, not one of the release gates; no permission change can make the upload succeed on this
plan, so the workflow was left untouched. To use it: enable code scanning (GitHub Advanced Security)
or make the repository public, and add `actions: read` to its permissions as the action documents for
private repositories.

## Release line closed (2026-09-10)

* **Merge:** PR #40 merged with a merge commit, `main` = **`f7ff600`** (parents `865b701`, `9a8d266`).
  The tree of `main` is byte-identical to `9a8d266`; `2e30721`, `f7e1e62`, `12db66c`, `56e998f`,
  `3bbb07c` and `9a8d266` are ancestors of `main`; the four tags still point where they were pushed.
* **Post-merge verification:** the push-triggered run on `main`
  ([34474090176](https://github.com/radalzubi/harvestmind/actions/runs/34474090176)) passed every job
  (pytest 1,810 passed / 2 skipped in 36 min; ruff; mypy; bandit + pip-audit "No known vulnerabilities
  found"; gitleaks; frozen regression PASS on highspy 1.15.1 with the three equal-plan label swaps
  reported; Docker image smoke `{'status': 'ok', 'service': 'zaad-api', 'env': 'prod', 'auth_enforced':
  True}` with anonymous jobs 401 and the legacy demo closed, compose validated; frontend typecheck /
  lint 0 errors / build / npm audit 0 vulnerabilities). Locally on the `main` tree: the canonical API and
  workspace tests (12) pass; legacy planners are off outside dev; `/network` is absent (404 on the
  site); Network Twin's head `734fa49` is not an ancestor of `main`.
* **PR closures (executed, branches kept, nothing deleted, `delete_branch_on_merge` false):**
  #16, #17, #18, #20, #21, #23, #24, #25, #30, #31, #33, #35, #36, #37, #38 closed as superseded
  (each head re-verified as an ancestor of `main`); #32 closed with the historical-evidence note
  (holdout3 negative result, evidence only); #19 closed after the Vercel repoint. #39 (Network Twin)
  stays open and deferred. Dependabot opened #41-#51 (GitHub Actions, npm and pip bumps) on the merge;
  they are out of this release's scope and untouched (any solver-stack bump needs the frozen regression
  before acceptance; the ruff / TypeScript / ESLint majors need their own gate runs).
* **Vercel (authorized, done after the post-merge verification):** project `zaad` (team
  `rad-al-zubi-s-projects`, serves `zaadsupply.com`, root `web`) production branch changed from
  `adaptive/decision-engine` to **`main`** (the public project API does not expose the production
  branch, so the change was made in the dashboard: Settings -> Environments -> Production -> Branch
  Tracking); a production deployment of `main` at `f7ff600` was created through the deployments API
  (`dpl_AbNhZqenfZa51PC29C8dkenJja67`, READY, aliases `zaadsupply.com`, `www.zaadsupply.com`,
  `zaad-tau.vercel.app`). Live smoke: `/`, `/how-it-works`, `/overview`, `/upload` 200, `/network` 404.
  The project's only production variable is `NEXT_PUBLIC_API_URL` (unchanged). The API deployment is
  outside Vercel and outside this pass; its required posture is the handoff above (`HARVESTMIND_ENV=prod`,
  `HARVESTMIND_AUTH_REQUIRED=true`, `ZAAD_LEGACY_PLANNERS=0`, explicit CORS origins, admin key, persistent
  data root, positive rate limit). The second Vercel project `harvestmind` already tracked `main`.
* **Verdict:** ZAAD CANONICAL RELEASE LINE — PASS, P2 MAY BE BRANCHED. P2 has not been started; it
  branches from `main` (`f7ff600` or later). Nothing in this pass claims production-ready security.

## Production P0/P1 plumbing (2026-09-10, verified live)

The API deployment is separate from Vercel: Fly app `zaad-api` (`api.zaadsupply.com`, region fra, volume
`harvestmind_data`). After the canonical merge it was still running the 2026-09-05 image (service
`harvestmind-api`, no `/api/zaad/*` route), so the site on `main` could not reach the frozen optimizer.
The owner deployed `registry.fly.io/zaad-api:canonical-11f5459` (release v13) with the persistent
`ZAAD_JOB_STORE` / `ZAAD_SHADOW_LEDGER` paths and `ZAAD_LEGACY_PLANNERS=0` (volume snapshot taken first).

Live verification against `https://api.zaadsupply.com` (production `NEXT_PUBLIC_API_URL` of the Vercel
project `zaad`): `/health` = `zaad-api`, env `pilot`, `auth_enforced` true, rate limit 60; 91 OpenAPI paths
including every `/api/zaad/network/*` route; anonymous `/fmcg/status`, `/api/zaad/network/jobs`,
`request/from-workspace` = 401; `/api/zaad/demo`, `/fmcg/plan?mode=incumbent`, `/api/zaad/plan` = 410
with the canonical pointer; CORS preflight allows `https://zaadsupply.com` and `https://www.zaadsupply.com`
and refuses a foreign origin; the site sends `Authorization: Bearer`. Bounded synthetic smoke on a
self-serve workspace (`op_b9bbe700`, SYNTHETIC CALIBRATED sample, no customer data): `request/from-workspace`
for two SKUs builds `zaad.network.v2` with the leakage guard and fitted provenance (1 s);
`plan/from-workspace` with `max_solve_seconds=5` returns `engine = zaad.full frozen P1`,
`mode_run = canonical_p1`, `planner_owner = PROTECTION_RECOVERY`, `solver_status = RETAIN_INCUMBENT`,
`approval_required = true`, `executable_purchase_order = false` (25 s); `/fmcg/plan?mode=canonical` the
same (36 s). The only frontend callers of the old engine are the explicit `/zaad/legacy` page and the
`(legacy)`-labelled modes of the `/fmcg` selector, which answer 410 in production; no normal route falls
back silently. Fly logs after the deploy: one health-check miss inside the start-up grace, the old
process's cancellation traceback, then "Application startup complete"; no 5xx during the smoke.

**PRODUCTION P0/P1 PLUMBING — VERIFIED.**

## P2 multi-echelon / network optimization (2026-09-10, branch `claude/zaad-meio-p2`, worktree `harvestmind-p2`, parent `11f5459`)

Not merged, not pushed. Evidence in `docs/zaad_full/evidence/p2/` (architecture decision, development
record, pre-registration with its dated correction, authoritative results, invariants, adversarial review,
scalability, P0 / P1 isolation, closeout). The frozen core was found to be one joint network MILP already;
P2 adds the network layer `zaad/meio` (topology, reachability, router, accounting, explanations, network
policies and baselines, fixtures, benchmark, workspace adapter with migration 016, API `network=true`,
interactive bounds) and default-off / telemetry hooks in the frozen files (demand correlation, lane packs
and dispatch fees, incumbent transfers, replay registry, settlement flows, network continuation). Frozen
regression identical throughout; six-cell P0 isolation decision-identical (cell 108 on an idle machine; cell 21 identical to the frozen
code's own replay, its divergence from the record being documented run-to-run variability). Authoritative benchmark: 20 / 20
valid fixtures pass every economic, service and structural gate, 18 / 18 network principles, 20 / 20
invariants, adversarial review clean, full suite 1,838 passed. **Verdict: P2 CORE ARCHITECTURE BUILT —
FREEZE BLOCKED** on one pre-registered gate: the runtime maximum per review (180 s) is exceeded on two of
344 reviews (M 257 s, O 315 s: three candidate classes at the declared per-solve budget with six to eight
worlds); p50 9.7 s and p95 87 s pass. See `P2_CLOSEOUT.md` for the blocker and the decision it needs.

## P2 performance pass (2026-09-10, branch `claude/zaad-meio-p2`, code `cab3849`)

Not merged, not pushed. Evidence in `docs/zaad_full/evidence/p2/perf/` (diagnosis written before any
change, development log, dated corrective plan, re-run results, architecture note, profiles, gate
logs). The original runtime failure stands as recorded (`P2_RESULTS.md`: M 257 s, O 315 s). Profiling
the two failing reviews on their exact snapshots showed 69% of the wall in the warm-start completion
forfeiting its cap and the rest in solves whose first incumbent took 10-31 s, because 95% of the
binaries were FEFO indicators between cohorts that all outlive a 12-period horizon (big-M 1e6). One
exact model change (`zaad/full/model.py`, `FEFO_SYMMETRY_ELIMINATION`: no FEFO indicator between two
cohorts that both outlive the horizon and the latest schedulable transfer arrival; network requests
only, the single-node P1 formulation verbatim) removes 95% of the binaries; every candidate then solves
at the root node with identical objectives. Authoritative set re-run unchanged (`p2_authoritative_perf`):
**p50 0.5 s, p95 6.6 s, max 14.6 s** (gate 60 / 120 / 180), 0 time-limited solves, 20 / 20 fixtures,
18 / 18 principles, 20 / 20 invariants, adversarial clean; P1 B / T / Q / A and the P0 six-cell set
(120 / 120 reviews) decision-identical; full suite 1,843 passed. Every decision difference from the
pre-performance record is a tie broken differently (objective equality proved on the snapshot) or the
one review whose frozen plan was time-limited. **Verdict: P2 MULTI-ECHELON / NETWORK OPTIMIZATION —
PASS AND FROZEN** (see `perf/P2_PERF_RESULTS.md`, `P2_CLOSEOUT.md`; frozen SHA recorded there).

## P2 release line (2026-09-10 / 11, authorized)

* **Preflight**: `claude/zaad-meio-p2` at `fa615ff`, clean; `origin/main` at `11f5459` had not advanced
  except by PR #53 (docs only, the production-plumbing record), merged first as `6d2934e`; the P2
  branch then received one docs-only merge of `main` (`cef7a72`, ledger sections kept side by side).
* **Freeze tags** (published for the first time, verified on origin): `p2-frozen-product` = `cab3849`
  (the frozen P2 runtime / code), `p2-frozen` = `fa615ff` (the complete freeze record with evidence
  and closeout). The local pre-release tag already pointed at `fa615ff`; the product tag was created
  before publication. Ancestry: `2e30721`, `f7e1e62`, `12db66c`, `cab3849` are ancestors of `fa615ff`.
* **PR #54** (`claude/zaad-meio-p2` -> `main`, "ZAAD P2: multi-echelon network optimization, performance
  closure, and freeze"). First CI run 34532888450: every gate green except pytest, cancelled at the
  45-minute job budget at 85% (1,845 tests; a 20-minute stretch inside the integration tests that does
  not reproduce locally on the same scipy 1.18.1 / highspy 1.15.1 stack, where the same files run in
  8 s). Release-only fix `89211b1`: pytest budget 90 minutes and `--durations=30`; no test and no
  optimizer code changed. Second run 34537444878 green on every job: pytest 1,843 passed, 2 skipped
  (71:50 on the runner; slowest tests the two network workspace plans at 1,048 s and 523 s and the
  frozen economic-horizon test at 420 s), ruff, mypy, security, gitleaks, frozen regression, Docker
  build, frontend. CodeQL: the documented "code scanning is not enabled" environment failure, unchanged.
* **Merge**: merge commit `9c4ece7` at 2026-09-10T23:40:25Z (pre-merge `main` `6d2934e`, PR head
  `89211b1`). Every freeze SHA is an ancestor of `main`. Post-merge main CI 34543195400 green
  (pytest 1,843 passed, 2 skipped in 55:45; frozen regression green); local canonical regression on
  `9c4ece7` PASS (B / T / Q / A twelve-review identity, P0 cell 15).
* **Fly**: `zaad-api` release **v14**, image `registry.fly.io/zaad-api:canonical-9c4ece7`, rolling
  update of the existing machine `0804e0dfd1e948` (fra), volume `harvestmind_data` untouched, secrets
  untouched (`ZAAD_LEGACY_PLANNERS=0`, `ZAAD_JOB_STORE`, `ZAAD_SHADOW_LEDGER` persistent). Start-up:
  the old process's cancellation traceback, one health-check miss inside the grace period, then
  "Application startup complete"; no 5xx during the smoke.
* **Bounded production smoke** (`https://api.zaadsupply.com`): `/health` = `zaad-api`, env `pilot`,
  `auth_enforced` true; 11 `/api/zaad/network/*` routes present; `/api/zaad/demo` and `/api/zaad/plan`
  410 with the canonical pointer; anonymous `/fmcg/status`, `/api/zaad/network/jobs`,
  `request/from-workspace` and `/fmcg/plan?mode=incumbent` 401; CORS preflight allows
  `https://zaadsupply.com` and `https://www.zaadsupply.com`, refuses a foreign origin (400). P1 path on
  a fresh self-serve synthetic workspace (`op_47bdde74`, `load-sample-fmcg`, two SKUs):
  `plan/from-workspace` -> `engine = zaad.full frozen P1`, `mode_run = canonical_p1`,
  `planner_owner = PROTECTION_RECOVERY`, `solver_status = RETAIN_INCUMBENT`, `approval_required = true`,
  `executable_purchase_order = false` (23.5 s). P2 path (`op_be0813f3`, payload `/api/zaad/network/plan`,
  one SKU, one central and two branches, two lanes, horizon 12, three worlds, 5 s budget): HTTP 200 in
  1.8 s, `zaad.network.2.0`, state NO_ACTION, owner PURCHASING_ECONOMICS, selected
  `operator_rule:network:rop`, status RETAIN_INCUMBENT, period-zero purchase 39.2 and transfers 68.1 /
  76.5, branch service .990 / .982, economics block, network block with explanations ("no change to
  your current network policy this period"), provenance fingerprint, `approval_required = true`,
  `executable_purchase_order = false`. Oversized payload (15 locations) -> 413 with the interactive
  bounds. One observation outside P2's scope: a whole-workspace `/fmcg/plan?mode=canonical` call without a SKU subset (150 synthetic SKUs) did not return inside a 400 s client window and left no error, traceback or 5xx in the logs (health stayed 200); the interactive canonical route is meant to be called with a SKU subset, as the plumbing smoke did (36 s), and the whole-workspace case belongs to the asynchronous job path.
* **Frontend**: `/`, `/overview`, `/upload`, `/fmcg`, `/state`, `/access` on `https://zaadsupply.com`
  answer 200 before and after the API release (unchanged site; the P2 fields are available on the
  backend for the later dashboard / Network Twin phases).
* **Untouched**: Validation7, Validation8, holdout4 (unrun, unread); Network Twin PR #39 open and
  deferred; Dependabot #41-#51 untouched (no solver-stack bump); sector physics, P3, dashboard and
  website uplift not started.
* **Verdict: ZAAD P2 RELEASE LINE — PASS** (final `main` `9c4ece7`, Fly `zaad-api` v14
  `canonical-9c4ece7`). Next authorized build: Three-Sector Physics Engine (commercial goods,
  produce, meat & seafood) — not started.

## Three-sector physics engine (2026-09-11, branch `claude/zaad-sector-physics`, worktree `harvestmind-sectors`, parent `ea1ed3a`)

Not merged, not pushed, not deployed. Evidence in `docs/zaad_full/evidence/sectors/` (capability audit,
architecture, dated fixture specification, development log, authoritative results, performance record,
invariants, closeout, gate logs). One engine: `zaad/sectors` declares per-SKU operating physics
(COMMERCIAL / PRODUCE / MEAT_SEAFOOD; storage state, age at receipt, minimum remaining life at receipt
and at sale, shipment weight) with provenance, plus optional storage states on locations and lanes;
the frozen model, settlement, continuation, rule projection and report consult one resolved view
behind `physics is not None` (a legacy request resolves to None). Migration 017 (additive), both
workspace adapters, `sector_mode` API parameter, 422 on malformed physics. Authoritative synthetic
run: 26 / 26 pre-registered fixtures (C1-C7, P1-P8, M1-M8, X1-X3) pass; 19 / 19 invariants; runtime
p50 1.4 s / p95 8.4 s / max 59.5 s, 0 time-limited solves. Frozen behaviour: P0 six-cell 120 / 120,
P1 B / T / Q / A identity and 720 / 720 invariants, P2 matrix 20 / 20 with 344 / 344 reviews
decision-identical to the release record. Full suite 1,865 passed, 2 skipped. **Verdict: THREE-SECTOR
PHYSICS ENGINE — PASS AND FROZEN LOCALLY** (product `43d769f`, local tags `sector-physics-frozen-product`
and `sector-physics-frozen`; ENGINEERING VALIDATED, not real-data validated).

## Three-sector physics release line (2026-09-11, authorized)

* **Preflight**: `claude/zaad-sector-physics` at `4f358f7`, clean; `origin/main` still `ea1ed3a` (no
  advancement). Ancestry: `43d769f` in `4f358f7`; every P0 / P1 / P2 freeze SHA in the sector freeze.
* **Freeze tags published exactly** (verified on origin, never moved): `sector-physics-frozen-product`
  = `43d769f`, `sector-physics-frozen` = `4f358f7`.
* **PR #56** ("ZAAD: Three-Sector Physics Engine — commercial, produce, meat & seafood", base
  `ea1ed3a`). First exhaustive run 34573264612: every gate green except pytest, cancelled by the
  runner at the 90-minute job budget at 92% (the same suite is 4:42 locally; the P2 matrix is
  decision-identical under the sector code: runner overhead, not a model regression). CI-only fix
  `be12202`: the identical 1,867 collected tests run as three parallel shards (integration, unit
  without the zaad files, zaad unit files); no timeout widened, no test changed. Run 34580683633
  green on every job: pytest 275 + 1,139 + 451 = **1,865 passed, 2 skipped** (unit-zaad shard 72 min
  on the runner), ruff, mypy, security (bandit, pip-audit), gitleaks, frozen regression, Docker
  build, frontend. CodeQL: the documented "code scanning is not enabled" environment failure.
* **Merge**: `dca3d48` at 2026-09-11T09:59:16Z (pre-merge `main` `ea1ed3a`, head `be12202`). Merged
  tree identical to the tested candidate (`git diff be12202 dca3d48` empty); runtime directories
  identical to the product freeze `43d769f`. Bounded post-merge verification on the exact commit:
  ancestry, API import, migration 017 present, canonical regression PASS, sector and network API
  tests (the three 429s of one combined run were the per-minute recommendation rate limiter across
  files in one process; the file passes 4 / 4 alone). No second full CI (tree identity proven).
* **Fly v15** `canonical-dca3d48` (rolling, machine `0804e0dfd1e948`, volume and secrets untouched,
  `ZAAD_LEGACY_PLANNERS=0`). Production smoke: health, routes, legacy 410, anonymous 401, CORS,
  legacy P1 workspace path (two SKUs, 24 s), commercial / produce / meat & seafood payloads PASS;
  **the mixed-sector payload answered 500**: on the Fly machine a base-stock projection breached
  receiving capacity on a stress world, the candidate gate stored an infinite weighted service
  shortfall and the JSON encoder refused it (reproduced read-only on the machine; not reproducible
  on macOS: a solver tie broke differently). Release fix **PR #57** `3f57284` (`zaad/full/planner.py`:
  the report's weighted-service-shortfall fields carry None where the recovery ranking already did;
  gate decisions read the numeric value before serialisation and are unchanged; regression test).
  CI run 34588333043 green (1,866 passed, 2 skipped); merged as **`5ca3772`** at 11:15:36Z; merged
  tree identical to the tested head; runtime delta against `dca3d48` is that one file.
* **Fly v16** `registry.fly.io/zaad-api:canonical-5ca3772` (rolling, same machine, volume and secrets
  untouched). Smoke on v16: `/health` = `zaad-api`, env `pilot`, auth enforced; 11 network routes;
  `/api/zaad/demo` and `/api/zaad/plan` 410; anonymous protected calls 401; CORS allows zaadsupply.com
  and www, refuses a foreign origin; legacy workspace (`op_0a69199c`, no sector fields) builds
  (`sector_mode` null, no profiles) and plans on the frozen P1 path (`canonical_p1`,
  `approval_required` true, `executable_purchase_order` false, 24 s); the same workspace with
  `sector_mode=COMMERCIAL` carries a physics block with undeclared (neutral) profiles. Payload
  smokes, all HTTP 200, `approval_required` true, `executable_purchase_order` false: COMMERCIAL
  (case pack 12: purchase 48 = 4 x 12 with the operator-language explanation; 31 s), PRODUCE
  (age / sellable life: transfer cohort keeps expiry 4, "arrive with 3 periods of life, 2 of them
  sellable"; 2 s), MEAT_SEAFOOD (chilled, ambient south lane never used, reefer lane declared; 6 s),
  MIXED (commercial A with produce B: profiles isolated, A min life 0 / B min life 1, shared
  branches; 5 s). Malformed inputs 422 with clear messages: unknown sector mode, negative shelf
  life, minimum life above shelf life, invalid storage state, physics for an unknown SKU, declared
  value without provenance. Logs after the v16 start-up: 0 x 5xx, 0 tracebacks from the active
  process, no store / migration / auth errors (one health-check miss inside the grace period).
* **Migration 017**: additive, nullable, idempotent (`ADD COLUMN IF NOT EXISTS`, the pattern since 007);
  applied by the existing mechanism (`setup_db` at vault creation) to every vault created from v15 on;
  existing vaults keep their schema and load through the guarded adapters (legacy-neutral); no
  backfill. To declare physics on a pre-existing vault the operator runs the idempotent
  `scripts.setup_db.setup_db` on that vault's DuckDB file.
* **Frontend**: `/`, `/overview`, `/upload`, `/fmcg`, `/state`, `/access` answer 200 before and after.
* **Known observations (future performance work, not fixed here)**: C1 report-only service-frontier
  oracle up to ~59.5 s; two-SKU P1 workspace request ~24 s end to end on a 5 s solve budget; the
  synchronous 150-SKU whole-workspace canonical call exceeded 400 s (P2 release).
* **Untouched**: Validation7, Validation8, holdout4 (unrun, unread); Network Twin #39; P3-P6;
  dashboard and website uplift; Dependabot solver-stack bumps.
* **Verdict: ZAAD THREE-SECTOR PHYSICS RELEASE LINE — PASS** (final released runtime `5ca3772`, Fly
  `zaad-api` v16 `canonical-5ca3772`; ENGINEERING VALIDATED, not real-data validated). Next
  authorized build: P3 supplier / sourcing portfolio optimization — not started.

## Three-sector physics release bookkeeping (2026-09-11, lineage tags)

Three immutable markers describe the sector phase. They are distinct commits and are never moved.

| tag (on origin) | SHA | meaning |
|---|---|---|
| `sector-physics-frozen-product` | `43d769f` | original sector optimization / runtime semantics freeze, before release smoke |
| `sector-physics-frozen` | `4f358f7` | complete local engineering evidence freeze (fixtures, invariants, benchmark, closeout) |
| `sector-physics-release-runtime` | `5ca3772` | exact runtime deployed to Fly `zaad-api` v16 (`canonical-5ca3772`) after PR #57 |

`43d769f` freezes sector optimization semantics. `5ca3772` is the exact released runtime and contains
one post-freeze JSON-safe reporting correction (PR #57, `zaad/full/planner.py`) that does not alter
optimizer gate decisions: the report's weighted-service-shortfall fields carry None where a
stress-world settlement is physically unusable (the value the recovery ranking already used); the
gate reads the numeric value before serialisation. Evidence for that correction: canonical regression
PASS on the merged commit, the targeted regression test, exhaustive pre-merge CI green on the
identical tree (run 34588333043, 1,866 passed, 2 skipped), production mixed-sector smoke 200 on v16.
`43d769f` is therefore not byte-identical to production; v16 (`5ca3772`) is the authoritative released
runtime. Final `main` `4cc9f52` adds the docs-only release closeout after the released runtime.

Ancestry (verified): `43d769f` -> `4f358f7`; `43d769f` -> `5ca3772` (through `dca3d48`);
`5ca3772` -> `4cc9f52`; `2e30721`, `f7e1e62`, `12db66c`, `cab3849`, `fa615ff`, `9c4ece7` all in
`4cc9f52`. Original tags re-verified on origin at bookkeeping time: `43d769f` / `4f358f7`, unchanged.

GitHub Actions at bookkeeping time: the push runs on `main` for `5ca3772` (34593147827) and `4cc9f52`
(34593818699) and the docs PR #58 run did not start ("recent account payments have failed or your
spending limit needs to be increased"): REMOTE_CI_UNAVAILABLE — GITHUB ACTIONS BILLING. This is a
billing condition, not a code failure; the code line's evidence is the green pre-merge runs on
`be12202` and `3f57284`, whose trees equal the merged commits. Owner action: restore Actions billing
and rerun CI on `main`.

## P3 supplier / sourcing portfolio optimization (2026-09-11, branch `claude/zaad-sourcing-p3`, worktree `harvestmind-p3`, parent `main` `7bc4206`)

* **Audit first** (`evidence/p3/P3_EXISTING_CAPABILITIES.md`): the frozen engine already chooses among approved
  sources jointly (per-source purchase columns, capacity, MOQ, packs, supplier orders across SKUs, payment
  terms through the cash balance, shared resources, per-source fill / lead fitting, shared-domain supply
  shocks). No second optimizer, candidate class, supplier score or diversification rule was built.
* **P3 layer** (`zaad/sourcing`): a default-off `SourcingPortfolio` on the frozen request (risk groups with
  kind, correlation and provenance; declared share limits and committed units; declared switching /
  qualification costs; the operator's incumbent source mix). Hooks reached only when a portfolio is
  declared: model (exact zero-capability pruning, share rows, one first-stage switching binary), worlds
  (group factor from a salted generator, marginals preserved, frozen stream untouched), settlement
  (switching ledger line under ORDERING), rule projections (incumbent mix split, shared-resource fit),
  replay (an executed switch joins the mix), planner `report["sourcing"]` with operator-language reasons;
  approval required, no executable PO. Migration 018 (`stg_fmcg_sources`, four supplier risk columns);
  `sourcing` parameter on the workspace endpoints; interactive bounds (413) and 422 `sourcing_invalid`.
* **Evidence**: 30 / 30 pre-registered fixtures PASS (`p3_authoritative`; changes recorded in the spec and
  dev log), 34 / 34 invariants, 23 / 23 adversarial cases fail safely; runtime 480 reviews p50 0.66 s /
  p95 19.2 s / max 42.8 s, 0 time-limited; P0 six-cell arm `p3_sourcing` 120 / 120 decision-identical;
  canonical regression identical; P1 invariants no failures; P2 matrix under the P3 code 20 / 20, 18 / 18,
  344 / 344 decision-identical; sector matrix 26 / 26, 19 / 19 invariants, 402 / 416 identical with the 14
  differences confined to fixture P3_age_at_receipt: one documented correctness correction in
  physics-enabled historical replay (received perishable purchases keep their declared remaining life;
  live planner / settlement unchanged; legacy replays bit-identical), audited and causally proven in
  `evidence/sectors/corrections/` (2026-09-11 corrective pass); "sector physics remains frozen" is
  withdrawn in favour of that precise statement.
* **Frozen and local only**: product tag `p3-frozen-product`, evidence tag `p3-frozen` (see
  `evidence/p3/P3_CLOSEOUT.md` for the SHAs). Not pushed, not merged, not deployed. ENGINEERING
  VALIDATED, not real-data validated; no savings claimed.

## P3 supplier / sourcing portfolio release line (2026-09-11, authorized)

* **Remote CI prerequisite**: the last known state was REMOTE_CI_UNAVAILABLE (billing); one rerun of the
  main run on `7bc4206` (34605444241) started every job with steps and completed green, so the release
  proceeded.
* **Preflight**: `claude/zaad-sourcing-p3` at `fb91946`, clean; `origin/main` `7bc4206` (no advancement).
  Freeze integrity: `p3-frozen-product` = `9e496ed`, `p3-frozen` = `628d49f`, `p3-corrective-evidence` =
  `fb91946`; `9e496ed` in both; runtime directories identical between `9e496ed` and `fb91946` (the only
  file outside docs / tests is the P0 arm registration in `scripts/p1_p0_arms.py`). Branch and the three
  tags published exactly (verified on origin, never moved); `sector-physics-replay-correction` stays a
  local forensic marker.
* **PR #60** ("ZAAD P3: Supplier / Sourcing Portfolio Optimization", base `7bc4206`). First exhaustive run
  34626589387: every gate green except the unit-zaad pytest shard, cancelled by the runner at the 90-minute
  job budget while the docs-only main rerun competed for runners (the zaad unit files take 224 s locally).
  CI-only fix `326c010`: that shard split into two disjoint name ranges (`[a-r]` 323 tests, `[s-z]` 170
  tests; union = the 493 zaad unit tests exactly); no timeout widened, no test changed. Run 34635732278
  green on every job: pytest 275 + 1,139 + 322 + 170 = **1,906 passed, 2 skipped** (integration 14 min,
  unit-core 6 min, unit-zaad-a 48 min, unit-zaad-b 43 min), ruff, mypy, security (bandit, pip-audit),
  gitleaks, Docker build, frontend, frozen regression. CodeQL: the known "resource not accessible by
  integration" (code scanning not enabled) configuration failure.
* **Merge**: `0de6850` (pre-merge `main` `7bc4206`, head `326c010`, merge commit). Whole-tree diff against
  the tested head empty; runtime directories identical to the product freeze `9e496ed`. Bounded post-merge
  verification on the exact commit: ancestry, API and `zaad.sourcing` import, 33 sourcing / receipt-life
  tests, canonical regression PASS, migration 018 present. No second full CI (tree identity proven).
* **Migration 018**: additive, idempotent (`CREATE TABLE IF NOT EXISTS stg_fmcg_sources`, four
  `ADD COLUMN IF NOT EXISTS` supplier risk columns), no backfill, nothing inferred. Applied by the
  existing mechanism (`setup_db` at vault creation): the smoke vault created on v17 reports the source
  table present; a pre-P3 vault (`op_0a69199c`, inspected read-only on the machine) has no
  `stg_fmcg_sources` and keeps working through the legacy adapter (`sourcing=true` on such a vault warns
  and builds the frozen request). To declare P3 sourcing on a pre-existing vault the operator runs the
  idempotent `scripts.setup_db.setup_db` on that vault's DuckDB file (the API holds the vault lock while
  it serves the tenant; run it with the tenant idle).
* **Fly v17** image label `canonical-0de6850` on the `zaad-api` registry repository (rolling, machine `0804e0dfd1e948`, volume
  `harvestmind_data` untouched, the Fly configuration values left exactly as they were (names only verified), legacy planners still disabled, env `pilot`); health
  checks passing after the grace period, no restart loop.
* **Production smoke on v17** (`evidence/p3/release/production_smoke_v17.json`): `/health` = `zaad-api`,
  pilot, auth enforced; legacy `/api/zaad/demo` and `/api/zaad/plan` 410; anonymous protected calls 401;
  CORS allows zaadsupply.com and www, refuses a foreign origin. Self-serve workspace `op_38e4101e`
  (sample FMCG, 427,995 rows): legacy request has `sourcing` null (`requested` false); with `sourcing=true`
  and no declarations the block stays null and the request stays frozen; the P1 workspace plan runs on the
  canonical path with approval required. Payload smokes (all HTTP 200, `approval_required` true,
  `executable_purchase_order` false, economics reconciled, no unmapped ledger key): legacy no-P3 (no
  sourcing block); single source (allocation = the P1 commitment, share 1.0); two-source economics (B
  cheaper per unit, A cheaper landed after freight and terms: A retained, sentence present); capacity
  split (A at its 200 capacity, B 108, sum = commitment, sentence present); MOQ / MOV (B orders 1,333 >=
  MOQ 1,200 and MOV); packs (120 = 1 x 120-unit pallet); payment terms (declared 50 / 50 retained, not
  material); switching small (B unused: "starting to buy from it would cost 2,000"), switching large (B
  adopted, cost 300 charged once); shares (A at most 70 % and B at least 30 % honoured exactly);
  correlated risk (plant group listed with provenance on A and B, C independent; one source per period,
  no intra-period split); independent identical sources (period-level label ties, never a split within a
  period); PRODUCE (short-life B unused; age by source in the profile); MEAT_SEAFOOD (frozen source into a
  chilled-only destination rejected with the reason); network (P2 transfers 300 at period 0, source split
  P3, conservation exact); multi-SKU shared capacity (S1 lines 158 + 292 = 450 = the shared cap, S2 takes
  the overflow); shared MOV (combined S1 orders 650 + 655 units >= 5,000 MOV); age at receipt payload
  (profile `{src_A: 3}` on shelf life 6: "arrive with 3 of 6 periods of life"). Malformed inputs: unknown
  group member, unqualified source with a minimum share, negative capacity, minimum above maximum share,
  impossible aggregate shares, missing provenance, infinite price all 422; 11 sources on one pair 413
  before any model. Frontend `/`, `/overview`, `/upload`, `/fmcg`, `/state`, `/access` 200.
* **Age-at-receipt workspace check** (`evidence/p3/release/age_at_receipt_workspace_*`): a new produce
  workspace `op_a2b8b9d9` loaded through the intake upload with a SKU master declaring shelf life 42 days,
  age at receipt 21 days and sale minimum 7 days; the production adapter built `sku_physics`
  `age_at_receipt_periods` 3 on a 6-period shelf life (received life 3, not 6) and the plan's physics
  profile carried it; approval required, no executable order.
* **Logs after the smokes**: 0 x 5xx, 0 tracebacks, no store / migration / tenant / serialization error;
  one health-check miss inside the rolling-deploy grace; 59 x 200, 7 x 422, 3 x 401, 2 x 410, 1 x 413,
  1 x 400 (foreign CORS preflight).
* **Release-runtime tag**: `p3-release-runtime` = `0de6850` (on origin; identical runtime tree to
  `9e496ed`).
* **Known observations (future performance work, not fixed here)**: sector C1 frontier oracle ~60 s; the
  two-SKU P1 workspace call ~24 s on a 5 s budget; the synchronous 150-SKU whole-workspace call > 400 s;
  new: interactive P3 payloads with supplier-order MOV binaries across two SKUs run far slower on the Fly
  machine than locally (shared-MOV smoke 218 s, multi-SKU shared capacity 78 s, plant-group case 46 s,
  against 1-20 s locally); async jobs remain the path for such requests.
* **Untouched**: Validation7, Validation8, holdout4 (unrun, unread); Network Twin #39; P4-P6; dashboard
  and website uplift; Dependabot solver-stack bumps.
* **Verdict: ZAAD P3 SUPPLIER / SOURCING PORTFOLIO RELEASE LINE — PASS** (released runtime `0de6850`, Fly
  `zaad-api` v17 `canonical-0de6850`; ENGINEERING VALIDATED, not real-data validated; no savings claimed).
  Next authorized phase: P4 adaptive recourse — not started.

## P3 production performance closure (2026-09-11, branch `perf/p3-shared-mov-closure`, worktree `harvestmind-p3-perf`, parent `main` `1e712c9`)

* **Original release observation (kept, not erased)**: the P3 release smoke's shared-supplier-MOV case
  (`payload.shared_mov`: two SKUs, one supplier with a 5,000 MOV and a 150 fixed order cost, declared line
  capacity 1,000,000) measured **218.4 s** on Fly v17 (`0de6850`) against the declared 180 s interactive bound;
  functionally correct, performance blocked.
* **Exact workload**: snapshotted byte for byte (`evidence/p3/perf_closure/shared_mov_prod_snapshot.json`)
  with the multi-SKU capacity, plant-group, simple P3 and P2 network snapshots and the v17 reference results.
* **Root cause (measured, `P3_SHARED_MOV_PROFILE.md`)**: 96 % of the wall time inside HiGHS across 18 calls
  (12 distinct candidate / valuation models; no first-stage binary duplicated per world; nothing rebuilt
  twice). (1) The supplier-order linking rows used the declared capacity (1,000,000) as big-M, so the
  relaxation never priced the MOV or the fixed cost: base_stock 4.7 s / 1,214 nodes, oracles 84 nodes.
  (2) After the bound is tight, HiGHS's root restart doubles every remaining solve for the same optimum.
  (3) The 218 s itself was the request on a **throttled shared CPU** (guest counters: 518 s steal against
  271 s user time since boot); the exact request rerun on the unthrottled machine took 76.2 s with every
  candidate optimal and the same decision as locally. The frozen `depleted` indicators' big-M, heuristic
  effort, scaling, pricing, cut and LP-age settings were measured and are not drivers.
* **Correction** (`zaad/full/model.py`, PR #64 `5bbdefc` -> merge `61a3e75`): scoped to the P3
  shared-supplier-order class (`shared_supplier_orders`: a sourcing review whose supplier order links lines
  of more than one SKU). Inside it: `activation_bounds` (the exact undominated quantity per line and period
  as the coefficient of the `order` / `active` linking rows; purchase columns keep their capacity; guarded
  by salvage < landed cost, no bound under fixed plans or declared share rows, pack-lattice rounding),
  highspy with `mip_allow_restart` off, and explicit rejection of dominated warm-start seeds. Outside the
  class nothing changes. Two broader scopes were built, measured and withdrawn because they flipped
  tie representatives (equal-cost transfers, identical-price sources) through the selector's confirmation
  gates in E4 / R4 / T (`tie_evidence/`).
* **Exactness**: every candidate on the exact snapshot returns the identical objective, bound and purchase
  plan before and after; only equal-cost transfer allocations move (objective 25,408.1631 both).
* **Before / after**: local 17.55 s -> 12.8 s (solver 17.06 -> 12.3 s; base_stock 4.68 -> 0.15 s; every
  solve at or near one node). Fly: exact snapshot 218.4 s (v17 release smoke, throttled) / 76.2 s (v17 unthrottled rerun) -> **39.4 s** fresh and **37.8 s** after the sustained sequence on v18, every candidate optimal; multi-SKU capacity 77.6 -> 9.5 s; plant group 45.6 -> 14.5 s; simple P3 1.8 s; P2 network 1.6 s.
* **Regression on the final code**: P3 30 / 30, 34 / 34, 23 / 23, 2,273 / 2,304 replay reviews identical
  to `p3_corrective` (the 31 others all C6: one equal-cost transfer tie at review 0 and its cascade,
  review-0 candidates identical on both seeds); P2 20 / 20, 18 / 18, invariants PASS, 1,720 / 1,720
  identical; sector 26 / 26, 19 / 19, ZAAD reviews 416 / 416 identical (the `echelon_base_stock`
  comparator's 19 differing reviews reproduce on the unchanged released code: pre-existing comparator
  variability, recorded); P1 canonical B / T / Q / A identity, invariants 60 / 0; P0 six-cell arm
  `p3_perf_closure` 118 / 120 under contention, quiet rerun of cells 21 and 108 50 / 50 -> 120 / 120.
  New structural test `tests/unit/test_zaad_activation_bounds.py` (no wall clock).
* **Remote CI**: PR #64 run 34657879427 green on every executable job: pytest 275 + 1,139 + 328 + 170 = **1,912 passed, 2 skipped** (the six new structural tests included), ruff, mypy, security (bandit, pip-audit), gitleaks, Docker build, frontend, frozen regression; CodeQL: the known configuration failure only.
* **Merge / tree identity**: PR #64 head `5bbdefc`, pre-merge `main` `1e712c9`, merge commit `61a3e75`; whole-tree diff against the tested head empty, so no second full CI.
* **Deployment**: `fly deploy -a zaad-api --image-label canonical-61a3e75 --strategy rolling --yes` from `harvestmind-main` at `61a3e75`: release v18, machine `0804e0dfd1e948` (fra, shared-cpu-2x, 2 GB), volume `harvestmind_data`, secrets and configuration identical before and after (listed), health `ok`, auth enforced; the deploy log's only traceback is uvicorn's SIGINT shutdown of the previous VM.
* **Production re-run**: exact shared-MOV snapshot **39.4 s** (fresh) and **37.8 s** (after the four other snapshots), candidates incumbent 0.1 / base_stock 0.5 / deterministic 6.8 / stochastic 10.7 / cadence_2 5.5 / cadence_4 3.7 s, all OPTIMAL; same purchase commitment, source split (A 0.991 / 0.009, B 0.990 / 0.010), MOV satisfaction, objective and service as the local run and the v17 unthrottled rerun; `approval_required` true, `executable_purchase_order` false on every response; guest steal over the whole sequence 130 jiffies against 9,924 user (unthrottled numbers). Primary gate < 180 s met with a 4.6x margin; the residual host-throttling risk (12-31x observed at release) is recorded, not hidden.
* **Log review**: 0 x 5xx, 0 request tracebacks, 0 timeouts, 0 OOM, 0 store / serialization errors; 41 x 200 in the window including the six plan calls (`evidence/p3/perf_closure/fly_logs_after_rerun.txt`).
* **Performance-closure tag**: `p3-performance-closure-runtime` -> `61a3e75`; `p3-release-runtime` stays
  on `0de6850` (the original P3 released runtime), never moved.
* **Recorded, not fixed**: the same loose big-M under the P1 shared-order class (fixture T) and the
  single-SKU MOV / MOQ class (E4, S4); the `echelon_base_stock` comparator's run-to-run variability;
  the shared-CPU steal on the production machine (a performance-CPU machine or the async job path remain
  the defences when the host throttles); sector C1 ~60 s, P1 workspace ~24 s, 150-SKU > 400 s unchanged.
* **Untouched**: Validation7, Validation8, holdout4; Network Twin #39; P4-P6; dashboard and website
  uplift; Dependabot solver-stack bumps.
* **Verdict**: **ZAAD P3 PRODUCTION PERFORMANCE CLOSURE — PASS**; P3 release line fully closed (released runtime `0de6850`, performance-closure runtime `61a3e75`, Fly v18); ENGINEERING VALIDATED, not real-data validated; no savings claimed. Next authorized phase: P4 adaptive recourse — not started.

## P4 adaptive recourse release line (2026-09-12, authorized; branch `release/zaad-p4-adaptive-recourse`, worktree `harvestmind-p4rel`, base `main` `b24fd02`)

* Local engineering freeze `d8cdad5` (`p4-frozen-product`) / evidence `7059379` (`p4-frozen`), published unmoved. Main since the P4 base `ebcd1d0`: seven docs files, no runtime file.
* Release audit (`evidence/p4/P4_RELEASE_AUDIT.md`): A PI semantics corrected (bound only when OPTIMAL; time-limited PI = feasible cost, excluded from ordering; solver bound apart; verdicts distinguish no-comparator / time-limited-adaptive), B nearest-signature lookup removed (exact or REPLAN_REQUIRED with the static commitments as declared fallback, reported), C jobs safety verified (no change), D historical P3 wording (2,273 / 2,304 + 31 ties vs 2,304 / 2,304 P4-disabled current baseline) fixed. 13 pre-existing lint findings in the P4 scripts / tests fixed.
* Gates on the candidate: P4 28 / 28, 27 / 27, 25 / 25, 30-cell matrix; P3 snapshot identical 12.2 s; P1 identity + 60 invariants; P2 20 / 20, 18 / 18, 1,720 / 1,720; sector 26 / 26, 19 / 19, 416 / 416; P3 30 / 30, 34 / 34, 23 / 23, 2,304 / 2,304; P0 120 / 120 (one pass); migration 019 audited on fresh and populated pre-019 vaults; full suite 1,946 passed / 2 skipped.
* PR #67, tested head `0305e6a`, CI run 34675377987 green (1,946 passed on 4 shards; CodeQL environment defect unchanged); merged `8c813ac` (tree `e1e1f2d` identical to the tested head, no post-merge rerun).
* Fly `zaad-api` v20 `canonical-8c813ac` (v19 superseded: built from a worktree with stray untracked Finder duplicates; v20 from a clean detached checkout), machine / volume / secrets / env unchanged. Smokes A-S PASS as recorded in `evidence/p4/P4_RELEASE_CLOSEOUT.md`; N (shared-order recourse through `/jobs`) safe but TIMEOUT under 6x host steal (infrastructure residual, scope stated). Logs clean.
* Tag `p4-release-runtime` = `8c813ac`. Historical tags immutable (verified peeled on origin).
* VERDICT: ZAAD P4 ADAPTIVE RECOURSE — RELEASED AND CLOSED. ENGINEERING VALIDATED, NOT REAL-DATA VALIDATED. Next authorized phase: P5 — ATP / scarce-supply allocation (not started).

## P4 production performance closure (2026-09-12, branch `perf/p4-recourse-performance-closure`, worktree `harvestmind-p4-perf`, parent `main` `adf45e4`) — TRACK A of the parallel stage

* Diagnosis before any change (`evidence/p4/perf_closure/P4_PERF_DIAGNOSIS.md`, harness `scripts/p4_perf_profile.py`, 35 cells with HiGHS logs): the heavy cost is the unseeded adaptive tree solve (shared-order 12 worlds: 78 s time-limited incumbent dearer than the static optimum; produce: FEFO indicators, rejected warm completion). One exact change adopted: warm-start the adaptive tree solve from the static comparator (planner + `policy.compare`); rejected: indicator big-M tightening (invalid harness bound on produce; no gain on shared order), PI seeding, decomposition.
* Before / after: shared order 12 worlds 177 -> 138 s (adaptive 39 s OPTIMAL, verdict corrected), 8 worlds 60 -> 55 s, produce 6 / 8 worlds 41 / 60 -> 36 / 54 s, S1 adaptive time-limited -> OPTIMAL 10 s, interactive classes unchanged, 16-world shared order unchanged; no gate changed or recommended.
* Gates: P3 snapshot identical, P1 identity + 60, P2 20 / 20 + 18 / 18 + 1,720 / 1,720, sector 26 / 26 + 19 / 19 + 416 / 416, P3 30 / 30 + 34 / 34 + 23 / 23 + 2,304 / 2,304, P0 120 / 120 (one pass), P4 28 / 28 (objectives identical) + 27 / 27 + 25 / 25, full suite 1,946 / 2.
* PR #69 tested head `a9b2b92`, CI 34696879480 green; merged `6b58764` (tree identical); Fly v21 `canonical-6b58764` from a clean checkout; production benchmark: interactive 3.1 / 3.7 / 3.4 s, produce 67 s (steal 0.02), shared-order job TIMEOUT under 3.2x steal (infrastructure residual unchanged); logs clean; tag `p4-performance-closure-runtime` = `6b58764`, `p4-release-runtime` unmoved.
* VERDICT: ZAAD P4 PRODUCTION PERFORMANCE CLOSURE — PASS.

## P5 ATP / scarce-supply allocation — parallel-phase isolated engineering (2026-09-12, branch `claude/zaad-atp-p5`, worktree `harvestmind-p5`) — TRACK B

* Audit `docs/zaad_full/p5/P5_EXISTING_CAPABILITIES.md`, architecture `P5_ARCHITECTURE.md`, pre-registration `P5_PREREGISTRATION.md` (fixtures A-V, 20 invariants, 16 adversarial), dev log. Isolated package `zaad/atp` (contracts with provenance, ATP ladder, incumbent policies, exact MILP via scipy HiGHS, shared-ledger economics, validation, report, fixtures, adapter), migration 020, `Request.atp` default None (identity proven), endpoint `POST /api/zaad/atp/promise` behind `ZAAD_ATP_ENABLED=1`. Results: 24 / 24 fixtures, 16 / 16 adversarial, 9 tests, ruff / mypy / bandit clean. Commits `f9d0251` -> rebased `ae7001a` + `149fb5f` on the TRACK A main; no shared-core file touched; not pushed, not frozen, not released. Next: shared-core integration (separate authorization).

## P5 ATP / scarce-supply allocation — shared-core integration engineered (2026-09-12, branch `claude/zaad-atp-p5`), NOT released

* Isolated baseline tag `p5-isolated-baseline` = `660e5fc` (pushed; re-run from that SHA clean). Integration on top: `P5_INTEGRATION.md` (state contract: envelope, P0 overlay not a reservation, firm / non-firm inbound, direct vs alternative ship-from, PROPOSED reservations; ledger audit with owners, no double charge), planner hook after the frozen report (`zaad/full/planner.py`), workspace flag (`atp=True`, migration 020 adapter), API gate (`ZAAD_ATP_ENABLED`; 422 `atp_disabled` / 413 / 403). Evidence `docs/zaad_full/evidence/p5/integration/`: I01-I20 20 / 20 (I20 identical to the pre-P5 runtime `6b58764`), isolated 24 / 24, adversarial 17 / 17, invariants, profile, frozen regression gates, migration and API audits. `zaad/full/model.py`, P3 rows, P4 node indexing, scenario draws, tolerances, holdouts, historical tags: untouched. Next: P5 release audit under its own authorization; no deployment.

## P5 ATP / scarce-supply allocation — release audit (2026-09-12, branch `release/p5-atp-release-audit` from `17d2d74`)

* Economics: lost-sale basis corrected to the lost contribution (`selling_price - asset_value`, the frozen model's allocation-ranking basis; declared line / class margins override; gross selling price reported as information; ledger key `lost_contribution`) - a P5 semantic correction, no verdict changed on the 24 + 20 matrices, R01-R03 pre-registered and passing. SLA / class shortage penalty: distinct terms with a fail-closed `shortage_penalty_basis` (ADDITIONAL_TO_SERVICE_SLA with a reference and CONTRACT / OPERATOR_DECLARED provenance, or REPLACES_SERVICE_SLA), migration 021. P4 plumbing: `plan/from-workspace` forwards every phase flag by keyword. Evidence `docs/zaad_full/evidence/p5/release_audit/` (R01-R18 18 / 18 with runs 1-2 preserved, matrices, adversarial 18 / 18, profile, migration and API audits, frozen chain). Release: PR #72 merged as `main` `2fc7b50` (tested head `e33e027`, tree-identical; product freeze `p5-frozen-product` = `eacf3c3`, evidence freeze `p5-frozen` = `6919379`), Fly `zaad-api` v22 `canonical-2fc7b50` from a clean detached checkout, production smoke and logs clean, tag **`p5-release-runtime`** = `2fc7b50`. ZAAD P5 RELEASE AUDIT — PASS. Next authorized phase: none started (P6 not started).

## P4B V1 open PO / commitment intervention — IMPLEMENTED (2026-09-13, branch `claude/zaad-commitments-p4b` from `5dc87b4`), NOT released

* Design gate PR #74 (BUILD, V1). Implementation on the released P0 / P1 amendment columns: KEEP incumbent (base-stock proxy keeps when options are declared), bounded refund / credit (`credit_per_unit <= prepaid x deposit_refundable_fraction`; one guarded line in the model and in the settlement), fee keys and credit mapped to ORDERING, `zaad/commitments/` (windows, irreversibility ladder, operator block, `NO MATERIAL COMMITMENT IMPROVEMENT AVAILABLE`), migration 022, workspace `commitments=true`. Evidence `docs/zaad_full/evidence/p4b/`: fixtures 21 / 21 (runs 1-4 preserved), invariants, adversarial 16 / 16, profile, frozen chain green (P3 snapshot identical, P1 720, P2 1,720 / 1,720, sector 416 / 416, P3 2,304 / 2,304, P0 120 / 120), no-declaration identity against `2fc7b50`, suite 1,973. Untouched: P0-P5 semantics, P4 node map, P3 formulation, probabilities, tolerances, physics, holdouts, historical tags. Next: P4B release audit under its own authorization; no deployment; V2 not started.

## P4B V1 open PO / commitment intervention — RELEASE AUDIT (2026-09-13, branch `release/p4b-v1-release-audit` from PR #75 head `aacb7b9`)

* Authoritative record `docs/zaad_full/evidence/p4b/release_audit/P4B_RELEASE_AUDIT.md`. Six corrections, smallest scope each: R1 adapter normalisation boundary (`commitments:` refusals for stage / action / provenance / numbers / duplicates; case normalised, nothing mapped to a neighbour); R2 option-set bounds (`INTERACTIVE_LIMITS` 12 per order / 200 non-keep; 413 on `/plan`, four times on `/jobs`); R3 split floor as a sum of clipped cancel caps + settlement floor check (guarded by a positive floor); R4 credit on cancel options only; R5 block 1.1 with `commitment_action` / `commitment_verdict` / `commitment_value_vs_keep` (0 when every order is KEEP) / `overall_plan_status` / `plan_changes_outside_commitments` / `reading`; R6 a pre-existing production defect (numpy bool in `service_reliability`, `/plan` 500 on `2fc7b50`, request id `req-b379888a10da`) cast to `bool`.
* Frozen decisions of record: fixture re-registrations classified VALID FIXTURE REPAIR with causal evidence (`f06_boundary_scan.log`); the released multi-dimensional materiality standard (cost, carried inventory, service) governs commitment recommendations unchanged (E1a); refunds are cancel-only and bounded by `prepaid x deposit_refundable_fraction`; under split the cancel caps must sum inside the floor.
* Validation on the audit product: release-audit cases 35 / 35, fixtures 21 / 21 (F00 identical to `2fc7b50`), adversarial 16 / 16, invariants, profile structurally identical (850 / 300 / 122 nodes), suite 1,979 passed / 2 skipped, ruff / mypy / bandit clean, frozen chain P3 snapshot identical (18 HiGHS calls), P1 canonical PASS + invariants 0 failures, P2 1,720 / 1,720 (15 load-time-limit reviews rerun quiet: 280 / 280), sector 416 / 416, P3 2,304 / 2,304, P0 arm 120 / 120.
* Freeze: `p4b-v1-frozen-product` = `28c1fa7`, `p4b-v1-frozen` = tag `p4b-v1-frozen`. Release: CI run 34774980685 green (12 / 12), PR #76 merged as `main` `1851f40` (tree = tested head), Fly `zaad-api` v23 `canonical-1851f40` from a clean detached checkout, production smoke 12 / 12 (the pre-existing `/plan` 500 on the no-declaration state is gone), logs clean, tag `p4b-v1-release-runtime` = `1851f40`. PR #75 is marked merged by GitHub (its head `aacb7b9` is an ancestor of the merge commit through the release branch); it was never merged independently.


## ZAAD Operating Product V1 + V2 — audited, corrected, built, merged and deployed; production plan path BLOCKED (2026-09-15, branch `feat/zaad-operating-product-v1`, PR #81)

* V1 (Opus handoff `3333b0e`) independently audited by reproduction (`docs/zaad_full/FABLE_V1_AUDIT.md`): two blockers (DuckDB attach race → one anchor connection per vault, checkpointed; jobs orphaned by a restart → owner / lease / heartbeat, `ABANDONED`, adoption), seven highs (evaluation record-first with purposes; staleness by content hash and workspace data version; approval names its evaluation; honest wording), corrected on the same branch; audited checkpoint `77b7185` (CI 34920776278, 13 / 13).
* V2 on the same branch (`docs/zaad_full/OPERATING_PRODUCT_V2.md`, release audit `docs/zaad_full/FABLE_V2_RELEASE_AUDIT.md`): governance (append-only audit log, per-actor tokens with roles / capabilities, self-approval policy, optimistic concurrency, idempotency, migration 025), closed loop (human-recorded external status, decision responses, outcomes, five value registers, History), location-aware inventory with SKU reconciliation, capability readiness counted from the vault (14 capabilities, quality checks), amendment counterfactual under declared contract terms (migration 026; fee beside the engine's difference as two stated numbers; SPLIT refused), all-or-none bulk proposals, transfer proposals from concrete P2 moves (migration 027), numeric xlsx cells, per-supplier / default formats, Arabic chrome with bidi-isolated figures, executed actions on the network, telemetry allowlist, external solve profile (96 % of a plan's wall clock is HiGHS; no decomposition — global ties). `zaad/` untouched after the V1 checkpoint (only `zaad/full/jobs.py` job infrastructure in the whole PR; frozen canonical regression PASS on the checkpoint and on CI). Validation7 / Validation8 / holdout4 not accessed. No ERP integration named. ZAAD sends nothing to a supplier.
* Gates on the tested head `b98bd0e`: full suite 2,188 passed / 2 skipped (2,134 at the checkpoint, +54, none removed); ruff, mypy (CI scope), bandit, pip-audit clean; frontend tsc / eslint / 138 tests / build green; CI run 34926697504 13 / 13 on the exact head, both Vercel checks green.
* Merge: PR #81 merged as `main` `458fcaf` (tree `0c00a09`, identical to the tested head; parents `4a56470` + `b98bd0e`). Vercel production deployed from the merge commit (`Vercel – zaad: success` on the commit status; production deployment Ready). PR #82 (`b4dbdc0`) added `.github/workflows/deploy-api.yml`, a GitHub-runner deploy of an exact commit, after both laptop build paths failed (below); its first run could not start because GitHub Actions refused every job on this private repository for billing ("recent account payments have failed or your spending limit needs to be increased"), which also stopped CI on `main` from 10:35 UTC.
* Backend: Fly `zaad-api` **v26**, image `zaad-api:canonical-458fcaf`, digest `sha256:4ba1cd256bcbf732339b9d273a03c93541c7d90f46c18d08aab93dc14b2e661d`, prior v25 `canonical-e0fecdc` (the pre-operating-product tree: every V2 route was 404 in production until this deploy while the Vercel frontend already expected them). The image was built **on the Fly builder machine** (`fly machine exec`) from the GitHub tarball of the exact commit `458fcaf` (Dockerfile, pyproject.toml and api/main.py digests equal to a clean local checkout), pushed to `registry.fly.io`, and deployed by image: the laptop's link could not carry the 346 MB context (Depot upload stalled; the classic builder's gRPC status stream failed with `h2c 500` / `Unavailable` on three fresh builders; the WireGuard tunnel timed out at flyctl's probe). Machine / volume / secrets / env unchanged. Startup log clean (one pre-listen health probe, passing 12 s later).
* Production smoke (`scripts/operating_product_release_smoke.py --self-serve`, throwaway workspace `op_ca598163` with the 427,995-row sample): **19 / 19**. Browser walk on zaadsupply.com with a second throwaway workspace `op_1ed2d08a`: connect, Home (standing, snapshot, readiness line), Inventory in the site view with the SKU drawer reconciliation, Purchase orders, Upload (capability matrix, status line from the same counted answer), Data (fields, quality checks, column chooser), supplier Diagnostics (lateness honestly unmeasurable — no promised dates in the sample), Network panel (executed actions, links), History (five registers), Arabic toggle (`dir=rtl`, `lang=ar`, Arabic navigation, figures `direction: ltr`) and back; proposal FABLE-V2-PROD-QA-1 created, evaluated (two single-product solves, 40 s; TOTAL proposal-vs-current +222.65 USD, three columns, no unavailable cells), approved against a current evaluation, exported (`x-zaad-transmitted: false`, standard profile), external status PLACED_EXTERNALLY recorded, History counts updated. Console clean on every page. Roles: `/me` returns the 14 capabilities of the pilot ADMIN; a second actor was not minted in production (needs the admin key), so role gating rests on the tested enforcement.
* **BLOCKED — the plan path.** The product's default plan (10 products, `max_solve_seconds=15`, job cap 450 s from `max_solve × (10 + services) × 1.5`) reached TIMEOUT in production (11:54:26 → 12:01:59), and a 5-product plan (cap 337 s) also TIMEOUT. Measured on the machine itself with `scripts.v2_solve_profile --skus 5`: 306 s of solver time for a 5-product fixture (build 7 s) on `shared-cpu-2x` / 2 GB — roughly 2.5–3× the laptop's time — so neither cap fits. While a solve runs, reads take 2–3 s; when two solves overlapped, reads took 40–80 s and one dataset page answered 503. The fix is either dedicated CPU (`fly scale vm performance-2x --memory 4096`, a spend change that the session's auto-mode classifier refused) or a code change to the job cap / default scope (needs CI, which the GitHub billing block prevents). Neither could be applied in this session. The earlier ledger note ("shared-CPU steal … a performance-CPU machine or the async job path remain the defences") now has a measurement: the async path alone is not enough on this machine size.
* **V2 PRODUCTION RELEASE — BLOCKED** (everything except the plan path verified in production). No runtime tag created. Throwaway production workspaces `op_ca598163` and `op_1ed2d08a` hold sample data only. Fly deploy token `github-actions deploy-api` (30 days, scoped to `zaad-api`) stored as repository secret `FLY_API_TOKEN`; a 3-hour push token was used on the builder and expires on its own.

## Production planner performance recovery — measured, root-caused, orchestration fixed, planner still BLOCKED at the default scope (2026-09-15, branch `fix/production-planner-performance` from `e961131`)

* Verified start: `main` `e961131`; Fly v26 `canonical-458fcaf` (digest `sha256:4ba1cd25…`), `shared-cpu-2x` 2 GB, health 200; Vercel production `e961131`; GitHub Actions billing block confirmed on run 34958788944 (10:35 UTC) and **cleared** by re-running it at 14:22 UTC — 13 / 13 at 14:31.
* Measured in production, one plan at a time, reads timed while solving (`scripts/production_plan_probe.py`, throwaway workspaces `op_444e3293`, `op_9844a31c`, `op_954c232d` and the 10-product run's, sample data only): 1 product 4.6 s; 2 products 29.1 s and a second 2-product plan QUEUED 19.2 s then 29.0 s; 5 products 137.8 s (172 s CPU, 3.7 s steal); **10 products TIMEOUT at 450 s** (509 s CPU, 7.3 s steal — unthrottled). Reads: 0.2–0.5 s median, 0.93 s worst, 0 errors in 902 samples.
* Root cause: `/proc/stat` on the machine carried user 348 s / **steal 1,888 s** from the V2 closeout's consecutive solves — Fly shared vCPUs are 6.25 % baseline with a 500 s burst balance; one plan spends it and everything after (including the API) runs throttled; that is the day's TIMEOUTs and 40–80 s reads. Second, independent cause: the planner's joint escalation solve (two lexicographic MILPs over every product, 22,000 columns at 10 products) and the per-service confirmation ladder grow superlinearly — 10 products exceed 450 s of one unthrottled core. Classification B. Solver share 94–100 % at every size; nothing outside the solver is worth work.
* Coupling: the default 10 are 7 components (largest 3, by shared supplier capacity); decomposition **rejected** because the escalation objective pools unmet demand across products (§6 of the record).
* Fixed (orchestration only, `zaad/full/jobs.py` + `api/routers/zaad_full.py` + web): one explicit solver lease granted in submission order, shared with the synchronous routes (`429 planner_busy`), atomic QUEUED→RUNNING claim, `queue_position` / `running_now` on job reads, queued state on the web; `scripts/production_solve_benchmark.py`, `scripts/production_plan_probe.py`. Gates on the branch: canonical regression PASS, P1 invariants 720 clean, workspace smoke, 40 job / evaluation / diagnostic tests, 6 new lease tests + 1 API test, web 140 tests, ruff / mypy / bandit clean.
* Not done, by rule: no machine change (spend), no scope or cap change (product policy), no runtime tag (unhealthy plan path), no Insights.
* Merged as `main` `d2a3cb5` (`Merge PR #83: …`, parents `e961131` + `8ca59fb`, tree `9ce1c5d` = the tested head's). Deployed by the `deploy-api` workflow (run 34988281346) as Fly **v27 `canonical-d2a3cb5`**, digest `sha256:2d5f2b5a…`, rolling restart clean (logs: umount, reboot, filesystem clean, health passing at 15:28:02 UTC). Production smoke on v27 (`scripts/operating_product_release_smoke.py --self-serve`, throwaway `op_0e51acef`): **19 / 19**. A 1-product plan on v27: DONE in 4.0 s, reads 0.23–0.43 s median. No runtime tag: the plan path is not healthy at the default scope.
* Verdict: **ZAAD V2 PRODUCTION PLANNER — BLOCKED** on the two owner decisions above.

## ZAAD Operating Product V2.1A — Visual Insights + Canonical Connectivity + Customer Demand Intelligence — RELEASED (2026-09-16, branch `feat/zaad-insights-canonical-connectivity` from `3a25b52`, PR #84)

* Built on the owner's explicit instruction not to wait for the planner's machine decision: Insights reads uploaded records and the latest *completed* plan; it never starts a solve, and it says when the workspace's data changed after that plan (`OPERATING_PRODUCT_V2_1_INSIGHTS.md`; audit `FABLE_V2_1_RELEASE_AUDIT.md`).
* Backend `api/product/insights.py` + `api/routers/zaad_insights.py` (`/api/zaad/insights/{summary,plan,demand,demand/period,inventory,supply,suppliers,service,decisions,value,connectivity}`): bounded DuckDB aggregations over the caller's vault, provenance (data, metric, numerator, denominator, filters, coverage, last updated, plan) on every payload, nulls with a reason and never zero, lateness never counted without a promised date, five value registers never combined, engine connectivity matrix P0 / P1 / P2 / sector / P3 / P4 / P5 / P4B. `POST /intake/load-demo-company`. No file under `zaad/` changed.
* Web: `/insights` (six tabs + Perishability when a sector is declared), URL filter state, period drill-down (customers, products, sites, changes, stock, inbound orders, plan decisions), "Data & scope" and a table alternative on every chart, chart → action links, action → insights links on decision detail, three summaries on Home, Arabic copy; `MultiLine` / `StackedBars` added to the chart kit.
* DEMO company `synthetic/fmcg/demo_company.py` (*Al-Bahr Trading (DEMO)*, 42,280 rows, two years, scenarios built in and test-pinned), `scripts/zaad_demo_workspace.py` (the loop through the public API: plan → responses → proposal → evaluation → approve → export → external status → outcomes), `scripts/insights_scale_qa.py` (10k / 50k products: every query < 800 ms median; 437 ms worst at 50k / 2.6 M order rows).
* Gates on the tested head `2901ee9`: 16 Insights API tests, 7 demo integrity tests, 10 web tests (150 total), tsc / eslint / ruff / mypy / bandit / pip-audit / gitleaks / docker / frozen regression — CI 35011852846 **13 / 13**. Browser QA on the local dev server and the demo workspace: all tabs, the spike drill-down, filters, Arabic, mobile, plan-backed Decisions & value, decision → insights links; one 500 (a filtered supply query binding out of order) found and fixed before merge.
* Merge `13dde49` (parents `3a25b52` + `2901ee9`, tree identical to the tested head). Fly **v28 `canonical-13dde49`** (digest `sha256:374b4e91…`) by the `deploy-api` workflow; clean rolling restart; Vercel production `13dde49` Ready. Production smoke **24 / 24** (throwaway workspace `op_15bc84a7`).
* Tag **`zaad-operating-product-v2.1a-runtime`** = `13dde49` (annotated `d1f92a8`), pushed. Production demo (`scripts/zaad_demo_workspace.py --products 5`, throwaway `op_387d9787`): the company loaded; the 5-product three-site plan reached TIMEOUT at its 562 s cap — the V2 planner limit already recorded, not an Insights defect; Insights reads *No completed ZAAD plan yet* on that workspace exactly as specified. The full loop completed twice on the local server with the same code (`op_8f0e526c`, `op_96acea06`).
* Browser walk on `zaadsupply.com/insights` (sample workspace): Overview and Demand honest on data with no shipped quantities and no promised dates; no console errors (audit §8). Follow-up PR #85 (scripts only) merged as `75be986` after CI 35053894310 13 / 13.
* **V2.1A — RELEASE PASS** on the Insights criteria; the planner's default-scope latency remains the owner's decision (current-state table).

## Exact next action

The planner is still the release blocker for the operating product's runtime tag. Decide the two items in the current-state table — scale `zaad-api` to `performance-2x` / 4 GB, and choose the default plan scope (5, with larger explicit choices) or a budget-following cap (~900 s at 10 products) — then re-run `scripts/production_plan_probe.py --self-serve --products 10` (or the chosen default) on the new machine: it must complete inside its cap with reads in their idle band, twice in a row. Only then create `zaad-operating-product-v2-runtime` on the deployed merge (`d2a3cb5` today), update this table and `CURRENT_SYSTEM.md`, and start V2.1 (Insights) on a new branch. Until then: P4B V1 is released (Fly v23, `1851f40`, tag `p4b-v1-release-runtime`) on top of P5 (v22, `2fc7b50`). P4B V2, P6, P7, P8, P9 are not started and each needs a separate authorization. Keep
`ZAAD_LEGACY_PLANNERS` explicit on every deployed environment and run
`scripts/zaad_canonical_regression.py` before accepting any Dependabot bump that touches the solver
stack.

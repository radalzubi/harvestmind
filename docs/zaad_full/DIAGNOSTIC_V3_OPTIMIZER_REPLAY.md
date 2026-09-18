# Diagnostic V3 — policy benchmark separated from a rolling replay of the ZAAD optimizer — implementation tracker

**Status: DONE — RELEASED (2026-09-18).** Branch `feat/diagnostic-v3-optimizer-replay` from `main` `521ed68` → PR #91 (tested head `4177b9c`, CI 35363075037 13 / 13) merged as `03bcf2c`, Fly `zaad-api` v33 `canonical-03bcf2c`; follow-up PR #92 (tested head `0ecb5a2`, CI 35368689123 13 / 13 after one re-run of the known solver-lease timing race) merged as `d0edf15`, Fly **v34** `canonical-d0edf15` (digest `sha256:7a820f007d0760faa6faea5f3eeffe9d30b005212a48200b8c487040cd7059de`, deploy-api run 35370542365); Vercel production `dpl_GXAAN52UJ4FK6UEXSZt8MrrsUEpd` from `d0edf15`; machine `0804e0dfd1e948` unchanged; runtime tag `zaad-diagnostic-v3-runtime` = `d0edf15`. Release record in §7.

## 0. The conceptual problem

Diagnostic V2 presents one comparison: simple replenishment policies (`order_up_to`, `deterministic_sp`,
`stochastic_sp`, `anchored_sp`, `adaptive_sp`) replayed on rolling folds of the operator's history by
`backtesting.safe_selector.safe_select`, with a nested held-out re-check. On the NTDCO-shaped case that read
"order-up-to +15.4% on the selection periods, about −0.4% on the unseen periods, current policy retained".
That is a valid **policy validation** result. It is not, and must never be read as, the performance of ZAAD's
adaptive optimizer, which was not part of that comparison at all.

## 1. Repo review (what was verified before coding)

| Question | Finding | Where |
|---|---|---|
| What runs in production when a decision is made? | `zaad.full.planner.plan(request)` on a `zaad.full.contracts.Request` built by `zaad.full.workspace.build_request(conn, operator_id, as_of=…)`; the job runner (`zaad/full/jobs.py::_run`) and the synchronous route both call `plan` | `api/routers/zaad_full.py`, `zaad/full/jobs.py` |
| Is `deterministic_sp` the production optimizer? | **No.** `backtesting/counterfactual.py::policy_deterministic_sp` (and `stochastic_sp`, `anchored_sp`, `adaptive_sp`) build a `optimization.multi_period_sp.MultiPeriodStochasticLP` on `FoldInputs`; that is the older FMCG LP, not the frozen ZAAD engine (`zaad/full/model.py` MILP under `plan`'s candidate orchestration, P0 protection / recovery, P1 purchasing economics). `order_up_to` is `policy_order_up_to`: a periodic-review order-up-to rule over lead + review with a z-buffer | `backtesting/counterfactual.py` lines 281, 423, 443 |
| Is there an existing rolling replay of the real engine? | **Yes.** `zaad/full/replay.py::replay(initial, truth, reviews, method, rolling=True)`: observe arrivals → refit fills from observed receipts → plan on a fresh as-of snapshot → settle one period on a private truth `World` → roll stock, pipeline, history, shipment observations forward. `method="gated"` calls `plan(req)` unchanged. The frozen canonical regression (`scripts/zaad_canonical_regression.py`) runs exactly this loop on the P1 fixtures. The truth is drawn synthetically (`zaad/full/evaluation.py::long_truth`) — there is no historical-truth builder yet | `zaad/full/replay.py` |
| Point-in-time protections | `build_request(as_of=D)` uses order rows dated before `D` for history, purchase orders closed before `D` for the supply fits, the latest inventory snapshot before `D` for opening stock, open orders placed before `D`, and reports a `leakage_guard` block. `replay` appends truth demand to `history` only after the period settles, materialises receipts only when they arrive, and refits `fill_mean` from arrived receipts only. Workspace requests carry no external `signals` (verified: 0) | `zaad/full/workspace.py` lines 187–202, 433–500, 573; `zaad/full/replay.py` |
| Settlement and ledger | `zaad/full/settlement.py::settle` (one work-conserving evaluator for every policy: procurement, freight, handling, ordering, receiving, holding, financing, working capital, lost sales, SLA, disposal, transfer, switching; opening / closing assets); `zaad/full/economics.py::cost_breakdown` maps the ledger to PURCHASE / FREIGHT / ORDERING / RECEIVING / CARRYING / FINANCING / SHORTAGE / INVENTORY_VALUE_CHANGE; `zaad/full/evaluation.py::endpoint` scores any rolling replay policy-agnostically | as named |
| Inventory transitions | `settle` returns `end_stock` (per SKU, expiry) and `pending`; `replay` builds the next review's `stock` from them (locked stock kept apart) | `zaad/full/replay.py` lines 245–262 |
| Supplier fill / lead settlement | a truth `World` carries `arrival[(source, τ)]` (absolute period an order placed at τ arrives) and `fills[(source, τ)]`; `replay` assigns them to every new purchase at its placement period and to open POs via `po_due` / `po_fill` | `zaad/full/worlds.py::World`, `replay` lines 275–294 |
| Frozen regressions | `scripts/zaad_canonical_regression.py` (P1 B/T/Q/A identity, P0 cell 15), P1 invariants; CI job "zaad frozen regression" | `.github/workflows/ci.yml` |
| NTDCO fixture | `tests/fixtures/diagnostic_ntdco_old_summary.json` (shape-faithful, owner-quoted values; no customer data). A local registry entry named NTDCO exists in `data/` with zero rows | `tests/unit/test_diagnostic_findings.py` |
| Cost of one production solve | demo company, `as_of` 2026-03-02: 5 SKUs → 32 s locally (9 MILPs, state PROTECT, RETAIN_INCUMBENT); 36 SKUs → 35 s (8 MILPs, ABSTAIN with the operator rule). The request's `max_solve_seconds` (15 s per candidate) bounds a solve whatever the SKU count; an abstaining review keeps the operator's rule, as production does | `scratchpad/measure_plan.py` |

Conclusion of the review: a valid rolling replay of the production optimizer **can** be built by giving
`zaad.full.replay.replay` a truth `World` reconstructed from the operator's own history instead of a drawn one,
and by adding two baseline "methods" (the operator's actual orders as placed; the reconstructed rule) that run
through the same loop and the same settlement. The counterfactual settlement question (what a supplier would have
delivered against an order the operator never placed) is the only place where assumptions enter; they are made
explicit per decision (§3).

## 2. Design

### 2.1 Two analytical layers, kept apart everywhere
- **Policy benchmark** (unchanged computation): `safe_select` over the V2 candidates. Presented as "Simple policy
  benchmark"; its result is about fixed replenishment rules, with the held-out explanation retained.
- **ZAAD historical decision replay** (new): `zaad/full/historical.py`. Three legs through the same replay loop and
  the same settlement: `actual` (the operator's orders as placed, MEASURED decisions), `rule` (the reconstructed
  incumbent rule projected from each point-in-time snapshot, `method="incumbent"`), `zaad` (`method="gated"` =
  `plan(req)`, the production optimizer, re-run at every weekly decision date on the state its own earlier
  decisions produced).

### 2.2 Historical truth (`build_truth`)
For the replay window (review 0 = origin Monday D0; absolute periods τ = 0 … T−1+H):
- `demand[svc_sku][τ]` = the operator's customer-order quantity in week τ (MEASURED; demand as ordered, exogenous
  to stock; recorded shortfalls do not reduce it).
- `arrival[(src_sku, τ)]`, `fills[(src_sku, τ)]` for an order placed at τ, by hierarchy:
  1. MEASURED — the operator placed a PO for that SKU in week τ and it was received: lead = first receipt − PO
     date, fill = received ÷ ordered (quantity-weighted over the week's POs);
  2. INFERRED — the nearest received PO of the same supplier within ±4 weeks (supplier behaviour at that time,
     quantity-independence assumed);
  3. SIMULATED — a seeded draw from the supplier's empirical fill and lead samples over the whole history;
  4. ASSUMED — no receipts for the supplier at all: the source's declared / assumed lead and fill.
  When ZAAD orders a different quantity than the operator did in a MEASURED cell, the cell is counted as
  INFERRED for that decision (the observed fill ratio is applied to a quantity the supplier never saw).
- Open POs at D0: `po_due` / `po_fill` from receipts after D0 (MEASURED); never received → expected ETA and the
  fitted fill (ASSUMED), flagged.
- Everything after D0 is settlement truth only. The optimizer sees it exclusively through `replay`'s observation
  rules (history after settlement, receipts on arrival). Prices, SKU set, calendars, economics are frozen at D0
  (ASSUMED constant over the window; recorded).

### 2.3 Scope, budget, coverage (no silent sampling)
- SKUs: the top `HARVESTMIND_REPLAY_SKUS` (default 5) by demand value at D0 — a fixed, pre-registered rule, never
  a choice of dates; the share of demand value covered is reported.
- Decision dates: every weekly review in the window, in order; `HARVESTMIND_REPLAY_REVIEWS` (default 26) reviews
  ending at the latest date that still leaves the planner's horizon of truth. No date sampling.
- Budget: `HARVESTMIND_REPLAY_BUDGET_S` (default 1200). The ZAAD leg runs chronologically and stops at the budget;
  every leg is then scored on the same completed prefix and the coverage (k of T decision dates) is reported.
- Everything is reported: SKUs replayed / total, value share, reviews completed / planned, solves, per-solve and
  total wall time, peak RSS.

### 2.4 Results contract (`summary["optimizer_replay"]`)
`status` (complete / partial / unavailable + reason), `scope`, `coverage`, `legs` {actual, rule, zaad} with
`endpoint` scores (`zaad.full.evaluation.endpoint`), per-review cost / service / inventory per leg, per-review
differences (zaad − actual, zaad − rule), decision rows (review, date, SKU, supplier, actual qty, rule qty, ZAAD
qty, ZAAD action class, quantity difference, timing note, service outcome per SKU, end stock per SKU, settlement
provenance), provenance shares (MEASURED / INFERRED / SIMULATED / ASSUMED by decision), the replay-confidence
assessment, and the point-in-time attestation (per review: history ends before as_of, no receipt observed after
as_of, no PO placed after as_of).

### 2.5 Report V3
Sections: executive summary (two separate statements) · data readiness · how you order today · **simple policy
benchmark** · **ZAAD historical decision replay** (summary table, per-period chart with negative periods, regime
split where supported, provenance and confidence, coverage, drill-down rows) · management attention (with computed
intersections) · suppliers · lane exposure · actions · methodology appendix with one canonical provenance ledger
(OPERATOR / MEASURED / INFERRED / PUBLIC_BENCHMARK / ASSUMED / UNKNOWN) and automated consistency checks.

## 3. Counterfactual settlement policy (explicit)

| Situation | Settlement | Label |
|---|---|---|
| operator's own order, received | observed lead and fill | MEASURED |
| ZAAD orders in a week the operator ordered the same SKU | observed lead and fill applied to ZAAD's quantity | INFERRED (quantity-independence assumed) |
| ZAAD orders in a week the operator did not order that SKU, supplier received something within ±4 weeks | nearest observed lead and fill of that supplier | INFERRED |
| no supplier observation within ±4 weeks | seeded draw from the supplier's empirical fill / lead over the history | SIMULATED |
| supplier never observed | declared / assumed lead and fill | ASSUMED |
| open PO at D0 received after D0 | observed receipt | MEASURED |
| open PO at D0 never received | expected ETA, fitted fill | ASSUMED (flagged) |
| supplier capacity | as the request declares it at D0 (customer-provided or inferred from PO peaks) | per provenance |
| prices, economics, SKU set, promotions after D0 | frozen at D0 | ASSUMED constant |
| customer demand | orders as placed | MEASURED |

## 4. Progress

- [x] Branch, review, tracker
- [x] `zaad/full/historical.py`: truth builder, actual-orders method (recorded orders conformed to the declared pack / capacity envelope, every change recorded), three-leg runner, endpoint scoring, per-period differences with a block-bootstrap interval (≥ 8 periods), decision rows, provenance shares, regime split, confidence, attestation
- [x] Job integration (`api/routers/jobs.py`: stage `replaying` with progress per decision date; `HARVESTMIND_REPLAY`, `_SKUS`, `_REVIEWS`, `_BUDGET_S`; an unavailable or failed replay never fails the diagnostic)
- [x] Report V3 (`reports/diagnostic_v3.py` + `diagnostic_findings.py`, `diagnostic_pdf.py`, `DiagnosticReport.tsx`, `api.ts`): benchmark framed as fixed rules, replay section, two-part executive summary, synthesis findings, canonical provenance ledger + automated consistency checks
- [x] Tests: `tests/unit/test_diagnostic_v3_report.py` (16), `tests/integration/test_historical_replay.py` (9: perturbation invariance of the point-in-time request and of every replay snapshot, three legs with evolving state, counterfactual labels, budget stop, abstain fallback, short history, real planner on two products × two dates, isolation)
- [x] Manual QA on the demo workspace; performance table (§5)
- [x] PR, CI on exact head, merge, deploy, production QA, tag, docs (§7)

## 5. Local QA and performance (synthetic demo company, 2026-09-18)

`HARVESTMIND_REPLAY_SKUS=3`, `_REVIEWS=8`, `_BUDGET_S=900`, in-process runner, one solver thread, Apple Silicon.

| step | value |
|---|---|
| stages seen in the browser | preparing → reconstructing → lanes → testing → **replaying** ("ZAAD re-solved decision date k of 8 (last solve n s)") → reporting; animated bar throughout |
| diagnostic total (`timing.run_s`) | 278 s, of which the replay 263 s |
| replay | 8 decision dates 2026-04-27 … 2026-06-15, 3 of 36 SKUs (20% of demand value), 8 optimizer solves, mean 32.9 s, max 59.5 s (later reviews, PROTECT state), peak RSS 879 MB |
| result (synthetic) | ZAAD 1.1% more costly than the operator's actual orders over the window, better in 4 of 8 periods, worst period −171,826 JOD; the optimizer retained the reconstructed rule on 7 of 8 dates; 100% of ZAAD's 13 orders settled INFERRED (observed supplier behaviour applied to a different quantity or a nearby week); replay confidence Moderate (3 stock locations, terminal value assumed, 20% value coverage) |
| policy benchmark on the same run | fixed order-up-to rule +77.7% on selection, +72.7% on unseen periods (synthetic B_lumpy-like demand); stated as a fixed rule, never as ZAAD |
| consistency checks | all pass after the readiness limitations became ledger-driven (the first run caught "capacity is inferred" in the readiness text while the supplier list declares it) |
| payload | `GET /jobs/{id}` 171 KB (report 62 KB incl. 24 decision rows; summary with the replay 100 KB); PDF 39 KB, 10 pages (a dense fixture: 4 synthesis findings + 5 lanes) |
| point-in-time | every planning snapshot attested clean on all three legs; the perturbation tests hold |

Earlier measurements: one production solve on the demo request is bounded by the request's 15 s per-candidate limit — 32 s for 5 SKUs (9 MILPs), 35 s for 36 SKUs (8 MILPs, ABSTAIN). A 26-date replay is therefore roughly 15–25 minutes of solver time; the default budget stops it honestly at the time limit and reports coverage.

## 6. Decisions and limits (kept current)

- The replay scope is the top `HARVESTMIND_REPLAY_SKUS` (5) products by demand value at the first decision date, every weekly decision date over `HARVESTMIND_REPLAY_REVIEWS` (26) reviews, stopped at `HARVESTMIND_REPLAY_BUDGET_S` (1200 s); coverage and the value share are always reported. No date sampling.
- The recorded orders of the `actual` leg are conformed to the declared pack multiple and capacity envelope so the settlement's physical checks hold; every change is recorded with the recorded quantity.
- An abstaining review (the planner's ABSTAIN) executes the operator's reconstructed rule for that period, as production does; the row says so.
- The replay engine values a lost sale at a stated 30% margin over cost where no price is given (the frozen engine's own assumption), while the policy benchmark anchors such products to the incumbent; the ledger shows both treatments with the explanation.
- The replay plans the main location's stock (the production purchase-plan path); branch stock is not netted. Prices, product set and economics are frozen at the first decision date.
- Per-product economics are not attributed (the ledger is settled for the replayed products together); per-product service and stock are.
- A dense report is 10 pages; the V2 target of 3–6 no longer holds once the replay section exists.

## 7. Release record (2026-09-18)

| step | value |
|---|---|
| PR #91 | `feat/diagnostic-v3-optimizer-replay`; tested head `4177b9c`; CI run 35363075037 13 / 13 (two earlier heads failed on test-only problems: a module fixture that set `HARVESTMIND_AUTH_REQUIRED` directly and leaked 401s into the intake tests, fixed with a module-scoped `MonkeyPatch`; and a 10 s hold in the V2 lifecycle test that raced on the 2-vCPU runner, raised to 90 s) |
| merge 1 | `03bcf2c2fbf9c80a2829cb812bdbf7b9b6e4782b` (`Merge PR #91`, main was `521ed68`) |
| deploy 1 | Fly `zaad-api` **v33**, image `canonical-03bcf2c`, digest `sha256:2e347c6838ee6e0efb6abca5fea9afcc1aad75e6cad65b7f8e191a834e01de9c`, deploy-api run 35364778824; Vercel production `dpl_9P6ZzhYS3DixMbWisztwJHZZJdBn` from `03bcf2c`; machine `0804e0dfd1e948` `shared-cpu-2x` unchanged |
| production QA 1 (v33) | throwaway self-serve workspace **V3 QA DEMO (synthetic)** `op_9246979a` loaded with the synthetic DEMO company (36 SKUs, 6 suppliers, 21,011 order rows); second tenant `op_ddbd8a22`; no customer workspace touched. `POST /jobs/diagnostic` 2.4 s; second press returned the same job; stages `queued` (25 s machine boot) → `lanes` → `testing` → `replaying` (progress "ZAAD re-solved decision date k of 26 (last solve n s)") → `done` "report ready"; run 2,567 s. Replay **partial**: 8 of 26 dates within the 1200 s budget, 5 of 36 products (31% of demand value), solves 4.7 / 70 / 41 / 137 / 106 / 382 / 338 / 180 s (mean 157 s, max 382 s), peak RSS 426 MB, all 8 dates `RETAIN_INCUMBENT` (the report's retention note states that the ZAAD column equals the rule column), attestation clean on all three legs, settlement 100% INFERRED (ZAAD's quantities differed from the recorded orders on 33 of 40 product-weeks), 3 recorded orders conformed to pack multiples. Result stated plainly: ZAAD (= the reconstructed rule) 7.3% more costly than the actual orders over the window, 4 of 8 periods better, worst period 2026-01-26 −196,691 JOD, 80% CI on the mean per-period difference −28,572 to +89,618 JOD; replay confidence **Low** (coverage). Benchmark, separately: a fixed order-up-to rule +77.7% on selection and +72.7% unseen, framed as SIMPLE POLICY BENCHMARK; all six consistency checks pass; the benchmark text never says "optimizer". Isolation: other tenant 404, anonymous 401 on job, report.json, report.pdf. PDF 39,652 bytes, 10 pages; report payload 199 KB. Browser (zaadsupply.com, Chromium engine): the run view reconnected to the running job with the six stages, the result rendered sections 1–8, section 4 with the callout, scope, summary table, retention note, period chart, lookahead attestation and the decision drill-down (40 rows, first row 2025-12-22 / DEMO-0013 / DEMO-SUP-06 / you ordered 2,880 / ZAAD no order). |
| finding from QA 1 | after the budget stop, the clean-prefix re-run called the planner again for the 8 completed dates (the loop spent ~21 min solving them and ~21 min solving them again: run 2,567 s for 2,520 s of replay). Fixed in PR #92: the decision taken at each review is recorded and served again in the re-run; `optimizer_solves` now equals the completed dates. Production solves are far slower than the local 3.7–59.5 s because the shared-CPU machine's burst budget drains during a long solve (`zaad-environment-blockers-2026-09`); the per-candidate 15 s limit is CPU-throttled wall time. |
| PR #92 | `fix/replay-partial-prefix-cache`; tested head `0ecb5a2`; CI run 35368689123 13 / 13 (the unit-zaad-4 shard re-run once on the same head for the known `test_zaad_solver_lease` timing race) |
| merge 2 | `d0edf15309573ad97ea30dec4fcfb3ac2445e0bd` (`Merge PR #92`, main was `03bcf2c`) |
| deploy 2 | Fly `zaad-api` **v34**, image `canonical-d0edf15`, digest `sha256:7a820f007d0760faa6faea5f3eeffe9d30b005212a48200b8c487040cd7059de`, deploy-api run 35370542365; Vercel production `dpl_GXAAN52UJ4FK6UEXSZt8MrrsUEpd` from `d0edf15`; machine unchanged |
| production QA 2 (v34) | same workspaces; job `job_6a7e84a32d`; `POST` 2.2 s, second press the same job; `queued` 24 s → `testing` → `replaying` → `done` in **1,457 s** (v33: 2,567 s). Replay **partial**: 9 of 26 dates within the 1200 s budget (the check runs after each solve, so the last solve overshoots the budget), `optimizer_solves` 9 = `decision_points` 9 (no re-solve), solves 3.3 / 69 / 28 / 121 / 74 / 346 / 336 / 159 s + one more (mean 158 s, max 346 s), replay 1,425 s, peak RSS 426 MB; all 9 dates `RETAIN_INCUMBENT`; attestation clean on all legs; settlement 100% INFERRED. Result: ZAAD (= the rule) 2.9% more costly than the actual orders over the 9-date window, 5 of 9 periods better, mean per-period difference 1,473 JOD in ZAAD's favour, worst period 2026-01-26 −196,691 JOD, 80% CI −54,185 to +82,447 JOD; confidence **Low** (coverage). Six consistency checks pass; isolation 404 / 401 on job, report.json, report.pdf; PDF 39,707 bytes, 10 pages; payload 211 KB. |
| runtime tag | `zaad-diagnostic-v3-runtime` = `d0edf15` (annotated; older tags untouched) |
| not done | NTDCO: no customer key is held, so the NTDCO regression case is covered by the frozen `tests/unit/test_diagnostic_findings.py` expectations (benchmark conclusion unchanged) and not by a production run. The duplicated "promotion calendar" entry in the readiness field list (two staging columns map to one label) is a V2 wording item left for a wording pass. |

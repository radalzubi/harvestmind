# Diagnostic V3 — policy benchmark separated from a rolling replay of the ZAAD optimizer — implementation tracker

**Status: IN PROGRESS (2026-09-18).** Branch `feat/diagnostic-v3-optimizer-replay` from `main` `521ed68`.

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
- [ ] PR, CI on exact head, merge, deploy, production QA, tag, docs

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

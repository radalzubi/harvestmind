# P4B — pre-registration: fixture matrix, invariants, adversarial cases (design gate)

Registered at the design gate, before any implementation. Every fixture is a frozen `Request` from
the released bases (`zaad/full/demo.py` "recovery" open PO, P1 fixtures, P3 / P4 bases) with declared
`POOption` rows; the pass condition is fixed here. Results are ENGINEERING EVIDENCE ONLY.

## Fixture matrix

| id | case | state | pass condition |
|---|---|---|---|
| 1 | cancellation economically optimal | open PO 100, on hand covers demand for the horizon, cancel option fee 0.25 / unit, deadline open | CANCEL selected; ledger `cancel_fee` = 25; no purchase created; KEEP incumbent cost > selected cost by more than materiality |
| 2 | cancellation available but not worthwhile | same PO, demand needs the units, cancel fee 0.25 | KEEP retained; `NO MATERIAL COMMITMENT IMPROVEMENT AVAILABLE`; `amend[keep]` = 100 |
| 3 | cancellation prohibited | cancel option absent, or `deadline < as_of`, or `stage` not in `allowed_stages` | no cancel column with capacity > 0; KEEP; the report names the blocking rule |
| 4 | partial reduction allowed | `allow_split_amendments` true, cancel `max_quantity` 60 (minimum remaining 40); demand needs ~50 | REDUCE by <= 60 with `amend[keep] >= 40`; conservation `keep + cancel = 100` |
| 5 | reduction below supplier minimum prohibited | as 4 with demand needing 20 | cancel exactly 60 (never 80); `amend[keep]` = 40 = minimum remaining |
| 6 | defer reduces excess inventory | on hand high, de_expedite option +2 periods fee 0.10, holding declared | DEFER selected; `holding` lower than under KEEP by more than the fee; arrival at `due_in + world ETA error` |
| 7 | defer causes unacceptable stockout | on hand low, same defer option | KEEP (or EXPEDITE if declared); DEFER not selected; service floors met |
| 8 | expedite economically justified | stockout projected before the keep ETA; expedite option -2 periods premium 0.50 | EXPEDITE selected; `expedite_fee` = 50; shortage avoided in every world |
| 9 | expedite available but too expensive | same with premium 5.00 | KEEP; `NO MATERIAL COMMITMENT IMPROVEMENT AVAILABLE` or a cheaper P1 purchase, never the expedite |
| 10 | PO already shipped -> intervention prohibited | `stage` shipped, `departed_at` set; cancel / defer options list `allowed_stages` (confirmed) | every non-keep capacity 0; KEEP; settlement raises on any forced amendment |
| 11 | sunk deposit correctly treated as sunk | `prepaid_per_remaining_unit` 2, cancel fee 0, no credit; on hand covers demand | CANCEL still selected when the invoice saved exceeds the fee (the deposit is not a reason to keep); `opening_assets` carries the deposit; no `commitment_credit` |
| 12 | refundable deposit correctly credited | as 11 with `credit_per_unit` 2 (refundable) | `commitment_credit` = 200 on cancel; credit never exceeds prepaid + paid invoice; cancel becomes cheaper than in 11 by exactly 200 |
| 13 | supplier short-fill changes intervention value | `expected_accepted_remaining` 60 of 100 (fill 0.6), demand needs 80 | EXPEDITE / KEEP valued on 60 arriving units; the report states the fill assumption; no action assumes 100 |
| 14 | alternative source interacts with existing PO | P3 base with an approved alternate source; expensive PO expedite vs cheaper alternate purchase | the joint solve chooses the alternate purchase + KEEP (or REDUCE) rather than the expedite; no reroute variable exists; source decomposition unchanged in P3 terms |
| 15 | correlated disruption case | declared stress with `shared_failure` affecting the PO's source and the alternate | intervention values computed on the stress worlds; no option is chosen on the assumption of independence; hedged candidate consistent with P0 |
| 16 | perishable inbound where delay destroys usable life | PRODUCE physics, receipt life 4 periods, defer +3 | DEFER never selected when the deferred cohort is unsellable at arrival (`receipt_life`) - the arrival cohort's expiry follows `physics.receipt_life` |
| 17 | payment timing / working-capital case | keep invoice due at period 1 vs defer invoice due at period 4; `cost_of_capital_per_period` declared; tight `opening_cash` | DEFER valued with the payment shift; cash constraint respected in every world; no new capital constraint (P9) |
| 18 | identical observable histories -> identical P4B action (V2 only) | recourse with epoch 3, cancel deadline at period 5, two worlds with the same history to period 2 | `amend[p, o, node]` identical for both worlds (same node); non-anticipativity by construction |
| 19 | new information arrives -> valid action divergence (V2 only) | as 18 with demand diverging at period 2 | different nodes at epoch 3; different amendments allowed; no divergence before the epoch |
| 20 | incumbent KEEP remains optimal -> NO MATERIAL IMPROVEMENT AVAILABLE | balanced state, every option declared | verdict `NO MATERIAL COMMITMENT IMPROVEMENT AVAILABLE`; recommendation = KEEP; report identical to a request without options except the verdict block |

Disabled-path identity: a request without non-keep options produces a report byte-identical (timing
stripped) to the released runtime `2fc7b50`.

## Invariants (every fixture)

1. never cancel or reduce more than the open quantity: `Σ_o amend[p, o] = remaining`, `amend <= cap`;
2. never reduce below the contractual minimum: `amend[keep] >= minimum_remaining_quantity` (= `remaining - cancel.max_quantity`);
3. never change already received quantity: `received` untouched; only `remaining` is amended;
4. no intervention after cutoff: `deadline < as_of` or stage-ineligible -> capacity 0 (model) and PhysicalViolation (settlement);
5. no negative PO balance;
6. conservation before / after intervention (units, cohorts, arrivals);
7. payment effects reconcile: fees at period 0, invoices at `payment_due_in`, credits dated, cash trace balanced;
8. cancellation credits reconcile: `commitment_credit <= prepaid + invoice already paid` per unit;
9. no double-counted freight: an amended unit is charged its invoice once; new-purchase freight only on new purchases;
10. no source duplication: an amended PO keeps its source; reroute-to-source only through cancel + purchase;
11. no P4 non-anticipativity violation (V2: same node -> same amendment);
12. no intervention based on future information: options, deadlines and stages are `known_at <= as_of`;
13. no implicit P7 route optimization (no route / mode variable);
14. no implicit P9 capital allocation (no new capital constraint; cost of capital only);
15. deterministic tie behaviour (documented tie among equal-cost options: keep first);
16. human approval required: `approval_required: true`, `executable_purchase_order: false`, no amendment executed;
17. KEEP is always feasible when the incumbent is feasible (the keep option is mandatory and uncapped to `remaining`);
18. disabled path exactly preserves released behaviour.

## Adversarial cases (fail closed)

| case | expected |
|---|---|
| cancel quantity above remaining | REFUSED_AT_CONTRACT (`max_quantity`) / PhysicalViolation |
| reduce below the contractual minimum | STRUCTURALLY_IMPOSSIBLE (capacity) |
| expired deadline with a declared option | capacity 0; settlement refuses a forced amendment |
| option on a stage not in `allowed_stages` (shipped PO with cancel) | capacity 0 |
| negative fee (a hidden credit) | REFUSED_AT_CONTRACT (`fee_per_unit >= 0`; credits only through `credit_per_unit`) |
| credit above what was paid | REFUSED_AT_CONTRACT |
| split amendment when `allow_split_amendments` is false | exclusivity row: exactly one option |
| duplicate option ids / two keep options | REFUSED_AT_CONTRACT (exactly one keep) |
| option on a closed (dust) PO | ignored (`po_closed`), no row |
| option with `known_at > as_of` (future information) | REFUSED_AT_CONTRACT (causality) |
| REROUTE request (route / mode field) | REFUSED_AT_CONTRACT: not a P4B action (P7) |
| expedite beyond `max_quantity` (undeclared capacity) | STRUCTURALLY_IMPOSSIBLE |
| undeclared stage vocabulary value | REFUSED_AT_CONTRACT |
| options declared without provenance / reference | REFUSED_AT_CONTRACT |

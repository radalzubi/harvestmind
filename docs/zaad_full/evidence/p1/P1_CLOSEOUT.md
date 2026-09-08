# P1 CYCLE-STOCK ECONOMICS — CLOSE-OUT

> **Current verdict (closure pass, 2026-09-08): P1 CYCLE-STOCK ECONOMICS — REMAINS OPEN.** See "CLOSURE PASS" below; the first pass's verdict and evidence are kept above it as the record they were.

**Verdict: P1 CYCLE-STOCK ECONOMICS — FAIL ON FIXTURE PARITY (C, O, P); MECHANISMS COMPLETE AND RECONCILED; NOT FROZEN.**

The mechanisms the brief asked for are implemented, tested, reconciled and explained, and ZAAD P1
beats or ties the best competent baseline on 17 of 20 development fixtures. It does not on three
(MOQ four weeks, low opening stock, high opening stock), by 2.1% to 3.7% against a pre-registered
tolerance of 2%, and two pre-registered attribution expectations were wrongly written and fail.
The tolerance was not widened and the expectations were not edited, so the exact verdict "PASS AND
FROZEN" cannot be given. What is and is not established is set out below.

Branch `claude/zaad-cycle-stock-p1`, worktree `harvestmind-p1`, parent (frozen P0) `2e30721`.
Evidence in `docs/zaad_full/evidence/p1/`. Development fixtures only: every economic figure is a
CONFIGURED_ASSUMPTION; nothing here is customer validation, industry proof or a savings claim.

## 1. Result table (primary arm: nil declared stress, target-basis gate, order smoothing off)

Means over three seeds, eleven rolling reviews of a twelve-period weekly plan. The full table with
every required column (service, P10, breaches, unmet, worst shortfall, inventory units and value,
order count and size, purchase / freight / ordering / receiving / carrying / financing / shortage /
inventory value change / total, working capital, deltas, action recommended, why) is
`P1_RESULT_TABLE_none.md`; the per-cell records are `fixtures_none.jsonl`.

| fixture | incumbent | best baseline | ZAAD P1 | ZAAD vs incumbent | ZAAD vs best baseline | pre-registered checks |
|---|---|---|---|---|---|---|
| A_no_terms_good_incumbent | 5,824 | 5,824 (incumbent) | 5,887 | +1.1% | +1.1% | PASS |
| B_fixed_order_cost_replace_sold | 8,528 | 6,995 (economic_lot) | 6,223 | -27.0% | -11.0% | PASS |
| C_moq_four_weeks | 9,595 | 5,898 (reorder_point) | 6,115 | -36.3% | +3.7% | FAIL: zaad_not_worse |
| D_case_multiple | 5,807 | 5,807 (incumbent) | 5,775 | -0.5% | -0.5% | PASS |
| E_pallet_multiple | 6,239 | 6,239 (incumbent) | 6,239 | +0.0% | +0.0% | PASS |
| F_mov_two_skus | 14,040 | 11,766 (periodic:2) | 11,669 | -16.9% | -0.8% | PASS |
| G_freight_tiers | 21,400 | 16,720 (economic_lot) | 14,970 | -30.0% | -10.5% | PASS |
| H_per_pallet_freight | 6,884 | 6,826 (periodic:2) | 6,671 | -3.1% | -2.3% | PASS |
| I_max_pallets_ftl_cap | 16,274 | 9,814 (economic_lot) | 9,967 | -38.8% | +1.6% | PASS |
| J_net60_cost_of_capital | 7,478 | 6,850 (periodic:2) | 6,079 | -18.7% | -11.3% | PASS |
| K_deposit_early_cash | 7,490 | 6,862 (periodic:2) | 6,079 | -18.8% | -11.4% | PASS |
| L_high_holding_rate | 7,434 | 6,856 (periodic:2) | 6,134 | -17.5% | -10.5% | PASS |
| M_order_calendar_wednesday | 6,256 | 6,256 (incumbent) | 6,272 | +0.3% | +0.3% | PASS |
| N_long_lead_21_days | 5,937 | 5,937 (incumbent) | 6,025 | +1.5% | +1.5% | FAIL: categories |
| O_low_opening_stock | 6,521 | 6,399 (reorder_point) | 6,576 | +0.8% | +2.8% | FAIL: zaad_not_worse |
| P_high_opening_stock | 6,282 | 5,786 (reorder_point) | 5,906 | -6.0% | +2.1% | FAIL: zaad_not_worse |
| Q_volatile_demand_high_target | 5,971 | 5,971 (incumbent) | 6,043 | +1.2% | +1.2% | PASS |
| R_asymmetric_prices_mov | 63,448 | 63,448 (incumbent) | 63,255 | -0.3% | -0.3% | FAIL: categories |
| S_cash_constrained | 6,924 | 6,234 (economic_lot) | 6,147 | -11.2% | -1.4% | PASS |
| T_combined_realistic | 24,255 | 17,593 (economic_lot) | 15,256 | -37.1% | -13.3% | PASS |

Policies: INCUMBENT is the operator's declared rule projected from each review's snapshot
(`replace_sold`, `reorder_point` or `periodic:2` per fixture); REORDER_POINT+PROTECTION,
PERIODIC_REVIEW(2) and EOQ_LIKE are lot-, MOV-, load- and cash-aware projections
(`zaad/full/policies.py`); ZAAD P1 is the gated planner. All 300 cells of every arm completed;
no policy failed settlement.

Sensitivity and ablation arms (same fixtures, same seeds):

| arm | what changes | fixtures passing | where ZAAD moved |
|---|---|---|---|
| `none` (primary) | - | 15 / 20 | - |
| `late` | declared stress: one week late, full fill | 15 / 20 | protection is bought where the stress bites (I +2%, O +2%); P passes on cost and fails only the "mostly abstain" expectation |
| `gate` | `service_gate_basis="incumbent"` (V7 rule) | 15 / 20 | I: 9,967 -> 10,813 (+8.5%); the lean full-load plan is refused against the replace-sold incumbent's 100% service |
| `smooth` | `order_smoothing=.02` (P0 default) back on | 15 / 20 | C: 6,115 -> 6,201; F: 11,669 -> 12,114 (+3.8%): the smoothing proxy fights consolidation |

## 1a. Runtime

Per-review wall time of the gated planner, primary arm (660 reviews): p50 0.10 s, p90 0.65 s,
p95 1.00 s, max 19.8 s (one cadence-candidate MILP hitting the 15 s budget plus confirmation);
whole arm 90 s on three workers. No benchmark approached the eight-hour stop.

## 1b. Reconciliation and invariants

- Every cell of every arm: ledger components sum to the settlement's economic cost to 1e-9
  (`|ledger sum - total| = 0.0` across 1,200 cells).
- `scripts/p1_invariants.py`: 60 / 60 (20 fixtures x 3 seeds, first review): components
  reconcile; attribution partitions every order exactly; no negative category; every supplier
  order clears MOV and the maximum load; operating components non-negative; provenance labels from
  the closed set and no CUSTOMER_PROVIDED label on a fixture; no unmapped ledger key; materiality
  verdict from the closed set; recommendation matches status; abstention reason stated; timing
  audit and waterfall agree on arrival periods.
- Unit tests: 23 P1 tests in `tests/unit/test_zaad_p1_economics.py`; full suite green at the
  final SHA: 1431 passed, 2 skipped.

## 2. What P1 built (phases 1-8)

| phase | delivered | where |
|---|---|---|
| 1 audit + data model + cost accounting | gap analysis; `SupplierTerms` (MOV, fixed order cost, receiving per receipt / per pallet, units per pallet, stepped freight tiers, per-pallet freight, max load), `Liquidity.cost_of_capital_per_period`, materiality thresholds, provenance labels, `cadence_candidates`; model rows and settlement mirror for every term; `working_capital` ledger component | `contracts.py`, `model.py`, `settlement.py`, `P1_GAP_ANALYSIS.md` |
| 2 order timing + calendars | `next_replenishment` (arrival and next realistic replenishment under order / production / shipping / receiving calendars); `SUPPLIER_CALENDAR` attribution; timing audit reused from `procurement_timing` | `economics.py` |
| 3 MOQ + case + pallet | integer lot rules already in the model (P0); attributed as `MOQ`, `CASE_ROUNDING`, `PALLET_ROUNDING` in the order a buyer applies them | `economics.py` |
| 4 MOV + multi-SKU coordination | supplier-order binary per period, `sum(q * price) >= MOV * order`; settlement raises on a below-MOV order; `MOV` attribution shares the top-up across lines | `model.py`, `settlement.py`, `economics.py` |
| 5 freight LTL / FTL / container | integer pallets per supplier order, tier binaries, per-pallet freight, maximum load; settlement prices the same tariff; `FREIGHT_ECONOMICS` attribution (pallet completion, tier landing) | same |
| 6 payment terms + financing + carrying | deposit / trigger / net days (P0); cost of capital on own cash deployed, charged after borrowing so debt interest and capital charge never overlap; carrying on asset value only | `settlement.py`, `model.py` |
| 7 joint economic optimisation | the one MILP prices all of the above jointly; `cadence_2_network` / `cadence_4_network` optional candidates when a supplier carries order-level economics; `timing_tiebreak` for indifferent timings | `planner.py`, `model.py` |
| 8 attribution + explanations + abstention | `cost_breakdown` (PURCHASE / FREIGHT / ORDERING / RECEIVING / CARRYING / FINANCING / SHORTAGE / OTHER / INVENTORY_VALUE_CHANGE, reconciling to the settlement's economic cost), `order_waterfall`, `explain_order`, `materiality` with NO MATERIAL IMPROVEMENT AVAILABLE, `provenance`, `missing_data_fallbacks`; `report["economics"]` block | `economics.py`, `planner.py` |

Every order in a report is explained as: demand until the next realistic replenishment + justified protection + lot requirements - usable on hand - usable inbound = economic need, then MOQ, case, pallet, MOV, freight tier and order-cost steps, then calendars. The attribution categories partition the ordered quantity exactly (invariant 2), and anything the arithmetic cannot explain is labelled OTHER_EXPLAINED and said so in the sentence.

## 3. Changes to selector behaviour, each with its reason and its ablation

| change | default | reason | evidence |
|---|---|---|---|
| `service_gate_basis="target"` | new field, default `target` | the V7 rule counted any fall against the incumbent's service as a worsening. Against an over-buying incumbent (replace-sold under a 400-unit MOQ runs at 100% service) every lean candidate failed `_priority_consistent` and the alternatives loop admitted a bloated service-first plan instead (fixture C review 2: 676 units bought with 357 on hand). Under the target basis a service that stays at or above its target has not worsened; below target, and in recovery mode, the strict rule stands unchanged. | arm `gate` (basis `incumbent`) in `P1_RESULT_TABLE_none_gate_incumbent.md` |
| materiality gate: NO MATERIAL IMPROVEMENT AVAILABLE | new fields `materiality_cost_fraction=.01`, `materiality_inventory_fraction=.05`, `materiality_service=.005` | a candidate that passes every gate but moves cost, carried inventory and worst service by less than the declared materiality is not worth an intervention; service counts only up to the target | fixture A (near-optimal incumbent): abstention share in the table |
| `timing_tiebreak=1e-4` | new field, objective only | with no cost of capital and a small holding rate the model was indifferent between committing cash now or later; HiGHS returned whichever it found first. The tie-break is not a cost and never enters the ledger. | `test_timing_tiebreak_prefers_later_commitment_when_the_economics_are_indifferent` |
| settlement financial tail counts dated known receivables | settlement | the model's liquidity rows already used them; the settlement's tail rule did not, so a plan the model financed on declared receivables was `OPTIMAL_PHYSICALLY_INVALID` (fixture S, every policy) | `test_terminal_financing_tail_counts_declared_receivables_like_the_model_does` |
| cost of capital charged after borrowing, own cash only | settlement (P1 code) | first draft charged it before borrowing, so credit-financed dollars carried both interest and the capital charge | `test_phase6_carrying_financing_and_capital_are_separate_and_not_double_counted` |

Untouched: P0 solve states, residual gate, settlement gate on `usable_plan`, comparable-gap ranking, REQUIRED / OPTIONAL / NOT_APPLICABLE accounting, the deficit rule (.20), the adaptive solve budget, the warm-start cascade, and every recovery-mode rule. `order_smoothing` default (.02) is untouched (see section 5).

## 4. Deviations from the pre-registration, recorded rather than hidden

1. **Review window 8 -> 11.** With an eight-review window on a twelve-period plan, a policy that defers its purchases past review 8 is never charged for the stock periods 8-11 need, while the optimizer, which plans to the end of its horizon, is charged for that stock at terminal value inside the window. Measured before the change on fixtures C / I / F / T at 8 versus 11 reviews the ranking flipped on I and T (ZAAD from 16% / 13% worse than EOQ to 6% / 7% better). The window now equals the replay's own horizon - 1 convention for every policy alike.
2. **Fixture S revised.** The first draft (opening cash 1,500, credit 1,500, no dated receivables) left every policy, the incumbent included, unable to finance week 6, because the model counts only dated known receivables as cash in. Dated receivables of 450 per week make financing binding rather than impossible.
3. **Declared stress.** A declared stress is mandatory on every request. The first draft declared the P0-style envelope (10% short fill, one week late, +5% demand). Under it the P0 stress gate, correctly, refused lean plans that stock out under the disruption, and the fixtures measured protection economics rather than cycle-stock economics. The primary arm declares a nil stress (the fitted world itself) so the gate runs but cannot dominate; the `late` arm (one week late, full fill) is kept as the sensitivity result.
4. **`order_smoothing=0` on the fixtures.** See section 5. The product default is untouched.
5. **Fixture N's `LEAD_TIME_EXPOSURE` expectation** was written on the gross requirement; with 350 units on hand the three weeks of lead-time demand are covered by on-hand and the netted attribution is correctly zero. The expectation is left failing and is explained here rather than edited.

## 5. Discontinuities and hidden terms found

| item | what it does | status |
|---|---|---|
| `order_smoothing` (.02, reliability profile) | 2% of landed unit cost per unit of period-to-period change in each source's order quantity, in the model objective only, never settled | material: about $200 of phantom cost on a 1,000-unit consolidated $5 order, the size of an undeclared fixed order cost; it spreads purchases evenly and buys early. Off on the P1 fixtures; ablation arm `smooth` shows the effect; default left for the owner to decide |
| freight tiers | one unit over a tier boundary costs the next tier (settlement test: 400 units = $800, 401 units = $1,100) | modelled exactly by tier binaries; attributed as FREIGHT_ECONOMICS when an order lands on a boundary |
| MOQ / MOV | a need of 65 units becomes an order of 400 (MOQ) or is lifted by another SKU (MOV) | modelled; attributed; the baselines are lot- and MOV-aware so no policy fails settlement on a lot rule |
| maximum load | a 9-pallet cap splits or defers demand | modelled; the EOQ baseline caps its lot at a full load |
| terminal value (.8 of price on the fixtures) | stock left at the end of a window is credited at 80% | applied identically to every policy; it is the reason the window had to equal the plan horizon |
| the confirmation draw | a candidate optimised to exactly the service floor meets it on the selection worlds and fails it on an independent draw about half the time | P0 behaviour, unchanged; it is why `base_stock` (which over-serves) is sometimes the accepted candidate at review 0 on lean fixtures |

## 6. Provenance and missing-data fallbacks

Every economic input in a report carries one of CUSTOMER_PROVIDED / INFERRED_FROM_HISTORY / CONFIGURED_ASSUMPTION / NOT_AVAILABLE (`economics.provenance`). An undeclared non-zero figure is CONFIGURED_ASSUMPTION; an undeclared zero is NOT_AVAILABLE. On the fixtures every figure is CONFIGURED_ASSUMPTION or NOT_AVAILABLE (invariant 6: no CUSTOMER_PROVIDED label appears). Fallbacks are stated in the report (`missing_data_fallbacks`):

- cost of capital NOT_AVAILABLE: payment timing is valued only through interest on drawn credit, and the timing tie-break prefers later commitment;
- holding rate NOT_AVAILABLE: carrying is zero and inventory is compared on value only;
- a freight tariff without pallet sizes, or with a pallet size missing for one SKU: pallet economics disabled for that supplier, said so;
- no supplier terms: MOV, fixed order cost, receiving and tariffs NOT_AVAILABLE, per-unit source costs only.

No generic industry rate is hard-coded anywhere; the holding, capital and interest rates on the fixtures are declared per fixture and converted from annual to per-period by `annual_to_period`.

## 8. Commercial sanity questions

| | question | answer from the evidence |
|---|---|---|
| A | Can ZAAD tell a buyer to order nothing? | Yes. Fixture P (six weeks on hand) - ZAAD buys nothing for the first reviews while the replace-sold incumbent keeps buying; cost and inventory in the table. |
| B | Does it ever recommend less than the incumbent? | Yes - every fixture with a replace-sold incumbent under a lot rule (B, C, F, G, L, T). |
| C | Does it ever recommend more / earlier? | Yes - consolidation into a full load (I: 450 units at once; G / T: the whole horizon's demand in one tiered load) and the low-stock fixture O. |
| D | Can it say "no material improvement"? | Yes - the NO MATERIAL IMPROVEMENT AVAILABLE verdict on fixture A and on individual reviews elsewhere (review outcomes in the jsonl). |
| E | Does every order come with a reason a buyer would accept? | Each period-0 order carries a one-sentence explanation built from the waterfall (examples in section 9); the unexplained remainder is named as such. |
| F | Are MOQ, case, pallet, MOV and freight shown as costs, not hidden in "safety stock"? | Yes - they are separate attribution categories and, for freight, ordering and receiving, separate cost components that reconcile to the settlement. |
| G | Is cash timing valued? | Only when a cost of capital is declared (J vs K: net-60 versus 30% deposit at order differ in FINANCING alone, PURCHASE identical). Without it the report says NOT_AVAILABLE. |
| H | Does a cheaper plan that stocks out get through? | No - the service floor, the independent confirmation and the stress gate are unchanged from P0; the target-basis change only stops an above-target fall from counting as a worsening. |
| I | Is the comparison fair to the incumbent? | The incumbent is the operator's declared rule projected from the same snapshot every review, and the baselines are lot-, MOV-, load- and cash-aware. Deliberately weak baselines were not used; where a baseline fails a fixture it is because the fixture forbids its behaviour (unfinanceable lot), and that is shown as FAILED, not hidden. |
| J | What is the number a CFO should not believe? | Any TOTAL COST DELTA on these fixtures. They are development fixtures with configured economics; the deltas show the mechanisms work and reconcile, not what a customer will save. |

## 9. Persona review

- **Buyer / planner:** the explanation names the cadence, the lot rule and the tariff step that shaped the quantity, and nets off what is on hand and inbound. What is missing: a "what if I order half" counterfactual; that is P2 material.
- **Finance:** components reconcile to the cent; working capital and financing are separate from carrying; the capital charge is only on own cash. What finance will ask for and does not get here: a customer-provided cost of capital and holding rate (both CONFIGURED_ASSUMPTION on every fixture).
- **Supply-chain director:** cadence and consolidation are explicit candidates, not side effects; the freight tier and the FTL cap are respected by every plan. The `order_smoothing` finding is the item to decide on.
- **Sceptical engineer:** the target-basis gate is a real change to selector semantics and is the one item that could be argued; the ablation arm quantifies it. Fixture expectations were changed in three recorded places (window, S, N) and nowhere else.

## 7. Where ZAAD P1 loses, and why (no fix applied)

| fixture | ZAAD vs best baseline | cause from the review logs |
|---|---|---|
| C MOQ four weeks | +3.7% (seed 41001 alone: -2.3%) | under a 400-unit MOQ with no order cost and no cost of capital the model places its second lot as soon as it is cheaper than a stock-out on the scenario worlds, one to two reviews before the reorder-point rule does; the extra units end the window at terminal value. The timing tie-break is deliberately too small to move a lot-sized decision. |
| O low opening stock | +2.8% | an early stockout is unavoidable for every policy (review 0: "requested service targets are not jointly achievable"); ZAAD then runs on the 95% floor and pays shortage in the weeks realised demand exceeds the forecast, where the reorder-point rule's z-protection happens to cover it. |
| P high opening stock | +2.1% | same mechanism from review 5 on; on the `late` arm ZAAD is the cheapest policy. |

The common thread is that with a nil stress and an expected-service floor ZAAD's chosen plan sits
on the floor, and the independent truth draw lands above or below it. That is P0 behaviour and it
was not changed to make these pass. On the fixtures where order-level economics exist (B, F, G, H,
I, J, K, L, S, T) ZAAD P1 is the cheapest policy or within 1.6% of it.

Attribution expectations that fail: N expected LEAD_TIME_EXPOSURE but the three weeks of lead-time
demand are covered by the 350 units on hand, so the netted category is correctly zero; R expected
MOV but a $3,000 MOV against $5,500 of weekly demand at those prices never binds. Both are fixture-
design errors, left failing and explained.

## 10. Pass gate (reconstructed from the brief's requirements; 24 items)

| # | item | result |
|---|---|---|
| 1 | data model explicit (SupplierTerms, cost of capital, materiality, provenance, cadence) | PASS |
| 2 | units correct and stated (units, cases, pallets, currency per period, annual->period conversion explicit) | PASS |
| 3 | provenance on every economic input; missing data named, never invented | PASS |
| 4 | no duplicated economics (per-line fee vs supplier order cost; holding vs interest vs capital) | PASS |
| 5 | model and settlement carry the same rows (MOV, tiers, pallets, receiving, capital) | PASS |
| 6 | cost components reconcile to the settlement's economic cost | PASS (1,200 / 1,200 cells) |
| 7 | attribution partitions every order exactly | PASS |
| 8 | invariants script green | PASS (60 / 60) |
| 9 | timing under supplier calendars; next realistic replenishment | PASS |
| 10 | MOQ / case / pallet respected and attributed | PASS |
| 11 | MOV coordinated across SKUs | PASS |
| 12 | freight tiers, per-pallet freight, maximum load | PASS |
| 13 | payment terms, financing, carrying, capital with no double count | PASS |
| 14 | joint optimisation with cadence candidates | PASS |
| 15 | plain-language explanation per order | PASS |
| 16 | NO MATERIAL IMPROVEMENT AVAILABLE with configurable materiality | PASS |
| 17 | competent baselines, none deliberately weak | PASS |
| 18 | fixtures A-T pre-registered; deviations recorded | PASS with 5 recorded deviations |
| 19 | ZAAD not worse than the best baseline within tolerance on every fixture | **FAIL** (C, O, P) |
| 20 | pre-registered attribution expectations | **FAIL** (N, R: expectations wrongly written) |
| 21 | service floors respected; no physical failure of an accepted plan | PASS |
| 22 | runtime inside budget | PASS |
| 23 | Network Twin, frontend, Vercel, other worktrees, P0 evidence untouched; no Validation7 / 8 / holdout4; nothing merged; P2 and sector physics not started | PASS |
| 24 | verdict not softened | PASS (this document) |


## 9a. Explanation examples (period-0 orders of the first review, seed 41001, verbatim from the report)

- **B_fixed_order_cost_replace_sold**: Order 1058 units of A from supplier at review 0 (arrives period 1): 48 covers demand from arrival until the next realistic replenishment (period 2); 15 is service protection (LEAN); 996 extends cover by about 10.1 periods, avoiding about 10.1 orders ($2,516 in order-level costs) against about $72 of extra carrying and capital. Usable on hand 150 and inbound 0 were netted off.
- **I_max_pallets_ftl_cap**: Order 408 units of A from supplier at review 0 (arrives period 1): 48 covers demand from arrival until the next realistic replenishment (period 2); 15 is service protection (LEAN); 346 completes the pallet load or the freight tier the order lands on. Usable on hand 150 and inbound 0 were netted off.
- **T_combined_realistic**: Order 168 units of A from supplier at review 0 (arrives period 1): 48 covers demand from arrival until the next realistic replenishment (period 2); 15 is service protection (LEAN); 9 is case rounding; 60 lifts the supplier order to its minimum order value; 36 completes the pallet load or the freight tier the order lands on. Usable on hand 150 and inbound 0 were netted off. Order 168 units of B from supplier at review 0 (arrives period 1): 48 covers demand from arrival until the next realistic replenishment (period 2); 15 is service protection (LEAN); 9 is case rounding; 60 lifts the supplier order to its minimum order value; 36 completes the pallet load or the freight tier the order lands on. Usable on hand 150 and inbound 0 were netted off.
- **P_high_opening_stock**: (no period-0 order: the plan buys nothing this review)
- **M_order_calendar_wednesday**: Order 168 units of A from supplier at review 0 (arrives period 2): 48 covers demand before it lands in period 2; 99 covers demand from arrival until the next realistic replenishment (period 3); 19 is service protection (LEAN); 3 is not explained by the waterfall arithmetic (the joint solve found it cheaper; see the cost comparison). Usable on hand 150 and inbound 0 were netted off.

## 11. Final state

- Code and evidence at the SHA recorded in the last commit of `claude/zaad-cycle-stock-p1` (parent `2e30721`).
- Unit tests: 1431 passed, 2 skipped (full suite, final SHA). P1 tests: 23.
- Evidence files: `P1_GAP_ANALYSIS.md` (with amendment), `P1_RESULT_TABLE_{none,none_gate_incumbent,late,none_smoothing_0.02}.md`,
  `P1_EXPECTATIONS_*.json`, `P1_RUNTIME_*.json`, `fixtures_{none,gate,late,smooth}.jsonl`, `P1_INVARIANTS.json`, this file.
- Not started: P2 (network pooling, central versus local protection, transfer service windows, echelon accounting) and
  full sector physics (expiry / FEFO / cold chain / promotions).
- Untouched: Validation7, Validation8, holdout4 (unrun); Network Twin / PR #39; frontend; Vercel; production; other worktrees;
  P0 evidence (referenced only). Nothing merged. PR #38 and PR #39 remain as they were.
- Not claimed: production ready, industry proven, customer validated, guaranteed savings, optimizer complete.

**Recommended next step (not executed):** decide the two selector defaults this pass surfaced, with the P0
six-cell confirmation as the check: (1) whether `order_smoothing` should default to 0 whenever a supplier
declares order-level economics, and (2) whether `service_gate_basis="target"` should stand as the product
default. Then close the three fixture-parity exceptions by measuring the confirmation knife-edge (a
candidate optimised to exactly the service floor failing an independent draw) rather than by widening
any tolerance.


# CLOSURE PASS (2026-09-08, second pass on this close-out)

**Verdict after the closure pass: P1 CYCLE-STOCK ECONOMICS — REMAINS OPEN.**

Fixture parity now holds on 17 of 20 pre-registered fixtures at the original 2% tolerance, O and
P included; C remains outside at +2.3%. Two attribution expectations (N, R) are proven invalid by
the fixtures' own arithmetic and are left in the record as failing. No tolerance was widened, no
fixture, seed, window or baseline was changed, no expectation was edited.

## C1. Evidence lock

Recorded before any code change in `P1_CLOSURE_LOCK.md`: fixture definitions, seeds (41001-41003), window (11 reviews of a 12-period weekly plan), the 2% parity tolerance, the P1 defaults at SHA 3773944 and the five earlier deviations. None of C, O, P, their seeds, expectations, window or baselines was changed in this pass.

## C2. Root causes (decision-time versus truth-time trace, `closure/cop_trace.json`, `scripts/p1_cop_trace.py`)

| fixture | causal category | mechanism, with the numbers that establish it |
|---|---|---|
| O (low opening stock) and P (high opening stock), steady state | **1. SCENARIO COVERAGE** | Three iid scenario worlds let the plan protect only against the largest of three draws per period (median: the 79th percentile). The plan's projected service on those worlds sat 3-4 points above the 95% target (mean +0.031 / +0.036, never a knife-edge in projection), yet realised weekly service fell to .86-.94 whenever truth demand exceeded the best sampled draw, in 30-40% of weeks. The waterfall said "15 units of service protection" while the order was 12-17 units *below* the arithmetic need: the plan held no protection because its worlds never showed the tail. Same sign on every seed and both fixtures: systematic, not sampling noise. Economically the model was wrong on its own inputs: a stockout costs $7.5 net per unit, protection $0.014 per unit-period. |
| O, reviews 0-1 | **3. SELECTION (P0 recovery rule, left as is)** | With 20 units on hand and a one-week lead the review-0 stockout is unavoidable for every policy (78 units). The review is in recovery mode; P0's rule admits a candidate only if it *materially improves* the weighted shortfall, which nothing can, so the declared periodic incumbent's 294-unit order stands against the reorder-point baseline's 192. Reviews 0-1 are $185 of O's $152 total gap: over the other nine reviews ZAAD is net $33 better than the best baseline. This rule is P0 recovery logic and was not changed. |
| C (400-unit MOQ) | **5. HORIZON / TERMINAL EFFECT** | Under the MOQ the horizon-optimal plan buys the rest of the window in one lot (453, 608-618) rather than two 400s, and at the last reviews buys a 400 lot for a 38-56-unit expected deficit; the leftover is credited at the 80% terminal value inside the window. With the haircut removed (diagnostic only, plans unchanged) the gap is +1.58% before the fix and +1.58% after it, against +3.7% / +4.0% with it. The remainder is lot timing under an MOQ with near-zero holding and no cost of capital. |

The knife-edge hypothesis (step D) is rejected for all three: chosen-plan projected service minus target was +0.043 (C), +0.031 (O), +0.036 (P) on average and the per-world minimum was above the target on most reviews. The gap is between the sampled worlds and the truth's tail, not between the plan and the floor.

## C3. Calibration check (step E)

Demand quantiles: truth and scenario paths are drawn from the same bootstrap of the fixture history (sizes 89-111, sd 6); the fitted spread is right. Fill and lead distributions: deterministic on these fixtures (fill .98, lead 7 days). Correlation: none in truth. Sampling count: three. Scenario weighting: equal. Service floor: expected unit fill over the horizon and worlds. The under-representation is the sampling count combined with equal weights: the expectation is unbiased but the plan reacts to the realised sample, and with three draws the tail beyond the target is absent from most reviews. The fix therefore changes the representation, not the target and not a margin.

## C4. The fix (step H) and what it is not

1. **Target-stratified scenario worlds** (`worlds.draw`, `forecast.sample`, request field `stratified_scenarios=True`): S-1 body worlds drawn below the lowest service target (weight target/(S-1) each) and one tail world drawn above it (weight 1-target). Stratified sampling of the same fitted distribution: unbiased, no margin, the tail always present at its probability mass. The tail world varies per-period noise at the fitted level; the level shock and young-regime mixture stay in the body worlds (the unconditional form fabricated a path above an old demand regime and failed `test_young_regime_is_bounded_mixture_not_symmetric_widening`). Single-world and deterministic draws, which are every benchmark's truth path, are bit-identical to before (tested).
2. **Weight-aware selector statistics** (`planner._wmean`, `_service_value`, bootstrap, burden, materiality): every mean over evaluation rows respects scenario weights and reduces to the former plain mean under equal weights (tested), so equal-weight paths are unchanged.
3. **Leanness may not be bought with service** (`plan`, V7 ranking branch): inside the cost band the leanest plan wins only among plans whose expected shortage exposure on the selection worlds is no larger than the cheapest plan's. Before, a plan with no protection that paid the resulting shortage was "leanest" whenever that shortage cost less than the 5% band, which on a purchase-dominated cost is far more than protection costs to carry.
4. **Lean reviews only.** Items 1 and 3, and the target service-gate basis, apply when the review is lean: calm screen state (NO_ACTION, NORMAL_REPLENISHMENT, CAPITAL_OPTIMIZATION) and no active risk driver on any SKU/location. Under PROTECT, RECOVER, NETWORK_ALLOCATION, ESCALATE_UNKNOWN or any active driver, P0's own downside representation and rules stand unchanged. This split is the brief's NORMAL/LEAN versus RECOVERY/DISRUPTION line, and it was forced by evidence: the unconditional target gate and the unconditional stratified worlds each lost service on P0 cells 20 and 21 (section C5).

Not done: no safety-stock layer, no target + margin, no scenario-count change on the fixtures, no change to C/O/P definitions, seeds, window, tolerance or baselines, no change to any P0 recovery rule.

## C5. The two defaults against the frozen P0 six-cell set (step B)

Cells 15/16/20/21/90/108, seed 38001, the P0 close-out's own configuration (`scripts/p1_p0_arms.py`, `closure/p0_arm_*.json`).

ARM A (P1 code, P0 behaviour: incumbent gate, smoothing .02, no tie-break, no materiality gate) reproduces the P0 record: cells 15/16/20/90/108 identical to `final8_clean_warm_rule_deficit`; cell 21 within the recorded run-to-run band of time-limited solves (service .760 / breaches 5 / unmet 93 identical; inventory 130.5 vs 144.8).

ARM C (conditional smoothing) is identical to ARM A by construction: none of the six cells declares supplier terms or a fixed order fee, so `effective_smoothing` returns the declared .02 on every one (checked programmatically; recorded in the transcript of this pass).

**Timing tie-break (step G).** The coefficient is applied per unit-period of earliness scaled by 1/(H-1), so its total objective contribution is bounded by `timing_tiebreak` x purchase value: at the default that is 1e-4 of spend, two orders of magnitude below the 1% cost materiality and below the solver's own relative gap on any plan above $100. Proved by `test_timing_tiebreak_total_is_bounded_by_its_coefficient_times_purchase_value` at H=12 and H=30. It never enters projected cost or the ledger (`test_random_identical_world_reconciliation` reconciles model and settlement exactly). Decision: keep 1e-4, objective-only, horizon-scaled.

**Smoothing (step B2).** Decision: `order_smoothing` is applied only when the request declares no explicit order economics (no supplier terms, no per-line fixed order fee); with explicit economics it is switched off, because the proxy then double-counts lumpiness as an undeclared order cost (about 2% of landed cost per unit of change, roughly $200 on a 1,000-unit $5 order). The P0 default value .02 is unchanged and P0 cells are unaffected.

## C6. Default decisions (step B, concluded)

| default | decision | evidence |
|---|---|---|
| `service_gate_basis` | **"incumbent" (P0 rule) stays the default.** The target basis remains a request option, applied only on lean reviews when chosen. | Unconditional target gate on the P0 six-cell set: cell 20 service .894 -> .818 (6 breaches), cell 21 .760 -> .703 with one starved required class, cell 90 4 -> 5 breaches, cell 108 unmet 69.8 -> 76.0. Once the scenario representation was corrected, the fixtures the gate was introduced for pass without it (I +1.7%, O +1.7%, P -0.5% under the incumbent gate). |
| `stratified_scenarios` and the band guard | **default on, lean reviews only** (calm screen state, no active risk driver). | Unconditional: cell 20 .894 -> .792, cell 21 .760 -> .746. Lean-only with the incumbent gate: see the `final_incgate` row of the P0 table. |
| `order_smoothing` | **value .02 unchanged; applied only without explicit order economics.** | Identical to P0 on all six cells (none declares supplier terms or order fees; `effective_smoothing` returns .02 on each). On the fixtures the smoothing ablation moved C from +2.3% to +3.2% and F from +1.5% to +1.5% (categories), confirming the proxy fights consolidation where order economics exist. |
| `timing_tiebreak` | **1e-4, objective only, horizon-scaled.** | Bounded by 1e-4 x purchase value at any horizon (test at H=12 and H=30); never in projected cost or the ledger. |

## C7. Invalid expectations, proven (gate item 1)

Two pre-registered attribution expectations cannot hold by the fixture's own arithmetic. Neither fixture was edited; the checks stay in the record marked as proven invalid.

- **N (`LEAD_TIME_EXPOSURE` expected).** Lead-time demand is the fitted mean 98.9 x 3 periods = 297 units; usable on hand is 350; the netted category is max(0, 297 - 350) = 0 in every seed. The expectation was written on the gross requirement, which the waterfall (correctly) nets against on hand first.
- **R (`MOV` expected).** One period of mean demand at list prices is 100 x $5 + 100 x $50 = $5,441 per order against a $3,000 minimum order value: the MOV never binds on any order covering at least one period, so no MOV units can be attributed. The fixture was meant to make the MOV bind on the cheap line and was mis-sized.

## C8. Residual C, named

C fails parity at +2.3% (tolerance 2%). Cause 5, horizon/terminal: under a 400-unit MOQ the horizon-optimal plan buys the rest of the window in one lot and any last-review lot for a small expected deficit, and the leftover is credited at 80% of price inside the twelve-week window; with the haircut removed as a diagnostic (plans unchanged) C is +1.6%. Not sampling noise: the sign is the same on every seed. Not a systematic calibration problem: the demand representation is now correct on the fixtures where it mattered (O, P). Not changed: terminal value, window, MOQ, tolerance. The best next intervention is to value end-of-window stock at its continuation value in the benchmark rather than at salvage, which is a benchmark-design decision, not an optimizer change, and is not made here.


## C9. Targeted rerun (step I) and full A-T rerun (step J), final defaults

Targeted (C, O, P plus controls T, A, G, Q; `closure/targeted_fix3.json`): P +0.72%, O +2.37%, C
+4.03% under the target gate; the full run below is at the final defaults (incumbent gate).

Primary arm (nil declared stress, P1 defaults; `P1_RESULT_TABLE_none.md`, `fixtures_none.jsonl`):

17 / 20 fixtures pass

| fixture | incumbent | best baseline | ZAAD P1 | ZAAD vs incumbent | ZAAD vs best baseline | checks |
|---|---|---|---|---|---|---|
| A_no_terms_good_incumbent | 5,824 | 5,824 (incumbent) | 5,825 | +0.0% | +0.0% | PASS |
| B_fixed_order_cost_replace_sold | 8,528 | 6,995 (economic_lot) | 6,262 | -26.6% | -10.5% | PASS |
| C_moq_four_weeks | 9,595 | 5,898 (reorder_point) | 6,034 | -37.1% | +2.3% | FAIL: zaad_not_worse |
| D_case_multiple | 5,807 | 5,807 (incumbent) | 5,771 | -0.6% | -0.6% | PASS |
| E_pallet_multiple | 6,239 | 6,239 (incumbent) | 6,239 | +0.0% | +0.0% | PASS |
| F_mov_two_skus | 14,040 | 11,766 (periodic:2) | 11,852 | -15.6% | +0.7% | PASS |
| G_freight_tiers | 21,400 | 16,720 (economic_lot) | 14,793 | -30.9% | -11.5% | PASS |
| H_per_pallet_freight | 6,884 | 6,826 (periodic:2) | 6,524 | -5.2% | -4.4% | PASS |
| I_max_pallets_ftl_cap | 16,274 | 9,814 (economic_lot) | 9,981 | -38.7% | +1.7% | PASS |
| J_net60_cost_of_capital | 7,478 | 6,850 (periodic:2) | 6,097 | -18.5% | -11.0% | PASS |
| K_deposit_early_cash | 7,490 | 6,862 (periodic:2) | 6,097 | -18.6% | -11.1% | PASS |
| L_high_holding_rate | 7,434 | 6,856 (periodic:2) | 6,165 | -17.1% | -10.1% | PASS |
| M_order_calendar_wednesday | 6,256 | 6,256 (incumbent) | 6,209 | -0.7% | -0.7% | PASS |
| N_long_lead_21_days | 5,937 | 5,937 (incumbent) | 6,043 | +1.8% | +1.8% | FAIL: categories |
| O_low_opening_stock | 6,521 | 6,399 (reorder_point) | 6,506 | -0.2% | +1.7% | PASS |
| P_high_opening_stock | 6,282 | 5,786 (reorder_point) | 5,758 | -8.3% | -0.5% | PASS |
| Q_volatile_demand_high_target | 5,971 | 5,971 (incumbent) | 5,971 | +0.0% | +0.0% | PASS |
| R_asymmetric_prices_mov | 63,448 | 63,448 (incumbent) | 63,941 | +0.8% | +0.8% | FAIL: categories |
| S_cash_constrained | 6,924 | 6,234 (economic_lot) | 6,176 | -10.8% | -0.9% | PASS |
| T_combined_realistic | 24,255 | 17,593 (economic_lot) | 15,598 | -35.7% | -11.3% | PASS |

ZAAD P1 mean service across the 60 gated cells 0.990; interventions 371 of 660 reviews,
NO MATERIAL IMPROVEMENT AVAILABLE on 6; attribution residual zero on every cell (partitions
exact); components reconcile to the settlement on every cell of every arm; invariants 60 / 60.

Arms (same fixtures and seeds):

| arm | passing | C | O | P |
|---|---|---|---|---|
| late | 16 / 20 | +2.38% | -0.07% | +0.66% |
| none | 17 / 20 | +2.31% | +1.67% | -0.48% |
| none_gate_target | 15 / 20 | +4.03% | +2.37% | +0.72% |
| none_smoothing_0.02 | 17 / 20 | +5.98% | +0.99% | -0.75% |

The target-gate arm is the ablation of the reverted default: with the representation fixed, the
target basis makes C, O and P worse. The smoothing arm shows the proxy's cost where order
economics exist (C +2.3% -> +6.0%).

Runtime, primary arm: p50 0.11 s, p90 0.92 s, p95 1.47 s, max
16.6 s per review; 87 s for the arm on three workers (the `late` arm took 913 s on
the same machine while a P0 cell ran alongside it; its per-review p95 is 1.9 s).

## C10. P0 six-cell arms (step B3)

| arm | cell | service | p10 | breaches | unmet | worst | inventory | cost | required done/req | starved | joint req/built/chosen | lat p50 | p95 | max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | 15 | 0.983 | 1.000 | 1 | 4.2 | 4.2 | 50.0 | 1576 | 34/36 | **0** | 0/0/0 | 0.14 | 1.1 | 1.2 |
| final | 16 | 0.972 | 1.000 | 1 | 7.0 | 7.0 | 134.5 | 1515 | 30/36 | **0** | 0/2/0 | 0.13 | 1.0 | 3.9 |
| final | 20 | 0.916 | 0.000 | 3 | 32.3 | 17.0 | 203.2 | 2475 | 52/59 | **0** | 0/2/1 | 0.15 | 29.8 | 55.0 |
| final | 21 | 0.746 | 0.000 | 6 | 98.3 | 27.0 | 148.0 | 3590 | 47/65 | **0** | 9/14/6 | 0.78 | 29.4 | 54.7 |
| final | 90 | 0.863 | 0.220 | 4 | 70.1 | 22.0 | 121.0 | 3405 | 63/72 | **0** | 2/6/2 | 1.00 | 87.1 | 113.6 |
| final | 108 | 0.890 | 0.308 | 4 | 63.0 | 20.9 | 116.1 | 3677 | 74/78 | **0** | 2/6/1 | 7.19 | 133.1 | 153.1 |
| final_incgate | 15 | 0.983 | 1.000 | 1 | 4.2 | 4.2 | 50.0 | 1576 | 34/36 | **0** | 0/0/0 | 0.14 | 0.9 | 1.1 |
| final_incgate | 16 | 0.972 | 1.000 | 1 | 7.0 | 7.0 | 134.5 | 1515 | 30/36 | **0** | 0/2/0 | 0.13 | 1.0 | 4.0 |
| final_incgate | 20 | 0.916 | 0.000 | 3 | 32.3 | 17.0 | 203.2 | 2475 | 52/59 | **0** | 0/2/1 | 0.15 | 29.9 | 55.3 |
| final_incgate | 21 | 0.746 | 0.000 | 6 | 98.3 | 27.0 | 148.0 | 3580 | 47/65 | **0** | 9/14/5 | 0.69 | 29.9 | 55.2 |
| final_incgate | 90 | 0.863 | 0.220 | 4 | 70.1 | 22.0 | 121.0 | 3405 | 63/72 | **0** | 2/6/2 | 0.98 | 85.7 | 113.6 |
| final_incgate | 108 | 0.890 | 0.308 | 4 | 63.0 | 20.9 | 116.1 | 3677 | 74/78 | **0** | 2/6/1 | 6.84 | 133.1 | 153.1 |
| final_unconditional | 15 | 1.000 | 1.000 | 0 | 0.0 | 0.0 | 124.5 | 1620 | 36/36 | **0** | 0/0/0 | 0.11 | 1.2 | 5.1 |
| final_unconditional | 16 | 0.972 | 1.000 | 1 | 7.0 | 7.0 | 160.2 | 1428 | 36/36 | **0** | 0/0/0 | 0.11 | 0.8 | 1.2 |
| final_unconditional | 20 | 0.792 | 0.000 | 7 | 80.6 | 18.9 | 176.5 | 2720 | 43/59 | **0** | 4/7/1 | 0.27 | 26.2 | 46.5 |
| final_unconditional | 21 | 0.746 | 0.000 | 6 | 98.3 | 27.0 | 121.6 | 3215 | 46/64 | **0** | 9/12/5 | 0.65 | 24.7 | 45.3 |
| final_unconditional | 90 | 0.859 | 0.223 | 5 | 72.3 | 22.0 | 271.8 | 3350 | 75/81 | **0** | 4/6/2 | 1.05 | 50.6 | 85.3 |
| final_unconditional | 108 | 0.906 | 0.308 | 4 | 54.0 | 21.0 | 275.0 | 3652 | 85/85 | **0** | 1/11/1 | 1.63 | 113.7 | 147.5 |
| gate | 15 | 1.000 | 1.000 | 0 | 0.0 | 0.0 | 63.2 | 1612 | 36/36 | **0** | 0/0/0 | 0.13 | 2.2 | 5.1 |
| gate | 16 | 0.972 | 1.000 | 1 | 7.0 | 7.0 | 137.1 | 1425 | 36/36 | **0** | 0/0/0 | 0.09 | 1.1 | 1.1 |
| gate | 20 | 0.818 | 0.159 | 6 | 70.6 | 21.5 | 179.7 | 2678 | 53/67 | **0** | 8/9/3 | 0.21 | 26.5 | 57.8 |
| gate | 21 | 0.703 | 0.000 | 6 | 115.0 | 27.0 | 114.4 | 3362 | 47/65 | **1** | 11/11/5 | 0.46 | 26.0 | 58.5 |
| gate | 90 | 0.859 | 0.223 | 5 | 72.4 | 22.0 | 103.8 | 3360 | 63/72 | **0** | 4/8/0 | 0.36 | 63.2 | 100.2 |
| gate | 108 | 0.868 | 0.221 | 5 | 76.0 | 22.0 | 91.1 | 3696 | 64/76 | **0** | 2/8/2 | 1.49 | 122.9 | 153.1 |
| p0_defaults | 15 | 0.980 | 0.962 | 1 | 5.0 | 4.2 | 46.1 | 1678 | 32/36 | **0** | 0/1/0 | 0.13 | 1.3 | 1.6 |
| p0_defaults | 16 | 0.972 | 1.000 | 1 | 7.0 | 7.0 | 134.5 | 1515 | 30/36 | **0** | 0/2/0 | 0.13 | 0.8 | 2.5 |
| p0_defaults | 20 | 0.894 | 0.233 | 3 | 40.9 | 14.0 | 183.7 | 2502 | 50/58 | **0** | 0/3/2 | 0.17 | 25.6 | 59.8 |
| p0_defaults | 21 | 0.760 | 0.000 | 5 | 93.0 | 27.0 | 130.5 | 3257 | 45/61 | **0** | 7/10/5 | 0.74 | 30.0 | 60.2 |
| p0_defaults | 90 | 0.863 | 0.220 | 4 | 70.1 | 22.0 | 94.4 | 3315 | 57/64 | **0** | 1/3/1 | 0.81 | 81.1 | 113.7 |
| p0_defaults | 108 | 0.879 | 0.225 | 4 | 69.8 | 22.0 | 138.6 | 3723 | 74/78 | **0** | 0/5/1 | 3.20 | 133.0 | 153.1 |
| representation_only | 15 | 0.980 | 0.962 | 1 | 5.0 | 4.2 | 46.1 | 1678 | 32/36 | **0** | 0/1/0 | 0.12 | 1.3 | 2.3 |
| representation_only | 16 | 0.972 | 1.000 | 1 | 7.0 | 7.0 | 134.5 | 1515 | 30/36 | **0** | 0/2/0 | 0.13 | 0.9 | 3.9 |

Reading: `p0_defaults` (P1 code, P0 behaviour) reproduces the frozen record. `gate`
(unconditional target basis) regresses 20, 21, 90, 108. `final_unconditional` (stratified worlds
and guard everywhere) regresses 20 and 21. `final` and `final_incgate` (lean reviews only)
improve 15, 20 and 108, leave 16 identical, and move 21 (service -.014, cost +10%) and 90
(inventory +28% at identical service, joint recovery chosen on 2 reviews instead of 1). Required
starvation is zero in every arm and cell 21's recovery behaviour (joint recovery required and
chosen) is intact throughout. `representation_only` isolates the stratified worlds and guard from
the materiality gate and the tie-break: see C11.

## C11. Default decision after the isolating arm, and the final product defaults

`representation_only` (stratified worlds and band guard on lean reviews, P0 gate, no tie-break,
materiality gate off) against `p0_defaults`:

| cell | service | breaches | unmet | inventory | cost | starved | joint req/built/chosen |
|---|---|---|---|---|---|---|---|
| 15 | .980 -> .980 | 1 -> 1 | 5.0 -> 5.0 | 46.1 -> 46.1 | 1678 -> 1678 | 0 | 0/1/0 -> 0/1/0 |
| 16 | .972 -> .972 | 1 -> 1 | 7.0 -> 7.0 | 134.5 -> 134.5 | 1515 -> 1515 | 0 | 0/2/0 -> 0/2/0 |
| 20 | .894 -> .894 | 3 -> 3 | 40.9 -> 40.9 | 183.7 -> 183.7 | 2502 -> 2502 | 0 | 0/3/2 -> 0/3/2 |
| 21 | .760 -> .760 | 5 -> 5 | 93.0 -> 93.0 | 130.5 -> 147.5 (P0 record 144.8) | 3257 -> 3381 (record 3364) | 0 | 7/10/5 -> 9/14/5 (record 9/13/6) |
| 90 | .863 -> .858 | 4 -> 5 | 70.1 -> 72.6 | 94.4 -> 140.4 | 3315 -> 3388 | 0 | 1/3/1 -> 2/6/0 |
| 108 | .879 -> .885 | 4 -> 4 | 69.8 -> 65.9 | 138.6 -> 142.0 | 3723 -> 3673 | 0 | 0/5/1 -> 1/5/1 |

Cells 15, 16 and 20 are identical; cell 21 is identical on service, breaches and unmet and inside
the recorded run-to-run band on inventory and cost; cell 108 is better. Cell 90 is a genuine
regression: 49% more inventory, one more breach, service .863 -> .858, at the cell the P0 freeze
names for "no unnecessary joint protection". Required starvation is zero everywhere and cell 21's
recovery behaviour is intact. By the rule of this pass (a default that regresses P0 does not ship
as default), the representation is not the default.

The bundled arms (`final`, `final_incgate`) additionally moved cell 21 (service -.014, cost
+10%) and cell 15 (better); with the representation alone neutral on both, that movement belongs
to the materiality gate and the timing tie-break, which this pass did not separate.

**Final product defaults (all P0 behaviour, one provable no-op added):**

| field | default | P1 fixtures declare | why |
|---|---|---|---|
| `service_gate_basis` | `incumbent` (P0) | `incumbent` | unconditional target gate regressed 20/21/90/108; not needed once the representation is fixed |
| `stratified_scenarios` (with the band guard) | `False` | `True` | regresses cell 90 |
| `materiality_*` thresholds | 0 (gate off) | .01 / .05 / .005 | bundled movement on 21/90 not separated from the tie-break |
| `timing_tiebreak` | 0 | 1e-4 | same; bounded at 1e-4 of spend when on |
| `order_smoothing` | .02, applied only without explicit order economics | 0 | identical to P0 on every cell without order economics |

So the product's default behaviour on the P0 set is the frozen P0 behaviour (`p0_defaults` arm
reproduces the record), and the P1 result below is a result under declared request settings, not
under product defaults. That is stated as such and is one of the reasons P1 remains open.

## C12. Final state of the closure pass

- Unit tests at the final code state: 1436 passed, 2 skipped (final baseline was 1431 + 2; the 5 additions are the closure tests: stratified worlds, weighted statistics, conditional smoothing, tie-break bound, attributable protection).
- Invariants: 60 / 60. Attribution residual zero on every gated cell. Components reconcile to the settlement on every cell of every arm.
- Full A-T at the final code (declared fixture settings): 17 / 20. C +2.31% (parity), N and R attribution expectations proven invalid (C7). O +1.67%, P -0.48%, I +1.71%.
- P0 six-cell set under product defaults: identical to the frozen record (`p0_defaults`).
- Evidence files: `P1_CLOSURE_LOCK.md`, `closure/cop_trace.json`, `closure/p0_arm_{p0_defaults,gate,final_unconditional,final,final_incgate,representation_only}.json`, `closure/targeted_fix*.json`, `closure/TABLES.md`, `P1_RESULT_TABLE_*.md`, `P1_EXPECTATIONS_*.json`, `P1_RUNTIME_*.json`, `fixtures_*.jsonl`, `P1_INVARIANTS.json`.
- Not started: P2 and sector physics. Untouched: Validation7, Validation8, holdout4 (unrun, not inspected), Network Twin / PR #39, PR #38, frontend, Vercel, production, other worktrees. Nothing merged, pushed or opened.
- Not claimed: industry standard complete, production ready, customer validated, guaranteed savings.

**What was explicitly refused:** widening the 2% tolerance; editing C, O, P, their seeds, window, expectations or baselines; a generic safety margin; shipping any default that regressed a P0 cell; calling the C residual noise (it is the terminal haircut, same sign on every seed); calling the O/P finding noise (it was a systematic representation gap, now fixed under declared settings).

**Best next intervention (not executed):** (1) separate the materiality gate from the tie-break on the P0 six-cell set (two arms, about an hour) so each can be judged for default on its own; (2) understand cell 90 under the stratified representation - why the tail world raises inventory without service on that truth path - before proposing it as default; (3) decide, as a benchmark-design question, whether end-of-window stock should be valued at continuation value rather than salvage, which is what keeps C at +2.3%.

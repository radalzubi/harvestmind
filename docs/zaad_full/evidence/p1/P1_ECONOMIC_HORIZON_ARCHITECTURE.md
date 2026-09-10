# P1 final closure: purchasing economics beyond the detailed horizon (design record and pre-registration)

Written at `c917392` before the development comparison and the authoritative runs. Sections 1-4 are the
audit and the design comparison; section 5 is the pre-registration of the selected architecture and is
not edited after the runs (corrections are appended, dated).

## 1. Root cause of B (phase A audit; `P1_CLOSEOUT.md` L1-L5 for the confirmation-floor half)

B's declared economics at the review: fixed order cost 250 per order, holding .00288 of value per period
(.0144 per unit-week at the $5 price), no cost of capital, fitted demand 98.9 per period (sd 6.1), lead
one period, no MOQ / MOV / pack / pallet / freight. Economic lot reference (`lotsizing.reference_lots`)
1,854 units = the EOQ, cycle 18.7 periods, against a twelve-period detailed horizon. Realised path
(`horizon52_tAonly`, +2.66%): first material lots 1,093 / 1,053 / 1,071, material lots 800-1,240 (average
991 / 1,132 / 1,048), 6-9 orders per seed against the EOQ buyer's 3, seven ~100-unit incumbent top-ups
retained by the confirmation floor, ordering 1,500-2,250 against 750, carrying 432-454 against 699-726,
purchases 28,200-30,700 against 27,700-28,300, average inventory ~600 against ~950, service 1.000.

Why the twelve-period solve prefers the smaller lot (marginal analysis at review 0, 150 on hand, mean
world): with the pass-J terminal term (one slab of 1,854 units at margin 1.0 above salvage, i.e. a credit
of exactly the $5 purchase price per residual unit) the optimum is 1,058 units, the window's demand to
the unit, and the envelope is flat from a cap of 1,100 to 2,200: every extra unit costs its purchase plus
eleven weeks of in-window carrying (.158) and is credited exactly its purchase. The long-run value the
horizon cannot see is c*/mu - price = .27 per unit at the margin: the unit's share of the avoided future
order cost (250 / 1,854 = .135) plus the average holding the displaced future unit would have incurred in
a steady-state lot (h * Q / 2mu = .135). The pass-J slab subtracted the second term as "carrying until
consumption at half a lot" for every residual unit, which is right for the last unit of a full lot and
wrong for the first: it overcharged small residuals by up to .135 per unit and left the credit at the
price. The seven top-ups are the same mechanism one step later: with lots that only cover the window,
stock runs down within 6-9 weeks, the deferral candidate's fitted-world service dips below the weekly
buyer's 1.000, and the confirmation floor retains the incumbent's 100 units (L1); with a lot that covers
a cycle the deferral candidate serves 1.000 too.

## 2. Phase B: the current terminal / lot-sizing architecture

A. Represented: end-of-plan stock and committed post-horizon arrivals credited, in the solve, at salvage
plus (landed - salvage - carrying at half a lot) up to one reference lot; in the selection rows, at
landed less each unit's own carrying until consumption (`terminal.py`). B. Omitted: the average holding
a displaced future unit would have incurred (h Q / 2mu per unit); and the slab's carrying subtraction is
the half-lot value for every unit rather than the k-th unit's own. C. Overvalued: nowhere (solve credit
<= price; rows <= landed). D. Undervalued: every residual unit by up to .27 on B, systematically on
every fixture with order-level economics. E. The planner cannot compare "one large order now" with
"several later orders" beyond the horizon except through this credit. F. Yes: avoided future order and
holding events are undercounted. G. Candidate generation is complete for this purpose: the lot-size
envelope shows the MILP finds any lot the objective prefers (section 3 experiment). H. Reference lots
are computed ex ante (`reference_lots`) but were used only for the premium.

## 3. Phase C: three architectures

| | 1. Steady-state relative-value continuation (selected) | 2. Analytic economic-lot candidate | 3. Aggregated economic tail periods |
|---|---|---|---|
| Definition | Credit residual unit k (consumed k/mu after the plan) at c*/mu - rate * price * k/mu, floored at salvage, capped at c*/mu, up to one economic cycle; c*/mu = landed + rate * price * Q_ref / 2mu. In the solve: one slab per post-window period (mu units at margin c*/mu - salvage - rate * price * (j + 1/2)); in the selection rows: the same per-unit formula through `continuation_value(landed=c*/mu, cap=one cycle)`. | Add a candidate whose period-0 order is the reference lot (or the EOQ rule's projection) and let the selector compare it on the twelve-period rows. | Append 1-2 coarse periods (e.g. 8 weeks each) after the detailed horizon with aggregate demand, holding on average inventory and one order opportunity, and value stock at the end of the tail. |
| Information | Declared economics at the review (K, tariff, rate, price, MOQ / MOV / pack / load through Q_ref), fitted mean demand. | Same. | Same plus tail calendars, capacities, payment timing across the tail. |
| Leakage | None: no future truth, same forecast origin. | None. | None, but the tail must repeat declared data (as the rolling replay does). |
| Service | Unchanged: service targets, stress confirmation and the incumbent floor untouched; only the objective's terminal term changes. | Unchanged. | Service in the tail is aggregate and approximate. |
| Accounting | Planner-internal; selection rows reconcile through the same ledger key; the benchmark's terminal rule unchanged. | Unchanged. | Tail costs must be kept out of the realised ledger and reconciled separately. |
| Solver | +J continuous variables per SKU / location / world (J = cycle periods, 19 on B, 5 on I, 1 elsewhere), one row. | +1 candidate solve per review. | Larger MILP (tail periods with integer order variables), calendar semantics for coarse periods. |
| Runtime | Negligible. | +1 solve per P1-owned review (~+15%). | 1.5-3x per solve. |
| MOQ / MOV / freight / load | Through Q_ref and the tariff at Q_ref in c*; the in-window lot rules unchanged. | Through the candidate's own rounding. | Through the tail's order variables. |
| No-order decisions | Preserved: the credit is concave and never exceeds c*/mu; with ample stock the marginal unit is worth less than its price, so nothing is bought. | The candidate can be rejected by the selector. | Preserved. |
| Long cycles | Exact in the average-cost sense for any cycle length; no horizon growth. | Only if the candidate is right. | Needs enough tail to cover the cycle (grows with the cycle). |
| Incumbent already optimal | Materiality and incumbent-first unchanged; the credit raises no candidate above an efficient incumbent. | Same. | Same. |
| Disruption | P0-owned reviews receive no continuation term (unchanged). | Same. | Same. |
| Terminal interaction | Replaces the pass-J term; benchmark rule untouched. | Depends on 1 (a candidate with a large residual is undervalued without it). | Replaces the terminal by a tail plus a smaller terminal. |
| P0 | Untouched (P0 passes no continuation). | Untouched. | Model change touches shared code paths. |
| Complexity | Small (one function family, one loop generalisation in the model). | Small, but insufficient alone. | Large. |
| Failure modes | Concave credit above price could invite a late in-window purchase; ruled out analytically (a late lot pays K and its carrying and its marginal credit at a full residual equals the price) and checked adversarially (section 4). Non-stationary demand: c* uses the fitted level at the review. | Selector still faces the horizon-edge bias. | Coarse-period approximation error; runtime. |

Rejected: 2 alone (it does not fix the objective the selector uses), 3 (the relative-value continuation is
its analytic limit at a fraction of the cost), and the longer detailed horizon (the brief's evidence:
non-monotone, quadratic runtime).

## 4. Adversarial review of architecture 1 (before pre-registration)

* Very high K: c*/mu rises with K / Q_ref, the credit rises toward the larger economic lot; capped at
  one cycle of units and at c*/mu per unit. Near-zero K: Q_ref = max(MOQ, MOV units, one period), the
  credit reduces to price plus half a period of holding: ordinary detailed-horizon behaviour.
* Very high carrying: Q_ref shrinks (EOQ), slabs shrink (margin falls to zero within a few periods),
  credit reduces to price. Long lead: c* unchanged (lead affects protection, not the cycle); short lead:
  same.
* MOQ above the economic lot: Q_ref = MOQ (a legal lot), credit up to one MOQ of units. Freight
  threshold just above the economic lot: the tariff at Q_ref enters c* only; the in-window solve decides
  whether to fill the truck on the actual freight tiers (unchanged), so the truck is not filled blindly.
* Intermittent / declining / rising demand: c* uses the fitted mean at the review, the same information
  the rest of the plan uses; a confirmed decline is P0-owned (RECOVER) and gets no credit.
* Volatile high-service SKU (Q): no order-level economics, credit within a cent of the price; the
  confirmation floor untouched. Incumbent with excellent cadence: the candidate that mirrors it wins no
  material improvement; abstention unchanged.
* Cycle far beyond the horizon: the credit is a closed form, no horizon needed. Cycle inside the horizon:
  the residual at the edge is small and the credit is near the price.
* Horizon-edge gaming: a purchase at the last in-window period pays its order cost and receives a credit
  whose marginal value at a full residual equals the price; buying beyond one cycle earns salvage. No
  terminal arbitrage; no double counting (the solve credits the same post-horizon supply set as before;
  the realised ledger is untouched).

## 5. Pre-registration of the selected architecture (before the authoritative runs)

Rule: `terminal_economic_basis = "cycle"` (default) on P1-owned reviews with the lot terminal valuation:
solve terms `cycle_continuation_terms`, selection rows `continuation_value(landed=c*/mu, cap=one cycle)`.
Files: `zaad/full/lotsizing.py` (steady_state_unit_costs, economic_cycle, cycle_continuation_terms,
continuation_caps), `zaad/full/model.py` (a continuation entry may be a list of slabs), `zaad/full/terminal.py`
(cap), `zaad/full/planner.py` (basis switch, caps on rows, report fields), `zaad/full/contracts.py` (field).
Parameters: none tuned; caps: one economic cycle of units, c*/mu per unit, salvage floor. Expected
behaviour: B's first lot moves from ~1,060 toward the economic lot, orders per seed toward 3-4, top-ups
retained by the floor fall as stock covers the cycle; short-cycle fixtures change by less than a point;
Q unchanged; A's abstention unchanged; P0 cells identical. Runtime: within a few per cent of p50 1.0 s /
p95 6.3 s. Pass criteria: the freeze gate of the brief (B <= 2%, every valid fixture, Q service, A
abstention, T closed, P0 120 / 120 apart from recorded variability, legacy screen acceptable, horizon
diagnostic materially more stable than the pass-K sweep on the first lot, tests, invariants, reconciliation).
No tuning after this section is written.

### 5a. Addendum before the development comparison (2026-09-09): the received-unit basis

The first implementation valued residual stock against the price of an ORDERED unit and moved B's
review-0 lot only from 1,058 to 1,159. The pinned-objective audit isolated why: the ledger (and the
model) charge a purchase on the ordered quantity while stock receives the filled part (declared fill
.98 on every P1 source), so one more received unit costs price / fill = 5.102, not 5.000, and the credit
sat at exact break-even with the extra unit's in-window carrying. The steady-state unit cost is therefore
defined per RECEIVED unit: (price + per-unit freight + handling + order-and-tariff share of one lot) /
fill + rate * price * (lot * fill) / (2 mu). With it the review-0 optimum is 1,866 units (economic lot
1,854), the envelope rises monotonically to it and is flat beyond; a plan capped below the lot reorders a
full lot at its reorder point instead of topping up. The recorded pass-J landed basis is left as recorded
(per ordered unit). This is part of the architecture, fixed here before the development comparison and
before the authoritative runs; no parameter is tuned.

## 6. Pre-registration of the horizon-robustness diagnostic (written before it is run)

Purpose (brief section 17): show that the economic decision no longer depends on the arbitrary detailed
horizon. Runs: fixture B, ZAAD gated only, planning horizon 12 (the development record
`horizon52_cycle_dev`), 16, 20, 24 via `scripts/p1_horizon_benchmark.py --horizon` (tags
`horizon52_cycle_h16/h20/h24`), the benchmark's own stitched truth, comparators from `horizon52_tAonly`.
No 32-period arm. Diagnostic only: the declared benchmark stays the constant twelve-period horizon, and
no horizon value is selected from the result. Prediction: the first material lot stays within 10% of the
economic lot (1,854) at every horizon and the cost delta moves by less than the pass-K sweep's range
(+0.15 to +2.21% over 12-32); solve time grows with the horizon as before. Pass reading: "materially more
stable than the pass-K sweep on the first lot" (section 5).

## 7. Adversarial sweep (brief section 24; mean-world period-0 lot without / with the continuation)

| case | economic lot | cycle (periods) | c*/mu | slabs | x0 without | x0 with | orders (with) |
|---|---|---|---|---|---|---|---|
| B's economics (K 250) | 1,854 | 18.7 | 5.372 | 19 | 1,058 | 1,866 | period 0 only |
| very high K 5,000 | 8,293 | 83.8 | 6.308 | 84 | 1,058 | 8,427 | period 0 only |
| near-zero K 1 | 117 | 1.2 | 5.119 | 2 | 49 | 49 | every period (weekly buying unchanged) |
| K 250, carrying 2.0 / year | 508 | 5.1 | 6.087 | 6 | 453 | 453 | 0, 5, 10 (a full lot at the reorder point, 505, not more) |
| K 250, lead 21 days | 1,854 | 18.7 | 5.372 | 19 | 908 | 1,918 | period 0 only |
| K 250, MOQ 3,000 above the lot | 3,000 | 30.3 | 5.401 | 31 | 3,000 | 3,000 | period 0 only |
| K 250, cost of capital 30% / year | 1,071 | 10.8 | 5.569 | 11 | 1,058 | 1,058 | period 0 only (lot inside the window: unchanged) |
| K 250, opening stock 5,000 | 1,854 | 18.7 | 5.372 | 19 | 0 | 0 | none |
| K 250, demand 10 / week | 586 | 59.3 | 5.955 | 60 | 0 | 0 | none (opening stock covers the window) |
| K 250, detailed horizon 4 | 1,854 | 18.7 | 5.372 | 19 | 251 | 1,866 | period 0 only (horizon-independent) |

Reading: the credit never buys more than one economic lot, never buys when stock covers the cycle, is
inert when the lot sits inside the window or when order-level economics are absent, and makes the lot
independent of the detailed horizon. A late in-window purchase appears only where the reorder point
falls late in the window (carrying 2.0 / year: 505 at period 10 against a 508 lot), which is the cadence
the economics call for, not horizon-edge arbitrage. Freight thresholds: tests 5-6 of
`tests/unit/test_zaad_economic_horizon.py` derive the expectation from the declared tiers (a cheaper full
load is bought; an uneconomic truck is not filled).

### 5b. Addendum before the authoritative runs (2026-09-09): shelf-life bound on the solve-side slabs

The adversarial sweep (section 7, "very high K") credits 84 post-window periods; a perishable SKU cannot
earn credit for consumption after it expires. `cycle_continuation_terms` now bounds the slab count at
shelf_life - detailed horizon (the remaining life of a unit landed in period 0; the selection rows already
apply each lot's own expiry through `continuation_value`). Every P1 fixture declares a 52-period shelf
life, so no P1 run changes (bound 40 slabs against 19 on B, 5 on I, 9 on T); test 18 covers the bound.

## 8. Phase D development comparison (`closure/horizon52_cycle_dev.jsonl.gz`, cycle basis, comparators from `horizon52_tAonly`)

| fixture | delta @52 cycle / pass-L | first lots (seeds) | orders per seed | avg inv | terminal | service |
|---|---|---|---|---|---|---|
| B | **+1.85% / +2.66%** (PASS at 52 and at every endpoint 40-52; +0.30 at 40, class E as before) | 983 / 1,645 / 1,866 (was 1,093 / 1,053 / 1,071) | 5 / 6 / 6 (was 8 / 6 / 9) | 791 (597) | 1,010 (402) | 1.000 |
| A | +0.80 / +0.81 (41 actions, unchanged) | unchanged | unchanged | 17 | 6 | .989 |
| C | +0.34 / +0.39 | 400 / 453 / 400 | 13 / 12 / 13 | 327 | 270 | 1.000 |
| G | -1.22 / -0.76 | 1,957 / 1,938 / 1,935 | 6 / 6 / 8 | 1,155 | 1,394 | 1.000 |
| I | +0.23 / +0.07 | 450 x3 | 12 / 12 / 13 | 266 | 347 | 1.000 |
| J | +0.94 / +0.34 | 983 / 950 / 871 (was ~1,070) | 6 / 6 / 8 | 574 | 262 | 1.000 |
| O | -0.01 / +0.13 | 294 x3 | 34 / 37 / 33 | 78 | 44 | .981 |
| Q | +0.19 / +0.17 (137 retained, service .991 unchanged) | 112 x3 | 48 / 44 / 46 | 73 | 58 | .991 |
| T | -0.83 / -0.28 | 1,920 x3 | 6 / 6 / 6 | 1,053 | 1,059 | 1.000 |

Floor-retained ~100-unit orders on B: 7 -> 1 (seed 41003 review 40, a PROTECT review). Runtime on B: p50
1.3 s (0.6), p95 3.8 s (1.7): the 19 slabs per world. Every control inside its tolerance; J moved from
+0.34 to +0.94 (its 10.8-period cycle sits inside the window; the concave credit values the last residual
units below the pass-J flat slab, so the plan holds less at the window end: terminal 262 against 355).

The gate traces (`closure/gate_trace_B_*_4100{1,2,3}_cycle_pre5c.json`, cycle basis before rule P1-S; the committed pass-L traces are unchanged) show where B's remaining
+1.85% comes from, and it is not the continuation. Two mechanisms:

1. Near-ties at low stock (reviews 0 and 24): the stochastic candidates plan a partial lot now and a
   full lot at the in-window reorder point (983 + 1,934 at period 10; 2,128; 865 + a lot at period 8) within
   0.07% of the deterministic full lot, the difference being the three sampled worlds' fill draws. The
   continuation makes a late full lot exactly break-even by construction (its credit equals its purchase
   plus the order cost), so the timing of full lots is a matter of indifference resolved by noise. This
   costs one partial lot per seed and is accepted.
2. The selector's leanness band on purchasing-economics reviews (CAPITAL_OPTIMIZATION reviews 13, 16,
   20, 25, 26, 31, 33 with 350-435 on hand): the cheapest well-solved candidates buy nothing now and a
   full lot at the reorder point two or three periods ahead; the cadence-4 candidate buys a partial lot
   now (504-652 units) at +0.8% to +3.4% hedged cost and wins because it is leaner (burden 3,600-3,900
   against 5,300-7,600) inside the 5% downside band (`planner.py` v7 rank: `band` then `min(burden,
   earliness, cost)`). That rule exists so that protection has to beat the lean plan by more than
   estimate noise; on a purchasing-economics review carried capital is already priced by the objective
   (holding, cost of capital, and now the cycle continuation), so the band charges cycle stock a second
   time, up to the tolerance, and converts the continuation's indifference into partial lots: 5-6 orders
   a seed against the EOQ buyer's 3 (ordering 1,417 against 750 at 52).

### 5c. Pre-registered amendment before the second development run and the authoritative runs (2026-09-09): rule P1-S

Rule: on a review the router assigns to PURCHASING_ECONOMICS, the v7 selection ranks well-solved feasible
candidates on hedged cost; burden and earliness break numerical ties only (relative 1e-6). On a
PROTECTION_RECOVERY review the band, its shortage-exposure guard and the leanness preference are
unchanged. No threshold is introduced (the tie tolerance is numerical equality). Everything after
selection - materiality, incumbent-first acceptance, stress confirmation with the incumbent floor,
capital tie-break, alternatives loop - is unchanged, so a leaner-but-costlier plan is no longer chosen
over a cheaper one, and a cheaper plan still has to beat the incumbent materially and pass the floor.
Predictions: B's cadence partial lots at CAPITAL_OPTIMIZATION reviews disappear, orders per seed 3-5,
B at or below +1.0% (gate <= +2.00% at 52 and at every endpoint 40-52); A's declared actions stay at or
below 46 / 156 (43 recorded) with the legacy `action` check passing; Q's declared service stays >= .99
and the legacy service >= .98 (the floor is untouched); C, G, I, J, O, T inside tolerance, T <= 0; P0
six-cell arm identical (every P0 review is protection-owned); runtime unchanged. Failure of any control
reverts the rule and the verdict is written on the continuation alone.

## 9. Second development comparison under rule P1-S (`closure/horizon52_cycle_dev2.jsonl.gz`) and the residual

| fixture | delta @52 P1-S / cycle only / pass-L | first lots | orders per seed | avg inv | terminal | service | notes |
|---|---|---|---|---|---|---|---|
| B | **+1.30% / +1.85% / +2.66%** (PASS at 52 and at every endpoint 40-52: -0.41 .. +1.34; seeds +2.46 / -0.24 / +1.69) | 983 / 1,645 / 2,128 | 4 / 3 / 4 (cadence 15.7 / 17.5 / 16.3 weeks against the 18.7-week cycle) | 985 | 1,207 | 1.000 | retained top-ups 0; ordering 917 against the EOQ buyer's 750 |
| A | +0.80 / +0.80 / +0.81 | unchanged | unchanged | 17 | 6 | .989 | 41 pending (43), 17 abstentions (21): no rise in interventions |
| C | +0.45 / +0.34 / +0.39 | 400 / 450 / 400 | 13 / 12 / 13 | 340 | 170 | 1.000 | |
| G | -1.77 / -1.22 / -0.76 | 1,883 / 1,914 / 1,935 | 6 / 6 / 8 | 1,166 | 1,574 | .999 | |
| I | +0.11 / +0.23 / +0.07 | 450 x3 | 12 x3 | 334 | 306 | .999 | |
| J | +1.35 / +0.94 / +0.34 | 983 / 1,340 / 871 | 8 / 6 / 6 (cadence 7.3 / 7.2 / 9.8 against a 10.8-period cycle) | 557 | 539 | 1.000 | inside tolerance; see below |
| O | +0.30 / -0.01 / +0.13 | 294 x3 | 34 / 35 / 32 | 79 | 44 | .979 | |
| Q | +0.19 / +0.19 / +0.17 | 112 x3 | 48 / 44 / 46 | 73 | 58 | .991 | 137 retained, service unchanged |
| T | -0.13 / -0.83 / -0.28 | 1,920 x3 | 8 / 6 / 6 | 1,132 | 1,327 | 1.000 | closed |

Every pre-registered prediction of 5c holds: B's cadence partial lots are gone (orders 3-4 a seed), B at
+1.30%, A's actions did not rise, Q unchanged, T closed, every control inside tolerance.

The residual on B (+1.30%) and the movement on J (+0.34 -> +1.35) share one mechanism, mechanism 1 of
section 8: at a review with low stock the stochastic candidates plan a partial lot now and a full lot at
the in-window reorder point, within 0.6% of the deterministic full lot, and rule P1-S rightly takes the
cheapest. The continuation makes the timing of full lots a matter of exact indifference (a late full lot's
credit equals its purchase plus the order cost, the relative value function of the EOQ cycle), so the
choice between the two plans is decided by what the three sampled selection worlds happen to contain.
Scenario-count diagnostic (review 0, product configuration is three worlds; 12 and 30 are diagnostic only):

| review | worlds | deterministic lot (hedged) | stochastic / cadence lot (hedged) | chosen |
|---|---|---|---|---|
| B 41001 | 3 | 1,866 (6,363.8) | 983 (6,320.3) | 983 |
| B 41001 | 12 | 1,866 (6,348.4) | 1,694 (6,346.8) | 1,694 |
| B 41001 | 30 | 1,866 (6,338.3) | 1,698 (6,336.9) | 1,698 |
| B 41003 | 3 | 1,866 (6,225.7) | 2,128 (6,221.2) | 2,128 |
| B 41003 | 12 | 1,866 (6,275.1) | 2,042 (6,272.9) | 2,042 |
| B 41003 | 30 | 1,866 (6,294.2) | 1,912 (6,294.0) | 1,912 |
| J 41001 | 3 | 1,462 (6,318.1) | 983 (6,280.0) | 983 |
| J 41001 | 12 | 1,462 (6,293.7) | 788 (6,292.4) | 788 |
| J 41001 | 30 | 1,462 (6,284.2) | 1,369 (6,283.3) | 1,369 |

With more worlds the candidates converge on the full lot and the hedged costs become indistinguishable
(1-2 on 6,300); with three worlds the fill draws (sd 1% on 1,000-unit orders, 50-100 per world) are the
same size as the 58 the mean world puts between the split and the full lot. The scenario count is a P0
setting and the brief forbids compute as a substitute for architecture, so this is recorded as the
residual, not tuned. On J a second, smaller simplification is noted: the steady-state unit cost charges
the cost of capital on inventory value from receipt, while the model charges it on the cash cycle (net
60 days: the deterministic candidate buys 1,462 against the 1,071 reference lot). Both fixtures pass.

## 10. Horizon-robustness diagnostic outcome (section 6; `closure/horizon52_cycle.jsonl.gz` at 12, `horizon52_cycle_h16/h20/h24.jsonl`)

| detailed horizon | delta @52 (landed continuation) vs the EOQ buyer | seeds | first lots | orders per seed | lots >= 1,500 | solve p50 / p95 / max (s) |
|---|---|---|---|---|---|---|
| 12 (declared) | **+1.30%** | +2.46 / -0.24 / +1.69 | 983 / 1,645 / 2,128 | 4 / 3 / 4 | 9 of 11 | 0.7 / 3.4 / 6.1 |
| 16 | +1.35% | +0.75 / +1.71 / +1.59 | 1,386 / 1,385 / 1,081 | 3 / 4 / 4 | 4 of 11 | 4.3 / 14.0 / 19.9 |
| 20 | +1.58% | +1.27 / +0.10 / +3.38 | 1,082 / 2,054 / 468 | 4 / 3 / 6 | 7 of 13 | 11.6 / 35.6 / 56.9 |
| 24 | +1.25% | +2.03 / +1.29 / +0.44 | 1,574 / 2,070 / 2,058 | 4 / 4 / 3 | 10 of 11 | 34.0 / 108.1 / 177.7 |

Reading against the pre-registration of section 6: the cost delta moves by 0.33 pp over 12-24 against
the pass-K sweep's 2.06 pp (+0.15 to +2.21 over 12-32), orders per seed stay at 3-4 at every horizon
(pass K's lots overshot the cycle at 24 and 32), and the verdict is PASS at every horizon: the economic
decision no longer depends on the detailed horizon in the way the pass-K sweep showed. The first lot is
not within 10% of the economic lot at every horizon in the rolling replay: the review-0 choice is the
near-tie of section 9 (in the mean world, test 17, it is), and a longer window gives the split plans more
placements. Solve time grows steeply with the horizon, as in pass K; the declared benchmark stays at 12.
No horizon value is selected from this table.

## 11. Authoritative outcome

`P1_CLOSEOUT.md` sections M9-M12: declared benchmark A-T at the final code (`closure/horizon52_cycle.jsonl.gz`),
B +1.30% PASS at 52 and at every endpoint 40-52, 17 / 17 valid fixtures PASS, T -0.13%, legacy screen
items unchanged, P0 six-cell arm, runtime, freeze gate and verdict.

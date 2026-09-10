# P2 authoritative results

Records: `p2_authoritative.jsonl` (the pre-registered run, 200 cells: 20 fixtures x 5 policies x 2
seeds, eight rolling reviews, R twenty), `p2_authoritative_c1.jsonl` and `p2_authoritative_c2.jsonl`
(the fixtures Correction 1 invalidated - D, M, O, Q - re-run under the corrected code, first under
concurrent load and then with the machine otherwise quiet), `p2_final.jsonl` / `.summary.json` /
`.tables.md` (the sixteen untouched fixtures from the pre-registered run plus D, M, O, Q from the
quiet re-run; the same rules, `scripts/p2_final_table.py`). Costs are the P2 continuation basis;
the asset-basis gaps are reported in the summaries.

## 1. Fixture table (final set)

| fixture | class | best baseline | ZAAD gap | tol | ZAAD min branch service | incumbent min service | ZAAD transfers | ZAAD abstained | wall p50 / p95 / max s | pass |
|---|---|---|---|---|---|---|---|---|---|---|
| A independent demand | VALID | independent | +0.12% | 2% | .978 | .978 | 1541 | 6.5 / 8 | 7 / 14 / 18 | PASS |
| B correlated demand | VALID | network_rop | -0.06% | 2% | .984 | .984 | 1531 | 6.0 / 8 | 12 / 16 / 21 | PASS |
| C short lane | VALID | independent | +0.12% | 2% | .978 | .978 | 1541 | 6.5 / 8 | 7 / 14 / 18 | PASS |
| D long lane (6 worlds) | VALID | independent | -0.07% | 2% | .979 | .978 | 1618 | 0.0 / 8 | 58 / 87 / 88 | PASS |
| E high transfer cost | VALID | independent | +0.34% | 2% | .977 | .978 | 1525 | 7.5 / 8 | 6 / 11 / 15 | PASS |
| F low transfer cost | VALID | echelon_base_stock | +0.40% | 2% | .983 | .977 | 1605 | 6.5 / 8 | 7 / 11 / 16 | PASS |
| G central supply shortage | VALID | independent | +0.00% | 3% | .565 | .565 | 922 | 8.0 / 8 | 4 / 9 / 12 | PASS |
| H one-branch shock | VALID | independent | +2.06% | 3% | .963 | .770 | 2180 | 2.5 / 8 | 30 / 64 / 112 | PASS |
| I shared supplier disruption | VALID | independent | +0.44% | 5% | .977 | .978 | 1522 | 0.5 / 8 | 1 / 1 / 1 | PASS |
| J asymmetric targets | VALID | echelon_base_stock | +1.35% | 2% | .968 | .972 | 1541 | 4.5 / 8 | 18 / 29 / 31 | PASS |
| K unequal scale | VALID | network_rop | +0.63% | 2% | .980 | .985 | 2712 | 4.0 / 8 | 9 / 15 / 29 | PASS |
| L already efficient | VALID | echelon_base_stock | +0.46% | 2% | .977 | .977 | 1340 | 7.5 / 8 | 6 / 11 / 14 | PASS |
| M unreachable stock (8 worlds) | VALID | central_pool | +0.02% | 2% | .545 | .545 | 1637 | 4.0 / 8 | 91 / 118 / 257 | PASS |
| N pipeline covers | VALID | echelon_base_stock | +0.40% | 2% | .920 | .919 | 1135 | 7.5 / 8 | 6 / 13 / 21 | PASS |
| O two lane options (6 worlds) | VALID | independent | -0.69% | 2% | .990 | .978 | 1635 | 0.0 / 8 | 76 / 87 / 315 | PASS |
| P lane capacity | VALID | network_rop | +0.00% | 3% | .740 | .740 | 1120 | 8.0 / 8 | 7 / 9 / 11 | PASS |
| Q packs and dispatch fee | VALID | independent | -0.69% | 2% | 1.000 | .965 | 1812 | 0.0 / 8 | 26 / 59 / 89 | PASS |
| R order / transfer interaction (20 reviews) | VALID | independent | -2.19% | 2% | .992 | .989 | 3935 | 0.0 / 8 | 12 / 60 / 96 | PASS |
| S recovery after imbalance | VALID | independent | +0.71% | 3% | .872 | .872 | 1350 | 7.0 / 8 | 6 / 12 / 14 | PASS |
| T single node, network off | VALID | echelon_base_stock | +0.86% | 2% | .986 | .990 | 0 | 2.0 / 8 | 0 / 1 / 1 | PASS |

**20 / 20 valid fixtures pass every economic, service, action, reverse-movement, conservation and
starvation gate. 18 / 18 network principles pass.** Asset-basis gaps (not a gate) are within 2.6% on
every fixture (largest H +2.6%, R -3.8% in ZAAD's favour). The corrected fixtures pass in both re-runs
(c1: D -0.16%, M +0.01%, O -0.55%, Q -0.69%; c2: D -0.07%, M +0.02%, O -0.69%, Q -0.69%).

## 2. Network principles (final set)

pooling_has_value (A: ZAAD within 0.12% of isolated chains), pooling_benefit_shrinks (B's benefit no
larger than A's within the tolerance), correlated_demand_no_fabricated_diversification,
long_lead_positions_more_locally (branch cover D .84 periods against C .22),
no_churn_at_high_transfer_cost (E moves exactly what the incumbent moves), rebalance_before_purchase
(F buys nothing in its first two reviews and moves 391), principled_allocation_under_shortage (G: no
severe starvation beyond the incumbent's), healthy_branch_not_starved (H north .963 against the
incumbent's .919), priority_branch_protected (J north 1.000), small_branch_not_starved (K south .968),
already_efficient_abstains (L abstains on 7.5 of 8 reviews, cost within 0.5%),
remote_stock_not_credited (M serves exactly what the incumbent serves; invariant 03 proves nothing
unreachable is credited), no_over_transfer_when_pipeline_covers (N), cheap_lane_when_time_allows (O
passes), capacity_respected (P), legal_packs (Q), recovery_without_ping_pong (S), single_node_identity
(T; canonical regression). All PASS.

## 3. Runtime gate (pre-registered: p50 <= 60 s, p95 <= 120 s, max <= 180 s, no required-candidate starvation)

| set | ZAAD reviews | p50 s | p95 s | max s | required-candidate starvation | verdict |
|---|---|---|---|---|---|---|
| pre-registered run (`p2_authoritative`) | 344 | 9.7 | 60.7 | 281.9 (Q) | 15 (D, M, O: the stochastic class at a 15 s budget with 6-8 worlds) | FAIL |
| corrected, under load (`p2_authoritative_c1` for D, M, O, Q) | 344 | 9.6 | 86.8 | 120.8 | 1 (O 41002 r6, stochastic class) | FAIL |
| corrected, quiet machine (`p2_authoritative_c2` for D, M, O, Q) - the final set | 344 | 9.7 | 86.9 | 314.6 | 0 | FAIL |

Solve statuses over every ZAAD candidate of the final set: 1,476 OPTIMAL, 143 INFEASIBLE (service
floors provably unattainable on a candidate class, recorded), 19 FEASIBLE_TIME_LIMIT (usable plans
without a proof, admitted by the solve-quality gate), 0 NO_FEASIBLE_SOLUTION. The two reviews above
the gate: M seed 41002 review 7 (257 s, NETWORK_ALLOCATION, eight worlds, budget 40 s x 2.2 x 1.3 =
114 s per solve, three candidates at the cap) and O seed 41001 review 6 (315 s, CAPITAL_OPTIMIZATION,
six worlds, 86 s per solve, three candidates at the cap plus completions). The mechanism is structural:
review wall time is the number of candidate classes the frozen screen requests times the declared
per-solve budget, and the pre-registered world rule raises that budget on long lanes. It does not
depend on machine load (the loaded run was faster on these reviews because its solves stopped
earlier, once with no feasible solution).

p50 and p95 pass on every set. The max does not. The gate is not relaxed after the fact.

## 4. Behaviour summary (final set, ZAAD)

Owners over 344 reviews: 251 PURCHASING_ECONOMICS, 93 PROTECTION_RECOVERY. No-action / abstention:
L 7.5 / 8, G and P 8 / 8 (nothing can be done about a supplier or a lane that cannot carry demand),
E 7.5 / 8, A / C 6.5 / 8, N 7.5 / 8. Transfers never reverse (reverse-pair units 0 on every cell);
conservation residual <= 1e-12 on every review; capacity and packs respected (P and Q complete; the
settlement would have refused otherwise).

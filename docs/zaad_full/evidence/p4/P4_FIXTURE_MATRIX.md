# P4 fixture matrix (pre-registered)

Written before the authoritative run (`scripts/p4_benchmark.py`). Every fixture: a frozen request builder, the recourse declaration, a world builder (a scenario tree on the fitted sampler, or handcrafted branches from the mean world with shared histories and two continuations each), and the pre-registered principle. Gate per fixture: every solve usable, PI <= adaptive <= static within the solver tolerance wherever a static plan exists, non-anticipativity on the solved values, every represented world settles under its own policy plan, and the principle. Time-limited solves are recorded as performance observations.

| fixture | family | request | review periods | observables | actions | worlds | principle |
|---|---|---|---|---|---|---|---|
| N1_disabled_is_frozen | neutrality | `p2_base` | [3] | ['demand', 'receipts'] | ['purchase', 'transfer'] | tree (3 histories x continuations^epochs) | frozen_identity |
| N2_no_epochs_is_static | neutrality | `p2_base` | [] | ['demand', 'receipts'] | ['purchase', 'transfer'] | tree (3 histories x continuations^epochs) | equals_static |
| N3_zero_information | neutrality | `p2_base` | [3] | ['demand'] | ['purchase', 'transfer'] | normal (50%) / high_later (50%) x 2 continuations | one_set_equals_static |
| A1_demand_visible_at_epoch | non_anticipativity | `p2_base` | [3] | ['demand'] | ['purchase', 'transfer'] | normal (50%) / high (50%) x 2 continuations | same_before_diverge_after |
| A2_delayed_information | non_anticipativity | `p2_base` | [2, 4] | ['receipts'] | ['purchase', 'transfer'] | on_time (50%) / late (50%) x 2 continuations | no_branch_until_observed |
| D1_demand_recourse | demand | `p2_base` | [3] | ['demand'] | ['purchase', 'transfer'] | normal (50%) / high (50%) x 2 continuations | high_branch_buys_more |
| D2_two_epochs | demand | `p2_base` | [3, 6] | ['demand'] | ['purchase', 'transfer'] | normal (50%) / high (50%) x 2 continuations | high_branch_buys_more |
| R1_supplier_short_fill | receipts | `p2_base` | [3] | ['receipts'] | ['purchase', 'transfer'] | full (50%) / short (50%) x 2 continuations | short_branch_replaces_supply |
| R2_shipment_delay | receipts | `p2_base` | [3] | ['receipts'] | ['purchase', 'transfer'] | on_time (50%) / late (50%) x 2 continuations | late_branch_covers_gap |
| V1_recovery | recovery | `p2_base` | [4] | ['receipts'] | ['purchase', 'transfer'] | recovered (50%) / persistent (50%) x 2 continuations | recovered_branch_buys_less |
| W1_waiting_has_value | waiting | `p2_base` | [2] | ['demand'] | ['purchase', 'transfer'] | low (50%) / high (50%) x 2 continuations | waiting_value |
| W2_no_benefit | waiting | `p2_base` | [3] | ['demand'] | ['purchase', 'transfer'] | a (50%) / b (50%) x 2 continuations | no_benefit |
| W3_flexibility_costs_mov | waiting | `p2_base` | [3] | ['demand'] | ['purchase', 'transfer'] | normal (50%) / high (50%) x 2 continuations | ordering_only |
| I1_p1_fixed_cost_lots | p1 | `p2_base` | [3] | ['demand'] | ['purchase', 'transfer'] | normal (50%) / high (50%) x 2 continuations | moq_in_every_branch |
| I2_p2_transfer_recourse | p2 | `p2_base` | [3] | ['demand'] | ['transfer'] | normal (50%) / north_surge (50%) x 2 continuations | transfers_adapt_conserved |
| I3_p3_source_mix | p3 | `p2_base` | [3] | ['demand', 'receipts'] | ['purchase', 'transfer'] | normal (50%) / high (50%) x 2 continuations | capacity_in_every_branch |
| I4_p3_shares_hold | p3 | `p2_base` | [3] | ['demand'] | ['purchase', 'transfer'] | normal (50%) / high (50%) x 2 continuations | shares_in_every_branch |
| I5_p3_switching_cost | p3 | `p2_base` | [3] | ['receipts'] | ['purchase', 'transfer'] | full (50%) / short (50%) x 2 continuations | ordering_only |
| I6_multi_sku_shared_capacity | p3 | `p2_base` | [3] | ['demand'] | ['purchase', 'transfer'] | normal (50%) / high (50%) x 2 continuations | capacity_in_every_branch |
| I7_correlated_plant | correlated | `p2_base` | [3] | ['receipts'] | ['purchase', 'transfer'] | plant_up (50%) / plant_down (50%) x 2 continuations | plant_observed_once |
| S1_commercial_packs | sector | `p2_base` | [3] | ['demand'] | ['purchase', 'transfer'] | normal (50%) / high (50%) x 2 continuations | packs_in_every_branch |
| S2_produce_sell_through | sector | `p2_base` | [2] | ['demand'] | ['purchase', 'transfer'] | slow (50%) / fast (50%) x 2 continuations | feasible_every_world |
| S3_meat_cold_chain | sector | `p2_base` | [3] | ['demand', 'receipts'] | ['purchase', 'transfer'] | normal (50%) / high (50%) x 2 continuations | feasible_every_world |
| S4_mixed_sectors_static_infeasible | sector | `p2_base` | [3] | ['demand'] | ['purchase', 'transfer'] | normal (50%) / high (50%) x 2 continuations | feasible_every_world |
| S5_mixed_sectors | sector | `p2_base` | [3] | ['demand'] | ['purchase', 'transfer'] | normal (50%) / high (50%) x 2 continuations | feasible_every_world |
| T1_tree_three_histories | tree | `p2_base` | [3] | ['demand', 'receipts'] | ['purchase', 'transfer'] | tree (3 histories x continuations^epochs) | ordering_only |
| T2_tree_two_epochs | tree | `p2_base` | [3, 6] | ['demand', 'receipts'] | ['purchase', 'transfer'] | tree (3 histories x continuations^epochs) | ordering_only |
| T3_perfect_information_bound | tree | `p2_base` | [2, 5] | ['demand'] | ['purchase', 'transfer'] | tree (3 histories x continuations^epochs) | pi_ordering |

Principles: `frozen_identity` (disabled block: report identical up to timings and the request hash); `equals_static` (no epochs: adaptive == static); `one_set_equals_static` (identical observable histories -> one set, value 0); `same_before_diverge_after`; `no_branch_until_observed` (late confirmation: one set at the first epoch, two at the second, plans identical until then); `high_branch_buys_more`; `short_branch_replaces_supply` / `late_branch_covers_gap` (the disrupted branch buys or moves more after the observation); `recovered_branch_buys_less`; `waiting_value` (value > 0 and the adaptive plan commits no more than the static plan before the epoch); `no_benefit`; `moq_in_every_branch` / `capacity_in_every_branch` / `shares_in_every_branch` / `packs_in_every_branch` (P1 / P3 / sector rows hold in every branch plan); `transfers_adapt_conserved`; `plant_observed_once` (both plant members short-fill together: one set per plant state, never a split by source label); `feasible_every_world`; `ordering_only`; `pi_ordering`.

# P3 sourcing portfolio: authoritative results

Run `p3_authoritative` (`p3_authoritative.jsonl` / `.summary.json` / `.tables.md`) on the final P3 code: the
pre-registered fixture matrix as run (`P3_FIXTURE_SPEC.md`, changes recorded), seeds 41001 / 41002, eight
rolling reviews, policies incumbent mix / cheapest landed single source / ZAAD restricted to each competing
supplier / ZAAD P3, six workers, wall 552 s. Synthetic throughout: **ENGINEERING VALIDATED, not real-data
validated.** No savings are claimed.

## Gates

**30 / 30 fixtures PASS** the economic gate (ZAAD's `cost_p3` within the pre-registered tolerance of the
best valid baseline: residual stock valued at the cheapest usable source's landed cost per received unit, no
policy premium; a baseline is valid when no branch serves more than .05 below ZAAD's), the service gate (every
branch at or above min(target, incumbent mix) - .01), the structural gates (conservation residual <= 1e-9, no
physical failure, no reverse lane pair) and the fixture's own principle. Solve statuses over every ZAAD
candidate: {'OPTIMAL': 2266, 'INFEASIBLE': 6}; 0 time-limited.

| fixture | family | best baseline | ZAAD gap (cost_p3) | gap on cost_p2 | tol | ZAAD min branch service | incumbent mix | abstained / 8 | wall p50 / max s | principle |
|---|---|---|---|---|---|---|---|---|---|---|
| E1_dominant_source | economics | cheapest_landed | +0.00% | +0.00% | 2% | 0.978 | 0.978 | 7.5 | 0.4 / 0.8 | b_unused |
| E2_landed_beats_unit_price | economics | cheapest_landed | +0.00% | +0.00% | 2% | 0.978 | 0.978 | 7.5 | 0.4 / 1.0 | a_dominant_share |
| E3_price_break_scale | economics | cheapest_landed | +0.28% | +0.28% | 2% | 0.980 | 0.977 | 7.0 | 1.5 / 2.2 | tier2_when_large |
| E4_moq_mov_small_order | economics | cheapest_landed | -1.00% | -1.00% | 2% | 0.998 | 0.992 | 1.5 | 6.7 / 10.7 | b_orders_executable |
| E5_payment_terms_preference | economics | single:supplier_b | +0.96% | +0.96% | 2% | 0.980 | 0.980 | 5.5 | 0.4 / 0.8 | a_dominant_share |
| E6_switching_cost_retains_incumbent | economics | incumbent_mix | +0.00% | +0.37% | 2% | 0.978 | 0.978 | 7.5 | 2.2 / 2.7 | b_unused |
| R1_cheap_unreliable | reliability | incumbent_mix | -0.59% | -0.45% | 3% | 0.978 | 0.979 | 3.5 | 1.0 / 1.3 | not_worse |
| R2_capacity_forces_split | reliability | single:supplier_b | -2.59% | -1.18% | 3% | 0.978 | 0.722 | 6.0 | 0.5 / 0.9 | a_at_capacity_then_b |
| R3_independent_tail_benefit | reliability | cheapest_landed | +0.10% | +0.10% | 3% | 0.978 | 0.978 | 1.5 | 0.3 / 0.8 | not_worse |
| R4_shared_plant_no_fake_diversification | reliability | cheapest_landed | +0.43% | +0.39% | 3% | 0.987 | 0.992 | 1.5 | 5.0 / 7.5 | no_split |
| R5_shared_port_risk | reliability | single:supplier | +0.12% | +0.12% | 3% | 0.982 | 0.979 | 2.5 | 0.4 / 0.9 | group_listed |
| R6_identical_no_split | reliability | single:supplier_b | +0.27% | +0.27% | 3% | 0.987 | 0.992 | 1.5 | 4.9 / 7.2 | no_split |
| C1_supplier_max_capacity | constraints | incumbent_mix | +0.22% | +0.22% | 2% | 0.888 | 0.893 | 6.0 | 0.4 / 0.7 | both_used_within_capacity |
| C2_declared_min_max_share | constraints | cheapest_landed | +0.82% | +0.82% | 2% | 0.980 | 0.979 | 7.5 | 0.4 / 0.7 | min_share_honoured |
| C3_source_blackout | constraints | single:supplier_b | +0.00% | +0.00% | 2% | 0.989 | 0.639 | 7.0 | 0.4 / 0.8 | no_purchase_in_blackout |
| C4_unqualified_source | constraints | cheapest_landed | +0.26% | +0.26% | 2% | 0.978 | 0.978 | 6.5 | 0.4 / 0.9 | unqualified_unused |
| C5_shared_capacity_multi_sku | constraints | single:supplier_s2 | -4.27% | -2.42% | 2% | 0.966 | 0.570 | 3.0 | 1.6 / 2.6 | shared_resource_respected |
| C6_shared_mov_multi_sku | constraints | single:supplier | +0.29% | +0.20% | 2% | 0.982 | 0.992 | 1.0 | 19.6 / 24.8 | shared_mov_respected |
| S1_produce_short_life | sector | incumbent_mix | +0.01% | +0.49% | 3% | 0.978 | 0.978 | 7.0 | 1.2 / 3.8 | b_unused |
| S2_produce_yield_uncertainty | sector | incumbent_mix | +1.66% | +1.36% | 3% | 0.969 | 0.976 | 0.0 | 14.9 / 26.0 | not_worse |
| S3_frozen_invalid_route | sector | cheapest_landed | +0.00% | +0.00% | 3% | 0.978 | 0.978 | 7.5 | 0.4 / 1.0 | b_unused |
| S4_commercial_pallets | sector | single:supplier | +0.66% | +0.95% | 3% | 0.987 | 0.992 | 4.5 | 24.2 / 42.8 | whole_packs |
| N1_source_to_central_with_transfers | network | cheapest_landed | +0.23% | +0.23% | 2% | 0.929 | 0.933 | 1.5 | 0.9 / 1.3 | conservation |
| N2_local_and_central_conserved | network | cheapest_landed | -0.04% | -0.04% | 2% | 0.980 | 0.991 | 1.0 | 0.3 / 0.3 | conservation |
| N3_mixed_sector_shared_capacity | network | single:supplier_s2 | -3.97% | -2.12% | 2% | 0.972 | 0.570 | 3.5 | 6.5 / 14.6 | shared_resource_respected |
| A1_incumbent_mix_optimal | abstention | incumbent_mix | +0.00% | +0.39% | 2% | 0.979 | 0.979 | 8.0 | 0.4 / 0.7 | abstains |
| A2_weak_evidence_flagged | abstention | single:supplier_b | +1.01% | +1.01% | 3% | 0.978 | 0.978 | 8.0 | 0.5 / 0.8 | weak_evidence_flagged |
| A3_pruning_identity | abstention | incumbent_mix | -1.04% | -0.59% | 2% | 0.984 | 0.978 | 6.5 | 0.4 / 0.8 | prune_identity |
| A5_single_source_legacy_identity | abstention | cheapest_landed | +0.12% | +0.12% | 2% | 0.978 | 0.978 | 6.5 | 0.3 / 0.6 | legacy_identity |
| A6_no_order_no_allocation | abstention | single:supplier | +0.44% | +0.44% | 2% | 1.000 | 1.000 | 5.0 | 0.5 / 0.6 | no_order_no_allocation |

## What the sourcing layer did (both seeds, settled on the truth)

* **E1 / E2**: the dominated or dearer-landed source never receives quantity; the block states that supplier B's lower unit price loses after freight, handling and payment terms.
* **E3**: every purchase from supplier B above the tier threshold is on the 4.4 tier; small orders stay on the 5.0 tier or with A.
* **E4**: every B order is at least its MOQ and its supplier order value at least the MOV (the settlement re-checks both); ZAAD is 1 % cheaper than the cheapest-landed rule.
* **E5**: on the reviews where ZAAD acts it buys from the Net-60 source; the declared 50 / 50 mix is retained where the difference is not material.
* **E6**: a 1.5 % nominal saving never triggers a switch against a declared 2,000 switching cost; the incumbent mix is retained on 7.5 of 8 reviews.
* **R2**: on every review where ZAAD acts and needs more than A's capacity, A is at its capacity and B carries the remainder; the incumbent (A only) serves .72.
* **R4 / R6**: identical or plant-sharing sources are never split for diversification's sake (one source per review); the shared-plant sentence is present on R4.
* **C1 / C5 / N3**: no source above its capacity, no shared resource above its cap; S2 takes the overflow on the multi-SKU fixtures (ZAAD 4 % cheaper than the all-S2 single source, incumbent starving at .57).
* **C2**: the declared minimum share of B (30 %) holds on every review with a purchase; the maximum share of A (70 %) likewise.
* **C3 / C4**: no purchase lands in a shutdown period; unapproved and unreviewed sources never receive quantity and the block says why.
* **C6**: every supplier order combining both SKUs is at or above the shared MOV; combined orders occur.
* **S1 / S3**: the short-life produce source and the frozen source into a chilled-only destination never receive quantity; the block gives the physical reason.
* **S2**: the cheap low-yield produce source is not adopted; ZAAD is within 1.7 % of the incumbent and cheaper than the all-B policy.
* **S4**: every purchase a whole case and pallet on both suppliers.
* **N1 / N2**: conservation exact with two sources into central and with a branch-direct source.
* **A1**: the declared 60 / 40 mix that the capacities make optimal is retained on 8 of 8 reviews (NO MATERIAL IMPROVEMENT).
* **A2**: the FALLBACK-provenance group and the history-less source are flagged weak; no independence benefit is claimed.
* **A3 / A5**: pruning and the empty sourcing block change no purchase; transfer differences are proven objective ties.
* **A6**: no order, no allocation; the block reports NO_ORDER with every option at zero.

## Runtime

480 ZAAD reviews: p50 0.66 s, p95 19.2 s, max 42.8 s; over 60 s: 0; over 180 s: 0.
By family: economics p50 0.8 s / max 10.7 s; reliability p50 0.9 s / max 7.5 s; constraints p50 0.5 s / max 24.8 s; sector p50 5.1 s / max 42.8 s; network p50 0.9 s / max 14.6 s; abstention p50 0.4 s / max 0.8 s. Details: `P3_PERFORMANCE.md`.

## Not claimed

No commercial validation, no real-world savings, no calibration to operator data. The fixtures are synthetic and the tolerances are engineering gates.

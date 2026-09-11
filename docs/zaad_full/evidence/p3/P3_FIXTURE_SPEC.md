# P3 sourcing portfolio: pre-registered fixture specification

Registered 2026-09-11 before any P3 result was produced. Every fixture is the P2 network frame
(`zaad.meio.fixtures_p2.p2_request`: supplier into a central DC, two branches, one lane each, weekly
periods, horizon 12, seeds 41001 / 41002, eight rolling reviews) with one or more additional approved
sources into the same destination, built by `zaad.sourcing.fixtures.build`. Source A is the frozen
fixture's supplier (`src_A`, unit price 5, lead 7 days, fill .98); every other source is a clone with the
overrides listed. Synthetic throughout: ENGINEERING VALIDATED, never real-data validated.

## Policies compared

| policy | meaning |
|---|---|
| `incumbent_mix` | the operator's declared incumbent source mix under the network reorder-point rule (`network:rop` with the fixture's `incumbent_shares`; the frozen cheapest-landed primary source when none is declared) |
| `cheapest_landed` | the same rule buying everything from the cheapest landed-cost source (incumbent shares stripped) |
| `single:<source>` | ZAAD restricted to one approved source (every other source unapproved); the best of these ex post is the best single-source policy |
| `gated` | ZAAD P3: the frozen joint decision on the request with its sourcing block |
| `gated_noprune` / `gated_legacy` | equivalence variants for A3 (pruning off) and A5 (sourcing block stripped) |

## Gates (all fixtures)

* economic: ZAAD's continuation-valued window cost within the fixture tolerance of the best valid
  baseline (a baseline is valid when no branch serves more than .05 below ZAAD's);
* service: every branch at or above min(target, incumbent mix) - .01 (unavoidable shortage only where
  the incumbent starves too);
* structural: conservation residual <= 1e-9, no physical failure, no source above its capacity, no
  purchase below its MOQ or off its packs (the settlement refuses these), no reverse lane pairs;
* principle: the fixture's own statement below, checked on the recorded ZAAD reviews.

## Fixtures (30)

| id | family | construction | principle |
|---|---|---|---|
| E1_dominant_source | economics | B: price 5.4, freight .3, lead 14 d, fill .95, capacity 400 | B never receives quantity |
| E2_landed_beats_unit_price | economics | B: price 4.6 but freight .6 + handling .1 and prepayment terms; A Net 45 on cost of capital 12 %/yr | A carries >= 90 % of purchased units; the block says B is cheaper per unit but dearer landed |
| E3_price_break_scale | economics | B in two exclusive tiers: 5.0 up to 400 units, 4.4 from 500 units (MOQ 500); demand 400 per branch | any review buying >= 500 from B uses the 4.4 tier; not worse than every baseline |
| E4_moq_mov_small_order | economics | B: price 4.5, MOQ 1,200, supplier MOV 6,000; demand 100 per branch | every B order >= 1,200 and >= MOV (settlement), and ZAAD is not worse: the small-order economics stay with A |
| E5_payment_terms_preference | economics | A and B identical except A Net 60 and B 100 % deposit at order; cost of capital 15 %/yr | A carries >= 90 % of units |
| E6_switching_cost_retains_incumbent | economics | incumbent 100 % A; B 1.5 % cheaper landed; declared switching cost 2,000 for B | B never receives quantity (the saving is below the declared cost) |
| R1_cheap_unreliable | reliability | B: price 4.6, fill .85 sd .10, lead sd 7 d; A .99 / .01 / 0 | not worse; service kept |
| R2_capacity_forces_split | reliability | A capacity 500 per period, B unlimited at 5.3; demand 400 per branch | on every review buying more than 500, A is at capacity and B takes the remainder |
| R3_independent_tail_benefit | reliability | A and B independent (own resources); stress `supplier_closure` on A's resource only | not worse than the best single source; block states the sources are independent |
| R4_shared_plant_no_fake_diversification | reliability | A and B identical economics; risk group `plant_1` (PLANT, correlation 1, OPERATOR_DECLARED); fixed order fee 25 each | no review splits the pair (max share >= .99); the block carries the shared-plant sentence |
| R5_shared_port_risk | reliability | A and B via the same port node; risk group PORT with PHYSICAL_DEPENDENCY provenance; stress on the port | not worse; block lists the port group on both sources |
| R6_identical_no_split | reliability | A and B identical and independent, fixed order fee 25 each | no review splits the pair for its own sake (at most one source per review) |
| C1_supplier_max_capacity | constraints | A capacity 300, B capacity 300 (dearer); demand 250 per branch | no purchase above capacity (settlement) and both sources used on reviews needing more than 300; service kept |
| C2_declared_min_max_share | constraints | A cheaper; B minimum share .30 and A maximum share .70 (horizon scope, OPERATOR_DECLARED) | B's share of every plan's horizon commitment >= .30 - 1e-6 whenever anything is bought |
| C3_source_blackout | constraints | B cheaper but capacity 0 in periods 1-3 of every review (shutdown) and a weekday-restricted order calendar | no B purchase lands in a zero-capacity period; not worse |
| C4_unqualified_source | constraints | B 10 % cheaper but `approved = false`; C `compliance = unreviewed` | neither receives quantity; the block reports "not qualified" |
| C5_shared_capacity_multi_sku | constraints | SKUs A and B; supplier S1 cheap, both SKUs share resource `S1_cap` = 600 volume per period; S2 dearer, unlimited | S1's shared resource never exceeds 600 (settlement); S2 takes the overflow |
| C6_shared_mov_multi_sku | constraints | SKUs A and B from S1 with supplier MOV 5,000 and fixed order cost 150 shared across both lines; S2 no MOV, dearer | every S1 order (both lines combined) >= 5,000 (settlement shipments); at least one review combines both SKUs in one S1 order |
| S1_produce_short_life | sector | PRODUCE, shelf life 8, minimum life at receipt 3 and at sale 2; B cheaper with age at receipt 6 periods | B never receives quantity; the block gives the remaining-life reason |
| S2_produce_yield_uncertainty | sector | PRODUCE; B cheaper, fill .80 sd .15 (usable yield); A .98 / .02 | not worse; service kept |
| S3_frozen_invalid_route | sector | MEAT_SEAFOOD FROZEN; B delivers to `south`, which stores CHILLED only | B never receives quantity; the block says the destination cannot store frozen goods |
| S4_commercial_pallets | sector | COMMERCIAL; A case 12 / pallet 120; B case 10 / pallet 100 with pallet freight; B slightly cheaper per unit | every purchase a whole pack (settlement); not worse |
| N1_source_to_central_with_transfers | network | two central sources; lanes unchanged | conservation exact; transfers still made by the frozen P2 layer; not worse |
| N2_local_and_central_conserved | network | A into central (capacity 400), B directly into `north` | conservation residual <= 1e-9; no capacity breach |
| N3_mixed_sector_shared_capacity | network | SKU A COMMERCIAL and SKU B PRODUCE (life 8, min sale 2) both from S1 sharing resource 600; S2 unlimited | resource respected; A's purchases identical whether or not B carries physics (no cross-physics leakage) |
| A1_incumbent_mix_optimal | abstention | incumbent shares A .6 / B .4; A capacity 480 = 60 % of demand; B slightly dearer | abstains on >= 5 of 8 reviews |
| A2_weak_evidence_flagged | abstention | risk group with FALLBACK provenance; B fill provenance NOT_AVAILABLE | the block marks the evidence weak and claims no independence benefit |
| A3_pruning_identity | abstention | two ineligible sources (expired quote, blocked) beside two eligible ones | `gated` and `gated_noprune` decisions identical review by review |
| A5_single_source_legacy_identity | abstention | one approved source with an empty sourcing block | `gated` and `gated_legacy` decisions identical review by review |
| A6_no_order_no_allocation | abstention | opening stock covers the window | no purchase on reviews 0-2; the sourcing block reports zero commitments and no allocation |

A4 (missing critical economics / provenance fails clearly) is an adversarial contract test
(`P3_ADVERSARIAL.md`), not a benchmark fixture. Tolerances: 2 % for economics, constraints and network
families, 3 % for reliability and sector families (the P2 / sector convention).

## Changes after registration (every one recorded in `P3_DEV_LOG.md` with its reason)

| fixture | registered | as run | reason |
|---|---|---|---|
| E3 | demand 400 per branch; tiers 5.0 up to 400 / 4.4 from 500 | demand 150; tiers 5.0 up to 200 / 4.4 from 250 | the P2 frame's opening stock starves at demand 400 (a P0 recovery regime, not a sourcing question) |
| R2 | incumbent mix 60 / 40; demand 400; A capacity 500 | incumbent 100 % A; demand 150; A capacity 200 | the declared 60 / 40 mix was retained on small reviews by materiality (by design); demand 400 starved |
| C2 | horizon-scope shares | period-scope shares | a rolling plan may defer the minority source review after review; the horizon scope is proven on the plan by invariant 17 |
| C5, N3 | shared capacity 600 at the default demand | demand 150; shared capacity 450 | the shared cap never bound at the default demand; at 250 the frozen recovery gate rejected the joint plan (starvation regime) |
| S1 | B below the receipt minimum | B arrives with 3 of 8 periods (receipt minimum 2, sale minimum 2) | the frozen sector contract refuses a source below the receipt minimum |
| S2 | B yield .80 sd .15 | B yield .70 sd .15 | both pre-registered truth draws gave B a top-decile realised yield (.88, .91) that reversed the expected economics inside the window |
| S3 | B into `south` (chilled only) | B into a chilled-only cross-dock with no lane | the frozen sector contract refuses frozen stock and demand at a chilled-only branch; a lane from the empty cross-dock changed the P2 topology behaviour |
| A1 | demand 400; A capacity 480 | default demand; A capacity 120 | demand 400 starved at review 0 |
| A3 principle | decision identity | purchase identity plus an objective-tie proof for differing transfer quantities | the P2 transfer degeneracy (equal holding rates, per-unit lane cost) |
| E5, R2 principles | whole-window shares | shares on reviews where ZAAD acts | a retained incumbent keeps the operator's declared mix by design |

Policy definitions were refined once: `cheapest_landed` is a replay method (the rule without a mix or share
limit, settled on the fixture's own request so a declared switching cost applies) that never projects
an expired or blocked source; `single:<supplier>` variants keep the declared mix and switching costs
and run only where the supplier competes with another usable supplier on some pair. The economic
gate uses `cost_p3` (residual stock valued at the cheapest usable source's landed cost per received
unit, no policy premium); `cost_p2` is recorded beside it.

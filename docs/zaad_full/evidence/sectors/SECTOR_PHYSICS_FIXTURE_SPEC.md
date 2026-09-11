# Sector physics: pre-registered fixture specification

Dated 2026-09-11, before the physics implementation is tuned against any result. Changes after this
date are appended as dated corrections with the coding or specification defect they fix; fixtures,
seeds, tolerances and pass rules are not otherwise edited after results are seen.

## Common frame

Every fixture is built by `zaad.sectors.fixtures.sector_request` on top of the P2 builder
(`zaad.meio.fixtures_p2.p2_request`): weekly periods, horizon 12, one SKU unless stated, one supplier
into the central DC, two branches (north, south) with one lane each, or a single node where stated;
seeds 41001 / 41002; eight rolling reviews; the P2 world rule (`network_scenarios`) and budget rule
(`network_solve_seconds`, base 15 s); demand 100 / week per branch at 15% noise; unit price 5, holding
15% / year, target .95; the incumbent is the declared `network:rop` rule (single node: `reorder_point`).
Policies: the P2 set (`network_rop`, `central_pool`, `independent`, `echelon_base_stock`, `gated`) on
network fixtures; `gated` against `network_rop` on single-node fixtures. Scoring: the P2
continuation basis (`scripts.p2_benchmark.p2_score`), settled on the truth with the physics enforced
by the settlement for every policy. A baseline that cannot execute under the physics
(PHYSICAL_FAILURE) is recorded as such and excluded from "best baseline".

Economic gate: ZAAD's cost is within the fixture tolerance of the best valid baseline (2%, 3% for
shortage / shock fixtures). Service gate: on every branch ZAAD's service is no worse than the
incumbent's by more than .01 where the incumbent meets target, and at least the incumbent's where
it does not. Structural gates: conservation residual <= 1e-9, no reverse pairs, no PHYSICAL_FAILURE
on ZAAD, no required-candidate starvation. Each fixture adds its own principle check below.

Materiality: on a well-run fixture the correct answer is abstention; "abstained on k of 8 reviews"
is a recorded property, not a failure.

## COMMERCIAL (sector_mode COMMERCIAL, ambient, shelf life 52; physics exercised through the frozen P1 economics)

| id | fixture | physics | principle check |
|---|---|---|---|
| C1 | case-pack rounding | `case_multiple` 12 on the supplier source | every ZAAD purchase is a multiple of 12 (settlement would refuse otherwise); explanation names the case size |
| C2 | pallet / load threshold | `units_per_pallet` 120, `freight_per_pallet` 40, `max_pallets` 8 per shipment, `weight_per_unit` 2.5 with `max_shipment_weight` 2,200 (the weight cap binds before 8 pallets) | no shipment above 8 pallets or 2,200 weight; explanation names the binding load limit |
| C3 | MOQ / MOV economics | `minimum` 240 units, `minimum_order_value` 1,800, `fixed_order_cost` 60 | no purchase between 0 and the MOQ; every order's value >= MOV |
| C4 | long import lead | `supplier_lead_days` 35 (five periods), age at receipt 0 | ZAAD is not worse than the best baseline; abstention property recorded |
| C5 | variable supplier arrival | `lead_sd_days` 7 (one period), fill .95 sd .03 | as C4 under the P0 protection machinery; no starvation |
| C6 | storage-capacity constraint | branch `capacity_volume` 320 units | no receiving-capacity breach (settlement refuses otherwise); ZAAD not worse than the best valid baseline |
| C7 | no material improvement | well-stocked, calm demand, incumbent already economic | ZAAD abstains on >= 6 of 8 reviews; cost within .5% of the incumbent |

## PRODUCE (sector_mode PRODUCE, ambient / chilled, shelf life 3 to 6 periods)

| id | fixture | physics | principle check |
|---|---|---|---|
| P1 | fresh inventory, no unnecessary purchase | shelf life 6, opening lots fresh (expiry 6), min life at sale 1 | ZAAD does not buy while sellable stock covers the lead; abstains on the first two reviews |
| P2 | near-expiry inventory | opening branch lots at expiry 2 (one sellable period with min life at sale 1) | ZAAD's period-zero action is a purchase or transfer the incumbent rule (which counts physical units) does not make; north service >= incumbent's + .05 |
| P3 | age-at-receipt deterioration | shelf life 6, import source age at receipt 3 (three sellable periods on arrival), local source age 0 at a 20% price premium | ZAAD uses the local source for at least part of the demand; expired units per week below the incumbent's |
| P4 | transfer becomes useless | shelf life 4, south lane lead 3, min life at sale 1: a south transfer arrives with at most one sellable period | ZAAD transfers to south less than the incumbent rule and never a cohort that arrives unsellable (invariant 7 / settlement); north (lead 1) still served |
| P5 | spoilage against service | shelf life 3, demand noise 30%, target .95 | ZAAD's expiry cost plus shortage cost is not worse than the best baseline; expired units reported |
| P6 | uncertain usable yield | supplier fill mean .85 sd .08 (declared, OPERATOR_OBSERVED) | ZAAD keeps service under the yield uncertainty (>= incumbent); no starvation |
| P7 | FEFO settlement | two opening cohorts (expiry 2 and 5) at each branch | settlement consumes the older cohort first on every review (invariant 5); no unit served after its sellable life |
| P8 | no material improvement | well-run produce network, fresh lots, calm demand | ZAAD abstains on >= 5 of 8 reviews |

## MEAT_SEAFOOD (sector_mode MEAT_SEAFOOD; two SKUs where stated)

| id | fixture | physics | principle check |
|---|---|---|---|
| M1 | chilled shelf life | one CHILLED SKU, shelf life 3, min life at sale 1, all locations CHILLED-capable | ZAAD serves without expiring more than the best baseline; service >= incumbent |
| M2 | frozen shelf life | one FROZEN SKU, shelf life 40, all locations FROZEN-capable | behaves like commercial (no expiry within the window); abstention property recorded |
| M3 | storage-state infeasibility | FROZEN SKU; south lists only CHILLED | no frozen unit is ever held at or shipped to south (invariant 8); south's demand for the frozen SKU is unavoidable shortage, reported as such |
| M4 | cold-chain lane infeasibility | CHILLED SKU; the south lane lists only AMBIENT; a second lane `reefer_south` lists CHILLED at 3x cost | every south transfer uses `reefer_south` (invariant 9) |
| M5 | aging against service | CHILLED SKU shelf life 3, demand noise 25%, target .97 | ZAAD not worse than the best baseline on cost; expired units reported; abstention property recorded |
| M6 | transfer of a usable lot | CHILLED SKU shelf life 5, central holds a lot at expiry 4, north is short | ZAAD moves the lot to north in period zero (arrives with 3 periods > min life 1) |
| M7 | transfer rejected by expiry | as M6 with the lot at expiry 2 and lane lead 1, min life at receipt 1 | the lot is not moved (arrival at 1 period = at the threshold); it is consumed or expires at central; explanation states the remaining life |
| M8 | no material improvement | well-run frozen network | ZAAD abstains on >= 6 of 8 reviews |

## MIXED (sku_physics per SKU)

| id | fixture | physics | principle check |
|---|---|---|---|
| X1 | commercial + produce at one location | two SKUs at the same branches: A commercial (shelf 52), B produce (shelf 4, min sale 1); shared branch capacity 400 units | B's expiry never charges A; A's decisions equal the single-SKU commercial run of the same seed within 1% cost (invariant 11); capacity respected |
| X2 | produce + frozen seafood sharing network capacity | A produce (chilled, shelf 4), B seafood FROZEN (shelf 40); lanes CHILLED+FROZEN capable with capacity 250 / week shared | lane capacity respected; frozen units never expire; produce never served past its sellable life |
| X3 | three sectors, no cross-physics | A commercial ambient, B produce chilled, C seafood frozen; south lists AMBIENT + CHILLED only | C never at south; A and B unaffected by C's ineligibility; conservation reconciles per SKU |

## Runtime record

Every review's wall time is recorded; reviews above 60 s are profiled and explained; any review above
180 s is a phase blocker unless outside the interactive contract.

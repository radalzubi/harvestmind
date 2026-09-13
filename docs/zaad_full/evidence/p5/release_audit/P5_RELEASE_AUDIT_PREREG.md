# P5 release audit — pre-registered audit cases (written before the corrected engine ran them)

Starting head `17d2d74` (PR #71). Cases run through `scripts/p5_release_audit.py`; pass conditions are
fixed here. Economics under audit: the lost-sale basis (item A) and the SLA / shortage-penalty
provenance rule (item B); the P4 workspace plumbing (item C). Corrections to a case after a run are
allowed only for a documented genuine fixture defect, logged in `P5_RELEASE_AUDIT.md`.

Expected basis after the audit decision (recorded in advance, tested by R01): a unit not shipped costs
its **lost contribution** = `Service.selling_price - SKU.asset_value` (the frozen model's own allocation
ranking basis, `model.py` / `settlement.py`: `-(selling_price - asset_value)`), unless a line or class
margin is declared; the gross selling price is reported as information only. A zero-contribution unit
is still served when serving is otherwise free (documented tie).

| id | case | state | pass condition |
|---|---|---|---|
| R01 | selling price vs declared margin, ranking changes | stock 50 north; line a declares `unit_margin` 2, line b uses the frozen contribution (10 - 5 = 5); second part: north 30 + central 200, lane cost 6 per unit, line 80 with `cross_location` | b filled 50, a 0, `why` cites lost contribution 5 against 2 (under the gross basis both would read 10 and tie); second part: nothing shipped over the lane (6 > 5), 50 unmet, `alternative_ship_from` 0; with a declared line margin 8 the lane is used (50 via lane) |
| R02 | minimum-ship with retained inventory | stock 50; line 80, `minimum_ship_quantity` 60 | nothing shipped, 80 unmet; `remaining_supply` shows 50 `remaining_unreserved` (retained, not charged); `lost_contribution` = 80 x 5, `sla` = 80 x 2.5, `gross_lost_sales_opportunity` (informational) = 800 |
| R03 | all-or-nothing | stock 50; two lines of 40, partial forbidden | exactly one line ships 40, the other is unmet 40, 10 units retained and reported as remaining; ledger charges only the unmet line |
| R04 | SLA only | class penalty 0, Service SLA 2.5; scarce | `sla` = unmet x 2.5, `shortage_penalty` 0, no basis required |
| R05 | shortage penalty only | services with SLA 0, class penalty 3 (no basis) | accepted (no second consequence exists), `shortage_penalty` = unmet x 3, `sla` 0 |
| R06 | both, distinct provenance | Service SLA 2.5 + class penalty 3 with `shortage_penalty_basis` ADDITIONAL_TO_SERVICE_SLA, provenance CONTRACT, reference MSA-9; variant REPLACES_SERVICE_SLA | ADDITIONAL: `sla` = unmet x 2.5 and `shortage_penalty` = unmet x 3, drivers show both with basis; REPLACES: `sla` 0 for those lines, `shortage_penalty` = unmet x 3, `sla_replaced_per_unit` 2.5 reported |
| R07 | duplicate-equivalent declaration fails closed | (a) class penalty 2.5 = SLA, no basis; (b) penalty 3, no basis; (c) ADDITIONAL with provenance CONFIGURED_ASSUMPTION; (d) ADDITIONAL without reference | each refused at the contract with a message naming the double-declaration rule |
| R08 | incumbent optimal | I18 declaration with the basis declared | `NO MATERIAL ALLOCATION IMPROVEMENT AVAILABLE`, value 0, recommendation = incumbent |
| R09 | P0 overlay non-binding | I01 through `plan()` | north promised 150 = allocatable although `protection_units` 21.8 (`below_protection_units` > 0); frozen report identical with and without the block |
| R10 | existing reservations unavailable | I06 | envelope reserved 60, allocatable 40, Σ promised 40 |
| R11 | uncertain OpenPO never firm | I08 | PO in `non_firm_availability` with promised 0; no shipment from it; confidence 0.8 refused |
| R12 | firm inbound promise timing | I11 and H | units promised at or after `due_in`, never before; backorder at period 2 |
| R13 | alternative ship-from creates no P2 transfer | I17 | `p2_transfers_created` 0, shipments tagged ALTERNATIVE_SHIP_FROM with a lane id, no `transfer` ledger key, no transfer action in the report |
| R14 | FEFO / perishable | I04 | old cohort 60 before new 40; unsellable cohorts never drawn |
| R15 | cold chain | I05 | only north's 40, blocked central lot with the storage-state reason |
| R16 | P4 recourse workspace false / true | vault with a declared `stg_recourse_spec` row; `POST /plan/from-workspace` | `recourse=false` (and no flag): no `recourse` key, report identical to the no-flag call (timing stripped); `recourse=true`: `report["recourse"]` present with `review_periods` [3] and the P4 verdict; the built request carries `recourse.enabled` true |
| R17 | P4 + P5 workspace together | same vault plus migration 020 rows; `atp=true&recourse=true` (`ZAAD_ATP_ENABLED=1`) | `request/from-workspace` carries both blocks; `plan/from-workspace` (shape network) carries `report["recourse"]` and `report["atp"]`; with `atp=false&recourse=true` only the P4 block; keyword passing (no positional dependence) |
| R18 | ATP disabled = pre-P5 behaviour | I20 vs the runtime `6b58764` checkout | reports identical (timing / hashes stripped) |

Regression matrices to be preserved and re-run on the corrected engine: isolated A-V (24), integration
I01-I20 (20), adversarial (17 + the R07 family), invariants 1-20.

## Addendum (after runs 1-2, before run 3; see `P5_RELEASE_AUDIT.md`)

R01 second part re-registered: the line requests period 1 (the lane has a one-period lead; run 1
requested period 0, unreachable for any economics) and the lane costs 9 per unit (runs 1-2 used 6,
below both bases once the frozen SLA 2.5 is added to the unmet cost, so the case did not separate
them). Pass condition: contribution basis (5 + 2.5 = 7.5 < 9) -> nothing over the lane, 50 unmet,
`alternative_ship_from` 0; declared margin 8 (8 + 2.5 = 10.5 > 9) -> 50 via the lane. The gross basis
(10 + 2.5 = 12.5) would ship over the lane in both variants. R07's runner compared the full refusal
message (run 1 compared a 220-character truncation). No other case changed.

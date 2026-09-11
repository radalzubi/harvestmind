# P3 supplier / sourcing portfolio: audit of existing source capabilities

Branch `claude/zaad-sourcing-p3` from canonical `main` `7bc4206` (released runtime `5ca3772` plus two
docs-only merges), worktree `harvestmind-p3`. Read before any P3 code was written: `zaad/full/{contracts,
model,worlds,uncertainty,settlement,economics,policies,planner,workspace}.py`, `zaad/meio/{baselines,
workspace}.py`, `zaad/sectors/*`, `db/migrations/*`, `api/routers/zaad_full.py`.

Classes: **A** already correct (reuse as is) · **B** reusable, needs a P3 connection · **C** partial ·
**D** missing · **E** deferred to P4+ · **F** rejected.

## The source object already exists

`zaad.full.contracts.Source` is "one operator-approved supplier / SKU / destination / itinerary / price-tier
option": `supplier`, `sku`, `destination`, `route` (supplier -> intermediate nodes -> destination),
`resources` (shared capacity pools), `capacity_by_period`, `unit_price`, `freight_per_unit`,
`handling_per_unit`, `minimum` (MOQ), `multiple` / `case_multiple` / `pallet_multiple` /
`transport_multiple`, `maximum`, `fixed_order_fee`, `terms` (payment terms record: deposit, balance
trigger, net days, financing fee, FX, letter of credit), `order_calendar`, `shipping_calendar`,
`lead_days`, `dispatch_days`, production calendar / workdays, leg transit days and arrival calendars,
`fill_mean` / `fill_sd`, `lead_sd_days`, `approved`, `compliance`, `quote_expires`, `quote_reference`,
`exclusive_quote_group` (mutually exclusive price tiers). A SourceOption is therefore this record; P3
adds no second source object.

| capability (brief B6) | where it lives today | class | P3 action |
|---|---|---|---|
| 1 approved source choice | `model.solve`: one purchase column per source and period for every approved, cleared, unexpired source; the joint MILP chooses among them; `Source.approved`, `compliance` | A | none (explicit activation and report only) |
| 2 multi-source split | same columns; capacity, MOQ, packs and supplier orders already make the split executable | A | none |
| 3 source-specific unit / landed cost | `unit_price` x FX, `freight_per_unit`, `handling_per_unit`, `fixed_order_fee`, financing fee; `economics.order_waterfall` attributes each line | A | reuse in the sourcing block |
| 4 source-specific MOQ | `Source.minimum` with the `active` binary; settlement re-checks | A | none |
| 5 source-specific MOV | supplier-level MOV in `SupplierTerms.minimum_order_value` (per supplier order across its lines) | A | none |
| 6 pack / pallet / load executability | pack, case, pallet and transport multiples (general integers); supplier pallets, freight tiers, `max_pallets`, weight cap (sector) | A | none |
| 7 payment terms / financing | `Terms` (deposit, trigger, net days, financing fee, LC) priced through the cash balance and `cost_of_capital_per_period` (P1) | A | reconciliation tests only; no second charge |
| 8 source capacity | `Source.capacity_by_period` (SKU-source-period) and `Resource.capacity_by_period` shared by every source that lists it (volume units); settlement re-checks both | A | none |
| 9 source-specific lead uncertainty | `lead_sd_days`, observed Kaplan-Meier lead support in `uncertainty.supply_profile` from `shipment_history` | A | none |
| 10 source-specific fill / usable yield | `fill_mean` / `fill_sd`, observed accepted ratios, recent fill run (v5) | A | none |
| 11 correlated source failure | `worlds.draw`: sources sharing a failure domain (declared `Resource.failure_domains` plus every intermediate route node) share the same Gaussian supply shock; `Stress.shared_failure` | C | shared domains are perfectly correlated and carry no provenance; P3 adds declared risk groups with a correlation strength and provenance (`SourceRiskGroup`), blended into the frozen shock without touching the frozen stream |
| 12 shared supplier / plant / route risk | as 11: route nodes are automatic shared domains; a shared plant is only shared if the operator lists it as a resource domain or a route node | C | risk groups (kind MANUFACTURER / PLANT / PACKAGING / PORT / ROUTE / CARRIER / 3PL / UPSTREAM_FACILITY) |
| 13 operator-declared contractual share limits | nothing | D | `SourceShareConstraint` (minimum / maximum share, committed units; horizon or period scope) as linear rows |
| 14 source eligibility / qualification | `approved`, `compliance == "cleared"`, `quote_expires` against the order date; physics eligibility (sector) | A | report the reason a source is unusable |
| 15 sector physics | `age_at_receipt_by_source`, receipt life below minimum -> source unusable, storage-state eligibility of the destination, weight cap | A | none |
| 16 incumbent-first abstention | `incumbent_orders` (dated, per source), `incumbent_rule` projections, materiality gate (`economics.materiality`), selector | B | the rule projections buy from the cheapest landed source (`policies._primary_source`); P3 declares the incumbent source mix (`IncumbentSourceShare`) and splits the rule's quantity accordingly |
| 17 multi-SKU shared source constraints | supplier orders (`model.supplier_orders`): MOV, fixed order cost, receipt fee, freight tiers, pallets and weight priced once per supplier and period across every SKU line; `Resource` capacity shared across SKUs | A | none (fixtures C5, C6, N3 prove it) |

Other brief items: **price tiers** (B7, E3): `exclusive_quote_group` makes tier records mutually
exclusive per period (A). **Switching / qualification cost** (B17): nothing (D; `SourceSwitchingCost`,
one first-stage binary per declared non-incumbent source). **Source calendars / blackouts** (B18):
order and shipping calendars with weekdays, blackout dates and cutoff hour move the order and
departure to the next open day; zero capacity in a period is the hard "cannot accept" (A). **External
signals** (B21): `zaad.signals.route_evidence` maps signals to physical severity on the source's route
and resources, which lowers fill and lengthens lead in the worlds (A; the chain signal -> physical
impact -> scenario -> decision already exists). **Scenario-invariant commitments** (B22, B23): every
purchase column is first-stage; only inventory, fulfilment and cash react per world (A). **Exact
pruning** (B25): only the diagnostic `disabled={"alternates"}` (keeps the cheapest landed source); no
zero-capability pruning (D, narrow). **Baselines** (B33): `network:rop` / `network:pool` rule
projections, `independent`, `echelon_base_stock` (A); P3 adds the incumbent mix, the cheapest landed
single source and the best single-source ZAAD run as comparators.

## Workspace / persistence

The vault adapter (`zaad/full/workspace.py`) fits fill and lead per supplier from PO and receipt
history but attaches exactly one supplier per SKU (`stg_fmcg_skus.supplier_id` or the supplier with the
most PO units). There is no SKU x supplier staging table: `stg_fmcg_suppliers` is a supplier master
(capacity per week, promised lead, origin, weight cap) and `stg_fmcg_purchase_orders` carries
`supplier_id`, `sku`, `unit_cost`. Multiple approved sources per SKU therefore need one additive table
(migration 018 `stg_fmcg_sources`: SKU x supplier terms, shares, qualification, provenance) and four
nullable supplier columns for risk groups and switching cost (class D). Existing vaults keep their
schema; without the table the adapter builds the frozen single-source request.

## Rejected (F) and deferred (E)

* F: a supplier reliability score with an arbitrary weight (reliability enters through fill, lead,
  yield and arrival life in the worlds, which already exist).
* F: any diversification rule (share caps, 50/50 splits) not declared by the operator.
* F: inferring correlation from supplier names or shared strings; only declared groups, declared
  resource domains and the itinerary nodes correlate sources.
* F: general dominance pruning ("B is worse than A on every dimension"): with finite capacities two
  sources are additive, so a dominated source can still be needed; the only exact rule kept is
  zero-capability pruning (no eligible period), proven equivalent on fixture A3.
* E (P4): scenario-contingent source switching, recourse after observing the future.
* E (P6): decision-aware model risk on the supply distributions.

## Baselines before any change (this machine, system Python 3.14, scipy 1.18.1 / highspy 1.15.1)

| gate | result | wall |
|---|---|---|
| canonical regression (`scripts.zaad_canonical_regression`) | PASS (B / T / Q / A identical, P0 cell 15) | 48 s |
| sector unit tests (`tests/unit/test_zaad_sectors*.py`) | pass | 73 s |
| P2 invariants (`scripts.p2_invariants --benchmark p2_final`) | see `P3_DEV_LOG.md` entry 1 | |
| sector invariants (`scripts.sector_invariants --benchmark sector_authoritative`) | see entry 1 | |
| P1 invariants (`scripts.p1_invariants`) | see entry 1 | |

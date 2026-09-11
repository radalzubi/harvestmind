# Three-sector physics engine: architecture

Date 2026-09-11 (written before implementation; amended sections are dated).

## One engine, three physical realities

Sector physics does not add an optimizer, an ownership class or an objective term. It changes the
decision environment the frozen engine already optimises over - which units exist, where they may
be, when they may be sold, what a receipt is worth - and lets P0 / P1 / P2 choose the action.

```
Request (frozen contract)  +  sector physics (typed, default-off)
        |                              |
        v                              v
  zaad.sectors.contracts.resolve(req) -> Physics (per SKU, per location, per lane) or None (legacy)
        |
        +--> model.solve        : eligibility caps, sellable allocation, cohort-aware continuation, weight cap
        +--> settlement.settle  : the same physics re-derived from the plan (receipt life, state, sellable FEFO, weight)
        +--> terminal.continuation_value : sellable expiry
        +--> planner.plan / meio.plan_network : `physics` block in the report (explanations, sellable inventory)
        +--> workspace / API   : columns -> physics, validation, provenance
```

`resolve(req)` returns `None` when the request declares no `sector_mode` and no `sku_physics`; every
hook then takes the frozen path with no new variable, row, branch or field read. That is the
legacy-neutrality argument: the physics code is unreachable on a legacy request.

## Contract (`zaad/sectors/contracts.py`)

* `SectorMode`: `COMMERCIAL | PRODUCE | MEAT_SEAFOOD`.
* `Request.sector_mode: SectorMode | None = None` (request default) and
  `Request.sku_physics: tuple[SkuPhysics, ...] = ()` (SKU-level, overrides the default). A mixed
  distributor declares profiles per SKU; a single-sector one declares the mode and only the fields
  that differ per SKU. Unspecified SKUs in a request with a `sector_mode` receive the sector's
  neutral profile (no life thresholds, no age, ambient state): the mode alone changes nothing about
  a SKU until a physics field is declared for it.
* `SkuPhysics` (all fields typed, ranged, with provenance; nothing invented):

| field | units | range | required | fallback | affects |
|---|---|---|---|---|---|
| `sku` | id | must exist in `skus` | yes | - | binding |
| `sector` | mode | one of three | yes | request default | reporting, validation |
| `storage_state` | enum AMBIENT / CHILLED / FROZEN | - | no | AMBIENT | location and lane eligibility; no transitions exist |
| `age_at_receipt_periods` | periods | 0 .. shelf_life-1 | no | 0 | remaining life of every new purchase arrival (`shelf_life - age`) |
| `age_at_receipt_by_source` | periods per source id | same | no | the SKU value | per-source override (import vs local) |
| `minimum_remaining_life_at_receipt` | periods | 0 .. shelf_life-1 | no | 0 | an arrival (purchase or transfer) with less remaining life is not usable: the source or the cohort's lane variable is capped at zero; the settlement refuses it |
| `minimum_remaining_life_at_sale` | periods | 0 .. shelf_life-1 | no | 0 | a cohort is sellable at period t only while `expiry - t > threshold`; unsellable stock stays physical (holding, disposal) but cannot serve, cannot be transferred usefully and earns salvage only in continuation |
| `weight_per_unit` | operator mass unit | > 0 | no | none | shipment weight cap with `SupplierTerms.max_shipment_weight` |
| `provenance` | per field | OPERATOR_OBSERVED / OPERATOR_DECLARED / DERIVED_FROM_OPERATOR_HISTORY / PUBLIC_PRIOR / FALLBACK / UNKNOWN | yes for every declared field | UNKNOWN is rejected for a declared numeric field | reporting |

* Location / lane eligibility lives on the frozen records as optional fields with empty = unrestricted:
  `Location.storage_states`, `Transfer.storage_states` (tuples of the enum). A SKU in state S may be
  held only at locations that list S (or list nothing), and moved only on lanes that list S (or
  nothing). Purchases into an ineligible destination are capped to zero. Opening stock at an
  ineligible location is a validation error (4xx), never silently moved.
* `SupplierTerms.max_shipment_weight: float | None` (P1 record, optional): one row per supplier and
  period, `sum(q * weight) <= max_weight * order`, mirrored in the settlement like `max_pallets`.
* Validation (`zaad/sectors/validation.py`): unknown mode, physics for an unknown SKU, duplicate
  profiles, thresholds at or above shelf life, age at or above shelf life, a state no location can
  hold, stock at an ineligible location, non-positive weight, more profiles than SKUs, unknown
  storage state on a location or lane. Raised as `ValueError` inside the pydantic model so the API
  answers 422.

## Where each rule enters the frozen model (exact, structural, no new binaries)

1. **Purchase arrival life**: `expiry = due + shelf_life - age`. If `expiry - due < min_receipt` the
   source cannot be used (cap 0), and the purchase variable has no arrival. No binary.
2. **Transfer eligibility**: the existing cap-to-zero on `due >= expiry` becomes
   `due + min_receipt >= expiry` or lane / destination state mismatch -> cap 0. No binary.
3. **Sellable allocation**: `allocate` variables are created only for cohorts with
   `expiry - t > min_sale`; the `depleted` anti-hoarding row and the FEFO rows range over sellable
   cohorts only. Fewer variables, not more. Physical inventory, holding, disposal unchanged.
4. **Continuation (P1 slabs) on physics requests**: cohort-aware cumulative rows
   `sum_{j' >= j} served_{j'} <= sum_{cohorts alive and sellable at post-window period j} supply`
   for every slab j, added only when the request carries physics (legacy models keep the single
   aggregate row and their exact frozen identity; the legacy over-credit of a short opening lot
   is recorded in the capabilities audit).
5. **Shipment weight**: one continuous row per supplier-period, like pallets.
6. **Storage capacity, packs, MOQ / MOV, fill, lead**: unchanged frozen physics.

FEFO indicators: unchanged code; in-window cohorts of a perishable SKU keep their indicators
between *sellable* cohorts. Cohort counts stay bounded by (shelf life + lead) alive cohorts.

## Settlement (`settle`)

The same rules, re-derived from the executed plan: purchase arrivals carry `shelf_life - age`; a
receipt (purchase or transfer) below the minimum life at receipt or at an ineligible location is a
`PhysicalViolation`; consumption is FEFO over sellable cohorts; end stock reports `sellable`
units per SKU / location beside the physical rows; the weight cap is checked. Conservation
buckets are unchanged (initial + received - served - expired - transit loss - closing).

## Evaluation and continuation

`terminal.continuation_value` consumes a residual unit only while it is sellable
(`tau < expiry - min_sale`), otherwise salvage. Legacy: threshold 0, identical arithmetic.

## Ownership and explanations

No new owner. The report gains a `physics` block on physics requests only: per SKU the profile
and provenance, per location the physical and sellable on-hand at period zero, and sentences in
sector language produced by `zaad/sectors/explain.py` from the settlement and the plan (rounded
packs, capped receipts, unsellable transfers, ineligible lanes, near-life inventory). Ownership
labels stay P0 / P1 / P2.

## Resource bounds

Profiles <= number of SKUs (<= 5,000, the frozen cap); storage states are a three-value enum;
cohort count per SKU is bounded by the frozen shelf-life cap (520) and the horizon; no lists of
lots, grades or states are accepted. The interactive API caps are unchanged.

## Workspace / API

Optional columns on `stg_fmcg_skus` (`sector`, `storage_state`, `age_at_receipt_days`,
`min_remaining_life_receipt_days`, `min_remaining_life_sale_days`, `weight_per_unit`),
`stg_fmcg_inventory.expiry_date` (lot expiry -> `Stock.expires_in`), `stg_fmcg_locations.storage_states`,
`stg_fmcg_lanes.storage_states`; migration 017 (additive, nullable). Absent columns or null cells
leave the request legacy (UNKNOWN stays unknown); a request-level `sector_mode` query parameter
sets the default sector. The API validates through the contract; malformed physics -> 422.

## What is deliberately not built

Thaw / freeze transitions, gradual shrink, grade mixes, weather or harvest models, processing
yields, routing, supplier portfolio choices (P3).

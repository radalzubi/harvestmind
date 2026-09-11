# Sector physics: what ZAAD already models (audit before any code)

Date 2026-09-11. Branch `claude/zaad-sector-physics` from `main` `ea1ed3a` (released P2 code `9c4ece7`;
frozen `2e30721` / `f7e1e62` / `12db66c` / `cab3849` / `fa615ff` all ancestors). Starting gates in
`baseline/`: canonical regression PASS (B / T / Q / A identity, P0 cell 15), P2 tests 49 passed, P2
invariants 20 / 20, P2 review profiles A r7 0.3 s, H r4 0.8 s, M r7 7.0 s, O r6 0.7 s, Q r6 13.4 s.

Classification: **A** already modelled correctly, **B** present but not sector-aware, **C** partially
modelled, **D** missing, **E** defer to P3+, **F** rejected / not economically useful.

| capability | where | class | note |
|---|---|---|---|
| shelf life (nominal) | `SKU.shelf_life` periods; purchase arrivals expire `due + shelf_life`; POs likewise | A | reused as the nominal life of the SKU in its declared storage state |
| lot / cohort expiry on hand | `Stock.expires_in`; model and settlement keyed by (sku, location, expiry) | A | the workspace adapter sets every opening lot to the full shelf life (`stock.age = NOT_AVAILABLE`): lot expiry from the vault is **D** (workspace) |
| expiry, disposal | model: no terminal credit for `expiry <= H`, disposal charge at `expiry == t+1`; settlement: `expiry <= t` disposed with `disposal_fee`, asset value lost | A | "expired inventory cannot satisfy service" already holds physically |
| FEFO consumption | settlement consumes cohorts by earliest expiry; model FEFO indicators (P2: only between cohorts inside the window, `FEFO_SYMMETRY_ELIMINATION`) | A | guard: perishables reintroduce in-window cohorts, so the indicators return exactly where they are mathematically needed and nowhere else |
| age at receipt | none: every arrival carries the full nominal life | D | produce imports and meat / seafood need `remaining life at receipt = shelf life - age` |
| minimum remaining life at receipt / at sale (sellable life) | none: a unit is sellable until the period it expires | D | the produce and meat / seafood central object; enters allocation eligibility, transfer eligibility, purchase eligibility, continuation |
| transfer age | transfers keep the cohort's expiry (no reset); a cohort that would arrive expired is capped to zero (`due >= expiry`) | A / C | arrival with *insufficient sellable* life is not represented (D, covered by the minimum-life rule) |
| usable yield / short delivery / damage | `Source.fill_mean / fill_sd`, fitted from receipts where history exists (`uncertainty.supply_profile`), sampled per world | A | reused as the usable-yield distribution; no agricultural yield model is added |
| spoilage before expiry (gradual shrink) | none | E | expiry, disposal and fill cover the decision-relevant loss on the fixtures; a per-period shrink rate needs operator observation the staging schema does not carry; recorded as a later addition with its conservation bucket |
| storage state (ambient / chilled / frozen) | none | D | per-SKU declared state; no thaw / freeze transitions (prohibited by construction) |
| location / lane cold-chain eligibility | none | D | optional `storage_states` on `Location` and `Transfer`; empty = unrestricted (legacy) |
| case / inner / pallet / transport packs | `Source.multiple`, `case_multiple`, `pallet_multiple`, `transport_multiple`; lane `Transfer.multiple` (P2); settlement re-checks | A | commercial executability exists; the workspace maps `units_per_case` and pallets |
| MOQ / MOV / fixed order cost / freight tiers / receipt fees / pallet economics / max pallets | `Source.minimum`, `SupplierTerms.*` (P1) | A | P1 owns the economics; not duplicated |
| weight / cube load limits | cube: `SKU.volume` against `Location.capacity_volume` and per-pallet units; weight: none | C | one exact addition: `SkuPhysics.weight_per_unit` with `SupplierTerms.max_shipment_weight` (a load cap like `max_pallets`); no routing |
| import lead time and its variability | `Source.lead_days`, `lead_sd_days`, calendars, legs, dispatch; fitted from shipment history; sampled per world | A | |
| supplier capacity, shared resources | `Source.capacity_by_period`, `Resource` | A (P3 owns portfolio decisions) | |
| storage capacity | `Location.capacity_volume` before and after receipts; settlement raises on breach | A | |
| obsolescence of slow movers | none beyond shelf life | F | `shelf_life` already is the economic life; a second decay curve is not decision-relevant on operator data |
| service basis (physical vs sellable) | `unit_fill` counts served units; a unit can be served until its expiry period | B | with a sellable-life rule, service becomes "sellable fill" by construction; reported alongside `physical_on_hand` / `sellable_on_hand`, never renamed globally |
| terminal value (in solve) | salvage `terminal_value` on cohorts with `expiry > H`; continuation slabs (P1) bounded by `shelf_life - horizon` on the solve side | C | slabs are fed by every post-horizon cohort regardless of its own expiry; sector-explicit cohort-aware slab rows are needed for perishables (legacy left as is, see architecture) |
| terminal value (evaluation) | `terminal.continuation_value`: a unit that expires before it is consumed earns salvage | A / B | sellable-life aware only with the physics threshold |
| dynamic cadence | P1 free schedule, cadence candidates optional | A | unchanged |
| substitution | `Substitute` rules | A | untouched |
| unit of measure | eaches; the workspace converts cases | A | untouched |
| P3 territory: supplier splitting, alternates, contracts | `Source` alternates exist as candidates | E | not touched |

Reused rather than re-created: shelf life, cohorts, FEFO, fill yield, packs, MOQ / MOV, pallets,
capacity, lead-time uncertainty, disposal, terminal salvage, continuation. New physics is limited to
what the audit marks D or C: age at receipt, minimum remaining life at receipt / at sale, storage
state with location / lane eligibility, shipment weight, cohort-aware continuation on physics
requests, lot expiry from the vault.

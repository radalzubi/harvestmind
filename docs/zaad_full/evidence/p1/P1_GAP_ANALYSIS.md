# P1 cycle-stock economics — gap analysis (audit before code)

Branch `claude/zaad-cycle-stock-p1`, worktree `harvestmind-p1`, parent (frozen P0) SHA `2e30721`.
Audited: `zaad/full/{contracts,model,worlds,settlement,planner,capital,replay,echelon,protection}.py`,
`scripts/run_zaad_full_benchmark.py`, `zaad/full/demo.py`, `docs/zaad_full/evidence/v8/P0_CLOSEOUT.md`.

## What already exists and is correct (reuse, do not rebuild)

| requirement | status | where |
|---|---|---|
| Review vs order vs ship vs arrival dates, supplier order calendar, shipping calendar, production workdays, dispatch days, multi-leg transit, receiving calendar | IMPLEMENTED_CORRECTLY | `worlds.dates()`; `next_open()`; used by the MILP and settlement identically |
| Order quantity chosen jointly with timing over the horizon, under demand/fill/lead uncertainty (scenario worlds), usable on-hand and pipeline | IMPLEMENTED_CORRECTLY | `model.solve()` network MPC; `targets()` is only the incumbent proxy |
| SKU/source MOQ (`minimum`), pack (`multiple`), case / pallet / transport multiples as integer variables; source maximum, per-period capacity, shared resource capacity | IMPLEMENTED_CORRECTLY | `model.py` purchase block; settlement re-checks every one (`pack violation`, `case/pallet/transport multiple violation`, `source capacity / MOQ`) |
| Per-source fixed order fee (binary `active`), per-unit freight, per-unit handling (= per-unit receiving) | IMPLEMENTED_CORRECTLY | `expense(active, fixed_order_fee)`, `landed` |
| Payment terms: deposit, balance trigger (order/shipment/arrival) + net days, financing fee fraction, letter-of-credit reserve; prepaid = deposit 1.0 | IMPLEMENTED_CORRECTLY | model `payments[w][t]`; settlement mirrors; cost recognised in full at order, cash timed separately |
| Cash balance, credit limit, interest per period on drawn debt (time-scaled per period), terminal solvency | IMPLEMENTED_CORRECTLY | model cash/debt rows; settlement `insufficient dated liquidity` |
| Carrying cost per value per period per location; disposal; terminal value; continuation demand | IMPLEMENTED_CORRECTLY | `holding_per_value_period`; single blended rate, no components |
| Storage capacity (volume per location, incl. locked stock) | IMPLEMENTED_CORRECTLY | model inventory bounds + capacity row; settlement `receiving capacity breach` |
| Usable inbound with correct timing (open POs by due period × fill; inbound transfers) | IMPLEMENTED_CORRECTLY | `arrivals[w][sku, loc, expiry, due]`; PO amendments keep/cancel/expedite |
| Service floors, protection (lean baseline, active drivers, quantile), FTL/warm start/accounting safety | IMPLEMENTED_CORRECTLY (P0 frozen) | untouched |
| Ledger components: procurement, freight, handling, order_fees, financing, holding, disposal, sla, lost sales, substitution, transfer, opening/closing assets; `ledger_residual` check | IMPLEMENTED_CORRECTLY | `settlement.settle()` |
| Abstention: RETAIN_INCUMBENT when benefit not material (`downside_cost_tolerance`, bootstrap lower bound, capital tie-break) | PARTIAL | selector; no explicit "NO MATERIAL IMPROVEMENT AVAILABLE" verdict, materiality not separately configurable by inventory / service |
| Inventory attribution waterfall (demand_cycle, local_service, source_lead, pooled, active_protection, moq_pack, early_order, ...) | PARTIAL | `capital.decompose`; no MOV / freight / calendar categories; per on-hand unit, not per order |
| Timing explanation (needed-by, latest safe order period, cash advanced) | PARTIAL | `procurement_timing`; no need-construction waterfall, no rounding attribution |
| Baselines: incumbent, projected base stock, order-up-to, deterministic, stochastic, robust, echelon | PARTIAL | `replay.choose`; no periodic-review-at-cadence or economic-lot (EOQ-like) baseline |

## Gaps

| requirement | status | note |
|---|---|---|
| Supplier minimum order value across SKUs | MISSING | only per-source unit MOQ exists |
| Supplier-level fixed order cost shared by the SKUs on one order | MISSING / CONFLICTING | `fixed_order_fee` is per source (SKU) per period: three SKUs from one supplier pay it three times |
| Receiving cost: fixed per receipt, per pallet | MISSING | only per-unit handling |
| Freight: per-shipment fixed charge, stepped LTL/FTL/container tiers, per-pallet, max shipment | MISSING | only per-unit freight; `transport_multiple` rounds units, does not price the shipment |
| Cadence comparison (weekly / biweekly / monthly / calendar) on total cost | MISSING | the MILP picks timing freely (dynamic cadence) but nothing compares or reports cadences |
| Opportunity cost of own cash (working capital) | MISSING | financing charged only when debt is drawn; identical POs with different cash timing are indistinguishable when cash is ample |
| Provenance of economic inputs | MISSING | no CUSTOMER_PROVIDED / INFERRED / CONFIGURED / NOT_AVAILABLE tagging |
| Total-cost decomposition and working-capital report as first-class outputs | PARTIAL | ledger exists; not surfaced per candidate with ordering/receiving split |
| Per-order economic construction (demand until next feasible arrival + protection - on hand - inbound + rounding/economics) | MISSING | |
| Explicit NO MATERIAL IMPROVEMENT verdict with configurable materiality | PARTIAL | |
| Sector physics, network pooling | OUT_OF_SCOPE (P2 / sector) | |

Hidden buffers: none found. Every unit the MILP holds is a consequence of service floors, packs, MOQ, lead times or explicit protection; `targets()` (incumbent proxy) uses the calibrated quantile only. `order_smoothing` (.02) is a small declared term, not a buffer. Duplicated economics: `fixed_order_fee` per source vs a supplier-level order cost (resolved by making the supplier-level cost a separate field; the per-source fee stays a per-line fee). No double counting between holding (accrual on asset value) and financing (interest on drawn debt) - the new cost of capital must be charged on cash deployed, never on the same dollars as debt interest.

Units: quantities in SKU units; packs/cases/pallets as integer multipliers of units (`multiple`, `case_multiple`, `pallet_multiple`, `transport_multiple`); volume in location units of volume; money in request currency after `fx_rate_to_currency`; time in periods of `period_days` days; rates per period (`holding_per_value_period`, `interest_per_period`); calendars in days. Annual rates supplied by customers must be converted with `period_days / 365` at the boundary (fixtures do this explicitly).

## Smallest architecture that satisfies P1

1. **Data model** (`contracts.py`): `SupplierTerms` (supplier, minimum_order_value, fixed_order_cost, receiving_fee_per_receipt, receiving_per_pallet, units_per_pallet, freight tiers `{up_to_pallets, charge}`, per_pallet freight, max_pallets, provenance); `Liquidity.cost_of_capital_per_period`; materiality settings; a provenance map for existing economic fields.
2. **One formulation** (`model.py`): per (supplier, period) an order binary tying its sources' `active` flags, MOV row `sum(q*price) >= MOV * order`, fixed order cost expensed once, integer pallets `>= sum(q / units_per_pallet)`, tier binaries with `pallets <= sum(up_to_k * tier_k)` and `sum(tier_k) = order`, tier charge + per-pallet freight + receiving fees expensed; cost-of-capital term on cash; an `allowed_periods` mask for cadence-restricted candidates. Settlement mirrors every row and raises on violation.
3. **Economics module** (`economics.py`): cost decomposition (purchase, freight, ordering, receiving, carrying, financing, shortage, other) reconciling to `economic_cost`; working capital; per-order construction waterfall with attribution; abstention verdict; plain-language explanation. Attached to the planner report; candidate ranking unchanged (total cost, same gates).
4. **Cadence candidates** as OPTIONAL classes (weekly / biweekly / monthly / supplier-calendar) so the comparison is explicit and reported; the unrestricted solve remains the dynamic cadence.
5. **Baselines** in `replay.choose`: `periodic_review` (order-up-to at a fixed cadence) and `economic_lot` (reorder point + fixed lot from order cost and carrying rate).
6. **Fixtures A-T** with pre-registered expectations and a runner producing the required table.

## Runtime estimate

P1 fixtures are single-location, one to three SKUs, H=12, 3 scenarios: 1-15 s per review. 20 fixtures x 6 policies x 12 reviews ~ 1,400 solves, ~40-60 minutes single-process; well under the 8-hour limit. Unit tests seconds. No benchmark near the limit is planned; the six-cell P0 set is not re-run by P1.

## Amendment (after Phase 9, recorded rather than rewritten)

The audit above said `order_smoothing` (.02) was "a small declared term, not a buffer". That was
wrong. Measured on the P1 fixtures it is a material shadow cost: 2% of landed unit cost per unit of
period-to-period change in each source's order quantity, charged in the model objective only and
never in the settlement ledger. On a $5 item a 1,000-unit consolidated order pays about $200 of
phantom cost (the ramp up and the ramp down), the size of an undeclared fixed order cost, and the
model answers by spreading purchases evenly and buying early (see the `smooth_up`/`smooth_down`
columns; fixture reproduction in `tests/unit/test_zaad_p1_economics.py::test_timing_tiebreak_...`).
With explicit order-level economics it double-counts lumpiness. The P1 fixtures set
`order_smoothing=0` explicitly (a request setting, documented in `zaad/full/fixtures_p1.py`); the
P0 product default (.02) is untouched, an ablation arm keeps it on, and revisiting the default is
the recommended next step, not executed here.

A second timing property surfaced by the same investigation: with no declared cost of capital and
a small holding rate the model is indifferent between committing cash now or later and HiGHS
returns whichever it finds first. `timing_tiebreak` (1e-4 of unit price per period of earliness,
objective only, never settled) breaks the tie toward later commitment; it is two orders of magnitude
below the smallest materiality the selector acts on.

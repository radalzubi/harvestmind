# P5 — shared-core integration: state contract, ledger ownership, architecture

Status: shared-core integration engineering (branch `claude/zaad-atp-p5`, worktree `harvestmind-p5`).
Starting state: canonical `main` `50980fc`, production runtime `6b58764` (tag
`p4-performance-closure-runtime`), P4 closed. Isolated P5 baseline: tag `p5-isolated-baseline` =
`660e5fc` (pushed; isolated tests, 24 / 24 fixtures and 16 / 16 adversarial re-run from that exact SHA,
`docs/zaad_full/evidence/p5/benchmarks/p5_isolated_baseline`). Nothing here is deployed or released.

## 1. Allocatable-supply envelope (`zaad/atp/state.py`)

What P5 may consume, in order, per (SKU, location, period):

| step | source | frozen semantics it mirrors |
|---|---|---|
| physical | `Stock.quantity` | the settlement's `locked` volume counts everything physical |
| physically usable | minus `Stock.damaged`, `Stock.quarantined` | `Stock.usable` |
| sellable | minus cohorts unsellable at the promise period (`Physics.sellable`: remaining life), locations the SKU's storage state may not occupy (`Physics.location_ok`) | the frozen model and settlement allocate only sellable cohorts at eligible locations |
| unreserved | minus `Stock.reserved` | `Stock.usable` excludes it: the frozen model's opening stock (`model.py`: `initial[...] += lot.usable`) and the settlement's opening position never plan on reserved units. It is the frozen contract's ONLY hard reservation |
| hard commitments owned elsewhere | none exist | P0 protection is a service-level construct (quantile / CVaR service floors and the protection profile) inside the planner's candidate solves; the contract has no record that reserves units for it. P1 purchases, P2 transfers and P3 sourcing add supply or move it; none reserves it |
| = allocatable ATP | on-hand lots P5 may promise | |

**P0 protection interaction.** P0 expresses protection economically and through service constraints,
not as a reservation, so P5 does not invent one: a firm customer order is realised demand, which is
what protection exists to serve. On the planner path the P0 profile of the same request is reported
as an **overlay** per (SKU, location): `protection_units`, `lean_baseline_units`, regime, the on-hand
allocatable stock, what P5 promises from it, what remains, and `below_protection_units` (how far the
remaining position sits under the P0 protection level), `hard_reservation: false`. P0's next review
plans from the position the promises leave. Outside the planner the overlay is marked unavailable.

**Future availability** is split by the frozen semantics of the record, never by a confidence factor:

| tier | record | frozen semantics | P5 |
|---|---|---|---|
| on-hand ATP | `Stock` | opening stock | promisable now |
| FIRM inbound | `InboundTransfer` (accepted quantity in flight, `due_in`) | the frozen model fixes it (`lower = upper = accepted_quantity`) and the settlement lands it at `due_in` unconditionally | promisable at or after `due_in` when `include_inbound` |
| NON-FIRM inbound | `OpenPO.expected_accepted_remaining` | fill and lead are drawn per world (uncertain) | never promised; reported as `non_firm_availability` with the expected period; `next_promise` distinguishes firm from non-firm |

`inbound_confidence` is kept in the schema (migration 020 column) but only the value 1 is accepted:
any other value is refused at the contract ("probabilistic inbound is never promised"). No threshold
converts uncertain supply into a promise.

**Direct fulfilment versus P2 transfer.** A line's eligible ship-from set (the service's own
location by default, or the declared `ship_from`) is served DIRECT. With `cross_location`, stock at
a non-eligible location reachable over an approved, physics-eligible lane is priced as
`ALTERNATIVE_SHIP_FROM` (lane unit cost, lead, capacity) and every such shipment carries
`fulfilment: ALTERNATIVE_SHIP_FROM` and the lane id. P5 emits no transfer: the report states
`p2_transfers_created: 0`, and supply that would need one (location not eligible and no approved
eligible lane, or `cross_location` off) is listed in `blocked_supply` with the reason "no implicit
transfer is created".

**Reservation ownership.** Every shipment of the recommendation is one proposed reservation
(`reservations`): id, customer, order, line, requested and supplied SKU, quantity, physical units,
lot (with the frozen record it came from), location, lane, fulfilment, promise period, requested
period, status `PROPOSED`. Conservation is a hard row per lot (no unit twice), per line the unit
states sum to the requested quantity, and `Stock.reserved` never enters a lot. Release semantics:
nothing is persisted or committed by P5; on operator approval the units are recorded as
`Stock.reserved` (the frozen hard reservation) by the operator's own order management, which also
releases them. A promised unit therefore cannot remain available to another customer inside the
recommendation, and after approval it leaves the planner's usable stock through the frozen field.

## 2. Ledger audit (`zaad/atp/economics.py`)

| P5 key | charged per | basis | owner | frozen reference |
|---|---|---|---|---|
| `lost_sales_opportunity` | unmet unit, refused unit | `Service.selling_price` unless a class / line margin is declared; the basis is reported per line (`drivers[line].lost_sale_basis`) | frozen settlement convention (`settle()`: `need * service.selling_price`) or P5 declaration | `zaad/full/settlement.py` |
| `sla` | unmet unit | `Service.sla_per_unmet` | frozen Service record | `settle()`: `need * service.sla_per_unmet`; `model.py`: `selling_price + sla_per_unmet` per unmet unit |
| `shortage_penalty` | unmet unit | `ServiceClass.shortage_penalty_per_unit` | P5 declaration (its own key; it was folded into `sla` in the isolated engine and is now separate so the two terms are visible side by side) | none (new) |
| `backorder_carry` | late unit x periods late | `ServiceClass.late_penalty_per_unit_period` | P5 declaration | none (new; the frozen ledger has no lateness) |
| `substitution` | substituted service-equivalent unit | `Substitute.penalty_per_output / service_equivalence` | frozen Substitute record | `compatible()` fee, `settle()`: `quantity * fee` |
| `alternative_ship_from` | physical unit shipped from an alternative location | `Transfer.cost_per_unit` on the approved lane | P2 lane record, priced only | `settle()` charges `transfer` for real movements; P5 uses a distinct key because no movement is created |
| `refusal` | refused unit | `ServiceClass.refusal_cost_per_unit` | P5 declaration | none (new) |

Double-count proof: each unit of a line ends in exactly one of {on time, late, substituted (on time
or late), unmet, refused} (`unit_states[line].balance_residual = 0`, invariant 3); `sla` and
`shortage_penalty` apply to unmet units only, `refusal` to refused units only,
`lost_sales_opportunity` to both (a refused sale is lost too); a substitute shipped late carries the
substitution fee and the lateness (two distinct declared outcomes on one unit, each charged once);
nothing is charged on a unit shipped on time from its own location. Ledger total equals the engine
objective (invariant 13, fixture I17).

Basis decision: the frozen ledger's key convention for a lost sale is the gross selling price
(`lost_sales_opportunity`), with the asset value of retained stock accounted separately through
`opening_assets` / `closing_assets`. P5 keeps the key convention and does not carry asset movements
(they belong to the planner's settlement ledger; the two ledgers are never summed). A declared
`lost_margin_per_unit` / `unit_margin` replaces the basis and is labelled as such. Unresolved
question, recorded for the release audit: whether the P5 comparison should net the retained unit's
asset value (the frozen net content) — it changes magnitudes only where all-or-nothing or
minimum-ship rules leave supply unshipped, never who is served first.

Terms P5 does not price, by ownership: holding, handling, financing, freight, procurement, disposal,
switching (planner ledger); demand forecasts (P0); purchase timing (P1); transfer decisions (P2);
source split (P3); conditional actions (P4).

## 3. Integration architecture

```
Request.atp (default None) ─────────────┐
                                        ▼
zaad/full/planner.plan()  ── frozen P0-P4 report complete ──▶ atp_block(req, atp, protection=P0 profile, planner_path=True) ──▶ report["atp"]
                                                                       │
api/routers/zaad_atp.py (standalone) ──────────────────────────────────┤  atp_block(req, atp)  (no planner, no overlay)
                                                                       ▼
                                              zaad/atp/integration.atp_block
                                                 build_state (envelope)  →  check_state (fail closed)  →  incumbent policy  →  exact MILP
                                                 →  price both on the P5 ledger  →  materiality (request's own fraction)  →  report
                                                 →  protection_overlay (planner path)  →  REFUSED block on AtpRefused (no crash of the plan)
```

* `zaad/full/planner.py`: one hook after the P4 block; `resolve_atp(req)` is None on a frozen
  request, so no P5 code is reached (I20, `test_disabled_path_is_frozen`,
  `test_disabled_path_reaches_no_p5_code_inside_the_planner`, the pre-P5 runtime comparison).
  `zaad/full/model.py`, the P3 rows, the P4 node indexing, scenario draws, tolerances: untouched.
* `/jobs` and `plan_network` call `plan()`, so the block travels with them.
* Workspace: `build_request(..., atp=True)` / `build_network_request(..., atp=True)` attach the
  vault's declared orders, classes and policy (migration 020 adapter) and report
  `build["atp"]`; both from-workspace endpoints take `atp=true`.
* API gating (`api/routers/zaad_full.py::atp_gate`): default off everywhere - a request with an
  enabled block answers 422 `atp_disabled` on `/plan`, `/jobs` and the from-workspace endpoints
  unless `ZAAD_ATP_ENABLED=1`; the interactive path enforces the P5 bounds (413); the standalone
  endpoint answers 404 when off. Operator mismatch is 403 before any work. Nothing is persisted.
* Purchase-plan / network-plan shapes carry `atp` and `executable_promise: false` when present.

## 4. What changed against the isolated engine (all logged in `P5_DEV_LOG.md`)

* state: firm / non-firm tiers replace confidence weighting; `inbound_confidence` != 1 refused;
  open POs reported as non-firm; envelope ladder reported;
* economics: `shortage_penalty` split out of `sla`; `transfer` renamed `alternative_ship_from`;
  `fulfilment` tag on every shipment; lost-sale basis labelled; owners reported;
* ties (documented, not economics): home location first among equal-cost direct channels; FEFO among
  cohorts (the frozen model's rule); indifference groups keyed on the declared numbers, never on the
  class id;
* report: reservations, envelope, non-firm availability, blocked supply, protection overlay, path.

# P5 — ATP / scarce-supply allocation / economic service classes: architecture

Status: parallel-phase design (TRACK B). Isolated implementation in `zaad/atp/`; no shared-core
integration until TRACK A (P4 performance closure) is merged and this branch is rebased.

## 1. Business question

When there is not enough inventory to fulfil every demand on time: who receives what, when is it
promised, and what does ZAAD defer, backorder, substitute, transfer-price or refuse? P5 owns
fulfilment allocation and promising. It does not own protection (P0), purchasing (P1), network
positioning and movement (P2), sourcing (P3) or conditionality (P4). See
`P5_EXISTING_CAPABILITIES.md` section 4 for the ownership table.

## 2. Principles

1. **Declared economics only.** Every priority driver is a declared, provenance-carrying number:
   contractual service floor, shortage penalty, late-delivery penalty, lost margin, minimum fill
   commitment, requested-date commitment, an operator-declared strategic flag, an operator-declared
   tier. Names, labels and inferred scores never rank a customer. `Customer.service_class` stays a
   reporting label.
2. **One ledger.** P5 prices allocation with the frozen `Service` economics (`selling_price`,
   `sla_per_unmet`) and the settlement ledger vocabulary; the only new keys are `backorder_carry`
   (declared late penalty x units x periods late) and `refusal` (declared refusal cost), each
   charged to a unit exactly once (section 8).
3. **No unit promised twice.** Reservations are explicit; conservation is a hard row per (SKU,
   location, period) on the ATP ladder.
4. **Time is real.** Supply has availability periods (on hand now, inbound POs by arrival period,
   inbound transfers by arrival period); orders have order and requested periods; a promise period
   is a decision constrained by both; lanes add lead time.
5. **Incumbent first.** The operator's promising rule is evaluated on the same state with the same
   economics; P5 recommends a change only above the request's own materiality standard, otherwise
   `NO MATERIAL ALLOCATION IMPROVEMENT AVAILABLE`.
6. **Default off, exact identity.** `Request.atp` absent or `enabled: false` reaches no P5 code;
   P0-P4 behaviour is bit-identical.
7. **Approval.** `approval_required: true`, nothing executes, no promise is sent anywhere.

## 3. Package layout (`zaad/atp/`)

| module | content |
|---|---|
| `contracts.py` | `ServiceClass`, `PromiseLine`, `CustomerOrder`, `AtpSpec` (the request-level declaration), `INTERACTIVE_LIMITS`, `resolve(req)` (None when absent / disabled), `validate_request(req)` |
| `state.py` | the supply ladder per (SKU, location, period): physical -> usable -> unreserved -> ATP -> CTP; built from the frozen `Request` (`stock`, `pipeline`, `inbound_transfers`, `sku_physics` / sector physics) |
| `economics.py` | the price of an allocation: on-time units, late units (backorder carry), substituted units, unmet units, refusals; reconciled to the settlement ledger keys; no double count |
| `policies.py` | incumbent comparators as deterministic allocators on the same state: `fifo_promise` (today's settlement rule), `fcfs_order_date`, `tier_priority`, `proportional`, `contractual_then_priority` (the standalone helper's rule), `declared_manual` |
| `allocation.py` | the exact optimiser: a small MILP over ship / backorder / substitute / unmet columns with conservation, time, eligibility, partial / minimum-ship / backorder rules, contractual floors; solved with scipy's bundled HiGHS (`scipy.optimize.milp`), never through `zaad/full/model.py` |
| `validation.py` | fail-closed checks (adversarial matrix) |
| `explain.py` | the operator report (section 10) |
| `fixtures.py` | the pre-registered fixture matrix A-V (`P5_PREREGISTRATION.md`) |
| `workspace.py` | vault adapter for migration 020 (declaration only) |

Scripts: `scripts/p5_benchmark.py`, `scripts/p5_invariants.py`, `scripts/p5_adversarial.py`.
Tests: `tests/unit/test_zaad_atp.py`, `tests/unit/test_zaad_atp_workspace.py`.

## 4. Data model

```
ServiceClass                       # declared economic / contractual class, per customer or per line
  id
  provenance: OPERATOR_DECLARED | CONTRACT | CONFIGURED_ASSUMPTION
  reference: str                   # contract id, policy id; required for CONTRACT
  contractual_service_floor: 0..1  # minimum fill of the class's accepted quantity (hard)
  shortage_penalty_per_unit >= 0   # charged per unmet unit in addition to the Service SLA? NO: it REPLACES
                                   # nothing - it is the class's declared penalty; the Service's
                                   # sla_per_unmet remains the stream-level term (section 8 for the rule)
  late_penalty_per_unit_period >= 0
  refusal_cost_per_unit >= 0
  lost_margin_per_unit: float | None   # when None the frozen Service economics apply
  strategic: bool                  # allowed only with provenance OPERATOR_DECLARED and a reference
  tier: str | None                 # declared label, used only for the tier_priority incumbent

PromiseLine
  id, sku, quantity > 0
  minimum_ship_quantity >= 0       # 0 = none; a shipment below it is not allowed
  requested_period >= 0            # relative to as_of (period index)
  ship_from: tuple[location, ...]  # eligibility; empty = the service's own location only
  unit_margin: float | None        # declared; None -> Service selling_price - Sku asset_value

CustomerOrder
  id, customer (must exist in req.customers), service_class (must exist)
  order_period <= 0                # when it was placed (0 = now)
  lines: tuple[PromiseLine, ...]
  partial_fulfillment_allowed: bool
  backorder_allowed: bool
  max_backorder_periods: int       # 0 = must ship at the requested period or not at all
  substitution_allowed: bool       # gated on top of the frozen Substitute approval
  late_semantics: ACCEPT_LATE | CANCEL_IF_LATE
  priority_provenance: OPERATOR_DECLARED | CONTRACT | CONFIGURED_ASSUMPTION

AtpSpec  (Request.atp, default None)
  enabled: bool = False
  orders, service_classes
  incumbent_policy: FIFO_PROMISE | FCFS_ORDER_DATE | TIER_PRIORITY | PROPORTIONAL | CONTRACTUAL_THEN_PRIORITY | DECLARED_MANUAL
  manual_sequence: tuple[order id, ...]     # required for DECLARED_MANUAL
  fairness: NONE | PROPORTIONAL_WHEN_INDIFFERENT
  include_inbound: bool            # CTP: count pipeline / in-flight transfers by arrival period
  inbound_confidence: 0..1         # declared; inbound counts at confidence x quantity (assumption, reported)
  promise_horizon: int             # periods over which a backorder may be promised
  cross_location: bool             # allow eligible alternative ship-from (priced with P2 lane data)
  provenance
```

Existing records reused unchanged: `Customer`, `Service`, `Substitute`, `Stock`, `Location`,
`Transfer`, `Pipeline`, `InboundTransfer`, sector physics.

## 5. ATP semantics (state.py)

Per (SKU, location, period t in 0..promise_horizon):

* physical(t): on-hand cohorts + arrivals scheduled by t (pipeline POs, in-flight transfers);
* usable(t): physical minus damaged and quarantined, minus cohorts not sellable at t under sector
  physics (remaining life, storage state at the location);
* unreserved(t): usable minus `Stock.reserved`;
* ATP(t): cumulative unreserved supply through t minus units promised at or before t (the
  optimiser's own reservations) — on-hand supply only when `include_inbound` is false;
* CTP(t): ATP(t) plus inbound arrivals by t weighted by the declared `inbound_confidence`
  (reported as an assumption); with `cross_location`, eligible alternative locations contribute at
  their lane lead (arrival t = ship period + lead) and lane cost, priced, not moved.

A unit arriving at period a is promisable only for promise periods >= a. Conservation:
Σ_lines ship[line, sku, loc, t'] for t' <= t <= supply(sku, loc, t) for every t (cumulative rows).

## 6. Decision variables and rules (allocation.py)

ship[line, supplied sku, location, t] >= 0 (t in order_period..promise_horizon); for each line
Σ ship + unmet[line] = quantity (a substitute counts in service-equivalent units through the frozen
`Substitute` ratio). Rules:

* partial forbidden: a binary full[line]; ship total in {0, quantity};
* minimum ship quantity: ship total = 0 or >= minimum (binary);
* backorder forbidden: ship only at t <= requested period (+ 0); allowed: t <= requested +
  max_backorder_periods; CANCEL_IF_LATE turns late units into refusals;
* contractual floor: Σ shipped over the class >= floor x Σ accepted quantity (hard; infeasible
  floors -> `INFEASIBLE_CONTRACTUAL_FLOORS`, no recommendation, same as the standalone helper);
* substitution: only rules approved for the customer and channel, only when the order allows it;
* location eligibility, lane eligibility (sector), sellability at t.

Objective (minimise): unmet x (lost margin + Service SLA + class shortage penalty) + late units x
periods late x late penalty + substitution penalty + lane cost for alternative ship-from +
refusal cost; plus deterministic tie terms of 1e-6 x (requested period, order period, line rank)
so equal-cost allocations resolve the same way on every run (documented tie-breaking; the
`PROPORTIONAL_WHEN_INDIFFERENT` fairness option replaces the lexical tie among economically
indifferent lines with pro-rata shares).

The MILP is small (lines x locations x periods) and solved to optimality with scipy's HiGHS; a
time-limited solve returns `FEASIBLE_TIME_LIMIT` and is never labelled optimal.

## 7. Incumbent policies (policies.py)

Deterministic greedy allocators on the same ladder, so every comparator is priced identically:
`FIFO_PROMISE` (earliest promised / requested period, then id — the settlement rule today),
`FCFS_ORDER_DATE`, `TIER_PRIORITY` (`Customer.priority` desc, then margin desc, then id),
`PROPORTIONAL` (pro-rata on scarce (sku, location, period) supply), `CONTRACTUAL_THEN_PRIORITY`
(contractual floors first, then priority / margin groups pro-rata — `zaad/allocation.py`'s rule),
`DECLARED_MANUAL` (the operator's sequence). Each honours the order's own partial / backorder /
substitution rules; none uses names.

## 8. Economics and the shared ledger (economics.py)

A unit of a line ends in exactly one state: shipped on time; shipped late (backordered); shipped as
a substitute (on time or late); unmet (lost); refused (CANCEL_IF_LATE, or an explicit refusal).
Charges:

| state | ledger key | amount |
|---|---|---|
| unmet | `lost_sales_opportunity` | lost margin (declared, else Service selling_price - Sku asset_value) |
| unmet | `sla` | Service `sla_per_unmet` + class `shortage_penalty_per_unit` |
| late | `backorder_carry` (new) | periods late x class `late_penalty_per_unit_period` |
| substitute | `substitution` | frozen `Substitute.penalty_per_output` per service-equivalent unit |
| alternative ship-from | `transfer` | P2 lane `cost_per_unit` (priced only) |
| refused | `refusal` (new) | class `refusal_cost_per_unit` |

Nothing is charged twice: a late unit is not unmet; a substituted unit is not unmet; margin is not
charged on a shipped unit. Reconciliation invariant: Σ over unit states = Σ requested quantity, and
the ledger total equals the objective value.

## 9. Materiality and abstention

`value_of_allocation = incumbent_cost - optimised_cost` on the same state and economics. Material
only above `req.materiality_cost_fraction x |incumbent_cost|` (the request's own standard, no P5
threshold). Not material -> `NO MATERIAL ALLOCATION IMPROVEMENT AVAILABLE`, the incumbent
allocation is the recommendation. Engineering evidence only; never savings, never annualised.

## 10. Operator report (explain.py)

`report["atp"]`: promised (line, quantity, period, ship-from), shipped now (period 0), backordered
(quantity, promise period, periods late, driver), substituted (rule id), unfulfilled (quantity,
driver), refused; per pair "why A before B": the declared driver that separates them (contractual
floor, shortage penalty, late penalty, lost margin, declared strategic flag, requested period), in
numbers; remaining inventory and reserved supply per (SKU, location, period); when the remaining
demand can be promised (first period with ATP/CTP); assumptions (inbound confidence, cross-location
pricing, sellability rules); `approval_required: true`, `executable_promise: false`. No aggregate
priority score appears anywhere.

## 11. Interfaces to other phases (defined, not threaded)

* **P2**: `state.alternative_supply(sku, destination)` reads approved lanes (lead, cost, capacity,
  storage state) for pricing an alternative ship-from; P5 emits `fulfilment_alternatives` (priced
  requests), never a transfer action. Joint optimisation of movement and promising is a later
  shared-core decision.
* **P4**: a P5 promise is a here-and-now action today. The future interface is a
  `promise[line, ..., node]` column indexed by the P4 information-set node for periods at or after a
  review epoch, with the same non-anticipativity by construction; the interface is documented in
  `P5_DEV_LOG.md` and NOT implemented during the parallel phase.
* **P0-P3**: read-only inputs (usable stock, pipeline arrivals, sources for substitution ratios).

## 12. Persistence and API

Migration 020 (additive, idempotent, nullable): `stg_customer_orders`, `stg_service_classes`
(declaration rows); no backfill; absent tables or no rows -> nothing attached. Adapter
`zaad/atp/workspace.py`. API: `Request.atp` (default None) and an isolated router
`api/routers/zaad_atp.py` with `POST /api/zaad/atp/promise` behind the same authentication, the
same 422 / 413 discipline (`atp_invalid`, `INTERACTIVE_LIMITS`: orders <= 200, lines <= 500,
promise horizon <= 26) and `approval_required: true`. The endpoint runs the isolated engine on the
request state; it does not call the planner. The from-workspace endpoints gain an `atp` flag only
at shared-core integration.

## 13. Fixture matrix, invariants, adversarial

Pre-registered in `P5_PREREGISTRATION.md` (A-V, 20 invariants, 16 adversarial cases) before the
engine is tuned.

## 14. What is intentionally not built now

Threading promises through P4 nodes; joint P2 movement + promising; substitution beyond the
declared `Substitute` contract (no lifecycle / supersession, P10); expedite options; capable-to-
promise on unconfirmed supplier capacity; any change to `zaad/full/model.py`, `zaad/full/planner.py`
candidate orchestration, the P3 shared-order rows or the P4 node indexing.

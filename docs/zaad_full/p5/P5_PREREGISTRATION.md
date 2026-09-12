# P5 — pre-registration: fixture matrix, invariants, adversarial matrix

Registered before the isolated engine was tuned (parallel phase, TRACK B). Fixture definitions
are frozen at registration; a fixture that turns out mis-specified is corrected with a dated note
in `P5_DEV_LOG.md` and re-registered, never adjusted after seeing a result it was meant to test.
Every fixture runs the isolated engine on a synthetic state built from the frozen `Request`
records (customers, services, stock, pipeline, inbound transfers, substitutions, physics) plus a
P5 declaration; economics come from the frozen `Service` records and the declared service
classes. Results are ENGINEERING EVIDENCE ONLY.

## Fixture matrix (principle per fixture)

| id | case | state | declaration | principle (pass condition) |
|---|---|---|---|---|
| A | enough inventory for everyone | supply >= total demand at every period | default classes | every line promised in full at its requested period; optimised allocation identical to the incumbent's; verdict `NO MATERIAL ALLOCATION IMPROVEMENT AVAILABLE` |
| B | true scarcity | supply 60 % of demand at period 0, no inbound | two classes with different shortage penalties | allocation required; the higher-penalty class is filled first; total shipped = supply; unmet = demand - supply; ledger reconciles |
| C | high contractual penalty vs high margin | class X: penalty 40 / margin 5; class Y: penalty 0 / margin 30; one scarce SKU | | the engine fills the higher total driver (penalty + margin) first and the report names the driver in numbers; `PROPORTIONAL` incumbent loses value |
| D | partial fulfilment allowed | scarce, 3 lines all partial-allowed | | every line receives a share; no line forced to zero by an all-or-nothing rule |
| E | partial fulfilment forbidden | same supply, partial forbidden on 2 lines | | those lines ship 0 or in full; total shipped <= supply; a forbidden line never ships a fraction |
| F | backorder allowed | supply now 50 %, inbound at period 2, backorders allowed 3 periods | `include_inbound` true | the balance is promised at period 2 as backorder with `backorder_carry` = late units x 2 x penalty; nothing is unmet |
| G | backorder forbidden | same state, backorders forbidden | | the balance is unmet (or refused under CANCEL_IF_LATE); no promise later than the requested period |
| H | different requested dates | line a requests period 0, line b period 3; supply arrives at 0 and 3 | | each line promised at its own requested period; no unit promised earlier than its arrival |
| I | future inbound available before promise date | inbound PO due at period 1, request at period 2 | `include_inbound` true, confidence 1 | the inbound counts (CTP); the line is promised at period 2 in full |
| J | future inbound too late | inbound due at period 4, request at period 2, backorders forbidden | | the inbound does not count for that line; unmet; the report says when the remaining demand can be promised (period 4) |
| K | multiple locations | stock at L1 (short) and L2 (surplus); line eligible from both | `cross_location` true | the shortfall is priced from L2 with the lane cost and lead; no transfer action is emitted; ledger `transfer` = units x lane cost |
| L | transfer lead interaction | L2 lane lead 2 periods, request at period 0, backorders allowed 1 period | | L2 units cannot be promised before period 2 -> unmet or refused for the period-0 demand; with `max_backorder_periods` 2 they are promised at period 2 |
| M | produce remaining-life constraint | cohort expiring in 1 period; request at period 2; physics `min_sale` 1 | PRODUCE physics | the near-expiry cohort is not promisable at period 2; ATP excludes it; unmet unless another cohort |
| N | meat / seafood cold-chain constraint | chilled SKU; location L2 has no chilled storage state; lane L2->L1 not chilled | MEAT_SEAFOOD physics | no unit is promised from L2; the report states the physics reason |
| O | customer-specific service floors | class with `contractual_service_floor` 0.8; scarce | | the floor is met exactly or the case is `INFEASIBLE_CONTRACTUAL_FLOORS` (no recommendation); other lines take the residual |
| P | economically indifferent customers | two lines, same class, same margin, same dates; supply 50 % | fairness NONE vs PROPORTIONAL_WHEN_INDIFFERENT | NONE: the documented lexical tie (order period, then id) fills one line; PROPORTIONAL: 50 / 50; both deterministic across 3 runs; costs equal |
| Q | already-optimal incumbent | scarce; the incumbent `TIER_PRIORITY` sequence equals the economic order | | value 0 within tolerance; verdict `NO MATERIAL ALLOCATION IMPROVEMENT AVAILABLE`; the recommendation IS the incumbent allocation |
| R | one strategic-account declaration | class `strategic` true with OPERATOR_DECLARED provenance and a reference | | the strategic line is filled first only through its declared shortage penalty / floor (the flag alone changes nothing without economics); the report cites the reference |
| S | malformed priority provenance | `strategic` true with provenance CONFIGURED_ASSUMPTION and no reference | | refused at the contract (422 `atp_invalid`); no allocation |
| T | attempted double reservation | two lines whose sum exceeds supply, plus `Stock.reserved` already covering part | | Σ promised <= unreserved supply; the reserved units are never promised; invariant 1 holds |
| U | substitution interface | requested SKU short; an approved `Substitute` for the customer and channel; order allows substitution | | the substitute is promised in service-equivalent units with the frozen ratio and penalty; an unapproved rule or a non-allowing order never substitutes |
| V | mixed commercial + perishables | two SKUs (commercial, produce) in one order; produce cohort near expiry | mixed physics | each line obeys its own physics; the order-level metrics reconcile; approval true |

## Invariants (release-level, every fixture)

1. no unit allocated twice: Σ ship over lines <= supply per (SKU, location, cumulative period);
2. allocation <= physical usable supply (never damaged, quarantined, unsellable or reserved units);
3. reservation conservation: Σ over unit states (on time + late + substituted + unmet + refused) =
   requested quantity for every line;
4. promise period physically feasible: >= order period, >= arrival period of the units used,
   >= ship period + lane lead for an alternative location;
5. location feasibility: ship-from in the line's eligibility set and physics `location_ok`;
6. lane lead respected (K, L);
7. customer minimums respected when accepted: shipped total = 0 or >= minimum_ship_quantity;
8. partial-fill rule respected: forbidden -> shipped total in {0, quantity};
9. backorder rule respected: forbidden -> no promise later than the requested period;
   allowed -> promise <= requested + max_backorder_periods;
10. service-class provenance valid: strategic only with OPERATOR_DECLARED + reference;
11. no negative allocation;
12. sector life / state rules preserved (M, N): every promised cohort sellable at the promise period;
13. shared economic ledger reconciles: objective = Σ ledger keys; the keys are the settlement
    vocabulary plus `backorder_carry` / `refusal`; no unit charged twice;
14. no source-decision ownership leakage: the P5 result contains no purchase / source field;
15. no purchase-decision ownership leakage: total supply is never increased by P5;
16. no future-information leakage: inbound counts only by its declared arrival period and declared
    confidence; nothing observed after `as_of` enters the state;
17. deterministic ties: three runs of every fixture give identical allocations;
18. approval required: `approval_required` true, `executable_promise` false on every report;
19. incumbent-first materiality: the recommendation is the incumbent allocation unless the value
    exceeds `materiality_cost_fraction x |incumbent cost|`;
20. P5 disabled path exact identity: a request without `atp` (or `enabled: false`) produces a
    planner report byte-identical (timing / hash stripped) to the frozen one, and `resolve()` is None.

## Adversarial matrix (fail closed)

| case | expected |
|---|---|
| duplicate customer order id | REFUSED_AT_CONTRACT |
| negative demand (line quantity) | REFUSED_AT_CONTRACT |
| impossible requested date (before the order period, or beyond the promise horizon) | REFUSED_AT_CONTRACT |
| unknown SKU | REFUSED_AT_CONTRACT |
| unknown customer | REFUSED_AT_CONTRACT |
| unknown location in ship-from | REFUSED_AT_CONTRACT |
| invalid priority class (order references an undeclared class) | REFUSED_AT_CONTRACT |
| undeclared strategic flag (strategic without OPERATOR_DECLARED provenance / reference) | REFUSED_AT_CONTRACT |
| conflicting service policies (DECLARED_MANUAL without a sequence; a sequence naming an unknown order; floor > 1) | REFUSED_AT_CONTRACT |
| double reservation attempt (reserved > quantity on a stock record) | REFUSED_AT_CONTRACT (frozen Stock validator) or STRUCTURALLY_IMPOSSIBLE (engine never promises reserved units) |
| expired produce | STRUCTURALLY_IMPOSSIBLE (not in ATP) |
| cold-chain invalid shipment | STRUCTURALLY_IMPOSSIBLE (location / lane not eligible) |
| substitution not approved | STRUCTURALLY_IMPOSSIBLE (no column exists) |
| huge order count (resource abuse) | REFUSED_AT_BOUNDS (413 above `INTERACTIVE_LIMITS`) |
| malformed economics (negative penalty, NaN margin) | REFUSED_AT_CONTRACT |
| cross-tenant order reference (customer of another operator / operator mismatch) | REFUSED_AT_CONTRACT / 403 at the API |

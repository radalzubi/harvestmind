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

## Shared-core integration fixtures (registered 2026-09-12, before the integrated engine ran them)

Every fixture below runs the integrated engine (`zaad/atp/integration.atp_block`) on the frozen
request records; I01 and I20 run through the planner (`zaad/full/planner.plan`), I19 through the
API. Pass conditions are fixed here; corrections, if any, are logged in `P5_DEV_LOG.md`.

| id | brief item | state | pass condition |
|---|---|---|---|
| I01 | P0 protection + P5 scarcity (planner path) | the released P2 network request, orders for the base's own customers exceeding on-hand stock at north and south | the frozen plan (every key but `atp`) is identical with and without the P5 block; `protection_overlay` carries one row per served (SKU, location) with `hard_reservation` false, `promised_from_on_hand` = the on-hand allocatable stock and `below_protection_units` = the P0 `protection_units`; every promise draws only from the allocatable envelope |
| I02 | P2 network stock + direct ship-from | stock north 30 / central 200; one line at north 80 eligible from north AND central; `cross_location` off | 30 promised from north + 50 from central, every shipment `fulfilment` DIRECT, `alternative_ship_from` ledger 0, `p2_transfers_created` 0, nothing unmet |
| I03 | attempted implicit transfer rejected | same stock; line eligible from north only; (a) `cross_location` off, (b) on with the central -> north lane unapproved | (a) and (b): 30 promised from north, 50 unmet, no shipment from central, `blocked_supply` names the central lot with a "no implicit transfer" reason, `p2_transfers_created` 0 |
| I04 | perishable FEFO allocation | PRODUCE physics; north cohorts old (60, expires in 3) and new (100, expires in 8); line 100 at period 0 | the old cohort is drawn in full before the new one (60 + 40); a cohort unsellable at the promise period is never drawn |
| I05 | cold-chain eligibility | MEAT_SEAFOOD chilled SKU; north 40, central 200; the central -> north lane AMBIENT-only; `cross_location` on; line at north 100 requested at period 1 | only north's 40 promised, no shipment on the lane, `blocked_supply` names the central lot with a storage-state (sector physics) reason |
| I06 | existing reservation exclusion | stock 100 with `Stock.reserved` 60; two lines of 30 | the envelope row shows reserved 60 and `allocatable_atp` 40; Σ promised = 40; the reserved units never appear in a reservation |
| I07 | order-bound reservation conservation | stock 70; three lines 50 / 30 / 20 | every reservation names exactly one (customer, order, line, SKU, lot, location, promise period) and carries status PROPOSED; ids unique; Σ reservations per lot <= lot quantity; per line Σ reservations + unmet + refused = quantity |
| I08 | confirmed inbound versus uncertain inbound | stock 0; firm in-flight transfer 40 due at period 1; open purchase order 60 expected at period 2; line 100 requested at period 2; `include_inbound` on | 40 promised at period 2 from the firm transfer; 60 unmet; `non_firm_availability` lists the purchase order with `promised` 0; `next_promise` points at non-firm supply only; a request declaring `inbound_confidence` 0.8 is refused at the contract |
| I09 | partial shipment | stock 50; one line 80, partial allowed | 50 promised, 30 unmet, unit states balance |
| I10 | minimum-ship constraint | line 80 with `minimum_ship_quantity` 60; (a) stock 50, (b) stock 65 | (a) nothing promised, 80 unmet; (b) 65 promised |
| I11 | backorder allowed | stock 50; firm transfer 50 due at 2; line 100, backorders allowed 3 periods, late penalty 1 | 50 on time + 50 at period 2 as backorder; `backorder_carry` = 50 x 2 x 1; nothing unmet |
| I12 | backorder prohibited | same state, backorders forbidden | 50 on time, 50 unmet, no promise later than the requested period |
| I13 | substitution allowed | A 20 / B 100 at north; approved `Substitute` A_by_B (penalty .5); order allows substitution; line 60 | 20 A + 40 B (service-equivalent) promised, `substitution` ledger 20, nothing unmet |
| I14 | substitution prohibited | same state, order forbids substitution | 20 A promised, 40 unmet, no substitute shipped |
| I15 | two service classes with identical economics -> identical treatment | classes `gold` and `silver` with identical numbers (different names, tiers); two lines of 50; supply 50; fairness PROPORTIONAL_WHEN_INDIFFERENT | 25 / 25; swapping the class ids between the orders gives the same per-line allocation; with fairness NONE the documented tie (order period, then line id) decides, again independent of the names |
| I16 | declared economic priority changing allocation | I15 with `shortage_penalty_per_unit` 20 declared on one class | that class's line is filled first (50 / 0); the report's `why` cites "shortage penalty per unit 20.00 against 0.00" |
| I17 | economic-ledger reconciliation | one request with an on-time, a late, a substituted, an alternative-ship-from, an unmet and a refused unit state | every ledger key present with an owner; ledger total = optimised cost (1e-6); per line Σ unit states = quantity; `sla` = unmet x Service SLA only, `shortage_penalty` = unmet x class penalty, `refusal` only on refused units, `lost_sales_opportunity` = (unmet + refused) x lost-sale basis; incumbent ledger reconciles the same way |
| I18 | incumbent wins | scarce; the TIER_PRIORITY incumbent equals the economic order | verdict `NO MATERIAL ALLOCATION IMPROVEMENT AVAILABLE`, value 0 within tolerance, the recommendation IS the incumbent allocation |
| I19 | tenant mismatch fail-closed (API) | a request of operator A with an enabled block | `/api/zaad/network/plan` and `/api/zaad/atp/promise` as operator B -> 403; with `ZAAD_ATP_ENABLED` unset the planner path answers 422 `atp_disabled` and the standalone endpoint 404; nothing is planned or promised |
| I20 | P5 disabled -> exact pre-P5 behaviour | the released P2 request without `atp`, and with `atp.enabled` false | `plan()` reports identical to each other and to the report of the pre-P5 runtime `6b58764` (timing and hashes stripped), no `atp` key, `resolve()` None |

Invariants 1-19 are checked on every I fixture that produces a recommendation; 20 is I20.

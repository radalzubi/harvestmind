# P5 — existing-capability audit (before any P5 code)

Scope: what the frozen ZAAD stack (main `adf45e4`, runtime `8c813ac`) already carries for
allocation, available-to-promise, order promising, customer priority, service classes, backorders,
reservations, customer orders, partial fulfilment, substitutions, fulfilment dates, shortage
penalties, margin, strategic accounts, fairness and customer SLAs; and what P5 must therefore NOT
duplicate. Sources: `zaad/full/contracts.py`, `zaad/full/model.py`, `zaad/full/settlement.py`,
`zaad/allocation.py`, `zaad/engine.py` (legacy), `zaad/sectors/contracts.py`, the industry roadmap
(`docs/zaad_full/OPTIMIZER_PRODUCT_STRATEGY_AND_INDUSTRY_ROADMAP.md`, sections 3.4 and P5) and the
phase closeouts (P0-P4).

## 1. What exists

| concept | where | what it is today | P5 consequence |
|---|---|---|---|
| customer | `Customer(id, channel, priority > 0, service_class: str | None)` | a declared priority weight (used by the model's service ordering) and an optional contract-class LABEL for reporting only ("targets stay on the Service record; the class never sets them") | P5 reuses `Customer`; the label stays a label; any differentiation must come from declared economics (section 19 of the brief), never from the label or the name |
| service (demand stream) | `Service(id, sku, location, customer, target, selling_price, sla_per_unmet, metric)` | one demand stream per (customer, SKU, location) with a service TARGET, a selling price (lost-sale opportunity), an SLA penalty per unmet unit and a metric (`unit_fill`, `line_fill`, `order_fill`, `otif`, `order_otif`) | the economic drivers of shortage already live here: P5 must price allocation with THESE numbers (no second ledger) |
| customer order lines | `OrderLine(id, order_id, service, quantity, due_in, ordered_at, requested_at, promised_at, delivered_at, filled, cancelled, revision, superseded_by)` with `open_quantity`, `line_chain` | dated order lines with requested and promised dates, partial fill (`filled`), cancellation and revision chains; consumed by the order-level metrics of the model (`line_full`, `line_units`, `order_full` binaries) and by settlement (`order_metrics`: line fill, order fill, OTIF, order OTIF, partial and late lines) | P5's `CustomerOrder` / `OrderLine` must EXTEND this record (ship-from eligibility, minimum ship quantity, partial / backorder / substitution flags, economics provenance), not replace it |
| allocation inside the frozen model | `allocate[sku, service, expiry, t, w]` columns, `unmet[service, t, w]`, `depleted` (no hoarding while demand is lost), `fefo` (older cohorts first), `priority[high, low, sku, t, w]` (a higher-ranked service's unmet forces lower-ranked services to zero on shared stock), `direct_first` (own SKU before a substitute) | the optimizer already allocates stock across services per period and world; the ranking is `(-customer.priority, -(selling_price - asset_value), service id)` — a declared priority then margin, ties by id | P5 does not re-implement per-period allocation; it introduces ORDER-level promising (dates, partial rules, backorders, reservations) that the stream-level model lacks, and later feeds the model's ranking with auditable economic classes |
| settlement allocation | `settle()` distributes served units to open lines in `(promised_at, id)` order (earliest promise first) and computes the order metrics | this IS the current incumbent promising rule: first-promised-first-served on the served quantity | P5's incumbent comparators start here (FIFO by promise date) |
| substitution | `Substitute(id, supplied_sku, requested_sku, customers, channels, input_per_output, penalty_per_output, service_equivalence, approved, brand_approval_reference, cannibalization_assumption)`; `compatible(req, service)` | declared, approved, customer- and channel-eligible substitution with a conversion ratio and a penalty, honoured by the model and priced in the ledger (`substitution`) | P5 reuses this contract verbatim for the substitution interface; no semantic inference, no new mapping |
| shortage economics | settlement ledger keys: `lost_sales_opportunity`, `sla`, `substitution`, `holding`, `handling`, `disposal`, `freight`, `transfer`, `procurement`, `financing`, `ordering`, `order_fees`, `switching`, `receiving`, `working_capital`, `opening_assets`, `closing_assets`; model costs `selling_price + sla_per_unmet` per unmet unit | one shared ledger; lost sale and SLA penalty are distinct keys; margin foregone is `selling_price - asset_value` inside the ranking | P5 penalties (late delivery, backorder carrying, partial-fulfilment) must map onto these keys or be added as NEW keys to the same ledger with an explicit no-double-count rule (section 24 of the brief) |
| physical vs reserved inventory | `Stock(quantity, reserved, damaged, quarantined, expires_in, age_periods)` | reserved stock is declared on the stock record; the model plans on usable stock | P5's ATP ladder starts from these fields (physical -> usable -> unreserved -> ATP) |
| sector physics | `Physics.sellable(sku, expiry, t)`, `location_ok`, `lane_ok`, `state`, `receipt_life`, `min_sale` | remaining-life at sale, cold-chain state eligibility per location and lane | P5 promises only stock that is sellable at the promise period and only from eligible locations / lanes; it never re-implements these rules |
| network | `Transfer(lead_periods, capacity, cost, loss, approved, multiple, fixed_cost_per_dispatch, storage_states)`, P2 router and accounting | where inventory sits and moves is P2's | P5 may PRICE fulfilment from an alternative location using P2's lane data; it may not move stock itself (section 23) |
| standalone helper | `zaad/allocation.py::allocate(available, lines)` with `CustomerLine(id, quantity, contractual_minimum, priority, unit_margin)` | contractual minima first, then priority / margin groups pro-rata; `INFEASIBLE_MINIMA` when minima exceed supply; explicitly "not yet an order-line OTIF optimizer or part of product-total simulation"; used by one acceptance test | this is the seed of P5's contractual-floor and proportional-tie rules; P5 supersedes it with a dated, multi-location, reservation-aware engine and keeps the helper's behaviour as the `contractual_then_priority` incumbent policy |
| legacy engine | `zaad/engine.py` "greedy capacity allocation" / "supplier_allocation" | supplier-side capacity allocation (P3's domain), not customer allocation | not P5 |
| vault | `stg_fmcg_orders` (customer demand history rows), `stg_fmcg_inventory`, `stg_fmcg_suppliers`, … (migration 013-019) | order history feeds the forecast and the `OrderLine` records of the frozen request | P5 persistence adds an additive customer-order / promising declaration table; it never rewrites `stg_fmcg_orders` |

## 2. What does not exist

* available-to-promise / capable-to-promise as a first-class quantity (physical -> usable ->
  unreserved -> ATP, with dates);
* reservations that bind a unit to one order (the model's `allocate` columns are per period and world,
  not per order; settlement distributes served units to lines after the fact);
* promise-date decisions (the `promised_at` on a line is an INPUT today; nothing chooses it);
* backorder semantics (an unmet unit is lost or penalised at the period; it is never carried as an
  open obligation to a later period);
* partial-fulfilment and minimum-ship rules per order;
* explicit economic service classes with provenance (penalty, margin, contractual floor, declared
  strategic flag) — `Customer.priority` is one opaque number, `service_class` a label;
* fairness / proportional rules stated as declared policy (the standalone helper has pro-rata ties,
  the model has id ties);
* an incumbent allocation policy as a comparator (the model's ranking is the only policy);
* an operator report answering "who got what and why".

## 3. What P5 must therefore do and not do

Do: build an ORDER-level promising layer (`zaad/atp/`) on the existing `Customer`, `Service`,
`OrderLine`, `Substitute`, `Stock`, `Transfer`, `Physics` records and the settlement ledger; add only
the missing concepts (ATP ladder, reservations, promise dates, backorders, partial rules, economic
class provenance, incumbent policies, report); keep the frozen model's per-period allocation exactly
as it is until the shared-core integration after TRACK A closes.

Do not: create a second customer / order / substitution contract; create a second shortage ledger;
touch `zaad/full/model.py`, the P4 node indexing, the P3 shared-order rows or the candidate
orchestration during the parallel phase; infer importance from names or labels; produce an opaque
priority score.

## 4. Ownership boundaries (which phase decides what)

| decision | owner | P5 role |
|---|---|---|
| how much protection to carry | P0 | consumes the resulting usable stock |
| how much to purchase, when | P1 | none (P5 never emits a purchase) |
| where inventory sits, transfer feasibility and economics | P2 | may price an alternative ship-from with P2's lane data; never moves stock |
| which supplier / source decomposition | P3 | none |
| which future decisions may adapt to observed information | P4 | later: P5 promises become node-indexed decisions; the interface is defined here, not threaded |
| who receives scarce available supply, what is promised and when, what is backordered / deferred / substituted / refused | **P5** | the whole decision |
| physical life, storage state, lane eligibility | sector physics | P5 only reads |

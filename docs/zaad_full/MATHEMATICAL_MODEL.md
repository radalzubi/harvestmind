# Mathematical contract — network v2

Authoritative implementation: `zaad/full/model.py`; independent evaluator:
`settlement.py`. One currency, declared base units, volume per SKU, periods of
`period_days`. The initial graph and every financial coefficient must be known
at the origin. Source quotes are operator-approved contiguous node itineraries.

## Decision variables

`x[r,t] >= 0`: external order by supplier/SKU/destination/route option.
`T[a,e,t] >= 0`: transfer on arc a of expiry cohort e.
`q[p,o] >= 0`: open PO quantity assigned to a permitted contractual option o.
These are **shared across scenarios**. No 0/50/100 source-mix restriction.

Scenario recourse: `I[k,l,e,t,w]`, fulfilled service-equivalent units
`F[k,service,e,t,w]`, unmet demand `u[service,t,w]`, cash and outstanding debt.
Demand is lost sales, not a fabricated backlog. Only period-zero choices are
eligible for human review; subsequent reviews receive new state and forecasts.

## Conservation and operational constraints

For each usable expiry cohort (e>t):

`I_t = I_(t-1) + fill[r,t-L,w]*x[r,t-L] + PO_receipts + inbound_transfers
       + transfer_arrivals*(1-loss) - transfer_departures - sum(conversion*F)`.

Expiry removes the entire remaining cohort at e, with the declared disposal
fee. Transfers preserve expiry and cannot arrive after it. Inventory has no
free disposal or creation slack. Arrivals enter once. Existing pipeline is
already expected-accepted; new fills apply to ordered quantities once.

`sum(F) + u = demand`. Approved substitution ratios include declared service
equivalence; incompatible customer/channel mappings are absent. Complementarity
binaries prohibit compatible remaining stock while demand is lost. Additional
constraints enforce FEFO, customer priority, then direct-before-substitution.
The independent evaluator uses the same priority order and work-conserving FEFO.

All route and shared-resource capacities bind simultaneously. Each required
pack/case/pallet/transport multiple gets its own integer variable. MOQ activates
with a binary; mutually exclusive all-unit quote tiers share an activation cap.
Quotes expire at the feasible calendar order date. Storage capacity is checked
before service and at end of period, including reserved/damaged/quarantined stock.

`sum_o q[p,o] = outstanding[p]`. Options have explicit quantity caps, deadlines,
shipment-stage permission, fees, remaining invoice and payment date. If splitting
is prohibited, exactly one option carries the whole open quantity. The planner
cannot cancel shipped supply unless a supplied contract explicitly permits it.

## Economics

`economic_cost = opening_stock_asset + opening_PO_prepaid_asset
 + new_and_remaining_contract_procurement + freight + handling + order_fees
 + transfer + substitution + cancellation/reschedule fees + financing
 + holding + disposal + SLA + lost_sales_opportunity - terminal_assets`.

Terminal stock/pipeline uses an explicit nonnegative value no greater than base
asset value; expiry at the boundary has zero terminal value. New invoices are
charged regardless of payment timing. Purchasing is paid on ordered units in v2,
unlike v1's accepted-unit assumption. Contract-specific invoice adjustments must
be entered as updated PO options, not silently assumed refunds.

Lost-sales opportunity uses selling price because consumed asset/procurement
cost already changes with actual fulfillment. Equivalently it differs from
negative realized operating profit by the fixed potential-sales constant. Do
not add lost contribution again or treat working-capital release as profit.
Every evaluator output reports each component and an exact sum reconciliation.

## Service and risk

Ordinary service floors constrain scenario-weighted unit fill by service group.
Robust candidates additionally require each declared scenario's unit-fill floor.
Line/order/OTIF constraints need actual declared outstanding lines and use binary
completion indicators; OTIF here is **line-level**, not inferred from totals.

An infeasible requested-service solve remains INFEASIBLE. A separate recovery
solve first maximizes priority-weighted service, then minimizes economic cost
at that optimum. It is labelled recovery, not a relaxed passing plan. Individual
service-frontier solves are separate upper bounds under the mean world and are
not simultaneously achievable promises or real-world guarantees.

CVaR90 uses `eta + sum(p_w*positive(cost_w-eta))/.1`; the objective adds a declared
weight to expected cost. Stress scenarios vary fill, lead, recovery, demand and
shared failures. Independent confirmation uses new draws; adverse confirmation
changes the model assumptions themselves and reports failed cells.

## Important limits

Invoices outside the modeled cash horizon remain outstanding, not cash-feasibility
guarantees for later dates. Sparse order-line allocation under conflicts needs
further adversarial operational reconciliation. Replay uses a shrinking supplied
horizon rather than inventing future capacity/receivables; production calls can
supply a new full horizon each review. No claim of optimal multistage recourse,
fitted causal disruption effects or calibrated rare-event service is made.

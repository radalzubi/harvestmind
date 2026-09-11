# ZAAD bounded decision-search mathematics

Authoritative for `zaad/`, separate from the legacy formulations in `docs/MATH_SPEC.md`. Units: quantity in declared item base units; item volume converts physical capacity; time in request.period_days; money in one request currency.

## Policy and information

At review t, forecast mean μ_j and scale σ_j use pre-origin history only. For a candidate route mix and modeled lead L, coverage H_j=L+1 review. Buffer candidate z∈{0,1,2,3}:

`target_j = μ_j H_j + z σ_j sqrt(H_j)`.

The incumbent uses `μ_j(H_j + incumbent_cover_j)` instead. Required expected receipt is

`g_j = max(0, target_j − usable_stock_j − Σ pending_expected_j,due≤t+Hj)`.

Requested route quantity is pack-rounded `g_route / expected_fill_route`, subject to MOQ if positive. Primary/alternate shares are0/.5/1, then remaining shortfall spills only into real spare capacities. Item ordering priority is criticality×unit margin. There is no claim of a global min-cost-flow optimum.

`Σ routes_on_edge x_route × item_volume ≤ edge_capacity`;
`x_route ≤ route_capacity`;
`Σ landed_quote_route x_route ≤ review_budget`;
`usable+reserved+damaged+all_booked_pending+new_booked quantities`, volume converted, does not exceed warehouse bound. A quote must be valid at that future simulated review. Illegal/unavailable/unapproved routes have zero eligibility, never expensive-but-allowed penalties.

## Common settlement

Before period demand is revealed: receive due actual shipments, expire lots, form publicly visible stock/pipeline, decide orders. Current-period realized demand and future actual fills/leads cannot enter the first action. New realized accepted arrival is `x_route,t × realized_fill_route,t` at `t+realized_lead`. Booked pipeline is already delivered-equivalent and is not haircut twice. Unreceived overdue POs are provisionally due at next review; actual future receipt remains private.

FEFO service is work conserving: `served=min(usable_inventory, demand)`; unmet=`demand−served`; next inventory=`usable_inventory−served`. No policy can hoard inventory through fictitious unmet demand to satisfy later floors. Opening due-now POs are normalized identically in emitted and simulated first actions.

## Economic identity

`consumed_asset_cost = opening_stock_and_pipeline_assets + accepted_purchase_base − closing_stock_assets − closing_actual_pending_assets`.

`economic_cost = consumed_asset_cost + paid_landed_premium + holding + disposal_fee + lost_sales_revenue`.

Lost sales are valued at full selling price in this identity because served base COGS already changes with actual fulfillment. Adding lost contribution again would double count. With a fixed demand path, minimize this cost equivalently maximizes sales less consumed goods and operating expense up to the constant potential sales revenue. Expired stock leaves the asset balance and disposal adds only disposal fee. Base cost is a lower bound on every landed quote. Premiums are not salvaged at terminal time. Accepted-quantity payment and terminal base-value recovery are assumptions; contract deposits, salvage discounts, future expiry and unpaid receivables need extension.

CFO reports inventory release separately from horizon carry-cost improvement; no automatic annualization or revenue percentage. The book-cash order bound is not the same as realized invoice timing. Absolute real-operator cost needs source reconciliation before gainshare billing.

## Search and gate

Candidate unit fill for j is `Σ_s,t served_jst / Σ_s,t demand_jst`. Every requested SKU floor and physical bound must hold on selection draws. All-zero demand is a feasibility sentinel, explicitly not measured service. Pick minimum mean economic cost among feasible candidates. A second independent seed evaluates candidate and incumbent on identical worlds;300 paired bootstrap resamples estimate a one-sided90% modeled-benefit lower bound. Require that bound>0, per-SKU expected service, no physical breach and worst sampled regret≤5% of selection incumbent mean cost. Otherwise retain incumbent; no feasible candidate→ABSTAIN. The force-unit-fill control always abstains.

This gate is conditional on assumed scenarios. Neither bootstrap nor a second Monte Carlo seed tests model misspecification, and neither implies calibrated real-world safety. Realized final service failures are reported, not reclassified as passing.

CVaR90 in benchmarks averages the worst ceil(0.1N) modeled costs of a finite policy. Small N makes it coarse; it is not a tail guarantee or a globally solved CVaR program. Final independently generated cases use five seeds, insufficient for reliable rare-event frequency estimation.

# ZAAD normal inventory engine

Implementation: `zaad/contracts.py`, `intake.py`, `forecast.py`, `engine.py`.

## Decision and inputs

One item ID represents a SKU at a location. Base units, volume per unit, packs, MOQ, shelf life, unit cost, selling price, carry cost, service target, criticality and operator incumbent cover are explicit. The graph verifies a contiguous supplier-to-location path. Inventory excludes reserved/damaged stock from usable quantity but retains it in physical storage occupancy. Versioned current POs preserve expected accepted quantity and due period; duplicate revisions are refused rather than summed. All operator records must have been known by the decision origin. Zero-demand history weeks must be explicit; gaps are not filled with fabricated demand.

This is a bounded snapshot adapter, not a complete ERP ledger. Payment terms, partial-receipt revision reconciliation, order-line commitments, pallet/weight constraints, shipment booking calendars, open-order censoring, inventory movements and automated source-unit conversion are not implemented.

## Forecasts earn selection by chronological scores

The existing boosting/quantile/conformal code remains intact. The new path compares moving average, EWMA, Croston-SBA and TSB; seasonal-naive is eligible with at least68 observations. Last12 training observations provide chronological WIS, 90th-quantile pinball, bias and empirical80% coverage for candidate selection. Those model-selection observations are not final holdout evidence. Residual-bootstrap scenarios use up to52 training periods. Intermittency candidates are actually exercised, but selection and interval calibration remain small-sample and no conformal guarantee is claimed. No ETS fit, pooled hierarchy, promotions input or structural-break model is added in this prototype.

## Physical candidate family

Incumbent is a competent fill-aware inventory-position rule: mean demand over expected lead + review + operator cover, less usable stock and timely expected pipeline, divided by expected accepted fill. Other candidates vary buffer multiples0/1/2/3 and primary/alternate mix0/.5/1. Each reorders weekly from its own actual stock and publicly expected pending book; current-period future demand is unavailable when ordering. Supplier/route/edge volume capacity, pack/MOQ, review cash and conservative warehouse booked-quantity bounds are common to every policy. Supplier-blind phantom allocation is not possible.

Available stock always serves demand, FEFO; the old target-only LP's voluntary withholding behavior is not inherited. Purchases arrive only after sampled lead and fill once. Quotes expire during projected reviews, and unavailable or legally uncleared paths cannot be used. Priority/margin order determines scarce procurement allocation; this is greedy and not a global multi-commodity optimum.

## Service, frontier and decision gate

Each candidate reports expected aggregate unit fill and per-SKU unit fill, inventory, cost/tail cost, physical/service feasibility and churn. The service target filters candidates; it is **not** a demand quantile or cycle-service label. Among feasible candidates the planner selects least modeled economic cost, then independent Monte Carlo confirmation checks benefit, per-SKU service, physical limits and worst regret. An infeasible family causes abstention, not floor relaxation. Only first-review actions are exposed, human approval remains mandatory.

The finite policy family is not a continuous global optimum. Simulator-internal weekly reordering uses a fixed selected rule with updated inventory/pipeline, not re-estimated forecast/method at every week. New real decisions require a fresh API call. Unit-fill feasibility sentinel1 on all-zero demand is explicitly not measured service. Line fill, order fill, OTIF and customer-level availability are not inferred from product totals.

## Economics and limits

Cost ledger and asset identity are defined in MATHEMATICAL_SPEC.md. Review cash is a booked-quantity upper bound, not an accounts-payable cash-flow plan. Supplier payment on accepted units is an assumption. Closing pending assets are valued at base cost; carrying premiums are not falsely salvaged. Future terminal expiry and payment-before-delivery terms need sensitivity tests. Storage is deliberately conservative: all booked pending quantities consume prospective capacity even if some will be sold before later arrivals.

The final holdout shows normal value is small and strong simple rules are competitive. Promotion/structural demand changes and intermittent demand produce negative cases. No parameters were tuned after observing them. See BENCHMARK_RESULTS.md and FAILURE_ANALYSIS.md.

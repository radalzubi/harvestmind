# Measured sparse scale probe

Actual local results on the corrected frozen engine (`evidence/final_v2/scalability.jsonl`):

| SKUs | Locations | Variables | Constraints | Total seconds | Status |
|---:|---:|---:|---:|---:|---|
|10|5|688|733|0.015|OPTIMAL|
|100|5|6,808|6,943|0.106|OPTIMAL|
|1,000|5|68,008|69,043|1.859|OPTIMAL|
|5,000|5|340,008|345,043|28.503|OPTIMAL|

One source/SKU, four periods, one deterministic scenario. The5,000-SKU process
peaked around1.51GB RSS on this Mac. Other local jobs were running, so timings
are indicative, not a reproducible hardware performance guarantee. This does
**not** prove interactive5,000-SKU stochastic planning with many sources,
substitution links, dense customer lines and12–52 periods.

The implementation constructs reachable SKU/location pairs and sparse constraints.
It does not split a shared cash or capacity pool into independently overcommitted
SKU subproblems. A commercial-scale scenario portfolio should be profiled on the
customer graph before choosing Benders, Lagrangian budgets or rolling partitions.
No Benders/DRO solver has been claimed merely because it appears in the roadmap.

Interactive API limits20SKUs/40sources/20service groups/12periods/4scenarios and
four stress envelopes, with an aggregate requested solver-time budget. Larger
snapshots use the offline CLI; an asynchronous operational batch queue is not
implemented on this v2 route. Optional commercial solvers require installed
binaries/licenses; missing solvers are refused, never silently substituted.

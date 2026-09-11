# Service, allocation and feasibility

Service groups explicitly bind SKU, location, customer and channel via the customer
record. Different groups can have different prices, SLA charges, targets and priority.
The same physical stock cannot fulfill two customers or substitutions simultaneously.

Current service uses customer priority, then contribution, then stable IDs, FEFO and
direct stock before approved substitutes. Conversion and service equivalence are
separate declared assumptions. Customer/brand/channel permission is mandatory.

Unit fill is measured from actual served/demand totals. Zero demand reports unobserved
service, not a measured100%. Declared order lines enable line/order completeness and
line-level OTIF at their requested/promise dates; aggregate SKU totals never create OTIF.
The current order metrics cover outstanding lines inside the horizon, not historical
whole-order completeness across arbitrary past/future deliveries.

An individual service frontier solves best achievable **modeled mean-world unit fill**
for each service group. These bounds compete for the same resources and are not jointly
achievable promises. Requested target minus its bound is a modeled unavoidable gap;
it is not a guarantee about an unknown future scenario. Separate lexicographic recovery
guidance exposes what can be done when full targets are impossible.

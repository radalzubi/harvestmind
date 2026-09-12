# P5 adversarial matrix (fail closed)

17 / 17 PASS

| case | outcome | result |
|---|---|---|
| duplicate customer order id | REFUSED_AT_CONTRACT: Value error, atp: duplicate customer order id [type=value_error, input_value={'enabled': T | PASS |
| negative demand | REFUSED_AT_CONTRACT: 1 validation error for PromiseLine | PASS |
| impossible requested date | REFUSED_AT_CONTRACT: Value error, atp: line l1 requests delivery beyond the promise horizon (impossible request | REFUSED_AT_CONTRACT: 1 val | PASS |
| unknown SKU | REFUSED_AT_CONTRACT: Value error, atp: line l1 names an unknown SKU ZZZ [type=value_error, input_value={'schema | PASS |
| unknown customer | REFUSED_AT_CONTRACT: Value error, atp: order o1 names an unknown customer nobody [type=value_error, input_value | PASS |
| unknown location | REFUSED_AT_CONTRACT: Value error, atp: line l1 names an unknown location mars [type=value_error, input_value={' | PASS |
| invalid priority class | REFUSED_AT_CONTRACT: Value error, atp: order o1 references an undeclared service class gold (invalid priority c | PASS |
| undeclared strategic flag | REFUSED_AT_CONTRACT: Value error, atp: a strategic flag needs OPERATOR_DECLARED provenance and a reference (und | PASS |
| conflicting service policies | REFUSED_AT_CONTRACT: Value error, atp: D | REFUSED_AT_CONTRACT: Value error, atp: m | REFUSED_AT_CONTRACT: 1 validation error  | REFUSED_AT_ | PASS |
| double reservation attempt | REFUSED_AT_CONTRACT: Value error, unusable quantities exceed | STRUCTURALLY_IMPOSSIBLE: 40.0 of 100 promised (60 reserved) | PASS |
| expired produce | STRUCTURALLY_IMPOSSIBLE: expired cohort never promised | PASS |
| cold-chain invalid shipment | REFUSED_AT_CONTRACT: Value error, stock lot_A_south_2: A (CHILLED) is  | STRUCTURALLY_IMPOSSIBLE: no shipment on an ineligible lane | PASS |
| substitution not approved | STRUCTURALLY_IMPOSSIBLE: no column for an unapproved rule | PASS |
| huge order count (resource abuse) | REFUSED_AT_BOUNDS: orders 201 over the interactive limit 200 | REFUSED_AT_CONTRACT: Value error, atp: order count beyond th | PASS |
| malformed economics | REFUSED_AT_CONTRACT: 1 validation e | REFUSED_AT_CONTRACT: 1 validation e | REFUSED_AT_CONTRACT: 1 validation e | PASS |
| cross-tenant order reference | REFUSED_AT_CONTRACT: Value error, atp: order o1 names an unknown customer op_other:customer_7 [type=value_error | PASS |
| probabilistic inbound (confidence factor) | REFUSED_AT_CONTRACT: Value error, atp: inbound_confidence must be 1: probabilistic inbound is never promised (o | PASS |

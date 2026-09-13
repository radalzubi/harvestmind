# P4B V1 adversarial matrix (fail closed)

16 / 16 PASS

| case | outcome | result |
|---|---|---|
| unknown action | REFUSED_AT_CONTRACT: 1 validation error for Request
pipeline.0.options.1.action
  Input should be 'keep', 'can | PASS |
| malformed stage | REFUSED_AT_CONTRACT: 1 validation error for Request
pipeline.0.stage
  Input should be 'placed', 'ordered', 'c | PASS |
| expired option | REFUSED_AT_CONTRACT: expired or stage-ineligible amendment | PASS |
| prohibited stage | REFUSED_AT_CONTRACT: expired or stage-ineligible amendment | PASS |
| negative fee | REFUSED_AT_CONTRACT: 1 validation error for Request
pipeline.0.options.1.fee_per_unit
  Input should be greate | PASS |
| negative credit | REFUSED_AT_CONTRACT: 1 validation error for Request
pipeline.0.options.1.credit_per_unit
  Input should be gre | PASS |
| excessive refund | REFUSED_AT_CONTRACT: 1 validation error for Request
pipeline.0
  Value error, commitments: option cancel credi | PASS |
| credit above paid / refundable amount | REFUSED_AT_CONTRACT: 1 validation error for Request
pipeline.0
  Value | REFUSED_AT_CONTRACT: 1 validation err | PASS |
| cancel quantity above remaining | REFUSED_AT_CONTRACT: amendment quantity outside contract | PASS |
| minimum remaining violation | REFUSED_AT_CONTRACT: 1 validation error for Request
pipeline.0
  Value error, commitments: cancel option cance | PASS |
| split when split prohibited | REFUSED_AT_CONTRACT: PO amendment conservation or exclusivity | PASS |
| unknown PO in declarations | REFUSED_AT_CONTRACT: commitments: declared options for open orders the workspace does not carry: ['ghost'] | PASS |
| cross-tenant declaration | IGNORED: another tenant's declaration attaches nothing (KEEP-only) | PASS |
| missing provenance (assumption) | REFUSED_AT_CONTRACT: 1 validation error for Request
pipeline.0.options.1
  Value error, commitments: option ca | PASS |
| declared keep row | REFUSED_AT_CONTRACT: commitments: option k of order po1 declares keep; the keep option is built from the order | PASS |
| option without deadline | REFUSED_AT_CONTRACT: commitments: option c declares no deadline (an amendment right needs its window) | PASS |

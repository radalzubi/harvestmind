# P4 adversarial cases

**25 / 25 fail safely**

| case | outcome | result |
|---|---|---|
| review period outside horizon | REFUSED_AT_CONTRACT | PASS |
| duplicate review epoch | REFUSED_AT_CONTRACT | PASS |
| review at period zero | REFUSED_AT_CONTRACT | PASS |
| unsupported observable | REFUSED_AT_CONTRACT | PASS |
| illegal adaptive action | REFUSED_AT_CONTRACT | PASS |
| invalid information tolerance | REFUSED_AT_CONTRACT | PASS |
| more epochs than supported | REFUSED_AT_CONTRACT | PASS |
| recourse enabled without structure | REFUSED_AT_CONTRACT | PASS |
| future-information leak into a signature | STRUCTURALLY_IMPOSSIBLE | PASS |
| scenario reorder | INVARIANT_HOLDS | PASS |
| duplicate scenario | INVARIANT_HOLDS | PASS |
| tiny probability scenario | INVARIANT_HOLDS | PASS |
| zero-probability scenario | REFUSED_AT_MODEL | PASS |
| near-tolerance observable values | DETERMINISTIC_QUANTISATION | PASS |
| supplier failure known too early | STRUCTURALLY_IMPOSSIBLE | PASS |
| transfer arrival before lead time | STRUCTURALLY_IMPOSSIBLE | PASS |
| committed purchase cancelled by a branch | STRUCTURALLY_IMPOSSIBLE | PASS |
| source capacity exceeded after adaptation | INVARIANT_HOLDS | PASS |
| MOV counted per line instead of per shared order | INVARIANT_HOLDS | PASS |
| perishable lot treated as fresh after review | INVARIANT_HOLDS | PASS |
| cold-chain state reset | INVARIANT_HOLDS | PASS |
| adaptive cheaper only through double counting | INVARIANT_HOLDS | PASS |
| perfect-information plan surfaced as executable | REPORT_ONLY | PASS |
| policy lookup leaking the future | STRUCTURALLY_IMPOSSIBLE | PASS |
| disabled block reaches a hook | FROZEN_PATH | PASS |

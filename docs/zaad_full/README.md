# ZAAD network optimizer v2

This work replaces the bounded policy menu **on the new v2 path** with actual
continuous / mixed-integer network optimization. Legacy v1 remains compatible;
its frozen evidence is untouched. Start with [implementation status](IMPLEMENTATION_STATUS.md),
[mathematics](MATHEMATICAL_MODEL.md), and [results](BENCHMARK_RESULTS.md).

**Not autonomous. Not Oracle parity. Not customer-validated.** An approval is a
prospective shadow review of period-zero actions, never a transmitted PO.

Release verdict: **NEEDS FURTHER ENGINEERING**, with exact financial-tail,
service/robustness, order-line reconciliation, large-job and inherited security
blockers in [failure analysis](FAILURE_ANALYSIS.md). The working architecture is
substantive; the complete enterprise specification is not claimed finished.

```bash
python3 scripts/zaad_network.py --fixture transfer --output /tmp/zaad-transfer.json
python3 scripts/zaad_network.py --templates --output /tmp/zaad-templates
python3 -m pytest tests/unit/test_zaad_full_model.py tests/unit/test_zaad_full_controls.py -q
```

UI: `/zaad/network`. API: `/api/zaad/network/schema`, `/fixture`, `/plan`,
`/shadow`, `/shadow/{id}/review`, `/shadow/{id}/outcome`. Persistent routes
require an operator token even in development. Set `ZAAD_SHADOW_LEDGER` to a
dedicated protected SQLite file outside all training databases.

The final evidence uses new seeds, an exact source/configuration fingerprint,
and the 85-cell **coverage matrix**, not the much larger full Cartesian matrix.
`--matrix full` generates all 7,560 normal combinations plus stress/action cells;
that exhaustive experiment must not be confused with the executed coverage run.
Accepted final artifacts live in `evidence/final_v2/`. Earlier attempts are
retained and labelled; do not substitute their results for the corrected final.

Every action needs explicit costs, capacities, timing and operator permissions.
Supplier/route IDs refer to the supplied source catalogue; alternate routes,
substitutions and cancellation rights are never invented by the engine.

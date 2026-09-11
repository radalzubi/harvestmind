# Addendum (2026-09-11, P3 phase): replay materialisation now honours age at receipt

Found while building the P3 sourcing benchmark. The rolling replay (`zaad/full/replay.py`) turned a
received purchase order into opening stock with the SKU's full shelf life, whatever age at receipt the
declared sector physics gave arrivals from that source. The planner, the settlement and the model
already used `physics.receipt_life(sku, source)`; only the truth side of the benchmark harness did not.

Effect on this record: fixture **P3_age_at_receipt** was scored on a truth in which the "old" import
source delivered fresh goods. The P3 phase corrected the replay (a materialised receipt carries
`physics.receipt_life` on a physics request; legacy requests keep the full shelf life, so every
P0 / P1 / P2 record is unaffected) and re-ran this matrix under the P3 code (`sector_under_p3`):
26 / 26 fixtures still pass; 402 / 416 ZAAD reviews are decision-identical to `sector_authoritative`;
the 14 differing reviews are all on P3_age_at_receipt (both seeds), where ZAAD now plans against a truth
that matches its own physics. The authoritative sector record is not rewritten; this addendum and
`sector_under_p3.*` / `sector_under_p3_compare.json` are the correction.

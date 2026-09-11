# Corrective sector record (2026-09-11): age at receipt in the rolling replay

Status of the historical markers: `sector-physics-frozen-product` = `43d769f`, `sector-physics-frozen` =
`4f358f7`, `sector-physics-release-runtime` = `5ca3772` are immutable and not moved. The authoritative
sector record (`sector_authoritative.*`, 26 / 26, 19 / 19) is not rewritten; this dated record explains
the one correction found after it. Code audit: `AGE_AT_RECEIPT_REPLAY_AUDIT.md`.

## 1. What was wrong

The frozen and released sector implementation (`43d769f`, `5ca3772`) contained a defect in the
**historical rolling replay** for explicit perishable age-at-receipt physics: when a purchase order
arrived during a replay, `zaad.full.replay.replay` turned it into opening stock with the SKU's full
nominal shelf life (`expires_in = sku.shelf_life`) instead of the remaining life the declared physics
gives an arrival from that source (`shelf_life - age_at_receipt`). Example: shelf life 6, age at
receipt 3 -> the truth handed the lot 6 periods instead of 3.

## 2. The boundary the audit found

The **live planner was already correct**: the model prices every purchase column with
`physics.receipt_life(sku, source)` (and makes a source below the receipt minimum ineligible), the
settlement receives pending purchases with the same life and refuses a source below the minimum, and
the network rule projection uses the same rule. None of those lines changed. The defect lived only on
the truth side of the benchmark harness, between one review's executed purchase and the next review's
opening stock. It did not "reset" live inventory in a production plan; it made historical evaluation
credit an old-arriving source with freshness the physics denied, and every downstream cohort (transfers,
FEFO, expiry, sellable service, terminal value) of such a lot inherited the wrong life.

## 3. Why P3 exposed it

P3 compares sources. Its fixture S1 (a cheap produce source declared to arrive with 3 of 8 periods)
lost 8 % to a rule buying the "old" source, whose lots reached the branches with life the physics
said they could not have. Receipt-life fidelity became economically material once two sources with
different ages competed; in the sector phase the age-at-receipt fixture had only ZAAD's own choices
to compare and the gate still passed.

## 4. The correction

Commit `33f96cc` (first commit in the P3 lineage containing it; product freeze `9e496ed` has the
identical runtime tree): a materialised receipt carries `physics.receipt_life(sku, source)` on a
physics request and `sku.shelf_life` on a legacy request. One function, one line of behaviour. No
optimizer, settlement or projection change.

## 5. Legacy and no-physics behaviour identical

* Legacy requests (no `sector_mode`, no `sku_physics`): `resolve` is None; the materialisation is
  bit-identical. P2 authoritative matrix under the corrected code: 344 / 344 ZAAD reviews
  decision-identical; P0 six-cell 120 / 120; canonical B / T / Q / A identity.
* Physics requests without a declared age (COMMERCIAL, MEAT_SEAFOOD, PRODUCE with age 0): `receipt_life
  = shelf_life`, identical; the neutral counterfactual below is 0 / 16 reviews different and the other
  25 sector fixtures are 402 / 402 identical in the sector re-run. Unit tests:
  `tests/unit/test_zaad_replay_receipt_life.py`.

## 6. The 14 / 416 reviews that changed, one by one

Fixture `P3_age_at_receipt` (sector PRODUCE, the only sector fixture declaring an age at receipt):
SKU A, nominal shelf life 6 periods, sale minimum 1, import source `src_A` declared age at receipt 3
(expected remaining life at receipt **3**), local sources `src_A_north` / `src_A_south` at a 20 % price
premium with age 0 (life 6). ZAAD policy `gated`, seeds 41001 and 41002, rolling reviews 0-7. Review 0
is identical on both seeds (no purchase order has yet been materialised); every review from 1 on differs
after the first import lands. "Lives" lists the remaining life of the observed (materialised) lots in the
review's planning snapshot: original replay **6** (full shelf life), corrected **3** for the import and 6
for the local sources.

| seed | review | screen state (old -> new) | executed purchases, original | executed purchases, corrected | old cost / served | new cost / served | demand | lives old | lives new |
|---|---|---|---|---|---|---|---|---|---|
| 41001 | 1 | NO_ACTION -> NO_ACTION | src_A 194.1, src_A_north 13.3 | src_A 195.5, src_A_south 13.4 | 1442 / 183.9 | 1445 / 183.9 | 183.9 | [6] | [3, 6] |
| 41001 | 2 | NO_ACTION -> NO_ACTION | src_A 180.7 | src_A 180.7, src_A_north 17.1 | 1663 / 220.3 | 1702 / 220.3 | 220.3 | [6] | [3, 6] |
| 41001 | 3 | NO_ACTION -> NO_ACTION | src_A 196.3, src_A_north 30.9 | src_A 203.1, src_A_north 21.5 | 2003 / 194.7 | 1727 / 228.4 | 229.3 | [6] | [3, 6] |
| 41001 | 4 | NO_ACTION -> NO_ACTION | src_A 191.6, src_A_south 25.5 | src_A 191.6, src_A_north 9.9, src_A_south 41.5 | 1572 / 205.9 | 1749 / 189.9 | 208.0 | [6] | [3, 6] |
| 41001 | 5 | NO_ACTION -> NORMAL_REPLENISHMENT | src_A 194.2, src_A_north 15.8 | src_A 204.0, src_A_north 1.4 | 1458 / 186.6 | 1460 / 186.6 | 186.6 | [6] | [3, 6] |
| 41001 | 6 | NO_ACTION -> NO_ACTION | src_A 182.0 | src_A 181.2 | 1468 / 200.1 | 1552 / 200.1 | 200.1 | [6] | [3, 6] |
| 41001 | 7 | NO_ACTION -> NO_ACTION | src_A 186.8, src_A_north 21.9 | src_A 177.4, src_A_north 17.1, src_A_south 22.6 | 1602 / 205.6 | 1728 / 210.7 | 210.7 | [6] | [3] |
| 41002 | 1 | NO_ACTION -> NO_ACTION | src_A 182.0, src_A_south 18.9 | src_A 182.0, src_A_north 19.8 | 1541 / 210.4 | 1542 / 210.4 | 210.4 | [6] | [3, 6] |
| 41002 | 2 | NO_ACTION -> NO_ACTION | src_A 195.8, src_A_north 6.9 | src_A 197.3, src_A_north 17.3 | 1483 / 195.0 | 1508 / 195.0 | 195.0 | [6] | [3, 6] |
| 41002 | 3 | NO_ACTION -> NO_ACTION | src_A 194.8, src_A_south 28.0 | src_A 183.7, src_A_south 36.0 | 1733 / 204.9 | 1747 / 205.2 | 216.7 | [6] | [3, 6] |
| 41002 | 4 | NO_ACTION -> NO_ACTION | src_A 192.0, src_A_north 16.9 | src_A 200.6, src_A_north 5.1 | 1565 / 216.1 | 1559 / 216.1 | 216.1 | [6] | [3, 6] |
| 41002 | 5 | NO_ACTION -> NO_ACTION | src_A_north 198.9, src_A_south 220.7 | src_A 184.3 | 2247 / 185.8 | 1631 / 185.5 | 203.7 | [6] | [3, 6] |
| 41002 | 6 | NO_ACTION -> NO_ACTION | none | src_A 175.6, src_A_north 19.3 | 1465 / 201.1 | 1487 / 201.1 | 201.1 | [6] | [3] |
| 41002 | 7 | NETWORK_ALLOCATION -> NO_ACTION | src_A 198.6, src_A_south 9.1 | src_A 199.6, src_A_north 11.2, src_A_south 21.4 | 1547 / 206.9 | 1633 / 202.2 | 206.9 | [] | [3, 6] |

Exactly these 14 (seed, review) pairs are the differing reviews of `sector_under_p3_compare.json`
(`sector_authoritative` against the P3 re-run: 416 compared, 402 identical, 14 differing) and of the
corrective re-run `sector_corrective` (see section 8). No other fixture, seed or review differs.
Mechanism common to all 14: the import lot in the planning snapshot carries 3 periods instead of 6, so
the FEFO / sellable position, the transfers the branches can still sell and the next lot's timing shift;
the screen state, the planner owner and the abstention are unchanged except where the position shift
moves the screen (41001 r5 NO_ACTION -> NORMAL_REPLENISHMENT, 41002 r7 NETWORK_ALLOCATION -> NO_ACTION).

## 7. Counterfactual (`counterfactual.py`, records `counterfactual_*.json`)

| variant | code line | differing reviews against the original code line | observed import lot life at review 1 |
|---|---|---|---|
| A: declared age 3, original replay (`5ca3772` runtime in `harvestmind-main`) | original | reference | 6 |
| B: declared age 3, corrected replay (`9e496ed`) | corrected | 7 of 8 on seed 41001, 7 of 8 on seed 41002 (reviews 1-7; the 14 above) | 3 |
| C: age set to neutral (0), corrected replay | corrected | **0 of 8 on both seeds** against A run with age 0 | 6 on both lines |

A and C align exactly when no receipt age is declared; B differs exactly when the declared non-zero age
changes the physical truth. The differences are therefore caused by the receipt-life truth correction,
not by P3 source-selection logic (the fixture declares no sourcing portfolio; `Request.sourcing` is
None on every run).

## 8. Sector authoritative regression on the product code (`sector_corrective`, gates/)

Complete sector suite (26 fixtures, seeds 41001 / 41002, eight reviews, the P2 policy set, six workers,
wall 8 min) on the P3 product runtime `9e496ed`: **26 / 26 fixtures PASS** (economic, service, structural
and principle gates); sector invariants **19 / 19**; by sector: COMMERCIAL p50 1.1 s / max 60.6 s (C1
frozen frontier oracle, the class the sector record profiled), PRODUCE 3.4 s / 30.0 s, MEAT_SEAFOOD
0.8 s / 4.3 s, MIXED 1.8 s / 3.7 s; 0 time-limited solves. Decision comparison against the authoritative
sector record (`sector_corrective_compare.json`): 416 compared, **402 identical, 14 differing**, exactly
the (seed, review) pairs of section 6 (reviews 1-7 on both seeds of P3_age_at_receipt) and none other.
The authoritative sector record (`sector_authoritative.*`) is preserved unchanged.

## 9. P0 / P1 / P2 isolation (gates/)

* P0 canonical regression: PASS (B / T / Q / A twelve-review identity, P0 cell 15 identity).
* P1 invariants: no failures.
* P2 authoritative matrix re-run (`p2_corrective`): 20 / 20 fixtures, 18 / 18 principles; decision
  comparison against the P2 release record: **344 / 344 identical** (`evidence/p2/p2_corrective_compare.json`;
  wall p50 0.78 s under contention with the sector and P3 matrices running alongside).
* P0 six-cell arm `p3_sourcing_corrective` (run alongside the two matrices): cells 15, 16, 20, 90, 108
  decision-identical to `router_cycle` (12 / 12, 12 / 12, 20 / 20, 26 / 26, 30 / 30); cell 21, the
  wall-clock-limited cell, 5 / 20 under contention, the run-to-run variability the P2 record documents
  for that cell. The same product runtime run alone earlier today (`p3_sourcing`,
  `evidence/p3/gates/p0_six_cell_p3_sourcing.log`) was 120 / 120. Cell 21 rerun alone on the quiet
  machine: see section 12.

## 10. P3 revalidation on the product code (gates/)

`p3_corrective`: **30 / 30 fixtures PASS**, no fixture changed; **34 / 34 invariants**; **23 / 23
adversarial**. Runtime 480 reviews p50 0.71 s / p95 20.8 s / max 46.2 s (reference 0.66 / 19.2 / 42.8 s;
run alongside the P0 arm), 0 time-limited, none over 60 s, none over 180 s.

## 11. Performance

No formulation change: the correction touches one dictionary value in the replay's materialisation. Sector
matrix p50 1.7 s / p95 11.0 s / max 60.6 s (record 1.4 / 8.4 / 59.5 s, same maximum class); P3 0.71 / 20.8 /
46.2 s (reference 0.66 / 19.2 / 42.8 s); P2 0.78 / 10.2 / 22.1 s (record 0.48 / 6.6 / 14.6 s) - every
increase is contention from the concurrent chains, no review above 60 s in P2 or P3, and the single
sector review above 60 s is the frozen C1 oracle already explained in the sector record. No review near
the 180 s blocker.

## 12. P0 cell 21 rerun alone (`gates/p0_cell21_rerun.log`)

Arm `p3_sourcing_corrective_rerun`, cell 21 alone on the quiet machine (133 s): **20 / 20
decision-identical** to `router_cycle` (cost 3331 -> 3331, service .760, unmet 93.0, starved 0). With the
five cells of the concurrent run, the product runtime is **120 / 120** P0-owned reviews decision-identical,
the same result as the earlier quiet run of the identical runtime.

## 13. Statement

1. The original sector freeze (`43d769f`, `4f358f7`) and the released runtime (`5ca3772`) remain immutable.
2. The frozen and released sector implementation contained a historical-replay defect for explicit
   perishable age-at-receipt physics (section 1).
3. The defect did not reset live inventory: the planner, the settlement and the projections already used
   the declared receipt life; only the truth side of the rolling replay materialised a received lot as
   fresh (section 2).
4. P3 exposed it because source comparisons made receipt-life fidelity economically material (section 3).
5. The correction preserves the declared remaining life on receipt; it is one line of behaviour in
   `zaad/full/replay.py`, first in commit `33f96cc`, present unchanged in the product freeze `9e496ed`
   (section 4; local marker `sector-physics-replay-correction` = `33f96cc`, the first commit in the P3
   lineage containing the correction; that commit also carries P3 benchmark and API changes and is not a
   standalone sector runtime).
6. Legacy and no-physics requests remain identical (section 5; neutral counterfactual 0 / 16; P2 344 / 344;
   P0 120 / 120; P1 identity and invariants).
7. 14 / 416 authoritative sector replay reviews changed, all on fixture P3_age_at_receipt, each listed
   with its cause (sections 6-7); the original 402 / 416 evidence is preserved, not hidden.
8. All authoritative sector fixtures (26 / 26) and invariants (19 / 19) remain PASS on the product code
   (section 8).
9. P0 / P1 / P2 remain unchanged (sections 9, 12).
10. This is a correctness correction of the evaluation harness, not P3 tuning: no fixture, tolerance,
    seed, optimizer economics or selector rule was changed to obtain it, and the P3 evidence (30 / 30,
    34 / 34, 23 / 23) stands on the corrected semantics (section 10).

Verdict: **SECTOR AGE-AT-RECEIPT REPLAY CORRECTION — VERIFIED.** P3 remains PASS AND FROZEN LOCALLY at
product `9e496ed` (runtime unchanged by this audit); this record and the tests are a corrective
evidence follow-up commit (`p3-corrective-evidence`), the P3 freeze tags are not moved. P3 is not
released; its release requires remote exhaustive CI capability restored (GitHub Actions billing-blocked
at the time of this audit: REMOTE_CI_UNAVAILABLE — GITHUB ACTIONS BILLING).

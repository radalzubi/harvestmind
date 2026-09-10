# P2 performance corrective plan (pre-registered before the authoritative re-run)

Date 2026-09-10. Branch `claude/zaad-meio-p2`. Written after the diagnosis
(`P2_PERF_DIAGNOSIS.md`) and the development measurements (`P2_PERF_LOG.md`) and BEFORE the
authoritative re-run it governs. Nothing below is changed after the re-run starts.

## What the corrective change is

One exact model change: the FEFO indicator between two cohorts that both outlive the window
(horizon and the latest schedulable transfer arrival of the SKU) is omitted on network requests
(`zaad/full/model.py`, `FEFO_SYMMETRY_ELIMINATION`). Equivalence argument and measurements: perf log
entry 1. No other lever is applied (entries 2-3 record what was evaluated and why it is not needed).

What is NOT changed: worlds (`network_scenarios`: 3 / 6 / 8), horizons, candidate classes, service
floors and their basis, MIP gap (1e-6; Q's declared 1e-4), the frozen budget rules (`solve_budget`,
`network_solve_seconds`), the warm-start policy, fixture economics, seeds, baselines, tolerances,
the validity rule, the scoring basis, the 20 fixtures, the 5 policies, 8 reviews (R: 20).

## Pre-registered re-run

* Command: `PYTHONPATH=. python3 -m scripts.p2_benchmark --tag p2_authoritative_perf --workers 4`
  (the fixture matrix, seeds, policies and review counts of `scripts/p2_fixtures.py` exactly as
  recorded for `p2_authoritative`; the `--scenarios` / `--max-solve` development overrides unused).
* Summary: `scripts/p2_final_table.py --base p2_authoritative_perf --corrected p2_authoritative_perf
  --replaced "" --out p2_final_perf` (the same `summarize` rules; no fixture replaced; the runtime
  gate read over every ZAAD review of the run).
* Runtime gate, unchanged from `P2_PREREGISTRATION.md`: ZAAD wall per review p50 <= 60 s, p95 <= 120
  s, **max <= 180 s**, no NO_FEASIBLE_SOLUTION on a required candidate. Performance target
  (the reason for the pass, not a gate): max < 180 s, p50 < 9.7 s, p95 < 86.9 s against the final
  record.
* Economic / service gates: identical to the pre-registration (every valid fixture must pass; 18 / 18
  principles). A fixture that passed before and fails now is a regression to be explained, not
  re-tuned.
* Decision comparison: `scripts/p2_decision_compare.py docs/zaad_full/evidence/p2/p2_final.jsonl
  docs/zaad_full/evidence/p2/p2_authoritative_perf.jsonl` over every policy, review by review
  (state, owner, status, abstention, executed purchases and transfers, settled cost, served units,
  candidate statuses). Expected and acceptable differences, stated now: (a) reviews whose frozen
  solve ended FEASIBLE_TIME_LIMIT (19 candidate solves in the final record, on D, M, O, Q) now reach
  a proven optimum, so their executed plan can differ - in ZAAD's favour or not, reported either
  way; (b) reviews after such a review inherit a different state; (c) exact ties re-labelled
  (cohort labels of transfers, guidance-period transfer timing at equal cost). Any difference on a
  review whose frozen candidates were all OPTIMAL and whose predecessors are identical is a finding
  to be explained candidate by candidate (objective equality is the test); an unexplained one blocks
  the freeze.
* Frozen behaviour: `scripts/zaad_canonical_regression.py` (P1 B, T, Q, A twelve-review identity;
  P0 cell 15) and the P0 six-cell arm `p2_perf` (`scripts/p1_p0_arms.py p2_perf`, compared with
  `router_cycle` by `scripts/p1_ownership_compare.py` under the frozen decision keys). Cells 21 and
  108 are the documented wall-clock-limited cells; a divergence there is compared at decision level
  and against the frozen code's own replay before it counts.
* Full engineering gate at the final SHA: pytest, the P2 tests, `scripts/p2_invariants.py`,
  `scripts/p2_adversarial.py`, ruff, mypy, bandit, `git diff --check`, the workspace smoke and the
  network workspace smoke, the API tests.

## Verdict rule

`P2 MULTI-ECHELON / NETWORK OPTIMIZATION - PASS AND FROZEN` only if every gate above passes on the
unchanged set; otherwise `P2 PERFORMANCE ENGINEERING COMPLETE - FREEZE BLOCKED` with the blocker
named. The 180 s maximum is not moved.

# P2 multi-echelon / network optimization: closeout

Branch `claude/zaad-meio-p2`, worktree `harvestmind-p2`, parent `11f5459` (canonical `main`). Frozen
tags unchanged: `p0-frozen` = `2e30721`, `p1-frozen-product` = `f7e1e62`, `p1-frozen` = `12db66c`.
Not merged, not pushed. P2 commits: `377e6b5` (network domain), `5e6bec2` (network continuation,
benchmark, fixtures), `c6ff177` (workspace adapter, API, invariants, adversarial, scalability),
`0f2d50e` (closure rules, scenario rule, pre-registration), `660b2f4` (Correction 1), `04fa28b`
(authoritative evidence), `6261d12` (first closeout: FREEZE BLOCKED), then the performance pass:
`cab3849` (perf: FEFO symmetry elimination), `a317f3c` (test: harness, snapshots, comparisons,
equivalence tests), `a0b1573` (docs: diagnosis, log, corrective plan, profiles) and the final
evidence commit carrying this closeout (tagged locally `p2-frozen`).

## Verdict

**P2 MULTI-ECHELON / NETWORK OPTIMIZATION — PASS AND FROZEN.** Frozen code SHA `cab3849`
(`zaad/full`, `zaad/meio`, `api`, `scripts` as of that commit; the later commits add tests and
evidence only). The freeze record is the commit that carries this file, tag `p2-frozen`.

### History of the runtime gate (preserved, not edited)

1. First closeout (`6261d12`, `P2_RESULTS.md` section 3): **ORIGINAL P2 RUNTIME GATE — FAILED**, M
   seed 41002 review 7 at 257 s and O seed 41001 review 6 at 315 s against the pre-registered 180 s
   maximum (p50 9.7 s, p95 86.9 s passed). Verdict then: P2 CORE ARCHITECTURE BUILT — FREEZE BLOCKED.
2. Performance pass (`perf/`): diagnosis before any change (`P2_PERF_DIAGNOSIS.md`), one exact model
   change measured per candidate (`P2_PERF_LOG.md`), a dated corrective plan pre-registering the
   re-run under the same 180 s gate (`P2_PERF_CORRECTIVE_PLAN.md`), the unchanged authoritative set
   re-run (`P2_PERF_RESULTS.md`): **p50 0.5 s, p95 6.6 s, max 14.6 s, PASS**.

The gate was not moved. No fixture, seed, world count, horizon, candidate class, service floor, MIP
gap, baseline or tolerance changed. No commercial solver.

## The change, in one paragraph

Profiling the two failing reviews on their exact snapshots showed 95% of the binaries were FEFO
indicators between cohorts that all expire 45-64 periods beyond a 12-period horizon (big-M 1e6): the
relaxation was so weak that HiGHS needed 10-31 s to find a first incumbent and the warm-start
completion forfeited its 30 s cap on every eight-world candidate (69% of the 250 s wall). Two such
cohorts are economically interchangeable, so the FEFO rule between them constrains only a label. The
model now builds the indicator against older cohorts inside the window only (horizon and the latest
schedulable transfer arrival of the SKU), on network requests; the single-node P1 formulation is
verbatim. Every candidate of every profiled review solves at the root node with identical objectives.

## Freeze gate (31 items) at the frozen SHA

| item | evidence | result |
|---|---|---|
| 1 inventory conservation | invariant 01 (`P2_INVARIANTS.md`, re-run at the frozen SHA); conservation residual <= 1e-12 on every review of `p2_authoritative_perf` | PASS |
| 2 no double counting | invariant 02 | PASS |
| 3 reachability | invariant 03; M | PASS |
| 4 lane capacity | invariant 07; P completes | PASS |
| 5 shared central inventory | invariant 09 | PASS |
| 6 shared supplier constraints | invariant 10 | PASS |
| 7 service per location | per-branch gates on every fixture (`p2_final_perf.tables.md`) | PASS |
| 8 principled allocation | invariant 17; G, J, K | PASS |
| 9 transfer economics | invariants 04-06; E, F, O | PASS |
| 10 no transfer loops | reverse-pair units 0 on every cell; invariant 19; free reverse pair refused (adversarial) | PASS |
| 11 no forced network action | L abstains 7.5 / 8; G, P 8 / 8; `already_perfect_incumbent` retains | PASS |
| 12 independent-demand pooling | invariant 13; A | PASS |
| 13 correlated demand invents nothing | invariant 14; B | PASS |
| 14 short / long lead | principle `long_lead_positions_more_locally`; invariant 06 | PASS |
| 15 already-efficient abstains | L | PASS |
| 16 all valid fixtures pass | 20 / 20 (`perf/P2_PERF_RESULTS.md`) | PASS |
| 17 P0 frozen behaviour | canonical regression identical (cell 15); six-cell arm `p2_perf` 120 / 120 reviews decision-identical to `router_cycle`, cells 21 and 108 included | PASS |
| 18 P1 frozen behaviour | B, T, Q, A twelve-review identity at the frozen SHA (`perf/gates/canonical_regression_v2.log`) | PASS |
| 19 runtime commercially plausible | **p50 0.5 s, p95 6.6 s, max 14.6 s against 60 / 120 / 180; 0 starvation; 0 time-limited solves** | **PASS** |
| 20 accounting reconciles | invariant 20; every cell | PASS |
| 21 API / workspace smoke | workspace smoke, network workspace smoke, API tests 9 passed (`perf/gates/engineering_gate_final.log`, `api_tests_final.log`) | PASS |
| 22 full tests | 1,843 passed, 2 skipped (`perf/gates/pytest_final.log`) | PASS |
| 23 static checks | ruff clean, mypy 136 files clean, bandit 0 medium / high, `git diff --check` clean | PASS |
| 24 clean tree | at the freeze commit | PASS |
| 25 no benchmark tuning | pre-registration and Correction 1 unchanged; corrective plan dated before the re-run; the change is a model reformulation, not a rule | PASS |
| 26-28 Validation7 / Validation8 / holdout4 | untouched | PASS |
| 29 Network Twin | PR #39 untouched | PASS |
| 30 sector physics | not started | PASS |
| 31 dashboard / website | not started | PASS |

## Performance evidence (summary; details in `perf/`)

1. Original failure preserved: `P2_RESULTS.md` section 3 and item 1 above, unedited.
2. Profiling method: exact snapshots (`scripts/p2_snapshots.py`), in-process instrumentation
   (`scripts/p2_profile_review.py`), deep HiGHS logs; quiet machine; source untouched for the baseline.
3. Portfolio: G r2 (0.8 s), A r7 (7.9 s), H r4 (77.5 s), M 41002 r7 (250.4 s, the failing review
   reproduced in state and time), O 41001 r6 (88.0 s; its CAPITAL_OPTIMIZATION variant is three of
   the same solve), plus Q r6 (77.7 s) and R r11 (61.1 s) for the pack / order mechanisms.
4. Per-candidate numbers (class, build, completion, solve, evaluation, variables / integers /
   binaries / rows / nonzeros, worlds, horizon, budget, status, objective, bound, gap, nodes, LP
   iterations, first / final incumbent, proof, presolve reductions, memory): `perf/profiles/*.json`.
5. Dominating mechanism: warm-start completion forfeiting its cap (69% of M's wall) on top of a
   weak relaxation from symmetric FEFO big-M indicators (95% of the binaries), multiplied by worlds
   and by requested classes. Not construction (1 s), settlement (0.1 s), memory (511 MB peak) or proof
   after the first incumbent.
6. HiGHS presolve raw -> reduced recorded per candidate (M stochastic: 13,761 x 13,631 -> 3,139 x
   3,054 with 807 binaries before; 10,175 columns -> 2,121 x 3,352 with 161 binaries after).
7. Exact structural presolve in Python: evaluated, not applied (HiGHS removes 70-78%; build is 0.8 s).
8. Bound tightening: evaluated; no data-derived bound below the 1e6 location capacity exists on
   these requests; node counts before / after recorded (315-2,536 -> 1-47).
9. Dominance / symmetry: the FEFO elimination (entry 1), with its equivalence argument and five tests.
10. Formulation strength (packs, dispatch): Q keeps its pack / dispatch flags; 14.6 s max; not changed.
11. Warm starts: first-incumbent times before / after recorded (M stochastic 10.3 s -> 0.1 s; O 27.4 s
    -> 0.1 s); the frozen policy is unchanged and no longer forfeits its cap.
12. Receding-horizon reuse / caching: not needed; not applied.
13. Candidate independence and parallel execution: analysed, not applied (no gate benefit; path
    changes on frozen cells).
14. HiGHS parameter portfolio: not applied for the same reason; recorded.
15. Time to decision against time to proof (M, O): equal before and after; no gap policy.
16. Model build: 0.8 s of 7.0 s on M after the change; not optimised.
17. Settlement / replay: 0.07 s per review; not optimised.
18. Decomposition: not needed.
19. Multi-SKU architecture note and async as a safety mechanism: `perf/P2_PERF_ARCHITECTURE_NOTE.md`.
20. Per-change development log with SHA, equivalence argument, dimensions, times, nodes, objective,
    decision identity, accepted / rejected: `perf/P2_PERF_LOG.md`; success target met (max 14.6 s <
    180 s; p50 0.5 s < 9.7 s; p95 6.6 s < 86.9 s).

## Frozen-file footprint

As in the first closeout (default-off or telemetry hooks, identity proved) plus `model.py`
`FEFO_SYMMETRY_ELIMINATION` (network requests only; single-node models column-for-column identical,
tested).

## Known limitations (recorded, not tuned)

* The executed transfer quantity on the P2 fixtures is not unique at the optimum (equal holding
  rates, zero cost of capital, per-unit lane cost): two exact formulations settle differently on the
  truth, in both directions, inside every tolerance. A product deployment that wants a unique
  executable transfer should declare the economics that break the tie (a holding differential or a
  cost of capital), not a solver preference.
* On a perishable network (shelf life inside the horizon plus lane lead) the FEFO rows return for the
  cohorts that can expire; the interactive caps bound that model, and the next exact levers are
  recorded in the architecture note.
* The long-lane world rule (six / eight worlds) and its budget rule stand as pre-registered; they
  now cost a few seconds per review.
* Correlation groups are SKUs; lane disruption is not represented in the worlds; the production
  topology built by the adapter is central -> branch.

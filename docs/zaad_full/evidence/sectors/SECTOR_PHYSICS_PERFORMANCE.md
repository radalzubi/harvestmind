# Three-sector physics: performance record

The P2 lesson applies: remove irrelevant structure before asking HiGHS to solve it. The physics adds
no binary variable; it removes allocation columns (unsellable cohorts) and caps eligibility. Perishable
SKUs bring in-window cohorts back, and with them the FEFO indicators the P2 symmetry elimination keeps
only where they are mathematically needed. Everything below is measured with the P2 profiling harness
(`scripts.sector_profile`, in-process instrumentation, HiGHS through scipy 1.17.1 / highspy 1.14.0 on
the 12-core machine of the P2 record).

## Baselines (before any sector change, same machine)

| review | wall | note |
|---|---|---|
| P2 A 41001 r7 | 0.3 s | three worlds, long-life commercial |
| P2 H 41001 r4 | 0.8 s | PROTECT review |
| P2 M 41002 r7 | 7.0 s | eight worlds, NETWORK_ALLOCATION |
| P2 O 41001 r6 | 0.7 s | six worlds |
| P2 Q 41002 r6 | 13.4 s | lane packs and dispatch fees |

## Authoritative sector run (416 ZAAD reviews)

| set | p50 | p95 | max | time-limited solves | over 60 s | over 180 s |
|---|---|---|---|---|---|---|
| all sectors | 1.4 s | 8.4 s | 59.5 s | 0 | 0 | 0 |
| COMMERCIAL | 0.8 s | - | 59.5 s (C1) | 0 | 0 | 0 |
| PRODUCE | 2.2 s | - | 20.9 s (P3) | 0 | 0 | 0 |
| MEAT_SEAFOOD | 0.7 s | - | 3.6 s | 0 | 0 | 0 |
| MIXED | 1.7 s | - | 3.5 s | 0 | 0 | 0 |

Legacy P2 matrix under the sector code: p50 0.5 s, p95 6.5 s, max 14.5 s (release record 0.5 / 6.6 /
14.6 s): no regression.

## Representative profiles (`profiles/*.json`)

| review | wall | dominant candidate | variables | binaries (of which FEFO) | rows | nodes | note |
|---|---|---|---|---|---|---|---|
| C1 41002 r6 (case packs, NO_ACTION) | 58.6 s | frozen service-frontier oracle phase 2, south: 42.9 s time-limited at the 43 s budget, 319 k nodes; north 13.7 s, 101 k nodes | 1,274 | 24 (0) + 12 general-integer `case` | 734 | - | decision candidates 1.2 s and 0.5 s; the oracle is report-only frozen P0 code exposed by integer purchase packs |
| C1 41001 r2 | 53.8 s | same mechanism | | | | | |
| P3 41002 r7 (age at receipt, NETWORK_ALLOCATION, 3 worlds) | 19.6 s | joint_recovery 11.7 s, 5,436 nodes | 4,347 | 1,040 (944) | 4,356 | | six candidates 1.1-2.2 s each |
| P4 41001 r5 (long south lane, 6 worlds) | 18.1 s | cvar_network 8.0 s, 1,223 nodes | 5,510 | 1,368 (1,224) | 5,765 | | four stochastic candidates 2-8 s |
| P6 41002 r1 (yield uncertainty, PROTECT) | 15.7 s | hedged completion 5.4 s; solves 1.1-2.5 s | 3,972 | 952 (856) | 4,016 | | |
| M6 41001 r0 (chilled, transfer of a lot) | 1.4 s | - | | | | | |
| X3 41001 r0 (three SKUs, three sectors) | 2.0 s | - | | | | | |

Reading: on a perishable with a six-period shelf life about four cohorts are alive at once, so the
FEFO indicators number (alive cohorts - 1) x services x periods x worlds, around 700-1,400 binaries
on these fixtures, and HiGHS proves every candidate at 20-5,400 nodes in 1-12 s. The per-review time
is the number of requested classes times that. No completion forfeits its cap (the P2 diagnosis's
mechanism does not recur: first incumbents arrive in under a second on every profiled candidate).

## The one review class above 60 s

C1 (case packs): 54-60 s on two reviews of 16, all in the frozen `service_frontier` oracles
(`solve(service_first=<service>)`; phase 2 minimises cost subject to the phase-1 optimum within
1e-7) with 12 general-integer `case` columns; 100-320 k nodes on a 1,274-column model. It is
report-only (never a decision candidate), P0 code frozen since `2e30721`, and is reached by any
request with integer purchase packs - the P2 fixture Q (lane packs) showed the same class of time.
Below the 180 s blocker; not changed (a frozen-code change; documented here as the explanation the
60 s rule requires).

## Model-build, settlement and memory

Build 0.1-0.3 s per review; settlement 0.05-0.1 s per review (evaluation of every candidate on every
world); peak RSS below 500 MB on every profiled review.

## Not applied

No HiGHS parameter change, no commercial solver, no time-limit increase, no world reduction, no
economics or service change to meet runtime.

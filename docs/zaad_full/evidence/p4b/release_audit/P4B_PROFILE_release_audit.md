# P4B V1 performance profile `release_audit/P4B_PROFILE_release_audit` (released model, stochastic candidate solve, demo request)

| cell | variables | binaries | constraints | build s | solve s | proof s | nodes | gap | status | peak RSS MB |
|---|---|---|---|---|---|---|---|---|---|---|
| no options | 504 | 145 | 540 | 0.001 | 0.015 | 0.015 | 1 | 0.0 | OPTIMAL | 116.7 |
| 1 PO, keep only x3 | 508 | 147 | 546 | 0.001 | 0.014 | 0.014 | 1 | 0.0 | OPTIMAL | 116.9 |
| 3 POs, cancel+defer+expedite, exclusive | 634 | 192 | 665 | 0.001 | 0.094 | 0.094 | 1 | 0.0 | OPTIMAL | 122.3 |
| 3 POs, cancel+defer+expedite, split | 622 | 180 | 650 | 0.001 | 0.027 | 0.027 | 1 | 0.0 | OPTIMAL | 122.5 |
| 10 POs, cancel+defer, exclusive | 616 | 192 | 641 | 0.001 | 0.204 | 0.204 | 1 | 0.0 | OPTIMAL | 126.3 |
| 30 POs, cancel+defer+expedite, exclusive | 850 | 300 | 828 | 0.002 | 0.674 | 0.674 | 122 | 0.0 | OPTIMAL | 134.3 |
| 30 POs, cancel+defer+expedite, split | 730 | 180 | 678 | 0.002 | 0.07 | 0.07 | 1 | 0.0 | OPTIMAL | 134.7 |

first incumbent: HiGHS through scipy reports no incumbent timeline; every cell is proved at the root or within the solve time shown (proof s = solve s when OPTIMAL).

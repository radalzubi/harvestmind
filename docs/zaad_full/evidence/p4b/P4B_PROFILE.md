# P4B V1 performance profile `P4B_PROFILE` (released model, stochastic candidate solve, demo request)

| cell | variables | binaries | constraints | build s | solve s | proof s | nodes | gap | status | peak RSS MB |
|---|---|---|---|---|---|---|---|---|---|---|
| no options | 504 | 145 | 540 | 0.001 | 0.015 | 0.015 | 1 | 0.0 | OPTIMAL | 117.2 |
| 1 PO, keep only x3 | 508 | 147 | 546 | 0.001 | 0.013 | 0.013 | 1 | 0.0 | OPTIMAL | 117.4 |
| 3 POs, cancel+defer+expedite, exclusive | 634 | 192 | 665 | 0.001 | 0.096 | 0.096 | 1 | 0.0 | OPTIMAL | 121.8 |
| 3 POs, cancel+defer+expedite, split | 622 | 180 | 650 | 0.001 | 0.027 | 0.027 | 1 | 0.0 | OPTIMAL | 122.0 |
| 10 POs, cancel+defer, exclusive | 616 | 192 | 641 | 0.001 | 0.206 | 0.206 | 1 | 0.0 | OPTIMAL | 126.0 |
| 30 POs, cancel+defer+expedite, exclusive | 850 | 300 | 828 | 0.002 | 0.687 | 0.687 | 122 | 0.0 | OPTIMAL | 134.1 |
| 30 POs, cancel+defer+expedite, split | 730 | 180 | 678 | 0.002 | 0.071 | 0.071 | 1 | 0.0 | OPTIMAL | 134.4 |

first incumbent: HiGHS through scipy reports no incumbent timeline; every cell is proved at the root or within the solve time shown (proof s = solve s when OPTIMAL).

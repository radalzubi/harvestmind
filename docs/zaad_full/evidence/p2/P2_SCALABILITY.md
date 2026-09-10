# P2 scalability diagnostic (1 central + N branches, H = 12, weekly)

| branches | locations | lanes | det vars / rows / s | stochastic (3 worlds) vars / rows / s / status | plan_network wall s / MILPs / state | max RSS MB |
|---|---|---|---|---|---|---|
| 2 | 3 | 2 | 1464 / 1260 / 0.0 | 3744 / 3678 / 1.1 / OPTIMAL | 9.4 / 4 / NO_ACTION | 217.0 |
| 5 | 6 | 5 | 3372 / 2808 / 0.1 | 8532 / 8244 / 6.6 / OPTIMAL | 11.8 / 4 / NO_ACTION | 290.0 |
| 8 | 9 | 8 | 5280 / 4356 / 0.1 | 13320 / 12810 / 32.5 / OPTIMAL | 68.3 / 4 / NO_ACTION | 409.0 |

# P5 performance profile `P5_PROFILE` (engine alone, scipy HiGHS)

| cell | rows | columns | binaries | channels | build s | solve s | first incumbent s | proof s | nodes | LP iterations | status | gap | promise wall s | peak RSS MB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5x1 lines, horizon 8, 1 location(s), firm inbound False | 9 | 21 | 1 | 15 | 0.0001 | 0.0073 | 0.0 | 0.01 | 1 | 2 | OPTIMAL | 0.0 | 0.006 | 117.0 |
| 20x2 lines, horizon 8, 1 location(s), firm inbound False | 60 | 171 | 11 | 120 | 0.0003 | 0.005 | 0.0 | 0.0 | 1 | 13 | OPTIMAL | 0.0 | 0.007 | 117.7 |
| 50x2 lines, horizon 8, 2 location(s), firm inbound True | 167 | 932 | 34 | 798 | 0.0012 | 0.0155 | 0.0 | 0.01 | 1 | 196 | OPTIMAL | 0.0 | 0.026 | 120.6 |
| 100x3 lines, horizon 12, 2 location(s), firm inbound True | 473 | 2815 | 109 | 2406 | 0.0043 | 0.0768 | 0.0 | 0.01 | 1 | 535 | OPTIMAL | 0.0 | 0.142 | 128.6 |
| 200x2 lines, horizon 26, 2 location(s), firm inbound True | 629 | 3751 | 149 | 3202 | 0.0108 | 0.1281 | 0.0 | 0.02 | 1 | 729 | OPTIMAL | 0.0 | 0.244 | 135.1 |
| 100x5 lines, horizon 26, 2 location(s), firm inbound True | 787 | 4709 | 189 | 4020 | 0.0073 | 0.1931 | 0.0 | 0.03 | 1 | 878 | OPTIMAL | 0.0 | 0.37 | 142.4 |

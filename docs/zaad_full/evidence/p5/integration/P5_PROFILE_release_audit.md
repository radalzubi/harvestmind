# P5 performance profile `P5_PROFILE_release_audit` (engine alone, scipy HiGHS)

| cell | rows | columns | binaries | channels | build s | solve s | first incumbent s | proof s | nodes | LP iterations | status | gap | promise wall s | peak RSS MB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5x1 lines, horizon 8, 1 location(s), firm inbound False | 9 | 21 | 1 | 15 | 0.0001 | 0.0021 | 0.0 | 0.0 | 1 | 2 | OPTIMAL | 0.0 | 0.002 | 115.2 |
| 20x2 lines, horizon 8, 1 location(s), firm inbound False | 60 | 171 | 11 | 120 | 0.0004 | 0.0048 | 0.0 | 0.0 | 1 | 13 | OPTIMAL | 0.0 | 0.007 | 116.0 |
| 50x2 lines, horizon 8, 2 location(s), firm inbound True | 167 | 932 | 34 | 798 | 0.0015 | 0.0159 | 0.0 | 0.01 | 1 | 190 | OPTIMAL | 0.0 | 0.028 | 119.1 |
| 100x3 lines, horizon 12, 2 location(s), firm inbound True | 473 | 2815 | 109 | 2406 | 0.005 | 0.0826 | 0.0 | 0.01 | 1 | 575 | OPTIMAL | 0.0 | 0.154 | 127.3 |
| 200x2 lines, horizon 26, 2 location(s), firm inbound True | 629 | 3751 | 149 | 3202 | 0.012 | 0.137 | 0.0 | 0.02 | 1 | 732 | OPTIMAL | 0.0 | 0.261 | 133.4 |
| 100x5 lines, horizon 26, 2 location(s), firm inbound True | 787 | 4709 | 189 | 4020 | 0.0087 | 0.2014 | 0.0 | 0.03 | 1 | 860 | OPTIMAL | 0.0 | 0.381 | 139.1 |

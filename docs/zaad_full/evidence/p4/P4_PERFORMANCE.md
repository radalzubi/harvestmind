# P4 performance matrix (release candidate, local Apple laptop, quiet machine; Fly shared-cpu-2x measured 4-5x slower unthrottled at the P3 closure)

Engineering matrix `scripts/p4_profile.py`: histories x review epochs x continuations x request class (single SKU, P2 network, two-source P3, shared-supplier-order P3, representative PRODUCE sector request). `compare wall` = static + adaptive + perfect-information solves on the tree; `planner wall` = the whole `plan()` (frozen candidates on the selection draw plus the tree solves, settlement, report). Statuses: every adaptive solve OPTIMAL except the PRODUCE class at 12 and 16 tree worlds (FEASIBLE_TIME_LIMIT at the request's own 43 s budget; its static comparator returned NO_FEASIBLE_SOLUTION there, verdict NOT COMPARABLE / NOT SELECTED, nothing selected). Verdicts follow the release-audit semantics (blocker A): a time-limited adaptive incumbent dearer than the static plan is "NOT SELECTED (time-limited ...)", never an ordering failure. The frozen local record of `d8cdad5` is `frozen_local/P4_PERFORMANCE.md`. The interactive rule stays structural: tree worlds <= 8 and not the shared-supplier-order class; the batch cap stays 16.

| class | histories | epochs | cont. | worlds | sets | adaptive status | adaptive s | vars | binaries | rows | HiGHS nodes | static s | PI s | compare wall s | planner wall s | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| single_sku_single_location | 3 | [3] | 2 | 6 | {'3': 3} | OPTIMAL | 1.3 | 3054 | 936 | 3193 | 17 | 1.28 | 0.05 | 2.64 | 2.59 | NO MATERIAL ADAPTIVE BENEFIT |
| single_sku_single_location | 3 | [3, 6] | 2 | 12 | {'3': 3, '6': 6} | OPTIMAL | 0.92 | 6096 | 1872 | 6373 | 1 | 12.73 | 0.14 | 13.79 | 13.19 | NO MATERIAL ADAPTIVE BENEFIT |
| single_sku_single_location | 4 | [3] | 2 | 8 | {'3': 4} | OPTIMAL | 1.5 | 4071 | 1248 | 4256 | 29 | 0.59 | 0.07 | 2.17 | 2.4 | NO MATERIAL ADAPTIVE BENEFIT |
| single_sku_single_location | 4 | [3, 6] | 2 | 16 | {'3': 4, '6': 8} | OPTIMAL | 4.01 | 8127 | 2496 | 8496 | 112 | 19.56 | 0.14 | 23.71 | 26.51 | NO MATERIAL ADAPTIVE BENEFIT |
| single_sku_single_location | 8 | [3] | 1 | 8 | {'3': 8} | OPTIMAL | 0.13 | 4107 | 1248 | 4292 | 1 | 3.83 | 0.09 | 4.05 | 0.72 | NO MATERIAL ADAPTIVE BENEFIT |
| single_sku_single_location | 8 | [3, 6] | 1 | 8 | {'3': 8, '6': 8} | OPTIMAL | 0.13 | 4107 | 1248 | 4292 | 1 | 3.55 | 0.09 | 3.77 | 0.76 | NO MATERIAL ADAPTIVE BENEFIT |
| p2_network | 3 | [3] | 2 | 6 | {'3': 3} | OPTIMAL | 0.12 | 5922 | 144 | 3903 | 1 | 0.16 | 0.11 | 0.39 | 0.72 | NO MATERIAL ADAPTIVE BENEFIT |
| p2_network | 3 | [3, 6] | 2 | 12 | {'3': 3, '6': 6} | OPTIMAL | 0.3 | 11520 | 288 | 7755 | 1 | 0.71 | 0.26 | 1.28 | 1.41 | NO MATERIAL ADAPTIVE BENEFIT |
| p2_network | 4 | [3] | 2 | 8 | {'3': 4} | OPTIMAL | 0.18 | 7869 | 192 | 5196 | 1 | 0.69 | 0.16 | 1.04 | 1.0 | NO MATERIAL ADAPTIVE BENEFIT |
| p2_network | 4 | [3, 6] | 2 | 16 | {'3': 4, '6': 8} | OPTIMAL | 0.48 | 15333 | 384 | 10332 | 1 | 0.93 | 0.39 | 1.82 | 2.05 | NO MATERIAL ADAPTIVE BENEFIT |
| p2_network | 8 | [3] | 1 | 8 | {'3': 8} | OPTIMAL | 0.17 | 8841 | 192 | 5304 | 1 | 0.24 | 0.15 | 0.57 | 0.62 | NO MATERIAL ADAPTIVE BENEFIT |
| p2_network | 8 | [3, 6] | 1 | 8 | {'3': 8, '6': 8} | OPTIMAL | 0.17 | 8841 | 192 | 5304 | 1 | 0.26 | 0.16 | 0.6 | 0.62 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_two_sources | 3 | [3] | 2 | 6 | {'3': 3} | OPTIMAL | 0.12 | 5952 | 144 | 3933 | 1 | 0.21 | 0.11 | 0.45 | 0.8 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_two_sources | 3 | [3, 6] | 2 | 12 | {'3': 3, '6': 6} | OPTIMAL | 0.29 | 11568 | 288 | 7803 | 1 | 0.57 | 0.26 | 1.14 | 1.52 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_two_sources | 4 | [3] | 2 | 8 | {'3': 4} | OPTIMAL | 0.18 | 7908 | 192 | 5235 | 1 | 0.41 | 0.16 | 0.75 | 1.12 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_two_sources | 4 | [3, 6] | 2 | 16 | {'3': 4, '6': 8} | OPTIMAL | 0.47 | 15396 | 384 | 10395 | 1 | 0.81 | 0.39 | 1.69 | 2.21 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_two_sources | 8 | [3] | 1 | 8 | {'3': 8} | OPTIMAL | 0.17 | 8916 | 192 | 5379 | 1 | 0.36 | 0.16 | 0.7 | 0.71 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_two_sources | 8 | [3, 6] | 1 | 8 | {'3': 8, '6': 8} | OPTIMAL | 0.19 | 8916 | 192 | 5379 | 1 | 0.34 | 0.16 | 0.69 | 0.71 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_multi_sku_shared_order | 3 | [3] | 2 | 6 | {'3': 3} | OPTIMAL | 2.06 | 11790 | 318 | 7338 | 2 | 4.37 | 2.33 | 8.78 | 32.87 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_multi_sku_shared_order | 3 | [3, 6] | 2 | 12 | {'3': 3, '6': 6} | OPTIMAL | 7.87 | 22896 | 624 | 14538 | 4 | 7.6 | 11.42 | 26.91 | 176.2 | ADAPTIVE PLAN NOT SELECTED (time-limited adaptive solve did not improve on the static plan) |
| p3_multi_sku_shared_order | 4 | [3] | 2 | 8 | {'3': 4} | OPTIMAL | 6.69 | 15663 | 423 | 9765 | 3 | 8.41 | 10.54 | 25.66 | 58.4 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_multi_sku_shared_order | 4 | [3, 6] | 2 | 16 | {'3': 4, '6': 8} | OPTIMAL | 19.96 | 30471 | 831 | 19365 | 27 | 11.85 | 32.69 | 64.54 | 191.6 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_multi_sku_shared_order | 8 | [3] | 1 | 8 | {'3': 8} | OPTIMAL | 3.56 | 17715 | 459 | 10089 | 9 | 6.92 | 6.58 | 17.08 | 26.64 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_multi_sku_shared_order | 8 | [3, 6] | 1 | 8 | {'3': 8, '6': 8} | OPTIMAL | 9.95 | 17715 | 459 | 10089 | 9 | 6.6 | 6.18 | 22.75 | 24.15 | NO MATERIAL ADAPTIVE BENEFIT |
| sector_produce | 3 | [3] | 2 | 6 | {'3': 3} | OPTIMAL | 5.53 | 6434 | 1488 | 6250 | 377 | 23.75 | 0.21 | 29.5 | 38.98 | NO MATERIAL ADAPTIVE BENEFIT |
| sector_produce | 3 | [3, 6] | 2 | 12 | {'3': 3, '6': 6} | FEASIBLE_TIME_LIMIT | 43.05 | 12548 | 2976 | 12448 | 2485 | 43.04 | 0.67 | 86.77 | 92.65 | ADAPTIVE PLAN NOT SELECTED (a static candidate passed the gates at lower settled cost) |
| sector_produce | 4 | [3] | 2 | 8 | {'3': 4} | OPTIMAL | 10.41 | 8551 | 1984 | 8325 | 766 | 31.11 | 0.29 | 41.81 | 57.95 | NO MATERIAL ADAPTIVE BENEFIT |
| sector_produce | 4 | [3, 6] | 2 | 16 | {'3': 4, '6': 8} | FEASIBLE_TIME_LIMIT | 43.13 | 16703 | 3968 | 16589 | 2139 | 43.11 | 0.72 | 86.98 | 95.17 | ADAPTIVE PLAN NOT COMPARABLE (no static comparator plan: infeasible or not found within the time budget) |
| sector_produce | 8 | [3] | 1 | 8 | {'3': 8} | OPTIMAL | 0.26 | 9299 | 1984 | 8433 | 1 | 41.3 | 0.24 | 41.81 | 10.12 | NO MATERIAL ADAPTIVE BENEFIT |
| sector_produce | 8 | [3, 6] | 1 | 8 | {'3': 8, '6': 8} | OPTIMAL | 4.07 | 9299 | 1984 | 8433 | 68 | 42.98 | 0.22 | 47.28 | 14.89 | NO MATERIAL ADAPTIVE BENEFIT |

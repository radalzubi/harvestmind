# P4 performance matrix (local, Apple laptop; Fly shared-cpu-2x measured 4-5x slower unthrottled at the P3 closure)

Engineering matrix `scripts/p4_profile.py`: histories x review epochs x continuations x request class. `compare wall` = static + adaptive + perfect-information solves on the tree; `planner wall` = the whole `plan()` (frozen candidates on the selection draw plus the three tree solves, settlement, report). Every adaptive solve here is OPTIMAL.

| class | histories | epochs | cont. | worlds | sets | adaptive s | vars | binaries | rows | HiGHS nodes | static s | PI s | compare wall s | planner wall s | planner verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| single_sku_single_location | 3 | [3] | 2 | 6 | {'3': 3} | 1.32 | 3054 | 936 | 3193 | 17 | 1.3 | 0.05 | 2.68 | 2.64 | NO MATERIAL ADAPTIVE BENEFIT |
| single_sku_single_location | 3 | [3, 6] | 2 | 12 | {'3': 3, '6': 6} | 0.92 | 6096 | 1872 | 6373 | 1 | 12.43 | 0.14 | 13.49 | 13.32 | NO MATERIAL ADAPTIVE BENEFIT |
| single_sku_single_location | 4 | [3] | 2 | 8 | {'3': 4} | 1.49 | 4071 | 1248 | 4256 | 29 | 0.59 | 0.07 | 2.16 | 2.42 | NO MATERIAL ADAPTIVE BENEFIT |
| single_sku_single_location | 4 | [3, 6] | 2 | 16 | {'3': 4, '6': 8} | 4.03 | 8127 | 2496 | 8496 | 112 | 19.57 | 0.14 | 23.75 | 26.55 | NO MATERIAL ADAPTIVE BENEFIT |
| single_sku_single_location | 8 | [3] | 1 | 8 | {'3': 8} | 0.13 | 4107 | 1248 | 4292 | 1 | 3.83 | 0.09 | 4.05 | 0.72 | NO MATERIAL ADAPTIVE BENEFIT |
| single_sku_single_location | 8 | [3, 6] | 1 | 8 | {'3': 8, '6': 8} | 0.13 | 4107 | 1248 | 4292 | 1 | 3.58 | 0.09 | 3.8 | 0.77 | NO MATERIAL ADAPTIVE BENEFIT |
| p2_network | 3 | [3] | 2 | 6 | {'3': 3} | 0.12 | 5922 | 144 | 3903 | 1 | 0.16 | 0.11 | 0.39 | 0.72 | NO MATERIAL ADAPTIVE BENEFIT |
| p2_network | 3 | [3, 6] | 2 | 12 | {'3': 3, '6': 6} | 0.3 | 11520 | 288 | 7755 | 1 | 0.72 | 0.26 | 1.29 | 1.41 | NO MATERIAL ADAPTIVE BENEFIT |
| p2_network | 4 | [3] | 2 | 8 | {'3': 4} | 0.18 | 7869 | 192 | 5196 | 1 | 0.69 | 0.16 | 1.04 | 0.99 | NO MATERIAL ADAPTIVE BENEFIT |
| p2_network | 4 | [3, 6] | 2 | 16 | {'3': 4, '6': 8} | 0.48 | 15333 | 384 | 10332 | 1 | 0.93 | 0.39 | 1.82 | 2.06 | NO MATERIAL ADAPTIVE BENEFIT |
| p2_network | 8 | [3] | 1 | 8 | {'3': 8} | 0.17 | 8841 | 192 | 5304 | 1 | 0.25 | 0.16 | 0.58 | 0.62 | NO MATERIAL ADAPTIVE BENEFIT |
| p2_network | 8 | [3, 6] | 1 | 8 | {'3': 8, '6': 8} | 0.17 | 8841 | 192 | 5304 | 1 | 0.26 | 0.16 | 0.6 | 0.62 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_two_sources | 3 | [3] | 2 | 6 | {'3': 3} | 0.12 | 5952 | 144 | 3933 | 1 | 0.21 | 0.11 | 0.45 | 0.8 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_two_sources | 3 | [3, 6] | 2 | 12 | {'3': 3, '6': 6} | 0.29 | 11568 | 288 | 7803 | 1 | 0.57 | 0.27 | 1.14 | 1.52 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_two_sources | 4 | [3] | 2 | 8 | {'3': 4} | 0.17 | 7908 | 192 | 5235 | 1 | 0.41 | 0.16 | 0.75 | 1.12 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_two_sources | 4 | [3, 6] | 2 | 16 | {'3': 4, '6': 8} | 0.47 | 15396 | 384 | 10395 | 1 | 0.81 | 0.4 | 1.7 | 2.22 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_two_sources | 8 | [3] | 1 | 8 | {'3': 8} | 0.17 | 8916 | 192 | 5379 | 1 | 0.36 | 0.16 | 0.69 | 0.71 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_two_sources | 8 | [3, 6] | 1 | 8 | {'3': 8, '6': 8} | 0.18 | 8916 | 192 | 5379 | 1 | 0.33 | 0.16 | 0.67 | 0.71 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_multi_sku_shared_order | 3 | [3] | 2 | 6 | {'3': 3} | 2.07 | 11790 | 318 | 7338 | 2 | 4.4 | 2.34 | 8.82 | 33.14 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_multi_sku_shared_order | 3 | [3, 6] | 2 | 12 | {'3': 3, '6': 6} | 7.9 | 22896 | 624 | 14538 | 4 | 7.64 | 11.45 | 27.02 | 176.26 | ADAPTIVE PLAN REJECTED (ordering check failed) |
| p3_multi_sku_shared_order | 4 | [3] | 2 | 8 | {'3': 4} | 6.72 | 15663 | 423 | 9765 | 3 | 8.44 | 10.58 | 25.75 | 58.83 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_multi_sku_shared_order | 4 | [3, 6] | 2 | 16 | {'3': 4, '6': 8} | 20.23 | 30471 | 831 | 19365 | 27 | 12.54 | 33.08 | 65.89 | 192.45 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_multi_sku_shared_order | 8 | [3] | 1 | 8 | {'3': 8} | 3.52 | 17715 | 459 | 10089 | 9 | 6.85 | 6.51 | 16.9 | 26.3 | NO MATERIAL ADAPTIVE BENEFIT |
| p3_multi_sku_shared_order | 8 | [3, 6] | 1 | 8 | {'3': 8, '6': 8} | 9.79 | 17715 | 459 | 10089 | 9 | 6.51 | 6.09 | 22.42 | 23.72 | NO MATERIAL ADAPTIVE BENEFIT |

## Reading

* Columns grow linearly with the tree: variables ~ worlds x (per-world block) + one purchase / transfer column per line, period and node; binaries per node only for the order-class rows (12 order binaries x sets on the shared-order class), the rest are the frozen per-world indicators.
* P2 network, two-source P3 and the single-SKU P1 class stay interactive at 8 worlds (planner 0.6 - 2.6 s local); 16 worlds on the single-SKU class with two epochs takes 26 s local (~120 s on Fly): not interactive.
* The P3 shared-supplier-order class (two SKUs on one MOV order, the P3 performance-closure class) is the slow one: planner 33 s (6 worlds), 59 s (8), 176 - 192 s (12 - 16) locally; the static solve of this class alone is 12 - 39 s. With recourse it is **batch-only** in V1 (deterministic rule below), through the existing asynchronous jobs endpoint.

## Deterministic interactive rule (V1, enforced in `validated()` before any model)

A synchronous `/api/zaad/network/plan` request with `recourse.enabled` is accepted only when
`scenarios x continuations ^ epochs <= 8` **and** the request is not in the shared-supplier-order
class (`zaad.full.model.shared_supplier_orders`); otherwise 413 with the reason, and the same request
is accepted by `POST /api/zaad/network/jobs` (structural cap 16 tree worlds, the job runner's own
wall clock and quotas). Expected interactive wall on Fly from the local numbers: single-SKU 8 worlds
~11 s, P2 / two-source P3 8 worlds ~10 s, well inside the 180 s gate.

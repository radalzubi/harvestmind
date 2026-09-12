# P3 production performance closure: BEFORE

Runtime measured: `0de6850` (P3 released runtime; `1e712c9` is runtime-identical). Local machine:
Apple laptop, Python 3.14, scipy 1.17.1 (frozen solver route), highspy 1.14.0 (warm-started
solves). Fly: `zaad-api` v17, machine `0804e0dfd1e948`, shared-cpu-2x, 2 GB, fra.

Every local figure comes from `local_profile_<case>_before.json` (the instrumented harness records
each HiGHS call with the candidate it belongs to, the model size, status, nodes and objective).
Every Fly figure comes from the release smoke (`../release/production_smoke_v17.json`, throttled
machine) or from the reproduction on 2026-09-11 (`fly_before_shared_mov_full.json`).

## A. exact shared-MOV production snapshot (`shared_mov_prod_snapshot.json`)

| | value |
|---|---|
| wall, local | 17.55 s (solver 17.06 s, 18 HiGHS calls; build 0.35 s; settlement 0.12 s; serialisation 0.003 s) |
| wall, Fly release smoke (throttled) | **218.4 s** |
| wall, Fly reproduction (unthrottled) | 76.2 s |
| solver calls | 18 (12 candidate / valuation models, 2 warm-start completions, 4 phase-one objectives) |
| variables / binaries / rows | 1-world 2,476 / 60 / 1,363; 3-world 5,904 / 156 / 3,759 (see the profile) |
| nodes (base, deterministic, stochastic, cadence 2, cadence 4) | 1,214 / 260 / 13 / 3 / 1 |
| status | every solve OPTIMAL locally and on the unthrottled Fly rerun; time-limited on the throttled release run |
| selected action | `stochastic_network`, NO_ACTION state, PURCHASING_ECONOMICS owner, MATERIAL_IMPROVEMENT (cost -0.33 %, inventory -24.2 %, service +0.000) |
| objective (stochastic_network solver objective) | 25,408.1631 (projected cost); settled selected TOTAL 25,960.31 vs incumbent 26,045.65 |
| service | every service at or above the incumbent's; no service worse |
| source allocation (plan) | A: `src_A` 2,808.7 (0.991) + `src_S2` 24.6 (0.009); B: `src_A_B` 2,831.1 (0.990) + `src_S2_B` 29.0 (0.010); period 0: `src_S2` 24.6, `src_S2_B` 29.0 |
| incumbent allocation | `network:rop`: A 2,044.8 at period 0 (4,089.5 over the plan), B likewise |
| MOV satisfaction | `supplier` orders at periods 1 (621 + 622 = 1,243 units, 6,216 value) and 4 (2,187 + 2,209, 21,984 value): both above the 5,000 MOV; no order at period 0 |
| pack quantities | none declared |
| materiality | MATERIAL_IMPROVEMENT; approval required; executable order false |
| release-smoke (throttled) decision | `cadence_4_network`, period-0 `src_A` 650.0 / `src_A_B` 654.7, shares 1.0 / 0.0 - a weaker, time-limited plan of the same request |

## B. multi-SKU shared-capacity snapshot (`multi_sku_capacity_prod_snapshot.json`)

| | value |
|---|---|
| wall, local | 2.47 s (solver 1.98 s, 23 calls) |
| wall, Fly release smoke | 77.6 s |
| selected | `stochastic_network`, NORMAL_REPLENISHMENT, CHANGE_SOURCE_MIX on both pairs |
| allocation (plan) | A: `src_A` 2,426.0 / `src_S2` 699.2; B: `src_A_B` 2,074.0 / `src_S2_B` 1,071.1; period 0: `src_A` 158.3, `src_S2` 153.0, `src_A_B` 291.7, `src_S2_B` 45.0 |
| settled selected TOTAL | 39,850.471 |

## C. correlated plant-group snapshot (`correlated_risk_prod_snapshot.json`)

| | value |
|---|---|
| wall, local | 3.77 s (solver 3.57 s, 10 calls; deterministic_network 1.37 s / 265 nodes; oracles 569 and 871 nodes) |
| wall, Fly release smoke | 45.6 s |
| selected | `deterministic_network` (solver objective 9,747.326489), NO_ACTION, CHANGE_SOURCE_MIX |
| allocation (plan), local | A: `src_A` 1,433.3 / `src_B` 818.2 / `src_C` 0 (tie: `src_A` and `src_B` carry the identical 5.00 landed price and share the plant group) |
| allocation (plan), Fly v17 | A: `src_A` 0 / `src_B` 2,251.5 / `src_C` 0 - the same objective, the other representative of the tie |
| settled selected TOTAL, local | 12,986.559 |

## D. simple two-source economics case (`simple_p3_prod_snapshot.json`)

| | value |
|---|---|
| wall, local | 0.41 s (solver 0.21 s, 10 calls) |
| selected | incumbent retained (`operator_rule:network:rop`), RETAIN_INCUMBENT_MIX, `src_A` 2,081.4 / `src_B` 0 |
| settled TOTAL | 12,889.393 |

## E. P2 representative network case (`p2_network_prod_snapshot.json`, no P3 block)

| | value |
|---|---|
| wall, local | 0.34 s (solver 0.16 s, 9 calls) |
| selected | incumbent retained (`operator_rule:network:rop`); settled TOTAL 12,936.558; sourcing block absent |

## F. P1 representative cases

The P1 canonical regression (fixtures B / T / Q / A, twelve reviews each) is the P1 benchmark of
record for this closure; its before state is the frozen authoritative record it compares against
(`scripts/zaad_canonical_regression.py`, identity True on `1e712c9`, `gates/canonical_regression.log`).

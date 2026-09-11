# P3 sourcing portfolio: performance record

Measured with the P2 profiling harness (`scripts.p3_profile`, in-process instrumentation, HiGHS through
scipy 1.18.1 / highspy 1.15.1 on the 12-core machine of the sector record), and with the authoritative
benchmark (`p3_authoritative`, six workers).

## Binary discipline

P3 adds at most one binary per declared non-incumbent source with a switching cost (`switch`, first
stage, never per period or per world) and no binary for a share constraint (linear rows). The frozen
source binaries stay what they were: `active` per source-period only when a MOQ, a fixed fee or a quote
group is declared, pack / case / pallet general integers only when a pack is declared, `order` and
`pallets` per supplier-period only when supplier terms are declared. Zero-capability pruning removes the
binaries of every source-period bounded at zero (exact; A3 identity). Profiles below list the integer
columns by kind; none is a source x world or a P3 source x period binary.

## Authoritative run (480 ZAAD reviews)

| set | p50 | p95 | max | time-limited | over 60 s | over 180 s |
|---|---|---|---|---|---|---|
| all families | 0.66 s | 19.2 s | 42.8 s | 0 | 0 | 0 |
| economics (E1-E6) | 0.8 s | - | 10.7 s (E4, MOQ / MOV binaries) | 0 | 0 | 0 |
| reliability (R1-R6) | 0.9 s | - | 7.5 s | 0 | 0 | 0 |
| constraints (C1-C6) | 0.5 s | - | 24.8 s (C6, supplier MOV across two SKUs) | 0 | 0 | 0 |
| sector (S1-S4) | 5.1 s | - | 42.8 s (S4, case and pallet packs on two suppliers) | 0 | 0 | 0 |
| network (N1-N3) | 0.9 s | - | 14.6 s (N3, mixed sector) | 0 | 0 | 0 |
| abstention (A1-A6) | 0.4 s | - | 0.8 s | 0 | 0 | 0 |

Solve statuses over every ZAAD candidate: 2,266 OPTIMAL, 6 INFEASIBLE (service floors provably
unattainable on a candidate class), 0 time-limited. Adding a second or third source to the P2 frame
leaves the median review under one second; no multi-minute review arose from a source count.

## Representative profiles (`profiles/`)

| review | wall | dominant candidate | variables | integer (binary) columns by kind | rows | nodes | note |
|---|---|---|---|---|---|---|---|
| E3 41001 r0 (two price tiers) | 0.8 s | joint_recovery 0.2 s | 1,224-3,780 | 48-120 (active 24 = 2 tiers x 12 periods, depleted) | 755-2,663 | 1 | the exclusive quote group is 24 `active` binaries, one row per period |
| C6 41001 r0 (shared MOV, two SKUs) | 18.2 s | base_stock proxy 4.9 s, 1,214 nodes; deterministic 2.7 s | 2,364-5,904 | 60-156 (order 12, depleted) | 1,363-3,759 | up to 1,214 | the supplier-order MOV binary is the frozen P1 mechanism; two SKU lines share it |
| N3 41001 r1 (mixed sector, shared capacity) | 4.7 s | joint_recovery 2.3 s | 2,549-8,192 | 266-1,064 (FEFO 218-872 on the produce SKU, depleted) | 1,714-6,575 | 1 | the FEFO indicators belong to the produce SKU's cohorts (sector record); the commercial SKU adds none |
| S4 41001 r3 (case / pallet packs, two suppliers) | 21.5 s | `restricted:alternates` 15.0 s, 8,088 nodes | 1,516-3,586 | 96-144 (case 24, pallets 12, order 12, depleted) | 880-2,373 | 8,088 | decision candidates 0.2-1.2 s; the 15 s is the frozen report-only alternates valuation (the same solve with the second source removed) on integer packs, the class the sector record profiled on C1 |

Reading: the P3 hooks add no integer column to any profiled review beyond the `switch` binary on E6
(one column). The only reviews above 20 s are the frozen report-only valuations on integer packs (S4,
C6's base-stock proxy), the class already documented in the sector record; they are below the 60 s
"profile and explain" rule on the profiled reviews and the benchmark's maximum (42.8 s, S4 seed 41002)
is below the 180 s blocker. Model build 0.1-0.4 s per review; settlement 0.05-0.1 s; warm-start
completion 0.1-0.7 s.

## Legacy runtime under the P3 code

P2 authoritative matrix re-run (`p2_under_p3`): p50 0.50 s, p95 7.3 s, max 16.8 s (release record
0.48 / 6.6 / 14.6 s: run alongside the P3 gate chain; decisions 344 / 344 identical). Sector matrix
re-run (`sector_under_p3`): p50 1.5 s, p95 9.0 s, max 60.6 s (record 1.4 / 8.4 / 59.5 s; the same C1
frontier oracle). No time-limited solve in either.

## Not applied

No HiGHS parameter change, no commercial solver, no time-limit increase, no world reduction, no
economics or service change to meet runtime.

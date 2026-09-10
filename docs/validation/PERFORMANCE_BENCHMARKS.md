# Performance benchmarks

Environment: {'platform': 'macOS-26.3.1-arm64-arm-64bit-Mach-O', 'python': '3.14.3', 'machine': 'arm64', 'cpu_count': 12}

These are measurements on one developer machine, not guarantees.

## Optimizer (MultiPeriodStochasticLP, HiGHS)

| case | p50 s | min s | max s |
|---|---|---|---|
| skus=10,scen=30,H=12,LP | 0.48 | 0.46 | 0.56 |
| skus=100,scen=30,H=12,LP | 6.05 | 5.95 | 6.62 |
| skus=100,scen=30,H=12,MILP | 9.68 | 9.54 | 9.79 |
| skus=1000,scen=20,H=8,LP | 46.99 | 46.35 | 47.62 |
| skus=500,scen=20,H=8,MILP | 19.77 | 19.36 | 20.18 |

## Simulator

| case | s |
|---|---|
| skus=60,weeks=156 | 1.86 |
| skus=150,weeks=156 | 5.04 |
| skus=1000,weeks=104 | 20.26 |

## Ingestion

| case | p50 s |
|---|---|
| validate_rows=10000 | 0.002 |
| duckdb_insert_rows=10000 | 0.002 |
| validate_rows=100000 | 0.011 |
| duckdb_insert_rows=100000 | 0.013 |

## API (in-process TestClient)

| path | p50 ms | p95 ms | p99 ms |
|---|---|---|---|
| /health | 0.9 | 1.1 | 2.6 |
| /ready | 10.6 | 11.3 | 15.9 |
| / | 0.9 | 1.1 | 1.2 |

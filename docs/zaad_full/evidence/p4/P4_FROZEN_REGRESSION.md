# P4 frozen regression (P0 / P1 / P2 / sector / P3 under the P4 code)

Runtime under test: branch `claude/zaad-adaptive-recourse-p4` (this closeout's product commit). No
request in any frozen matrix declares a `recourse` block, so by construction none of these runs
reaches a P4 code path; the runs prove that the one hook in the model builder (node-indexed columns
when a node map is supplied, frozen names otherwise) and the planner's guarded candidate leave every
frozen decision bit-identical. Baselines are the P3 performance-closure records (the production
runtime `61a3e75`): `p2_perf_closure`, `sector_perf_closure`, `p3_perf_closure`, `router_cycle`.
Logs: `gates/`.

| gate | result |
|---|---|
| P3 performance-closure shared-MOV snapshot (`perf_closure/shared_mov_prod_snapshot.json`) | 12.0 s local (perf-closure runtime 12.8 s on the same machine), 18 HiGHS calls, every candidate optimal with the identical objective (stochastic 25,408.1631, deterministic 25,656.5736, cadences 25,458.3590, base 51,267.0518), same selection (`stochastic_network`) and the same purchases; no `recourse` block in the report (`gates/p3_snapshot_under_p4.json`) |
| P1 canonical B / T / Q / A twelve-review identity + P0 cell 15 | identical True on every fixture; CANONICAL REGRESSION PASS (`gates/canonical_regression.log`) |
| P1 invariants | 60 passing, 0 failures (`gates/p1_invariants.log`) |
| P2 fixtures / principles / invariants | 20 / 20, 18 / 18, INVARIANTS PASS (`gates/p2_benchmark.log`, `gates/p2_invariants.log`) |
| P2 authoritative review identity vs `p2_perf_closure` | 1,720 / 1,720 reviews identical, every policy (`gates/p2_compare.log`) |
| sector fixtures / invariants | 26 / 26, 19 / 19 (`gates/sector_benchmark.log`, `gates/sector_invariants.log`) |
| ZAAD sector review identity vs `sector_perf_closure` (gated policy, the identity claim of record) | 416 / 416 identical (`gates/sector_compare.log`); the `echelon_base_stock` comparator's own run-to-run variability, documented at the P3 performance closure, is not a P4 regression and is not re-interpreted as one |
| P3 fixtures / invariants / adversarial | 30 / 30 fixtures (480 ZAAD reviews p50 0.65 s / p95 17.5 s / max 41.9 s, 0 time-limited), 34 / 34 invariants, 23 / 23 adversarial (`gates/p3_benchmark.log`, `gates/p3_invariants.log`, `gates/p3_adversarial.log`) |
| P3 review identity vs `p3_perf_closure` (the CURRENT P3 baseline, i.e. the production runtime `61a3e75`) | 2,304 / 2,304 replay reviews identical across every policy, C6 included (`gates/p3_compare.log`). This is the P4-disabled regression against the current baseline. It is a different comparison from the historical P3 performance-closure record, which remains **2,273 / 2,304 identical + 31 proven objective-flat C6 transfer ties** (`61a3e75` against `p3_corrective`, `evidence/p3/perf_closure/P3_PRODUCTION_PERF_AFTER.md`); P4 does not rewrite that record |
| P3 structural performance tests | `tests/unit/test_zaad_activation_bounds.py` green in the full suite |
| P0 six-cell arm `p4_recourse` vs `router_cycle` | cells 15 / 16 / 20 / 21 / 90 decision-identical (12 / 12, 12 / 12, 20 / 20, 20 / 20, 26 / 26); cell 108 29 / 30 under CPU contention (review 5: the hedged candidate timed out and dropped from the feasible set, unmet and cost identical - the known wall-clock class); quiet rerun of cell 108 (`p4_recourse_rerun`) 30 / 30 identical -> **120 / 120** under the established protocol (`gates/p0_arm.log`, `gates/p0_compare.log`, `gates/p0_arm_rerun.log`, `gates/p0_compare_rerun108.log`) |

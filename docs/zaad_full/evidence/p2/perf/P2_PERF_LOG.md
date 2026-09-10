# P2 performance pass: development log

One entry per change, in order. Every entry records the SHA it was measured at, the change, the
equivalence argument, the measured dimensions / times / nodes / objective / decision identity on the
profiled portfolio (`scripts/p2_profile_review.py` on the cached snapshots, quiet machine, deep HiGHS
logs), and whether it was accepted. Baseline profiles: `perf/profiles/<fixture>_<seed>_r<k>.json`
at `6261d12`; the diagnosis is `P2_PERF_DIAGNOSIS.md`.

Rules observed throughout: same decision problem (worlds, horizons, candidate classes, service
floors, MIP gap 1e-6, fixture economics and seeds untouched); no fixture, seed or review is
recognised anywhere; no commercial solver; the 180 s gate is not moved.

## Entry 0 - diagnosis (no code change), `6261d12`

See `P2_PERF_DIAGNOSIS.md`. Summary: on the failing reviews 69% of the wall is the warm-start
completion (a first-feasibility MIP that forfeits its 30 s cap on eight-world models), the rest is
the MILPs proper, whose first incumbent takes 10-31 s because 95% of the binaries are FEFO
indicators between cohorts that all outlive the horizon (big-M 1e6). Construction, settlement,
memory and proof-after-incumbent are not material.

## Entry 1 - exact FEFO symmetry elimination (`zaad/full/model.py`, `FEFO_SYMMETRY_ELIMINATION`)

**Change.** The FEFO indicator for consuming cohort `e_young` at (SKU, location, period, world) is
built against the older cohorts that can matter inside the window only: `e_old <= max(H,
latest transfer arrival schedulable for the SKU)`. If no older cohort is inside the window, no
indicator and no rows are created. The window is computed from the request's own horizon, lanes and
receiving calendars (`latest_due` per SKU, taken in the transfer loop); it recognises nothing about
any fixture.

**Equivalence argument.** Two cohorts of one SKU that both outlive the window are interchangeable in
the model: (i) their inventory columns exist on every period, carry the same holding cost, the same
terminal value and the same continuation supply, and never the disposal charge (`expiry == t+1`);
(ii) their transfer columns exist on every lane and period with the same capacity, cost, loss and
arrival period, and the arrival-before-expiry cap (`due >= expiry`) never binds because
`expiry > latest_due`; (iii) every other row that touches them (depleted, priority, direct-first,
packs, dispatch, location capacity, continuation supply) sums over cohorts. The only row that
distinguishes them is FEFO itself. Given any solution of the relaxed model, re-disaggregate the
pooled flow of the interchangeable group at each location and period - consumption from the oldest
cohort first, outbound transfers from the youngest - and every original row holds with the same
aggregated purchases, transfers, unmet, cash and objective; the original solution set is contained
in the relaxed one. Hence the optimal objective, the projected service, the purchases, the
cohort-summed transfers and the incumbent projection are identical; only which interchangeable
label carries a transfer or a consumption can differ. The settlement applies FEFO on its own to
consumption and checks period-zero transfers against opening stock per cohort, which the relaxed
model still enforces (its per-cohort balance rows are untouched). FEFO between any cohort and an
older cohort inside the window is kept exactly, so perishable P0 / P1 cells keep their rows where
they can bind.

**Scope.** Network requests only (a declared transfer lane). On the frozen single-node P1 fixtures the
elimination is equally exact - on T (two SKUs, shelf life 52, no lanes) the stochastic candidate's
objective is -10820.3409555832 under both formulations (identical to 1e-15) - but the smaller model
breaks a tie between two equal-cost source splits differently (1248 / 672 against 1368 / 552 at
review 0), which would change the recorded P1 decision path. The frozen single-node formulation is
therefore kept verbatim (`window = inf` when `req.transfers` is empty): a frozen path is not re-tuned
for speed it does not need, and the P2 blocker lives on network requests. The rule is structural
(the request class), not a fixture, seed or review.

**Measurement** (`perf/profiles/*_v1.json` against the `6261d12` baselines, quiet machine,
`scripts/p2_profile_compare.py`; objective = candidate projected cost):

| review | wall before -> after | stochastic candidate: vars / binaries before -> after | nodes | statuses | objectives | decision |
|---|---|---|---|---|---|---|
| M 41002 r7 | **250.4 s -> 7.0 s** | 13,631 / 3,648 -> 10,175 / 192 | 315 -> 1 | identical (12 / 12) | identical to 1e-10 on every candidate | state, owner, selected policy, status, period-zero purchases and transfers identical; later-period guidance transfers re-timed within an exact tie (north: 105.7 + 105.6 at periods 3 and 4 -> 211.3 at period 3; totals 420.2 and 208.9 identical) |
| O 41001 r6 | **88.0 s -> 0.7 s** | 9,150 / 2,304 -> 6,990 / 144 | 1,458 -> 1 | stochastic FEASIBLE_TIME_LIMIT (gap 1.13%) -> OPTIMAL | 12,353.36 (time-limited plan) -> 12,285.27 (proven optimum) | same state, owner, selected policy, status and purchases; transfers differ because the frozen run never reached the optimum |
| H 41001 r4 | 77.5 s -> 0.8 s | 4,022 / 1,008 -> 3,086 / 72 | 1,278 -> 1 | identical | identical | identical on every key |
| A 41001 r7 | 7.9 s -> 0.3 s | 4,029 / 1,008 -> 3,093 / 72 | 171 -> 1 | identical | identical | identical on every key |
| G 41001 r2 | 0.8 s -> 0.5 s | 4,022 / 1,008 -> 3,086 / 72 | - (INFEASIBLE) | identical | identical | identical on every key |

Every candidate of every profiled review now solves at the root node (HiGHS 1.14 deep re-solve of
M's stochastic model: 3,139 x 3,054 with 807 binaries after presolve -> 2,121 x 3,352 with 161
binaries; first incumbent 0.1 s, proof 0.5 s, 3,902 LP iterations against 10.3 s / 23.4 s /
192,245). The remaining binaries are the `depleted` indicators (one per service x period x world)
and the executable-period packs / dispatch flags where declared.

**Frozen behaviour.** `scripts/zaad_canonical_regression.py`: P1 B, T, Q, A twelve reviews identical,
P0 cell 15 identical (`perf/gates/canonical_regression_v2.log`; the ungated first cut failed on T,
`canonical_regression_v1.log`, which is what fixed the scope above). Full suite 1,838 passed, 2
skipped (`perf/gates/pytest_v1.log`, ungated cut; re-run at the final SHA below).

**Accepted.**

## Entry 2 - warm-start completion re-measured (no code change)

After entry 1 the completion no longer forfeits its cap: on M r7 every floor completion is accepted
in 0.2-0.6 s (1.9 s of the 7.0 s review) and the seeded main solves take 0.5-1.1 s; unseeded deep
re-solves of the same models reach the first incumbent in 0.1 s and the proof in 0.5 s. The
completion is now a small fixed cost rather than a lost budget; the frozen v8 policy (its budget
`min(30 s, 0.6 x budget)`, the equal -> floor cascade) is left unchanged rather than re-tuned on
speed it no longer needs. Time to first incumbent before -> after (unseeded, HiGHS 1.14): M
stochastic 10.3 s -> 0.1 s, cvar 30.8 s -> 0.1 s; O stochastic 27.4 s (never improved, no proof in
56 s) -> 0.1 s (proof 0.2 s). Recorded, not binding.

## Entry 3 - levers evaluated and not applied

* **Bound tightening of the big-M rows** (`depleted`, remaining `fefo`, `priority`, `direct_first`; M
  = location capacity / unit volume = 1e6): a valid tighter bound on the stock sum would need finite
  supplier, lane or inbound capacities; on the P2 requests every one of them is 1e6, so no
  data-derived bound below the location capacity exists. LP relaxation and node counts before ->
  after entry 1 are recorded above; with every candidate at the root node there is nothing left
  for tightening to buy. Not applied.
* **Exact structural presolve in Python** (unreachable transfer columns, closed calendar arcs, zero
  capacity, impossible receipts): HiGHS presolve already removes 70-78% of rows and columns
  (recorded per candidate in the deep profiles); construction is 0.8 s of M's 7.0 s. Not applied.
* **Formulation of packs / dispatch** (Q): see the Q profile below.
* **HiGHS parameter tuning, threads, parallel candidate execution, receding-horizon reuse,
  decomposition**: not needed once the portfolio is inside the gate by two orders of magnitude;
  each would change the solver path on frozen cells for no gate benefit. Not applied.
* **Gap policy**: rejected by the measurement (time to decision equals time to proof on every
  profiled candidate before and after).

# Sector physics: development log

Branch `claude/zaad-sector-physics` (worktree `harvestmind-sectors`) from `main` `ea1ed3a`. Every entry
records hypothesis, change, fixture, result and the decision; negative evidence stays.

## Entry 0 - starting state (2026-09-11)

Canonical regression PASS (B / T / Q / A identity, P0 cell 15); P2 tests 49 passed; P2 invariants 20 / 20
(`baseline/`); P2 review profiles A r7 0.3 s, H r4 0.8 s, M r7 7.0 s, O r6 0.7 s, Q r6 13.4 s. Audit of
the existing physics written before code (`SECTOR_PHYSICS_EXISTING_CAPABILITIES.md`); architecture and
fixture specification dated before implementation.

## Entry 1 - contract and validation, `246080c`

`zaad/sectors/contracts.py` (`SectorMode`, `SkuPhysics`, `Physics` view, `resolve`) and
`validation.py`; default-off fields on `Location`, `Transfer`, `SupplierTerms`, `Request`. Declared
values must carry a provenance other than UNKNOWN; thresholds and ages below the shelf life; a state
no location can hold, stock at an ineligible location, unknown states and modes are refused at the
contract. Legacy requests resolve to None. Accepted.

## Entry 2 - model hooks, `246080c`

Hypothesis: every produce / meat rule can be expressed as eligibility caps and sellable-cohort
allocation without a new binary. Change: receipt life on purchase and PO arrivals, source and lane
caps for state / minimum life at receipt, zero-capacity inventory at ineligible locations,
`allocate` / `depleted` / FEFO over sellable cohorts only, cohort-aware cumulative continuation rows
on physics requests, weight cap row. Result: canonical regression identical after the patch (legacy
path untouched); binaries on the produce fixtures are FEFO indicators between in-window cohorts
(P3 r7: 708 of 780; P4 r5: 1,224 of 1,368) - the P2 symmetry elimination still removes every
out-of-window indicator (invariant 06). Accepted.

## Entry 3 - settlement and continuation, `246080c`

The same rules re-derived from the executed plan: receipt life, state eligibility and minimum life at
receipt as `PhysicalViolation`, FEFO over sellable cohorts, weight cap, `sellable` flag on end stock;
`terminal.continuation_value` consumes only while sellable (monotone in remaining life, invariant 04).
Accepted.

## Entry 4 - the rule projection had to be physics-legal, `246080c`

Hypothesis (rejected): the declared `network:rop` incumbent could stay physics-unaware. Result on the
first smoke (X3, M3): the rule shipped a frozen SKU to a chilled-only branch, its projection was
INFEASIBLE, ZAAD abstained with "no verified feasible incumbent" and the cells ended at review 0.
Change: the rule respects hard feasibility only (eligible lanes and destinations, minimum life at
receipt, receipt life, weight cap) and stays naive about sellable life (it counts physical units,
which is the comparison ZAAD exists to make). Accepted; recorded as the incumbent's definition.

## Entry 5 - first development run (`sector_dev1`, code `246080c`..`8b7aadc`)

26 / 26 fixtures pass the economic, service, structural and principle gates; 416 ZAAD reviews, p50
1.4 s, p95 8.7 s, max 60.0 s (C1 41002 r6), 1,829 OPTIMAL / 198 INFEASIBLE (floors provably
unattainable on a class) / 0 time-limited candidate solves.

Observations recorded, not tuned:

* **C1 (case packs) 54-60 s reviews.** Profile (`profiles/C1_41002_r6.json`): 58.6 s, of which the
  frozen service-frontier oracles (`solve(service_first=<service>)`, phase 2 = minimum cost subject to
  the phase-1 optimum within 1e-7) take 13.7 s and 42.9 s (time-limited at the 43 s budget, 319 k
  nodes) on a 1,274-variable model with 12 general-integer `case` columns; the decision candidates
  (deterministic, stochastic) solve in 1.2 s and 0.5 s. The oracle is report-only (the
  `service_frontier` block), frozen P0 code, and is exposed by integer purchase packs, not by the
  physics layer (the P2 fixture Q with lane packs showed the same class of time). Not changed:
  below the 180 s blocker, explained here, and a change would be a frozen-code change.
* **C5 (variable supplier arrival) service .79 / .76 with the incumbent retained on every review.**
  Replayed with the physics stripped (`sector_mode` None): decisions identical review for review, so
  the behaviour is the frozen P0 engine's under a one-period lead standard deviation with delays
  only, not a sector effect. The fixture's gate (not worse than the best baseline, no avoidable
  starvation) passes. Recorded as a frozen-engine property on this frame.
* **P3 (age at receipt) +1.67% against the isolated-chain baseline, inside 3%.** ZAAD buys local
  fresh units and expires fewer than the incumbent (principle PASS); the isolated chains, with no
  transfers to time, land cheaper on this seed pair.
* **M5 (chilled aging against service) +2.51%, inside 3%.**
* **X3 minimum branch service 0 on both ZAAD and the incumbent**: the frozen SKU's south service
  is unavoidable shortage (south cannot hold FROZEN); the gate uses the unavoidable-shortage rule.

## Entry 6 - vault and API, `43d769f`

Migration 017; both adapters carry the columns with provenance; `sector_mode` query parameter;
422 on malformed physics. Legacy vaults build identical requests (test). Accepted.

## Entry 7 - authoritative run and P2 under the sector code

See `SECTOR_PHYSICS_RESULTS.md` and `SECTOR_PHYSICS_PERFORMANCE.md`.

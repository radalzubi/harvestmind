# Three-sector physics engine: closeout

Branch `claude/zaad-sector-physics`, worktree `harvestmind-sectors`, parent `main` `ea1ed3a` (released P2
code `9c4ece7`). Frozen tags unchanged: `p0-frozen` = `2e30721`, `p1-frozen-product` = `f7e1e62`,
`p1-frozen` = `12db66c`, `p2-frozen-product` = `cab3849`, `p2-frozen` = `fa615ff`. Not merged, not pushed,
not deployed. Commits: `246080c` (sector physics on the frozen engine), `43d769f` (vault and API),
`8b7aadc` (fixtures, benchmark, invariants, profiler, tests), then the evidence commits carrying this
closeout.

## Verdict

**THREE-SECTOR PHYSICS ENGINE — PASS AND FROZEN LOCALLY.** Frozen product (runtime code) SHA `43d769f`
(`zaad/sectors`, the default-off hooks in `zaad/full` and `zaad/meio`, `api`, migration 017; the later
commits add scripts, tests and evidence only). Frozen evidence SHA: the commit that carries this file
(local tag `sector-physics-frozen`; product tag `sector-physics-frozen-product`). Tags are local;
nothing pushed. **Status: ENGINEERING VALIDATED on synthetic fixtures, not REAL-DATA VALIDATED.**

## One engine

No sector optimizer exists. `zaad/sectors` declares physics per SKU (sector, storage state, age at
receipt, minimum life at receipt and at sale, weight) and resolves it with the optional storage
states of locations and lanes into one read-only view that the frozen model, settlement,
continuation valuation, rule projection and report consult at a handful of points, every one behind
`physics is not None`. A legacy request resolves to None. Ownership stays P0 / P1 / P2; the report
gains a `physics` block with sector-language explanations. Details: `SECTOR_PHYSICS_ARCHITECTURE.md`,
audit of what already existed: `SECTOR_PHYSICS_EXISTING_CAPABILITIES.md`.

## Freeze criteria

| criterion | evidence | result |
|---|---|---|
| A one shared engine intact | no sector planner; hooks default-off; `resolve` None on legacy | PASS |
| B COMMERCIAL physics | C1-C7 pass economic, service, structural and principle gates | PASS |
| C PRODUCE physics | P1-P8 pass | PASS |
| D MEAT_SEAFOOD physics | M1-M8 pass | PASS |
| E mixed-sector fixtures | X1-X3 pass | PASS |
| F sector invariants | 19 / 19 (`SECTOR_PHYSICS_INVARIANTS.md`, the 21 required properties incl. benchmark conservation) | PASS |
| G P0 frozen behaviour | six-cell arm `sector_physics` 120 / 120 decision-identical to `router_cycle`; canonical cell 15 identical | PASS |
| H P1 frozen behaviour | B / T / Q / A twelve-review identity; 720 / 720 P1 invariants | PASS |
| I P2 frozen behaviour | P2 matrix re-run under the sector code: 20 / 20, 18 / 18, 344 / 344 ZAAD reviews decision-identical to the release record | PASS |
| J network conservation | residual <= 1e-9 on every ZAAD review of both benchmarks; invariant 12 | PASS |
| K FEFO symmetry performance not regressed | P2 runtime 0.5 / 6.5 / 14.5 s (record 0.5 / 6.6 / 14.6); invariant 06: no indicator between out-of-window cohorts | PASS |
| L API / workspace sector contract | migration 017, both adapters, `sector_mode` parameter, 422 on malformed physics; 5 workspace / API tests | PASS |
| M security / resource bounds | profiles <= SKUs, three-value state enum, frozen caps unchanged, unknown state / mode / SKU refused at the contract; bandit clean | PASS |
| N representative runtime bounded and documented | 416 reviews p50 1.4 s, p95 8.4 s, max 59.5 s; the one class near 60 s profiled and explained (`SECTOR_PHYSICS_PERFORMANCE.md`); none over 180 s | PASS |
| O full suite on the final candidate | 1,865 passed, 2 skipped (`gates/pytest_final.log`); ruff, mypy (71 files), bandit, `git diff --check` clean | PASS |
| P / Q / R Validation7 / Validation8 / holdout4 | untouched, unrun, unread | PASS |
| S no commercial solver | HiGHS only | PASS |
| T no P3 behaviour | no supplier portfolio, splitting, alternate-sourcing or contract logic added; the existing alternate-source candidates unchanged | PASS |

## What each sector got

* **COMMERCIAL**: the frozen P1 purchasing economics made operationally exact - whole cases,
  pallets and a shipment weight cap beside them, MOQ / MOV, import lead and its variability,
  storage capacity; dynamic cadence untouched. Principle: economic replenishment under real
  purchasing and import constraints.
* **PRODUCE**: sellable life (minimum remaining life at sale) as the central object; age at receipt
  per SKU and per source; minimum life at receipt for purchases and transfers; FEFO over sellable
  cohorts; expiry economics unchanged (disposal, lost value); terminal and continuation value fall
  with remaining life; transfer age never resets. Principle: the right amount of product, with
  enough life left to sell it.
* **MEAT_SEAFOOD**: storage state per SKU with no thaw / freeze transition; state-specific shelf
  life through the SKU's own life; location and lane eligibility as hard feasibility; the same lot
  and sellable-life rules. Principle: protect service without turning uncertainty into unnecessary
  aging, expiry and working capital.
* **MIXED**: per-SKU profiles in one request; physics of one SKU never touches another
  (invariant 11); shared capacity respected.

## Known limitations (recorded, not tuned)

* Gradual shrink before expiry, grade mixes and thaw / freeze transitions are not modelled
  (deferred; the audit records why).
* The legacy continuation slabs still credit every post-horizon cohort on a legacy request (the
  cohort-aware rows are sector-explicit to keep the P1 freeze identity); a legacy opening lot
  shorter than the slabs is over-credited exactly as before.
* The frozen service-frontier oracle spends up to 60 s on integer case packs (report-only).
* The frozen P0 engine under a one-period lead standard deviation (C5) retains the incumbent at
  service .77-.79; the behaviour is identical without the sector layer.
* The rule incumbent counts physical units (by design); a sellable-life-aware operator rule is not
  offered as a baseline.
* The unbounded whole-workspace canonical call (150 SKUs) is untouched by this phase.

## Untouched

Validation7, Validation8, holdout4; Network Twin #39; P3-P6; dashboard and website uplift.

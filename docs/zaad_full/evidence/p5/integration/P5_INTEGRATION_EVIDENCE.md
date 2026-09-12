# P5 shared-core integration — evidence (engineering evidence only; not released, not deployed)

| item | value |
|---|---|
| starting `main` | `50980fc` (docs-only above the production runtime) |
| production runtime | `6b58764`, tag `p4-performance-closure-runtime` (unmoved) |
| isolated P5 baseline | tag `p5-isolated-baseline` = `660e5fc` (`claude/zaad-atp-p5` on `50980fc`, pushed); re-run from that SHA: tests 9 / 9, fixtures 24 / 24 (`../benchmarks/p5_isolated_baseline`), adversarial 16 / 16 (record byte-identical) |
| integration branch | `claude/zaad-atp-p5`: product `b984543`, evidence `2c87fb0` (PR [#71](https://github.com/radalzubi/harvestmind/pull/71), not merged) |
| CI (once, on `2c87fb0`) | run 34708783613 green on every gate: ruff, gitleaks, security (bandit, pip-audit), mypy, docker build, frontend, zaad frozen regression, pytest 4 shards (integration, unit-core, unit-zaad-a, unit-zaad-b); CodeQL fails as on every prior release (code scanning not enabled on the private repository - environment defect, not a gate). The docs-only commit recording this line does not get a second run (cancelled for cost discipline) |
| untouched | `zaad/full/model.py`, P3 shared-order formulation, P4 information sets / node indexing, scenario probabilities, solver tolerances, sector physics, Validation7 / Validation8 / holdout4 (never accessed), historical tags, released evidence |

## Shared-state ownership

`docs/zaad_full/p5/P5_INTEGRATION.md` section 1. In one line each: physical -> usable -> sellable
(sector physics) -> unreserved (`Stock.reserved`, the only hard reservation; the frozen model plans
on `Stock.usable` which excludes it) -> allocatable ATP; no hard protection commitment exists (P0
protection is a service-level construct: reported as an overlay, `hard_reservation: false`);
`InboundTransfer` firm (fixed in the frozen model), `OpenPO` non-firm (drawn per world) and never
promised; `inbound_confidence` != 1 refused; DIRECT vs ALTERNATIVE_SHIP_FROM (priced with the P2
lane, no transfer created, `p2_transfers_created: 0`, blocked supply named); one PROPOSED
reservation per shipment traceable to customer / order / line / SKU / lot / location / period.

## Economic-ledger ownership

`P5_INTEGRATION.md` section 2: seven keys, each with a per-unit state, a basis and an owner
(`lost_sales_opportunity` = frozen settlement convention `selling_price` or a declared margin,
labelled; `sla` = frozen `Service.sla_per_unmet`; `shortage_penalty`, `backorder_carry`,
`refusal` = P5 declarations on their own keys; `substitution` = frozen `Substitute` fee;
`alternative_ship_from` = frozen P2 lane price). Double-count proof: one state per unit, keys
disjoint by state, ledger total = objective (I17, invariant 13). Not priced by ownership: holding,
handling, financing, asset movements (planner ledger; never summed with the P5 ledger).

## Integration architecture

`P5_INTEGRATION.md` section 3: `zaad/atp/integration.atp_block` is the single orchestration used by
the planner hook (after the frozen P0-P4 report; `protection` overlay), `/jobs`, `plan_network`, the
standalone endpoint and the workspace path (`atp=True`, migration 020 adapter). API gate
`ZAAD_ATP_ENABLED` (default off): 422 `atp_disabled` on `/plan`, `/jobs`, from-workspace; 404 on the
standalone endpoint; 413 bounds; 403 tenant mismatch; nothing persisted; `approval_required: true`,
`executable_promise: false`.

## Fixture results

* Integration matrix I01-I20 (pre-registered in `P5_PREREGISTRATION.md`): **20 / 20**
  (`p5_integration.md/.json`); engine fixtures three runs identical; I01 planner path (frozen report
  identical with and without the block; overlay rows north / south promised 150 / 150,
  `below_protection_units` = P0 `protection_units` 21.77 / 22.79, central untouched); I20 identical to
  `enabled: false` and to the pre-P5 runtime `6b58764` (deploy checkout, timing and hashes stripped);
  I19 API: 422 `atp_disabled` / 404 with the flag off, 403 / 403 / 403 for the other tenant.
* Isolated matrix A-V on the integrated engine: **24 / 24** (`../benchmarks/p5_integrated`), three
  runs identical.
* Tie rules made explicit on first runs (dev log): home location first among equal-cost direct
  channels (I02), indifference keyed on declared numbers (I15), FEFO among cohorts (I04).

## Invariant results

`P5_INTEGRATION_INVARIANTS.md` (integration matrix) and `../P5_INVARIANTS.md` (isolated matrix):
invariants 1-19 pass on every recommendation; 20 (disabled-path identity) by I20 and
`tests/unit/test_zaad_atp.py::test_disabled_path_is_frozen` /
`tests/unit/test_zaad_atp_integration.py::test_disabled_path_reaches_no_p5_code_inside_the_planner`.

## Adversarial results

`../P5_ADVERSARIAL.md`: **17 / 17** fail closed (the 16 registered cases plus "probabilistic inbound
(confidence factor)" refused at the contract).

## Frozen regression results

One pass on the candidate `b984543` (`gates/`, chain identical to the P4 performance closure's, arm
`p5_integration` added to `scripts/p1_p0_arms.py`); every gate green, no rerun needed:

| gate | result |
|---|---|
| P3 shared-MOV production snapshot (P5 absent) | 11.96 s local, 18 HiGHS calls, decision view and candidates identical to the P4 closure record (timing stripped), no `atp` block |
| P1 canonical B / T / Q / A + P0 cell 15 | CANONICAL REGRESSION PASS; P1 invariants 720 checks, 0 failures |
| P2 | 20 / 20 fixtures, 18 / 18 principles, INVARIANTS PASS, 1,720 / 1,720 reviews identical vs `p2_perf_closure` (`p2_under_p5int`) |
| sector physics | 26 / 26, 19 / 19, 416 / 416 identical vs `sector_perf_closure` (`sector_under_p5int`) |
| P3 (current baseline) | 30 / 30, 34 / 34, 23 / 23 adversarial, 2,304 / 2,304 identical vs `p3_perf_closure` (`p3_under_p5int`; historical 2,273 / 2,304 + 31 proven ties unchanged) |
| P0 six-cell arm `p5_integration` vs `router_cycle` | 120 / 120 P0-owned reviews decision-identical (`p1/closure/p0_arm_p5_integration.json`) |
| P4 | unchanged code path; `tests/unit/test_zaad_recourse*.py` and the P4 release-audit tests inside the full suite (1,964 passed, 2 skipped) |

Released invariant / adversarial records the chain regenerates in place (`P2_INVARIANTS`,
`P3_INVARIANTS`, `P3_ADVERSARIAL`, `SECTOR_PHYSICS_INVARIANTS`) differed by timing and, in the P3 adversarial record, by the
validator's echo of the refused request dict (which now ends `'atp': None`); they were restored to
their released content; the `*_under_p5int` run records are kept beside the earlier
`*_under_p4perf` ones. P5-disabled requests preserve frozen behaviour by construction
(`resolve()` None -> no P5 code) and by measurement (I20, the P3 snapshot, every gate above).
Validation7, Validation8 and holdout4 were not accessed.

## Performance profile

`P5_PROFILE.md` (engine alone, scipy HiGHS, no performance work attempted):

| cell | rows | columns | binaries | channels | build s | solve s | first incumbent s | proof s | nodes | LP iterations | status | gap | promise wall s | peak RSS MB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5x1 lines, horizon 8, 1 location(s), firm inbound False | 9 | 21 | 1 | 15 | 0.0001 | 0.0073 | 0.0 | 0.01 | 1 | 2 | OPTIMAL | 0.0 | 0.006 | 117.0 |
| 20x2 lines, horizon 8, 1 location(s), firm inbound False | 60 | 171 | 11 | 120 | 0.0003 | 0.005 | 0.0 | 0.0 | 1 | 13 | OPTIMAL | 0.0 | 0.007 | 117.7 |
| 50x2 lines, horizon 8, 2 location(s), firm inbound True | 167 | 932 | 34 | 798 | 0.0012 | 0.0155 | 0.0 | 0.01 | 1 | 196 | OPTIMAL | 0.0 | 0.026 | 120.6 |
| 100x3 lines, horizon 12, 2 location(s), firm inbound True | 473 | 2815 | 109 | 2406 | 0.0043 | 0.0768 | 0.0 | 0.01 | 1 | 535 | OPTIMAL | 0.0 | 0.142 | 128.6 |
| 200x2 lines, horizon 26, 2 location(s), firm inbound True | 629 | 3751 | 149 | 3202 | 0.0108 | 0.1281 | 0.0 | 0.02 | 1 | 729 | OPTIMAL | 0.0 | 0.244 | 135.1 |
| 100x5 lines, horizon 26, 2 location(s), firm inbound True | 787 | 4709 | 189 | 4020 | 0.0073 | 0.1931 | 0.0 | 0.03 | 1 | 878 | OPTIMAL | 0.0 | 0.37 | 142.4 |

Every cell solves at the root node (nodes 1, first incumbent at 0.0 s, proof <= 0.03 s); the largest
declared cell inside the interactive bounds (500 lines, 26 periods, 2 locations, firm inbound) builds
in 0.007 s and solves in 0.19 s (787 rows, 4,709 columns, 189 binaries), the whole promise (incumbent
+ exact + pricing + report) in 0.37 s, peak RSS 142 MB. No change is proposed.

## Migration audit

Migration `020_atp_customer_orders.sql`: three new tables (`stg_atp_service_classes`,
`stg_atp_customer_orders`, `stg_atp_policy`), `CREATE TABLE IF NOT EXISTS` / `ADD COLUMN IF NOT
EXISTS`, nullable declaration columns only, no backfill, no allocation / promise / reservation
column (`test_migration_020_is_additive_and_idempotent`: a second `setup_db` run leaves the
information schema identical; no pre-020 table gains an `atp` column). The adapter attaches nothing
without rows; `inbound_confidence` in `stg_atp_policy` is accepted only at 1 by the contract.

## API / security audit

* Default off in every environment (`ZAAD_ATP_ENABLED`); flag off -> 422 `atp_disabled` on the
  planner paths before any model, 404 on the standalone endpoint (`test_planner_api_is_gated_bounded_and_tenant_checked`,
  `test_api_is_off_by_default_and_fails_closed`, I19).
* Same authentication as the planner; operator mismatch 403 on `/plan`, `/jobs`, `/atp/promise`.
* Bounds: contract envelope (4x interactive) at validation, interactive `INTERACTIVE_LIMITS`
  (200 orders / 500 lines / horizon 26 / 50 classes) -> 413 on `/plan`, from-workspace and the
  standalone endpoint; `/jobs` keeps the contract envelope.
* Payload caps unchanged (2 MiB interactive, 16 MiB jobs); malformed declarations 422
  `atp_invalid`; state refusals fail closed to a report-level `REFUSED` block inside `plan()` (the
  frozen plan is still returned) and 422 `atp_refused` on the standalone endpoint.
* Nothing is persisted or executed: `approval_required: true`, `executable_promise: false`,
  `executable_purchase_order: false`; reservations are PROPOSED only.
* Finding (not changed, P4 closed): `workspace_plan` passes `sourcing` but not `recourse` to the
  request builder (`api/routers/zaad_full.py`), so `recourse=true` is ignored on
  `POST /plan/from-workspace`; the P5 flag is passed by keyword so the released behaviour is unchanged.
* bandit (`-ll`, CI scope) clean; ruff (CI scope) clean; mypy (CI scope + `zaad/atp`) clean;
  gitleaks / pip-audit on CI.

## Known limitations

* P5 is a here-and-now promising layer: promises are not threaded through P4 information sets
  (interface documented, not built); no joint P2 movement + promising; no expedite / CTP on
  supplier capacity; substitution only through the frozen approved `Substitute` contract.
* The P0 overlay is available only on the planner path (the standalone endpoint has no protection
  profile); the overlay is informational, never a constraint.
* Non-firm supply (open purchase orders) is never promised, even when highly likely; the operator
  who wants it promised must have it declared as an accepted in-flight transfer.
* Requests built by `scene()` (history-less services) run the engine and the standalone endpoint
  but cannot be planned through the planner (forecast needs 16 observations) - engine fixtures only.
* Engineering evidence only: synthetic fixtures, no real-data validation, no commercial claim.

## Unresolved questions (for the release audit) - RESOLVED by `../release_audit/P5_RELEASE_AUDIT.md` (1: lost contribution basis; 2: `shortage_penalty_basis` fail-closed rule; 3: workspace `recourse` keyword fix; 4: unchanged, a known limitation)

1. Lost-sale basis: the P5 comparison charges the frozen key convention (gross selling price) and
   does not net the retained unit's asset value (the frozen ledger's net content through the asset
   keys). It changes magnitudes only where all-or-nothing / minimum-ship rules leave supply
   unshipped, never the order of service; a decision is needed on whether to add an asset-value
   credit or keep the declared-margin override as the only route.
2. Class `shortage_penalty` versus `Service.sla_per_unmet`: both are charged per unmet unit on
   separate keys; an operator who expresses one contractual penalty in both places would double it -
   the report shows both side by side per line; a validation rule (or a declared "replaces SLA"
   flag) is a release-audit decision.
3. `workspace_plan` drops the `recourse` flag (P4 plumbing, above): a one-line fix under its own
   authorization.
4. Whether P5 promises should feed back into the planner's usable stock within the same run
   (today: only after operator approval through `Stock.reserved`).

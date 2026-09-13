# ZAAD P5 ATP / scarce-supply allocation — release audit

| item | value |
|---|---|
| starting `main` | `50980fc` |
| production runtime | `6b58764` (tag `p4-performance-closure-runtime`, unmoved) |
| P5 isolated baseline | tag `p5-isolated-baseline` = `660e5fc` (unmoved) |
| audited head | `17d2d74` (PR #71: product `b984543` + evidence) |
| audit worktree / branch | `harvestmind-p5rel`, `release/p5-atp-release-audit` from `17d2d74` |
| holdouts | Validation7, Validation8, holdout4 not accessed |

## A. Lost-sale economics (audit and decision)

**Question.** The integration stage charged an unmet or refused unit at `Service.selling_price`
(the settlement's `lost_sales_opportunity` key convention). Is that the right economic quantity
for an allocation decision?

**Frozen facts.** (1) The settlement ledger charges `lost_sales_opportunity = need x selling_price`
per unmet unit AND carries the retained unit in `closing_assets` (at asset / terminal value); its
economic content per lost sale is therefore `selling_price - retained value + sla`, not the gross
price. (2) The frozen model and the settlement rank services for scarce stock by
`-(selling_price - asset_value)` (`zaad/full/model.py` `ordered_services`, `settlement.py`
allocation loop): contribution, not price, is the frozen allocation-ranking basis. (3) The
contract enforces `selling_price >= asset_value`, so contribution is never negative.

**Where the gross basis is wrong for P5 decisions.** Among lines of one SKU competing for the same
stock the two bases rank identically (the asset value cancels). They differ wherever a unit's
shipment is traded against another cost or against retaining the unit:
* an alternative ship-from at lane cost c: gross ships whenever `price + sla > c`, contribution
  ships only when `price - asset + sla > c` (R01 second part: lane 9 against 5 + 2.5 = 7.5 -> not
  shipped; the gross basis, 12.5, would pay 9 to earn 7.5);
* a declared margin against an undeclared line (R01 first part): under gross both read the full
  price and tie; under contribution the declared 2 ranks below the frozen 5;
* minimum-ship and all-or-nothing rules that leave stock unshipped (R02, R03): the retained units
  keep their asset value and stay in ATP - the gross basis overstates the loss by asset value x
  units and inflates the materiality denominator;
* substitution and lateness penalties compared against leaving a unit unmet (same mechanism).

**Decision.** P5 charges the **lost contribution**: `selling_price - asset_value` (the frozen
allocation-ranking basis) per unmet or refused unit, unless the operator declares a line
`unit_margin` or a class `lost_margin_per_unit`, which replace it (declared basis, reported). The
gross selling-price figure is reported as `gross_lost_sales_opportunity` (information; the
settlement's key convention) and never enters the objective. The P5 ledger key is renamed
`lost_contribution` so it is not mistaken for the settlement's gross key; the settlement itself is
untouched (no frozen economics changed). Because a zero-contribution unit would otherwise be
economically indifferent to being served, a documented tie (`TIE_UNMET`, 1e-5 per unit, below any
declared economics) keeps accepted demand served whenever serving is otherwise free; a positive
lane cost, substitution fee or late penalty still wins over a zero contribution.

**Classification.** A **P5 semantic correction**: no P0-P4 economics change; every P5 fixture's
cost magnitude changes (asset value 5 per unmet unit on the fixture SKU); no allocation and no
materiality verdict changed on the 24 isolated or the 20 integration fixtures (tables below); the
cases where decisions differ are pre-registered as R01-R03 and pass under the corrected basis.
Retained-unit value assumption: asset value, as in the frozen ranking; for a cohort that cannot be
retained (expiring within the promise window with no later use) the operator declares the margin
(known limitation).

## B. SLA and shortage penalty (distinct economics, fail-closed provenance)

`Service.sla_per_unmet` is a stream-level contractual payment (the settlement adds it to
`payments`; the model prices it per unmet unit). `ServiceClass.shortage_penalty_per_unit` is a
class-level declared consequence with its own provenance. They are distinct terms when they name
distinct consequences (a customer SLA and, say, a board-declared strategic shortage cost) and a
double count when they name the same one. Rule implemented in the contract (`zaad/atp/contracts.py`,
migration 021 column `shortage_penalty_basis`):

* whenever a class penalty > 0 serves a line whose stream carries `sla_per_unmet` > 0, the class
  must declare `shortage_penalty_basis`; absent -> **refused** at the contract (R07 a, b);
* `ADDITIONAL_TO_SERVICE_SLA` needs a `reference` naming the distinct contract / policy and
  CONTRACT or OPERATOR_DECLARED provenance; on a CONFIGURED_ASSUMPTION or without a reference ->
  refused (R07 c, d); both terms are then charged on their own keys and the report shows both per
  line with the basis (R06);
* `REPLACES_SERVICE_SLA`: the class term stands in for the stream SLA on those lines; `sla` is 0
  for them and `sla_replaced_per_unit` is reported (R06 variant);
* SLA only (R04) and penalty only on streams without an SLA (R05) need no declaration.

The two keys are not merged. Fixture declarations that carried a class penalty on an SLA-bearing
stream (B, C, O, Q, R, I15-I18, the profile grid) now declare ADDITIONAL_TO_SERVICE_SLA with a
fixture policy reference (declaration update required by the new contract; principles unchanged).

## C. P4 workspace `recourse` plumbing

`POST /api/zaad/network/plan/from-workspace` passed `sourcing` positionally and dropped `recourse`.
Fix: every phase flag (`sector_mode`, `sourcing`, `recourse`, `atp`) is passed by keyword. No model,
node, information-set or non-anticipativity code touched. Proof: R16 (`recourse=false` and no flag
identical, `recourse=true` attaches the declared specification and the P4 block appears with
`review_periods` [3]) and R17 (`atp=true&recourse=true` carries both blocks; each alone carries
only its own); permanent test `test_workspace_plan_forwards_every_phase_flag_by_keyword` (planner
call stubbed; the real-solve proof is R16 / R17).

## Audit-case runs (intermediate runs preserved)

* Run 1 (`p5_release_audit_cases_run1_failed.*`): 16 / 18. R07: all four declarations were refused
  with the right message; the runner compared a message truncated at 220 characters against a
  phrase beyond the cut (runner defect, truncation removed). R01 second part: the registered state
  requested delivery at period 0 while the lane has a one-period lead, so the lane was unreachable
  for any economics (genuine fixture defect: the line now requests period 1, as fixture K does).
* Run 2 (`p5_release_audit_cases_run2_failed.*`): 17 / 18. R01 second part: with the lane at 6 the
  corrected engine shipped over it, correctly - an unmet unit costs contribution 5 + the frozen SLA
  2.5 = 7.5 > 6; the pre-registered pass condition omitted the SLA term that the pre-registration
  itself charges on unmet units, and at 6 the case did not separate the bases (gross 12.5 ships
  too). Genuine pre-registration arithmetic defect: lane cost re-registered at 9 (contribution 7.5
  does not ship, gross 12.5 would, declared margin 8 + 2.5 = 10.5 ships). No engine code changed
  between the runs; the audit also re-runs the 24 + 20 matrices after each correction.
* Run 3 (`p5_release_audit_cases.*`): **18 / 18** (R01: line b 50 / a 0 with `why` citing lost contribution 5.00 against 2.00; lane at 9 unused at contribution + SLA 7.5 with 50 unmet and `alternative_ship_from` 0, used at declared margin 8 + 2.5 = 10.5 with 50 via the lane; R16 226 s of real recourse plans; R18 identical to the pre-P5 runtime).

## Results

### Audit cases R01-R18

18 / 18 on run 3 (`p5_release_audit_cases.md/.json`); invariants 1-19 on every engine case; R16 /
R17 with real recourse plans on the workspace vault; R18 identical to the pre-P5 runtime `6b58764`.

### P5 matrices on the corrected engine

* isolated A-V: 24 / 24 (`../benchmarks/p5_release_audit`), three runs identical; costs fall by the
  asset value per unmet unit against `p5_integrated`, no verdict or allocation changed;
* integration I01-I20: 20 / 20 (`../integration/p5_integration_release_audit`), no verdict changed,
  I20 identical to `enabled: false` and to the pre-P5 runtime;
* adversarial: 18 / 18 (`../P5_ADVERSARIAL.md`; new: double shortage declaration, four refusals);
* invariants: 1-19 pass on every recommendation of every matrix; 20 by I20 / R18 and the tests;
* tests: `test_zaad_atp.py` 9, `test_zaad_atp_integration.py` 10 (incl. the workspace-flag test).

### Frozen regressions

One pass on the audit tree (`gates/`, chain identical to the P4 and P5-integration closures, arm
`p5_release` in `scripts/p1_p0_arms.py`), every gate green, no rerun:

| gate | result |
|---|---|
| P3 shared-MOV production snapshot (P5 absent) | 18 HiGHS calls, decision view and candidates identical to the P4 closure record (timing stripped), no `atp` block |
| P1 canonical B / T / Q / A + P0 cell 15 | CANONICAL REGRESSION PASS; P1 invariants 720 checks, 0 failures |
| P2 | 20 / 20 fixtures, 18 / 18 principles, INVARIANTS PASS, 1,720 / 1,720 reviews identical vs `p2_perf_closure` (`p2_under_p5rel`) |
| sector physics | 26 / 26, 19 / 19, 416 / 416 identical vs `sector_perf_closure` (`sector_under_p5rel`) |
| P3 (current baseline) | 30 / 30, 34 / 34, 23 / 23 adversarial, 2,304 / 2,304 identical vs `p3_perf_closure` (`p3_under_p5rel`; historical 2,273 / 2,304 + 31 ties unchanged) |
| P4 | unchanged code path (the workspace fix is API plumbing); recourse unit and release-audit tests inside the full suite; R16 / R17 real recourse plans |
| P5 isolated | 24 / 24 (`../benchmarks/p5_release_audit`) |
| P5 integration | 20 / 20 (`../integration/p5_integration_release_audit`), I20 identical to the pre-P5 runtime `6b58764` |
| P0 six-cell arm `p5_release` vs `router_cycle` | 120 / 120 decision-identical (`p1/closure/p0_arm_p5_release.json`) |
| full suite | 1,965 passed, 2 skipped, 0 failed (6 m 07 s) |

Released records the chain regenerates in place differed by timing and the validator's request echo
only and were restored; run records kept as `*_under_p5rel`. Validation7, Validation8, holdout4 not
accessed.

### Performance (engine profile, before -> after the basis correction; no performance work)

| cell | rows / columns / binaries | solve s | promise wall s | status | peak RSS MB |
|---|---|---|---|---|---|
| 5x1 lines, horizon 8, 1 location(s), firm inbound False | 9 / 21 / 1 | 0.0073 -> 0.0021 | 0.006 -> 0.002 | OPTIMAL, nodes 1, first incumbent 0.0 s | 115.2 |
| 20x2 lines, horizon 8, 1 location(s), firm inbound False | 60 / 171 / 11 | 0.005 -> 0.0048 | 0.007 -> 0.007 | OPTIMAL, nodes 1, first incumbent 0.0 s | 116.0 |
| 50x2 lines, horizon 8, 2 location(s), firm inbound True | 167 / 932 / 34 | 0.0155 -> 0.0159 | 0.026 -> 0.028 | OPTIMAL, nodes 1, first incumbent 0.0 s | 119.1 |
| 100x3 lines, horizon 12, 2 location(s), firm inbound True | 473 / 2815 / 109 | 0.0768 -> 0.0826 | 0.142 -> 0.154 | OPTIMAL, nodes 1, first incumbent 0.0 s | 127.3 |
| 200x2 lines, horizon 26, 2 location(s), firm inbound True | 629 / 3751 / 149 | 0.1281 -> 0.137 | 0.244 -> 0.261 | OPTIMAL, nodes 1, first incumbent 0.0 s | 133.4 |
| 100x5 lines, horizon 26, 2 location(s), firm inbound True | 787 / 4709 / 189 | 0.1931 -> 0.2014 | 0.37 -> 0.381 | OPTIMAL, nodes 1, first incumbent 0.0 s | 139.1 |

No material change (largest cell 0.19 -> 0.20 s solve, 0.37 -> 0.38 s promise wall; every cell root-node optimal).

### Migration audit

Migration 021 adds one nullable column (`stg_atp_service_classes.shortage_penalty_basis`) with
`ADD COLUMN IF NOT EXISTS`; a fresh database migrated twice has an identical information schema;
no pre-P5 table carries an `atp` column; no allocation / promise / reservation is stored
(`test_migration_020_is_additive_and_idempotent`, re-checked on the audit head).

### API / security audit

Unchanged from the integration audit (`../integration/P5_INTEGRATION_EVIDENCE.md`): default off in
the code (`ZAAD_ATP_ENABLED`), 422 `atp_disabled` / 404 with the flag off, same authentication,
403 on operator mismatch on `/plan`, `/jobs` and `/atp/promise`, 413 bounds, 422 `atp_invalid` /
`atp_refused`, nothing persisted, `approval_required: true`, `executable_promise: false`. Release
configuration: `fly.toml` `[env]` sets `ZAAD_ATP_ENABLED = '1'` for the production environment
(versioned in the product freeze); the P4 workspace flag defect is fixed (item C). bandit `-ll`,
ruff and mypy (CI scope + `zaad/atp`) clean; gitleaks and pip-audit on CI.

### CI

First run on the evidence freeze `6919379` (run 34723634159): ten gates green, the `unit-zaad-a`
pytest shard (`test_zaad_[a-r]*.py`, 71 minutes on the P5 integration run) cancelled by the
workflow's 90-minute job cap (not a test failure: every test that ran passed; the P5 planner-path
tests add about seven minutes on that runner). Remedy in the workflow only: the shard is split into
`[a-m]` and `[n-r]`; no timeout widened, no product file changed (the product freeze tree is
unchanged). The re-run on the resharded head is recorded in the release record below.

Second run on the resharded head `e33e027` (run 34727673056): green on every gate - ruff, gitleaks,
security (bandit, pip-audit), mypy, docker build, frontend, zaad frozen regression, pytest five
shards (integration, unit-core, unit-zaad-a `[a-m]`, unit-zaad-n `[n-r]`, unit-zaad-b). CodeQL fails
as on every prior release (code scanning not enabled on the private repository; environment defect,
not a gate, and every real gate above is green). The merge-triggered runs on `main` were cancelled
(cost discipline; the merged tree is identical to the tested head).

### Release record

| step | value |
|---|---|
| merge | PR #72 -> `main` `2fc7b50`; whole-tree hash `082470f` identical to the tested head `e33e027`; product paths identical to `p5-frozen-product` (`eacf3c3`, tree `dd064f3`) |
| deploy | from the clean detached checkout `harvestmind-deploy` at `2fc7b50` (0 status entries): Fly `zaad-api` v22, `registry.fly.io/zaad-api:canonical-2fc7b50` (digest `sha256:0e3f735f3c17...`), machine `0804e0dfd1e948` started, volume and 12 secrets unchanged (`release/fly_secret_names.txt`), env now carries `ZAAD_ATP_ENABLED=1` (`release/fly_deploy_v22.log`) |
| production smoke (`release/smoke_p5.py`, `smoke_p5_results.json`) | health 200; disabled path: frozen plan 200 without an `atp` key (RETAIN_INCUMBENT); standalone `/atp/promise`: B scarcity 200 ALLOCATION CHANGE RECOMMENDED (2 reservations, 0 transfers), I17 every unit state 200 with all seven ledger keys populated; refusals 422 `atp_invalid` (double shortage declaration), 422 `atp_absent`, 413 bounds; planner `/plan` with a block 200 (frozen decision RETAIN_INCUMBENT, `atp` block on the planner path, protection overlay 3 rows); tenant mismatch 403 on `/atp/promise`, `/plan`, `/jobs`; `/jobs` 202 -> DONE in 11 s with the block; every response `approval_required: true`, `executable_promise: false` |
| logs after the smoke (`release/fly_logs_after_smoke.txt`) | 0 x 5xx, 0 errors, 0 OOM; the two "Traceback" lines are the replaced v21 process's shutdown at the rolling deploy (SIGINT -> asyncio CancelledError, 07:29:27Z) before any request reached v22; the v22 process logged none; 39 x 200, 1 x 202, 3 x 403, 1 x 413, 2 x 422 |
| release tag | `p5-release-runtime` -> `2fc7b50` (pushed); `p5-frozen-product` `eacf3c3`, `p5-frozen` `6919379`, `p5-isolated-baseline` `660e5fc`, `p4-performance-closure-runtime` `6b58764`, `p4-release-runtime` `8c813ac` and every older tag unmoved |


## Known limitations

* Retained-unit value is the asset value (frozen ranking basis); a cohort that cannot be retained
  (expires within the promise window with no later demand) is worth less - declare the margin.
* P5 substitution is penalty-governed in the optimiser (the frozen model's `direct_first` ordering
  is enforced by the incumbent policies, not as a hard rule in the exact allocation); the asset
  value difference between requested and supplied SKU is not priced (the declared `Substitute`
  penalty is the substitution economics).
* Promises are here-and-now (no P4 threading, no joint P2 movement, no CTP on supplier capacity);
  the P0 overlay exists on the planner path only; non-firm supply is never promised; P5 promises
  reach the planner's usable stock only after approval through `Stock.reserved`.
* Engineering evidence only: synthetic fixtures, no real-data validation, no commercial claim.

## Verdict

Every audit gate passed: the lost-sale economics are established (contribution basis, frozen
ranking convention, declared overrides, no silent change to frozen economics), the SLA / shortage
double declaration fails closed, the P4 workspace plumbing is fixed without touching P4 semantics,
R01-R18 18 / 18, the P5 matrices 24 / 24 and 20 / 20, adversarial 18 / 18, invariants 1-20, no
performance regression, migration additive and idempotent, API gated and tenant-isolated, P0-P5
frozen regressions identical in one pass, CI green once on the tested head, merge tree-identical,
deployed from a clean detached checkout, production smoke and logs clean, release tag created after
verification, no historical tag moved, P6 not started.

**ZAAD P5 RELEASE AUDIT — PASS.** Validation status unchanged: ENGINEERING VALIDATED, NOT REAL-DATA
VALIDATED.

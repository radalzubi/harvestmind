# HARDENING V1, H3b: actual operator-plan capture and shadow comparison

Branch `hardening/h3b-operator-plan-capture` from main `4ec15df` (H3a closed). Status: **implemented and
validated on synthetic data; NOT validated on real operator data.** Open for independent review; not merged.

## What H3b adds

- **Capture** (`api/product/operator_plans.py`, migration 031, `POST /api/zaad/shadow/plans`): an operator's
  intended purchasing plan for one planning origin, line by line (sku, supplier, destination where material,
  quantity, period, line reference) with a declared provenance from `OPERATOR_SUBMITTED`, `OPERATOR_UPLOADED`,
  `OPERATOR_CONFIRMED_DRAFT`. Any other origin is refused: a plan is never inferred from history, a rule, a
  Request's incumbent orders or a ZAAD proposal. Capability `createProposal` is required.
- **Immutable snapshot.** Lines are canonicalised (sorted by business key) and hashed (sha256 with the origin);
  every capture is a new version in an append-only table; identical content for the same origin returns the
  existing version (a retried request adds nothing); a correction must name the latest version and creates a
  superseding version, the old rows stay and only their status moves to SUPERSEDED. Reads recompute the hash
  and report `integrity = HASH_MISMATCH` on a tampered snapshot, which blocks readiness.
- **Shadow comparison** (`POST /api/zaad/shadow/plans/{id}/compare`, `zaad/full/shadow_plan.py`): ZAAD's
  recommendation for the plan's origin is produced exactly as before (synchronous planner run, or a finished
  planning job for the same origin), without the operator plan; both the captured plan (identified lines) and
  ZAAD's recommended buys are then settled as fixed solutions on the planner's own selection worlds (same fits,
  seed and draw, no terminal credit) and the cost breakdown and expected service of each are reported with the
  difference. The result is stored once with the plan version, content hash, request fingerprint, recommendation
  source and exposure instant. Capability `runPlanner` is required.
- **Quantities kept apart:** recorded plan units, identified plan units (lines mapped to one source), model-
  evaluated plan units, ZAAD units, unidentified lines, out-of-scope lines; each line carries its H3a identity
  fidelity. The planner's own decision reference is reported unchanged and separately.
- **Contract** (`zaad/full/comparator.py`): `shadow_readiness` and `shadow_comparison` implement the reserved
  `ACTUAL_OPERATOR_PLAN` comparator and `SHADOW_COMPARISON_MODE`. READY needs: a declared provenance, a verified
  hash, the same planning origin, capture strictly before the recommendation's exposure, and every line identified
  exactly. CONDITIONAL: a superseded version, unidentified lines (INCOMPLETE) or a plan the settlement could not
  score as recorded (TRANSFORMED): `can_claim_shadow_difference` is then false. NOT_READY_FOR_THIS_DECISION:
  no plan, capture at or after exposure, another origin, unestablished provenance, hash mismatch.
  `can_claim_realized_value` is always false here; realized value stays with the V2 outcome contract.
- **Synchronous and asynchronous provenance:** `refine_report` applies the workspace build's rule provenance to
  a planner report from either path, so a job report and a synchronous report carry the same
  `decision_reference` in a shadow comparison.

## Corrective pass (independent review of 2e738e0)

- **Explicit supersession.** A changed plan for an origin that already has a version must name the latest
  version in `supersedes`; missing, stale or wrong ids are refused; a first capture may not name one; an identical
  retry stays idempotent. The new version is written in a transaction and the schema's UNIQUE (operator, origin,
  version) and UNIQUE (operator, origin, content hash) constraints decide a race: two corrections of one version
  cannot both land, whatever each read first (the loser gets a refusal, nothing of it remains). Status is derived
  from whether a later version exists; no row is ever updated. A failed write rolls back head and lines together.
- **Planning-problem identity for job baselines.** A `baseline_job_id` is accepted only when the job's
  `information_hash` (the planner's sha256 of the full Request JSON: origin, SKU and source scope, horizon and
  period, service targets, inventory and pipeline state, supplier terms, scenario settings, seed and solve budget)
  equals the fingerprint of the request built now for the plan's origin with the same parameters. A different
  origin, missing fingerprint, unfinished job or any other difference is a 409 refusal, never a silent proceed.
- **Exposure timing.** `exposed_at` is the earliest recorded instant a recommendation for the origin was
  accessible: the earliest finished planning job for that origin in the job store (whether or not it was
  referenced), or the earliest stored comparison for the plan family; a repeated comparison never moves it later,
  and client-supplied times never set it. Captures at or after it are NOT READY. Since the cross-route correction
  below, every synchronous recommendation route records its exposure in the vault's ledger before it answers, so a
  synchronous comparison can be verified too; READY requires every source (ledger coverage, complete job history,
  prior comparisons) to be established as complete, and is CONDITIONAL otherwise (compared and labelled, but not
  claimed as a pre-exposure shadow difference).
- **Other checks.** Non-finite quantities and periods outside 0..52 are refused; repeated lines with one business
  key and no distinguishing reference are refused rather than summed; lines beyond the horizon and plans the
  settlement cannot score as recorded (for example a quantity that violates a declared case multiple) are
  CONDITIONAL with no shadow claim; integrity also checks the stored line count; the job path tolerates a service
  without a job store only for synchronous comparisons.

## Tests

- `tests/unit/test_operator_plan_capture.py` (13): explicit supersession (missing, stale, wrong, first-capture), concurrent
  corrections through the constraint (barrier-synchronised writers on separate cursors), rollback after a failed line write,
  non-finite and out-of-range inputs, repeated lines, unverified exposure, lines beyond horizon and unscorable plans; plus canonical hashing and idempotency; correction versions and
  intact old rows; validation and refused provenances; tampered snapshot blocks readiness; interleaved captures
  with retries; mapping by supplier and destination (never SKU alone, no guessing in a network); multi-line
  plans; readiness matrix and permissions; transformed and not-ready contracts; a bare incumbent order set is
  still not an operator plan.
- `tests/integration/test_shadow_comparison_api.py` (6, SYNTHETIC sample): job path READY with matching fingerprint; 409 refusals
  for horizon, service target, SKU scope, solve budget, origin, missing identity, unfinished job and changed workspace state;
  post-exposure correction NOT READY; exposure unchanged on repeat; synchronous run after a job inherits the job's exposure;
  unscorable plan CONDITIONAL; plus capture, retry, viewer refused,
  compare (READY / EXACT, quantities, modelled costs, stored record, reproducible figures); incomplete identity
  and superseded versions are CONDITIONAL; synchronous and job reports refine to identical provenance; a plan
  captured at or after exposure cannot be the baseline.
- `tests/integration/test_shadow_exposure_history.py` (4, real `JobStore`): the nine exposure-history cases listed under
  "Exposure-integrity correction".
- `tests/integration/test_shadow_exposure_routes.py` (9, real routes, vault ledger and `JobStore`): the cross-route cases
  listed under "Cross-route exposure correction".
- `tests/integration/test_shadow_exposure_provenance.py` (5, real registry, vault files, migration replay and routes):
  the new / upgraded / restored workspace cases listed under "Pre-migration coverage correction".

## Exposure-integrity correction (independent review of 4dc63e4)

**Original defect.** `earliest_job_exposure()` discovered the first exposure by iterating `store.list(operator,
limit=200)`: the 200 most recently created jobs, ordered by `created_at DESC`. An operator with more than 200 jobs
whose earliest finished job for the origin was older than that window had that exposure silently missed, and a plan
captured after it could be classified READY as a pre-exposure baseline. A listing failure was also read as "no
earlier exposure". Reproduced before the fix with the real `JobStore` (250 finished jobs for one origin, the oldest
created carrying the earliest finish): the bounded search returned the 51st-oldest job (finished 06:50) as the first
exposure instead of the oldest (06:00).

**Corrected contract.**

- `JobStore.earliest_done_for_origin(operator, as_of)` (`zaad/full/jobs.py`) is one SQL statement over the
  operator's rows (`WHERE operator = ? AND status = 'DONE'`, no `LIMIT`, no page, ordered by `finished_at`), so it
  examines every finished row the store holds and terminates with the table. It matches the report's `as_of` to the
  origin (SQLite `json_extract`, with a Python fallback when the JSON functions are absent) and returns the earliest
  match together with the scan's accounting: `scanned` finished rows and `unreadable` rows whose report, origin or
  finish stamp could not be assessed. The tenant boundary is the `WHERE` clause, as in `get` and `list`.
- `earliest_job_exposure()` (`api/routers/zaad_shadow.py`) returns an `Exposure` record: `JOB_FINISHED` when a
  finished job for the origin exists in a history established as complete, `NONE_RECORDED` when a complete history
  holds none, `UNVERIFIED` whenever completeness is not established (no job store configured, a store without the
  complete query, a store that raised, or any unreadable finished row). An exposure found in an incomplete history
  still counts as an exposure (it can make a plan NOT READY) but cannot verify anything. Missing records, a failed
  query, a partial scan or an unavailable store are never read as proof of no earlier exposure.
- A stored prior comparison's exposure is now split into what it **recorded** and what it **verified**
  (`operator_plans.first_exposure` returns both). The earliest recorded exposure always rules the exposure instant
  (a repeat can never move it later), but it is a `PRIOR_COMPARISON` basis only when a comparison established it from
  a complete job history; a synchronous run's own clock recorded by an earlier comparison stays `UNVERIFIED` however
  often it is repeated. This closes a second hole found while testing: two synchronous comparisons of the same plan
  would have promoted the first run's clock into a verified pre-exposure basis.
- **Record-loss detection.** When a comparison previously verified a job exposure for the plan family and the
  current complete scan finds no finished job at or before that instant, the store no longer holds records it once
  did (deletion, retention, or a different `ZAAD_JOB_STORE` file). The response marks
  `exposure.history.record_loss_detected`, the exposure instant keeps the earlier recorded value, and the basis is
  `UNVERIFIED`: READY is denied.
- Readiness: `UNVERIFIED` is CONDITIONAL (compared, labelled, no shadow-difference claim); capture at or after the
  exposure is NOT READY regardless of basis; READY requires a verified basis, so it is reachable only with a complete
  verified job history (or a prior comparison that had one, still consistent with the current scan).
- The response carries `exposure.history` (`complete`, `jobs_scanned`, `earliest_job_id`, `record_loss_detected`,
  `note`) so a reviewer can see what the classification rests on.

**Retention and deletion.** `zaad/full/jobs.py` has no delete or retention path: `reconcile()` only moves lapsed
non-terminal jobs to terminal states, and no code in the repository deletes job rows. The SQLite file named by
`ZAAD_JOB_STORE` is external configuration, so completeness is relative to that file: replacing or pruning it outside
the application is invisible to the scan except through record-loss detection, which needs a stored comparison to
have verified a job exposure for the family first. `finished_at` and `report_json` are written in the one update that
makes a job DONE (`_watch`), so the finish stamp is the first instant the recommendation was readable; the stamp of a
DONE row never changes afterwards.

**Adversarial evidence** (`tests/integration/test_shadow_exposure_history.py`, real `JobStore` throughout):

1. 250 finished jobs for the origin, earliest exposure on the oldest-created row: found (fails on 4dc63e4).
2. Multiple matches: the true earliest is selected, not the first listed.
3. Another operator's earlier finished job for the same origin is excluded.
4. An unfinished job, a FAILED job and a finished job for another origin do not count.
5. A finished row with an unreadable or missing report: the history is `UNVERIFIED`, the readable exposure is kept.
6. A store that raises, and a store without the complete query: `UNVERIFIED`, never "no exposure".
7. End to end: a plan captured after a hidden early exposure (older than 249 later jobs) is
   NOT_READY_FOR_THIS_DECISION with `can_claim_shadow_difference` false.
8. End to end: a plan captured before every finished job, with a complete verified history, is READY; a repeat keeps
   the identical exposure; one unreadable record withdraws READY to CONDITIONAL with the exposure unchanged; an
   offline store is CONDITIONAL with the reason in the response.
9. End to end: a store that no longer holds a previously verified job is flagged as record loss and denied READY; two
   synchronous comparisons with no job history stay CONDITIONAL and the second does not move the exposure later or
   gain a verified basis.

The earlier API tests keep their expectations (job-path READY with a matching fingerprint, 409 refusals, v2 after
exposure NOT READY, synchronous run inheriting a job's exposure, unscorable plan CONDITIONAL); the fake store used
there gained the complete query.

**Validation of the correction.** H3b unit and API tests, the new exposure-history tests and the H3a comparator tests
pass together (52); ruff, mypy and bandit with the CI arguments are clean; `scripts.zaad_canonical_regression`
PASS; `scripts.p1_invariants` 60/60 (regenerated evidence file restored, not committed); causal attestation 0
failures; `zaad_workspace_smoke 7 A_stable 3` completes with `executable_purchase_order: false`; the 2025-09-01
E_mixed_portfolio recheck is unchanged (pipeline 3000 / 3888 / 72, stock 5454 / 2208 / 204, all known before the
origin). No optimizer or planner mathematics changed; the full suite result is recorded in the PR.

**Remaining limitations after this pass** (the synchronous-route gap named here was closed by the cross-route
correction below). Record-loss detection is bounded by what stored comparisons verified; an externally pruned store
with no prior verified comparison for the family cannot be told from a complete one. Completeness is of the configured
stores, not of every place a recommendation could have been seen (for example a report exported and shared outside
the product).

## Cross-route exposure correction (independent review of e21c90a)

**Reproduced defect.** First exposure was established from completed jobs and stored comparisons only. A synchronous
recommendation through `/api/zaad/network/plan/from-workspace` left no record, so this sequence certified a
post-exposure plan: (1) the operator receives a synchronous recommendation for origin O; (2) captures a plan for O;
(3) a planning job for O finishes after the capture; (4) compares the plan with that job; (5) the complete job history
says the first exposure followed the capture and the comparison is READY. Reproduced on the real routes, vault and
job store (`test_a_synchronous_recommendation_before_capture_is_an_exposure`, READY on e21c90a, NOT READY now).

**Recommendation-route inventory** (every route or path that can return, store or expose a ZAAD recommendation):

| Route or path | Produces an actionable recommendation? | Exposure record |
|---|---|---|
| `POST /api/zaad/network/plan` (client-supplied Request) | yes, frozen planner, synchronous | ledger row `network_plan`, written before the response |
| `POST /api/zaad/network/plan/from-workspace` | yes, synchronous, origin derived from the vault | ledger row `network_plan_from_workspace` |
| `POST /api/zaad/network/shadow` (decision ledger) | yes, synchronous, stored in the SQLite decision ledger | ledger row `network_shadow_decision` with the decision id |
| `POST /fmcg/plan?mode=canonical` | yes, frozen planner, synchronous | ledger row `fmcg_plan_canonical` |
| `POST /api/zaad/shadow/plans/{id}/compare` without a job | yes, the comparison's own synchronous run | ledger row `shadow_compare` (plus the stored comparison) |
| `POST /api/zaad/network/jobs`, `GET /jobs/{id}` (WORKSPACE_PLAN) | yes, asynchronous; readable from the DONE transition | SQLite job store, complete operator scan on `finished_at` |
| `POST /api/zaad/orders/{draft}/evaluate` (PROPOSAL_BASELINE / OVERLAY jobs) | yes, two planner reports for the origin | same job store, same scan (purpose-agnostic) |
| `POST /api/zaad/plan`, `GET /api/zaad/demo` (superseded engine), `/fmcg/plan` non-canonical modes | yes, superseded engines behind `ZAAD_LEGACY_PLANNERS` (off outside dev) | not recorded: observing them reachable taints the vault's coverage for good |
| `POST /api/zaad/atp/promise` | no: a promising report, no purchase quantities | none |
| Analytics `planner.plan` (`api/analytics/query.py`) | no: a query planner for the semantic layer | none |
| Diagnostic report and its rolling replay (`api/routers/jobs.py`) | no: historical replay at past review dates, labelled non-actionable | none (see limitations) |
| `zaad/full/replay.py`, `zaad/meio/planner.py` | internal model execution reached only through the routes above | covered by the route that calls them |

**Exposure persistence.** Migration `032_recommendation_exposures.sql` adds two tables to the operator's DuckDB vault
(the H3b tables already live there, and every synchronous route holds the vault connection):
`zaad_recommendation_exposures` (append-only: operator, planning origin, route, request hash, reference, `exposed_at`
from the server clock) and `zaad_exposure_coverage` (one row: when this vault began recording, how it came to record,
the vault file a created vault was stamped for, and the first instant a superseded engine was observed reachable).
The migration replays on vault open and its insert is idempotent (`WHERE NOT EXISTS`); the pre-migration coverage
correction below says how a vault created under this schema is told from one upgraded to it. `ensure_exposure_tables`
creates the same tables lazily (source `LAZY`) when migration on open is disabled. Jobs stay in the SQLite job store
and are discovered by the complete scan of the previous correction; the two stores are read side by side, never
joined in one transaction.

**The point at which exposure becomes durable.** `zaad_full.expose()` runs after the planner has produced the report
and before the route returns it: `record_exposure` inserts the row (autocommit, the operator's vault) and the route
answers only once it has returned. If the insert raises, the route answers 503 `exposure_not_recorded` and withholds
the computed recommendation (`test_a_failed_exposure_write_withholds_the_recommendation`): nothing actionable leaves
unrecorded. For jobs the durable instant is the DONE transition, which writes `finished_at` and the report together.

**Race and persistence guarantees.** Both the capture stamp and the exposure stamp come from the server clock at
insert time; a client timestamp never sets either. READY needs `captured_at < exposed_at` strictly, so a tie is NOT
READY. A capture that lands before the exposure row could not have seen the recommendation, because the
recommendation is returned only after the row exists. Repeats append rows and the earliest row rules; concurrent
synchronous exposures (separate cursors) and a concurrent job completion all preserve the earliest instant
(`test_concurrent_synchronous_and_asynchronous_exposures_keep_the_earliest`); capture/exposure races never certify a
plan whose capture is not strictly earlier (`test_capture_and_exposure_races_never_certify_a_post_exposure_plan`).
Tenant isolation is the `operator_id` predicate on every read, as for plans and comparisons.

**Composition of sources** (`api/routers/zaad_shadow.py`). The exposure instant is the minimum over: this call's own
exposure (the job's `finished_at`, or the ledger row this run just wrote), the complete job scan, the ledger's
earliest row for the origin, and the earliest exposure any stored comparison of the plan family recorded. The basis
is VERIFIED (`JOB_FINISHED`, `RECOMMENDATION_LEDGER` or `PRIOR_COMPARISON`) only when every source is established as
complete: the job scan is complete, the ledger's coverage vouches for this plan (below), no superseded engine was ever
observed reachable, and no record loss is detected. Otherwise the basis is `UNVERIFIED` and the comparison is
CONDITIONAL, with the reasons in `exposure.history.note` and in the contract's caveats. An unverified source never
becomes verified because another source holds a later exposure: a prior comparison's exposure is a verified basis only
if that comparison was itself verified, and a stored comparison that verified a job exposure the current scan no
longer finds (or a verified exposure neither store holds) is record loss.

**Legacy history.** A recommendation served before a vault began recording is not in the ledger. The coverage row
makes the boundary explicit and the comparison refuses to verify across it: a plan captured before `coverage_since`
is UNVERIFIED, and a vault that existed before recording began is never verified at all (the pre-migration coverage
correction below replaced an earlier data-horizon rule that was unsound). Superseded engines are not instrumented: when any
instrumented route or comparison observes `ZAAD_LEGACY_PLANNERS` enabled it stamps the coverage row once, and from
then on the vault's history is never verified (switching the engines off later does not lift it), because an
unrecorded recommendation may have been served meanwhile for any origin.

**Adversarial evidence** (`tests/integration/test_shadow_exposure_routes.py`, real routes, vault and job store;
`ZAAD_LEGACY_PLANNERS=0` and a job store configured, as in production):

1. Synchronous recommendation, then capture, then a job finishing after the capture: NOT READY, basis the ledger.
2. A plan captured before every exposure is READY on the synchronous path and again with a later job; no realized
   value is claimable; the first exposure does not move.
3. Two synchronous recommendations for one origin keep the first as the exposure; a plan captured after is NOT READY.
4. Three concurrent synchronous exposures and a concurrent job completion: the comparison reports the minimum.
5. Capture and exposure racing on separate cursors: READY only when the capture is strictly earlier.
6. A failing ledger write: 503, recommendation withheld on `/plan/from-workspace` and `/fmcg/plan?mode=canonical`,
   nothing recorded.
7. Every synchronous route records before answering, with route label and reference, and the ledger's earliest row
   is the first route used.
8. Legacy history: a capture before coverage is UNVERIFIED, and an upgraded vault is UNVERIFIED for every origin
   (the provenance cases are in `test_shadow_exposure_provenance.py`, below).
9. Superseded engines reachable: UNVERIFIED on two comparisons with the exposure unchanged, and still UNVERIFIED
   after the engines are switched off (durable taint).
10. Another tenant's earlier recommendation for the same origin never counts.
11. A repeated comparison cannot launder UNVERIFIED into READY (also in `test_shadow_exposure_history.py`, step G).
12. Every response keeps `can_claim_realized_value` false and `realized_value.available` false.

The previous correction's cases (hidden early exposure beyond 200 jobs, unreadable records, store errors, record
loss) still pass; the earlier API tests now run with production settings and assert the verified synchronous path.

**Fail-closed behaviour.** No store, no complete job query, a raising store, an unreadable finished job, a ledger
write failure (recommendation withheld), coverage gaps, a reachable superseded engine, record loss, or an unverified
prior comparison each prevent READY; none is ever read as "no exposure".

**Remaining restrictions on READY, and limitations.** The diagnostic report's rolling replay shows what the optimizer would have decided at past review
dates; it is labelled historical and non-actionable and is not treated as exposure, so a plan captured for a past
origin after reading that report is not caught by this ledger (the contract's provenance rules, not the ledger,
govern whether such a plan is an intended plan at all). Exposure outside the product (an exported report shared by
other means) is not observable. The job-read route does not add ledger rows: the job's DONE instant is already the
earliest moment it was readable. No real operator plan has been captured; every figure is synthetic.

## Pre-migration coverage correction (independent review of 4a1e52c)

**Reproduced defect.** The cross-route correction inferred which planning origins an existing vault could have
served before migration 032 from the vault's data: origins up to the Monday after its latest order date at the
instant recording began were unverifiable, later origins were taken as never exposed. That inference is unsound.
`/api/zaad/network/plan` takes the whole Request from the caller, origin included, so a pre-migration recommendation
could have been served for any origin. Reproduced on a real registry-created vault
(`test_a_pre_migration_recommendation_for_a_future_origin_is_never_excluded`): orders ending at T; before migration
032 the raw route serves a recommendation for the origin three weeks past T (the pre-032 route records nothing);
migration 032 replays and recording begins; later orders arrive; the operator captures a plan for that origin; the
comparison's own run is recorded; the comparison was READY on 4a1e52c. It is CONDITIONAL now.

**Corrected contract: new versus upgraded workspaces.**

- **Created under recording (NEW).** `OperatorRegistry.create_operator` is the one path that creates a vault (the
  worker, the access routes, the seeding tools all call it). After `setup_db` applies the migrations it calls
  `stamp_vault_creation`, which marks the coverage row `CREATED` and binds it to the resolved path of the vault file,
  before the operator record exists and before any token could reach a route. Such a vault's whole life is under
  recording; its history can be verified and it keeps READY when every other gate passes
  (`test_a_workspace_created_under_recording_is_verified_and_ready_only_when_every_gate_passes`: READY on the
  synchronous and the job path, CONDITIONAL once superseded, NOT READY for a correction captured after exposure).
- **Upgraded (existed before recording).** A vault whose coverage row came from the migration's replay on open
  (`MIGRATION`) or from the lazy path (`LAZY`) existed before recording began. Nothing records what it served before,
  for any origin, so its history is never verified: UNVERIFIED, CONDITIONAL, no claim permission, for every origin
  and for ever. The vault's data plays no part in that judgement. Recording still works on such a vault (its ledger
  fills from the upgrade on), so NOT READY is still established when a recorded exposure precedes a capture
  (`test_an_upgraded_workspace_with_no_exposure_records_stays_unverified`). Genuine pre-migration evidence is kept
  where it exists: finished jobs in the SQLite store are found by the complete scan whatever their age, and a stored
  comparison's exposure still rules the instant; such evidence can only make a plan NOT READY, never READY.
- **Restored, copied or of unknown provenance.** A `CREATED` row names the file it was written for. When a
  connection knows its file (the product's vault connections carry the resolved path) and it is not that file, the
  vault is `RESTORED`: what was served to its operator elsewhere is in no record here, so it is UNVERIFIED
  (`test_a_restored_or_copied_vault_is_not_the_vault_it_was_created_as`, a created vault's file copied over another
  operator's vault). The classification never falls back to NEW on absence of evidence: any row that is not a
  `CREATED` row served from its own file is UPGRADED or RESTORED.

**Authoritative provenance mechanism, migration compatibility and replay.** The distinction rests on the creation
code path, not on the existence of the migration table: the migration's insert writes `MIGRATION` and only the
registry's creation step upgrades the row to `CREATED`. Migration 032 is additive (`CREATE TABLE IF NOT EXISTS`,
`ALTER TABLE ... ADD COLUMN IF NOT EXISTS` for the binding and taint columns, `INSERT ... WHERE NOT EXISTS`), so a
replay on every open changes nothing: provenance, coverage instant, binding and every ledger stamp survive repeated
replays, and an upgraded vault stays upgraded through them
(`test_repeated_migration_keeps_provenance_coverage_and_ledger_stamps`). The earlier draft's `max_order_date` column
is no longer created or read; a dev vault that has it keeps it, unused. No existing production data needs
remediation: every vault that exists today predates recording and is correctly UPGRADED; a vault created after this
deployment is NEW from creation.

**Test fixtures.** The in-memory vaults of the earlier H3b tests stand for registry-created vaults and call the same
`stamp_vault_creation` the registry calls; the provenance tests use the real registry, real vault files, the real
replay on open and the real routes.

**Limitations.** A vault restored in place, over its own file, under its own operator, is indistinguishable from the
original; exposures recorded after the backup are lost with it, and only the job-store record-loss check (for
previously verified job exposures) can notice. Existing workspaces never reach READY under this contract; that is the
honest consequence of their unrecorded past, not a defect to engineer around. The same-file binding is not checked
for a bare connection that does not know its file (tests, scripts); the product's connections always do.

## Deferred H3a limitations, evaluated for H3b

1. Duplicate PO-derived Request entity ids for multi-line POs open at the origin: does not affect plan capture or
   shadow comparison (plans are not purchase orders and are not injected into the Request). Deferred, unchanged.
2. Asynchronous jobs carrying `RULE_IN_REQUEST`: the shadow comparison refines any job report it uses, so the
   limitation does not reach H3b's output; the general job-read endpoint still returns the planner's own
   section. Deferred, unchanged.

## What this does not establish

No real operator plan has been captured; the fixtures are synthetic. The modelled difference is on simulated
worlds and is not a realized outcome. Frontend surfaces for capture and shadow results are not built.

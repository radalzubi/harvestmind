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
  and client-supplied times never set it. Captures at or after it are NOT READY. A synchronous run that has no
  recorded evidence of earlier exposure is `UNVERIFIED` and the comparison is CONDITIONAL (compared and labelled,
  but not claimed as a pre-exposure shadow difference), because earlier synchronous recommendations are not
  recorded. READY is therefore reachable only through the job path, and only when the operator's job history is
  established as complete (see "Exposure-integrity correction" below).
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

**Remaining limitations.** Synchronous `/plan/from-workspace` recommendations are still not recorded as exposures,
so a synchronous-only history can never be verified (by design: CONDITIONAL). Record-loss detection is bounded by
what stored comparisons verified; an externally pruned store with no prior verified comparison for the family cannot
be told from a complete one. Completeness is of the configured store, not of every place a recommendation could have
been seen (for example a report exported and shared outside the product).

## Deferred H3a limitations, evaluated for H3b

1. Duplicate PO-derived Request entity ids for multi-line POs open at the origin: does not affect plan capture or
   shadow comparison (plans are not purchase orders and are not injected into the Request). Deferred, unchanged.
2. Asynchronous jobs carrying `RULE_IN_REQUEST`: the shadow comparison refines any job report it uses, so the
   limitation does not reach H3b's output; the general job-read endpoint still returns the planner's own
   section. Deferred, unchanged.

## What this does not establish

No real operator plan has been captured; the fixtures are synthetic. The modelled difference is on simulated
worlds and is not a realized outcome. Frontend surfaces for capture and shadow results are not built.

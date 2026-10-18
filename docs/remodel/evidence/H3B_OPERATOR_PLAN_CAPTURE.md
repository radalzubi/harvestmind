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

## Tests

- `tests/unit/test_operator_plan_capture.py` (10): canonical hashing and idempotency; correction versions and
  intact old rows; validation and refused provenances; tampered snapshot blocks readiness; interleaved captures
  with retries; mapping by supplier and destination (never SKU alone, no guessing in a network); multi-line
  plans; readiness matrix and permissions; transformed and not-ready contracts; a bare incumbent order set is
  still not an operator plan.
- `tests/integration/test_shadow_comparison_api.py` (4, SYNTHETIC sample): capture, retry, viewer refused,
  compare (READY / EXACT, quantities, modelled costs, stored record, reproducible figures); incomplete identity
  and superseded versions are CONDITIONAL; synchronous and job reports refine to identical provenance; a plan
  captured at or after exposure cannot be the baseline.

## Deferred H3a limitations, evaluated for H3b

1. Duplicate PO-derived Request entity ids for multi-line POs open at the origin: does not affect plan capture or
   shadow comparison (plans are not purchase orders and are not injected into the Request). Deferred, unchanged.
2. Asynchronous jobs carrying `RULE_IN_REQUEST`: the shadow comparison refines any job report it uses, so the
   limitation does not reach H3b's output; the general job-read endpoint still returns the planner's own
   section. Deferred, unchanged.

## What this does not establish

No real operator plan has been captured; the fixtures are synthetic. The modelled difference is on simulated
worlds and is not a realized outcome. Frontend surfaces for capture and shadow results are not built.

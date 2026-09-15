-- 024: operating product V2 — deterministic evaluation identity and approval provenance.
--
-- Additive, nullable, idempotent. Nothing here touches the optimizer or any staging table.
--
-- Why these columns exist (Fable V1 audit, H1 and H2):
--
--   * `zaad_evaluations.draft_hash` — a content hash of what an evaluation actually evaluated
--     (the lines and the header fields the overlay reads). "Is this comparison still about the
--     order on the screen?" used to be answered by comparing timestamps, and approving, rejecting
--     or exporting a proposal bumped `updated_at`, so every approved proposal reported its own
--     comparison as out of date. A hash answers the question deterministically.
--   * `zaad_evaluations.workspace_version` — a hash over the staging tables' upload lineage at
--     evaluation time, so a comparison can also say "the data changed since" rather than only
--     "the proposal changed since".
--   * `zaad_draft_orders.approved_evaluation_id` — which evaluation an approval was made against,
--     and `approval_evaluation_state` — whether that evaluation was current, stale or absent when
--     the approver acted. An approval that does not say what it was looking at cannot be reviewed.

ALTER TABLE zaad_evaluations ADD COLUMN IF NOT EXISTS draft_hash VARCHAR;
ALTER TABLE zaad_evaluations ADD COLUMN IF NOT EXISTS workspace_version VARCHAR;
ALTER TABLE zaad_draft_orders ADD COLUMN IF NOT EXISTS approved_evaluation_id VARCHAR;
ALTER TABLE zaad_draft_orders ADD COLUMN IF NOT EXISTS approval_evaluation_state VARCHAR;  -- current | stale_acknowledged | none

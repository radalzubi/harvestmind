-- 025: Operating Product V2 — governance, the closed loop, outcomes.
--
-- Additive, nullable, idempotent. Nothing here touches the optimizer or any staging table.
--
-- Rules this schema keeps, on top of 023's three:
--
--   4. The audit log is append-only through every ordinary application path. Nothing in the
--      product deletes a row of it, and no endpoint offers to.
--   5. Nothing recorded here is a claim that ZAAD did something outside itself. An external status
--      is a person's statement that they placed, sent or received an order; an outcome is an
--      observation after an action, never an attribution.
--   6. Every object is owned by one operator, as before.

-- One row per user-created operational action: who did what to which object, from which state to
-- which, under which request id. `context` is a bounded JSON object of identifiers and short
-- labels — never a line's contents, a price, a dataset or a secret.
CREATE TABLE IF NOT EXISTS zaad_audit_log (
    audit_id            VARCHAR NOT NULL,
    operator_id         VARCHAR NOT NULL,
    actor               VARCHAR,
    actor_role          VARCHAR,
    object_type         VARCHAR NOT NULL,   -- draft | evaluation | export_profile | decision | outcome | setting | actor
    object_id           VARCHAR NOT NULL,
    action              VARCHAR NOT NULL,   -- created | edited | submitted | reopened | approved | rejected | evaluation_requested | exported | external_status | outcome_recorded | superseded | setting_changed | response_recorded | ...
    before_revision     INTEGER,
    after_revision      INTEGER,
    before_state        VARCHAR,
    after_state         VARCHAR,
    request_id          VARCHAR,
    context             VARCHAR,            -- JSON, bounded
    happened_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Workspace policy an administrator sets. Keys are an allowlist in api/product/governance.py.
CREATE TABLE IF NOT EXISTS zaad_workspace_settings (
    operator_id         VARCHAR NOT NULL,
    key                 VARCHAR NOT NULL,
    value               VARCHAR,
    updated_by          VARCHAR,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- A retried request must not act twice. The recorded response is replayed for 24 hours.
CREATE TABLE IF NOT EXISTS zaad_idempotency (
    operator_id         VARCHAR NOT NULL,
    key                 VARCHAR NOT NULL,
    path                VARCHAR NOT NULL,
    status_code         INTEGER,
    response            VARCHAR,            -- JSON, or base64 for a file
    media_type          VARCHAR,
    headers             VARCHAR,            -- JSON
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- The operator's response to a decision ZAAD produced. The decision itself is reproducible from
-- the job store (job id + decision id); this is what a person did about it, and why.
CREATE TABLE IF NOT EXISTS zaad_decision_responses (
    response_id         VARCHAR NOT NULL,
    operator_id         VARCHAR NOT NULL,
    job_id              VARCHAR NOT NULL,
    decision_id         VARCHAR NOT NULL,
    target_type         VARCHAR,
    target_id           VARCHAR,
    recommended         VARCHAR,            -- ZAAD's verb, as shown: KEEP | DEFER | BUY MORE | MOVE | ...
    status              VARCHAR NOT NULL,   -- REVIEWED | ACCEPTED | OVERRIDDEN | REJECTED
    reason_code         VARCHAR,            -- structured override reason, optional
    reason_text         VARCHAR,            -- free text, optional
    draft_id            VARCHAR,            -- the proposal created from this decision, if any
    information_hash    VARCHAR,
    as_of               VARCHAR,
    actor               VARCHAR,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- What was observed after an action. `source` says how: recorded by a person, or matched from the
-- operator's own receipts against the exported order's reference. Never an attribution.
CREATE TABLE IF NOT EXISTS zaad_outcomes (
    outcome_id          VARCHAR NOT NULL,
    operator_id         VARCHAR NOT NULL,
    draft_id            VARCHAR,
    decision_job_id     VARCHAR,
    decision_id         VARCHAR,
    metric              VARCHAR NOT NULL,   -- allowlist in api/product/governance.py
    value               DOUBLE,
    unit                VARCHAR,
    observed_at         TIMESTAMP,
    source              VARCHAR NOT NULL,   -- recorded | matched
    comparator_value    DOUBLE,             -- only with comparator_basis; what "realized savings" needs
    comparator_basis    VARCHAR,
    note                VARCHAR,
    actor               VARCHAR,
    recorded_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Product telemetry: an allowlisted event name and allowlisted identifier keys, nothing else.
CREATE TABLE IF NOT EXISTS zaad_telemetry (
    event_id            VARCHAR NOT NULL,
    operator_id         VARCHAR NOT NULL,
    actor               VARCHAR,
    name                VARCHAR NOT NULL,
    properties          VARCHAR,            -- JSON of allowlisted keys
    happened_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Optimistic concurrency and the closed loop on a proposal.
ALTER TABLE zaad_draft_orders ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
ALTER TABLE zaad_draft_orders ADD COLUMN IF NOT EXISTS external_status VARCHAR;      -- PLACED_EXTERNALLY | ACKNOWLEDGED | PARTIALLY_FULFILLED | FULFILLED | CANCELLED_EXTERNALLY
ALTER TABLE zaad_draft_orders ADD COLUMN IF NOT EXISTS external_reference VARCHAR;   -- the ERP or supplier reference the operator supplied
ALTER TABLE zaad_draft_orders ADD COLUMN IF NOT EXISTS external_updated_at TIMESTAMP;
ALTER TABLE zaad_draft_orders ADD COLUMN IF NOT EXISTS external_updated_by VARCHAR;

-- A supplier-specific profile can be the default for that supplier; one profile can be the
-- workspace default.
ALTER TABLE zaad_export_profiles ADD COLUMN IF NOT EXISTS is_default BOOLEAN DEFAULT FALSE;

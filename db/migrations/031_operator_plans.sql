-- HARDENING V1, H3b: an operator's actual purchasing plan, captured independently and before ZAAD's
-- recommendation is exposed, as an append-only, content-hashed snapshot. A correction is a new version
-- that supersedes the old one; no row is ever rewritten. The shadow comparison records which plan
-- version, which request fingerprint and which recommendation it compared.
CREATE TABLE IF NOT EXISTS zaad_operator_plans (
    plan_id             VARCHAR NOT NULL,       -- one id per captured version
    operator_id         VARCHAR NOT NULL,
    plan_key            VARCHAR NOT NULL,       -- the family a version belongs to (operator + planning origin)
    version             INTEGER NOT NULL,
    as_of               TIMESTAMP NOT NULL,     -- the planning origin the plan is for (period boundary)
    captured_at         TIMESTAMP NOT NULL,     -- when the snapshot was written (server clock, UTC)
    captured_by         VARCHAR,                -- the acting person
    provenance          VARCHAR NOT NULL,       -- OPERATOR_SUBMITTED | OPERATOR_UPLOADED | OPERATOR_CONFIRMED_DRAFT
    source_reference    VARCHAR,                -- the operator's own reference (an ERP export name, a draft id)
    content_hash        VARCHAR NOT NULL,       -- sha256 of the canonical line set
    line_count          INTEGER NOT NULL,
    status              VARCHAR NOT NULL,       -- CAPTURED | SUPERSEDED
    supersedes_plan_id  VARCHAR,
    note                VARCHAR,
    created_at          TIMESTAMP NOT NULL
);
CREATE TABLE IF NOT EXISTS zaad_operator_plan_lines (
    plan_id             VARCHAR NOT NULL,
    operator_id         VARCHAR NOT NULL,
    line_no             INTEGER NOT NULL,
    sku                 VARCHAR NOT NULL,
    supplier_id         VARCHAR,                -- may be absent: the line is then INCOMPLETE, never guessed
    destination_id      VARCHAR,
    quantity            DOUBLE NOT NULL,
    period              INTEGER NOT NULL DEFAULT 0,   -- planning period offset from as_of
    line_reference      VARCHAR
);
CREATE TABLE IF NOT EXISTS zaad_shadow_comparisons (
    comparison_id       VARCHAR NOT NULL,
    operator_id         VARCHAR NOT NULL,
    plan_id             VARCHAR NOT NULL,
    plan_version        INTEGER NOT NULL,
    plan_hash           VARCHAR NOT NULL,
    as_of               TIMESTAMP NOT NULL,
    request_hash        VARCHAR,                -- the Request fingerprint the recommendation rested on
    recommendation_source VARCHAR,              -- SYNC | JOB:<job_id>
    exposed_at          TIMESTAMP NOT NULL,     -- when ZAAD's recommendation became visible for this comparison
    status              VARCHAR NOT NULL,       -- DONE | FAILED
    result_json         VARCHAR,
    note                VARCHAR,
    created_at          TIMESTAMP NOT NULL
);

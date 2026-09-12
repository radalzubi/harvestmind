-- 019: adaptive recourse (P4). Additive, nullable, idempotent: an existing vault keeps every row it has.
-- One declaration row per operator: the review epochs, observables, actions and tolerances a planning
-- request attaches when it is built with recourse=true. Absent table or no row attaches nothing: the
-- adapter builds the frozen request. Solver nodes and information sets are never persisted.
CREATE TABLE IF NOT EXISTS stg_recourse_spec (
    operator_id             VARCHAR NOT NULL,
    enabled                 BOOLEAN DEFAULT FALSE,
    review_periods          VARCHAR,                       -- JSON list of review periods, e.g. '[2, 5]'
    observables             VARCHAR,                       -- JSON list: demand | receipts
    actions                 VARCHAR,                       -- JSON list: purchase | transfer
    demand_grid             DOUBLE,                        -- quantisation of realised demand per service per period (units)
    fill_grid               DOUBLE,                        -- quantisation of a confirmed fill fraction
    confirmation_lag        INTEGER,                       -- periods after landing before a receipt counts as confirmed
    continuations           INTEGER,                       -- futures per branch in the scenario tree
    perfect_information     BOOLEAN,                       -- report-only lower bound on or off
    provenance              VARCHAR,                       -- OPERATOR_DECLARED | CONFIGURED_ASSUMPTION
    declared_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE stg_recourse_spec ADD COLUMN IF NOT EXISTS _upload_session_id VARCHAR;
ALTER TABLE stg_recourse_spec ADD COLUMN IF NOT EXISTS _uploaded_at TIMESTAMP;
ALTER TABLE stg_recourse_spec ADD COLUMN IF NOT EXISTS _source_file VARCHAR;
ALTER TABLE stg_recourse_spec ADD COLUMN IF NOT EXISTS _operator_id VARCHAR;
COMMENT ON TABLE stg_recourse_spec IS 'Staging (P4): the operator''s declared adaptive-recourse specification. Declared data only; nothing is inferred; no solver node is stored.';

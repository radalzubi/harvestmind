-- 020: ATP / scarce-supply allocation (P5). Additive, nullable, idempotent: an existing vault keeps every
-- row it has. Declared customer orders and economic service classes a planning request attaches when it is
-- built with atp=true. Absent tables or no rows attach nothing: the adapter builds the frozen request.
-- No allocation, promise or reservation is ever persisted here; recommendations stay in the report.
CREATE TABLE IF NOT EXISTS stg_atp_service_classes (
    operator_id                  VARCHAR NOT NULL,
    class_id                     VARCHAR NOT NULL,
    provenance                   VARCHAR,                  -- OPERATOR_DECLARED | CONTRACT | CONFIGURED_ASSUMPTION
    reference                    VARCHAR,
    contractual_service_floor    DOUBLE,
    shortage_penalty_per_unit    DOUBLE,
    late_penalty_per_unit_period DOUBLE,
    refusal_cost_per_unit        DOUBLE,
    lost_margin_per_unit         DOUBLE,
    strategic                    BOOLEAN DEFAULT FALSE,
    tier                         VARCHAR,
    declared_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS stg_atp_customer_orders (
    operator_id                  VARCHAR NOT NULL,
    order_id                     VARCHAR NOT NULL,
    line_id                      VARCHAR NOT NULL,
    customer_id                  VARCHAR NOT NULL,
    service_class                VARCHAR NOT NULL,
    sku                          VARCHAR NOT NULL,
    quantity                     DOUBLE NOT NULL,
    minimum_ship_quantity        DOUBLE,
    order_period                 INTEGER,                  -- <= 0, relative to the planning origin
    requested_period             INTEGER,                  -- >= 0
    ship_from                    VARCHAR,                  -- JSON list of eligible locations; NULL = the service's location
    unit_margin                  DOUBLE,
    partial_fulfillment_allowed  BOOLEAN,
    backorder_allowed            BOOLEAN,
    max_backorder_periods        INTEGER,
    substitution_allowed         BOOLEAN,
    late_semantics               VARCHAR,                  -- ACCEPT_LATE | CANCEL_IF_LATE
    priority_provenance          VARCHAR,
    declared_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS stg_atp_policy (
    operator_id                  VARCHAR NOT NULL,
    incumbent_policy             VARCHAR,
    manual_sequence              VARCHAR,                  -- JSON list of order ids (DECLARED_MANUAL)
    fairness                     VARCHAR,
    include_inbound              BOOLEAN,
    inbound_confidence           DOUBLE,
    promise_horizon              INTEGER,
    cross_location               BOOLEAN,
    provenance                   VARCHAR,
    declared_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE stg_atp_customer_orders ADD COLUMN IF NOT EXISTS _upload_session_id VARCHAR;
ALTER TABLE stg_atp_customer_orders ADD COLUMN IF NOT EXISTS _uploaded_at TIMESTAMP;
ALTER TABLE stg_atp_customer_orders ADD COLUMN IF NOT EXISTS _source_file VARCHAR;
ALTER TABLE stg_atp_customer_orders ADD COLUMN IF NOT EXISTS _operator_id VARCHAR;
COMMENT ON TABLE stg_atp_customer_orders IS 'Staging (P5): declared customer order lines for promising. Declared data only; no allocation or reservation is stored.';

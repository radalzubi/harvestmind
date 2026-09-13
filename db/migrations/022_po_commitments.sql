-- 022: P4B V1 open PO / commitment intervention. Additive, nullable, idempotent. Declared commitment terms per
-- open order (stg_po_commitments) and declared amendment options (stg_po_options) a planning request attaches
-- when it is built with commitments=true. Absent tables or no rows attach nothing: every open order stays
-- KEEP-only (the released request). No amendment is ever executed or persisted here; recommendations stay in
-- the report and need operator approval. Amendment rights are never inferred from history.
CREATE TABLE IF NOT EXISTS stg_po_commitments (
    operator_id                  VARCHAR NOT NULL,
    po_id                        VARCHAR NOT NULL,
    stage                        VARCHAR,                  -- placed | ordered | confirmed | in_production | shipped | in_transit | arrived | delivered | received
    allow_split_amendments       BOOLEAN,
    minimum_remaining_quantity   DOUBLE,
    prepaid_per_remaining_unit   DOUBLE,
    deposit_refundable_fraction  DOUBLE,                   -- 0..1 share of the deposit refunded on amendment; 0 = sunk
    cancellation_status          VARCHAR,
    declared_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS stg_po_options (
    operator_id                  VARCHAR NOT NULL,
    po_id                        VARCHAR NOT NULL,
    option_id                    VARCHAR NOT NULL,
    action                       VARCHAR NOT NULL,         -- cancel | expedite | de_expedite | reschedule (keep is built from the order)
    due_offset_periods           INTEGER,                  -- arrival period under the option (relative to the planning origin)
    fee_per_unit                 DOUBLE,
    credit_per_unit              DOUBLE,                   -- refund / credit note per amended unit; bounded by the refundable deposit
    remaining_invoice_per_unit   DOUBLE,
    payment_offset_periods       INTEGER,
    max_quantity                 DOUBLE,
    deadline                     TIMESTAMP,                -- latest change date (required)
    allowed_stages               VARCHAR,                  -- JSON list of eligible stages
    contract_reference           VARCHAR,
    provenance                   VARCHAR,                  -- CONTRACT | OPERATOR_DECLARED (CONFIGURED_ASSUMPTION is refused for non-keep)
    declared_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE stg_po_options IS 'Staging (P4B): declared amendment options on open purchase orders. Declared data only; no amendment is executed or stored.';

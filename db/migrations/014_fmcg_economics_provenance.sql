-- Migration 014: commercially decisive inputs are OPERATOR data, not guesses.
ALTER TABLE stg_fmcg_skus ADD COLUMN IF NOT EXISTS contribution_margin DOUBLE;     -- per unit; if absent, margin is UNKNOWN
ALTER TABLE stg_fmcg_skus ADD COLUMN IF NOT EXISTS supplier_capacity_per_week DOUBLE; -- units the supplier can ship per week
ALTER TABLE stg_fmcg_skus ADD COLUMN IF NOT EXISTS service_class VARCHAR;           -- e.g. A_CRITICAL, B, C, SLA_CUSTOMER
ALTER TABLE stg_fmcg_skus ADD COLUMN IF NOT EXISTS manufacturer VARCHAR;
ALTER TABLE stg_fmcg_skus ADD COLUMN IF NOT EXISTS fixed_po_cost DOUBLE;

CREATE TABLE IF NOT EXISTS stg_fmcg_suppliers (
    supplier_id         VARCHAR NOT NULL,
    supplier_name       VARCHAR,
    route               VARCHAR,          -- shared-risk tag: port, road corridor, carrier
    manufacturer        VARCHAR,
    capacity_per_week   DOUBLE,           -- units across all SKUs, if known
    lead_time_promised_weeks DOUBLE,
    imported_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    _upload_session_id  VARCHAR,
    _uploaded_at        TIMESTAMP,
    _source_file        VARCHAR,
    _operator_id        VARCHAR
);
COMMENT ON TABLE stg_fmcg_suppliers IS 'Staging: supplier master with shared-risk tags (route, manufacturer) and capacity.';

CREATE TABLE IF NOT EXISTS stg_fmcg_economics (
    key                 VARCHAR NOT NULL,   -- e.g. cost_of_capital_annual, storage_handling_annual, currency
    value               VARCHAR NOT NULL,
    provenance          VARCHAR DEFAULT 'operator',
    note                VARCHAR,
    imported_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    _upload_session_id  VARCHAR,
    _uploaded_at        TIMESTAMP,
    _source_file        VARCHAR,
    _operator_id        VARCHAR
);
COMMENT ON TABLE stg_fmcg_economics IS 'Staging: named economic parameters with provenance (carrying-cost components, penalties, currency).';

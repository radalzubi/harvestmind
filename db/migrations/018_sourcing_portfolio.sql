-- 018: sourcing portfolio (P3). Additive, nullable, idempotent: an existing vault keeps every row it has.
-- One row per approved SKU x supplier source option beyond the SKU master's primary supplier. Absent
-- table or NULL cells attach nothing: the adapter builds the frozen single-source request.
CREATE TABLE IF NOT EXISTS stg_fmcg_sources (
    sku                     VARCHAR NOT NULL,
    supplier_id             VARCHAR NOT NULL,
    approved                BOOLEAN DEFAULT TRUE,          -- operator-qualified source (FALSE = declared but not approved)
    compliance              VARCHAR DEFAULT 'cleared',     -- cleared | blocked | unreviewed
    unit_cost               DOUBLE,                        -- this supplier's price for the SKU (NULL = latest PO cost from this supplier)
    freight_per_unit        DOUBLE,
    handling_per_unit       DOUBLE,
    fixed_po_cost           DOUBLE,
    moq_units               DOUBLE,
    units_per_case          DOUBLE,
    capacity_per_week       DOUBLE,                        -- NULL = the supplier master's capacity, else PO history, else unbounded
    lead_time_promised_weeks DOUBLE,                       -- NULL = fitted from this supplier's closed orders, else the assumed lead
    age_at_receipt_days     DOUBLE,                        -- sector physics: life already elapsed on arrival from this source
    minimum_share           DOUBLE,                        -- declared contractual share limits of this source in the SKU's commitment
    maximum_share           DOUBLE,
    committed_units         DOUBLE,
    incumbent_share         DOUBLE,                        -- the operator's current share bought from this source (declared mix)
    switching_cost          DOUBLE,                        -- declared cost of starting to buy from this source
    provenance              VARCHAR,                       -- OPERATOR_DECLARED | DERIVED_FROM_OPERATOR_HISTORY | PHYSICAL_DEPENDENCY | PUBLIC_PRIOR | FALLBACK
    imported_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE stg_fmcg_sources ADD COLUMN IF NOT EXISTS _upload_session_id VARCHAR;
ALTER TABLE stg_fmcg_sources ADD COLUMN IF NOT EXISTS _uploaded_at TIMESTAMP;
ALTER TABLE stg_fmcg_sources ADD COLUMN IF NOT EXISTS _source_file VARCHAR;
ALTER TABLE stg_fmcg_sources ADD COLUMN IF NOT EXISTS _operator_id VARCHAR;
COMMENT ON TABLE stg_fmcg_sources IS 'Staging (P3): approved SKU x supplier source options, contractual shares, incumbent mix and switching costs. Declared data only; nothing is inferred.';

-- Shared physical risk of suppliers (P3): suppliers with the same risk_group share one supply shock.
ALTER TABLE stg_fmcg_suppliers ADD COLUMN IF NOT EXISTS risk_group VARCHAR;              -- e.g. 'plant_shanghai_2' (NULL = no declared dependency)
ALTER TABLE stg_fmcg_suppliers ADD COLUMN IF NOT EXISTS risk_group_kind VARCHAR;         -- MANUFACTURER | PLANT | PACKAGING | PORT | ROUTE | CARRIER | 3PL | UPSTREAM_FACILITY | OTHER
ALTER TABLE stg_fmcg_suppliers ADD COLUMN IF NOT EXISTS risk_group_provenance VARCHAR;   -- OPERATOR_DECLARED | DERIVED_FROM_OPERATOR_HISTORY | PHYSICAL_DEPENDENCY | PUBLIC_PRIOR | FALLBACK
ALTER TABLE stg_fmcg_suppliers ADD COLUMN IF NOT EXISTS switching_cost DOUBLE;           -- declared cost of starting to buy from this supplier (any SKU)

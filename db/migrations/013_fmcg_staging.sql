-- Migration 013: FMCG staging tables
-- Flat intake buffers for a shelf-stable distributor's exports, in EACHES.
-- No FK constraints; validated by ingestion/validators.py; read by
-- api/routers/fmcg.py to build a plan. Column names match the CSV
-- templates in data/samples/fmcg/.

CREATE TABLE IF NOT EXISTS stg_fmcg_skus (
    sku                 VARCHAR NOT NULL,
    sku_name            VARCHAR,
    category            VARCHAR,
    supplier_id         VARCHAR,
    unit_cost           DOUBLE,
    unit_price          DOUBLE,
    units_per_case      INTEGER,
    cases_per_layer     INTEGER,
    layers_per_pallet   INTEGER,
    order_multiple      VARCHAR DEFAULT 'case',
    moq_units           DOUBLE DEFAULT 0,
    shelf_life_days     INTEGER,
    abc_class           VARCHAR,
    imported_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE stg_fmcg_skus IS 'Staging: FMCG SKU master with pack structure and economics, in eaches.';

CREATE TABLE IF NOT EXISTS stg_fmcg_orders (
    order_id            VARCHAR,
    customer_id         VARCHAR,
    order_date          DATE NOT NULL,
    requested_delivery_date DATE,
    sku                 VARCHAR NOT NULL,
    qty_ordered         DOUBLE NOT NULL,
    qty_shipped         DOUBLE,
    channel             VARCHAR,
    imported_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE stg_fmcg_orders IS 'Staging: customer order lines. qty_shipped < qty_ordered is a recorded shortfall.';

CREATE TABLE IF NOT EXISTS stg_fmcg_purchase_orders (
    po_id               VARCHAR NOT NULL,
    po_date             DATE NOT NULL,
    supplier_id         VARCHAR,
    sku                 VARCHAR NOT NULL,
    qty_ordered         DOUBLE NOT NULL,
    unit_cost           DOUBLE,
    expected_delivery_date DATE,
    imported_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE stg_fmcg_purchase_orders IS 'Staging: purchase orders placed on suppliers.';

CREATE TABLE IF NOT EXISTS stg_fmcg_receipts (
    receipt_id          VARCHAR,
    po_id               VARCHAR NOT NULL,
    receipt_date        DATE NOT NULL,
    sku                 VARCHAR,
    qty_received        DOUBLE NOT NULL,
    qty_rejected        DOUBLE DEFAULT 0,
    imported_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE stg_fmcg_receipts IS 'Staging: supplier receipts against POs. Fill and lead time are derived from PO vs receipt.';

CREATE TABLE IF NOT EXISTS stg_fmcg_inventory (
    snapshot_date       DATE NOT NULL,
    sku                 VARCHAR NOT NULL,
    location_id         VARCHAR DEFAULT 'MAIN',
    on_hand             DOUBLE NOT NULL,
    in_transit          DOUBLE DEFAULT 0,
    imported_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE stg_fmcg_inventory IS 'Staging: inventory snapshots per SKU and location, in eaches.';

CREATE TABLE IF NOT EXISTS stg_fmcg_promotions (
    sku                 VARCHAR NOT NULL,
    week_start          DATE NOT NULL,
    uplift              DOUBLE NOT NULL,
    imported_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE stg_fmcg_promotions IS 'Staging: planned promotion calendar; uplift is a demand multiplier known at planning time.';

-- Lineage columns, as on every other staging table (migration 011): the
-- audit path from any number back to its upload.
ALTER TABLE stg_fmcg_skus            ADD COLUMN IF NOT EXISTS _upload_session_id VARCHAR;
ALTER TABLE stg_fmcg_skus            ADD COLUMN IF NOT EXISTS _uploaded_at TIMESTAMP;
ALTER TABLE stg_fmcg_skus            ADD COLUMN IF NOT EXISTS _source_file VARCHAR;
ALTER TABLE stg_fmcg_skus            ADD COLUMN IF NOT EXISTS _operator_id VARCHAR;
ALTER TABLE stg_fmcg_orders          ADD COLUMN IF NOT EXISTS _upload_session_id VARCHAR;
ALTER TABLE stg_fmcg_orders          ADD COLUMN IF NOT EXISTS _uploaded_at TIMESTAMP;
ALTER TABLE stg_fmcg_orders          ADD COLUMN IF NOT EXISTS _source_file VARCHAR;
ALTER TABLE stg_fmcg_orders          ADD COLUMN IF NOT EXISTS _operator_id VARCHAR;
ALTER TABLE stg_fmcg_purchase_orders ADD COLUMN IF NOT EXISTS _upload_session_id VARCHAR;
ALTER TABLE stg_fmcg_purchase_orders ADD COLUMN IF NOT EXISTS _uploaded_at TIMESTAMP;
ALTER TABLE stg_fmcg_purchase_orders ADD COLUMN IF NOT EXISTS _source_file VARCHAR;
ALTER TABLE stg_fmcg_purchase_orders ADD COLUMN IF NOT EXISTS _operator_id VARCHAR;
ALTER TABLE stg_fmcg_receipts        ADD COLUMN IF NOT EXISTS _upload_session_id VARCHAR;
ALTER TABLE stg_fmcg_receipts        ADD COLUMN IF NOT EXISTS _uploaded_at TIMESTAMP;
ALTER TABLE stg_fmcg_receipts        ADD COLUMN IF NOT EXISTS _source_file VARCHAR;
ALTER TABLE stg_fmcg_receipts        ADD COLUMN IF NOT EXISTS _operator_id VARCHAR;
ALTER TABLE stg_fmcg_inventory       ADD COLUMN IF NOT EXISTS _upload_session_id VARCHAR;
ALTER TABLE stg_fmcg_inventory       ADD COLUMN IF NOT EXISTS _uploaded_at TIMESTAMP;
ALTER TABLE stg_fmcg_inventory       ADD COLUMN IF NOT EXISTS _source_file VARCHAR;
ALTER TABLE stg_fmcg_inventory       ADD COLUMN IF NOT EXISTS _operator_id VARCHAR;
ALTER TABLE stg_fmcg_promotions      ADD COLUMN IF NOT EXISTS _upload_session_id VARCHAR;
ALTER TABLE stg_fmcg_promotions      ADD COLUMN IF NOT EXISTS _uploaded_at TIMESTAMP;
ALTER TABLE stg_fmcg_promotions      ADD COLUMN IF NOT EXISTS _source_file VARCHAR;
ALTER TABLE stg_fmcg_promotions      ADD COLUMN IF NOT EXISTS _operator_id VARCHAR;

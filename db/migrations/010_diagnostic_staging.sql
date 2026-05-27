-- Migration 010: Diagnostic staging tables
-- Five flat staging tables that accept messy operator CSV data directly.
-- No FK constraints — these are intake buffers, not normalized fact tables.
-- The diagnostic_metrics engine reads from these tables.
-- Column names match the CSV templates shipped in data/samples/.

CREATE TABLE IF NOT EXISTS stg_products (
    product_id              VARCHAR,
    product_name            VARCHAR NOT NULL,
    category                VARCHAR,
    unit                    VARCHAR DEFAULT 'kg',
    default_shelf_life_days INTEGER,
    traceability_required   BOOLEAN DEFAULT FALSE,
    imported_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE stg_products IS 'Staging: operator product list. Maps to dim_products but accepts incomplete/unconstrained data.';

CREATE TABLE IF NOT EXISTS stg_supplier_deliveries (
    delivery_id             VARCHAR,
    supplier_id             VARCHAR,
    supplier_name           VARCHAR,
    product_id              VARCHAR,
    product_name            VARCHAR,
    delivery_date           DATE,
    ordered_quantity        DOUBLE,
    delivered_quantity      DOUBLE,
    accepted_quantity       DOUBLE,
    rejected_quantity       DOUBLE,
    unit_cost               DOUBLE,
    quality_grade           VARCHAR,
    lot_id                  VARCHAR,
    imported_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE stg_supplier_deliveries IS 'Staging: supplier delivery history. accepted_quantity and ordered_quantity extend fact_deliveries with fuller commitment tracking.';

CREATE TABLE IF NOT EXISTS stg_inventory_lots (
    lot_id                  VARCHAR,
    product_id              VARCHAR,
    product_name            VARCHAR,
    supplier_id             VARCHAR,
    quantity_on_hand        DOUBLE,
    unit                    VARCHAR DEFAULT 'kg',
    arrival_date            DATE,
    expiration_date         DATE,
    warehouse_location      VARCHAR,
    quality_grade           VARCHAR,
    committed_quantity      DOUBLE DEFAULT 0,
    imported_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE stg_inventory_lots IS 'Staging: lot-level inventory. expiration_date + arrival_date drive ATP and near-expiry risk calculations.';

CREATE TABLE IF NOT EXISTS stg_buyer_orders (
    order_id                VARCHAR,
    buyer_id                VARCHAR,
    buyer_name              VARCHAR,
    product_id              VARCHAR,
    product_name            VARCHAR,
    order_date              DATE,
    delivery_date           DATE,
    requested_quantity      DOUBLE,
    fulfilled_quantity      DOUBLE,
    substituted_quantity    DOUBLE DEFAULT 0,
    sales_price             DOUBLE,
    required_quality_grade  VARCHAR,
    imported_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE stg_buyer_orders IS 'Staging: buyer order history. fulfilled_quantity vs requested_quantity drives shortage and fulfillment-risk metrics.';

CREATE TABLE IF NOT EXISTS stg_waste_adjustments (
    adjustment_id           VARCHAR,
    date                    DATE,
    product_id              VARCHAR,
    product_name            VARCHAR,
    lot_id                  VARCHAR,
    quantity_lost           DOUBLE,
    reason                  VARCHAR,
    estimated_value_lost    DOUBLE,
    imported_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE stg_waste_adjustments IS 'Staging: waste and spoilage log. estimated_value_lost drives waste-loss dollar calculation.';

-- Indexes for diagnostic query performance
CREATE INDEX IF NOT EXISTS idx_stg_deliveries_supplier ON stg_supplier_deliveries(supplier_id);
CREATE INDEX IF NOT EXISTS idx_stg_deliveries_product  ON stg_supplier_deliveries(product_id);
CREATE INDEX IF NOT EXISTS idx_stg_deliveries_date     ON stg_supplier_deliveries(delivery_date);
CREATE INDEX IF NOT EXISTS idx_stg_inventory_product   ON stg_inventory_lots(product_id);
CREATE INDEX IF NOT EXISTS idx_stg_inventory_expiry    ON stg_inventory_lots(expiration_date);
CREATE INDEX IF NOT EXISTS idx_stg_orders_product      ON stg_buyer_orders(product_id);
CREATE INDEX IF NOT EXISTS idx_stg_orders_buyer        ON stg_buyer_orders(buyer_id);
CREATE INDEX IF NOT EXISTS idx_stg_orders_delivery     ON stg_buyer_orders(delivery_date);
CREATE INDEX IF NOT EXISTS idx_stg_waste_product       ON stg_waste_adjustments(product_id);
CREATE INDEX IF NOT EXISTS idx_stg_waste_date          ON stg_waste_adjustments(date);

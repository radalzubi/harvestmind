-- Migration 002: Transactional fact tables
-- Orders from buyers and purchase orders to suppliers.

CREATE TABLE IF NOT EXISTS fact_orders (
    order_id            VARCHAR PRIMARY KEY,
    buyer_id            VARCHAR NOT NULL REFERENCES dim_buyers(buyer_id),
    order_date          DATE NOT NULL,
    week_start          DATE NOT NULL,           -- ISO week start (Monday)
    status              VARCHAR NOT NULL DEFAULT 'confirmed',
    notes               VARCHAR,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_order_status CHECK (status IN ('draft','confirmed','fulfilled','partial','cancelled'))
);

COMMENT ON TABLE fact_orders IS 'Buyer order headers. Join with fact_order_lines for SKU-level detail.';

CREATE TABLE IF NOT EXISTS fact_order_lines (
    line_id             VARCHAR PRIMARY KEY,
    order_id            VARCHAR NOT NULL REFERENCES fact_orders(order_id),
    product_id          VARCHAR NOT NULL REFERENCES dim_products(product_id),
    qty_ordered_kg      DOUBLE NOT NULL CHECK (qty_ordered_kg >= 0),
    qty_delivered_kg    DOUBLE CHECK (qty_delivered_kg >= 0),
    price_per_kg        DOUBLE CHECK (price_per_kg >= 0),
    grade               VARCHAR DEFAULT 'A',
    lost_sale_flag      BOOLEAN DEFAULT FALSE,
    lost_sale_reason    VARCHAR,                 -- 'stockout','quality','substituted','cancelled'
    delivery_date       DATE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE fact_order_lines IS 'SKU-level order lines. qty_delivered_kg NULL means not yet fulfilled.';

CREATE TABLE IF NOT EXISTS fact_purchase_orders (
    po_id               VARCHAR PRIMARY KEY,
    supplier_id         VARCHAR NOT NULL REFERENCES dim_suppliers(supplier_id),
    product_id          VARCHAR NOT NULL REFERENCES dim_products(product_id),
    po_date             DATE NOT NULL,
    week_start          DATE NOT NULL,
    qty_committed_kg    DOUBLE NOT NULL CHECK (qty_committed_kg >= 0),
    qty_received_kg     DOUBLE CHECK (qty_received_kg >= 0),
    price_per_kg        DOUBLE CHECK (price_per_kg >= 0),
    is_spot_purchase    BOOLEAN NOT NULL DEFAULT FALSE,
    spot_premium_pct    DOUBLE,                  -- % above contract price if spot
    contract_id         VARCHAR,                 -- references dim_contracts if applicable
    delivery_window_start DATE,
    delivery_window_end   DATE,
    grade_spec          VARCHAR DEFAULT 'A',
    status              VARCHAR NOT NULL DEFAULT 'open',
    notes               VARCHAR,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_po_status CHECK (status IN ('open','partial','complete','cancelled'))
);

COMMENT ON TABLE fact_purchase_orders IS 'Commitments to suppliers. is_spot_purchase=TRUE captures emergency buys for KPI tracking.';

CREATE TABLE IF NOT EXISTS dim_contracts (
    contract_id             VARCHAR PRIMARY KEY,
    supplier_id             VARCHAR NOT NULL REFERENCES dim_suppliers(supplier_id),
    buyer_id                VARCHAR,
    product_id              VARCHAR NOT NULL REFERENCES dim_products(product_id),
    season                  VARCHAR NOT NULL,    -- e.g. '2024-summer'
    contract_start          DATE NOT NULL,
    contract_end            DATE NOT NULL,
    min_vol_kg              DOUBLE DEFAULT 0,
    max_vol_kg              DOUBLE,
    contracted_price_per_kg DOUBLE,
    price_type              VARCHAR DEFAULT 'fixed', -- 'fixed','formula','market_minus'
    delivery_window_start   DATE,
    delivery_window_end     DATE,
    exclusivity_flag        BOOLEAN DEFAULT FALSE,
    penalty_per_kg_shortfall DOUBLE DEFAULT 0,
    payment_terms_days      INTEGER DEFAULT 30,
    grade_spec              VARCHAR DEFAULT 'A',
    notes                   VARCHAR,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_vol CHECK (min_vol_kg <= COALESCE(max_vol_kg, 1e12))
);

COMMENT ON TABLE dim_contracts IS 'Supplier contracts defining the feasible commitment space for the optimizer.';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_orders_buyer ON fact_orders(buyer_id);
CREATE INDEX IF NOT EXISTS idx_orders_week ON fact_orders(week_start);
CREATE INDEX IF NOT EXISTS idx_order_lines_order ON fact_order_lines(order_id);
CREATE INDEX IF NOT EXISTS idx_order_lines_product ON fact_order_lines(product_id);
CREATE INDEX IF NOT EXISTS idx_po_supplier ON fact_purchase_orders(supplier_id);
CREATE INDEX IF NOT EXISTS idx_po_week ON fact_purchase_orders(week_start);
CREATE INDEX IF NOT EXISTS idx_po_spot ON fact_purchase_orders(is_spot_purchase);
CREATE INDEX IF NOT EXISTS idx_contracts_supplier ON dim_contracts(supplier_id);
CREATE INDEX IF NOT EXISTS idx_contracts_product ON dim_contracts(product_id);

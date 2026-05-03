-- Migration 003: Operational fact tables
-- Deliveries, inventory snapshots, waste events, and logistics lanes.

CREATE TABLE IF NOT EXISTS fact_deliveries (
    delivery_id         VARCHAR PRIMARY KEY,
    po_id               VARCHAR REFERENCES fact_purchase_orders(po_id),
    supplier_id         VARCHAR NOT NULL REFERENCES dim_suppliers(supplier_id),
    product_id          VARCHAR NOT NULL REFERENCES dim_products(product_id),
    delivery_date       DATE NOT NULL,
    qty_received_kg     DOUBLE NOT NULL CHECK (qty_received_kg >= 0),
    qty_rejected_kg     DOUBLE NOT NULL DEFAULT 0 CHECK (qty_rejected_kg >= 0),
    rejection_reason    VARCHAR,                 -- 'quality','over_ripe','size','contamination','late'
    grade_received      VARCHAR DEFAULT 'A',
    lot_id              VARCHAR,                 -- references fact_lots for FSMA-204
    temp_on_arrival_c   DOUBLE,
    transit_hrs         DOUBLE,
    driver_id           VARCHAR,
    vehicle_id          VARCHAR,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_reject CHECK (qty_rejected_kg <= qty_received_kg)
);

COMMENT ON TABLE fact_deliveries IS 'Actual deliveries from suppliers. Rejection data feeds supplier_reliability_scorer.';

CREATE TABLE IF NOT EXISTS fact_inventory_snapshot (
    snapshot_id         VARCHAR PRIMARY KEY,
    snapshot_date       DATE NOT NULL,
    location_id         VARCHAR NOT NULL REFERENCES dim_locations(location_id),
    product_id          VARCHAR NOT NULL REFERENCES dim_products(product_id),
    lot_id              VARCHAR,
    qty_on_hand_kg      DOUBLE NOT NULL CHECK (qty_on_hand_kg >= 0),
    qty_committed_kg    DOUBLE NOT NULL DEFAULT 0,
    qty_available_kg    DOUBLE GENERATED ALWAYS AS (qty_on_hand_kg - qty_committed_kg) VIRTUAL,
    age_days            INTEGER,                 -- days since harvest or receipt
    days_remaining      INTEGER,                 -- shelf_life_days - age_days
    storage_temp_c      DOUBLE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE fact_inventory_snapshot IS 'Weekly inventory snapshot. age_days feeds perishability constraints in optimizer.';

CREATE TABLE IF NOT EXISTS fact_waste_events (
    waste_id            VARCHAR PRIMARY KEY,
    event_date          DATE NOT NULL,
    location_id         VARCHAR REFERENCES dim_locations(location_id),
    product_id          VARCHAR NOT NULL REFERENCES dim_products(product_id),
    lot_id              VARCHAR,
    qty_wasted_kg       DOUBLE NOT NULL CHECK (qty_wasted_kg > 0),
    waste_stage         VARCHAR NOT NULL,        -- 'pre_sale','post_sale','transit','cold_chain','quality'
    reason_code         VARCHAR NOT NULL,        -- 'over_commitment','shelf_life','quality_reject','cold_chain_failure','demand_miss'
    estimated_value_usd DOUBLE,
    salvage_recovered   DOUBLE DEFAULT 0,
    notes               VARCHAR,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_waste_stage CHECK (waste_stage IN (
        'pre_sale','post_sale','transit','cold_chain','quality','shrink'
    )),
    CONSTRAINT chk_reason CHECK (reason_code IN (
        'over_commitment','shelf_life','quality_reject','cold_chain_failure',
        'demand_miss','supplier_error','transport_damage','other'
    ))
);

COMMENT ON TABLE fact_waste_events IS 'Waste/spoilage events. reason_code enables planning-vs-execution attribution in backtest.';

CREATE TABLE IF NOT EXISTS dim_logistics_lanes (
    lane_id             VARCHAR PRIMARY KEY,
    origin_node         VARCHAR NOT NULL,        -- location_id
    destination_node    VARCHAR NOT NULL,        -- location_id
    node_type_origin    VARCHAR,
    node_type_dest      VARCHAR,
    distance_km         DOUBLE,
    transit_hrs         DOUBLE NOT NULL,
    vehicle_type        VARCHAR DEFAULT 'refrigerated_truck',
    cold_chain_flag     BOOLEAN DEFAULT TRUE,
    cost_per_kg         DOUBLE,
    capacity_kg_per_trip DOUBLE,
    days_operational    VARCHAR[],               -- ['mon','tue','wed','thu','fri']
    carrier             VARCHAR,
    notes               VARCHAR
);

COMMENT ON TABLE dim_logistics_lanes IS 'Available transport lanes. Used in optimizer network constraints and recourse routing.';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_deliveries_supplier ON fact_deliveries(supplier_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_date ON fact_deliveries(delivery_date);
CREATE INDEX IF NOT EXISTS idx_deliveries_product ON fact_deliveries(product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_date ON fact_inventory_snapshot(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_inventory_location ON fact_inventory_snapshot(location_id);
CREATE INDEX IF NOT EXISTS idx_waste_date ON fact_waste_events(event_date);
CREATE INDEX IF NOT EXISTS idx_waste_reason ON fact_waste_events(reason_code);
CREATE INDEX IF NOT EXISTS idx_lanes_origin ON dim_logistics_lanes(origin_node);

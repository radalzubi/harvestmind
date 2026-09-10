-- P2 network staging: locations, lanes and transfers for the multi-echelon workspace adapter.
-- Additive. A workspace without rows in stg_fmcg_locations (or with one) plans exactly as before.

CREATE TABLE IF NOT EXISTS stg_fmcg_locations (
    location_id         VARCHAR NOT NULL,
    kind                VARCHAR DEFAULT 'branch',          -- central_dc | regional_dc | branch | warehouse
    holding_annual      DOUBLE,                            -- annual holding rate at this location (fraction of unit value); NULL = workspace default
    capacity_units      DOUBLE,                            -- storage capacity in eaches; NULL = unbounded
    imported_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE stg_fmcg_locations IS 'Staging: network locations. One row per DC / branch / warehouse.';

CREATE TABLE IF NOT EXISTS stg_fmcg_lanes (
    lane_id             VARCHAR,
    origin_id           VARCHAR NOT NULL,
    destination_id      VARCHAR NOT NULL,
    sku                 VARCHAR,                           -- NULL = every SKU
    lead_days           INTEGER,                           -- NULL = inferred from stg_fmcg_transfers history, else a declared assumption
    cost_per_unit       DOUBLE,                            -- NULL = not declared (transfers priced at zero, with a warning)
    capacity_per_week   DOUBLE,                            -- NULL = a declared multiple of the destination's weekly demand
    units_per_pack      DOUBLE,                            -- NULL / 0 = continuous
    fixed_cost_per_dispatch DOUBLE,
    approved            BOOLEAN DEFAULT TRUE,
    imported_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE stg_fmcg_lanes IS 'Staging: transfer lanes between locations with their physics and economics.';

CREATE TABLE IF NOT EXISTS stg_fmcg_transfers (
    transfer_id         VARCHAR,
    lane_id             VARCHAR,
    origin_id           VARCHAR NOT NULL,
    destination_id      VARCHAR NOT NULL,
    sku                 VARCHAR NOT NULL,
    qty                 DOUBLE NOT NULL,
    dispatch_date       DATE NOT NULL,
    expected_arrival_date DATE,
    received_date       DATE,                              -- NULL = still in transit
    imported_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE stg_fmcg_transfers IS 'Staging: transfer history and open transfers. Lane lead is fitted from dispatch to receipt.';

ALTER TABLE stg_fmcg_orders ADD COLUMN IF NOT EXISTS location_id VARCHAR DEFAULT 'MAIN';
ALTER TABLE stg_fmcg_purchase_orders ADD COLUMN IF NOT EXISTS destination_id VARCHAR DEFAULT 'MAIN';

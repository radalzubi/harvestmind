-- Migration 001: Core dimension tables
-- Products, suppliers, locations, and buyers — the master data backbone.
-- All fact tables reference these via foreign keys.

CREATE TABLE IF NOT EXISTS dim_products (
    product_id          VARCHAR PRIMARY KEY,
    crop_name           VARCHAR NOT NULL,
    crop_category       VARCHAR NOT NULL,        -- 'leafy_green','tomato','pepper','root_veg','melon','herb','other'
    variety             VARCHAR,
    unit                VARCHAR NOT NULL DEFAULT 'kg',
    shelf_life_days     INTEGER NOT NULL CHECK (shelf_life_days > 0),
    cold_chain_required BOOLEAN NOT NULL DEFAULT TRUE,
    grade_levels        VARCHAR[] DEFAULT ARRAY['A','B','C'],
    gtin_14             VARCHAR(14),
    plu_code            VARCHAR(5),
    is_ftl_item         BOOLEAN NOT NULL DEFAULT FALSE,  -- FSMA-204 Food Traceability List
    usda_commodity_code VARCHAR,
    notes               VARCHAR,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_category CHECK (crop_category IN (
        'leafy_green','tomato','pepper','root_veg','melon','herb',
        'squash','berry','stone_fruit','citrus','allium','brassica','other'
    ))
);

COMMENT ON TABLE dim_products IS 'Master product catalog. is_ftl_item flags FSMA-204 Food Traceability List items requiring KDE capture.';

CREATE TABLE IF NOT EXISTS dim_suppliers (
    supplier_id         VARCHAR PRIMARY KEY,
    supplier_name       VARCHAR NOT NULL,
    supplier_type       VARCHAR NOT NULL DEFAULT 'farm',  -- 'farm','aggregator','wholesaler','importer'
    lat                 DOUBLE,
    lon                 DOUBLE,
    region              VARCHAR,
    county_fips         VARCHAR(5),
    state               VARCHAR(2),
    farmer_phone        VARCHAR,
    farmer_email        VARCHAR,
    fpo_id              VARCHAR,                -- Farmer Producer Organization if applicable
    gln                 VARCHAR(13),            -- GS1 Global Location Number
    gap_certified       BOOLEAN DEFAULT FALSE,
    gfsi_certified      BOOLEAN DEFAULT FALSE,
    primary_crops       VARCHAR[],
    total_ha            DOUBLE,
    irrigation_flag     BOOLEAN DEFAULT FALSE,
    avg_reliability     DOUBLE,                 -- 0-1, updated by supplier_reliability_scorer
    notes               VARCHAR,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_type CHECK (supplier_type IN ('farm','aggregator','wholesaler','importer','cooperative'))
);

COMMENT ON TABLE dim_suppliers IS 'Supplier master. avg_reliability is updated weekly by forecasting/supply/supplier_reliability_scorer.py.';

CREATE TABLE IF NOT EXISTS dim_locations (
    location_id         VARCHAR PRIMARY KEY,
    location_name       VARCHAR NOT NULL,
    location_type       VARCHAR NOT NULL,       -- 'hub','dc','farm','buyer','cold_storage'
    address_line1       VARCHAR,
    city                VARCHAR,
    state               VARCHAR(2),
    zip                 VARCHAR(10),
    lat                 DOUBLE,
    lon                 DOUBLE,
    gln                 VARCHAR(13),
    cold_storage_m3     DOUBLE,
    notes               VARCHAR,

    CONSTRAINT chk_loc_type CHECK (location_type IN ('hub','dc','farm','buyer','cold_storage','port','processor'))
);

COMMENT ON TABLE dim_locations IS 'Physical locations used in FSMA-204 CTEs and logistics routing.';

CREATE TABLE IF NOT EXISTS dim_buyers (
    buyer_id            VARCHAR PRIMARY KEY,
    buyer_name          VARCHAR NOT NULL,
    buyer_type          VARCHAR NOT NULL,       -- 'restaurant','institution','retail','foodbank','wholesale','distributor'
    location_id         VARCHAR REFERENCES dim_locations(location_id),
    region              VARCHAR,
    city                VARCHAR,
    state               VARCHAR(2),
    primary_contact     VARCHAR,
    phone               VARCHAR,
    email               VARCHAR,
    credit_terms_days   INTEGER DEFAULT 30,
    preferred_crops     VARCHAR[],
    tier                INTEGER DEFAULT 2 CHECK (tier IN (1,2,3)),  -- 1=anchor, 2=standard, 3=occasional
    avg_weekly_spend    DOUBLE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_buyer_type CHECK (buyer_type IN (
        'restaurant','institution','retail','foodbank','wholesale','distributor','hotel','school','hospital'
    ))
);

COMMENT ON TABLE dim_buyers IS 'Buyer master. tier=1 anchor buyers get priority in service-level constraints.';

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_products_category ON dim_products(crop_category);
CREATE INDEX IF NOT EXISTS idx_products_ftl ON dim_products(is_ftl_item);
CREATE INDEX IF NOT EXISTS idx_suppliers_region ON dim_suppliers(region);
CREATE INDEX IF NOT EXISTS idx_buyers_tier ON dim_buyers(tier);
CREATE INDEX IF NOT EXISTS idx_buyers_type ON dim_buyers(buyer_type);

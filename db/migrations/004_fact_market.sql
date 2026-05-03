-- Migration 004: Market and environmental data tables
-- USDA AMS prices, spot purchases, weather observations.

CREATE TABLE IF NOT EXISTS fact_market_prices (
    price_id            VARCHAR PRIMARY KEY,
    source              VARCHAR NOT NULL DEFAULT 'usda_ams',
    report_date         DATE NOT NULL,
    market_name         VARCHAR,                 -- e.g. 'Chicago Terminal Market'
    product_id          VARCHAR REFERENCES dim_products(product_id),
    commodity_code      VARCHAR,                 -- USDA commodity code
    grade               VARCHAR,
    unit                VARCHAR DEFAULT 'kg',
    low_price           DOUBLE,
    high_price          DOUBLE,
    avg_price           DOUBLE,
    volume_units        DOUBLE,
    currency            VARCHAR(3) DEFAULT 'USD',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE fact_market_prices IS 'USDA AMS terminal market prices. Used for spot price scenario generation.';

CREATE TABLE IF NOT EXISTS fact_spot_purchases (
    spot_id             VARCHAR PRIMARY KEY,
    event_date          DATE NOT NULL,
    week_start          DATE NOT NULL,
    product_id          VARCHAR NOT NULL REFERENCES dim_products(product_id),
    buyer_id            VARCHAR REFERENCES dim_buyers(buyer_id),
    supplier_id         VARCHAR REFERENCES dim_suppliers(supplier_id),
    qty_kg              DOUBLE NOT NULL CHECK (qty_kg > 0),
    unit_price_paid     DOUBLE NOT NULL,
    contract_price_ref  DOUBLE,                  -- what contract price would have been
    spot_premium_pct    DOUBLE GENERATED ALWAYS AS (
        CASE WHEN contract_price_ref > 0
             THEN (unit_price_paid - contract_price_ref) / contract_price_ref * 100
             ELSE NULL END
    ) VIRTUAL,
    urgency_reason      VARCHAR,                 -- 'shortage','quality_reject','demand_spike','contract_failure'
    was_avoidable       BOOLEAN,                 -- planner judgment flag
    notes               VARCHAR,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE fact_spot_purchases IS 'Emergency spot buys. spot_premium_pct is the core KPI for economic impact attribution.';

CREATE TABLE IF NOT EXISTS fact_weather_obs (
    obs_id              VARCHAR PRIMARY KEY,
    obs_date            DATE NOT NULL,
    location_id         VARCHAR REFERENCES dim_locations(location_id),
    county_fips         VARCHAR(5),
    station_id          VARCHAR,
    source              VARCHAR NOT NULL,        -- 'noaa_cdo','nws','nasa_power','open_meteo'
    tmax_c              DOUBLE,
    tmin_c              DOUBLE,
    tavg_c              DOUBLE,
    precip_mm           DOUBLE,
    heat_stress_flag    BOOLEAN DEFAULT FALSE,   -- tmax > 32C for most vegetables
    drought_monitor_cat VARCHAR,                 -- 'D0','D1','D2','D3','D4' (USDM)
    enso_oni_index      DOUBLE,                  -- Oceanic Niño Index (monthly, propagated weekly)
    gdd_base10          DOUBLE,                  -- Growing degree days base 10C
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE fact_weather_obs IS 'Historical and forecast weather. Feeds yield scenario generator and demand features.';

CREATE TABLE IF NOT EXISTS fact_yield_obs (
    yield_id            VARCHAR PRIMARY KEY,
    supplier_id         VARCHAR NOT NULL REFERENCES dim_suppliers(supplier_id),
    product_id          VARCHAR NOT NULL REFERENCES dim_products(product_id),
    harvest_week        DATE NOT NULL,           -- week_start of harvest
    planned_ha          DOUBLE,
    realized_yield_kg_per_ha DOUBLE,
    total_kg_harvested  DOUBLE,
    grade_a_pct         DOUBLE CHECK (grade_a_pct BETWEEN 0 AND 100),
    reject_pct          DOUBLE CHECK (reject_pct BETWEEN 0 AND 100),
    enso_phase          VARCHAR,                 -- 'el_nino','la_nina','neutral' at harvest
    drought_cat         VARCHAR,
    weather_note        VARCHAR,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE fact_yield_obs IS 'Historical yield realizations per supplier×product×week. Core input for supply scenario generation.';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_prices_date ON fact_market_prices(report_date);
CREATE INDEX IF NOT EXISTS idx_prices_product ON fact_market_prices(product_id);
CREATE INDEX IF NOT EXISTS idx_spot_week ON fact_spot_purchases(week_start);
CREATE INDEX IF NOT EXISTS idx_spot_product ON fact_spot_purchases(product_id);
CREATE INDEX IF NOT EXISTS idx_weather_date ON fact_weather_obs(obs_date);
CREATE INDEX IF NOT EXISTS idx_weather_county ON fact_weather_obs(county_fips);
CREATE INDEX IF NOT EXISTS idx_yield_supplier ON fact_yield_obs(supplier_id);
CREATE INDEX IF NOT EXISTS idx_yield_week ON fact_yield_obs(harvest_week);

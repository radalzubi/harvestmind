-- Migration 008: External data sources (USDA pricing + food-hub prospects)
-- Idempotent. Adds tables consumed by:
--   ingestion/usda_ams_connector.py        → fact_usda_prices
--   ingestion/usda_food_hub_directory.py   → dim_prospect_hubs

-- ── fact_usda_prices ────────────────────────────────────────────────────────
-- USDA Agricultural Marketing Service (AMS) terminal-market prices, pulled
-- from the MyMarketNews API. Distinct from fact_market_prices (which holds
-- our internal contract / spot prices) so the two can be reconciled.
CREATE TABLE IF NOT EXISTS fact_usda_prices (
    price_id          VARCHAR PRIMARY KEY,
    report_date       DATE NOT NULL,
    market_id         VARCHAR NOT NULL,         -- e.g. IL_MN250 (Chicago)
    market_name       VARCHAR,
    commodity         VARCHAR NOT NULL,         -- canonical commodity name
    commodity_code    VARCHAR,
    product_id        VARCHAR REFERENCES dim_products(product_id),
    grade             VARCHAR,
    package           VARCHAR,
    unit              VARCHAR DEFAULT 'kg',
    low_price         DOUBLE,
    high_price        DOUBLE,
    avg_price         DOUBLE,
    price_per_kg      DOUBLE,                   -- canonical $/kg (lbs converted)
    currency          VARCHAR DEFAULT 'USD',
    source            VARCHAR DEFAULT 'usda_mymarketnews',
    fetched_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_usda_prices_commodity ON fact_usda_prices (commodity);
CREATE INDEX IF NOT EXISTS idx_usda_prices_date ON fact_usda_prices (report_date);

-- ── dim_prospect_hubs ───────────────────────────────────────────────────────
-- Food-hub prospects pulled from the USDA Local Food Portal. Used by sales /
-- partnership outreach — distinct from dim_buyers (active customers) and
-- dim_suppliers (active producer partners).
CREATE TABLE IF NOT EXISTS dim_prospect_hubs (
    hub_id            VARCHAR PRIMARY KEY,
    hub_name          VARCHAR NOT NULL,
    listing_id        VARCHAR,                  -- USDA portal record ID
    address           VARCHAR,
    city              VARCHAR,
    state             VARCHAR,
    zip               VARCHAR,
    products          VARCHAR,                  -- comma-separated product list
    website           VARCHAR,
    email             VARCHAR,
    phone             VARCHAR,
    lat               DOUBLE,
    lng               DOUBLE,
    region            VARCHAR,                  -- 'IN', 'Midwest', etc
    source            VARCHAR DEFAULT 'usda_localfoodportal',
    fetched_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_prospect_hubs_state ON dim_prospect_hubs (state);

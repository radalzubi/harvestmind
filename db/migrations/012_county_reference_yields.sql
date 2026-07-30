-- 012: County-level reference yields (USDA NASS QuickStats).
-- Public ground truth for calibrating weather-to-yield response,
-- independent of any single operator's delivery records. Joined to
-- fact_weather_obs by county_fips + year.

CREATE TABLE IF NOT EXISTS fact_county_yields (
    yield_obs_id    VARCHAR PRIMARY KEY,     -- fips-commodity-year
    year            INTEGER NOT NULL,
    state_alpha     VARCHAR(2),
    county_name     VARCHAR,
    county_fips     VARCHAR(5),
    commodity       VARCHAR NOT NULL,
    yield_value     DOUBLE NOT NULL,
    yield_unit      VARCHAR,                 -- e.g. 'TONS / ACRE'
    source          VARCHAR NOT NULL,        -- 'nass_quickstats'
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE fact_county_yields IS 'Public county-level annual yields (USDA NASS). Calibrates weather-to-yield response curves per region and crop.';

CREATE INDEX IF NOT EXISTS idx_county_yields_fips ON fact_county_yields(county_fips);
CREATE INDEX IF NOT EXISTS idx_county_yields_year ON fact_county_yields(year);

-- Migration 009: Customer tiers, transport metrics, audit-readiness columns
-- Idempotent. Adds:
--   • customer_tier on dim_buyers and a new dim_customer_segments table
--   • transport_miles + truck_class on fact_deliveries (Scope 3 emissions)
--   • audit_evidence_status + last_audit_date on dim_suppliers
--   • A wholesale `dim_distribution_partners` table for the > $50M segment

-- ── dim_customer_segments ────────────────────────────────────────────────────
-- Pricing/segmentation lookup. Powers the tier-aware ROI calculator
-- and the master orchestration script.
CREATE TABLE IF NOT EXISTS dim_customer_segments (
    tier              VARCHAR PRIMARY KEY,
    segment_label     VARCHAR NOT NULL,
    gmv_band_low_usd  DOUBLE,
    gmv_band_high_usd DOUBLE,
    monthly_price_usd DOUBLE NOT NULL,
    annual_price_usd  DOUBLE NOT NULL,
    setup_fee_usd     DOUBLE DEFAULT 0,
    sla_hours         INTEGER DEFAULT 24,
    notes             VARCHAR
);

-- Idempotent seed: only insert if missing.
INSERT INTO dim_customer_segments
    (tier, segment_label, gmv_band_low_usd, gmv_band_high_usd,
     monthly_price_usd, annual_price_usd, setup_fee_usd, sla_hours, notes)
SELECT * FROM (VALUES
    ('A',   'Food hub',                     1000000.0,    10000000.0,    999.0,  11988.0,  2500.0, 48,
        'Single-location fresh-produce food hubs'),
    ('A_HIGH','Food hub (premium)',         5000000.0,    15000000.0,   1499.0,  17988.0,  4000.0, 24,
        'Larger single-location hubs requiring 24h support'),
    ('B',   'Multi-site aggregator',       15000000.0,    75000000.0,   3750.0,  45000.0, 12500.0, 12,
        'Regional aggregators serving multiple buyers / states'),
    ('C',   'Regional distributor',        50000000.0,   500000000.0,   6250.0,  75000.0, 25000.0,  4,
        'Mid-market wholesale distributors with ERP integration'),
    ('D',   'Enterprise distributor',     500000000.0, 5000000000.0,   20833.0, 250000.0, 75000.0,  2,
        'Large distributors requiring SOC 2, multi-tenant, SSO')
) AS new_rows(tier, segment_label, gmv_band_low_usd, gmv_band_high_usd,
              monthly_price_usd, annual_price_usd, setup_fee_usd, sla_hours, notes)
WHERE tier NOT IN (SELECT tier FROM dim_customer_segments);

-- ── dim_buyers : customer_tier ──────────────────────────────────────────────
ALTER TABLE dim_buyers ADD COLUMN IF NOT EXISTS customer_tier VARCHAR;

-- ── fact_deliveries : Scope 3 emissions inputs ──────────────────────────────
ALTER TABLE fact_deliveries ADD COLUMN IF NOT EXISTS transport_miles  DOUBLE;
ALTER TABLE fact_deliveries ADD COLUMN IF NOT EXISTS truck_class      VARCHAR;
ALTER TABLE fact_deliveries ADD COLUMN IF NOT EXISTS fuel_type        VARCHAR DEFAULT 'diesel';
ALTER TABLE fact_deliveries ADD COLUMN IF NOT EXISTS estimated_co2e_kg DOUBLE;

-- ── dim_suppliers : audit readiness ─────────────────────────────────────────
ALTER TABLE dim_suppliers ADD COLUMN IF NOT EXISTS audit_evidence_status VARCHAR DEFAULT 'unverified';
ALTER TABLE dim_suppliers ADD COLUMN IF NOT EXISTS last_audit_date       DATE;
ALTER TABLE dim_suppliers ADD COLUMN IF NOT EXISTS gfsi_certification    VARCHAR;
ALTER TABLE dim_suppliers ADD COLUMN IF NOT EXISTS sqf_level             INTEGER;

-- ── dim_distribution_partners ──────────────────────────────────────────────
-- Larger upstream partners we sell to (Tier C / D). Distinct from
-- dim_buyers (downstream) and dim_suppliers (producers).
CREATE TABLE IF NOT EXISTS dim_distribution_partners (
    partner_id         VARCHAR PRIMARY KEY,
    partner_name       VARCHAR NOT NULL,
    partner_tier       VARCHAR NOT NULL REFERENCES dim_customer_segments(tier),
    annual_gmv_usd     DOUBLE,
    n_locations        INTEGER,
    n_skus             INTEGER,
    primary_state      VARCHAR,
    states_served      VARCHAR[],
    erp_system         VARCHAR,
    integration_status VARCHAR DEFAULT 'prospect',
    soc2_required      BOOLEAN DEFAULT FALSE,
    contact_name       VARCHAR,
    contact_email      VARCHAR,
    notes              VARCHAR,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

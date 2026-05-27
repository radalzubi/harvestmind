-- Migration 007: FSMA-204 KDE completeness
-- Idempotent. Adds the KDE columns that 005 didn't include explicitly,
-- adds the cte_type CHECK constraint, and rebuilds v_fsma_204_report so it
-- exposes every KDE the FDA requires for the 24-hour sortable spreadsheet.
--
-- Compliance reference: 21 CFR § 1.1455 (Records of Critical Tracking Events).

-- ── fact_lots: ensure unit / GTIN / SSCC are present ────────────────────────
-- These were already in 005 for new installs. The IF NOT EXISTS clauses make
-- the migration safe to apply against legacy databases.
ALTER TABLE fact_lots ADD COLUMN IF NOT EXISTS unit_of_measure VARCHAR DEFAULT 'kg';
ALTER TABLE fact_lots ADD COLUMN IF NOT EXISTS gtin_14         VARCHAR;
ALTER TABLE fact_lots ADD COLUMN IF NOT EXISTS sscc            VARCHAR;

-- ── fact_cte_events: KDE columns required by 21 CFR § 1.1455 ────────────────
ALTER TABLE fact_cte_events ADD COLUMN IF NOT EXISTS unit_of_measure       VARCHAR DEFAULT 'kg';
ALTER TABLE fact_cte_events ADD COLUMN IF NOT EXISTS referenced_tlc_codes  VARCHAR[];
ALTER TABLE fact_cte_events ADD COLUMN IF NOT EXISTS new_tlc_code          VARCHAR;
ALTER TABLE fact_cte_events ADD COLUMN IF NOT EXISTS recorded_by           VARCHAR;

-- DuckDB doesn't support adding CHECK constraints via ALTER TABLE in older
-- versions; the constraint is also defined inline in 005's CREATE TABLE for
-- new installs. The migration is therefore a no-op there. We keep the
-- comment as documentation.
-- Valid cte_type values: harvesting, cooling, initial_packing,
-- shipping, receiving, transformation.

-- ── v_fsma_204_report: the FDA 24-hour sortable spreadsheet ─────────────────
DROP VIEW IF EXISTS v_fsma_204_report;
CREATE VIEW v_fsma_204_report AS
SELECT
    l.traceability_lot_code,
    l.tlc_source_reference,
    p.crop_name                  AS product_description,
    c.cte_type,
    c.event_timestamp,
    c.quantity_kg,
    c.unit_of_measure,
    c.location_description,
    c.business_name,
    c.point_of_contact,
    c.phone_or_email,
    l.harvest_date,
    l.pack_date,
    l.gtin_14,
    l.sscc,
    c.referenced_tlc_codes,
    c.new_tlc_code,
    c.recorded_by
FROM fact_cte_events c
JOIN fact_lots      l ON c.lot_id     = l.lot_id
JOIN dim_products   p ON l.product_id = p.product_id
ORDER BY c.event_timestamp;

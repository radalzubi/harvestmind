-- Supplier origin country (ISO3) so a public logistics prior can stand in
-- for lead-time variability until the operator's receipts measure it.
ALTER TABLE stg_fmcg_suppliers ADD COLUMN IF NOT EXISTS origin_iso3 VARCHAR;

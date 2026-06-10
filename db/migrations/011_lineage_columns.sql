-- 011: row-level lineage on every staging table.
-- Who uploaded it, from which file, in which session, when. Nullable so
-- pre-existing rows remain valid; the operator-scoped ingestion path
-- REJECTS new inserts without these fields (infrastructure/lineage.py).

ALTER TABLE stg_products            ADD COLUMN IF NOT EXISTS _upload_session_id VARCHAR;
ALTER TABLE stg_products            ADD COLUMN IF NOT EXISTS _uploaded_at TIMESTAMP;
ALTER TABLE stg_products            ADD COLUMN IF NOT EXISTS _source_file VARCHAR;
ALTER TABLE stg_products            ADD COLUMN IF NOT EXISTS _operator_id VARCHAR;

ALTER TABLE stg_supplier_deliveries ADD COLUMN IF NOT EXISTS _upload_session_id VARCHAR;
ALTER TABLE stg_supplier_deliveries ADD COLUMN IF NOT EXISTS _uploaded_at TIMESTAMP;
ALTER TABLE stg_supplier_deliveries ADD COLUMN IF NOT EXISTS _source_file VARCHAR;
ALTER TABLE stg_supplier_deliveries ADD COLUMN IF NOT EXISTS _operator_id VARCHAR;

ALTER TABLE stg_inventory_lots      ADD COLUMN IF NOT EXISTS _upload_session_id VARCHAR;
ALTER TABLE stg_inventory_lots      ADD COLUMN IF NOT EXISTS _uploaded_at TIMESTAMP;
ALTER TABLE stg_inventory_lots      ADD COLUMN IF NOT EXISTS _source_file VARCHAR;
ALTER TABLE stg_inventory_lots      ADD COLUMN IF NOT EXISTS _operator_id VARCHAR;

ALTER TABLE stg_buyer_orders        ADD COLUMN IF NOT EXISTS _upload_session_id VARCHAR;
ALTER TABLE stg_buyer_orders        ADD COLUMN IF NOT EXISTS _uploaded_at TIMESTAMP;
ALTER TABLE stg_buyer_orders        ADD COLUMN IF NOT EXISTS _source_file VARCHAR;
ALTER TABLE stg_buyer_orders        ADD COLUMN IF NOT EXISTS _operator_id VARCHAR;

ALTER TABLE stg_waste_adjustments   ADD COLUMN IF NOT EXISTS _upload_session_id VARCHAR;
ALTER TABLE stg_waste_adjustments   ADD COLUMN IF NOT EXISTS _uploaded_at TIMESTAMP;
ALTER TABLE stg_waste_adjustments   ADD COLUMN IF NOT EXISTS _source_file VARCHAR;
ALTER TABLE stg_waste_adjustments   ADD COLUMN IF NOT EXISTS _operator_id VARCHAR;

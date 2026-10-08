-- HARDENING V1, H2: the inventory-state contract.
--
-- A stock count is a state description, and its date alone does not say which instant it describes.
--   snapshot_at       optional exact instant the quantities represent (POINT_IN_TIME)
--   source_known_at   optional exact instant the operator could know the count; never ZAAD's import time
--   snapshot_basis    optional declared reading of a date-only row: START_OF_DAY (the state before that
--                     day's movements) or END_OF_DAY (the state that closes the day and opens the next)
-- A workspace may declare one basis for every date-only row with the economics key
-- `inventory_snapshot_basis`. A date-only row with no basis has ambiguous timing and does not plan.
ALTER TABLE stg_fmcg_inventory ADD COLUMN IF NOT EXISTS snapshot_at TIMESTAMP;
ALTER TABLE stg_fmcg_inventory ADD COLUMN IF NOT EXISTS source_known_at TIMESTAMP;
ALTER TABLE stg_fmcg_inventory ADD COLUMN IF NOT EXISTS snapshot_basis VARCHAR;
-- H2 correction: an optional lot identity. Two rows for one (sku, location, instant, expiry) are either one
-- record repeated or two real lots; only an explicit lot_id can tell them apart. Never row order or upload metadata.
ALTER TABLE stg_fmcg_inventory ADD COLUMN IF NOT EXISTS lot_id VARCHAR;

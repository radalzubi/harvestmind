-- Three-sector physics: optional operating-physics columns on the FMCG staging tables.
-- Additive and nullable. A row without these columns, or with NULL cells, plans exactly as before
-- (no physics is attached; unknown stays unknown). No backfill.

-- SKU master: sector, storage state, life at receipt / at sale, shipment weight.
ALTER TABLE stg_fmcg_skus ADD COLUMN IF NOT EXISTS sector VARCHAR;                          -- COMMERCIAL | PRODUCE | MEAT_SEAFOOD
ALTER TABLE stg_fmcg_skus ADD COLUMN IF NOT EXISTS storage_state VARCHAR;                   -- AMBIENT | CHILLED | FROZEN
ALTER TABLE stg_fmcg_skus ADD COLUMN IF NOT EXISTS age_at_receipt_days DOUBLE;              -- life already elapsed when a purchase arrives
ALTER TABLE stg_fmcg_skus ADD COLUMN IF NOT EXISTS min_remaining_life_receipt_days DOUBLE;  -- a receipt below this is refused
ALTER TABLE stg_fmcg_skus ADD COLUMN IF NOT EXISTS min_remaining_life_sale_days DOUBLE;     -- a unit below this is not sellable
ALTER TABLE stg_fmcg_skus ADD COLUMN IF NOT EXISTS weight_per_unit DOUBLE;                  -- operator mass unit
ALTER TABLE stg_fmcg_skus ADD COLUMN IF NOT EXISTS physics_provenance VARCHAR;              -- OPERATOR_OBSERVED | OPERATOR_DECLARED | DERIVED_FROM_OPERATOR_HISTORY | PUBLIC_PRIOR | FALLBACK

-- Inventory snapshots: lot expiry (a lot with an expiry date carries its own remaining life).
ALTER TABLE stg_fmcg_inventory ADD COLUMN IF NOT EXISTS expiry_date DATE;

-- Locations and lanes: storage states they can hold / carry (comma-separated; NULL = unrestricted).
ALTER TABLE stg_fmcg_locations ADD COLUMN IF NOT EXISTS storage_states VARCHAR;
ALTER TABLE stg_fmcg_lanes ADD COLUMN IF NOT EXISTS storage_states VARCHAR;

-- Supplier terms: shipment weight cap (paired with weight_per_unit on the SKUs).
ALTER TABLE stg_fmcg_suppliers ADD COLUMN IF NOT EXISTS max_shipment_weight DOUBLE;

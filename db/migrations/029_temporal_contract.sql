-- HARDENING V1, H1b: the canonical temporal contract.
--
-- Three times are kept apart on a staging fact:
--   event_at         when the fact physically / commercially happened (exact, optional)
--   source_known_at  when the operator could have known it (exact, optional)
--   imported_at      when ZAAD received the row (never used for causality)
-- Historical availability is `source_known_at < decision_at`. Rows without these columns keep the
-- date-only fallback: the event starts at the start of its date and is taken to be known then.
-- Existing date columns are unchanged; old files keep loading.
ALTER TABLE stg_fmcg_orders ADD COLUMN IF NOT EXISTS source_known_at TIMESTAMP;
ALTER TABLE stg_fmcg_purchase_orders ADD COLUMN IF NOT EXISTS event_at TIMESTAMP;
ALTER TABLE stg_fmcg_purchase_orders ADD COLUMN IF NOT EXISTS source_known_at TIMESTAMP;
ALTER TABLE stg_fmcg_receipts ADD COLUMN IF NOT EXISTS event_at TIMESTAMP;
ALTER TABLE stg_fmcg_receipts ADD COLUMN IF NOT EXISTS source_known_at TIMESTAMP;
ALTER TABLE stg_fmcg_promotions ADD COLUMN IF NOT EXISTS source_known_at TIMESTAMP;

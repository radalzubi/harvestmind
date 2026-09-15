-- 027: transfer proposals (Operating Product V2).
--
-- A proposal can be a move of stock between the operator's own sites rather than a purchase:
-- `transfer_origin_id` names the site the stock leaves and `destination_id` the site it goes to,
-- with no supplier. Built only because P2's network report carries concrete transfers (origin,
-- destination, product, quantity); nothing is inferred. Additive and idempotent.
ALTER TABLE zaad_draft_orders ADD COLUMN IF NOT EXISTS transfer_origin_id VARCHAR;

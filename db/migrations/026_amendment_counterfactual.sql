-- 026: the declared contract terms an amendment evaluation was run under (Operating Product V2).
--
-- An amendment is evaluated as a fixed counterfactual: the open order's pipeline entry rewritten
-- as if the declared right had been exercised. The engine never sees the contract's fee for using
-- that right, so the terms are stored with the evaluation and shown as their own line.
-- Additive and idempotent.
ALTER TABLE zaad_evaluations ADD COLUMN IF NOT EXISTS amendment_json VARCHAR;

-- 021: P5 release audit (item B). Additive, nullable, idempotent: the declared relation between a service
-- class's shortage penalty and the frozen Service.sla_per_unmet of the streams it serves
-- (ADDITIONAL_TO_SERVICE_SLA | REPLACES_SERVICE_SLA). Required by the contract whenever both are declared
-- non-zero for a line, so one shortage consequence is never declared twice. No data is changed.
ALTER TABLE stg_atp_service_classes ADD COLUMN IF NOT EXISTS shortage_penalty_basis VARCHAR;

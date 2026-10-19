-- HARDENING V1, H3b (cross-route exposure integrity): every route that returns an actionable ZAAD recommendation
-- records, BEFORE it answers, that a recommendation for (operator, planning origin) became accessible. The ledger is
-- append-only: the earliest row for an origin is the first exposure and can never move later; repeats add rows.
-- The coverage row marks the instant this vault began recording and HOW the vault came to record: a vault the
-- registry creates under this schema is stamped CREATED (with the vault file it was created as) by the creation
-- code, before any recommendation could have been served to its operator; a vault that existed before and gains
-- the tables through this migration's replay on open stays MIGRATION, and one that gains them lazily stays LAZY.
-- Only a CREATED vault served from its own file has a complete history: an upgraded one may have served
-- recommendations for ANY origin before recording (the contract route takes the origin from the caller), so the
-- shadow comparison never verifies its history. Replay is idempotent: the insert happens once, the stamp is kept.
CREATE TABLE IF NOT EXISTS zaad_recommendation_exposures (
    exposure_id         VARCHAR NOT NULL,       -- one row per time a recommendation was made accessible
    operator_id         VARCHAR NOT NULL,
    as_of               TIMESTAMP NOT NULL,     -- the planning origin the recommendation was for
    route               VARCHAR NOT NULL,       -- the route that made it accessible
    request_hash        VARCHAR,                -- the planner's information_hash when the report carried one
    reference           VARCHAR,                -- decision id, comparison id or job id when there is one
    exposed_at          TIMESTAMP NOT NULL,     -- server clock, UTC, taken before the response is sent; never client-supplied
    created_at          TIMESTAMP NOT NULL,
    PRIMARY KEY (exposure_id)
);

CREATE TABLE IF NOT EXISTS zaad_exposure_coverage (
    coverage_since_ms   BIGINT NOT NULL,        -- epoch milliseconds, UTC: when this vault started recording exposures
    source              VARCHAR NOT NULL,       -- CREATED (stamped by the registry at vault creation), MIGRATION (replay on open), LAZY (first instrumented use)
    bound_vault_path    VARCHAR,                -- the vault file the CREATED stamp was written for; a copy served elsewhere is not that vault
    legacy_engines_seen_ms BIGINT               -- epoch ms: first time a superseded (unrecorded) planning engine was observed reachable; never cleared
);

-- vaults that created the table from an earlier draft of this migration (additive, idempotent)
ALTER TABLE zaad_exposure_coverage ADD COLUMN IF NOT EXISTS bound_vault_path VARCHAR;
ALTER TABLE zaad_exposure_coverage ADD COLUMN IF NOT EXISTS legacy_engines_seen_ms BIGINT;

INSERT INTO zaad_exposure_coverage (coverage_since_ms, source)
SELECT epoch_ms(now()), 'MIGRATION'
WHERE NOT EXISTS (SELECT 1 FROM zaad_exposure_coverage);

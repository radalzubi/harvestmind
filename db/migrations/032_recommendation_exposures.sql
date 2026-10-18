-- HARDENING V1, H3b (cross-route exposure integrity): every route that returns an actionable ZAAD recommendation
-- records, BEFORE it answers, that a recommendation for (operator, planning origin) became accessible. The ledger is
-- append-only: the earliest row for an origin is the first exposure and can never move later; repeats add rows.
-- The coverage row marks the instant this vault began recording. A recommendation served before that instant is not
-- in this ledger: the shadow comparison treats origins that the vault's data could already plan at that instant, and
-- plans captured before it, as unverifiable (never READY). `max_order_date` is the vault's latest order date when
-- recording began (NULL on a vault created under this schema: no data could have been planned before recording).
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
    max_order_date      DATE,                   -- the vault's latest order date at that instant (NULL: no data yet)
    source              VARCHAR NOT NULL,       -- MIGRATION (applied when the vault was opened or created) or LAZY (first instrumented use)
    legacy_engines_seen_ms BIGINT               -- epoch ms: first time a superseded (unrecorded) planning engine was observed reachable; never cleared
);

INSERT INTO zaad_exposure_coverage (coverage_since_ms, max_order_date, source)
SELECT epoch_ms(now()), (SELECT max(order_date) FROM stg_fmcg_orders), 'MIGRATION'
WHERE NOT EXISTS (SELECT 1 FROM zaad_exposure_coverage);

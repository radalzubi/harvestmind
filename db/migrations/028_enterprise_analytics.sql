-- 028: Enterprise Analytics V1 — dataset versions, saved analyses, dashboards.
--
-- Additive, nullable, idempotent. Nothing here touches the optimizer or any staging table.
-- Every object is owned by one operator; specs are stored as JSON that the server validated
-- against the semantic model on save and validates again on open — never raw frontend state.

-- The dataset version a result, an analysis or an export was computed on: derived from the vault's
-- per-table upload stamps and row counts, recorded the first time it is seen.
CREATE TABLE IF NOT EXISTS zaad_analytics_dataset_versions (
    dataset_version_id  VARCHAR NOT NULL,
    operator_id         VARCHAR NOT NULL,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated        VARCHAR,
    data_cutoff         VARCHAR,
    tables              VARCHAR             -- JSON: table → {rows, last_updated, upload_sessions}
);

-- A saved analysis: one VisualSpec (which carries its AnalyticsQuerySpec), owned, versioned,
-- private or shared with the workspace. Rows are never hard-deleted while a dashboard references
-- them; `deleted_at` hides them.
CREATE TABLE IF NOT EXISTS zaad_analytics_analyses (
    analysis_id             VARCHAR NOT NULL,
    operator_id             VARCHAR NOT NULL,
    name                    VARCHAR NOT NULL,
    description             VARCHAR,
    owner                   VARCHAR NOT NULL,   -- actor id
    visibility              VARCHAR NOT NULL,   -- private | workspace
    origin                  VARCHAR NOT NULL,   -- user | ask_zaad | zaad_curated
    visual_json             VARCHAR NOT NULL,   -- VisualSpec (validated)
    semantic_model_version  VARCHAR NOT NULL,
    dataset_version_id      VARCHAR,            -- the version it was last run on
    notes                   VARCHAR,
    version                 INTEGER NOT NULL DEFAULT 1,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at              TIMESTAMP
);

-- A dashboard: a validated composition of saved analyses with a grid layout and shared filters.
CREATE TABLE IF NOT EXISTS zaad_analytics_dashboards (
    dashboard_id            VARCHAR NOT NULL,
    operator_id             VARCHAR NOT NULL,
    name                    VARCHAR NOT NULL,
    description             VARCHAR,
    owner                   VARCHAR NOT NULL,
    visibility              VARCHAR NOT NULL,
    spec_json               VARCHAR NOT NULL,   -- DashboardSpec (validated)
    semantic_model_version  VARCHAR NOT NULL,
    version                 INTEGER NOT NULL DEFAULT 1,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at              TIMESTAMP
);

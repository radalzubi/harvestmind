-- Migration 006: Planning output tables
-- Written by the optimization engine. Read by dashboard and API.
-- Stores scenario sets, commitment decisions, and human-readable recommendations.

CREATE TABLE IF NOT EXISTS planning_scenarios (
    scenario_id         VARCHAR PRIMARY KEY,
    run_id              VARCHAR NOT NULL,           -- groups all scenarios from one planning run
    week_start          DATE NOT NULL,              -- planning horizon week
    scenario_index      INTEGER NOT NULL,           -- 0-based within the run
    scenario_weight     DOUBLE NOT NULL DEFAULT 1.0,
    model_type          VARCHAR NOT NULL,           -- 'deterministic','robust','two_stage','cvar'
    gamma               DOUBLE,                     -- Bertsimas-Sim Γ parameter (robust model)
    lambda_cvar         DOUBLE,                     -- CVaR weight (0=mean, 1=pure CVaR)
    alpha_cvar          DOUBLE DEFAULT 0.95,        -- CVaR confidence level
    -- Scenario parameters
    demand_multiplier   DOUBLE DEFAULT 1.0,         -- applied to base demand forecast
    yield_multiplier    DOUBLE DEFAULT 1.0,         -- applied to expected yield
    spot_price_multiplier DOUBLE DEFAULT 1.0,
    enso_phase          VARCHAR,                    -- 'el_nino','la_nina','neutral'
    drought_cat         VARCHAR,
    weather_scenario    VARCHAR,                    -- descriptive label
    -- Outcomes
    total_cost_usd      DOUBLE,
    service_level_pct   DOUBLE,
    waste_kg            DOUBLE,
    spot_buy_kg         DOUBLE,
    spot_premium_usd    DOUBLE,
    cvar_95             DOUBLE,
    solver_status       VARCHAR,                    -- 'optimal','infeasible','timeout','error'
    solve_time_s        DOUBLE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_model_type CHECK (model_type IN (
        'deterministic','robust','two_stage','cvar','robust_cvar'
    )),
    CONSTRAINT chk_scenario_weight CHECK (scenario_weight > 0),
    CONSTRAINT chk_service_level CHECK (service_level_pct IS NULL OR
        (service_level_pct BETWEEN 0 AND 100))
);

COMMENT ON TABLE planning_scenarios IS 'One row per scenario per run. Supports VSS/EVPI analysis and Γ/λ sensitivity sweeps.';

CREATE TABLE IF NOT EXISTS planning_commitments (
    commitment_id       VARCHAR PRIMARY KEY,
    run_id              VARCHAR NOT NULL,
    scenario_id         VARCHAR,                    -- NULL for first-stage (here-and-now) decisions
    week_start          DATE NOT NULL,
    supplier_id         VARCHAR NOT NULL REFERENCES dim_suppliers(supplier_id),
    product_id          VARCHAR NOT NULL REFERENCES dim_products(product_id),
    -- Decision variables
    committed_kg        DOUBLE NOT NULL CHECK (committed_kg >= 0),
    contract_kg         DOUBLE DEFAULT 0,           -- portion under existing contract
    spot_kg             DOUBLE DEFAULT 0,           -- spot buy recourse
    wasted_kg           DOUBLE DEFAULT 0,           -- slack in recourse
    rerouted_kg         DOUBLE DEFAULT 0,           -- recourse rerouting
    price_per_kg        DOUBLE,
    estimated_cost_usd  DOUBLE,
    decision_stage      VARCHAR NOT NULL DEFAULT 'first',  -- 'first','recourse'
    confidence_pct      DOUBLE,                     -- model confidence in this commitment
    notes               VARCHAR,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_stage CHECK (decision_stage IN ('first','recourse')),
    CONSTRAINT chk_spot_kg CHECK (spot_kg >= 0),
    CONSTRAINT chk_wasted_kg CHECK (wasted_kg >= 0)
);

COMMENT ON TABLE planning_commitments IS 'Optimizer output: commitment quantities per supplier×product×week. First-stage decisions are actionable; recourse are contingency.';

CREATE TABLE IF NOT EXISTS planning_recommendations (
    rec_id              VARCHAR PRIMARY KEY,
    run_id              VARCHAR NOT NULL,
    generated_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    week_start          DATE NOT NULL,
    rec_type            VARCHAR NOT NULL,           -- 'commitment','alert','risk','opportunity'
    priority            INTEGER NOT NULL DEFAULT 2 CHECK (priority IN (1,2,3)),  -- 1=critical
    product_id          VARCHAR REFERENCES dim_products(product_id),
    supplier_id         VARCHAR REFERENCES dim_suppliers(supplier_id),
    buyer_id            VARCHAR REFERENCES dim_buyers(buyer_id),
    headline            VARCHAR NOT NULL,           -- ≤120 chars, shown on dashboard card
    detail              VARCHAR,                    -- full explanation for drill-down
    recommended_action  VARCHAR,                    -- imperative sentence for operator
    expected_impact_usd DOUBLE,                     -- +ve = savings or revenue, -ve = cost/risk
    confidence_pct      DOUBLE CHECK (confidence_pct BETWEEN 0 AND 100),
    requires_response_by DATE,
    status              VARCHAR NOT NULL DEFAULT 'open',
    resolved_at         TIMESTAMP,
    resolved_by         VARCHAR,
    model_type          VARCHAR,
    gamma               DOUBLE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_rec_type CHECK (rec_type IN (
        'commitment','alert','risk','opportunity','compliance','quality'
    )),
    CONSTRAINT chk_status CHECK (status IN ('open','actioned','dismissed','expired'))
);

COMMENT ON TABLE planning_recommendations IS 'Human-readable recommendations surfaced from optimizer output. Dashboard shows open recs grouped by priority.';

-- Supporting index table for Benders decomposition run logs
CREATE TABLE IF NOT EXISTS optimization_run_log (
    run_id              VARCHAR PRIMARY KEY,
    run_timestamp       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    model_type          VARCHAR NOT NULL,
    week_start          DATE NOT NULL,
    n_scenarios         INTEGER,
    n_products          INTEGER,
    n_suppliers         INTEGER,
    gamma               DOUBLE,
    lambda_cvar         DOUBLE,
    alpha_cvar          DOUBLE,
    solver              VARCHAR DEFAULT 'highs',
    solver_status       VARCHAR,
    objective_value     DOUBLE,
    solve_time_s        DOUBLE,
    n_benders_cuts      INTEGER,
    vss                 DOUBLE,                     -- Value of Stochastic Solution
    evpi                DOUBLE,                     -- Expected Value of Perfect Information
    gap_pct             DOUBLE,                     -- MIP gap if applicable
    notes               VARCHAR
);

COMMENT ON TABLE optimization_run_log IS 'One row per optimization run. Tracks VSS, EVPI, and solver performance for benchmarking.';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_scenarios_run ON planning_scenarios(run_id);
CREATE INDEX IF NOT EXISTS idx_scenarios_week ON planning_scenarios(week_start);
CREATE INDEX IF NOT EXISTS idx_scenarios_model ON planning_scenarios(model_type);
CREATE INDEX IF NOT EXISTS idx_commitments_run ON planning_commitments(run_id);
CREATE INDEX IF NOT EXISTS idx_commitments_week ON planning_commitments(week_start);
CREATE INDEX IF NOT EXISTS idx_commitments_supplier ON planning_commitments(supplier_id);
CREATE INDEX IF NOT EXISTS idx_commitments_product ON planning_commitments(product_id);
CREATE INDEX IF NOT EXISTS idx_recs_week ON planning_recommendations(week_start);
CREATE INDEX IF NOT EXISTS idx_recs_status ON planning_recommendations(status);
CREATE INDEX IF NOT EXISTS idx_recs_priority ON planning_recommendations(priority);
CREATE INDEX IF NOT EXISTS idx_runlog_week ON optimization_run_log(week_start);

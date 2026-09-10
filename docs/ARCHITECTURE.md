# Architecture and dependency map

One engine, two operating domains. The diagram is the dependency direction;
nothing lower imports anything higher.

```
        web/ (Next.js)      dashboard/ (Streamlit)
                 \              /
                  api/ (FastAPI, token auth, per-operator DuckDB vault)
                   |
   ingestion/  ->  db/ (DuckDB, 12 migrations)  <-  synthetic/ (agri generator, fmcg/)
                   |
        backtesting/  (rolling_origin_engine, benchmark_suite, counterfactual)
                   |
        risk/ (scenarios, copulas, disruption overlay)   forecasting/ (demand, supply, conformal)
                   |
        optimization/ (two_stage_sp, multi_period_sp, solve_status, explain, audit_trail)
                   |
        domain/ (Domain, DomainPolicy, PackSpec, CostConfig, ServiceTarget)
```

| layer | what it owns | domain-aware? |
|---|---|---|
| `domain/` | units, pack structure, validated economics, service metrics, the two policies | yes — this is the only place that knows the domains apart |
| `optimization/` | LP/MILP formulations (time-varying supply, fixed schedules, baseline anchoring, CVaR regret), `vss_evpi.py`, `safe_stochastic.py` (anchored and DRO candidates), solver outcome vocabulary, explanations, audit | no — consumes a policy's answers as data |
| `risk/`, `forecasting/` | scenario generation, `supply_paths.py` (block-bootstrap, route-correlated supplier paths), disruption presets, demand forecasts and scoring | no |
| `adaptive/` | the state layer: `signals.py` (provenance, freshness, absence ≠ normal; IMF PortWatch adapter), `change_point.py` (CUSUM, Page–Hinkley, drift), `state_estimator.py` (regime probabilities, stress with named components, per-SKU hysteresis), `controller.py` (state → posture: λ, α, regret budget, ρ scale, trust regions, change cost, commit window, gate thresholds, admitted candidates, autonomy), `conditional_scenarios.py` (route-shared disruption paths, learned or ASSUMED), `engine.py` (fold → estimate → posture). See `docs/optimization/ADAPTIVE_DECISION_ENGINE.md` | no — it reads the fold and the signal store, never truth |
| `backtesting/` | leakage-guarded rolling origins, settlement, policy ladder, closed-loop evaluator; `incumbent.py` (the operator's own policy, configured or INFERRED), `safe_selector.py` (multi-fold nested selection with conservative gates), `regime.py` (transparent per-SKU regimes) | no — settlement reads the policy for decay, cost terms, pack rounding |
| `synthetic/` | agriculture generator; `fmcg/` calibrated distributor archetypes | one generator per domain |
| `ingestion/` | CSV/LLM intake, column mapping, validation, quarantine reports | produce staging (kg) and FMCG staging (eaches, migration 013) |
| `api/` | routers, auth, vault routing, error boundary, request ids; `routers/fmcg.py` plans from `stg_fmcg_*` in eaches | produce routers plus an FMCG surface |

## Where the domains actually differ

Only in `DomainPolicy`: whether stock decays, whether orders are whole
lots, which cost terms are live, how service is promised, whether supply
uncertainty is a yield on a commitment or a fill of an order. Every `if
domain == ...` was pushed into the policy; the optimizer, the settlement
and the counterfactual harness contain none.

## Time semantics

| field | meaning | used by |
|---|---|---|
| order date | when the customer asked | demand history |
| requested delivery date | when they want it | service measurement |
| PO date | when we committed | information cutoff for backtests |
| expected lead | PO date + supplier lead distribution | scenario data |
| receipt date | when it landed | realised fill and lead in settlement |
| planning period | week (produce) or the configured review period (FMCG) | optimizer index `t` |

A backtest may use only rows dated strictly before the origin
(`backtesting/leakage_guard.py`); realised receipts enter settlement only.

## Known naming debt

Quantity columns are named `*_kg` throughout the schema, API and both
frontends (about 800 references). The engine treats them as base units and
the domain policy names the unit; renaming is a P2 because it is
mechanical, wide, and buys nothing until the API surface is made
domain-aware.

## The decision loop (FMCG, `/fmcg/plan`)

```
uploads -> build_inputs (provenance: OPERATOR / MEASURED / PUBLIC / ASSUMED / UNKNOWN)
        -> incumbent (configured or INFERRED from POs)
        -> safe_select: inner folds replay recorded supplier outcomes; candidates
           {incumbent, order-up-to, deterministic, stochastic, anchored}; gates;
           nested hold-out confirmation
        -> winner's schedule; first commit_window weeks EXECUTABLE, rest ADVISORY
        -> diagnostics: regime per SKU, VSS/EVPI, baseline-relative regret
        -> explanations, Decimal money, audit record, next replan cadence/triggers
```

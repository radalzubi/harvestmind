# Commercial model validation

Every number here was produced by code in this repository from the
artifacts named. Classification of each dataset is in
`data/external/README.md`. Terminology: a result on synthetic or
historical data is a **simulated** or **backtested** improvement, never a
realised saving.

---

## Part 1 — Agriculture (perishable produce)

### Datasets

| dataset | class | use |
|---|---|---|
| US Census MWTS grocery wholesalers (NAICS 4244), 414 months, NSA, via FRED | REAL PUBLIC | demand path and forecast calibration |
| US Census merchant wholesaler inventory/sales ratio, 414 months | REAL PUBLIC | inventory norm (mean 1.264 = 38 days, p90 1.35) |
| IMF PortWatch AIS: 78,372 daily chokepoint and 22,376 daily port records, 2019–2026 | REAL PUBLIC | route-specific supply shocks; Red Sea crisis, COVID, Ever Given, Hormuz |
| synthetic operator cross-section (`synthetic/generator.py`) | SYNTHETIC CALIBRATED | which SKU, which supplier, which margin |

### Calibration

Scenario generator scored on 4,404 real origin-horizon pairs
(`artifacts/scenario_calibration.txt`, `scripts/validate_demand_scenarios_real.py`):

| method | WIS | 80% interval coverage | below median |
|---|---|---|---|
| iid bootstrap (previous default) | 0.0541 | 95.9% | 47.9% |
| **seasonal bootstrap (now default)** | **0.0356** | **80.0%** | **51.0%** |
| seasonal naive | 0.0396 | 54.5% | 20.2% |
| random walk | 0.0500 | 96.3% | 37.8% |

Disruption presets against measured arrivals (`artifacts/disruption_presets.txt`):
`red_sea_houthi` assumed 0.85, measured 0.743, revised to 0.75;
`aqaba_congestion` and `northern_land_disruption` consistent; three tail
presets untested (their events did not occur in 2019–2026). Aqaba carries
100% of Jordan's maritime imports; its five worst months on record all lie
inside the Red Sea crisis window.

### Experiments and results

Rolling-origin backtest of the multi-period stochastic optimizer on the
real demand path, 1,028 folds 1994–2026, 12-month horizons
(`docs/reports/REAL_DATA_VALIDATION_PROJECT_B.md`, evidence under
`docs/reports/evidence/real_validation/`):

| comparison | median edge | folds won |
|---|---|---|
| vs naive order-up-to with safety stock | +13.2% | 288/342 |
| vs cautious p90 lead buffering | +34.3% | 341/342 |
| vs the same optimizer with a point forecast, pooled | +1.8% | 597/1028 |
| — binding months (shortage > 20% of baseline cost) | +4.17% | 528/769 |
| — slack months | −4.75% | 69/259 |
| vs point forecast, with measured supply shocks (2019–26) | +10.5% | 283/336 |

Paired, block-bootstrapped: measured supply disruption raises the edge by
+2.26 points, CI [−0.70, +4.62], sign p = 0.025 — directionally supported,
not established at 95%.

### Revalidation of the formulation

`tests/unit/test_agriculture_invariants.py` recomputes, from solved
variables: the per-scenario balance with supplier yield applied exactly
once; non-negativity; capacity; that waste and unmet are never both
positive; weight normalisation and completion; the objective as weighted
recourse including the spot premium; first stage scenario-invariant and
permutation-invariant; a fixed first stage never beating the free one;
critical-fractile recovery with spot off; service floor honoured in
expectation; deterministic equivalence. `tests/unit/test_engine_leakage.py`
intercepts what reaches the solver from the production engine.

Defects found in this pass: the production backtest engine ran the
optimizer on the objective its own source labels a double-count (fixed to
the newsvendor objective priced as the scorer prices); an infeasible model
raised out of the solver wrapper (fixed); the effective underage cost with
spot available is `min(lost margin, spot premium)`, which lowers the
critical fractile — correct economics, now documented (MATH_SPEC §21).

### Limitations

No operator's records were used. The cross-section is synthetic. The supply
signal is arrivals, a proxy for fill. Results are monthly with 1–3 month
lead times.

---

## Part 2 — FMCG (shelf-stable distribution)

### Datasets

All FMCG operating histories are **SYNTHETIC CALIBRATED**
(`synthetic/fmcg/distributor_sim.py`), shaped by public evidence: gross
margin 12–22% for import distribution, carrying 1.5–2.5%/month, 38 days of
inventory (Census), OTIF norms 90–98%, ABC 20/30/50 carrying 80/15/5. No
distributor's records exist in this repository.

### Simulator coherence

Receipts are a PO's quantity times a fill draw landing at PO date plus a
lead draw from the same supplier state; stockouts are shortfalls against
order lines; a disruption is a supplier state. `tests/unit/test_fmcg_simulator.py`
checks receipts never exceed the PO, shipments never exceed orders, stock
never negative, PO lots whole, seed reproducibility, whole-pallet and MOQ
ordering for the importer, and that a disruption degrades fill inside its
window only.

### Experiments

Eight policies settled on identical realised paths through one settlement
(`backtesting/counterfactual.py`): naive forecast, last period, seasonal
naive, static safety stock, min/max, order-up-to (z = 1.64 over lead +
review, fill gross-up), the optimizer with a point forecast, the
stochastic optimizer, and SELECTED (backtest on trailing history picks
among order-up-to, deterministic and stochastic; nothing after the origin
used). Supplier capacity binds every policy. No fold is filtered on its
outcome.

#### Open loop (one 12-week schedule per fold, no re-plan) — superseded

`artifacts/fmcg_counterfactuals.json`, 5 seeds × 6 folds per archetype,
opening cover 5.4 weeks. The stochastic optimizer LOST to its point-forecast
twin in every archetype (−3% to −19%) while every policy sat at 99–100%
service: with 5.4 weeks of cover, insurance is never used and the policy
that buys it pays. This harness also has a horizon end effect (late orders
free, ending stock uncredited). Reported because it was run; not the basis
of any claim.

#### Closed loop (re-plan every 4 weeks over 40 weeks, state carried) — primary

`artifacts/fmcg_counterfactuals_rolling.json`, 3 seeds per archetype.

<!-- ROLLING_TABLE -->

#### Stress matrix

`artifacts/fmcg_stress_demand_cv_fill.json` (30 cells, demand CV × supplier
fill) and `artifacts/fmcg_stress_cover.json` (opening cover), 2 seeds × 2–3
folds, open loop. Pattern: the stochastic optimizer's edge over the point
forecast is negative at CV ≤ 0.3 and positive at CV ≥ 0.5 with fill ≤ 0.9,
reaching +20% to +34% at CV 1.2; a single cell shows a −392% worst fold at
CV 1.2 / fill 0.8 (a spike the deterministic plan happened to miss less).
Opening cover decides the sign: +18% at 0.5 weeks, negative from 1 week up.
No cell produced an unusable solver status.

### What the FMCG evidence supports

- The engine handles discrete cases, pallets and MOQ, uncertain fill and
  lead time, and warehouse capacity, with invariants tested.
- The stochastic optimizer beats a deterministic optimizer when demand or
  supply actually bind and loses when they do not. This is the theory's
  prediction and it held on real produce demand and on synthetic FMCG
  histories alike.
- A competent order-up-to heuristic is hard to beat where holding is cheap.
  The deployable mode is therefore SELECTED, which never runs a policy
  its own trailing backtest ranked below the heuristic.

### What it does not support

- Any claim about a real distributor. There is no operator data.
- Multi-echelon, transfers, promotions as a planned input (they are in the
  history, not the forecast), OTIF as a constraint.
- The HTTP API and frontends: FMCG runs at the library layer.

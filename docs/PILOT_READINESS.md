# Pilot Readiness

_Last updated: 2026-06-10 · suite: 396+ passing · supersedes the engine
sections of ENGINE_STATUS.md (the spot-economics finding there still
stands and is restated below)._

What the system can do today, what has been validated and on what data,
and what still gates a real pilot. Every claim below is reproducible from
the test suite or the gate runs cited.

---

## 1. The pipeline, end to end

ingestion → diagnostic → demand forecast → supplier-yield forecast →
two-sided stochastic allocation → benchmark → confidence → ROI, all
surfaced in the dashboard:

| Layer | State | Gate & result |
|---|---|---|
| Ingestion + hard validation | shipping | rejects negatives / reversed dates / unparseable required dates with named rows; scorecard violations block |
| Diagnostic (waste $, shortage $, suppliers, buyers, traceability, ATP) | shipping | arithmetic on the operator's own data; ATP uses the continuous shelf-life weight (cliff retired) |
| Demand forecaster (LGBM global + Croston routing) | gated | **MASE gate PASSED on 52-wk realistic sim**: beats seasonal-naive 4/4 folds, WAPE 0.251 vs 0.269, OOS ratio 0.933, bias +0.9% |
| Supplier-yield forecaster (EB Beta-Binomial, continuous shrinkage, service-linked quantile) | gated | **calibration gate PASSED**: 3,068 held-out deliveries, 10–90 coverage 0.767 (target 0.80 — slightly narrow, stated), PIT KS 0.049 |
| Tier-2 covariates (weather etc.) | hook only | admission harness built; weather signal **not admitted** (no observations — never on faith) |
| Two-sided stochastic optimizer (newsvendor objective, yield draws, service floor, diversification cap) | gated | see §2 — the verdict depends on spot economics |
| Validation harness (LP / naive / order-up-to baselines, SAA gap) | shipping | benchmark + SAA-gap endpoints live; prints the unflattering verdict when the SP loses |
| Validation-gated retraining (both forecasters) | shipping | refit deploys only if it beats the incumbent on holdout; versioned, logged, rollback tested |
| Explainability / confidence / ROI | shipping | LP shadow prices per binding capacity; confidence labeled *internal index, not a probability*; two-card ROI never summed |

## 2. The optimizer verdict — under stated assumptions

On the 52-week realistic synthetic operator, honest per-product
penalties, identical clean scoring for every policy:

| Spot assumption | SP vs deterministic LP | SP vs naive | SP vs order-up-to | Gate |
|---|---:|---:|---:|---|
| cheap (1.30× premium, 30% cap) | **+11.1%** (7/8, t=4.1) | +18.3% | +63.1% | **PASS** |
| expensive (1.60×, 15% cap) | **−4.0%** (3/8, t=−1.7) | +5.9% | +48.2% | **FAIL** |

The stochastic layer's edge over a deterministic LP **depends on what
emergency/spot coverage actually costs the operator** — the same finding
as the Phase 0.9 investigation, now reproduced in the full two-sided
engine and surfaced in the product (the benchmark page makes you pick a
spot assumption; the planning endpoint returns a sensitivity band when
spot is not elicited). Robust statements that hold across the grid: the
optimizer beats the naive run-rate and the order-up-to heuristic
everywhere tested; the SP-vs-LP edge is spot-contingent.

## 3. Validated (synthetic) vs awaiting real data

**Validated on synthetic data only.** Every number above comes from the
calibrated synthetic operator (~$8M, 28 products, 52 weeks). "Validated"
in this document means: internally consistent, lookahead-protected,
gate-checked — on synthetic data. No real operator's records have
touched any layer.

**Awaiting a real operator:**
1. **Spot economics** — the single parameter that decides whether the
   stochastic layer pays. Elicited in the first week of a pilot, never
   assumed.
2. **Forecast gates re-run on real history** — the MASE and calibration
   gates are per-operator; the system reports honestly when a gate fails
   (the naive or the raw history becomes the recommended input).
3. **The measured ROI card** — stays "not yet measured" until the
   benchmark runs on the operator's own history.
4. **Market validation** — no evidence yet that an operator will pay;
   the engine being real does not make the business real.

## 4. Honest claim language

Can say: "every model layer ships behind an out-of-sample gate and
reports when it loses to the simple baseline"; "on a realistic synthetic
operator the optimizer beats the operator heuristics everywhere tested,
and beats a deterministic LP when spot coverage is expensive to the
operator — which we measure first, not assume."

Cannot say: "validated" without the synthetic qualifier; any specific
dollar savings as if banked; the +11% (or any single SP-vs-LP number)
without naming its spot assumption.

## 5. Known gaps that do not block a pilot

- Multi-week recursive demand forecasting (the LGBM forecasts one week
  ahead; deeper horizons hold the rate flat — stated in the API).
- Benchmark scoring is product-level against realized demand; realized
  supplier fills are not replayed into the score (fair across policies,
  approximate in absolute terms).
- Cross-operator pooling exists as a tested hook only; wiring it before
  a second operator exists would fabricate confidence.
- The Streamlit-era v0.1 normalized-schema path (`/planning/run`,
  `/backtest/run`) remains for the older demo flows; the staging-first
  path above is the product.

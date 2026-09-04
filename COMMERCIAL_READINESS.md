# Commercial readiness

Branch `commercial-readiness/fmcg-agriculture`. Evidence is measured by
the code in this repository and lives in `artifacts/` and
`docs/validation/`; the machine-readable form is
`artifacts/commercial_readiness.json`, rebuilt by
`./scripts/commercial_validate.sh`. Baseline before this pass:
`docs/audits/pre_commercial_baseline.md`.

## Executive assessment

**Can we responsibly pilot this with a real operator?**

```
YES WITH CONDITIONS
```

Responsibly means: on the operator's own exported history, in backtest,
with the operator told in advance that the model earns its keep only when
supply or demand actually bind, and that the deployable mode will
sometimes recommend the same order-up-to logic they already run — because
its own trailing backtest said so. It does not mean the system has ever
been validated on a real distributor's order and receipt records. It has
not. That is the first condition and it cannot be closed from inside this
repository.

## What changed in this pass, in one paragraph

A domain layer was added so one engine serves perishable produce and
shelf-stable FMCG without relabelling: continuous decaying kilograms on
one side, whole cases and pallets with MOQ on the other, priced and
validated differently, with the optimizer, settlement and harness
domain-blind. The optimizer became a MILP where the domain needs it and
now reports an honest solver status instead of crashing on infeasibility
or dressing a time-limited answer as an optimum. Authentication is
fail-closed outside dev, uploads are idempotent and cannot 500 on a stray
column, every response carries a request id and no traceback reaches a
client. A calibrated FMCG simulator with six archetypes and a closed-loop
counterfactual harness with a competent eight-policy baseline ladder were
built; the production backtest engine's objective was corrected; and
every result table in the reports is written by code.

## Agriculture readiness

| dimension | score (1–5) | evidence |
|---|---|---|
| model correctness | 4 | invariants recomputed from solved variables (`test_agriculture_invariants.py`, `test_stochastic_correctness.py`); engine objective double-count fixed; leakage intercepted at the solver (`test_engine_leakage.py`); real-data backtest on 1,028 folds |
| data ingestion | 4 | 15 hostile-upload tests; unexpected columns, duplicates, blank quantities handled with named rows; content-hash idempotency |
| explainability | 4 | `/planning/two-sided` returns explanations and an audit record |
| robustness | 4 | solver outcome vocabulary; complete recourse proven; failure injection for DB, solver, LLM flag, bad key, empty data |
| performance | 4 | 100 SKUs × 30 scenarios × 12 periods in 6 s LP / 10 s MILP; 1,000 SKUs × 20 × 8 in 47 s (`docs/validation/PERFORMANCE_BENCHMARKS.md`) |
| security | 4 | 1 High, 4 Medium, 4 Low fixed, 0 open; 15 adversarial tenant tests; bandit 0; CodeQL, Dependabot, pip-audit gated |
| testing | 4 | 1,241 passed, 0 failed, 1 skipped; 130 new tests, one per defect or invariant |

## FMCG readiness

| dimension | score (1–5) | evidence |
|---|---|---|
| model correctness | 4 | whole-lot, MOQ, pallet and max-order constraints proven; free-disposal exploit closed; objective reconciles to components |
| data ingestion | 4 | six FMCG staging tables with validation, idempotent uploads, promotion calendar; end-to-end API test |
| explainability | 4 | every order returns its reasons and Decimal value on `/fmcg/plan`; mode selection shows the backtest costs that decided it |
| robustness | 4 | as above; stress matrix produced no unusable solve across 30+ cells |
| performance | 4 | 500 SKUs MILP × 20 × 8 in 20 s |
| security | 4 | shared with agriculture |
| testing | 4 | simulator coherence, library and HTTP acceptance flows, service-floor, transfer and promotion invariants; no real data |

## What the FMCG evidence actually says

Closed loop, six archetypes, three 40-week runs each, re-planning every
four weeks, every policy carrying its own state and bound by the same
supplier capacity (`docs/validation/COMMERCIAL_MODEL_VALIDATION.md`):

- The stochastic optimizer beats its point-forecast twin in 3 of 6
  archetypes (+9% to +14%) and loses in the others
  (-36% at worst). Regenerated after the P1/P2 pass: service floors,
  promotions as input, and a horizon of at least two lead times changed
  every number, mostly by raising service for all policies.
- **A competently tuned order-up-to heuristic beats the stochastic
  optimizer in every archetype (by 14% to 42%).** At the calibrated
  holding cost of 2%/month, insurance stock is nearly free and a heuristic
  that over-stocks wins; the optimizer prices the trade-off and holds less.
- The deployable mode, SELECTED — backtest order-up-to, deterministic and
  stochastic on the operator's own trailing history and run the winner —
  beats the deterministic optimizer in 5 of 6 archetypes
  (+35% at best) and is within 3.5% of it in the stable one,
  mostly by choosing the heuristic. The importer archetype, which
  under-served every policy before, now runs at 88% service.
- Where does the stochastic model win outright? Lean operators (opening
  cover ≤ 1 week, +8% to +19% over deterministic), high demand variability
  (CV 1.2 with fill ≤ 0.9, +35% to +42%), and — the decisive one — high
  carrying cost: at 4.6% of unit cost per week it beats the order-up-to
  heuristic by 6% to 38%, at the calibrated 0.46% it loses to it
  (`docs/validation/evidence/fmcg_stress_holding_cover.md`). The
  operator's true all-in carrying cost is the first number a pilot must
  measure.

This is not a marketing result. It is the reason the product should ship
SELECTED and not the stochastic model alone, and the reason the first
pilot must measure the operator's actual carrying cost before promising
anything.

## Adaptive decision engine (post-research pass)

The hard regime labels are replaced by an estimated operating state (regime probabilities, stress with named components, change points that need two bad receipts, per-SKU hysteresis, logistics signals with provenance and staleness where absence is never read as normal) and a state-dependent posture that changes *how* the optimizer optimizes: scenario width and persistence, CVaR weight and level on baseline-relative regret, regret budget, anchoring scale, per-SKU trust regions inside the MILP, a plan-stability cost against the previously published schedule, the executable commit window, the safe gate's thresholds, and which candidates are admitted at all. An autonomy score summarises how much freedom the optimizer is given and why; less evidence always means less autonomy. Transition behaviour (progressive disruption, sudden shock, false alarm, demand-only shock, recovery, asymmetric suppliers, easy/slack) is validated closed-loop on unseen seeds in `docs/validation/ADAPTIVE_ENGINE_VALIDATION.md`; design in `docs/optimization/ADAPTIVE_DECISION_ENGINE.md`. The engine has not been run on a real operator's live data.

What the transition validation showed, after four frozen runs on the same seven stories: the gated engine (state-conditioned candidates behind the evidence gate) tracks a competent incumbent within about a percent on every supply-side story, the false alarm, the recovery and the easy/slack case, while the ungated optimizer loses a fifth to a third on those same stories; detection lands on the affected suppliers once the trough is visible in receipts and stays off elsewhere. The engine now runs in efficiency, balanced and protection modes on one continuous mapping, reads public leading indicators (chokepoint transits lead Aqaba imports by about five weeks on real history; the pressure and fuel indices do not), and carries a demand channel. The negative result that remains is the demand-only shock: the ungated candidate now captures the surge, but the gate cannot certify it from pre-shock folds and brief mid-shock switches cost more than they earn. The specific fix, a regime-matched gate, needs its own frozen run and is the first follow-up. The validation harness itself needs a cheaper mode (fewer inner folds, cached fold solves) before it is run routinely: a full run is about an hour of four cores.

## Safe adaptive decision engine (previous pass)

The product no longer chooses among optimizers; it tests whether departing
from the operator's own policy is justified. Frozen design, unseen seeds,
SYNTHETIC CALIBRATED, nine regimes (`docs/validation/SAFE_POLICY_VALIDATION.md`,
`artifacts/safe_policy_validation.json`):

- **Standalone stochastic optimizer vs the inferred incumbent**: median
  -53.1% to +58.9% across regimes; worst single run -67.8%.
  At the calibrated carrying cost it loses in every low-carry regime; at
  high carrying cost it wins large.
- **SAFE_SELECTED vs the incumbent**: median -3.4% to +13.7%; worst
  single run -27.6% (one run in the mixed-portfolio regime, where a
  deterministic candidate cleared the gate and then lost — reported, not
  removed). In the easy/slack and low-carry regimes SAFE stays within
  2.1% of the incumbent; in the high-carry regimes it captures
  -3.4% to +13.7% of the value uncertainty creates.
- **Mode selection**: the incumbent was retained in 166 of 216 re-plans
  (77%); deterministic 33, order-up-to 10,
  stochastic 7. Retaining the incumbent in a calm period is the
  intended outcome.
- **Anchored stochastic candidate** as parameterised (λ=0.5, regime-weighted
  L1): median -39.1% to +22.3%. Not safe on its own at
  the calibrated carrying cost; useful only through the selector.

Negative findings kept: the anchored candidate's in-sample regret control
did not translate into out-of-sample safety at low carrying cost; one
mixed-regime run lost 27.6% after the gate opened; the incumbent inferred
from the simulated PO log is a competent order-up-to with safety stock, so
"no candidate cleared the threshold" was the common — and correct — answer.

## Remaining blockers

```
P0 — cannot pilot
```
- No validation on a real operator's order, receipt and inventory
  records. Every FMCG number is SYNTHETIC CALIBRATED; the agriculture
  demand path is real but the cross-section is not. The FMCG API now
  takes an operator's exports end to end (`POST /intake/upload/stg_fmcg_*`,
  `POST /fmcg/plan`), so closing this is a two-week backtest away.

```
P1 — resolved in the P1/P2 pass
```
- **FMCG through the product surface.** Migration 013 adds six staging
  tables in eaches; the shared upload endpoint validates them; `/fmcg/plan`
  runs SELECTED (or a named mode) and returns whole-lot orders with the
  reasons, Decimal money, the trailing-backtest costs that decided the
  mode, and an audit run id. Next.js `/fmcg` and Streamlit page 09 drive
  it. Tested end to end (`tests/integration/test_fmcg_api.py`).
- **Explanations and audit on the produce API.** `/planning/two-sided`
  now returns `explanations` and an `audit_record`; commitments carry
  unit-neutral `quantity`/`unit`.
- **Entrypoint guard.** A permissive process refuses to start on a
  non-loopback bind (`HARVESTMIND_BIND_HOST`); the Dockerfile and compose
  file declare the bind and default to `pilot`. Physical isolation (one
  DuckDB per operator) is a design decision, recorded as such.
- **Docker.** Built and smoke-tested in CI (import, fail-closed posture,
  compose validation). Still unverified on this host, which has no daemon.
- **mypy.** 68 → **0** on the decision core; now a blocking CI gate. One
  real bug surfaced: intermittent-demand forecasts read a field that did
  not exist (`fc.point`), and the USDA price connector was called with a
  keyword it does not accept.
- **Importer service.** Unit-fill service floors are enforced in the
  optimizer from the domain policy, and the closed-loop horizon is at
  least two lead times plus a review cycle.

```
P2 — resolved
```
- **Money.** `domain/money.py`: Decimal, currency-tagged, minor-unit
  quantised, totals reconcile exactly; used at every API boundary.
- **Multi-location.** Transfer arcs between location-keyed products with
  cost and lead, bounded by opening stock, conservation tested.
- **Promotions.** A planned uplift is an input to scenarios, the
  deterministic twin and the heuristics; `stg_fmcg_promotions` carries
  the calendar.
- **Service metrics.** Unit-fill floors enforced per product; OTIF, line
  and order fill measured.

```
P2 — deliberately deferred, with reason
```
- Line fill and order fill cannot be *enforced* by a product-level LP
  without order-line variables; they are measured.
- The produce database schema keeps `*_kg` column names. Responses now
  carry unit-neutral fields; the storage rename is a wide mechanical
  change that buys nothing for the pilot and risks the working produce
  product.
- A shared-database SaaS deployment is not offered; isolation stays
  physical.

## Evidence

- Tests: **1,262 passed, 0 failed, 1 skipped, 0 xfailed** (`artifacts/junit.xml`).
  Baseline was 1,111.
- Coverage on the critical packages: see `artifacts/coverage.json`
  (`by_package_pct` in the readiness JSON).
- Security: bandit medium+ **0** (baseline 24); pip-audit clean on a fresh
  install of `pyproject.toml` except one unfixed advisory in an optional
  extra; secret scan clean; history clean.
- Real data: 414 months US Census wholesale demand; 100,748 daily
  PortWatch records; disruption presets confronted with measurement, one
  revised.
- Simulation: 6 archetypes × 3 seeds × 40 weeks closed loop (10 re-plans
  each, 8 policies) = 1,440 settled policy-runs; 30-cell CV × fill matrix;
  cover and holding sweeps; open-loop matrix of 180 folds retained for
  the record.
- Performance: `docs/validation/PERFORMANCE_BENCHMARKS.md`.

## The sentence for an operator

If your history says supply or demand bite, this will hold less stock than
you do today and serve better; if it says they do not, it will tell you
to keep doing what you are doing, and we would rather say that in the
pilot than after it.

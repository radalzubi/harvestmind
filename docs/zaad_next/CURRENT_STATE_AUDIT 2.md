# Zaad: independent current-state audit

Reviewed base `6939523a7fe888bd9808ef55563314a485d88929` (PR20), September 2026.
This is a code and synthetic mechanism audit, not real customer validation or
a comprehensive penetration test. Historical negative results remain evidence;
their interpretation is narrowed where this audit finds a confound.

## The service-target plateau has a newly reproduced structural cause

`optimization/service_frontier.py::solve_service_target` sets shortage cost to
zero. `optimization/multi_period_sp.py` excludes the earliest lead-time dead
zone from both horizon and per-period service floors. Its scenario-wise recourse
can therefore withhold available stock from an early customer to reserve it
for demand it already knows will occur later in that scenario. Physical
`backtesting/counterfactual.py::settle` instead serves all available demand.
Those are different operating policies.

**Independent same-scenario parity probe:** target 100%, stable synthetic
operator, development seed701, origin60, 80 scenarios, per-period candidate.
Opening stock is 277.1278 units; known initial receipts add138.5639. Every
scenario's first-period demand is fully coverable. The optimizer nevertheless
models **37.5773 expected units unmet in period0** and zero unmet in all later
periods. Replaying its identical fixed schedule on the **same** 80 demand,
fill and lead scenarios through common greedy settlement produces exactly
**37.5773 expected unmet units later**. No out-of-sample demand or pipeline
forecast error is needed to reproduce the failure.

Consequently, PR20's 94% plateau does **not** establish that service-constrained
inventory optimization intrinsically fails. It establishes that its target-only
candidate and physical settlement do not implement the same service rule.
The per-period correction alone cannot fix an unconstrained first period.
This defect does not imply a corrected policy will outperform the incumbent.

### Other mechanisms, kept separate

- At exactly52 training weeks, `_seasonal_pool` uses only five observations
  (seasonal phase ±2), including stable IID demand without a seasonality gate.
  Eight sampled scenarios offer little upper-tail coverage. Target100 is100%
  on the sampled support, not an operational guarantee.
- New development seeds701–705 confirm that enlarging scenario support alone
  is insufficient. At target100/per-period: seasonal5/8 scenarios median
  realized fill91.45%, range88.35–96.75%; seasonal5/80:93.48%,91.35–98.04%;
  whole-history/8:92.62%,90.98–93.63%; whole-history/80:95.00%,93.18–97.28%.
  All20 runs solved without fallback. These are diagnosis ablations, not a
  replacement holdout or a tuned production recommendation.
  Every seed result is retained in `LEGACY_POOL_DIAGNOSTIC.csv`.
- Aggregate service can borrow shortage allowance from the future; the
  per-period variant addresses that mechanism but not the dead-zone issue.
- Every four-week review recreates an uncontrolled first period and uncertain
  pending receipts. The benchmark separates private realized POs from expected
  ones, but treats expected pipeline as deterministic inside the planner.
- The12-period finite horizon lacks terminal stock/PO economics; long-lead
  stress may exceed its adequate lookahead. Shelf-stable no-spot cases do not
  test the known expiry/transfer/emergency settlement mismatches.

### Corrective requirements

1. Define demand service physically: serve `min(available, demand)` unless
   explicit customer rationing is part of both the action space and execution.
   Do not merely add a guessed shortage penalty and call parity proven.
2. Pin an identical-scenario optimizer-versus-settlement regression that checks
   every period's stock, receipts and served units, including lead dead zones.
3. A causal normal inventory-position policy is a reusable baseline and potential
   production candidate. Calibrate its protection-period demand/service using
   training-only evidence; do not label an empirical quantile an SLA guarantee.
4. Separate demand-model selection/calibration, policy selection and untouched
   final evaluation. Do not reuse development seeds or PR20 seeds as blind tests.
5. Treat service-target/frontier, adaptive and incumbent-first selection as
   experimental until their own operational parity and decision value are shown.

## End-to-end production path is not the corrected PR20 replay

The path is staging CSV → `api/routers/fmcg.py::build_inputs` → adaptive state
and scenarios → candidate solve → `explain_schedule` → `/fmcg/plan` →
`web/src/app/fmcg/page.tsx`. PR20 corrected the audit simulator and selector;
important production adapter defects remain on this base.

| Priority | Code boundary | Verified issue / consequence |
|---|---|---|
| P0 | `fmcg.py::build_inputs`, receipt aggregation | Aggregates all receipts before restricting POs to `po_date < origin`; post-as-of receipts can influence fill/lead. Supply events are dated by PO placement, not receipt availability. |
| P0 | `latest_gate_decision` + `/fmcg/plan` safe branch | Cached gate matches product count/history length within14days, not exact data/economics/policy/provider fingerprints. Candidate rerun rejects only schedule=None, not floor/budget relaxation. Historical evidence can be reused for materially changed inputs. |
| P0 | same adapter, opening/pipeline | Ignores PO.expected_delivery_date already present in staging. All snapshot.in_transit is placed at min(meanlead,horizon−1), even accelerating beyond-horizon stock. No distinction between committed ordered quantity and confirmed delivered-equivalent receipt. |
| P0 | inventory groupby SKU | Chooses one latest row perSKU rather than reconciling locations. Multiple warehouses can lose stock or mix inconsistent snapshots. |
| P1 | supply estimator | Open unreceived POs become fill0 without distinguishing overdue failure from not-yet-due censoring; partial receipts are collapsed. Same-week supplier events overwrite one another. |
| P1 | `SignalStore.series` | Filters observation timestamp, not publication/availability timestamp. Monthly PortWatch sums whole month but stamps28th; revised/full-month data can appear available too early. |
| P1 | `_state_for` and `estimate` | No explicit as-of or persistent TrackerBank passed by live API; implemented hysteresis is not persisted across requests. US demand outlook is hardcoded even for ProjectB. |
| P1 | `FoldInputs.supplier_of` | One supplier perSKU, supplier route is a scalar tag. It cannot encode alternate quoted source+route choices, shared segments or genuinely substitutable complete paths. |
| P1 | model/economics boundary | Legacy recourse-only objective has no full alternate-source landed-price/payment/FX ledger. Cheaper route or supplier conclusions require the new economic contract. |

## Reuse and integration boundaries

- Reuse typed money, pack/MOQ handling, solver status, fill/lead history concepts,
  audit hashes, incumbent comparison, and explicit fallback diagnostics.
- Keep old scenario/risk implementations as comparators, not universal route
  inference. A weather-region copula is not a transport network dependency graph.
- Use canonical operator-owned histories: SKU-location inventory, PO line,
  accepted receipt, observed/available times, quote, lane, service target,
  units/currency and immutable provenance. Validate partials and cancellations.
- Canonical routes must be ordered segment paths from actual origin to actual
  destination with border/port/carrier modes, shared exposures and alternatives.
  Do not map every Aqaba arrival to a Bab-el-Mandeb exposure.
- Public providers return bounded, timestamped evidence with availability,
  retrieval status and freshness. They do not directly return a calibrated
  supplier-failure probability. Operator response evidence should update their
  uncertain effect mapping rather than silently label it measured.
- The new controller should be isolated from legacy `FoldInputs` assumptions,
  consume a validated as-of request, emit recommendation-only results, and keep
  each candidate under one physical and financial evaluator.
- Expose normal inventory, network exposure, signals, alternate plans, risk
  economics, evidence and audit in the UI. Keep configured targets, predicted
  service and realized service distinct; no autonomous PO write-back.

## Security and persistence assessment

Existing deployed-environment auth is enforced in `api/dependencies.py`;
authenticated principal takes precedence over a query-selected operator.
`DBManager` resolves separate per-operator vaults. Staging table allowlists,
upload limits and lineage columns are useful foundations. Existing development
mode remains permissive, and legacy rate limiting defaults off; these are not
appropriate defaults for a new remotely exposed expensive endpoint.

Migration013 already has locations, expected PO dates, receipt identifiers and
upload lineage, but the adapter discards several of them. Migrations014–015
add economic provenance and supplier origin, not a canonical multi-leg route
graph, versioned alternative quotes, or approval/event lifecycle.

The new experimental API should not silently migrate or write customer vaults.
Require tenant consistency, bounded request sizes/problem dimensions and a
mandatory request cap. Bind caches/decisions to immutable input fingerprints.
Never retrieve arbitrary user-supplied URLs on the provider path. Persisted
approvals, write-back, distributed rate limits and a security review remain
separate launch requirements. This audit is not security certification.

## Evidence preservation

The old causal and rejected PR20 evidence is untouched. This audit used fresh
development seeds and in-memory data only; no operator/training database was
read or modified for the probes. Minimal same-scenario parity reproduction is
kept alongside this report as `reproduce_legacy_service_mismatch.py`.

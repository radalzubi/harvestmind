# P1 final blocker B: pre-registration of the narrow confirmation-floor rule

Written at `aed5aba` after the read-only phase-1 trace (`scripts/p1_gate_trace.py`,
`closure/gate_trace_*.json`) and BEFORE any code change or run. Corrections are appended, dated, never
edited in place. Benchmark, fixtures, seeds, tolerance, the N / R / S classifications, terminal valuation,
candidate grids, capital tie-break, alternatives loop and every P0 rule are unchanged.

## 1. Hypothesis

A review the P1 purchasing planner owns (calm state, no active or decaying driver, LEAN regimes, no
confirmed decline, no recovery obligation, no service deficit) whose every declared stress is the
identity, and whose chosen candidate meets every service target and shows an established economic
benefit over the incumbent, should not have that candidate vetoed by the disruption confirmation's
incumbent-level per-service floor, whose purpose is protection of service under a credible stress.

## 2. Phase-1 trace (B seed 41003, `closure/gate_trace_B_fixed_order_cost_replace_sold_41003.json`)

| review | state | owner | on hand | chosen | candidate period-0 order | incumbent order | fitted confirmation cost (incumbent / candidate) | identity-stress worlds: incumbent service / candidate service | gate |
|---|---|---|---|---|---|---|---|---|---|
| 2 | CAPITAL_OPTIMIZATION | P1 (calm, LEAN, activity 0, no flags) | 996 | cadence_4 | none (defer) | 100 | 9,112 / 6,238 | 1.000 / .975 | REJECTED: physically usable, service target (.95) met, cost cap met, per-service floor failed |
| 3 | CAPITAL_OPTIMIZATION | P1 | 990 | stochastic | none | 101 | 9,331 / 6,459 | 1.000 / .988 | REJECTED: floor only |
| 9 | CAPITAL_OPTIMIZATION | P1 | 483 | joint_recovery (fitted) | none | 99 | 9,036 / 6,280 | 1.000 / .985 | REJECTED: floor only |
| 0, 5 | NO_ACTION / CAPITAL_OPTIMIZATION | P1 | 150 / 891 | cadence_2 / cvar | 1,071 / none | 99 / 100 | 9,187 / 6,545; 9,111 / 6,283 | .997 / .991; 1.000 / .991 | passed on the not-worse fallback (fall inside the 1% tolerance) |

Every rejected review: physically usable on every world, `service_met` true, `within_downside` false
through the per-service floor alone (line 1150 of `planner.py`: `b < _floor(req_gate, a, s) - tolerance`
with the incumbent basis), the not-worse fallback also failing on the same floor
(`_priority_consistent(req_gate, ...)` at line 1035). The retained action is the incumbent's weekly
replace-sold order of about 100 units (the seven such orders across the seeds of J16b / K7). The vetoed
"lot" is the economic plan: no top-up now, the next EOQ-sized lot later.

Answers to the five phase-1 questions: (1) yes, the veto is confined to the declared-stress confirmation
layer; (2) yes, the declared stress is "nil" (fill 1.0, lead +0, demand x1.0: the identity); (3) yes,
regime LEAN, activity 0, no flags, no decaying driver, no notes, owner reasons "no declared protection
mandate, calm screen state, no active or decaying driver, every SKU/location lean, no recovery
obligation"; (4) yes, from planner ownership, `is_protection_mandate` over the declared stresses,
`recovery_mode`, and the confirmation's own outcome; (5) yes, the predicate requires P1 ownership, and
every P0 cell is P0-owned on every review (K7).

## 3. Exact predicate (rule B-F)

In `plan()`, for the chosen candidate's declared-stress confirmation only:

```
waive_incumbent_floor =
      ownership.owner == PURCHASING_ECONOMICS                       # existing router decision
  and not any(is_protection_mandate(s) for s in req.stresses)     # every declared stress is the identity
  and not recovery_mode
  and accepted and benefit note is None                           # confirm_service_first established a positive economic benefit
                                                                  # (bootstrap lower bound > 0); NOT a capital tie-break, NOT symmetric
  and service_ok(req, candidate_rows)                             # meets every target on the fitted confirmation
```

When true, the per-service floor of that confirmation uses the target basis (`min(incumbent level,
target)`) in the `downside_ok` loop and in the not-worse fallback of `stress_gate` for that call; the
per-world cost cap, physical usability on every world, `service_met` on the stress worlds, priority
consistency and materiality are unchanged. When false, nothing changes.

Allowed states: P1-owned calm reviews (NO_ACTION, NORMAL_REPLENISHMENT, CAPITAL_OPTIMIZATION) with
identity stresses and an economically established candidate. Excluded: any P0-owned review (declared
mandate, escalation off, PROTECT / RECOVER / NETWORK_ALLOCATION / ESCALATE_UNKNOWN, active or decaying
driver, non-LEAN regime, confirmed decline, recovery obligation, service deficit), recovery mode, any
non-identity declared stress, capital tie-break acceptances (note "capital"), symmetric confirmations,
the alternatives loop (unchanged, keeps the incumbent floor), and candidates that miss a target.

Difference from the rejected broad T-B: T-B changed the basis for every gate on every P1-owned review
(stress floor, alternatives loop, symmetric path, tie-break survivals). B-F touches one gate call, only
for a candidate whose benefit the fitted confirmation has already established, and leaves the tie-break
and alternatives paths under the incumbent floor. On A the six extra T-B interventions were three
tie-break survivals and three alternatives-loop admissions: both paths are excluded here.

## 4. Pre-registered predictions and pass criteria (recorded before running)

* B: the seven retained ~100-unit orders become deferrals; B moves from +2.66% to about +1.6% (the
  value it took under broad T-B, whose B acceptances were all benefit-established), PASS at 52 and at
  every endpoint 40-52 with the magnitude still outside the +/-1 pp band (class E). Criterion: B <= +2.00%.
* A: interventions stay at or below a quarter of reviews on both records (legacy <= 8 / 33, declared
  <= 39 / 156), abstentions preserved; cost within tolerance. Criterion: the legacy expectation file's
  `action` check passes and the declared delta stays <= 2%.
* Q: declared service .991 unchanged within .003 and delta within tolerance; legacy service at or above
  its .98 target (recorded as a control; the declared benchmark is the gate).
* T: stays closed (<= 2%; expected -0.3 to -0.7%). G, I, P, C, O: within tolerance and within 0.5 pp of
  the T-A-only record. Genuine protection still routes to P0 (Q, O, M ownership counts unchanged).
* P0 six-cell arm: decision-identical apart from the recorded cell-21 / cell-108 wall-clock variability
  (the predicate cannot be true on a P0-owned review).

No threshold in the predicate is numeric or tuned: it reuses the router's decision, the stress-mandate
test, the recovery flag and the confirmation's own benefit outcome. No fixture, seed or quantity appears.

## 5. One-fix rule

If B stays above 2%, or any valid control fails, the rule is reverted, the adverse evidence is kept, and
the verdict is "P1 CORE ARCHITECTURE PASS — B REMAINS OPEN" with the residual quantified. No second
remedy without authorization.

## 6. Dated outcome (2026-09-09, after phases 4-5): rule B-F REJECTED under the one-fix rule

* Phase 4, B alone (`closure/horizon52_bf_B.jsonl.gz`): +2.66% -> +1.60% (seeds +1.71 / +0.34 / +2.75),
  PASS at every endpoint 40-52, magnitude 1.55 pp (class E), retained ~100-unit orders 7 -> 1 (the
  PROTECT review), service 1.000, solve time p50 .7-.8 s: the prediction of section 4 met exactly.
* Phase 5, declared-benchmark controls (`closure/horizon52_bf_controls.jsonl.gz`): every control passed
  and A and Q were unchanged in behaviour (A 43 actions / 21 abstentions, +0.81%; Q 20 actions, .991,
  +0.17%); T -0.57%, G -0.67%, I +0.24%, P +0.59%, C +0.13%, O +0.13%; genuine protection still P0-owned.
* The legacy 12-week record (`fixtures_product_defaults_bf.jsonl`, 17 / 20): Q +0.85% -> +3.11%, service
  .980 -> .965 against its .98 target. Traced (`closure/gate_trace_Q_volatile_demand_high_target_4100*_legacy.json`):
  seed 41003 review 8 (four periods left in the shrinking horizon) was waived, bought 44 units instead
  of the incumbent's 155 on an ex-ante estimate that met the target on the three fitted worlds, and
  stocked out on the volatile truth the next week (review-9 service .962 -> .541, +404 on that seed);
  seed 41002's waived acceptance bought the incumbent's quantity (no effect); seed 41001 identical.
* Section 4 named legacy Q service at or above .98 as a control and section 5 the consequence. The
  incumbent-level floor on Q is ordinary service protection against an optimistic ex-ante estimate on a
  volatile, high-target SKU, not only disruption protection; the predicate cannot separate the two from
  current state without a volatility or target criterion, which would be a tuned threshold. The rule is
  reverted; the planner keeps the incumbent floor on every review; the tests record the standing
  behaviour; every run record and trace is kept as adverse evidence.

# Failure analysis and release blockers

## Defects found and corrected, without erasing the record

1. **Arrival observation order in developmental replay.** An actually received
   shipment needed to be materialized before that review's decision. The earlier
   850-row validation remains developmental, not accepted final evidence.
2. **Unreceived overdue POs used for immediate transfers.** In the first frozen
   final attempt, insufficient-history ETA used `due_in=0` for expected-but-not-
   received POs. The optimizer could transfer those units today, while independent
   settlement correctly refused absent stock. The fix makes unreceived fallback
   ETA at least one review and adds an independent observed-stock bound shared
   across every outgoing arc. Tests cover quote fallback, an externally optimistic
   world, and multiple arcs sharing the same ten real units. Source checkpoint
   `a5a31fd` preserves the defective implementation; `488ab4c` preserves the fix.
3. **UI stale report/approval state.** Editing JSON left the previous result
   visible. All edits now invalidate report, decision ID, review status and reason;
   inputs are disabled during computation. Browser verification confirmed old
   report elements disappear immediately. This did not change the frozen engine.

The original final attempt is `evidence/final.jsonl` with seeds16001–16005. The
partial `evidence/corrected/` preflight (19001–19005) was stopped for two typing
errors before analyzing its outcome metrics. It is not a completed experiment.
Only `evidence/final_v2/` (22001–22005) supports the final comparison. No previous
artifact was overwritten, relabelled as fresh, or pooled into a better median.
Because attempts use different seeds, their median difference is **not** a paired
causal estimate of the transfer fix. The focused regression tests establish that
mechanism; the fresh final run evaluates the corrected engine independently.

## Meaning of a failure

- `PHYSICAL_FAILURE`: common independent settlement rejects the decision under
  realized stock, payment or physical constraints. This is not a zero-cost row.
- `INFEASIBLE`: the requested optimization state has no feasible solution under
  its specified constraints. Financial constraints can remain infeasible even
  after the separate service-first recovery solve. This alone does not prove
  that every possible real-world restructuring is impossible.
- `TIME_LIMIT`: no certified accepted optimal plan was returned within the
  configured solve limit. The solver does not silently substitute a heuristic.
- `ABSTAIN`: the gated method has no usable incumbent action to retain.
- A completed row with `service_breach=true` may reflect opening-stock shortage,
  lead-time/forecast error, insufficient supply, cash scarcity or an economic
  tradeoff. The benchmark does not compute an ex-post joint feasibility oracle
  for each truth path, so assigning every breach to unavoidable scarcity would
  be unjustified.

## Exact remaining blockers to the requested unrestricted shadow release

1. **Numerical dust can fail PO exclusivity.** Final cell42, seed22005, robust,
   stops at review5 with `PO amendment conservation or exclusivity`. A diagnostic
   rerun reproduced an outstanding PO of `4.139450919715629e-7` units with returned
   allocation0. The solver residual tolerance accepts this, while settlement
   requires exactly one active option for any non-splittable PO. This is a
   confirmed numerical-tolerance inconsistency, not evidence of a material
   stock-capacity overrun. It remains an explicit fail-closed release blocker:
   establish one unit-aware zero/obligation policy across extraction, replay and
   settlement, and test that policy without silently erasing material orders.
   The frozen evidence has not been retuned or relabelled after discovering it.
2. **Financial tail not constrained.** The optimizer enforces cash, credit and
   LC within the supplied horizon; committed invoices payable afterward are
   reported but not guaranteed financeable. An unrestricted "can afford the
   plan" approval needs a financial tail covering all liabilities, or an explicit
   post-horizon reserve/terminal solvency constraint. Until then, operator review
   must not treat an in-horizon cash result as full affordability certification.
3. **Service/robustness acceptance not established.** Final completed-run service
   breaches and adverse cost pairs are tabulated in BENCHMARK_RESULTS. Sampled
   confirmation and incumbent retention are not a no-harm guarantee. Diagnose
   avoidable errors separately from genuine joint physical/financial scarcity
   before claiming the requested same-or-better service release standard.
   In particular, downward-shift adaptation loses9/20 paired comparisons against
   frozen forecasting, with a worst modeled-cost loss of30.96%. The broad gate
   has279/415 completed-run service breaches and13/415 cost losses vs base-stock.
4. **Operational order-line reconciliation is narrower than enterprise OTIF.**
   Binary completion covers declared outstanding lines and line-level OTIF.
   Multi-SKU complete-order conflicts, retrospective late receipts, revisions and
   cancellation/credit-note reconciliation need adversarial operator-led tests.
5. **Large stochastic operational jobs are not qualified.** 1k/5k deterministic
   sparse sizing succeeded, but dense multi-scenario, multi-customer workloads
   need profiling, an asynchronous job boundary, cancellation/timeouts and shared
   worker quotas. The synchronous v2 API is intentionally capped at20SKUs.
6. **Repository-wide static security gate still needs triage.** The new path is
   clean, but the inherited listener and two urllib transport findings in
   VERIFICATION prevent representing full-repository security CI as green.

The corrected final contains2,892completed rows,59infeasible solves,13timeouts,
10abstentions and the one numerical-dust settlement rejection. All remain in
the per-run JSONL/CSV. No failed row is assigned a cost of zero.

Additional **evidence gaps**, rather than proof of a defect: no real prospective
operator data, uncalibrated ETA tails, several duplicated disruption mappings,
five unseparated action-value effects, no independent standard MEIO comparator,
and no exhaustive Cartesian experiment. These gaps are not filled by marketing
language or by counting passing unit tests.

The architecture is substantive and the isolated demo is executable. It is not
Oracle parity, an autonomous buyer, or a fully completed commercial specification.

## Status after the PR 24 follow-up (branch `claude/zaad-pr24-release-blockers`)

The six blockers above are the PR 23 record and are kept verbatim. Their
state on the follow-up branch, with detail in [PR24_FOLLOWUP.md](PR24_FOLLOWUP.md):

| Blocker | State | What changed |
|---|---|---|
| 1 Numerical PO dust | Resolved | One unit-aware zero policy (`zaad/full/tolerance.py`) shared by extraction, replay and settlement; dust POs close instead of failing exclusivity; material orders are never erased. |
| 2 Financial tail | Resolved for declared obligations | Terminal solvency row in the model and a matching settlement check; reports carry the reserve and headroom. Not a certification beyond the declared credit line. |
| 3 Downward-shift adaptation | **Open** | Asymmetric, soft and ensemble rules were built and measured on new seeds. None beats the frozen symmetric rule on decrease cells; the cause is gated-planner proxy chattering under stress rejection, not the forecast. Adverse results retained. |
| 4 Order-level OTIF | Semantics resolved, field validation open | Revisions, supersession, cancellation, partials, late receipts, complete-order and order OTIF are defined, modeled and settled. No real revision history has been run. |
| 5 Large jobs | Boundary resolved, capacity open | Bounded asynchronous job path with tenant isolation, quotas, timeouts, cancellation and durable reproducible results. Not load-profiled at its limits. |
| 6 Static security | Resolved | Declared bind scope and validated transport targets; Bandit medium/high clean on `api`, `infrastructure`, `zaad`. |

The PR 24 selector was also corrected: strict SLA gating whenever targets are
achievable, priority-weighted recovery only when they are not, a
tolerance-scaled material margin, ranking over every optimal candidate, and a
stress gate consistent with weighted recovery. Verdict: NEEDS FURTHER
ENGINEERING.

## Service reliability branch (`claude/zaad-service-reliability`)

Blocker 3 (service/robustness acceptance) is addressed by the reliability engine profile:
calibrated demand and supply uncertainty, route-derived failure domains, quantile (CVaR)
protection, an evidence-weighted hedged candidate, service-first acceptance, a stress gate
that asks for not-worse-than-incumbent when the declared stress makes the SLA impossible,
and per-service shortage classification. Development3 and validation3 evidence, every
adverse pass included, is in [SERVICE_RELIABILITY.md](SERVICE_RELIABILITY.md). The frozen
profile remains selectable as `engine_profile: "pr24"`.

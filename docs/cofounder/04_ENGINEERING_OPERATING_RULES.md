# ZAAD Engineering Operating Rules

## 1. Purpose

ZAAD's optimizer is difficult to validate because a change can look better on one benchmark while quietly changing economics, information timing, service behavior, or comparator semantics elsewhere.

This document defines the working rules a technical co-founder should follow before changing the optimizer.

---

## 2. Separate product questions by ownership

Do not let a new phase duplicate an older phase's responsibility.

Current ownership:

- **P0:** protection and recovery
- **P1:** total purchase commitment and purchasing economics
- **P2:** network placement/transfers
- **Sector Physics:** physical feasibility by SKU/sector
- **P3:** source decomposition and sourcing risk/economics
- **P4:** conditionality / adaptive recourse

Future phases should preserve the same principle.

When adding a feature, first answer:

> **Which phase owns this decision, and which existing phase should remain unchanged?**

---

## 3. Pre-register before tuning

Before changing behavior for a hard fixture or regression:

1. write the hypothesis,
2. identify the mechanism,
3. define the expected causal effect,
4. define control fixtures,
5. define pass/fail criteria,
6. only then implement.

Do not repeatedly edit a fixture, tolerance, seed, or metric until the desired answer appears.

Preserve failed experiments in evidence when they materially informed the final design.

---

## 4. Tiny causal fixtures before broad benchmarks

Before running thousands of reviews, create a minimal fixture that proves the mechanism.

Examples:

- P2 transfer conservation,
- sector age-at-receipt,
- P3 shared supplier capacity,
- P4 non-anticipativity,
- future P8 container cube/weight,
- future P9 portfolio capital ceiling.

A benchmark can show that something moved. A causal fixture explains why.

---

## 5. Invariants are mandatory

Each phase should define mathematical/physical invariants that must hold independent of benchmark economics.

Examples already relevant:

- inventory conservation,
- no double allocation,
- source capacity,
- shared supplier capacity,
- MOQ/MOV,
- pack/pallet integrity,
- transfer lead time,
- shelf-life/FEFO rules,
- cold-chain eligibility,
- economic reconciliation,
- no autonomous execution.

P4 must add:

- same observable information → same decision,
- no future information leakage,
- committed decisions remain committed unless explicit P4B modification rights exist,
- information-set probability consistency.

---

## 6. Independent settlement is a gate

Do not trust the optimization model merely because the solver returned an incumbent.

Use independent settlement/replay to confirm:

- physical feasibility,
- economic accounting,
- service consequences,
- source constraints,
- cash/liquidity constraints,
- inventory and transfer conservation,
- expiry/age rules.

If the optimizer and settlement disagree, treat that as a correctness problem.

---

## 7. Solver status is not product truth

A solution may be:

- optimal,
- feasible at time limit,
- infeasible,
- no incumbent,
- physically invalid,
- economically non-comparable.

A time-limited incumbent may be usable only when:

1. model residuals are acceptable,
2. physical settlement passes,
3. its gap is suitable for the comparison being made.

Do not silently promote a weak solver result to a customer recommendation.

---

## 8. Preserve frozen behavior by default

When a new phase is disabled, prior behavior should remain unchanged unless an explicitly documented correctness correction is being made.

Required regression pattern:

- P0 protocol,
- P1 canonical identity/invariants,
- P2 fixtures/principles/replay identity,
- sector fixtures/invariants,
- P3 fixtures/invariants/adversarial/performance structure.

If a difference occurs:

1. determine whether it is semantic,
2. determine whether it is an objective-flat tie,
3. determine whether the comparator itself is nondeterministic,
4. prove causality before accepting it.

Do not simplify a nuanced replay result into a false 100% identity claim.

---

## 9. Keep correctness corrections explicit

Sometimes a later phase exposes an earlier bug.

Allowed response:

- isolate the defect,
- show that the old behavior was wrong,
- write a correction record,
- prove the correction's scope,
- rerun affected evidence,
- keep historical freeze tags unchanged.

Not allowed:

- moving old tags,
- rewriting old evidence to make history look cleaner,
- calling a correctness change "no semantic change" when it is not.

The age-at-receipt replay correction is the model example.

---

## 10. Performance engineering rules

When runtime is bad:

1. capture the exact request/snapshot,
2. instrument build time vs solver time vs settlement/report time,
3. record variables, rows, binaries, nodes, gap, first incumbent, proof time,
4. inspect formulation strength,
5. inspect symmetry,
6. inspect big-M values,
7. inspect repeated candidate solves,
8. only then consider infrastructure or parallelism.

Prefer exact mathematical reformulation to simply raising the timeout.

Known lessons:

- P2: redundant FEFO symmetry binaries caused severe solver work.
- P3: loose activation big-M weakened the LP relaxation; host CPU contention amplified the wall-time outlier.

Do not erase infrastructure effects, but do not use them to hide formulation problems.

---

## 11. Complexity must be bounded deterministically

Do not rely only on wall-clock timeout for protection.

Bound relevant request dimensions such as:

- SKUs,
- periods,
- worlds,
- review epochs,
- information sets,
- locations,
- suppliers,
- routes,
- containers,
- expected binary count.

Reject or route oversized workloads before constructing an accidental combinatorial explosion.

---

## 12. No future-information leakage

This becomes especially important in P4 and historical replay.

At any decision time, the optimizer may use only information that would have been known then.

No:

- future realized demand,
- future supplier fill,
- future delays,
- future route failures,
- future labels,
- holdout outcomes.

Rolling historical replay must be causal.

---

## 13. Untouched holdout discipline

Do not inspect protected holdouts during development.

Use:

- development data for building,
- validation data for model/architecture selection,
- untouched holdout for final evaluation.

If a holdout influences a code change, it is no longer untouched and must be replaced or explicitly reclassified.

---

## 14. Evidence categories must remain distinct

Do not conflate:

### Engineering evidence

Synthetic fixtures, invariants, replay identities, solver benchmarks.

### Historical real-data evidence

Counterfactual replay on real customer history.

### Shadow evidence

Recommendations produced prospectively while the operator still acts independently.

### Live realized evidence

Measured outcomes after approved ZAAD actions are actually implemented.

Only the last two approach credible product-performance claims. Even historical replay requires careful causal interpretation.

---

## 15. Customer claims

Never convert configured fixture economics into sales claims.

Avoid:

- guaranteed savings,
- guaranteed inventory reduction,
- guaranteed service improvement,
- annualized synthetic benchmark results.

If real history shows the incumbent is efficient, report that.

---

## 16. Human approval is a safety invariant

Every recommendation remains human-reviewed unless a future explicitly authorized product phase changes execution authority.

P4 adapting a recommendation later does not imply autonomous execution later.

P4B changing an open PO does not imply ZAAD is allowed to cancel/expedite it automatically.

---

## 17. Release protocol

Preferred efficient release flow:

1. final candidate is frozen locally,
2. exhaustive CI on exact candidate,
3. no code changes after the exhaustive candidate gate,
4. merge,
5. verify tree/ancestry identity,
6. deploy exact runtime,
7. run bounded production smokes,
8. inspect logs,
9. create immutable release-runtime tag,
10. merge docs-only closeout separately if needed.

Do not repeatedly rerun the full expensive suite when the runtime tree is provably identical.

---

## 18. Security rules for optimizer work

Even before the dedicated hardening phase:

- tenant state must remain tenant-bound,
- malformed input must fail closed,
- unknown enum/state values must be rejected,
- resource exhaustion must be bounded,
- solver/model internals should not expose secrets,
- raw customer data should not leak into logs,
- recommendations must retain provenance/auditability.

Later security hardening should cover auth/RBAC/IDOR/CSRF/XSS/upload abuse/rate limits/secrets/dependencies/backups/deletion/export/audit.

---

## 19. Before coding a new optimizer feature

Answer all of these:

1. What exact operator decision is being added?
2. Who owns it?
3. What information is available when the decision occurs?
4. What is irreversible?
5. What physical constraints apply?
6. What economic ledger entries change?
7. What incumbent policy is the comparator?
8. What tiny fixture proves the mechanism?
9. What invariants must always hold?
10. What earlier phases must remain identical?
11. What complexity/performance gate applies?
12. What would falsify the feature's value?

If these are not answered, the feature is not ready for implementation.

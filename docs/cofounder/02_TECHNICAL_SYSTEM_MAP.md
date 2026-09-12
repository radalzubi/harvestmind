# ZAAD Technical System Map

## 1. Purpose

This document explains how the repository fits together technically. It is not a substitute for reading the implementation or evidence; it is the map a new co-founder should carry while reading them.

---

## 2. Canonical data-to-decision flow

Conceptually:

```text
customer operational data
    ↓
secure tenant data / intake
    ↓
normalization + provenance
    ↓
forecast / demand state + supplier/lead-time state
    ↓
scenario/world generation
    ↓
canonical request/state
    ↓
P0/P1/P2/P3 decision engine + sector physics
    ↓
independent settlement / physical-economic validation
    ↓
selector / incumbent comparison / materiality
    ↓
operator-facing report
    ↓
human approval
```

The earlier architecture record describes the original flow as:

```text
operator CSV/JSON + dated licensed signals
  -> full/contracts.py + intake.py
  -> forecast.py + eta.py
  -> worlds.py
  -> model.py
  -> settlement.py
  -> planner.py
  -> shadow.py -> authenticated API
```

See [`docs/zaad_full/ARCHITECTURE.md`](../zaad_full/ARCHITECTURE.md).

---

## 3. Major repository concepts

### `zaad/full`

This is the core planning/optimization path. Important responsibilities include:

- request/contracts,
- model construction,
- economics,
- settlement/replay,
- planner/selector logic,
- reporting,
- incumbent/alternative comparison,
- P0/P1 integration.

### `zaad/meio`

Network / P2 layer.

Responsibilities include:

- multi-location state,
- transfer decisions,
- shared inventory,
- location-level service,
- network conservation,
- P2-specific performance structure.

### `zaad/sectors`

Sector-physics declaration/resolution.

One shared optimizer uses per-SKU physics for:

- COMMERCIAL,
- PRODUCE,
- MEAT_SEAFOOD.

This layer should remain declarative. It is not a separate planner.

### `zaad/sourcing`

P3 source-portfolio declarations and logic.

Responsibilities include:

- source-share constraints,
- switching cost,
- source risk groups,
- declared correlation/common-cause risk,
- incumbent source mix,
- source-level reporting.

P3 does not own the total replenishment commitment. P1/P0 own the total commitment; P3 owns how that commitment is decomposed across sources when sourcing is active.

### API / workspace adapters

These translate persisted/customer-facing state into canonical optimizer requests. The canonical path is preferred; legacy paths are intentionally constrained/deprecated.

### Evidence and scripts

`docs/zaad_full/evidence/` and supporting scripts are not decorative. They are part of the engineering process:

- pre-registration,
- fixtures,
- invariants,
- adversarial cases,
- replay comparisons,
- performance profiles,
- freeze/closeout records.

---

## 4. Ownership boundaries

### P0 — protection/recovery

Owns:

- disruption protection,
- recovery/unwind,
- protection-specific acceptance logic,
- service protection under disruption.

Does not own normal cycle-stock purchasing economics.

### P1 — purchasing economics

Owns:

- total replenishment commitment,
- when to buy,
- how much to buy,
- whether to buy,
- cadence,
- MOQ/MOV/packs/pallets,
- freight/order economics,
- payment/carry/finance,
- economic lot continuation.

### P2 — network

Owns:

- where stock sits,
- transfers,
- pooling,
- location-level consequences,
- network conservation.

### Sector physics

Owns physical feasibility and age/state behavior, not decision policy.

### P3 — sourcing portfolio

Owns source decomposition and source-specific constraints/economics.

### P4 — adaptive recourse, next

Will own **conditionality over time**:

- review epochs,
- information sets,
- non-anticipativity,
- future actions that may adapt after observable information arrives.

P4 should reuse P0-P3 primitives rather than reimplement them.

---

## 5. Solver/model philosophy

ZAAD uses stochastic LP/MILP formulations with HiGHS as the commercial-free default solver path.

Core engineering principles:

- model the actual economic decision,
- keep physical and accounting constraints explicit,
- independently settle/replay candidate plans,
- accept time-limited solutions only when residuals and physical validation justify it,
- distinguish decision quality from solver proof quality,
- use exact formulation improvements before adding brute-force compute,
- avoid giant generalized scenario-tree abstractions unless evidence requires them.

---

## 6. Independent settlement matters

The model's claimed solution is not automatically trusted.

The settlement/replay path independently checks physical/economic reality such as:

- capacity,
- packs,
- MOQ/MOV,
- transfer timing,
- inventory conservation,
- liquidity/financing,
- expiry/age,
- source constraints,
- accounting reconciliation.

This separation is essential. A solver status alone is not evidence that an executable recommendation is valid.

---

## 7. Scenario/world generation

ZAAD uses compact stochastic worlds rather than one deterministic forecast.

Relevant uncertainty can include:

- demand,
- supplier fill,
- lead time,
- declared disruptions,
- source common-cause risk,
- network demand correlation.

The long-term P6 roadmap expands calibration/model-risk work. The current product should not be described as having fully solved probabilistic calibration on real customer data.

---

## 8. P4 architecture rule

P4 must enforce **non-anticipativity**.

If two scenarios are observationally identical at review time `t`, the action at `t` must be identical.

The model may adapt only after the observable histories diverge.

Preferred representation:

- a small number of review epochs,
- deterministic information-set construction,
- decisions indexed by information set,
- not one independent clairvoyant plan per scenario.

---

## 9. Shared economics

All future phases should reuse one authoritative ledger.

Do not let P7 transport economics, P8 container economics, P9 capital economics, or P4B cancellation economics create parallel accounting systems.

The same real-world cost should map to one place in the ledger.

---

## 10. Future composable architecture

The expanded system should look conceptually like:

```text
Canonical state
    ↓
Uncertainty / scenario layer
    ↓
Shared economics
    ↓
Decision modules
    ├── P0 Protection / Recovery
    ├── P1 Purchasing
    ├── P2 Network
    ├── P3 Sourcing
    ├── P4 Recourse
    ├── P4B Open Commitments
    ├── P5 ATP / Allocation
    ├── P7 Logistics
    ├── P8 Containers
    ├── P9 Capital
    └── P10 Lifecycle
    ↓
Joint solve where constraints truly couple
    ↓
Settlement / validation
    ↓
Human-approved policy
```

Do not build every phase into one monolithic model if decomposition is mathematically valid.

---

## 11. Infrastructure

Current broad infrastructure direction:

- frontend on Vercel,
- FastAPI/Python/HiGHS backend on Fly,
- API at `api.zaadsupply.com`,
- persistent operational/data layer evolving toward managed durable storage,
- large optimization workloads should eventually use async/batch execution rather than assuming every workload is synchronous.

Do not interpret current deployment choices as permanent architecture guarantees.

---

## 12. Performance lessons already learned

Two important examples:

### P2 FEFO symmetry

The original P2 model had unnecessary FEFO binary structure for cohorts that could not affect the modeled horizon. Removing exact symmetry reduced pathological runtimes dramatically without changing economics.

See:

- [`docs/zaad_full/evidence/p2/P2_CLOSEOUT.md`](../zaad_full/evidence/p2/P2_CLOSEOUT.md)

### P3 shared-MOV big-M

A shared-supplier-order formulation used declared source capacity as a loose activation big-M, creating a weak relaxation. Tightening the bound and disabling a problematic root restart on that scoped model class materially reduced runtime. Production host contention had amplified the original outlier.

See:

- [`docs/zaad_full/evidence/p3/perf_closure/P3_SHARED_MOV_PROFILE.md`](../zaad_full/evidence/p3/perf_closure/P3_SHARED_MOV_PROFILE.md)
- [`docs/zaad_full/evidence/p3/perf_closure/P3_PRODUCTION_PERF_AFTER.md`](../zaad_full/evidence/p3/perf_closure/P3_PRODUCTION_PERF_AFTER.md)

General lesson:

> **Profile the formulation first. Do not automatically blame Python, the solver, or infrastructure.**

---

## 13. Known architectural risks

A new technical owner should keep these visible:

- model size can explode as source × SKU × location × period × world × recourse grows,
- shared-CPU production hosts can distort observed latency,
- comparator/tie nondeterminism can look like semantic regression,
- old documents may preserve superseded intermediate failures,
- customer data quality may dominate model sophistication,
- P6 calibration remains incomplete until tested on real history,
- synchronous workspace calls do not scale indefinitely,
- security/tenant isolation/resource exhaustion require dedicated later hardening.

---

## 14. What to inspect in code before modifying anything

At minimum inspect:

- `zaad/full/contracts.py`
- `zaad/full/model.py`
- `zaad/full/settlement.py`
- `zaad/full/planner.py`
- `zaad/full/economics.py`
- `zaad/meio/`
- `zaad/sectors/`
- `zaad/sourcing/`
- canonical API/workspace adapters
- phase-specific tests
- current migration sequence
- current phase evidence closeouts

Then trace a representative request end-to-end before changing the optimizer.

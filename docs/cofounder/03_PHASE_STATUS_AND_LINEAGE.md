# ZAAD Phase Status and Lineage

## 1. Purpose

This file gives a new co-founder the minimum reliable lineage needed to understand what is frozen, merged, released, corrected, or still roadmap-only.

It is intentionally concise. For exact details, read the linked closeouts and release evidence.

---

## 2. Current canonical state

**Current docs main used as the starting point for this onboarding branch:** `ebcd1d0`  
**Current deployed P3 performance-closed runtime:** `61a3e75`  
**Current production validation status:** engineering-validated, not customer/real-data validated.

---

## 3. P0 — Protection & Recovery

**Status:** PASS / FROZEN

Frozen SHA:

- `2e30721`

Authoritative closeout:

- [`docs/zaad_full/evidence/v8/P0_CLOSEOUT.md`](../zaad_full/evidence/v8/P0_CLOSEOUT.md)

Key final conclusions:

- FEASIBLE_TIME_LIMIT can be usable only after residual and physical validation.
- `joint_recovery` is required only under the declared deficit rule when projected service falls materially below target.
- the six-cell protocol became the key P0 regression arm.

Do not reopen P0 casually. Later phases should prove neutrality/compatibility against it.

---

## 4. P1 — Purchasing Economics

**Status:** PASS / FROZEN

Product freeze:

- `f7e1e62`

Evidence freeze:

- `12db66c`

Authoritative closeout:

- [`docs/zaad_full/evidence/p1/P1_CLOSEOUT.md`](../zaad_full/evidence/p1/P1_CLOSEOUT.md)

Important reading warning:

The P1 closeout preserves earlier failed/open passes. Do **not** treat the first verdict in the file as final. The final closure appears later in the file and records:

> **P1 CYCLE-STOCK / PURCHASING ECONOMICS — PASS AND FROZEN.**

Final P1 capability includes dynamic purchasing economics, MOQ/MOV, packs/pallets, freight/load rules, payment/financing/carrying treatment, economic-lot continuation, materiality, and abstention.

---

## 5. P2 — Multi-Echelon / Network Optimization

**Status:** PASS / FROZEN / RELEASED

Product freeze:

- `cab3849`

Evidence freeze:

- `fa615ff`

Release merge/runtime lineage:

- release merge: `9c4ece7`
- release docs closeout later: `ea1ed3a`

Authoritative closeout:

- [`docs/zaad_full/evidence/p2/P2_CLOSEOUT.md`](../zaad_full/evidence/p2/P2_CLOSEOUT.md)

Important history:

The first P2 runtime gate failed. A later exact FEFO symmetry-elimination reformulation reduced runtime dramatically while preserving objectives/decisions. The failure is intentionally preserved in the evidence.

Do not rewrite history to imply P2 passed immediately.

---

## 6. Three-Sector Physics

**Status:** MERGED / RELEASED

Original product freeze:

- `43d769f`

Original evidence freeze:

- `4f358f7`

Release merge:

- `dca3d48`

Exact deployed runtime after JSON-safety correction:

- `5ca3772`
- tag: `sector-physics-release-runtime`

Final docs/bookkeeping main later advanced to:

- `7bc4206`

Authoritative closeout:

- [`docs/zaad_full/evidence/sectors/SECTOR_PHYSICS_CLOSEOUT.md`](../zaad_full/evidence/sectors/SECTOR_PHYSICS_CLOSEOUT.md)

Important correction:

Historical replay later received an **age-at-receipt** correctness correction so purchased perishable lots preserve declared remaining life instead of replaying as fresh. This was a historical replay correction; the live planner already used the declared receipt life.

Relevant addendum:

- [`docs/zaad_full/evidence/sectors/ADDENDUM_2026-09-11_P3_REPLAY_RECEIPT_LIFE.md`](../zaad_full/evidence/sectors/ADDENDUM_2026-09-11_P3_REPLAY_RECEIPT_LIFE.md)

Historical sector freeze tags must not be moved to hide this lineage.

---

## 7. P3 — Supplier / Sourcing Portfolio

**Status:** MERGED / RELEASED / PERFORMANCE-CLOSED

Original local product freeze:

- `9e496ed`
- tag: `p3-frozen-product`

Original evidence freeze:

- `628d49f`
- tag: `p3-frozen`

Corrective evidence:

- `fb91946`
- tag: `p3-corrective-evidence`

Original P3 release runtime:

- `0de6850`
- tag: `p3-release-runtime`

Performance-closed deployed runtime:

- `61a3e75`
- tag: `p3-performance-closure-runtime`

Final docs closeout main:

- `ebcd1d0`

Authoritative closeout:

- [`docs/zaad_full/evidence/p3/P3_CLOSEOUT.md`](../zaad_full/evidence/p3/P3_CLOSEOUT.md)

Performance closure:

- [`docs/zaad_full/evidence/p3/perf_closure/P3_SHARED_MOV_PROFILE.md`](../zaad_full/evidence/p3/perf_closure/P3_SHARED_MOV_PROFILE.md)
- [`docs/zaad_full/evidence/p3/perf_closure/P3_PRODUCTION_PERF_AFTER.md`](../zaad_full/evidence/p3/perf_closure/P3_PRODUCTION_PERF_AFTER.md)

Critical wording to preserve:

> P3 had a real formulation inefficiency, and production host contention amplified it into the ~218 s outlier.

Do **not** say P3 was fine all along.

Also preserve exactness language:

- the P3 replay identity was **2,273 / 2,304**, with 31 proven equal-cost C6 transfer ties/cascade effects,
- not 2,304 / 2,304.

---

## 8. P4 — Adaptive Recourse

**Status:** next authorized optimizer phase; not yet part of the released stack.

P4's purpose is to allow selected future actions to depend on information that becomes observable later while enforcing non-anticipativity.

Core requirements:

- review epochs,
- observable state,
- information sets,
- same information → same action,
- conditional future purchases,
- conditional source mix,
- conditional transfers,
- conditional protection changes,
- static vs adaptive vs perfect-information diagnostics.

Do not build a giant generic scenario-tree framework unless evidence forces it.

---

## 9. Expanded roadmap after P4

The strategy document currently recommends:

- **P4B** — Open PO / Commitment Recourse
- **P5** — ATP + Scarce-Supply Allocation + Economic Service Classes
- **P6** — Decision-Aware Uncertainty + Demand/Supply Calibration
- **P7** — Import Logistics Optimization
- **P8** — Container & Load Portfolio Optimization
- **P9** — Portfolio Capital Optimization
- **P10** — Product Lifecycle, Substitution & Supersession

Full rationale and industry evidence:

- [`docs/zaad_full/OPTIMIZER_PRODUCT_STRATEGY_AND_INDUSTRY_ROADMAP.md`](../zaad_full/OPTIMIZER_PRODUCT_STRATEGY_AND_INDUSTRY_ROADMAP.md)

---

## 10. Untouched / protected evaluation work

The repo's engineering process has intentionally protected later evaluation assets and phases from tuning.

Historically protected items include:

- Validation7,
- Validation8,
- holdout4,
- Network Twin work,
- later P4+ phases until explicitly authorized.

A new co-founder should preserve that discipline. Do not inspect protected holdouts merely to "understand the data" if they are still reserved for untouched evaluation.

---

## 11. Production vs docs commits

Do not confuse a later docs-only main SHA with the exact deployed runtime.

Example:

- `ebcd1d0` is the later documentation main,
- `61a3e75` is the performance-closed deployed P3 runtime.

When debugging production, use the exact runtime commit/tag, not merely the latest main SHA.

---

## 12. Lineage rules

- Historical freeze tags are immutable records.
- A later correctness correction should be documented as a correction, not hidden by moving old tags.
- Docs-only commits do not imply runtime changes.
- Release-runtime tags identify exact deployed semantics.
- Product/evidence tags may differ intentionally.
- A phase can be engineering-valid without being real-data validated.

This lineage discipline is part of ZAAD's correctness model, not administrative overhead.

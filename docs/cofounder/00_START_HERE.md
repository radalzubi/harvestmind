# ZAAD Co-Founder Onboarding — Start Here

**Purpose:** This folder is the canonical human/AI onboarding layer for a new ZAAD co-founder. It does not replace phase evidence or source code; it tells the reader what to read, what is authoritative, and how the pieces fit together.

**Current source of truth for the system:** [`docs/zaad_full/CURRENT_SYSTEM.md`](../zaad_full/CURRENT_SYSTEM.md) (released stack P0-P5 + P4B V1, runtime `1851f40` / Fly v23, tag `p4b-v1-release-runtime`).  
**This onboarding set was written at `main` `ebcd1d0` (P3 runtime `61a3e75`); phase lines below are historical where they predate P4, P5 and P4B.**  
**Current product validation status:** **ENGINEERING VALIDATED; NOT REAL-DATA VALIDATED.**  
**No customer savings claims are established by the repository.**

---

## 1. What ZAAD is

ZAAD is building a **human-approved stochastic decision layer for import-heavy distributors**.

The operating thesis is:

> **Less inventory when you don't need it. More protection where you do.**

ZAAD is not intended to replace the customer's ERP. It is intended to sit above existing ERP/planning data, reconstruct the operating state, stress-test decisions, and recommend economically justified actions.

The current decision stack answers:

1. **P0 — How much protection is justified?**
2. **P1 — When should we buy, how much, and should we buy at all?**
3. **P2 — Where should inventory sit across the network?**
4. **Sector Physics — What physical rules differ across commercial goods, produce, and meat/seafood?**
5. **P3 — Which supplier/source mix should provide the commitment?**
6. **P4 — What should change later when new information actually becomes observable?** (released)
7. **P5 — Which customer order gets scarce supply, and what is promised?** (released)
8. **P4B V1 — Keep, defer, expedite, reduce, cancel or split an open purchase order?** (released)

The expanded strategic roadmap then adds open-PO intervention, scarce-supply allocation/ATP, uncertainty calibration, import-logistics decisions, container composition, capital allocation, and lifecycle/supersession.

Read the full industry-backed roadmap:

- [`docs/zaad_full/OPTIMIZER_PRODUCT_STRATEGY_AND_INDUSTRY_ROADMAP.md`](../zaad_full/OPTIMIZER_PRODUCT_STRATEGY_AND_INDUSTRY_ROADMAP.md)

---

## 2. Read these files in this order

1. [`00_START_HERE.md`](./00_START_HERE.md) — this file.
2. [`01_PRODUCT_THESIS_AND_MARKET.md`](./01_PRODUCT_THESIS_AND_MARKET.md) — what problem ZAAD is solving, who it is for, and what should/should not be claimed.
3. [`02_TECHNICAL_SYSTEM_MAP.md`](./02_TECHNICAL_SYSTEM_MAP.md) — data flow, optimizer ownership boundaries, shared architecture, infrastructure.
4. [`03_PHASE_STATUS_AND_LINEAGE.md`](./03_PHASE_STATUS_AND_LINEAGE.md) — exact phase status, important SHAs/tags, current release lineage, known corrections.
5. [`04_ENGINEERING_OPERATING_RULES.md`](./04_ENGINEERING_OPERATING_RULES.md) — how ZAAD engineering should be changed, validated, frozen, released, and protected from false evidence.
6. [`05_TEAM_AND_WORKING_OWNERSHIP.md`](./05_TEAM_AND_WORKING_OWNERSHIP.md) — current co-founder team and recommended working ownership.
7. [`docs/zaad_full/REPOSITORY_CLEANUP_AUDIT.md`](../zaad_full/REPOSITORY_CLEANUP_AUDIT.md) — what every directory is, its classification and why it is kept (replaces the never-written reading map).
8. [`docs/zaad_full/OPTIMIZER_PRODUCT_STRATEGY_AND_INDUSTRY_ROADMAP.md`](../zaad_full/OPTIMIZER_PRODUCT_STRATEGY_AND_INDUSTRY_ROADMAP.md) — full future roadmap and verified industry context.

Then read the authoritative phase closeouts:

- [P0 closeout](../zaad_full/evidence/v8/P0_CLOSEOUT.md)
- [P1 closeout](../zaad_full/evidence/p1/P1_CLOSEOUT.md)
- [P2 closeout](../zaad_full/evidence/p2/P2_CLOSEOUT.md)
- [Sector physics closeout](../zaad_full/evidence/sectors/SECTOR_PHYSICS_CLOSEOUT.md)
- [P3 closeout](../zaad_full/evidence/p3/P3_CLOSEOUT.md)
- [P3 production performance closure](../zaad_full/evidence/p3/perf_closure/P3_PRODUCTION_PERF_AFTER.md)

---

## 3. Source-of-truth hierarchy

When documents conflict, use this order:

1. **Current source code on the exact commit being discussed.**
2. **Later corrective/release evidence that explicitly supersedes an earlier record.**
3. **Latest phase closeout section/amendment.**
4. **Earlier development logs / preregistrations / benchmark records.**
5. **These onboarding summaries.**
6. **Chat history, memory, founder recollection, or marketing language.**

Important: several closeout files preserve failed/intermediate states before later closure. Do not read the first verdict at the top of a long file and assume it is the final state. P1 is the clearest example: the file preserves multiple failed passes and later ends with the final PASS/FROZEN closure.

---

## 4. Current high-level status

| Layer | Status |
|---|---|
| P0 Protection & Recovery | PASS / FROZEN |
| P1 Purchasing Economics | PASS / FROZEN |
| P2 Multi-Echelon / Network | PASS / FROZEN |
| Three-Sector Physics | MERGED / RELEASED |
| P3 Supplier / Sourcing Portfolio | MERGED / RELEASED / PERFORMANCE-CLOSED |
| P4 Adaptive Recourse | NEXT AUTHORIZED ENGINEERING PHASE; not yet released |
| P5+ | Roadmap only |
| Real-data customer validation | NOT YET ESTABLISHED |

The current product is technically substantial, but commercial proof remains the important missing category of evidence.

---

## 5. Non-negotiable product principles

- **Human approval:** recommendations are not autonomous purchase orders.
- **Incumbent-first:** if the current operating policy is already materially efficient, ZAAD should be able to return **NO MATERIAL IMPROVEMENT AVAILABLE**.
- **No fake certainty:** external signals must map to physical consequences before affecting decisions.
- **No future leakage:** adaptive policies may use only information actually observable at the decision epoch.
- **One economic ledger:** do not let different optimizer modules double-count the same economic event.
- **One shared engine:** sector differences should be physical profiles, not separate optimizer codebases.
- **ERP overlay:** "Keep your ERP" is a design constraint, not merely sales language.
- **Synthetic evidence is engineering evidence, not customer savings.**
- **Real history decides commercial truth.**

---

## 6. What the new co-founder should understand after onboarding

A successful onboarding pass should leave the reader able to explain:

- the business wedge,
- P0 through P3 in plain English and mathematically,
- why P4 non-anticipativity is critical,
- how COMMERCIAL / PRODUCE / MEAT_SEAFOOD differ physically,
- the canonical data-to-decision path,
- why P0-P3 are intentionally separated by ownership,
- how ZAAD validates and freezes phases,
- why some historical evidence files contain failed states,
- the current production lineage,
- the difference between engineering validation and customer validation,
- the expanded P4-P10 roadmap,
- the major known risks: real-data value, runtime at scale, data onboarding, model-risk calibration, and sales/implementation proof.

If any of those are unclear, continue reading the linked source files before modifying the optimizer.

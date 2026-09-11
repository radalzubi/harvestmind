# P3 supplier / sourcing portfolio optimization: closeout

Branch `claude/zaad-sourcing-p3`, worktree `harvestmind-p3`, parent `main` `7bc4206` (released sector runtime
`5ca3772` plus two docs-only merges). Frozen tags unchanged: `p0-frozen` = `2e30721`, `p1-frozen-product` =
`f7e1e62`, `p1-frozen` = `12db66c`, `p2-frozen-product` = `cab3849`, `p2-frozen` = `fa615ff`,
`sector-physics-frozen-product` = `43d769f`, `sector-physics-frozen` = `4f358f7`,
`sector-physics-release-runtime` = `5ca3772`. Not merged, not pushed, not deployed. Commits: `7da067a` (the
P3 layer, scripts, tests), `33f96cc` (benchmark corrections, replay receipt life, API error code, P0 arm),
`9e496ed` (test isolation from the shared rate limiter) = **frozen product**; the evidence commit
carrying this closeout = **frozen evidence** (`p3-frozen`).

## Verdict

**P3 SUPPLIER / SOURCING PORTFOLIO OPTIMIZATION — PASS AND FROZEN LOCALLY.** Product tag `p3-frozen-product`
= `9e496ed`; evidence tag `p3-frozen` = `628d49f` (this file's first version); corrective evidence
follow-up (this wording, the sector correction records and the receipt-life tests) on a later commit
tagged `p3-corrective-evidence`. Tags are local; nothing pushed.
**Status: ENGINEERING VALIDATED on synthetic fixtures, not REAL-DATA VALIDATED. No savings claimed.**

**Sector semantics statement (corrected 2026-09-11).** Original sector frozen semantics remain preserved
except for one documented correctness correction in physics-enabled historical replay: purchased
perishable lots now retain their declared age-at-receipt / remaining life rather than being replayed
as fresh. Legacy / no-physics behaviour remains identical. The correction changes 14 / 416 authoritative
sector replay decisions, all causally attributed to fixture P3_age_at_receipt, while 26 / 26 sector
fixtures and 19 / 19 invariants remain PASS. The earlier wording "sector physics remains frozen" was too
strong and is withdrawn.

**Release status.** P3 is NOT released. P3 release requires remote exhaustive CI capability restored
(GitHub Actions is billing-blocked at the time of this closeout); no push, PR, merge or deployment has
been made.

## One engine, one more declared layer

No sourcing optimizer, candidate class, supplier score or diversification rule exists. `zaad/sourcing`
declares what the operator knows (shared-risk groups with provenance and correlation, contractual share
limits and committed units, switching / qualification costs, the incumbent source mix) on the frozen
request; `resolve(req)` is None on a legacy request and every hook is unreachable. The frozen joint solve
still chooses the total commitment (P1, or P0 when it owns the review) and its split (P3); the report's
`sourcing` block decomposes it with operator-language reasons. Details: `P3_ARCHITECTURE.md`; audit:
`P3_EXISTING_CAPABILITIES.md`; every experiment and correction: `P3_DEV_LOG.md`.

## Freeze criteria (brief B45)

| criterion | evidence | result |
|---|---|---|
| A source choice | E1, E2, C4, S1, S3: the dominated, dearer-landed, unqualified or physically unusable source never receives quantity | PASS |
| B source splitting | R2, C1, C5, N3: capacity-forced splits; invariant 03 (sum of sources = commitment) | PASS |
| C source-specific economics reconcile | invariants 25, 26; `economics.reconciled` true, no unmapped ledger key | PASS |
| D source capacity | invariants 05, 06; C1, C5, N3 | PASS |
| E MOQ / MOV / pack economics | invariants 07-09; E4, C6, S4 | PASS |
| F payment terms without double counting | invariant 10; E5 | PASS |
| G correlated supply risk | invariants 13, 15; R4, R5 | PASS |
| H no false diversification | R4 (shared plant: no split, sentence present), R6, invariant 16 | PASS |
| I contractual share constraints | invariant 17; C2 on every review with a purchase | PASS |
| J multi-SKU shared source constraints | C5, C6, N3; invariant 06 | PASS |
| K COMMERCIAL | S4, E1-E6 | PASS |
| L PRODUCE | S1, S2 | PASS |
| M MEAT_SEAFOOD | S3 | PASS |
| N network | N1-N3; invariant 22 conservation exact; P2 ownership unchanged (33) | PASS |
| O incumbent-first abstention | A1 (8 / 8 retained), E6, invariant 27 | PASS |
| P all P3 fixtures | 30 / 30 (`P3_RESULTS.md`, `p3_authoritative.*`) | PASS |
| Q all P3 invariants | 34 / 34 (`P3_INVARIANTS.md`, `gates/p3_invariants.log`) | PASS |
| R adversarial | 23 / 23 fail safely (`P3_ADVERSARIAL.md`) | PASS |
| S P0 frozen | six-cell arm `p3_sourcing` 120 / 120 decision-identical to `router_cycle` (`gates/p0_six_cell_p3_sourcing.log`); canonical cell 15 identical | PASS |
| T P1 frozen | canonical regression B / T / Q / A twelve-review identity (`gates/canonical_regression.log`); P1 invariants no failures (`gates/p1_invariants.log`) | PASS |
| U P2 frozen | `p2_under_p3`: 20 / 20 fixtures, 18 / 18 principles, 344 / 344 ZAAD reviews decision-identical (`evidence/p2/p2_under_p3_compare.json`) | PASS |
| V sector architecture and all previously validated sector semantics preserved, except documented correctness corrections that are independently isolated, causally proven, fully revalidated, and leave legacy / P0 / P1 / P2 behaviour unchanged | **one such correction for this freeze**: physics-enabled historical replay now materialises a received perishable purchase with its declared remaining life (`shelf_life - age_at_receipt`) instead of the full shelf life (`zaad/full/replay.py`, first in `33f96cc`). Live planner, settlement and projections already used the declared receipt life and are unchanged. Audit, review-by-review table and counterfactual: `evidence/sectors/corrections/AGE_AT_RECEIPT_REPLAY_AUDIT.md` and `AGE_AT_RECEIPT_REPLAY_CORRECTION.md`. Sector re-runs on the product code: 26 / 26 fixtures, 19 / 19 invariants; 402 / 416 ZAAD replay reviews identical with the 14 differences all causally attributed to fixture P3_age_at_receipt (the only sector fixture declaring an age at receipt); legacy / no-physics replays bit-identical (P2 344 / 344, P0 120 / 120). Future semantic changes still require an explicit correction record. | PASS (one documented correction) |
| W runtime bounded and explained | 480 reviews p50 0.66 s / p95 19.2 s / max 42.8 s, 0 time-limited, none over 60 s; profiles in `P3_PERFORMANCE.md` | PASS |
| X full repository suite | **1,901 passed, 2 skipped** (`gates/pytest_final.log`); ruff, mypy (CI scope), bandit, `git diff --check` clean (`gates/static_checks.log`) | PASS |
| Y no commercial solver | HiGHS only | PASS |
| Z Validation7 / Validation8 / holdout4 | untouched, unrun, unread | PASS |

## What P3 gives each situation

* **Economics**: total landed cost after freight, handling, financing and payment timing decides, not
  unit price (E2, E5); price tiers are taken when the lot earns them (E3); MOQ / MOV keep small orders
  with the flexible source (E4); a declared switching cost keeps the incumbent against a small nominal
  saving (E6).
* **Reliability**: fill, lead and yield uncertainty enter through the worlds (R1, S2); capacity forces a
  split and the block says which source is at capacity (R2); declared shared-risk groups correlate the
  members' shocks with marginals preserved and no independence benefit is claimed (R4, R5, A2).
* **Constraints**: declared shares, committed units, calendars / shutdowns, qualification, shared supplier
  capacity and MOV across SKUs (C1-C6).
* **Sectors and network**: a short-life produce source and a frozen source into a chilled-only destination
  are never used and the block says why (S1, S3); packs stay executable on both suppliers (S4); P2 keeps
  its transfers and conservation stays exact (N1-N3).
* **Abstention**: an optimal incumbent mix is retained, weak evidence is flagged, pruning and an empty
  block change nothing, no order means no allocation (A1-A6).

## Known limitations (recorded, not tuned)

* The incumbent projection books a shared resource first-line-first across SKUs; a buyer might
  apportion it (the projection is a physically legal comparator, not a recommendation).
* Switching costs are charged once when a switch is executed; once switched, the source is in the
  operator's mix (P4 will own contingent switching).
* Correlation is declared per group (a common factor); no correlation matrix is accepted.
* No upload path for `stg_fmcg_sources`; the table is filled by the operator's own load.
* The frozen report-only valuations on integer packs (alternates valuation, base-stock proxy, frontier
  oracle) remain the slowest class (S4 42.8 s, C6 24.8 s), below the 180 s blocker.
* The three production observations of the sector release (C1 ~59.5 s, P1 workspace ~24 s, 150-SKU
  synchronous call > 400 s) are untouched.

## Untouched

Validation7, Validation8, holdout4; Network Twin #39; P4-P6; dashboard and website uplift; Dependabot
solver-stack bumps; no push, no PR, no merge, no deployment.

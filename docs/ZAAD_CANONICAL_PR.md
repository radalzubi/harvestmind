# ZAAD canonical lineage: P0 and P1 frozen, site and main merged, customer-data path

<!-- Body of the one canonical pull request zaad/canonical -> main. Open it with:
     gh pr create --base main --head zaad/canonical --title "ZAAD canonical lineage: P0 and P1 frozen, site and main merged, customer-data path" --body-file docs/ZAAD_CANONICAL_PR.md -->

## What this PR is

One trustworthy ZAAD software lineage around the frozen optimizer. Three SHAs matter and are different things:

| | SHA | tag |
|---|---|---|
| P0 frozen (solver completeness / recovery logic — PASS AND FROZEN) | `2e30721` | `p0-frozen` |
| P1 frozen (cycle-stock / purchasing economics — PASS AND FROZEN; product code `f7e1e62`) | `12db66c` | `p1-frozen` (`p1-frozen-product`) |
| canonical integration (this branch's HEAD) | `3bbb07c` | — |

`56e998f` (tag `pre-canonical-integration`) is the post-freeze documentation state, not a freeze.

## Do not merge the historical optimizer PRs individually

PRs #16, #17, #18, #20, #21, #23, #24, #25, #30, #31, #32, #33, #35, #36, #37 and #38 are the development
lineage of the optimizer. Every one of their head commits is an ancestor of this branch (verified with
`git merge-base --is-ancestor`), so their accepted content is already here. Merging them separately would
recreate history that this branch already contains, and #32 in particular is a historical negative result
(the failed holdout3) that must stay as evidence, not be merged as a feature. After this PR merges they
are closed as superseded, never deleted.

## What is inside

* **Frozen optimizer integrity.** `zaad/full` is the P0 + P1 engine. The two merges (`28d9839` site
  lineage, `0fbd8ee` main) left its tree byte-identical to the freeze. `3263aff` closed the typed debt
  with annotations and three local renames only and made an infinite shortfall JSON-safe in the report.
  Evidence: `scripts/zaad_canonical_regression.py` reproduces the first twelve reviews of the P1
  freeze record for B, T, Q and A order for order and status for status, and P0 cell 15 review by
  review against the isolation arm; B alone on the freeze benchmark is bit-identical after the typing
  edits (`closure/identity_typing.jsonl.gz`); 720 / 720 invariants identical to the freeze record.
* **Customer-data adapter** (`zaad/full/workspace.py`): the operator's own vault (`stg_fmcg_*`) ->
  the frozen `Request`: weekly demand history before the origin, supplier fill and lead fitted per
  supplier with sample sizes and provenance (declared promises or configured assumptions otherwise),
  shipment observations, opening stock, open orders with keep options, promotions, pack structure and
  order-level economics, a leakage guard, compact dimensions in the build report.
* **API consolidation.** One planning engine: the frozen P1 optimizer under `/api/zaad/network`
  (plan, shadow, jobs, `request/from-workspace`, `plan/from-workspace`); `/fmcg/plan` defaults to
  `mode=canonical`. The first ZAAD engine (`/api/zaad`) and the safe-selector modes are served only
  while `ZAAD_LEGACY_PLANNERS` allows it (dev by default, off in pilot / staging / prod). No
  autonomous purchase order anywhere; approval stays with the operator.
* **Frontend / site integration.** The site lineage Vercel serves (SEO, /how-it-works, homepage) and
  the workspace (upload, data quality, purchase plan on the canonical engine, state, reports, network
  workspace); main's #28 copies resolved to the site lineage; the first engine's page redirects and is
  kept at `/zaad/legacy`; ESLint added; public surfaces say ZAAD.
* **CI / security closure** (`.github/workflows/ci.yml`): pytest (unit + integration), ruff on the
  canonical scope (blocking), mypy (blocking, clean), bandit and pip-audit, gitleaks, the ZAAD frozen
  regression + invariants + workspace smoke, the Docker image smoke (health, fail-closed posture, no
  open legacy planner in prod), frontend typecheck / lint / build / audit. weasyprint pinned at 70.0
  (CVE-2026-55073), the transitive npm advisory fixed, tracked coverage databases removed.
* **Real-data synthetic smoke** (`scripts/zaad_workspace_smoke.py`): a synthetic, schema-realistic
  distributor (not customer data) through upload -> vault -> adapter -> frozen plan -> purchase-plan
  rows; 192k raw rows become a 61 KB request for three SKUs.

## Local validation at `3bbb07c`

pytest 1,810 passed / 2 skipped; ruff canonical scope clean; mypy clean (135 files); bandit 0 medium /
high; pip-audit clean; frontend typecheck, lint (0 errors), build, npm audit clean; frozen regression
PASS; invariants 720 / 720. The Docker image smoke runs for the first time in this PR's CI.

## Deferred and untouched

Network Twin (PR #39) is deferred and not included. Validation7, Validation8 and holdout4 are
untouched. P2 has not started; it branches from `main` after this merges.

Source of truth: `docs/ZAAD_RELEASE_LEDGER.md`, `docs/ZAAD_REPOSITORY_CONSOLIDATION_PLAN.md`,
`docs/ZAAD_POST_P1_INTEGRATION_CHECKLIST.md`.

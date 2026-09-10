# ZAAD release ledger

Source of truth for what is frozen, where it lives, and what may move next. Written 2026-09-10 at the
end of the P1 freeze session, from git ancestry and the CI records (no optimizer matrix was rerun for
this ledger). Update this file whenever a freeze, a push, a merge or a Vercel change happens.

## Frozen states

| layer | state | SHA | branch (worktree) | pushed | evidence |
|---|---|---|---|---|---|
| P0 solver completeness / recovery | PASS AND FROZEN | `2e30721` | `claude/zaad-industry-standard-v8` (`harvestmind-zaad`) | **no**: origin is at `e8e2398`, nine commits behind the freeze (v8 orchestration, P0 corrections, warm start, close-out) | `docs/zaad_full/evidence/v8/p0` |
| P1 cycle stock / purchasing economics | PASS AND FROZEN | product `f7e1e62`, evidence `12db66c` | `claude/zaad-cycle-stock-p1` (`harvestmind-p1`), 26 commits on top of `2e30721` | **no** (local only, no PR) | `docs/zaad_full/evidence/p1` (`P1_CLOSEOUT.md` M12, `P1_ECONOMIC_HORIZON_ARCHITECTURE.md`, `P1_FINAL_RESULT_TABLE_cycle.md`) |
| P2 | NOT STARTED | - | - | - | - |
| Network Twin V1 | DEFERRED (draft PR #39) | `734fa49` | `claude/zaad-network-twin-v1` = `adaptive/decision-engine` + 3 web commits | yes | - |

P1 result at the freeze: declared benchmark (constant twelve-period rolling horizon, 52 reviews,
landed-cost continuation) B +1.30% vs the EOQ buyer (was +2.66%), PASS at 52 and at every endpoint
40..52; 17 / 17 valid fixtures PASS; T -0.13%; A and Q unchanged; P0 six-cell arm 120 / 120
decision-identical; invariants 720 / 720; 1,532 unit tests. Known residual: three-world near-ties on
the first lot (B +1.30%, J +1.35%), recorded and not tuned.

## Lineages (git ancestry, `origin` fetched 2026-09-10)

Common base of everything: `11f06e9` on `main`. Three divergent tips:

1. **Optimizer lineage**: `main@11f06e9` -> #16 -> #17 -> #18 -> #19 (`adaptive/decision-engine@2820a69`)
   -> #20 -> #21 -> #23 -> #24 -> #25 -> #30 -> #31 -> #32 -> #33 -> #35 -> #36 -> #37 -> #38 (`e8e2398`)
   -> P0 freeze `2e30721` (+9 local) -> P1 freeze `12db66c` (+26 local). Every step contains its parent
   completely (zero parent commits missing from any child); the tip `12db66c` contains every commit of
   every open optimizer PR. 157 commits and 1,003 files ahead of `main`.
2. **Site lineage**: `adaptive/decision-engine@c941c64` = `2820a69` + 12 commits (#22 homepage, #29 SEO,
   #34 how-it-works; 58 files, all under `web/`, one doc). Vercel production tracks this branch (commit
   `81f141e` records the deployment and the ignored-build-step configuration). Network Twin sits on it.
3. **`main`**: `11f06e9` + 5 commits (#14 Project B synthetic generator, #15 agent docs, #26 / #27 / #28
   the "deployed ZAAD frontend as production source" change and its revert): 64 files under `web/`,
   25 under `docs/`, 4 under `synthetic/`. None of these five commits is in either other lineage.

## PR dispositions (39 PRs; merged ones are history)

| PR | head -> base | disposition | reason |
|---|---|---|---|
| #16 real-data validation | `feat/commercial-real-data-validation` | SUPERSEDED | fully contained in the optimizer tip |
| #17 commercial readiness | `commercial-readiness/fmcg-agriculture` | SUPERSEDED | contained |
| #18 safe selector | `safe-adaptive/selector` | SUPERSEDED | contained |
| #19 adaptive decision engine | `adaptive/decision-engine` -> `safe-adaptive/selector` | CANONICAL (site) / MERGE LATER (optimizer part contained) | production branch for Vercel; its 12 site commits are the only site work; its optimizer content is contained in the lineage |
| #20 commercial audit | `codex/commercial-engine-evidence-audit` | SUPERSEDED | contained |
| #21 resilience engine | `codex/zaad-resilience-engine` | SUPERSEDED | contained |
| #23 full commercial optimizer | `codex/zaad-full-commercial-optimizer` | SUPERSEDED | contained |
| #24 selector fix | `chatgpt/zaad-pr23-service-selector-fix` | SUPERSEDED | contained |
| #25 release blockers | `claude/zaad-pr24-release-blockers` | SUPERSEDED | contained |
| #30 service reliability | `claude/zaad-service-reliability` | SUPERSEDED | contained |
| #31 false protection | `claude/zaad-false-protection` | SUPERSEDED | contained |
| #32 holdout3 | `claude/zaad-holdout3` | EVIDENCE ONLY / SUPERSEDED | contained; holdout3 verdict kept in evidence |
| #33 calibrated protection v4 | `claude/zaad-calibrated-protection-v4` | SUPERSEDED | contained; holdout4 frozen and unrun |
| #35 network recovery v5 | `claude/zaad-network-recovery-v5` | SUPERSEDED | contained |
| #36 MEIO / recovery v6 | `claude/zaad-meio-recovery-v6` | SUPERSEDED | contained (local branch one commit ahead of origin: development6 summaries) |
| #37 capital recovery v7 | `claude/zaad-capital-recovery-v7` | SUPERSEDED | contained; CI fully green at `0e278c3` |
| #38 V8 industry standard | `claude/zaad-industry-standard-v8` | CANONICAL (optimizer, to be replaced by the P1 tip) | origin nine commits behind the P0 freeze; mypy red (3 errors) at `e8e2398` |
| #39 Network Twin V1 | `claude/zaad-network-twin-v1` -> `adaptive/decision-engine` | DEFERRED FEATURE | untouched; integrate after the canonical optimizer lineage exists, the API contract is stable and the illustrative simulation is separated from optimizer output |
| P1 (no PR) | `claude/zaad-cycle-stock-p1` | **CANONICAL optimizer tip** | contains P0 and P1 freezes and every optimizer PR |

Nothing is merged, closed or deleted by this ledger.

## CI status and debt (workflow `.github/workflows/ci.yml`: pytest, ruff, security = bandit `-ll` + pip-audit, mypy, docker build, next build; `codeql.yml`; dependabot)

| candidate | pytest | ruff | mypy | security | docker | next build | Vercel |
|---|---|---|---|---|---|---|---|
| #37 `0e278c3` (optimizer, pre-P0) | pass | pass | pass | pass | pass | pass | pass |
| #38 `e8e2398` (optimizer, origin) | pass | pass | **fail (3 errors)** | pass | pass | pass | pass |
| P1 `12db66c` (local; CI not run) | 1,532 pass locally | changed files clean; repo-wide debt | **19 errors locally** (4 at the P0 freeze, 15 from P1 passes C-H in `settlement.py` / `economics.py`) | bandit clean on `zaad/full` locally | not run | not run | - |
| #19 `c941c64` (site / production) | pass | pass | **fail** | **fail (bandit: 3 Medium)** | pass | pass | pass |
| #39 `734fa49` (Network Twin) | pass | pass | **fail** | **fail (bandit: 3 Medium)** | pass | pass | pass |

Classification: mypy on the optimizer lineage = PRE-EXISTING DEBT (typing of P1 order-line metrics and
economics helpers; no runtime defect; not in the files changed by the P1 freeze); mypy and bandit on
the site lineage = CURRENT DEFECT to be fixed on the site branch before it merges (three Medium
findings absent from the optimizer lineage); the ruff job's repo-wide step runs with `|| true`
(STALE WORKFLOW: it hides ~150 findings in older P1 diagnostic scripts and pass C-H tests, while the
changed-files step is the real gate); pip-audit ignores `PYSEC-2026-3412` by configuration (record the
package and the reason before the canonical PR). Nothing was suppressed for this ledger.

## Untouched

Validation7 and Validation8 do not exist as directories; `docs/zaad_full/evidence/v4/holdout4` is
frozen and unrun; PR #38's origin state, PR #39, `web/`, Vercel and every other worktree are untouched.

## Exact next action

Authorize `git push origin claude/zaad-cycle-stock-p1` (and the nine P0 commits on
`claude/zaad-industry-standard-v8`), then follow `docs/ZAAD_POST_P1_INTEGRATION_CHECKLIST.md` step 1.
No push has been made.

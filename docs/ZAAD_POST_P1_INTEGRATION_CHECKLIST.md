# ZAAD post-P1 integration checklist

Operational companion to `docs/ZAAD_REPOSITORY_CONSOLIDATION_PLAN.md`. Tick each box in order; every
step names its command, its expected result and its rollback. Run from the `harvestmind-p1` worktree
unless stated. Nothing below starts P2.

## Step 0: freeze tags (local)

- [ ] `git tag p0-frozen 2e30721 && git tag p1-frozen-product f7e1e62 && git tag p1-frozen 12db66c`
- [ ] `git tag --contains 2e30721 | sort` lists all three tags
- rollback: `git tag -d <tag>`

## Step 1: publish the frozen branches (needs explicit authorization)

- [ ] `git push origin claude/zaad-industry-standard-v8` (nine P0 commits; origin moves `e8e2398` -> `2e30721`)
- [ ] `git push origin claude/zaad-cycle-stock-p1 --tags`
- [ ] open the P1 PR with base `claude/zaad-industry-standard-v8`, title "ZAAD P1: cycle stock / purchasing economics — PASS AND FROZEN"
- [ ] expected CI: pytest pass, ruff pass, docker pass, next build pass, mypy FAIL with exactly 19 errors (debt), security pass
- rollback: none required (push only; no history rewritten)

## Step 2: canonical branch

- [ ] `git branch zaad/canonical 12db66c`
- [ ] `git rev-list --count 12db66c..zaad/canonical` prints `0`
- rollback: `git branch -D zaad/canonical`

## Step 3: merge the site lineage

- [ ] `git tag consolidation-step3 zaad/canonical`
- [ ] `git checkout zaad/canonical && git merge --no-ff origin/adaptive/decision-engine`
- [ ] conflicts only under `web/`: resolve by taking the site lineage's version (`git checkout --theirs web/ && git add web/`)
- [ ] `cd web && npm ci && npm run build` succeeds
- [ ] `PYTHONPATH=. python3 -m pytest tests/unit -q` -> 1,532 passed, 2 skipped (±new tests from the site merge, none expected)
- [ ] `PYTHONPATH=. python3 -m scripts.p1_invariants` -> 720 / 720
- [ ] `PYTHONPATH=. python3 -m scripts.p1_horizon_benchmark --workers 4 --fixtures B_fixed_order_cost_replace_sold --tag identity_step3` then `PYTHONPATH=. python3 -m scripts.p1_cycle_compare identity_step3 horizon52_cycle_B B_fixed_order_cost_replace_sold` -> B +1.30%, first lots 983 / 1,645 / 2,128, orders 4 / 3 / 4 (bit-identical decisions)
- [ ] `git diff --check` clean
- rollback: `git reset --hard consolidation-step3` (only on `zaad/canonical`, before anything is pushed)

## Step 4: site-lineage CI defects (no optimizer behaviour change)

- [ ] `python -m bandit -r api infrastructure ingestion optimization risk backtesting reports pool forecasting domain zaad/full -ll -q` -> list the three Medium findings, fix each at its source, rerun clean
- [ ] `python -m mypy optimization risk backtesting api ingestion domain adaptive zaad/full --ignore-missing-imports` -> back to the optimizer's 19, then address those 19 in one commit titled "types(zaad): typed debt, no behaviour change"
- [ ] repeat the step-3 identity check after the typing commit (B bit-identical)
- [ ] tag `consolidation-step4`
- rollback: `git reset --hard consolidation-step3`

## Step 5: merge `main`

- [ ] owner decision recorded in `docs/ZAAD_RELEASE_LEDGER.md`: which `web/` is production (`adaptive/decision-engine` per the ledger, or `main` #28)
- [ ] `git tag consolidation-step5-pre zaad/canonical && git merge --no-ff origin/main`
- [ ] resolve `web/` per the decision; keep `synthetic/` and `docs/` from both sides
- [ ] `npm run build`, `pytest tests/unit -q`, invariants, the B identity check, `docker compose -f compose.pilot.yml config -q`
- [ ] tag `consolidation-step5`
- rollback: `git reset --hard consolidation-step5-pre`

## Step 6: the canonical pull request

- [ ] `git push origin zaad/canonical` and open "ZAAD canonical lineage: P0 and P1 frozen, site merged" -> `main`
- [ ] CI green except ticketed debt (link the ledger's CI table in the PR body)
- [ ] review: `docs/ZAAD_RELEASE_LEDGER.md` updated with the PR number

## Step 7: after the canonical PR merges

- [ ] repoint Vercel production to `main` (or keep `adaptive/decision-engine` until the next site change; record the choice)
- [ ] close #16, #17, #18, #20, #21, #23, #24, #25, #30, #31, #32, #33, #35, #36, #37, #38 as superseded with a comment linking the ledger
- [ ] close #19 only after Vercel no longer tracks its branch
- [ ] `.gitignore` `.coverage*`; remove the five tracked `.coverage N` files in a hygiene commit

## Step 8: Network Twin (deferred)

- [ ] preconditions: `zaad/canonical` merged; `/api/zaad_full` contract declared stable; the twin's scenario engine labelled illustrative and separated from optimizer output
- [ ] `git merge --no-ff origin/claude/zaad-network-twin-v1` into the canonical branch; `npm run build`; the twin's contract tests
- rollback: tag `consolidation-step8` taken before the merge

## Never during consolidation

merge or close a PR before step 7, delete a branch, rebase shared history, force-push, deploy, alter
Vercel, run holdout4, modify the Network Twin, rerun optimizer matrices, start P2.

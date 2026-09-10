# ZAAD post-P1 integration checklist

Operational companion to `docs/ZAAD_REPOSITORY_CONSOLIDATION_PLAN.md`. Updated 2026-09-10 at the end
of the canonical integration pass: done items are ticked with their evidence; the remaining items need
the owner's authorization (push, PR, closures, Vercel). Run from the `harvestmind-p1` worktree on
`zaad/canonical`.

## Done in this pass

- [x] Step 0: local tags `p0-frozen` (2e30721), `p1-frozen-product` (f7e1e62), `p1-frozen` (12db66c), `pre-canonical-integration` (56e998f)
- [x] Step 2: `zaad/canonical` created from `56e998f`
- [x] Step 3: site lineage merged (`28d9839`), no conflicts; frozen tree unchanged
- [x] Step 4: typed debt closed with identity evidence (`3263aff`); bandit clean on the canonical packages
- [x] Step 5: `main` merged (`0fbd8ee`); web conflicts resolved to the site lineage
- [x] Customer-data path and canonical API (`073d702`); CI, security, hygiene, ESLint (`d7f76cf`)
- [x] Validation on the canonical tree: pytest 1,810 passed / 2 skipped; ruff canonical scope clean; mypy clean; bandit 0 medium; pip-audit clean; frontend typecheck / lint / build / audit clean; `scripts/zaad_canonical_regression.py` PASS; invariants 720 / 720 identical to the freeze; workspace smoke OK
- [ ] Docker image smoke: defined in CI, not runnable on this machine (no Docker); passes on the first CI run or is fixed there

## Step 1: publish the frozen branches and the canonical branch (needs explicit authorization)

```bash
git push origin claude/zaad-industry-standard-v8      # nine P0 commits; origin moves e8e2398 -> 2e30721
git push origin claude/zaad-cycle-stock-p1            # P1 freeze 12db66c and the post-freeze docs 56e998f
git push origin p0-frozen p1-frozen-product p1-frozen pre-canonical-integration
git push -u origin zaad/canonical
```

Expected CI on `zaad/canonical`: every job green; if the Docker smoke fails, fix the smoke, never the
posture. Never force-push.

## Step 6: the canonical pull request

- [ ] open "ZAAD canonical lineage: P0 and P1 frozen, site and main merged, customer-data path" from `zaad/canonical` to `main`
- [ ] body links `docs/ZAAD_RELEASE_LEDGER.md` (frozen SHAs, integrity evidence, CI table, documented debt)
- [ ] CI green; review; merge without squash (the freeze SHAs must remain reachable from `main`)

## Step 7: after the canonical PR merges (needs explicit authorization)

- [ ] Vercel: point production at `main` (or keep `adaptive/decision-engine` until the next site change); record the choice in the ledger
- [ ] close as superseded with a note linking the ledger: #16, #17, #18, #20, #21, #23, #24, #25, #30, #31, #33, #35, #36, #37, #38; close #32 as a historical negative result (evidence retained)
- [ ] close #19 only after Vercel no longer tracks its branch
- [ ] set `ZAAD_LEGACY_PLANNERS` explicitly on every deployed environment (unset = off outside dev)

## Step 8: Network Twin (deferred)

- [ ] preconditions: canonical PR merged; `/api/zaad/network` declared stable; the twin's scenario engine remains a labelled demo adapter separated from optimizer output
- [ ] `git merge --no-ff origin/claude/zaad-network-twin-v1` into the canonical branch; `npm run typecheck && npm run lint && npm run build`; the twin's contract tests

## Later (not P2)

- [ ] repoint the purchase-plan page's legacy modes and the `/zaad/legacy` page; then remove the legacy engines and the parts of `optimization/`, `backtesting/`, `adaptive/` only they use (one release with legacy planners off first)
- [ ] the 21 ESLint warnings; HarvestMind names in configuration and internal modules; git-lfs for future evidence

## Never

merge or close a PR before step 6, delete a branch, rebase shared history, force-push, deploy, alter
Vercel, run Validation7 / Validation8 / holdout4, modify the Network Twin, rerun optimizer matrices for
consolidation, start P2.

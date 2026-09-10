# ZAAD post-P1 integration checklist

Operational companion to `docs/ZAAD_REPOSITORY_CONSOLIDATION_PLAN.md`. Updated 2026-09-10 at the close
of the release line: every step through Step 7 is done with its evidence (PR #40 merged as `f7ff600`,
`main` verified, superseded PRs closed, Vercel on `main`). Only Step 8 (Network Twin, deferred) remains.

## Done in this pass

- [x] Step 0: local tags `p0-frozen` (2e30721), `p1-frozen-product` (f7e1e62), `p1-frozen` (12db66c), `pre-canonical-integration` (56e998f)
- [x] Step 2: `zaad/canonical` created from `56e998f`
- [x] Step 3: site lineage merged (`28d9839`), no conflicts; frozen tree unchanged
- [x] Step 4: typed debt closed with identity evidence (`3263aff`); bandit clean on the canonical packages
- [x] Step 5: `main` merged (`0fbd8ee`); web conflicts resolved to the site lineage
- [x] Customer-data path and canonical API (`073d702`); CI, security, hygiene, ESLint (`d7f76cf`)
- [x] Validation on the canonical tree: pytest 1,810 passed / 2 skipped; ruff canonical scope clean; mypy clean; bandit 0 medium; pip-audit clean; frontend typecheck / lint / build / audit clean; `scripts/zaad_canonical_regression.py` PASS; invariants 720 / 720 identical to the freeze; workspace smoke OK
- [x] Docker image smoke: passed on GitHub (PR #40 runs 2-4 and the `main` run 34474090176): image builds, `/health` `zaad-api` with `auth_enforced` true in prod, anonymous jobs 401, legacy demo closed, compose validated

## Step 1: publish the frozen branches and the canonical branch — DONE 2026-09-10 (authorized)

- [x] frozen branches, four tags and `zaad/canonical` on origin at their exact SHAs
- [x] PR #40 opened (`zaad/canonical` -> `main`, body `docs/ZAAD_CANONICAL_PR.md`)
- [x] remote CI fixed to green on every job at `4bc8c4a` except one test on the literal key id, fixed at `7cf0431`
- [ ] **blocked**: run 4 (`7cf0431`) could not schedule any job (account billing / Actions spending limit). Restore billing, then `gh run rerun <run id>` and `gh pr checks 40 --watch`.

(the original step-1 commands, kept for the record)

```bash
git push origin claude/zaad-industry-standard-v8      # nine P0 commits; origin moves e8e2398 -> 2e30721
git push origin claude/zaad-cycle-stock-p1            # P1 freeze 12db66c and the post-freeze docs 56e998f
git push origin p0-frozen p1-frozen-product p1-frozen pre-canonical-integration
git push -u origin zaad/canonical
```

Expected CI on `zaad/canonical`: every job green; if the Docker smoke fails, fix the smoke, never the
posture. Never force-push.

## Step 6: the canonical pull request

```bash
gh pr create --base main --head zaad/canonical \
  --title "ZAAD canonical lineage: P0 and P1 frozen, site and main merged, customer-data path" \
  --body-file docs/ZAAD_CANONICAL_PR.md
gh pr checks --watch          # every job must be green; the Docker smoke runs here for the first time
```

- [x] opened from `zaad/canonical` to `main` with `docs/ZAAD_CANONICAL_PR.md` as the body (PR #40)
- [x] body links `docs/ZAAD_RELEASE_LEDGER.md` (frozen SHAs, integrity evidence, CI table, documented debt)
- [x] CI green on head `9a8d266` (run 34462761422, every job); merged without squash as `f7ff600`; `2e30721`, `f7e1e62`, `12db66c` reachable from `main`; `main` run 34474090176 green

## Step 7: after the canonical PR merges — DONE 2026-09-10 (authorized)

- [x] Vercel: project `zaad` production branch `adaptive/decision-engine` -> `main` (dashboard, Environments -> Production -> Branch Tracking); production deployment of `f7ff600` READY on `zaadsupply.com`; recorded in the ledger
- [x] closed as superseded 2026-09-10 (heads re-verified as ancestors of `main`; branches kept):

```bash
for n in 16 17 18 20 21 23 24 25 30 31 33 35 36 37 38; do
  gh pr close "$n" --comment "Superseded: this PR's head is an ancestor of the canonical ZAAD lineage now on main (see docs/ZAAD_RELEASE_LEDGER.md). Branch and evidence kept."
done
gh pr close 32 --comment "Historical negative result, kept as evidence: the untouched holdout3 evaluation (HOLDOUT FAILED) that started the v4 cycle. Its head is an ancestor of the canonical ZAAD lineage now on main; nothing here is merged as a feature. Branch and evidence kept."
```

- [x] #19 closed after the Vercel repoint; #39 left open (deferred); Dependabot #41-#51 untouched, out of scope
- [ ] set `ZAAD_LEGACY_PLANNERS` explicitly on every deployed API environment (unset = off outside dev); the API is deployed outside Vercel and outside this pass

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

## Step 9: P2 (multi-echelon / network) — BUILT 2026-09-10, FREEZE BLOCKED on the runtime maximum; PASS AND FROZEN after the performance pass (same day)

- [x] branch `claude/zaad-meio-p2` from `11f5459` in `harvestmind-p2`; P0 / P1 untouched in behaviour (regression identical; six-cell isolation)
- [x] network layer, fixtures A-T, baselines, benchmark, invariants, adversarial, scalability, workspace adapter, API, tests
- [x] authoritative run: 20 / 20 fixtures, 18 / 18 principles, 20 / 20 invariants
- [x] runtime maximum per review (pre-registered 180 s): failed as recorded (M 257 s, O 315 s); performance pass (exact FEFO symmetry elimination, network requests only) re-ran the unchanged set: p50 0.5 s, p95 6.6 s, max 14.6 s, 0 time-limited solves; P0 / P1 identity held (`docs/zaad_full/evidence/p2/perf/`)
- [x] verdict: P2 MULTI-ECHELON / NETWORK OPTIMIZATION — PASS AND FROZEN (`P2_CLOSEOUT.md`)
- [ ] not merged, not pushed: owner decision on the merge of `claude/zaad-meio-p2` into `main`


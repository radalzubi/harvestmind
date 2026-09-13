## chore(zaad): repository and CI cleanup after P4B release

Smaller, clearer, safer repository and a simpler CI, with the released optimizer stack (P0, P1, P2, sector physics, P3, P4, P5, P4B V1) byte-for-byte unchanged in `zaad/`, `api/` and `web/`. Inventory and classification of every tracked file: `docs/zaad_full/REPOSITORY_CLEANUP_AUDIT.md`. Validation record: `docs/zaad_full/evidence/cleanup/`.

### Files deleted (DEAD only, 51)
* 50 byte-identical macOS Finder duplicates (`name 2.md`, one `name 2.py`) under `docs/` (verified with `cmp`; no reference); `.gitignore` now refuses `* 2.*` / `* 3.*`.
* `.github/workflows/codeql.yml`: code scanning is unavailable on this plan (repository-level 403), so the workflow could never report green.

### Files retained despite appearing old
Legacy HarvestMind packages (mounted by the API or gated behind `ZAAD_LEGACY_PLANNERS`), `dashboard/`, `data/`, `artifacts/`, the P1 diagnostic scripts, the legacy study scripts that produced committed records, `docs/zaad_next` and the other historical docs directories, the July security-pass documents, all 22 migrations. Each is listed with its reason in the audit.

### Legacy compatibility retained
Repository / package / Docker / Fly naming (`harvestmind`, `HARVESTMIND_*`), the gated prototype engine under `/api/zaad` (the web demo calls it in dev), every legacy router (API surface unchanged), every feature flag (`ZAAD_LEGACY_PLANNERS` = 0, `ZAAD_ATP_ENABLED` = 1 in production), `data_contracts` (no importer; partner CSV contract; listed as debt).

### Dependencies removed (6, evidence: no import or use anywhere outside the dependency list)
`mlforecast`, `polars`, `sqlalchemy`, `pydantic-settings`, `tenacity`, `python-dotenv`. A fresh venv from the trimmed `pyproject.toml` installs, imports the API and the planner, and pip-audit on that closure reports no known vulnerabilities. This changes the Docker image, so the merged commit is deployed and smoked (rule 30).

### CI changes (one workflow)
* Triggers: push to `main` and pull requests, both ignoring `**.md`; `zaad/canonical` dropped as a push target. Evidence JSON / JSONL still runs every gate.
* Test job: ZAAD unit files in four name-range shards balanced on measured durations (local 53 / 66 / 76 / 43 s, previously 75 / 43 / 119) with a partition check; coverage collection and its never-read artifact removed; shard timeout 90 -> 60 min. Every test still runs once.
* Unchanged: ruff, mypy, bandit, pip-audit, gitleaks, frozen regression, Docker build + smoke, frontend typecheck / lint / build.

### CodeQL decision
Removed (option B): default setup answers "Code scanning is not enabled for this repository" and cannot be enabled on a private repository under the free personal plan. Security gates remain bandit, pip-audit, gitleaks.

### GitHub protection state
Not changeable: branch protection and rulesets answer "Upgrade to GitHub Pro or make this repository public". Minimal manual action recorded in the audit (upgrade or make public, then: PR required, `CI` jobs required, no force push, no deletion, no reviewer count).

### Branches
Deleted after merge: every branch merged with no unique history, the squash-merged `ci-pytest-ruff` (#4), `docs/migrate-agri-ai-workspace` (#15), `codex/frontend-pages-no-hero` (#26), `codex/revert-frontend-pages-no-hero` (#27), `codex/zaad-production-source` (#28), the superseded P3 closeout drafts (#61 / #62; contained in the merged v3). Retained: `docs/brief-al-burger` (unique, no PR), `claude/zaad-network-twin-v1` (PR #39 deferred), `dependabot/*` (open PRs).

### Repository size
Tracked files 2,063 -> 2,014 (51 deleted, 2 added; 6,006 lines removed). Working tree 319.2 -> 318.7 MB: the duplicates were small text and every evidence record is kept, so the size gain is small by design; the object store (4.3 MB pack) is history and unchanged.

### CI runtime
CI_BEFORE_AFTER

### Full regression on the cleanup tree
| gate | result on the cleanup tree |
|---|---|
| full pytest (fresh venv from the trimmed closure) | 1,980 passed, 2 skipped, 0 failed (6 m 18 s) |
| ruff (CI scope) / mypy (CI scope) / bandit (CI scope) | clean |
| pip-audit on the trimmed closure | no known vulnerabilities |
| P3 shared-MOV production snapshot | identical to the P4B release-audit gate, 18 HiGHS calls, no `commitments` key |
| P1 canonical regression / invariants | CANONICAL REGRESSION PASS; 720 checks, 60 / 60 records, 0 failures |
| P2 | 20 / 20, 18 / 18 principles, INVARIANTS PASS, 1,720 / 1,720 identical vs `p2_perf_closure` |
| sector physics | 26 / 26, 19 / 19, 416 / 416 identical vs `sector_perf_closure` |
| P3 | 30 / 30, 34 / 34, 23 / 23 adversarial, 2,304 / 2,304 identical vs `p3_perf_closure` |
| P4 | 28 / 28 fixtures, 27 / 27 invariants, 25 / 25 adversarial (= the release record) |
| P5 | 24 / 24 isolated, 20 / 20 integration, 18 / 18 adversarial (= the release record) |
| P4B | 21 / 21 fixtures incl. F00 identity against the production runtime checkout `1851f40`, 16 / 16 adversarial, 35 / 35 release-audit cases |
| P0 six-cell arm `p4b_release` vs `router_cycle` | 120 / 120 decision-identical |

Records: `docs/zaad_full/evidence/cleanup/` (`chain.sh`, `chain.log`, `gates/`: every log, the three decision-compare
records, the matrix tables and the P0 arm record). The regenerated full run files (`*_under_cleanup.jsonl`, 12 MB)
are reproducible from the scripts and are not committed; released records the matrices regenerate in place
(P2 / P3 / P4 / sector invariants, P3 / P4B adversarial, the P4B P0 arm) differed by tag, timing and the validator's
request echo only and were restored.

### Known remaining cleanup debt
* `data_contracts/` has no importer (partner CSV templates + an unreferenced pandera schema; `pandera` stays for it).
* The prototype engine `zaad/{engine,allocation,forecast,signals,intake,contracts,demo}.py` behind `/api/zaad` is still served in dev for the web demo; consolidation needs a frontend change.
* Legacy routers without a frontend caller (`/planning`, `/backtest`, `/data`, `/fsma`, `/reports`, `/diagnostics`, `/intake`, `/forecasts`, `/training`, `/pool`, `/jobs`) stay mounted; retiring them is an API-semantics decision.
* `web/` was not audited page by page.
* `ruff` still excludes `docs`, `dashboard` and `scripts/p1_*.py`; `mypy` covers the CI scope only.
* Post-merge CI on `main` re-runs the suite on a tree already tested in the PR (kept as the only guard against direct pushes while protection is unavailable).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

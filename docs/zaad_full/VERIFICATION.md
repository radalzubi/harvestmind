# Verification record

Executed locally on macOS ARM64, Python3.14.3. Remote CI is not represented as
green merely because local checks pass. PR20 and PR21 remain draft and unmerged;
this branch is stacked on PR21 commit `6462f70`.

## Functional and build checks

- Full shared-environment suite: **1,528 passed,1 skipped**,108.91seconds, four
  pre-existing FastAPI startup-event deprecation warnings.
- Clean isolated `.[dev]` installation: **1,528 passed,1 skipped**,
  131.33seconds,53dependency/deprecation warnings. No failing tests were skipped
  to obtain the clean-install result.
- All new v2 test files cover analytic continuous allocations, pack/transport
  integers, capacity and stock conservation, settlement/cost parity, cash timing,
  customer priority, actual-line OTIF, censored ETA, drift/intermittency, causal
  rolling replay, tenant isolation, expiry/CAS, and forced-unit-fill gate refusal.
- Three overdue-PO regressions cover expected ETA, externally optimistic worlds,
  and multiple outgoing arcs competing for the same real stock.
- `mypy ... zaad/full --ignore-missing-imports`: **117files passed**. This uses
  the CI import-stub policy; an initial invocation without that flag exposed
  absent third-party stubs, plus two real typing issues that were fixed before
  the accepted final freeze.
- Ruff on new/changed Python paths: passed. `git diff --check`: passed.
- Staged/tracked-file secret tripwire: **3passed**; no obvious secrets detected.
- `npx tsc --noEmit`: passed. `npm run build`: passed,35routes including
  `/zaad/network`. The existing Google-font build required network access.
- Browser-to-API smoke: normal and transfer fixtures load and compare; stress
  rejection/RETAIN_INCUMBENT visible; missing fields rejected visibly; anonymous
  persistent shadow save rejected; editing JSON clears the previous report.
  Initially blocked by a locked Mac, then passed after unlock and exact local
  CORS origin configuration. No real operator data or purchasing action used.
- Authenticated ledger transitions are covered through Python tests; the browser
  test intentionally did not create credentials or submit a real approval.

## Security audit scope

New optimizer and v2 API Bandit scan (`-ll`): **no medium/high findings**.
The full CI-scope scan reports **three inherited medium findings**, zero high:

| File | Finding | Status |
|---|---|---|
|`api/serve.py:20`|B104, all-interface container bind|Existing deliberate listener; requires deployment-context review/justified scanner annotation|
|`api/worker.py:38`|B310, urllib URL opening from deployment environment|Existing worker path; scheme/redirect policy needs review|
|`infrastructure/fly_machines.py:36`|B310, urllib URL opening from deployment configuration|Existing Fly transport; scheme/redirect policy needs review|

These were **not hidden or globally suppressed** to obtain a green label. The
workflow now explicitly includes `zaad/full` in type and security scanning.

A shared-environment `pip-audit` found132advisories across20installed packages;
that environment includes unrelated notebooks and versions below this repo's
declared security minimums. It is not the project dependency closure. A separate
clean virtual environment installed `.[dev]` and upgraded pip as CI does:
**no known vulnerabilities found** in that installation. Machine-readable
dependency versions and results: [dependency-audit.json](evidence/final_v2/dependency-audit.json).
No shared packages were upgraded and no declared requirements were loosened.

## Frozen benchmark environment

Engine checkpoint `488ab4c`; SHA256
`394b8d304ebaab052d21b7501941770e5dd984ddb5427274a4ada77922d7a420`.
The final simulation used the existing numerical environment: NumPy2.4.2,
SciPy1.17.1, HiGHS1.14.0, Pyomo6.10.0, pandas2.3.3, Pydantic2.13.3.
API smoke used FastAPI0.136.1/Starlette1.0.0 on localhost only; that old shared
installation is **not** the proposed release dependency set. The clean install
uses the declared newer versions, including FastAPI0.141.1/Starlette1.6.0 and
SciPy1.18.1/HiGHS1.15.1. Exact numeric replay across solver versions is not assumed.

The 1k/5k scale measurements are sparse deterministic probes, not full stochastic
production certification. See [SCALABILITY](SCALABILITY.md).

## PR 24 follow-up verification (branch `claude/zaad-pr24-release-blockers`)

Executed locally on macOS ARM64 in an isolated `.venv` with `.[dev,llm]`.
Remote CI is not represented as green by these local results.

- Focused suites: `tests/unit/test_zaad_tolerance_and_tail.py` 9 passed,
  `tests/unit/test_zaad_otif_and_adaptation.py` 5 passed and 1 skipped,
  `tests/integration/test_zaad_jobs.py` 3 passed, existing ZAAD suites
  93 passed.
- Full Python suite: **1,548 passed, 2 skipped** (1,545 in the main run plus
  the 3 job tests run in their own process so the spawned solver processes
  cannot interfere with unrelated fixtures), 119.5 seconds.
- Ruff on every changed or new Python file: passed. The 65 pre-existing
  repo-wide findings on untouched files are unchanged from the PR 24 base;
  CI lints only the files a PR modifies. `git diff --check`: passed.
- mypy on `zaad/full` and `api/routers/zaad_full.py`: only the pre-existing
  missing-stub errors for scipy and pyomo remain; the four typing errors
  introduced during this work were fixed before commit.
- `npx tsc --noEmit`: passed. `next build`: passed, all routes including
  `/zaad/network`. No web source was changed on this branch.
- Real-HTTP smoke against uvicorn on loopback with authentication required
  and a temporary data root: unauthenticated `POST /api/zaad/network/jobs`
  401; authenticated submit 202 with `executable_purchase_order: false`;
  job reached `DONE` with the stored seed, engine version and a 64-character
  config hash; the report carried `approval_required: true`; the tenant list
  showed only that job; a payload naming another operator returned 403;
  `DELETE` on a finished job returned its final row; the synchronous `/plan`
  endpoint still returned 200. No purchasing action was taken.
- Bandit `-ll` on `api`, `infrastructure`, `zaad`: **no medium or high
  findings** (10 low, all pre-existing). `nosec` annotations on those paths:
  13 on the base, 18 now, each with an inline reason (see PR24_FOLLOWUP).
- Adaptation evidence: `docs/zaad_full/evidence/adaptation/` holds every row of
  the development2 and validation2 runs for all modes, the per-run logs and
  the paired summaries. `holdout2` was not run.

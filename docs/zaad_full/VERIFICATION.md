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

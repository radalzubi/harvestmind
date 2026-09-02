# Commercial Pilot Readiness — Progress

## Baseline (2026-08-31)

- Branch: `codex/commercial-pilot-readiness`
- Base: `origin/main` at `5afaabcd2ee7213026da57f445c634f87521a37e`
- Python: 1,026 tests passed; selected-package coverage approximately 86%.
- Web: TypeScript and production build passed after dependency installation.
- Known baseline issues: stale documentation, two stochastic planning paths,
  browser auth not wired, static loss/performance pages, lockfile mismatch, four
  high-severity npm audit groups, no production deployment configuration, and
  synthetic-only validation.

## Status

- [x] Repository-wide baseline audit
- [x] Current Indiana, traceability, local-food, and competitor research frame
- [x] Implementation and acceptance plan
- [x] Canonical planning path and regression test
- [x] Browser pilot authentication
- [x] Live operational pages
- [x] Dependency and deployment hardening
- [x] Repeated Indiana synthetic validation
- [x] Commercial potential and market-gap report
- [x] Full regression and security verification

## Change log

- 2026-08-31: Created the implementation evidence pack. No customer or model
  performance claim is treated as validated.
- 2026-08-31: Ran 30 Indiana synthetic policy comparisons. The stochastic
  commercial gate passed 0/30, so the default API path now blocks stochastic
  commitments unless an operator-history benchmark passes.
- 2026-08-31: Verification passed: 1,035 Python tests, changed-file Ruff,
  TypeScript, Next.js 16.3.4 production build, and zero npm vulnerabilities at
  install. Docker/Compose files were added but could not be executed because
  Docker is not installed on this host.
- 2026-08-31: Removed unused AWS/SSH dependencies, moved legacy dashboard,
  real-LLM, and PDF stacks behind optional extras, raised patched API/runtime
  floors, declared the signal pool's previously implicit PyArrow runtime,
  and audited a clean isolated core install: 1,035 tests passed and no known
  vulnerabilities. A clean-stack warning pass reduced 3,000+ repetitions to
  29 third-party transition warnings from Starlette, LightGBM, and Pandas.

# Security policy

HarvestMind is research/pilot software for stochastic supply planning. This
document records the threat model, the assumptions every operator should
verify before connecting real partner data, and how to report issues.

## Reporting a vulnerability

Email `team@harvestmind.io` with:

- a brief description of the issue,
- the smallest reproduction you can share,
- the commit hash you observed it on,
- whether you have already shared it with anyone else.

We will acknowledge within five business days. Please do not file public
GitHub issues for security reports.

## Threat model

In scope (we treat these as real risks):

- arbitrary input through the FastAPI surface (`api/routers/*`)
- CSV/Excel files supplied through `ingestion/csv_ingestor.py`
- partner-supplied data ending up in logs, generated reports, or commits
- transitive dependency vulnerabilities flagged by `pip-audit`
- backtest correctness — specifically lookahead bias / data leakage that
  would inflate ROI claims to a partner

Out of scope for this version (intentionally — pilot software):

- enterprise identity federation, fine-grained roles, and horizontally scaled
  tenancy. Pilot access uses hashed per-operator bearer tokens and one DuckDB
  vault per operator.
- distributed rate limiting. The in-process limiter protects a single API
  process; networked deployments still need ingress limits.
- supply-chain attacks against the build environment.

## Assumptions and operating constraints

1. **Fail-closed networked deployment.** The default CORS allowlist is
   localhost-only (`api/main.py`). A pilot must set
   `HARVESTMIND_AUTH_REQUIRED=true`, `HARVESTMIND_ADMIN_KEY`, a positive rate
   limit, and `CORS_ALLOWED_ORIGINS` explicitly.
2. **No partner data in the repo.** `data/raw/`, `data/processed/`,
   `outputs/`, generated `*.duckdb`, `*.parquet`, and `*.pdf` files are
   gitignored. Synthetic data is generated deterministically by
   `synthetic/generate_pilot_dataset.py` from a seed.
3. **Secrets in env vars only.** Copy `.env.example` to `.env` and fill in;
   `.env` is gitignored. The repo contains zero hardcoded secrets — verified
   by automated scans (see "Security checks" below).
4. **Backtest results are decision support, not guarantees.** The
   rolling-origin engine enforces a strict information cutoff via
   `LeakageGuard` (`backtesting/leakage_guard.py`). The two-stage SP path
   uses *historical-mean* per-product demand as its scenario base, not
   realized future demand. Earlier development versions had a leak here
   that is now covered by `tests/unit/test_no_lookahead_leakage.py`.
5. **Solver status is checked.** `/planning/run` returns HTTP 422 if the
   solver does not reach `optimal`/`locallyOptimal`; recommendations are
   never produced from infeasible or timed-out solves.

## Security checks

Run these locally before deploying or merging changes that touch I/O or
the API surface:

```bash
make test                                       # full pytest suite
python3 -m ruff check .                         # lint, dead code, common issues
python3 -m pip_audit --skip-editable            # transitive CVE scan
grep -rEn "(api_key|secret|token|password)\s*=\s*['\"]" --include='*.py' .
```

The first three are also wired into the `make test` and `make lint`
targets.

## Deployment checklist

Before the first partner pilot:

- [ ] `CORS_ALLOWED_ORIGINS` set explicitly (no `"*"`)
- [ ] `HARVESTMIND_AUTH_REQUIRED=true`; verify an unauthenticated request is 401
- [ ] Unique operator token issued and transferred out-of-band; admin key not shared
- [ ] API behind TLS and ingress rate limits
- [ ] `APP_ENV=production` and `LOG_LEVEL=WARNING`
- [ ] `.env` populated; verify with `python3 -c "import os; print(os.getenv('NOAA_CDO_TOKEN','MISSING'))"`
- [ ] DuckDB file owned by the service user, mode `600`
- [ ] `outputs/` and `logs/` writable only by the service user
- [ ] `pip_audit` clean, or each remaining advisory recorded with rationale
- [ ] One full rolling-origin backtest completed and the resulting ROI
      report reviewed (no raw partner names appear in headlines beyond
      the partner's own ID)

## Data minimisation in reports

`reports/roi_report_generator.py` emits aggregate KPIs only — total
benefit, ROI multiple, payback, model-comparison averages. Per-supplier
or per-buyer rows are not rendered into the partner ROI HTML. If you
extend the template, keep raw line items out of the partner-facing
summary; cell-level data must stay behind HarvestMind operator authentication
and the deployment's network controls.


## Deployment posture (added in the commercial readiness pass)

- Set `HARVESTMIND_ENV=pilot|staging|prod` on any networked deployment.
  Authentication is enforced in those environments regardless of
  `HARVESTMIND_AUTH_REQUIRED`; only `dev` is permissive.
- `GET /health` reports `env` and `auth_enforced`; `GET /ready` checks the
  database and the solver. Check both after every deploy.
- Every response carries `X-Request-ID`; quote it when reporting an error.
  Unhandled errors never return a traceback.
- Findings, fixes and residual risks: `docs/security/SECURITY_HARDENING_REPORT.md`.
- CI gates: bandit (medium+ must be zero), pip-audit, CodeQL, secret scan
  in `scripts/commercial_validate.sh`; Dependabot weekly.

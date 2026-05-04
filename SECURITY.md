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

- multi-tenant authentication and authorization. The API has no auth layer
  today and **must only be exposed on a localhost or VPN-only interface**.
- rate limiting / DoS protection. Solver calls are CPU-bound; if you expose
  the API to untrusted networks, add a reverse proxy with rate limits.
- supply-chain attacks against the build environment.

## Assumptions and operating constraints

1. **Local-only deployment.** The default CORS allowlist is localhost-only
   (`api/main.py`). Production deployments must set `CORS_ALLOWED_ORIGINS`
   explicitly to a known list.
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
- [ ] API bound to localhost / private network only — there is no auth
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
summary; cell-level data should stay in the dashboard / API behind your
own auth layer.

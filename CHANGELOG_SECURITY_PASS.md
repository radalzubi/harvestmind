# Changelog — Security & Reliability Pass

_Date: 2026-06-18 · 11 files changed, 1 test file added · 490 → 506 tests passing_

## Code changes

**`api/main.py`**
- Added `security_headers` HTTP middleware (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, HSTS). Headers only — no behavior change.

**`api/routers/intake.py`**
- Added `MAX_UPLOAD_BYTES` (25 MB) + `MAX_EXTRACT_FILES` (20) caps; `_reject_if_too_large` helper → 413 on oversize uploads in `/upload/{table}` and `/extract`.
- `/intake/confirm`: enforce the `STAGING_TABLES` allowlist on the body-supplied table (400 on non-staging or missing table); fixes a write-injection and a `KeyError`→500.
- `/intake/confirm`: wrap the multi-table insert loop in a transaction (BEGIN/COMMIT/ROLLBACK); insert failures now return 422 with no partial write.
- `load_sample_data`: stop returning the absolute samples directory path; log it server-side instead.
- Added `loguru` logger import for server-side error logging.

**`ingestion/validators.py`**
- Added `KNOWN_STAGING_TABLES`; `validate_staging_df` now fails closed (returns an error) for any unrecognized table instead of passing vacuously.

**`reports/diagnostic_report_generator.py`, `reports/roi_report_generator.py`**
- Enabled Jinja2 `autoescape=select_autoescape([...])` to prevent stored/reflected XSS in served report HTML.

**`reports/grant_export.py`**
- Added `_csv_safe`; CSV cells starting with a formula character are neutralized before write.

**`reports/audit_package.py`**
- Added `_csv_safe_cell` / `_csv_safe_frame`; section CSV exports neutralize formula injection.
- `_summary_html` now HTML-escapes `partner_name`.

**`pool/pool_contributor.py`**
- `_demand_signals`: k-anonymity count query now uses the same `WHERE` filter as the signal query (floor measured against the rows that build the signal).
- `_contribute`: re-check consent immediately before the parquet write (closes a withdraw-mid-contribution window).

**`backtesting/roi_calculator.py`**
- Guard `origins_per_year` against a 0/NaN `horizon_weeks` (raise a clear `ValueError`).
- Guard `spot_savings_pct` against a sub-kilogram baseline denominator (→ 0.0 instead of an absurd percentage).
- Removed two dead, never-returned spot-percentage variables.

**`web/src/app/page.tsx`**
- "View Report" link now uses `NEXT_PUBLIC_API_URL` (was hardcoded `http://localhost:8000`); added `rel="noopener noreferrer"`.

**`web/src/app/reports/page.tsx`**
- `target="_blank"` links upgraded to `rel="noopener noreferrer"`.

## Tests

**Added `tests/integration/test_security_hardening.py`** (15 tests): security headers; confirm table allowlist + missing-key 400; oversize upload 413; validator fail-closed; CSV formula neutralization; audit HTML escape + CSV cell; ROI horizon/sub-kg guards + normal-case preservation.

**`tests/unit/test_diagnostic_report.py`** (+1 test): report escapes HTML in operator-supplied strings.

## Dependency changes

- **None.** No packages added, removed, or upgraded. (Rate-limiting via `slowapi` is recommended but deferred — see `SECURITY_CHECKLIST.md`.)

## Config changes

- **None to committed config.** `.env.example` already contained placeholders only.
- Operational guidance added in `SECURITY_CHECKLIST.md` (CORS, TLS/HSTS, reverse-proxy body limit).

## Behavior changes (intentional, minimal)

- Oversize uploads (>25 MB) now return **413** instead of being processed.
- `/intake/confirm` with a non-staging or missing target table now returns **400** (previously: wrote to the named table, or 500 on a missing key).
- `/intake/confirm` insert failures return **422** with nothing written (previously: possible partial write + 500).
- `compute_roi` raises `ValueError` on a non-positive `horizon_weeks` (previously: crash or NaN figures).
- Report HTML is now escaped — a report that previously *relied on* raw HTML in a data field would render it as text (none observed; all fields are data, not markup).
- No change to any successful, well-formed request's response shape or values.

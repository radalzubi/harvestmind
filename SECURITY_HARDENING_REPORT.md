# Security Hardening Report

_HarvestMind — production security & reliability pass_
_Date: 2026-06-18 · Scope: full repo (FastAPI backend, DuckDB data layer, Next.js frontend)_

## Executive summary

A full read-only audit was performed across authentication/authorization, multi-tenant
isolation, injection, cross-site scripting, CORS/headers, secrets, error handling, rate
limiting, data integrity, and business logic. Findings were triaged and the **safe,
behavior-preserving fixes were applied**; larger architectural items (notably the absence
of an authentication layer, which `SECURITY.md` documents as an intentional localhost-pilot
posture) are **documented for a product decision rather than changed unilaterally**, because
adding them would break every public API contract and the frontend.

- **Test status:** 490 → **506 passing** (16 regression tests added). No regressions.
- **Frontend:** `next build` passes (typecheck clean) for all 16 routes.
- **Lint:** `ruff` clean on all changed files.
- **Secrets:** none committed; `.env.example` is placeholders only; connectors read keys from the environment. Verified, no change needed.

The single most important residual risk — **no API authentication** — is real but
intentional for the current localhost pilot. It is the #1 manual action before any
network-exposed deployment (see `SECURITY_CHECKLIST.md`).

---

## Fixed in this pass

### H-1 · Broken access control: `/intake/confirm` wrote to any table named in the body
- **Severity:** High (Critical if the API is network-exposed)
- **Affected:** `api/routers/intake.py` (`confirm_extraction`), `ingestion/validators.py` (`validate_staging_df`)
- **Risk before:** The confirm endpoint grouped rows by a caller-supplied `r["table"]` with no allowlist. `validate_staging_df` returned `ok=True` for unknown tables (no rules → no errors), and `insert_from_df` accepts any valid SQL identifier. A caller could write arbitrary rows into master/fact tables (`dim_products`, `fact_orders`, FSMA tables), bypassing the staging→validation design. A row missing the `table` key also caused an unhandled `KeyError` → 500.
- **Fix:** Enforce the `STAGING_TABLES` allowlist in `confirm_extraction` (reject non-staging or missing table with **400**), and make `validate_staging_df` **fail closed** — an unrecognized table now returns an error instead of passing vacuously (`KNOWN_STAGING_TABLES` guard).
- **Residual risk:** None for table targeting on this path. Row-level field validation is unchanged.
- **Tests:** `test_confirm_rejects_non_staging_table`, `test_confirm_rejects_missing_table_key`, `test_validate_staging_df_unknown_table_fails_closed`.

### H-2 · Stored/reflected XSS: report HTML rendered with Jinja2 autoescape OFF
- **Severity:** High
- **Affected:** `reports/diagnostic_report_generator.py`, `reports/roi_report_generator.py`
- **Risk before:** Both `Environment(...)` instances omitted `autoescape` (Jinja2 default is off). The diagnostic/ROI reports are returned as `HTMLResponse` and interpolate operator-controlled strings (product/supplier/buyer names, waste reasons, `partner_name`). A crafted product name or `partner_name` query value containing markup would execute in any browser viewing the report — including partners/auditors it is shared with. (`pilot_summary_generator.py` already escaped; these two were missed.)
- **Fix:** `autoescape=select_autoescape(["html","htm","xml"])` on both environments. Numeric `fmt_*` filters are unaffected.
- **Residual risk:** Low. Serving the report with a `Content-Security-Policy` is recommended (checklist).
- **Tests:** `test_render_escapes_html_in_operator_strings`.

### H-3 · Memory-exhaustion DoS: unbounded file uploads
- **Severity:** High (Medium in localhost pilot)
- **Affected:** `api/routers/intake.py` (`/intake/upload/{table}`, `/intake/extract`)
- **Risk before:** The full request body was buffered into memory with no size cap, then pandas re-parsed it; `/extract` looped over an unbounded `files[]` and handed untrusted PDFs to `pdfplumber`. A large or many-file upload could OOM the worker.
- **Fix:** `MAX_UPLOAD_BYTES = 25 MB` per file (reject with **413**) and `MAX_EXTRACT_FILES = 20` per request.
- **Residual risk:** A streaming/`Content-Length` pre-check at the proxy is still recommended; the in-app cap bounds the already-read body.
- **Tests:** `test_upload_rejects_oversize_file`.

### M-1 · CSV / spreadsheet formula injection in exports
- **Severity:** Medium
- **Affected:** `reports/grant_export.py`, `reports/audit_package.py`
- **Risk before:** Operator-controlled text (names, reasons, `partner_name`) was written verbatim to CSVs. A cell beginning with a formula character is evaluated when a grant reviewer/auditor opens the file in Excel/Sheets.
- **Fix:** Neutralize any cell starting with `= + - @ \t \r` by prefixing a single quote (`_csv_safe` / `_csv_safe_frame`).
- **Residual risk:** None for the two export paths; future CSV writers should reuse the helper.
- **Tests:** `test_grant_csv_safe_neutralizes_formula`, `test_grant_csv_safe_passes_plain_text`, `test_audit_csv_cell_and_html_escape`.

### M-2 · HTML injection in the audit-package summary
- **Severity:** Medium
- **Affected:** `reports/audit_package.py` (`_summary_html`)
- **Risk before:** `partner_name` was interpolated raw into an f-string HTML document that is written to disk and zipped; opening it runs injected markup.
- **Fix:** `html.escape(partner_name)` before interpolation.
- **Tests:** `test_audit_csv_cell_and_html_escape`.

### M-3 · Missing security response headers
- **Severity:** Medium
- **Affected:** `api/main.py`
- **Risk before:** Only `CORSMiddleware` was registered. The report endpoints return operator-branded HTML with no `X-Frame-Options` (clickjacking), no `X-Content-Type-Options` (MIME sniffing), no `Referrer-Policy` (URL/param leakage), no HSTS.
- **Fix:** A behavior-preserving `security_headers` middleware sets `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, and HSTS (harmless over HTTP, effective behind TLS).
- **Tests:** `test_security_headers_present`.

### M-4 · Information disclosure in error responses
- **Severity:** Medium (Low)
- **Affected:** `api/routers/intake.py` (`load_sample_data`)
- **Risk before:** The 404 echoed the **absolute server filesystem path** of the samples directory to the client (recon aid).
- **Fix:** Return a generic message; log the real path server-side. (The CSV-parse error messages were left intact — they describe the *operator's own* uploaded file and are useful UX, not an internal leak.)
- **Residual risk:** Low. A global exception handler is recommended (checklist) but not required for the pilot.

### Pool privacy & data-integrity items (detailed in `BUG_FIX_REPORT.md`)
- **Pool k-anonymity count mismatch** (`pool/pool_contributor.py`) — fixed.
- **Consent time-of-check/time-of-use before pool write** (`pool/pool_contributor.py`) — fixed.
- **Non-atomic multi-table confirm insert** (`api/routers/intake.py`) — fixed.
- **ROI divide-by-near-zero / NaN** (`backtesting/roi_calculator.py`) — fixed.

---

## Audited and found NOT vulnerable (no change needed)

- **SQL injection:** queries use bound `?` parameters; the only string-interpolated SQL (`/intake/clear`, `/intake/status`, pool attach/queries) interpolates allowlisted staging-table names or server-generated `op_<hex>` ids, never raw user strings.
- **Command / code-execution / deserialization:** no shell-command execution, runtime code evaluation, or unsafe object deserialization in non-test application code.
- **Path traversal:** `operator_id` is gated by a registry-membership lookup before any filesystem use; upload filenames are sanitized to a safe basename (`vault_storage._safe_name`).
- **Secrets:** none committed; `.env.example` placeholders only; connectors read keys from the environment; no secret logging found.
- **CORS:** default is a localhost allowlist (not `*`), credentials disabled — the invalid wildcard-plus-credentials combination cannot occur.
- **Frontend XSS:** no raw-HTML injection sinks in React, no dynamic DOM markup writes, no runtime code evaluation; all API strings render as escaped JSX; data-fetch pages guard loading/empty/error states.
- **Cross-operator DB path:** `get_cross_operator_connection` is read-only, purpose-logged, and not reachable from any API route.

---

## Items NOT fixed — require a product/manual decision

| ID | Item | Why deferred |
|----|------|--------------|
| A-1 | **No API authentication / authorization**; `operator_id` is a caller-supplied parameter | Documented as intentional localhost-pilot posture in `SECURITY.md`. Adding auth changes every API contract and the frontend identity flow — a product decision, not a drop-in fix. **#1 action before network exposure.** |
| A-2 | Read endpoints (`/diagnostics`, `/planning`, `/reports`, …) run against the shared root DB, not per-operator vaults | Same root cause as A-1; correct fix is to wire reads through an authenticated operator → vault dependency. |
| A-3 | No rate limiting on heavy/unauthenticated endpoints (`/backtest/run`, `/reports/roi`, `/intake/extract`) | Adds a dependency (`slowapi`) or stateful middleware; deferred to avoid behavior/test impact in the pilot. Snippet in checklist. |
| A-4 | Re-uploading the same file is not idempotent (duplicates double dollar figures) | Fixing requires changing insert semantics / adding a content-hash or unique key — risks breaking legitimate re-uploads. Recommended approach in `BUG_FIX_REPORT.md` (H5). |

See `SECURITY_CHECKLIST.md` for concrete remediation guidance.

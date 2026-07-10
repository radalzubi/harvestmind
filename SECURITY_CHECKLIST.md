# Security Checklist

_HarvestMind — status after the hardening pass, and what remains._
_Date: 2026-06-18_

## Completed checks (this pass)

| Area | Status | Notes |
|------|--------|-------|
| SQL injection | ✅ Verified safe | Parameterized `?` binds; identifiers allowlisted |
| Command / code-exec / unsafe deserialization | ✅ Verified safe | None present in application code |
| Path traversal (operator_id, filenames) | ✅ Verified safe | Registry-gated ids; sanitized filenames |
| Hardcoded secrets | ✅ Verified safe | None committed; env-driven; `.env.example` placeholders |
| Secret/sensitive-data logging | ✅ Verified safe | No secret or operator-data logging found |
| CORS configuration | ✅ Safe default | Localhost allowlist, credentials disabled |
| Stored/reflected XSS in reports | ✅ Fixed | Jinja2 autoescape enabled |
| Frontend XSS sinks | ✅ Verified safe | No raw-HTML injection sinks; escaped JSX |
| CSV formula injection | ✅ Fixed | Exports neutralize formula cells |
| HTML injection (audit summary) | ✅ Fixed | `partner_name` escaped |
| Security response headers | ✅ Added | nosniff, frame-deny, no-referrer, HSTS |
| File-upload size limits | ✅ Added | 25 MB/file, 20 files/request |
| Broken access control (`/intake/confirm` table) | ✅ Fixed | Staging allowlist + fail-closed validator |
| Error-message info leakage | ✅ Reduced | Absolute path no longer returned |
| Multi-table insert atomicity | ✅ Fixed | Transaction-wrapped confirm |
| ROI denominator guards | ✅ Fixed | Horizon + sub-kg spot guarded |
| Pool k-anonymity floor correctness | ✅ Fixed | Count matches signal filter |
| Consent ordering before pool write | ✅ Fixed | Re-checked at write boundary |
| Frontend loading/empty/error states | ✅ Verified | Consistent guards across pages |

## Remaining risks (not changed — require a decision)

| Risk | Severity | Owner action |
|------|----------|--------------|
| **No API authentication / authorization** | Critical (if exposed) | Add an auth layer before any non-localhost deployment. `operator_id` must come from an authenticated principal, never the query/body. |
| ~~Read endpoints use the shared root DB, not per-operator vaults~~ **ADDRESSED** | — | `get_conn`/`get_readonly_conn` are now operator-aware: they route to the authenticated operator's vault (token) and require auth in enforced mode. Dev/tests fall back to the root DB. |
| No rate limiting on expensive endpoints | High (if exposed) | Add `slowapi` (snippet below) or enforce limits at a reverse proxy. |
| Re-uploads not idempotent (duplicate doubling) | High (correctness) | Add content-hash dedupe on the upload session (see `BUG_FIX_REPORT.md` H5). |
| No global exception handler | Low/Medium | Add a catch-all returning a generic body + correlation id. |
| Undated rows annualized in loss figures | Medium (correctness) | Bucket undated loss separately. |

## Recommended future hardening

- **Authentication:** issue per-operator API tokens (hashed in the registry); a single
  `Depends(require_operator)` dependency resolves the authenticated `operator_id` and is
  attached to every router. Remove `operator_id` as a client-supplied parameter.
- **Rate limiting (drop-in):**
  ```python
  # pip install slowapi
  from slowapi import Limiter
  from slowapi.util import get_remote_address
  limiter = Limiter(key_func=get_remote_address)
  app.state.limiter = limiter
  # then on heavy routes:
  @router.post("/run")
  @limiter.limit("3/minute")
  def run_backtest(...): ...
  ```
- **Content-Security-Policy** on the report HTML responses (`default-src 'none'; style-src 'unsafe-inline'`) as defense-in-depth on top of autoescape.
- **Global exception handler** + structured logging with a request correlation id.
- **DB-level lineage enforcement:** make `_operator_id`/`_upload_session_id` NOT NULL on vault staging tables so a non-API code path cannot insert untraceable rows.
- **Dependency audit in CI:** run `pip-audit` (Python) and `npm audit` (web) on each build. Note: the dependency comments referencing future-dated CVEs in `pyproject.toml` should be verified against a real advisory source.
- **operator_id format validation** (`^op_[0-9a-f]{8}$`) as defense-in-depth once auth lands.

## Deployment / configuration notes

- **Bind to localhost or a private network only** until authentication is added. The
  current posture (no auth, no rate limit) is safe *only* on a trusted host. This matches
  `SECURITY.md`.
- **`CORS_ALLOWED_ORIGINS`:** set an explicit origin allowlist in production. Do **not**
  use `*` for any host handling partner data, despite the convenience note in the code.
- **TLS:** terminate TLS at the proxy; the HSTS header added in this pass only takes effect
  over HTTPS.
- **Reverse proxy:** set a request body size limit (e.g. nginx `client_max_body_size 25m;`)
  in addition to the in-app cap.
- **Secrets:** provide real keys only via environment variables / a secrets manager; never
  commit `.env`. `.gitignore` already excludes it.
- **LLM extraction:** `USE_REAL_LLM` defaults to `false` (mock). Enabling it requires a key
  and turns `/intake/extract` into a billable, unauthenticated endpoint — gate it behind
  auth + rate limiting first.

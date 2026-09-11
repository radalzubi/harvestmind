# Security hardening report

Scope: the HarvestMind API (`api/`), operator vaults and registry
(`infrastructure/`), ingestion (`ingestion/`), the data pool (`pool/`), the
Next.js and Streamlit frontends, dependencies, CI, and Git history. Method:
OWASP ASVS/Top-10 walk of every router and dependency, bandit at medium
severity and above, pip-audit over the project's dependency closure, a
secret scan of the tree and the full history, and adversarial tests written
to *fail* if a control is missing. No live secrets appear in this document.

Severity: Critical = tenant data exposure or remote code execution; High =
authentication or authorisation bypass reachable by a misconfiguration;
Medium = information disclosure or a robustness gap; Low = hygiene;
Informational = confirmed non-issues worth recording.

## Summary

| severity | found | fixed | open |
|---|---|---|---|
| Critical | 0 | 0 | 0 |
| High | 1 | 1 | 0 |
| Medium | 4 | 4 | 0 |
| Low | 4 | 4 | 0 |
| Informational | 5 | — | — |

## High

### H-1 Authentication fail-open by default

**Vulnerability.** `HARVESTMIND_AUTH_REQUIRED` defaulted to `false`. In that
mode `get_conn` honoured the `?operator_id=` query parameter, so any
unauthenticated caller could select any operator's vault. Documented as
dev-only; nothing prevented a networked pilot shipping with the default.

**Attack path.** `GET /data/products?operator_id=<victim>` with no
credential, against a deployment that never set the flag.

**Affected code.** `api/dependencies.py::auth_required`, `get_conn`,
`get_readonly_conn`.

**Fix.** Enforcement is now on whenever `HARVESTMIND_ENV` names a deployed
environment (`pilot`, `staging`, `prod`), and an explicit
`AUTH_REQUIRED=false` does not switch it off there. `/health` reports
`env` and `auth_enforced` so the posture is observable from outside.
`.env.example` documents the rule.

**Validation.** `tests/unit/test_tenant_isolation.py::TestFailClosed` (3
tests) and `TestBOLA` (7 tests, 12 cases): a caller holding operator A's
token and naming operator B in the query, the `X-API-Key` header path,
forged and rotated tokens, suspended operators, and every operator-scoped
read endpoint without a token.

**Residual risk.** A deployment that leaves `HARVESTMIND_ENV=dev` on a
public host is still permissive. Recommended: the container entrypoint
refuse to start with `dev` when bound to a non-loopback interface (P1).

## Medium

### M-1 Unexpected upload column surfaced a database exception as HTTP 500

`POST /intake/upload/{table}` with a column the staging table lacks reached
`INSERT` and returned a DuckDB binder error. Fixed: unknown columns are
dropped with a warning naming them (`api/routers/intake.py`). Validated by
`test_unexpected_columns_produce_a_warning_not_an_error`.

### M-2 Exception text forwarded to clients

Four sites returned `str(e)` in `detail` (`api/routers/reports.py` ×2,
`api/routers/intake.py` ×2) and the Streamlit pages printed exception
messages. Fixed: exception class only; messages logged server-side. An
HTTP middleware now assigns `X-Request-ID` to every response and converts
any unhandled exception into a generic 500 carrying only the id, with the
traceback logged under it (`api/main.py`). Validated by
`tests/unit/test_error_boundary.py`.

### M-3 Non-idempotent uploads

A retried or double-clicked upload doubled every staged quantity. Fixed:
`infrastructure/vault_storage.py` keeps a SHA-256 beside each stored
upload and refuses identical content unless `force=true`; the API returns
a rejection report. Validated by `tests/unit/test_upload_idempotency.py`.

### M-4 Solver failure surfaced as an exception or as a plausible answer

`appsi_highs` raised `RuntimeError` on an infeasible model and returned a
time-limited MILP in the same shape as a proven optimum. Fixed:
`optimization/solve_status.py` classifies every outcome; unusable outcomes
return empty decisions. Validated by `tests/unit/test_solver_robustness.py`.

## Low

- **L-1** 22 string-built SQL statements (bandit B608). Each was read: all
  use allowlisted table names, identifiers validated by regex, or bound
  parameters. Each now carries a per-line `nosec B608` with its
  justification; a schema-name guard was added to `pool/pool_contributor.py`.
  bandit at medium severity is **0** and gates CI.
- **L-2** MD5 used for synthetic ids in four places (B324). Flagged
  `usedforsecurity=False`.
- **L-3** Dependency floors: `gitpython>=3.1.59`, `tornado>=6.5.8` raised
  to fixed versions. Nine other advisories were already fixed in
  `pyproject.toml`; the local environment was stale. `pip-audit` now gates
  CI on the closure CI installs. `weasyprint` PYSEC-2026-3412 has no
  published fix and is in an optional extra.
- **L-4** No Dependabot or CodeQL. Both added (`.github/dependabot.yml`,
  `.github/workflows/codeql.yml`, Python and JavaScript).

## Informational

- **I-1** Git history contains one credential-shaped string: a
  `postgresql://user:********@localhost` placeholder in `.env.example` at
  commit `38eeac9`, username literally `user`. Not a credential. No rotation
  required.
- **I-2** Tokens are stored as SHA-256 only, compared in constant time,
  rotatable, revoked on suspension (`infrastructure/operator_registry.py`).
- **I-3** Frontend keeps the token in `sessionStorage`, sends
  `Authorization: Bearer`; no `dangerouslySetInnerHTML` or `innerHTML` in
  `web/src`; error banners render `detail` text only.
- **I-4** Uploads: extension check, 25 MB cap, empty-file rejection,
  filename sanitised before storage, temp file unlinked, table allowlisted,
  identifiers regex-validated; content parsed by pandas from a temp path,
  never by name. Validated by `tests/unit/test_ingestion_adversarial.py`
  (15 tests) and `test_csv_ingestor_security.py`.
- **I-5** CORS defaults to localhost origins; production must set
  `CORS_ALLOWED_ORIGINS`. Rate limiting is per-process and off by default;
  ingress limits remain required.

## Tenancy model, stated plainly

Isolation is **physical**: one DuckDB file per operator, opened by
`DBManager` from the registry, selected only by the authenticated token.
No shared table carries a tenant column. This is strong for a pilot per
operator and would need row-level scoping before a shared-database SaaS
deployment (recorded as P1 in `COMMERCIAL_READINESS.md`).

## What was not done

- No penetration test against a deployed instance; all findings are from
  code review and in-process tests.
- No CSRF assessment: the API is token-authenticated and stateless, and the
  frontends do not use cookies.
- SSRF: the only outbound fetchers are the public-data connectors with
  fixed hosts; no user-supplied URL is fetched.

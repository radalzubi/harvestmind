# ZAAD full-stack security review — September 2026

**Status: IN PROGRESS (2026-09-25).** Branch `security/full-stack-hardening` from `main` `bdb570b` (= the frontier
decomposition runtime `328a294` plus its docs commits). Tracker written before any code change; the audit precedes every
fix; every finding is recorded before it is fixed; every confirmed vulnerability fixed here carries a regression test in
`tests/security/`. Scope: the API (`api/`), the tenant registry and vaults (`infrastructure/`), ingestion, the analytics
semantic layer and Ask ZAAD, the optimizer and diagnostic job paths, the Next.js interface (`web/`), CI and the Fly / Vercel
deployment. Primary objective: **a tenant must never read, infer, mutate, execute against, export or affect another tenant's
data or compute.** All testing against local test tenants and throwaway production demo workspaces only.

Severity: CRITICAL = cross-tenant data exposure, code execution or authentication bypass; HIGH = authorization bypass,
privilege escalation, token leakage or trivial unauthenticated resource exhaustion; MEDIUM = information disclosure, a
missing control with a compensating one, or a robustness gap an authenticated user can trigger; LOW = hygiene;
INFORMATIONAL = confirmed non-issues worth recording. Each finding is classified as a *confirmed vulnerability*, a *security
weakness*, a *defense-in-depth improvement* or a *false positive*.

The previous review (`SECURITY_HARDENING_REPORT.md`, pilot hardening) closed the fail-open auth default, exception text in
responses, non-idempotent uploads and the solver-failure masking. This review starts from the production posture as
deployed (v37): `HARVESTMIND_ENV=pilot`, auth enforced, rate limit 60 / min per IP and path, CORS allowlist without
credentials, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy: no-referrer`, HSTS, no CSP on the API, `/docs` and
`/openapi.json` public, self-serve workspaces on, the shared demo workspace off.

## 1. Architecture and attack surface

*(filled from the audit: routers, guards, storage, frontend, infra)*

## 2. Threat model

| actor | may | must not |
|---|---|---|
| A. anonymous internet user | read `/health`, `/ready`, `/access/config`, the public site; request access; start a self-serve workspace (when enabled); read the OpenAPI schema | reach any workspace read or write, any job, any report, any export; exhaust the solver, the disk or the LLM budget |
| B. VIEWER (actor token) | read the workspace, its analytics, shared analyses and dashboards, reports of finished jobs | upload or replace data, create or approve proposals, start optimizer or diagnostic jobs, use Ask ZAAD, export, change settings or consent, manage people, share analyses |
| C. BUYER | everything a viewer may plus upload, propose, evaluate, review, export, record outcomes, build and export analyses, Ask ZAAD, start plans | approve (unless the workspace allows self-approval and the role permits), share workspace-wide, manage people or settings |
| D. APPROVER | buyer's rights minus data management, plus approve / reject and share analyses | manage data, people, settings; forge another approver's identity |
| E. ADMIN (workspace token or ADMIN actor) | everything in the workspace | anything in another workspace; platform administration (`X-Admin-Key` is the platform operator's, never a tenant's) |
| F. compromised tenant user | whatever that role may, inside the workspace | escalate, reach another workspace, exfiltrate tokens |
| G. malicious tenant | everything E may in their own workspace | read, infer or affect any other tenant; starve the platform |
| H. malicious uploaded file | be parsed under limits | execute anything, escape the vault, exhaust memory or CPU, poison exports |
| I. malicious stored text (supplier, SKU, note…) | be stored and displayed as inert text | run as script or formula, steer the AI, change authorization |
| J. malicious / malformed AI response | be rejected by the validator | issue SQL, reach another tenant's data, invoke privileged actions, set solver parameters |
| K. leaked workspace token | act as that workspace until revoked | be recovered from logs, URLs, reports or exports; outlive revocation |
| L. worker / internal service with the wrong tenant context | act only on the job it was handed | choose a tenant; read a vault other than the job's |

High-value assets: workspace and actor tokens, the admin and worker keys, the provider key; order history, suppliers,
prices, purchase orders, inventory, customer identities where present, product economics; recommendations, proposals,
outcomes; reports and exports; saved analyses and dashboards; the audit log; AI prompt context; environment secrets.

Trust boundaries: (1) internet → API (bearer token per request, no cookies, CORS allowlist); (2) API → tenant vault (one
DuckDB file per operator, selected by the token only); (3) API → solver worker (private network, shared worker token,
job-scoped bundle); (4) API → LLM provider (server-side key, curated context, structured output validated before any
query); (5) browser → sessionStorage (token) and localStorage (per-viewer conveniences).

## 3. Findings (recorded before fixing; format of §48 of the brief)

Legend — class: **CV** confirmed vulnerability (reproduced), **SW** security weakness, **DD** defense-in-depth,
**FP** false positive. Attacker letters refer to §2. Reproductions are the tests named in each row (all in
`tests/security/`); every one was written to fail on `main` `bdb570b` before the fix.

### CRITICAL

**SEC-001 — A pilot customer's access code is committed and is a brute-forceable ADMIN credential.**
CWE-798 / CWE-307 / A07. Component: `docs/deploy/LIVE_MVP.md:31`, the docstring of `infrastructure/seed_workspaces.py:3`
(first added in `1daa6c7`, present in the history since), `infrastructure/operator_registry.py:171-179, 246-250`
(`set_access_code` accepts 6 characters; a code resolves to the workspace's ADMIN), `api/dependencies.py:97-117` (no
failed-attempt limit). Attacker: A (anonymous) with the repository, or A with 10⁶ requests. Precondition: the seeded
code is still the one in the repository (the live `HARVESTMIND_SEED_WORKSPACES` secret exists). Impact: full ADMIN
access to a real customer workspace; without the repository, ≈ 10⁶ guesses against an unthrottled `/me`, from as many
spoofed addresses as needed (SEC-008). Root cause: a human-typed short code used as a bearer credential, documented with
its value. Fix: the value removed from the tree (history is treated as compromised: **the owner must rotate the code**,
this pass cannot — it holds no customer credential and must not lock the customer out); failed authentications throttled
per client and globally with `Retry-After` (`api/dependencies.py`); new access codes must be at least 12 characters and
existing short ones are logged at startup as needing rotation; `seed_workspaces` refuses to *print* codes. Test:
`test_auth_hardening.py::test_failed_authentications_are_throttled`, `::test_short_access_codes_are_refused`. Status: fixed
in code; **rotation pending owner**.

### HIGH

**SEC-002 — Extraction session read needs no token and no tenant.** CWE-306 / A01. `GET /intake/session/{id}`
(`api/routers/intake.py:597`, no dependency), sessions in one global directory (`ingestion/extraction_sessions.py:38`).
Attacker: A or G with a session id (`ext-` + 12 hex, 48 bits, shown in the uploading tenant's browser). Impact: another
tenant's extracted rows (headers, sample rows, LLM output; regex-scrubbed only). Fix: the endpoint requires the
`manageData` actor; each session records the workspace that produced it (`operator_id` in `meta.json`) and both the read
and the confirm refuse a session of another workspace with 404. Test: `test_tenant_matrix.py::test_extraction_session_is_tenant_bound`.

**SEC-003 — Another tenant's extraction session can be confirmed into one's own vault.** CWE-639 / A01. `POST
/intake/confirm` (`intake.py:607-636`) loads any session by id from the body. Attacker: G holding tenant A's session id.
Impact: A's extracted rows land in G's vault (cross-tenant read by import). Fix: as SEC-002 (session bound to workspace).
Test: same file, `::test_confirming_another_tenants_session_is_refused`.

**SEC-004 — Session id used as a filesystem path.** CWE-22 / A01. `extraction_sessions._session_dir` / `load_session` /
`log_confirmation` (`:83, :167, :185`), `vault_storage.store_session_snapshot` (`:108`). Attacker: C (BUYER) via the
confirm body `session_id: "../../x"`. Impact: directories created and `confirmation.json` / `session_snapshot.json`
written outside the audit and vault roots; `result.json` read from any directory that has one. Fix: session ids validated
against `^ext-[0-9a-f]{12}$` at every entry; the storage helpers refuse anything else. Test:
`test_filesystem.py::test_session_id_traversal_is_refused`.

**SEC-005 — Every `HARVESTMIND_*` secret is copied into each worker machine's plain-text config.** CWE-522 / A02.
`infrastructure/fly_machines.py:48-55` passes through every `HARVESTMIND_*` variable except two: the admin key, the seed
workspaces (customer access codes), the worker token, the demo token. Attacker: anyone who can read machine configs, or a
compromised worker (L). Impact: platform-admin and customer credentials in a machine's config. Fix: an explicit allowlist
(`HARVESTMIND_WORKER_TOKEN`, `HARVESTMIND_DATA_ROOT`, `HARVESTMIND_ENV`, solver settings) — nothing else. Test:
`test_worker_boundary.py::test_worker_env_carries_no_admin_or_customer_secret`.

**SEC-006 — Internal worker routes are public and one static token covers every tenant's job.** CWE-284 / A01.
`/jobs/internal/{id}/bundle|progress|result` (`jobs.py:588-643`) on the public listener, guarded only by
`X-Worker-Token`. Attacker: K holding the worker token (a worker, a config reader). Impact: download any tenant's active
diagnostic bundle; overwrite any job's result (rendered into the operator's report and PDF). Fix: the worker receives a
**job-scoped** token (HMAC of the job id under the worker secret) and the routes accept only that job's token; requests that
arrived through the public proxy (Fly sets `Fly-Client-IP` on them; private-network calls carry none) are refused. Test:
`test_worker_boundary.py::test_job_token_is_bound_to_its_job`, `::test_internal_routes_refuse_public_proxy_traffic`.

**SEC-007 — Role not enforced on the solver, diagnostic, legacy and data-sharing routes.** CWE-285 / A01. Routes guarded
by `require_operator` only: `POST /api/zaad/network/jobs`, `DELETE …/jobs/{id}`, `POST …/plan`, `…/plan/from-workspace`,
`…/shadow`, `…/shadow/{id}/review` (APPROVE / REJECT), `…/shadow/{id}/outcome`, `POST /jobs/diagnostic`,
`POST /jobs/{id}/cancel`, `POST /fmcg/plan`, `POST /planning/run`, `/planning/two-sided`, `POST /backtest/run`,
`/backtest/benchmark`, `POST /assistant/ask` (LLM), `GET /assistant/summary` (LLM), `POST /pool/consent`,
`POST /fsma/lots/create`, `/fsma/cte/record`. Attacker: B (VIEWER actor token — `operator_id_for_token` resolves actor
tokens too). Impact: a viewer starts solves and LLM calls, approves shadow decisions, records outcomes, toggles data-pool
consent, writes traceability records. Fix: capability checks — `evaluate` for solves, plans, diagnostics and backtests;
`approve` for shadow review; `recordOutcome` for outcomes; `askZaad` for the assistant; `manageSettings` for pool consent;
`manageData` for FSMA writes. Test: `test_rbac_matrix.py` (every mutation × every role).

**SEC-008 — The client address is whatever the client says.** CWE-348 / A07. `api/serve.py:45`
`forwarded_allow_ips="*"`: uvicorn takes the leftmost `X-Forwarded-For`, so `request.client.host` — the key of
`rate_limiter` and `bounded_rate` — is attacker-chosen. Attacker: A. Impact: every per-address limit (public access
routes, LLM, solves, failed authentications) is bypassed; `_RL_BUCKETS` grows with each forged address. Fix: the client
address is `Fly-Client-IP` when the Fly proxy set it, else the socket peer; `X-Forwarded-For` is never read for limits
(`api/dependencies.py::client_ip`). Test: `test_rate_limits.py::test_forwarded_for_does_not_reset_the_limit`.

**SEC-009 — Request bodies are unbounded until after they are read.** CWE-400 / A04. No global body limit; uploads
(`intake.py:203, :567`) are read fully into memory before the 25 MB check; `/extract` accepts 20 files. Attacker: C. Impact:
memory exhaustion of the 2 GB machine that also serves every tenant. Fix: a body-size middleware refuses declared lengths
over the route class's cap (413) and aborts chunked bodies that exceed it; uploads are read in chunks against the cap.
Test: `test_uploads.py::test_oversized_upload_is_refused_before_it_is_read`.

### MEDIUM

**SEC-010 — Unbounded self-serve workspace creation.** CWE-770. `POST /access/start` creates a vault per call, limited only
by the (spoofable) per-address limiter. Fix: a per-address daily cap and a global daily cap (`HARVESTMIND_SELF_SERVE_DAILY_CAP`,
default 50), 429 beyond. Test: `test_rate_limits.py::test_self_serve_daily_cap`.
**SEC-011 — The workspace token travels in a URL and the interface stores it before validating it.** CWE-598.
`access.py:144, 274` (the emailed link), `web/src/app/access/page.tsx:24-39`. Fix (interface): the token is removed from
the address bar with `history.replaceState` before anything else, validated with `/me`, and stored only on success; the
link remains the pilot onboarding path (residual: mailbox and server access logs — recorded). Test: `web` unit test of
the access page's token handling.
**SEC-012 — No security headers on the interface.** CWE-1021 / CWE-693. `web/next.config.ts`. Fix: CSP (`default-src
'self'`, script/style per Next's needs, `connect-src` the API origin and the map tiles, `img-src` self data: https:,
`frame-ancestors 'none'`), `X-Content-Type-Options`, `Referrer-Policy: strict-origin-when-cross-origin`,
`Permissions-Policy`, `X-Frame-Options: DENY`, `poweredByHeader: false`. Test: `web` unit test asserting the header set.
**SEC-013 — Client CSV export has no formula-injection guard.** CWE-1236. `web/src/lib/csv.ts` used by `loss/page.tsx`
with product names. Fix: cells beginning with `= + - @ \t \r` are prefixed with `'` and quoted. Test: `csv.test.ts`.
**SEC-014 — Purchase-order PDF injects reportlab markup from customer fields (SSRF / local file read).** CWE-91 / CWE-918.
`api/product/exporting.py:383-389, :416` pass `reference`, `supplier_id`, `destination_id`, `notes` through `safe_cell`
(a formula guard, not an XML escape) into `Paragraph`. Fix: XML-escaped. Test: `test_exports.py::test_pdf_escapes_markup`.
**SEC-015 — Tracebacks print tenant data.** CWE-532. `api/routers/intake.py:24` uses loguru's default sink with
`diagnose=True`, so `logger.exception` at `:729` prints local variables — the confirm body and rows. Fix: loguru configured
with `diagnose=False, backtrace=False`; the wrong `%s` placeholder corrected. Test: `test_logging.py`.
**SEC-016 — Registry file: non-atomic writes, no lock, default permissions.** CWE-362 / CWE-732.
`operator_registry.py:73-86`. Fix: write to a temp file and `os.replace`, `chmod 0600`, an advisory lock around
load-modify-save. Test: `test_auth_hardening.py::test_registry_file_is_private_and_atomic`.
**SEC-017 — A workspace switch keeps the previous tenant's data in memory.** CWE-524. `workspace-data.tsx:240, 359`,
`session.tsx:113-130`. Fix: the workspace store keys on the operator id and resets on any token change or sign-out.
**SEC-018 — Deploy workflow: inputs interpolated into the shell, unpinned action, no permissions block, no check that the
SHA is on main.** CWE-78 / CWE-829. `.github/workflows/deploy-api.yml:39-55`. Fix: inputs passed through `env:`, `app`
allowlisted, `sha` verified to be an ancestor of `origin/main`, `permissions: contents: read`, flyctl action pinned to a
commit. (Only repository writers can dispatch it; still fixed.)
**SEC-019 — The extraction path stores and sends raw identifiers without pseudonymisation.** CWE-359. `intake.py:566-582`
vs `:235-250`. Recorded for the owner: extraction needs the raw text; the data-handling note must say so (residual).
**SEC-020 — Decision responses skip the job-ownership check when the job store is unconfigured.** CWE-863.
`zaad_history.py:176-179`. Fix: refuse with 503 instead of recording. Test: `test_rbac_matrix.py::test_decision_response_needs_the_job_store`.
**SEC-021 — Rate limiter: per-path keys, unbounded bucket map, one global budget shared by every tenant.** CWE-770.
`dependencies.py:163-181`, `zaad.py:28-46`. Fix: buckets pruned and keyed by route template; a per-tenant budget on the
expensive routes beside the global one. Test: `test_rate_limits.py`.
**SEC-022 — No Python lockfile; the image is rebuilt from `>=` ranges.** CWE-1104. Recorded for the owner (a lock changes
the build pipeline; not done blind in a security pass).
**SEC-023 — Workspace tokens never expire and only the admin can rotate them.** CWE-613. Recorded; rotation exists
(`POST /admin/operators/{id}/token`), expiry deferred with the owner.

### LOW

**SEC-024** internal exception text in a few `detail`s (`jobs.py:256, :343`, `zaad/full/jobs.py:113, :406`,
`zaad_full.py:176-179`, `zaad_analytics.py:77`, `handoff.py:98`, `intake.py:465`, `/ready`). Fix: class names only.
**SEC-025** `X-Request-ID` reflected unbounded. Fix: 64 chars, `[A-Za-z0-9._-]` else a fresh id.
**SEC-026** no `Cache-Control` on tenant responses. Fix: `no-store` on every authenticated route.
**SEC-027** `/docs`, `/redoc`, `/openapi.json` public in enforced environments. Fix: served in dev only.
**SEC-028** the interface grants every capability and role ADMIN when `/me` omits them (`session.tsx:71-89`). Fix: view only.
**SEC-029** sign-out leaves `zaad.recents.<ws>` and the sector in browser storage. Fix: cleared on sign-out and switch.
**SEC-030** `/app` writable by the app user (`Dockerfile:16`); extraction logs and the corpus live under `/app` (lost on
redeploy, shared across tenants). Fix: extraction sessions move under `HARVESTMIND_DATA_ROOT`; `/app` ownership is
recorded for a follow-up (the pool and corpus paths still write there).
**SEC-031** hand-off SKU cap overrun through commas in ids (`handoff.py:61`, `contracts.py:44`). Fix: cap after splitting.
**SEC-032** the legacy assistant accepts client-supplied `assistant` turns (`assistant.py:74-80`). Fix: user turns only.
**SEC-033** `update_analysis` `description` / `notes` unbounded (`saved.py:153-169`). Fix: 2,000 chars, strings only.
**SEC-034** a process started without `HARVESTMIND_ENV` and without `HARVESTMIND_BIND_HOST` on `0.0.0.0` is permissive
(`dependencies.py:66-80`). Recorded; the container sets both.

**SEC-035** a file that is not UTF-8 text reaches the upload's pseudonymiser and answers a generic 500 (`intake.py`,
`anonymize_csv_bytes`). Class: SW (no leak — the boundary redacts — but a hostile file produces an internal error). Fix:
422 "not readable text". Test: `test_uploads.py::test_malformed_and_odd_files_are_refused_cleanly`.
**SEC-036** a JSON body nested past the interpreter's recursion limit answers 500 on the order and analytics readers
(`zaad_orders.py:93`, `zaad_analytics.py:65`, `RecursionError` uncaught). Fix: 400 "not valid JSON". Test:
`test_exports_and_errors.py::test_broken_requests_do_not_expose_internals`.
**SEC-037** `GET /diagnostics/summary` answers 500 when a computed value is NaN ("Out of range float values are not JSON
compliant"): pre-existing and order-dependent in the suite (`test_intake_router.py::test_load_sample_data_diagnostics_computes`
fails on `main` when run alone). Class: SW (robustness). Fix: non-finite values serialised as null.

### INFORMATIONAL (confirmed non-issues)

Tokens are 256-bit, stored as SHA-256, compared in constant time; no token is logged; no endpoint takes a token in a
query string. Every SQL site interpolates code literals or allowlisted identifiers, values bind; the analytics builder
validates every metric, dimension, filter and limit against the registry and binds values — no injection found (Explore,
filters, sorts, search, saved queries, Ask ZAAD). No `subprocess`, `eval`, `exec`, `pickle.load`, `yaml.load`. No
user-supplied URL is fetched server-side (fixed hosts only). No cookies, so CSRF does not apply to the API. No markdown
renderer, no `innerHTML`; the one `dangerouslySetInnerHTML` is static JSON-LD with `<` escaped; AI answers render as text.
Ask ZAAD's output is forced through a tool schema, re-validated and re-authorised by the deterministic layer; it cannot
emit SQL, metrics outside the registry or solver parameters (the hand-off hardcodes horizon, service level and solve time
and passes ids only). Job stores scope every read, list and cancel by operator (404 otherwise); diagnostic reports are
under the caller's own vault. Server exports escape formulas and sanitise filenames. CORS is an allowlist without
credentials. The admin key fails closed when unset.

## 4. Tenant isolation matrix (`tests/security/test_tenant_matrix.py`)

Two real tenants through the real application (real tokens, no dependency override), both loaded with the same synthetic
FMCG sample and seed, so every SKU, supplier and purchase-order id exists in both vaults; tenant A creates an analysis, a
dashboard, an export format, a proposal and a diagnostic job record; tenant B's ADMIN then tries every route by A's id:

| family | routes tried with A's id under B's token | result |
|---|---|---|
| analytics | analysis read / patch / delete / run; dashboard read / patch / duplicate / delete; a B dashboard tile naming A's analysis; list and search | 404 everywhere, 422 for the tile; lists and search carry nothing of A's |
| proposals | read, history, evaluation, export preview, amendment; patch, submit, approve, export, external status, outcome, revise, delete | 404 (409 where the state machine answers first); A's proposal untouched |
| export formats | put, delete | 404 |
| diagnostic jobs | job, report.json, report.pdf, cancel, `/jobs/latest` | 404; latest is B's own |
| planning jobs | read, cancel | 404 |
| extraction sessions | read, confirm | **were 200 / 200 before (SEC-002 / 003)** — 401 anonymous, 404 another tenant, 200 own |
| workspace reads | inventory, suppliers, purchase orders, datasets by id | served from B's own vault (same ids, B's rows) |
| analytics cache | identical query spec from A and B | each answered from its own vault (`cache.py` keys carry the tenant) |

Ids through path, query, JSON body, nested references (dashboard tiles, hand-off) and pagination were exercised; no
response disclosed whether A's resource exists.

## 5. Role / capability matrix (`tests/security/test_rbac_matrix.py`)

Twenty-four mutations × four roles through real actor tokens, plus anonymous. Before this pass a VIEWER could start a
diagnostic, submit and cancel planning jobs, run the frozen planner, the legacy planners and the backtest, use the
legacy assistant (an LLM call), toggle data-pool consent and write FSMA records; a BUYER could approve or reject shadow
decisions; an APPROVER could write traceability records. After: every one of those answers 403 with the governance
message; the allowed roles are unchanged for everything that was already gated (uploads, proposals, approvals, export
formats, settings, people, analytics). The role always comes from the token — naming a role in a header, query or body
changes nothing — and a revoked actor token is dead on every route.

## 6. Uploads (`tests/security/test_uploads.py`)

Bounded before they are read: a declared length over the class cap is 413 without a body; a streamed body over the cap
is cut at the cap (uploads 64 MiB per request, everything else 20 MiB; the routes keep their own tighter caps: 25 MB per
file, 2 / 8 / 16 MiB JSON). Hostile CSV cells (formulas, script, SQL, prompt text, emoji, NUL, traversal) upload and stay
inert text in listings and search; a non-UTF-8 file, an empty file, duplicate headers and a traversal filename answer
4xx and land inside the vault if at all. Row and column counts remain bounded by the 25 MB file cap and pandas; a row cap
is recorded as a follow-up. No formula is ever evaluated: XLSX is read with openpyxl `read_only` / `data_only`.

## 7. Exports (`tests/security/test_exports_and_errors.py`, `web/src/lib/zaad/__tests__/security.test.ts`)

Server CSV / XLSX: every customer cell through `safe_cell` (formula guard), server-controlled filenames, provenance
block. Server PDF: customer fields XML-escaped (SEC-014 — `<img src=…>` no longer reaches reportlab). Client CSV:
formula guard added (SEC-013). Every export route is tenant- and capability-scoped (matrix above).

## 8. Frontend

No markdown renderer, no `innerHTML`, one static JSON-LD `dangerouslySetInnerHTML` with `<` escaped; AI answers, errors
and API strings render as React text. Payloads (script, SVG handler, IMG error, `javascript:` URL, nested HTML) stored
as supplier names render inert. Redirects use constants; external links carry `rel="noopener noreferrer"`; the map
style origin and the API origin are the only external hosts. After this pass: the access link strips the token from the
address bar before validating and stores it only on success (SEC-011); the header set carries CSP, frame-ancestors,
nosniff, referrer and permissions policies and `X-Powered-By` is off (SEC-012); a workspace switch or sign-out clears
the previous workspace's in-memory data and its stored labels (SEC-017 / 029); the interface assumes no capability the
API did not grant (SEC-028). Storage: the token in `sessionStorage` (per tab), locale / shortcuts / pins / hidden columns
in `localStorage`, no datasets or reports client-side, no service worker. The self-serve start page shows the new
workspace's token once so the person can keep it (by design; the API never returns it again).

## 9. Analytics (`test_tenant_matrix.py`, `tests/integration/test_analytics_security.py`, review)

Every metric, dimension, filter, sort, top-N and limit resolves through the semantic registry before any SQL is built;
identifiers in SQL are registry ids, values bind with `?`; `' OR 1=1 --` in a filter is data (no match). Role
classifications gate metrics and dimensions server-side; hidden metrics are not in the registry a role sees. Cache keys
carry tenant, dataset version, model version, role and spec hash. Free text on saved analyses is now bounded (SEC-033).

## 10. Ask ZAAD / AI

Architecture as required: question → model → **tool-schema-constrained candidate spec** → `AnalyticsQuerySpec` validation →
the same `validate()` and permission classes as a typed query → governed engine → result; one repair round, then a
rules fallback. The model cannot emit SQL, name metrics outside the registry, reach another tenant (its context is the
caller's vault only) or set solver parameters: the hand-off hardcodes horizon 12, service level 0.95 and 15 s and passes
ids only (now capped at 50 after splitting, SEC-031); submitting needs `evaluate`. Prompt-injection text stored as
supplier / SKU names reaches the model as data inside a bounded member list; the deterministic validator decides what
runs. The legacy `/assistant` now needs `askZaad` and takes only the client's own turns (SEC-007 / 032). Residual: the
extraction path sends raw identifiers to the provider (SEC-019, recorded for the owner).

## 11. Optimizer and diagnostic jobs

Job stores scope every read, list and cancel by operator (404 otherwise). Submission needs `runPlanner` /
`runDiagnostic` (SEC-007). Existing protections kept: the bounded interactive limits (413), the batch envelope (200
SKUs / 400 sources / 200 services / horizon / scenarios / stresses), the aggregate solver-time cap, the per-operator
quota (`QuotaExceeded` → 429), one active diagnostic per workspace (a second press returns the same job), the ordered
solver lease, the stale-job reaper, the hard job timeout. The worker boundary: an allowlisted environment and a job-scoped
token (SEC-005 / 006). Reads stay off the rate limiter so polling works; a tenant cannot cancel or read another's job.
Residual: the global recommendation budget is shared by every tenant (a per-tenant budget is recorded), and the
solver still shares the API machine (the frontier record's infrastructure recommendation).

## 12. Errors, logging, audit

Unhandled errors: generic 500 with a request id; the traceback stays server-side. Job failures now carry the class name
and the reference, never the message (SEC-024). `/ready` answers "unavailable" without a class. The intake logger no
longer prints local variables (SEC-015). No log line carries a token, a header or a body. The append-only audit log
records proposals, approvals, exports, outcomes, settings, sharing, uploads and data replacement, hand-offs and — the
platform-level events (token issue, actor revocation, self-serve start) are logged by the API logger with the request id;
moving them into the audit table is recorded as a follow-up.

## 13. Secrets, dependencies, CI

The committed customer access code is removed from the tree (SEC-001; the history still holds it — rotation is the
owner's action). No other secret in the tree or the probed history; `.env.example` files hold placeholders; the two
`NEXT_PUBLIC_*` names are the API origin and the map style. `pip-audit` (with the accepted weasyprint advisory) and
`npm audit`: **0 known vulnerabilities** on 2026-09-25. CI: least-privilege token, `pull_request` (not `_target`), gitleaks,
bandit, pip-audit, ruff, mypy, the frontend build and, from this pass, the `security` shard. The deploy workflow no longer
interpolates inputs into the shell, allowlists the app, verifies the commit is on `main` and pins the flyctl action to a
commit (SEC-018). No Python lockfile (SEC-022, recorded).

## 14. Infrastructure and data at rest

Fly: one public `http_service` to port 8000 with `force_https`, TLS at the edge, `/health` checks; the app listens on the
public proxy and the private network; the proxy stamps `Fly-Client-IP`, which is now the only address the limits trust
(SEC-008); the internal worker routes refuse proxy traffic (SEC-006). Vercel: the interface calls the API cross-origin with
a bearer header (no cookies, so CSRF does not apply); production builds carry no source maps; the CSP is set in
`next.config.ts`. Data at rest: one DuckDB per tenant under the Fly volume (`/var/lib/harvestmind/operators/<id>/` with
`uploads/`, `sessions/`, `exports/`, `reports/`), the registry (token hashes, HMAC secrets — now 0600, atomic) beside it,
the planning job store and shadow ledger as SQLite on the volume, extraction sessions now under the data root
(SEC-030). Encryption at rest is what Fly volumes provide (block-level); ZAAD implements none of its own — stated, not
claimed. Backups: Fly volume snapshots (daily, Fly's retention) — no application-level backup exists. Offboarding:
`delete_operator` marks the record only; vault files, uploads, sessions, reports, the pool contributions and the training
corpus remain on disk — **no complete tenant deletion exists** (recorded as a blocker for real customer data, §16).

## 15. Security test inventory

`tests/security/`: `test_tenant_matrix.py` (37), `test_rbac_matrix.py` (124), `test_filesystem.py` (22),
`test_worker_boundary.py` (3), `test_rate_limits.py` (6), `test_uploads.py` (5), `test_exports_and_errors.py` (6),
`test_auth_hardening.py` (12), `test_logging.py` (2); plus `web/src/lib/zaad/__tests__/security.test.ts` (3) and the
existing `tests/unit/test_tenant_isolation.py`, `test_auth.py`, `test_error_boundary.py`, `test_ingestion_adversarial.py`,
`test_csv_ingestor_security.py`, `tests/integration/test_analytics_security.py`, `test_security_hardening.py`,
`test_operating_product_v2_governance.py` (which now scans the newly gated routers). Every test is deterministic, needs no
network or key, and runs in the CI `security` shard.

## 16. Scorecard, residual risks, release record

*(at the end)*

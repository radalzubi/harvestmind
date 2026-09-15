# Fable 5.1 — independent audit of ZAAD Operating Product V1

**Auditor:** Claude Fable 5.1, acting as release owner. **Date:** 2026-09-15.
**Subject:** PR #81, branch `feat/zaad-operating-product-v1`, Opus handoff head
`3333b0eb7e14f5e5f1e566384a968d1fc0f09a1f`.

**Overall verdict: PASS WITH REQUIRED CORRECTIONS.** Two blockers, seven high-severity defects and
five correctness/security mediums were found by reproducing the product rather than reading about
it. Each is listed in §3 with how it was reproduced and what the correction is. The corrections are
made on the same branch; §5 records the audited checkpoint.

Nothing in this document is taken from the handoff on trust. Where a claim of the handoff was
reproduced it says so and how; where it was not reproduced it says that.

---

## 1. Starting position, verified

| item | verified value | how |
|---|---|---|
| `main` | `4a564707eb6a27fa16816e7c6e12e78b38c1e3b1` | `git rev-parse origin/main` after `git fetch --prune` |
| PR #81 | open, **draft**, base `main`, head `3333b0e…`, `mergeable: MERGEABLE`, `mergeStateStatus: UNSTABLE` | `gh pr view 81 --json …` |
| why UNSTABLE | the two Vercel checks report *"Deployment rate limited — retry in 24 hours"*; all 13 CI jobs are green | `gh pr checks 81` |
| branch head, local = remote | `3333b0eb7e14f5e5f1e566384a968d1fc0f09a1f` | `git rev-parse HEAD origin/feat/zaad-operating-product-v1` |
| working tree | clean, 0 modified / untracked | `git status --porcelain` |
| commits ahead of `main` | 110, merge base = `main` | `git rev-list --count`, `git merge-base` |
| `zaad/` and `evidence/` touched by the branch | **0 files** | `git diff --name-only main...HEAD \| grep -c '^zaad/'` |
| CI on the exact head | run `34894456602`, **13/13 success** | `gh run list --commit 3333b0e…` |
| production, unchanged | Fly `zaad-api` v25, image `canonical-e0fecdc`, one machine `started`, checks passing; Vercel project `zaad` (`prj_nzwPFrhoazRhmvUpqiT6S38AvD6I`), CLI signed in as `radalzubi2005-5818` | `fly status`, `fly image show`, `vercel whoami` |
| merge convention of previous release PRs | merge commit titled `Merge PR #NN: …` (#76, #77, #78, #79, #80) | `git log --merges` |

The PR head had **not** moved since the handoff. Nothing was reset.

## 2. Opus's claims, reproduced or not

| claim | result | evidence |
|---|---|---|
| 2,105 backend tests passing | **reproduced**: `2105 passed, 2 skipped, 8 warnings in 397.76s` | `python3 -m pytest tests/ -q -p no:randomly` on the head |
| 129 frontend tests passing | **reproduced**: `# pass 129 / # fail 0` | `npm test` in `web/` |
| canonical frozen regression passing | **reproduced**: `CANONICAL REGRESSION PASS`, every P1 arm identical over 12 reviews, P0 cell 15 identical and protection-owned | `PYTHONPATH=. python3 scripts/zaad_canonical_regression.py` |
| no optimizer math changed | **reproduced**: no file under `zaad/` or `evidence/` in the diff | see §1 |
| 50,000-product / ~4M-row scale | **reproduced**: fixtures rebuilt (10,000 / 780,120 rows; 50,000 / 3,900,120 rows), slowest median **318.3 ms** (data-explorer search at 50k) against the 800 ms budget, 0 over | `scripts/zaad_qa_workspaces.py scale`, `scripts/zaad_product_scale_bench.py` |
| proposal overlay working | **reproduced and verified**: see §4.2 | job store diff |
| PO lifecycle working | **reproduced**: create → edit → evaluate → compare → approve → export → revise → history, every step read back from the vault | §4.1 |
| CSV / XLSX / PDF export working | **reproduced**: all three produced from the live API, CSV read back, XLSX cells inspected with openpyxl, PDF rendered to an image and looked at (landscape, all twelve columns) | §4.5 |
| tenant isolation working | **reproduced**: 12 read paths and 7 write paths with a second workspace's valid token, every one 404/empty with no metadata | §4.6 |
| Network V2 working | reproduced as a surface (graph renders, objects lead somewhere); one status-vocabulary contradiction found (M3) | §4.7 |
| supplier diagnostics working | reproduced; one false zero found (H7) | §4.7 |
| Data explorer working | reproduced, including the allowlist and bounds under hostile input | §4.6 |
| browser write methods fixed | reproduced: PATCH and DELETE from the browser 200/204; preflights 200 | network tab |
| status contradictions fixed | **partly**: the ladder holds on Home/Decisions; the network canvas still says "Risk rising" under a Home that says "running normally" (M3) | §4.7 |
| solve timings 62–92 s / 108 s / 232 s | **reproduced from the job store**: 6 products 62.0 s, 71.2 s, 91.3 s, 92.3 s; 8 products 108.0 s; 10 products 231.9 s and 235.0 s; a new 6-product evaluation in this audit: 91.6 s + 53.3 s | `started_at`/`finished_at` of every row |
| migration 023 idempotent | **reproduced**: `setup_db.py` twice on a fresh file, 57 tables both times, six product tables, `brand` and `sub_category` present | fresh DuckDB file |
| reflow at 320 px | **reproduced**: 0 px horizontal overflow on Home, Inventory, Purchase orders (drawer open), a proposal, a supplier page, Data | `scrollWidth − clientWidth` |
| contrast | **reproduced** on the proposal page: 239 text nodes, 0 below AA | computed from the rendered DOM |
| keyboard | **reproduced**: Enter on a focused row opens the drawer with focus inside it; Escape closes it and restores focus to the row | DOM `activeElement` |
| "a job orphaned by an API restart stays RUNNING for ever" (handoff §10.1) | **reproduced**, and it is worse than described: see B2 | §3 |

## 3. Defects found independently

Severity: BLOCKER / HIGH / MEDIUM / LOW. "Fix" states what the corrective pass does; §5 records the
commits.

### BLOCKER

**B1 — Concurrent requests to one vault crash with a DuckDB file-handle conflict, and the 500 has no CORS headers.**
`infrastructure/db_manager.py` opens a fresh `duckdb.connect(path)` per request and closes it after
the response. When one request's connection is the last one open and closes while another request
is connecting to the same file, DuckDB's instance cache misses and the new instance fails with
`Binder Error: Unique file handle conflict: Cannot attach "harvestmind" … is already attached`.
Observed three times in one browsing session in `api.log` (`/api/zaad/network/directory`,
`/api/zaad/orders`, `/api/zaad/workspace/purchase-orders`), each while a write (a proposal being
created) overlapped page loads. Reproduced deterministically in-process: two writer threads and six
reader threads on one vault for 10 s → **712 errors** (524 reads, 188 writes) out of ~140,000
operations. The browser showed *"Failed to fetch"* on the Purchase orders tab, because the
outermost error boundary (`_request_id_middleware`) sits **outside** `CORSMiddleware`, so its 500
carries no `Access-Control-Allow-Origin` and the browser refuses to read it — including the
`X-Request-ID` the error copy tells the operator to quote.
*Fix:* one long-lived anchor connection per vault path held by the process (`DBManager`), every
request served a cursor on it, so the file is never re-attached; the error boundary moved inside
CORS so a 500 is readable; a regression test that hammers one vault from threads; a test that a
raising route still answers with CORS headers and a request id.

**B2 — Jobs orphaned by a process restart never reach a terminal state, and queued jobs never run.**
Reproduced: a 6-product plan submitted, the API killed with SIGKILL while it was RUNNING, the API
restarted. 90 s later `GET /jobs/{id}` still answered `RUNNING` (`finished_at: null`,
`timeout_s: 1800`); the active quota counted it; a job that was **QUEUED** at the time of the
restart stayed QUEUED for ever and was never executed. Cancelling the orphan answered
*"cancelled before start"* about a job that had started. Two orphans block a workspace from
planning (active quota 2). The solver child processes are daemons and die with the parent, so
nothing else is running — the rows are simply never updated.
*Fix (job infrastructure only, no optimizer mathematics):* `zaad/full/jobs.py` gains an owner and a
heartbeat lease per running job, reconciliation on startup and on every read (an expired lease
becomes the explicit terminal status `ABANDONED` with a reason; a job past `started_at + timeout_s`
with no live owner likewise), queued jobs owned by nobody are resumed at startup, and cancel says
what actually happened. The frozen regression is re-run after the change.

**B3 — Found while fixing B1: a schema change left in the write-ahead log makes a vault unopenable after a hard stop.**
Holding one connection open per vault (the B1 fix) means nothing checkpoints on close the way a
per-request connection did, so writes wait in DuckDB's write-ahead log until its own threshold.
Data-manipulation entries replay fine after a crash; a **schema** entry does not: with a single
`ALTER TABLE zaad_evaluations ADD COLUMN IF NOT EXISTS draft_hash VARCHAR` left in the WAL — which
is exactly what `ensure_tables` writes to every existing vault on the first request after this
release is deployed — DuckDB 1.5.2 refuses to open the file (`INTERNAL Error: Failure while
replaying WAL … GetDefaultDatabase with no default database set`). Reproduced live (the QA vault
became unopenable after the orphan-job reproduction's SIGKILL) and bisected offline to that one
statement; the copy with the `ALTER` followed by `CHECKPOINT` reopened. V1 was safe only because
its per-request connection closed, and checkpointed, straight after the DDL.
*Fix:* `ensure_tables` checkpoints after any DDL it ran; an anchor that goes idle is checkpointed
(throttled to once per two seconds; 0.3 ms on an unchanged 16 MB vault, 7 ms after a write); a
clean shutdown checkpoints every idle anchor; a test performs the 024 upgrade in a subprocess that
exits without closing and asserts the vault reopens. The unreplayable WAL from the reproduction is
kept at `/private/tmp/acme_vault_unreplayable.wal` as evidence; the QA vault was recovered by
removing it, losing only this audit's own writes since the previous restart.

**Not a defect, recorded so nobody chases it again — request "hangs" under load testing.** During
the audit some requests took 30 s or never answered, at first blamed on the job store, then on the
solver child starving the API. Thread dumps showed the server idle while the client waited, and a
CPU-hog experiment (eight busy processes at normal priority against the API at low priority: 145 of
145 answered in under 10 ms) ruled out starvation. The kernel showed **2,664 loopback sockets in
TIME_WAIT** from this audit's own probes; a burst of 2,500 fresh connections produced 131
failures, the next 100 produced 3, and after 45 s of quiet the same probe passed 100 of 100 (the
TIME_WAIT count itself had not yet fallen — 4,904 — so it is the client's port-collision rate, not
the count, that matters). It is the loopback client, not the API. A
solver-priority change tried on the way was reverted for lack of evidence. Browsers keep
connections alive and never see this; the production API sits behind Fly's proxy.

### HIGH

**H1 — Staleness is decided by timestamp coincidence, so every approved and exported proposal is reported as out of date.**
`read_evaluation` computes `stale = draft.updated_at > evaluation.created_at`, and `updated_at` is
bumped by *approve*, *reject*, *export* and *evaluate itself*. Reproduced twice: QA-LIFECYCLE-1
(exported on 2026-09-14, never edited after its evaluation — events: created, submitted, approved,
exported) answers `stale: true`; FABLE-AUDIT-1 in this audit showed **"This comparison is out of
date. This proposal was changed after it was evaluated"** the moment Approve was clicked, on the
approval record, with no edit in between. The brief (§12) asks for deterministic identities rather
than timestamps.
*Fix:* the evaluation stores a content hash of what it evaluated (lines and the header fields the
overlay reads) and a workspace data version (a hash over the staging tables' upload lineage);
`stale` is a hash comparison and the reason says which changed. Old evaluations without a hash fall
back to the timestamp rule, but only against *edited* events.

**H2 — Approval does not check or record evaluation freshness.**
`transition("approve")` approves a draft whose latest evaluation is stale, or that has none, and the
approval record does not name the evaluation it was made against. §93 of the brief: *on stale
evaluation, do not approve silently.*
*Fix:* an approval records `approved_evaluation_id`; approving over a stale evaluation is refused
(`evaluation_stale`) unless the caller explicitly acknowledges it, and the acknowledgement is
written to the event. Approving with no evaluation stays allowed (a buyer may approve a manual
order without asking ZAAD) and the record says so.

**H3 — Evaluation submission is not atomic and jobs carry no purpose.**
`POST /{id}/evaluate` submits the baseline run, then the overlaid run, and only then inserts the
`zaad_evaluations` row that marks them. A workspace read landing in that window — or after the
insert fails — adopts the baseline run as the workspace's plan. Confirmed by reading the code and
the frontend's `listPlanJobs` exclusion (`workspace-data.tsx`), which depends entirely on that row
existing. The handoff records this as its §10.6 and §10.12.
*Fix:* a persisted `purpose` on every job (`WORKSPACE_PLAN`, `PROPOSAL_BASELINE`,
`PROPOSAL_OVERLAY`) and a `reference` (the evaluation id); the evaluation record is written first,
the jobs are submitted against it, and a failure between the steps leaves a FAILED evaluation and
no plan-looking job. Readers select plans by purpose.

**H4 — The amendment view reads the first DONE job of any kind.**
`GET /{id}/amendment` iterates `store.list(operator)` and takes the first `DONE` job, which after an
evaluation is the *overlay* run — a plan of the workspace plus an order nobody placed — and reads
its commitment block as "ZAAD's last plan". *Fix:* select by purpose `WORKSPACE_PLAN`.

**H5 — A 500 is unreadable from the browser.** Part of B1; listed separately because it affects
every unhandled error, not only the vault race. *Fix:* as B1.

**H6 — A refused create leaves an orphan draft.**
`create_draft` inserts the head row and *then* validates the lines; when a line is refused (a
quantity of 10¹⁸, 501 lines) the head row stays. Reproduced: four "0 lines" drafts and one with a
300,000-character supplier id appeared on Home's *Recent activity* and in *Proposals open: 8* after
refused requests. The handoff fixed the same shape for edits and not for creates.
*Fix:* lines are checked before anything is written and the create runs in one transaction.

**H7 — "Open orders 23 — none past their date" on a supplier with no promised dates.**
`late_open_orders` counts `promised < as_of` and is zero when no order carries a promise; the page
prints *"none past their date"* under a header that says *"no promised dates uploaded"* — the false
zero the handoff's third day removed from three other columns.
*Fix:* `open_orders_with_promise` in the supplier metrics; the page says *"no promised dates"*
when it is zero.

### MEDIUM

**M1 — An unapproved draft can be exported as a purchase-order file.** `POST /{id}/export` has no
state check: a DRAFT, READY_FOR_REVIEW, REJECTED or SUPERSEDED proposal produces a file
(reproduced: 200, 185 bytes, from a DRAFT amendment). The product's own lifecycle is
APPROVE → EXPORT. *Fix:* export requires APPROVED or EXPORTED; the interface disables the button
with the reason.

**M2 — Identifiers are unbounded.** A 300,000-character `supplier_id` was stored (201) and
rendered on Home. `sku`, `destination_id`, `source_po_id`, `source_decision_id` likewise.
*Fix:* a 200-character bound on identifiers, refused in words.

**M3 — Status vocabulary contradiction between Home and the network canvas.** The P0 `PROTECT`
stance is labelled **"Risk rising"** on a site node (`model.ts` `STANCE_LABEL`) while Home says
*"Every supplier, lane and site ZAAD can see is running normally"* and the twin's own headline says
*"Everything looks normal"*. `OPERATING_PRODUCT_V1.md` §3 states that planned protection is the
system working, not a warning — the label says the opposite. *Fix:* the stance is named for what it
is ("Protecting stock"), and the chip is labelled as a plan stance, not a status.

**M4 — `PUT /profiles/{id}` upserts under a caller-chosen id.** An unknown id creates a profile
named by the caller (reproduced: `profile_doesnotexist` created). Within the caller's own
workspace, so not a tenant issue. *Fix:* PUT on an unknown id is 404.

**M5 — The imported-order drawer's "See the reasoning" links to `/decisions` with no decision id**,
landing on the page unselected although the page reads `?decision=` and the id (`po:<PO>`) is
known at the link. *Fix:* carry the id.

**M6 — No optimistic concurrency on edits; evaluation is not idempotent; the event history has no
"evaluation requested" event and a revision's history does not show its predecessors.** Recorded
here; addressed by the V2 governance work (§90–91, §58 of the brief) rather than patched twice.

**M7 — The Upload page says "Nothing needs your attention" while the purchase-order source carries
no promised delivery date for any of its 16,751 lines**, which is why three diagnostics say
lateness cannot be measured. Handoff §10.13. Addressed by V2 data readiness (§45–47).

### LOW

* **L1** The PDF shows the spreadsheet formula-escape prefix (`'=HYPERLINK…`) in cell text; a PDF
  has no formula risk, so the prefix is a cosmetic artefact of one `safe_cell` for three formats.
* **L2** The default filename template `{reference}_{supplier}_{date}` produces the same name for
  every revision of an order.
* **L3** An amendment proposal's *Order date* defaults to the wall-clock date rather than being
  absent (the order already exists).
* **L4** A `curl` client sending `Expect: 100-continue` with a 185 KB job body waited indefinitely
  against uvicorn on this machine; with the header suppressed the same request answers 202 in 9 ms.
  Browsers never send the header. Recorded for whoever integrates with the jobs API from libcurl.
* **L5** `27 d` renders `d 27` under `dir="rtl"` (known: handoff §10.14); reproduced on the
  supplier page. Addressed by the V2 i18n work.
* **L6** Cancelling an orphaned job answers "cancelled before start" (part of B2's fix).

## 4. What was walked, and what was measured

### 4.1 The buyer journey, live

Production build of the branch (`next build --webpack`, served by `next start`), the API started
with `ZAAD_JOB_STORE`, `HARVESTMIND_AUTH_REQUIRED=true`, `ZAAD_LEGACY_PLANNERS=0`,
`ZAAD_ATP_ENABLED=1`, workspace **Acme Importers** (`op_eb4f2c4f`: 150 products, 8 suppliers,
3 sites, 205 open orders, 18 declared amendment rights).

FIND SKU (`/inventory?q=SKU-0001`) → VIEW INVENTORY (drawer: 5,669 on hand across DC 2,835 /
NORTH 1,417 / SOUTH 1,417; 3,312 on order on 2 open orders; 12 recent POs) → VIEW SUPPLIER
(`/diagnostics/supplier/SUP-001`: 1,865 matched orders, fill 95.7 %, p50 14 d, p90 21 d) → VIEW
OPEN PO (`/orders?po=PO-016648`: 1,776 units, three declared rights with fees and deadlines) →
VIEW ZAAD DECISION (Decisions: KEEP PO-016648, two reasons, six commitments) → CREATE PROPOSAL
(FABLE-AUDIT-1, 480 units of SKU-0001 from SUP-001 to SOUTH; also an amendment "Change to
PO-016648: Arrive later") → EDIT (480 → 504; vault line reads 504.0) → EVALUATE (two jobs on the
released path: baseline 91.6 s, overlay 53.3 s) → COMPARE (three columns, 11 ledger rows, 12
service lines) → APPROVE (reason stored, `approved_by`, `approved_at`) → EXPORT
(`FABLE-AUDIT-1_SUP-001_20260915.csv`, export log row, state EXPORTED) → REOPEN (revision 2
created as a draft, revision 1 marked SUPERSEDED and kept) → TRACE (events: created, edited,
approved, exported). Every step was read back from `zaad_draft_orders`, `zaad_draft_lines`,
`zaad_draft_events`, `zaad_export_log` and `zaad_evaluations` in the vault, not from the screen.

### 4.2 The three-column comparison, recomputed

For both finished evaluations (`eval_02f6bcd5884b4842`, `eval_17c6e2edabd54c44`) the two stored
requests were diffed field by field: the **only** differing key is `pipeline`, the shared entries
are identical, and the overlay adds exactly one entry (`proposal_<draft>_1`, `stage: placed`,
`ordered` = the buyer's quantity, one `keep` option at the buyer's price, `provenance:
OPERATOR_DECLARED`). `as_of`, `seed` (41001), `horizon` (12), `scenarios` (6), the six products,
sources, locations and services are identical. Every ledger row's *current* equals the baseline
report's `economics.incumbent_costs[key]`, *ZAAD* equals `selected_costs[key]` from the same
report, *proposal* equals the overlay report's `incumbent_costs[key]`, and the difference equals
proposal − current to 1e-9 — **11 of 11 rows on both**; working capital and all 12 service rows
likewise. The two reports carry different `information_hash` values (the overlay is part of the
request), which is correct and is why staleness must not be judged from that field alone.

### 4.3 The overlay, attacked

A different supplier with no approved source → refused in words (`proposal_refused`); a missing
price → evaluated with the source's declared price and a note saying so; a quantity of 10¹⁸ →
refused (`MAX_LINE_VALUE`); 501 lines → refused; duplicate products → warned, each line a separate
pipeline entry; a deleted line → the draft re-validated before deletion; the proposal edited after
evaluation → `stale: true` with a reason (the correct branch of H1); evaluated twice → two records,
the newest read (not idempotent, M6); an amendment → `amendment_not_evaluated` 422 by design;
API restart during evaluation → B2. Source tables: no `INSERT`, `UPDATE` or `DELETE` in
`api/product/` names a `stg_` table (grep), and the vault's supplier and open-order counts were
identical before and after the walk.

### 4.4 Imported PO immutability

The amendment created against PO-016648 is a row in `zaad_draft_orders` with `source_po_id` and
`amendment_action`; `stg_fmcg_purchase_orders` for PO-016648 is unchanged (1 line, 1,776 units).
The product has no code path that writes a staging table.

### 4.5 Export

CSV: UTF-8 BOM, twelve headings, `Content-Disposition` filename from the template,
`X-ZAAD-Transmitted: false`. XLSX: every cell `data_type 's'`. PDF: A4 landscape, all twelve
columns including Currency, cells wrap. Formula injection: a reference of `=HYPERLINK("http://evil")`,
notes of `@SUM(1)`, a line note of `-2+3` and a product code of `=cmd|calc` all leave prefixed with
`'`; the filename is reduced to `HYPERLINK_http_evil__SUP-001_20260914.csv`. Revision identity:
each revision is its own `draft_id`, so an export of revision 2 cannot contain revision 1; the
export log records the revision. Profile selection is manual (handoff §4.3) — V2 §53.

### 4.6 Tenant isolation and security

With a freshly issued token for **QA Large Distributor** (`op_a194ebfb`) against Acme's objects:
draft, evaluation (with and without `evaluation_id`), amendment, job, product, purchase order,
supplier → **404 with a sentence and no metadata**; search for Acme's PO and supplier ids → empty
or the caller's own matches; the explorer filtered on Acme's PO → 0 rows; PATCH, DELETE, approve,
export, evaluate on Acme's drafts and cancel on Acme's job → 404; `?operator_id=op_eb4f2c4f` beside
a valid token → ignored (the token's vault). Anonymous → 401. Hostile names (`sort=sku;DROP`,
`__proto__`, `unit_cost)--`, a path-traversal dataset, an undeclared filter column) → 400/404 by
name; `limit=100000`, `offset=-5` → 422; `%`, `'; DROP TABLE …` and `SKU-000_` as search values →
0 rows and the tables intact; a form content type → 415. Bounds: 10¹⁸ and 501 lines refused; the
300,000-character identifier was **not** refused (M2).

### 4.7 Status hierarchy

Home (*Running normally · No changes recommended*), Decisions (*ZAAD found nothing worth
changing*), the Value tab (*not available — the selector kept your current plan*) and the twin's
headline (*Everything looks normal*) agree. The site chips *Risk rising* (DC) and *Recovering*
(SOUTH) are P0 stances rendered as statuses (M3). The supplier page's *none past their date* is
H7. The scope sentence ("10 of your 150 products") appears on Home, Decisions, Inventory and the
twin and agrees everywhere.

### 4.8 Accessibility

Measured, not certified: reflow 0 px at 320 CSS px on six surfaces; contrast 0 failures over 239
text nodes on the proposal page; keyboard open/close/restore on the inventory drawer; the toast
region is a polite live region; one `h1` per page. Not done: a pass with a real screen reader (none
is available in this environment) and the browser's own zoom rather than an emulated viewport.
RTL: direction and layout correct; value/unit order wrong (L5), to be fixed once in the formatters
with the V2 Arabic copy.

### 4.9 Solve scale, from the store

| products | sources | services | sites | scenarios | pipeline entries | wall seconds |
|---|---|---|---|---|---|---|
| 6 | 6 | 12 | 3 | 6 | 12–13 | 62.0, 71.2, 91.3, 92.3, 91.6, 53.3 |
| 8 | 8 | 16 | 3 | 6 | 15 | 108.0 |
| 10 | 10 | 20 | 3 | 6 | 21 | 231.9, 235.0 |
| 5 (10k workspace) | 5 | 15 | 3 | 3 | 5 | 4.2 |

Same product count, half the scenarios and a quarter of the pipeline: 4 s instead of 60–90 s. The
growth is not in the product count alone; it is in the open-order pipeline and the scenario count
that the products bring with them. Phase-level profiling (what is data build, model build, solver,
settlement) is not instrumented in V1 and is V2 work (§70).

## 5. Corrections and checkpoint

Corrective commits on `feat/zaad-operating-product-v1`, on top of the Opus head `3333b0e`:

| commit | what it closes | files |
|---|---|---|
| `5f405e2` fix(api): serve each vault from one anchor connection, checkpoint it, and let a 500 reach the browser | B1, B3, H5 | `infrastructure/db_manager.py`, `api/dependencies.py`, `api/main.py`, `api/routers/training.py`, `tests/unit/test_vault_connections.py`, `tests/integration/test_api_error_boundary.py` |
| `4c5ef80` fix(zaad/jobs): a job orphaned by a restart becomes ABANDONED, a queued one resumes, and every job says what it is for | B2, H3 (job half), L6 | `zaad/full/jobs.py`, `api/routers/zaad_full.py`, `tests/unit/test_zaad_job_lifecycle.py`, `web/src/lib/zaad/client.ts`, `web/src/lib/zaad/workspace-data.tsx` |
| `76c68a4` fix(api): evaluation is record-first, staleness is a content hash, an approval names what it was made against | H1, H2, H3, H4, H6, M1, M2, M4 | `api/product/{drafts,evaluation}.py`, `api/routers/zaad_orders.py`, `db/migrations/024_operating_product_v2.sql`, `tests/integration/test_evaluation_atomicity.py`, `tests/integration/test_operating_product_api.py`, `tests/unit/test_product_drafts_schema.py`, `web/src/lib/zaad/product.ts`, `web/src/app/orders/[id]/page.tsx` |
| `d403d3b` fix(web): a supplier's open orders say when lateness cannot be measured; PROTECT is not "Risk rising"; the reasoning link names its decision | H7, M3, M5 | `api/product/diagnostics.py`, `web/src/app/diagnostics/supplier/[id]/page.tsx`, `web/src/lib/network/model.ts`, `web/src/app/orders/page.tsx` |

**The one file under `zaad/` this pass touches is `zaad/full/jobs.py`**, and only its job
infrastructure: owner, lease, heartbeat, reconciliation, purpose. The planner is called exactly as
before; `PYTHONPATH=. python3 scripts/zaad_canonical_regression.py` on the tree after the change →
`CANONICAL REGRESSION PASS`, and again on the checkpoint (see below). No file under `zaad/full/`
other than `jobs.py`, and nothing under `zaad/meio/`, `zaad/sourcing/`, `zaad/recourse/`,
`zaad/atp/` or `zaad/commitments/`, is in the diff.

**Verified after the corrections, live on the production build and the restarted API:**

* the exported revision of FABLE-AUDIT-1 no longer reports its comparison as out of date;
* revision 2 cannot be exported and the page says why; the API answers `not_approved`;
* revision 2 was evaluated (baseline 91 s, overlay 53 s), then its quantity edited 504 → 528: the
  page said *"The comparison is out of date"* in the Decision section, Approve stayed disabled
  with a reason typed, was enabled by the acknowledgement checkbox, and the record reads *"Approved
  knowing the evaluation was out of date"* with `approval_evaluation_state = stale_acknowledged`
  and the evaluation id in the event;
* an evaluation killed mid-solve with SIGKILL and the API restarted: the baseline run reads
  `ABANDONED` with its reason, the queued overlay run was adopted by the new runner, and the
  active quota fell from 2 to 1 without anyone cancelling anything;
* two writer threads and six reader threads through the HTTP API against one vault for 20 s:
  no server error in the log;
* the supplier page reads *"no promised dates to measure against"*; the network chip reads
  *"Protecting stock"*; the imported-order drawer's "See the reasoning" opens the decision.

**Gates on the corrected tree:** `ruff` clean; `mypy` (CI's scope) *Success: no issues found in
146 source files*; every backend test touched by the pass — 152 passed; `tsc --noEmit` clean;
`npm test` 129 passed; `npm run build` green; `eslint` no errors. The whole backend suite and the
frozen regression on the checkpoint are recorded in the next section.

**Deliberately not changed in V1:** M6 (optimistic concurrency, idempotent evaluation, richer
history) and M7 (data readiness) are V2 work by design and are addressed there; L1–L5 are recorded.

**V1 AUDITED CHECKPOINT:** *recorded in the commit that follows this one* — see §6.

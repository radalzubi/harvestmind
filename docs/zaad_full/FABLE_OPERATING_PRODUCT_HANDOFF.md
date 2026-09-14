# Handoff to Fable 5.1 — ZAAD Operating Product V1

**Read this file, then [`OPERATING_PRODUCT_V1.md`](OPERATING_PRODUCT_V1.md), then the PR diff.**
Nothing else is needed to know what happened.

The work is **not merged and not deployed**. PR #81 is a draft awaiting your audit.

---

## 1. Position

| | |
|---|---|
| Starting `main` | `4a564707eb6a27fa16816e7c6e12e78b38c1e3b1` (verified) |
| Branch | `feat/zaad-operating-product-v1` |
| Pull request | [#81](https://github.com/radalzubi/harvestmind/pull/81) — **draft** |
| Head at handoff | *(see §12; recorded at the end of the session)* |
| Production runtime, unchanged | `e0fecdc`, tag `frontend-rebuild-runtime`, Fly `zaad-api` v25 |
| Working tree | clean |
| Merged or deployed | **no** |

**`zaad/` and `evidence/` are untouched.** `git diff --name-only main...HEAD | grep -E '^(zaad|evidence)/'`
returns nothing. No objective function, constraint, phase, economic assumption or frozen baseline
changed, and the frozen regression passes in CI on this branch.

## 2. What is in the diff

51 files: 32 under `web/`, 10 under `api/`, 3 tests, 2 scripts, 1 migration, 1 document,
`pyproject.toml` (one dependency), `.claude/launch.json` (a local dev entry).

| Area | Files |
|---|---|
| Application services | `api/product/{queries,catalog,diagnostics,drafts,exporting,evaluation}.py` |
| Routers | `api/routers/{zaad_workspace,zaad_orders}.py`, registered in `api/main.py` |
| Persistence | `db/migrations/023_operating_product.sql` |
| Surfaces | `web/src/app/{inventory,orders,orders/new,orders/[id],orders/formats,orders/upload,diagnostics,diagnostics/supplier/[id],upload,data,home}/page.tsx` |
| Shared frontend | `web/src/components/workspace/{Table,OrderForm,Shell}.tsx`, `web/src/lib/zaad/{product,standing}.ts` |
| Network | `web/src/lib/network/{groups,geo}.ts`, `adapters/canonical.ts`, `components/network/{IntelligencePanel,NetworkMap}.tsx` |
| QA tooling | `scripts/zaad_qa_workspaces.py`, `scripts/zaad_product_scale_bench.py` |

## 3. Requirements implemented

Against the brief's own numbering.

| § | Requirement | State |
|---|---|---|
| 6–7 | Eight destinations in three groups, each a real job | done |
| 8–9 | One status hierarchy; executive Home with an operating snapshot | done |
| 11–12 | Inventory at catalogue scale, SKU detail with contextual actions | done |
| 13–14 | Server-side paging, search, filter, sort; allowlisted names; bounded responses | done |
| 15–17 | Purchase orders, five origins, one canonical draft object, one lifecycle | done |
| 18–19 | Persistence in the operator's vault; imported data never mutated | done |
| 20–21 | Imported-order amendment in the P4B vocabulary, rights never inferred | done |
| 22–23 | Proposal evaluation: baseline + overlay through the released engine; three columns | done |
| 24 | A PO editor a buyer can use, with warnings that do not forbid | done |
| 26–29 | CSV / XLSX / print export, operator-defined profiles, template reading, export audit | done |
| 30 | Delete and edit rules by state, revisions for what is already decided | done |
| 31–38 | Diagnostics: suppliers, lateness registers, routes, product physics, value | done |
| 39–41 | Declared alternative sources surfaced on the SKU and supplier pages | done |
| 42 | Route boundary stated; ZAAD chooses no route | done |
| 43–44 | Every network object leads to a real surface | done |
| 45–47 | Multi-corridor QA fixture; crowd collapsing; readability at 8 / 30 / 100 suppliers | done |
| 48–53 | Upload before Data; a real data explorer; the source-name/row-count collision fixed | done |
| 55 | Global search, server-side | done |
| 56 | Engine connection matrix | done (table in `OPERATING_PRODUCT_V1.md` §11) |
| 59–61 | Async jobs, honest states, scoping stated and never silent | done |
| 62 | 10k and 50k fixtures, measured | done |
| 64–65 | User-created objects with actor, timestamp, version, audit; capability seam kept | done |
| 67–68 | Tables and drawers; deep links preserved | done |
| 71–73 | Honesty rules; no autonomous execution; export as the last mile | done |
| 78–80 | Responsive, RTL, accessibility | done, see §7 |
| 82–83 | Tenant safety and file-safety bounds | done |
| 84 | Migration additive and idempotent | done |
| 85 | Functional tests | done, see §5 |
| 93–95 | Documentation, branch, PR, commits | done |

## 4. Requirements **not** implemented

Stated plainly rather than left to be discovered.

1. **Bulk PO creation from several recommended purchases (§25).** The brief says to implement it
   only if the engine's output makes supplier and destination unambiguous, and not to guess where it
   does not. `report.actions` carries a `source` id, which resolves to one supplier and destination —
   but a recommendation set spanning several sources would need a grouping rule for MOQ, capacity
   and dates that the report does not supply. Not built. **Not guessed.**
2. **Transfer proposals from the network (§44).** P2 recommends where inventory should sit; there is
   no recorded-transfer workflow in the released system to write a transfer proposal into, and
   inventing one would be a new object model with no engine behind it.
3. **Supplier-specific export profiles** are stored (`zaad_export_profiles.supplier_id`) but the
   export endpoint does not yet select a profile by the draft's supplier automatically; a buyer picks
   the profile. Low risk, small gap.
4. **Column visibility on the data explorer (§50).** Columns are declared per dataset and the
   primary ones show on narrow screens; a per-user chooser is not built.
5. **Telemetry events (§92).** The semantic events are not emitted. No analytics vendor was added
   and none was wanted; the seam is the action handlers, which are all in two files.
6. **Arabic copy for the new surfaces (§79).** Direction is correct and every new surface is
   structurally usable in RTL (verified live). The new copy is English: the brief explicitly says
   not to translate it badly through ad hoc runtime strings, and `lib/i18n` is where it belongs when
   it is done properly.

## 5. Tests

| Suite | Result |
|---|---|
| `tests/integration/test_operating_product_api.py` | 36 passed |
| `tests/unit/test_product_exporting.py` | 24 passed |
| `tests/unit/test_product_evaluation.py` | 13 passed |
| `tests/unit/test_product_drafts_schema.py` | 9 passed |
| Whole integration shard (`tests/integration`) | **316 passed** |
| Whole local suite (`tests/unit` + `tests/integration`) | 2,058 passed, 2 skipped |
| Frontend (`npm test`) | **92 passed**, 31 new |
| Frontend typecheck / lint / production build | green |
| `ruff`, `mypy`, `bandit`, `pip-audit`, `gitleaks` | green |
| **zaad frozen regression** | **green** |

New frontend test files: `standing.test.ts` (12), `crowding.test.ts` (13), `abandoned.test.ts` (6),
plus tests added to `canonical.test.ts`.

## 6. Scale

Fixtures: `python3 scripts/zaad_qa_workspaces.py {corridor|scale} --db <path> [--skus N]`.
Benchmark: `python3 scripts/zaad_product_scale_bench.py <db> [<db>…]`.

| | 10,000 products / 800k rows | 50,000 products / 4.0M rows |
|---|---|---|
| slowest median query | 61 ms | **298 ms** |
| queries over the 800 ms budget | 0 | **0** |
| fixture build time | 0.9 s | 2.6 s |

Full per-query table in `OPERATING_PRODUCT_V1.md` §7.

## 7. Live QA performed

Against a running API (`HARVESTMIND_AUTH_REQUIRED=true`, `ZAAD_LEGACY_PLANNERS=0`, released jobs
path) and a **production build** of this branch, on synthetic workspaces created by the QA generator
— never against a live operator vault, and nothing was written to any production registry.

* Home (no plan / run in flight / plan ready / watch state), Decisions, Inventory (list, search,
  filters, sort, SKU drawer), Purchase orders (both tabs, imported-order panel with declared
  amendment rights), the PO editor, an **amendment against an imported order** created, approved and
  exported, an **uploaded spreadsheet** mapped and turned into a proposal, Diagnostics (suppliers,
  one supplier's lateness account, routes, product physics, value), the Data explorer with a record
  opened in full, Upload, and the Network in both Network and Map views on a three-corridor
  workspace.
* **A real proposal evaluation ran end to end**: two jobs on the released path, QUEUED → RUNNING →
  DONE, and the three-column comparison rendered from the two reports.
* **Mobile** at 375×812: the four-tab bar plus More, the reduced Inventory table, wrapped filters.
* **RTL** with `dir="rtl"`: rail, tables, drawers, buttons and forms all mirrored; horizontal
  overflow zero.
* **Every table's heading row read back out of the live DOM** rather than out of the source, and
  every column set in `web/src/` checked for a label used twice in one table. One table was showing
  two columns called "Ordered" — the date and the quantity. Both are now unambiguous.
* **Every workspace surface opened against a vault created before migration 023.** Export formats
  answered `500`. See below.

Fifteen defects were found this way and fixed; they are listed in the PR description. The three most
serious were invisible to the build and to the existing tests:

* `ensure_tables` — the fallback that prepares the product's own tables on a vault that predates
  migration 023 — split the migration file on `";"`. Migration 023 carries `COMMENT ON … IS '…;…'`
  strings and `--` comments containing semicolons, so most statements were cut in half, every half
  failed to parse, and **every failure was swallowed**. The vault was left with one of the six
  tables and a raw DuckDB catalogue error on the first visit to Purchase orders. Three of the seven
  vaults on this machine were in that state; all three carried `zaad_export_log` and nothing else,
  which is the signature. The splitter now walks the text (quoted strings and line comments do not
  end a statement), the function **verifies the six tables exist afterwards and refuses in words if
  they do not**, and `api/main.py` maps that refusal to a 422 so no order endpoint can turn it back
  into a 500. Nine unit tests in `tests/unit/test_product_drafts_schema.py` pin it. Repaired live:
  the signed-in vault was complete on the next request.

* `ZaadBuild.fits` declared `fill`; every API response has always carried `fill_mean`. Supplier
  reliability therefore never reached the Network Twin's risk scoring, the Decisions evidence line
  or the Data page — and the frontend fixture had invented the same wrong name, so the tests agreed
  with the bug. **This is a defect in the released product, not in this pass's new code.**
* The product counted open purchase orders as "ordered minus received", leaving a sliver open on
  every order a supplier had ever under-shipped: 13,889 "open" orders where 205 were open.

## 8. API, tables and migrations

* **27 new endpoints** under `/api/zaad/workspace/*` (read-only) and `/api/zaad/orders/*` (writes,
  export, evaluation). Full list in `OPERATING_PRODUCT_V1.md` §12.
* **Migration 023** — additive, nullable, idempotent. Six new tables (`zaad_draft_orders`,
  `zaad_draft_lines`, `zaad_draft_events`, `zaad_export_profiles`, `zaad_export_log`,
  `zaad_evaluations`) and two nullable columns on `stg_fmcg_skus` (`brand`, `sub_category`). No
  existing column is altered and no historical migration is rewritten. Verified against both an
  empty database and an upgraded one (`scripts/setup_db.py` runs it in every test fixture).
* `api/product/drafts.py::ensure_tables` creates the product's own tables on first use for a vault
  created before this release. It never creates or alters a staging table.
* **One dependency added**: `openpyxl>=3.1`, for XLSX export and for reading an operator's own XLSX
  import template. Nothing else in the closure changed; `pip-audit` is green.

## 9. Security review

* Every product table lives in the operator's own vault **and** carries `operator_id`, filtered on in
  every statement — two independent isolations.
* Another workspace's object is **absent**, not forbidden-with-detail: 404 with no metadata, on read,
  edit and delete. Tested.
* The data explorer's names are an allowlist; a hostile value binds as a parameter (a test asserts
  the table still exists afterwards).
* 39 bandit B608 findings, all in this pass's code, each annotated with why the statement is safe.
  `bandit -ll` is clean.
* Uploads are bounded (size, sheets, columns, rows, cell length). Workbook formulas are read as
  cached text and never evaluated.
* Every cell written to a CSV or XLSX passes through one function so a value beginning `=`, `+`, `-`
  or `@` cannot leave as a formula.
* No endpoint transmits anything. `executable: false` on every write response;
  `X-ZAAD-Transmitted: false` on every export.

## 10. Known defects and limitations at handoff

Ordered by how much they should worry you.

1. **A job orphaned by an API restart stays RUNNING for ever.** `zaad/full/jobs.py` has no reaper:
   if the process dies mid-solve, the row is never updated, and because the active quota counts
   QUEUED + RUNNING, **two orphans permanently block a workspace from planning**. Observed directly
   in this session by restarting the API mid-run. This is in the released optimizer package, which
   §86 of the brief forbids this pass from touching, so it is **not fixed here**. The product now
   detects it on the reader's side — a run that outlives the time the engine gave it is reported as
   interrupted rather than spun on for ever — but the row stays RUNNING and the quota stays spent.
   **The fix belongs in `JobStore`** (mark a row TIMEOUT when `started_at + timeout_s` has passed and
   no process owns it) and needs the frozen-regression treatment.
2. **Nothing in this pass raises the ceiling on how much can be planned at once, and the ceiling is
   low.** Three separate caps stack: `zaad.network.v2` allows at most 5,000 products in a `Request`;
   the jobs path allows 200 (`LARGE_LIMITS` in `api/routers/zaad_full.py`); and this product reads
   150 and says so on every page that shows a plan. The last of those is a product decision and
   reversible; the first two are the engine's and are not. The binding constraint is not the caps
   but the solve: a **ten-product, three-site, twelve-week run measured 3 m 52 s** on the corridor QA
   workspace (job `job_60c29e10`, 2026-09-14), and an eight-product one 1 m 48 s. So on a multi-site
   workspace the scope choices the product offers (5 / 10 / 25 / 50) are not interchangeable — the
   larger ones will approach or exceed the budget the job is given. **Record surfaces are unaffected:**
   inventory, purchase orders, diagnostics and the data explorer query the vault directly and were
   benchmarked at 50,000 products / 4.0 M rows with a slowest median query of 298 ms. The limit is on
   one optimization problem, not on the platform.
3. **An evaluation costs two of the daily job allowance** (default 24), so twelve evaluations a day.
   Stated in the 429 message; not hidden.
4. **An evaluation covers the proposal's products only.** Effects reaching other products — a
   supplier's weekly capacity shared with other orders — are outside the comparison. Every answer
   says so.
5. **A refused declaration degrades the read rather than failing it, and the degraded mode is
   silent about what it would have found.** One row in `stg_po_options` declaring a right on an
   order the planning adapter drops (`po_date >= origin`) makes the whole workspace read refuse. The
   product now retries once without `commitments` and reports the refusal verbatim, so Home,
   Decisions and the Network survive — but in that state **no open-order recommendation can be
   produced at all**, and ZAAD cannot say whether there would have been one. The banner says the
   part that is missing is missing; it cannot say how much.
6. **The evaluation-job exclusion is not atomic with submission.** `POST /orders/{id}/evaluate`
   submits the baseline run, submits the overlaid run, and only then writes the `zaad_evaluations`
   row that marks both as evaluation runs. A workspace read landing inside that window — or any
   read at all, if the insert fails after the submits succeed — sees the baseline job in
   `listPlanJobs()` and not in `evaluation_job_ids`, and will adopt it as the workspace's current
   plan. The baseline is a genuine plan, so nothing false is shown, but its scope is the proposal's
   products rather than the workspace's, and the operator did not ask for it. The window is short
   (two queue writes and a DuckDB insert) and was not observed in QA. The fix is to write the
   evaluation record first, or to carry a purpose field on the job — see item 10.
7. **Receipts that do not name a product** are attributed only when the order has one line; otherwise
   the line's received quantity is reported as unattributed, never apportioned.
8. **Sites are not placed on the map** in a multi-site workspace — the planning contract carries no
   coordinates and the operator's country would stack every site on one point.
9. **No supported delay driver** is produced: the canonical upload has no event timestamps between
   order and receipt. The five fields that would settle it are named on the page.
10. **The evaluation-run guard has two bases and neither is the job store itself.** The vault record
    is the normal answer; the overlaid run's own request is the fallback. A cleaner answer would be a
    purpose field on the job record — which is in `zaad/`, so not this pass.
11. **`npm run lint` could not be completed locally in the last hours of this session.** It ran in
    7–12 minutes earlier in the pass and passed; by the end the eslint process parked with the
    config's `globals.json` open, sleeping, and **0.94 s of CPU consumed in 3 m 24 s** — it was
    blocked, not slow. Two separate invocations behaved identically and were killed. The lint
    evidence for the final commits is therefore **CI's frontend job, not a local run**; CI has been
    green on every head of this branch. If you reproduce the hang, it is an environment problem on
    this machine and not a property of the code — `tsc --noEmit` and `next build` both complete in
    seconds on the same tree.

## 11. What is left for you

* The independent product and release audit, which is the point of this handoff.
* A judgement on §25 (bulk PO creation) and §44 (transfer proposals): both were left unbuilt rather
  than guessed. If you want them, they need a grouping rule and a transfer object respectively, and
  both are product decisions rather than implementation gaps.
* A decision on the orphaned-job defect (§10.1): it is real, it is in the frozen package, and it
  predates this work.
* Whether the Arabic copy for the new surfaces belongs in this release or the next.
* Merge and deploy, which this pass deliberately did not do.

## 12. Session record

* **CI:** run `34847967206` on `00eae63` — **13/13 green**, including the zaad frozen regression,
  bandit/pip-audit, gitleaks, the Docker build and the frontend job (typecheck, lint, test, build).
  A further run was triggered by the last commit; its result is recorded in the session's closing
  report.
* **Commits:** six, in the shape the brief suggested — application services; the operating surfaces;
  the QA-driven fixes; documentation; the security annotations; the in-flight-run fixes.
* **Working tree:** clean. **Branch:** pushed. **PR:** draft, reflecting the exact head.
* Two untracked leftovers from the superseded PR #39 (`\.github/workflows/codeql.yml`,
  `tests/unit/test_fmcg_network_block.py`) were found in the working tree at the start. They are
  outside this pass's scope, were briefly staged by accident and were removed from the commit; they
  are not in the branch. They are still absent from `main` and remain un-owned.

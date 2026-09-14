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
returns nothing, and the only file the diff touches outside `web/ api/ tests/ docs/ scripts/ db/`
is `pyproject.toml`. No objective function, constraint, phase, economic assumption or frozen
baseline changed; the frozen regression passes in CI on every head of this branch, and was also run
directly on the handoff head — `PYTHONPATH=. python3 scripts/zaad_canonical_regression.py` →
**CANONICAL REGRESSION PASS**, every P1 arm identical over 12 reviews and the P0 router_cycle cell
identical and still protection-owned.

One import crosses the line and is worth naming so it is not mistaken for something it is not:
`api/product/catalog.py` reads `ACTION_LABEL` from `zaad.commitments.contracts` to call a declared
contract option what P4B calls it. It is a read of a constant, lazily, inside one function. The
alternative was a second copy of the engine's vocabulary in the product, drifting from it.

## 2. What is in the diff

64 files: 40 under `web/`, 11 under `api/`, 5 test files, 2 scripts, 1 migration, 3 documents,
`pyproject.toml` (one dependency — `openpyxl`, nothing else), `.claude/launch.json` (a local dev
entry). `git diff --stat main...HEAD` — 12,566 insertions, 648 deletions.

| Area | Files |
|---|---|
| Application services | `api/product/{queries,catalog,diagnostics,drafts,exporting,evaluation}.py` |
| Routers | `api/routers/{zaad_workspace,zaad_orders}.py`, registered in `api/main.py` |
| Persistence | `db/migrations/023_operating_product.sql` |
| Surfaces | `web/src/app/{inventory,orders,orders/new,orders/[id],orders/formats,orders/upload,diagnostics,diagnostics/supplier/[id],upload,data,home}/page.tsx` |
| Shared frontend | `web/src/components/workspace/{Table,OrderForm,Shell,Gate,PlanState,CommandPalette}.tsx`, `web/src/components/Toast.tsx`, `web/src/lib/zaad/{product,standing,workspace-data}.ts(x)` |
| Network | `web/src/lib/network/{groups,geo,attention}.ts`, `adapters/canonical.ts`, `components/network/{IntelligencePanel,NetworkMap,NetworkGraph}.tsx` |
| QA tooling | `scripts/zaad_qa_workspaces.py`, `scripts/zaad_product_scale_bench.py` |
| Tests | `tests/integration/test_operating_product_api.py`, `tests/unit/test_product_{exporting,evaluation,drafts_schema,catalog_labels}.py` |

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
| 78–80 | Responsive, RTL, accessibility | done — with the caveat below |
| 82–83 | Tenant safety and file-safety bounds | done |
| 84 | Migration additive and idempotent | done |
| 85 | Functional tests | done, see §5 |
| 93–95 | Documentation, branch, PR, commits | done |

**The accessibility caveat.** Read "done" on §78–80 as *measured*, not *certified*. What was
checked, by driving the product rather than reading it:

* **Reflow (1.4.10)** — zero horizontal overflow on twelve surfaces at 375×812, in RTL, and in
  both, and zero again at **320 CSS px**, which is the width the criterion actually names.
* **Text spacing (1.4.12)** — the WCAG override applied live (line-height 1.5, letter-spacing
  0.12em, word-spacing 0.16em, paragraph spacing 2em): no overflow and nothing clipped but the
  `sr-only` elements, which are clipped on purpose.
* **Structure** — one `h1` per page, no skipped heading levels, no unnamed button, no image
  without `alt`.
* **Names** — every `aria-label` in the workspace free of internal identifiers. The network graph
  was announcing `Edge from sup:SUP-001 to port:aqaba`; it is not now.
* **Keyboard** — a table row opened with Enter, focus confirmed inside the drawer, Escape, and
  where focus lands afterwards; the same for the search palette; the skip link actually moving
  focus rather than only the viewport.
* **Announcement** — every confirmation now goes through a live region; none did before.
* **Contrast** — computed from the rendered DOM, every text node against its own resolved
  background, at the WCAG AA thresholds for its size and weight. **Zero failures** on Home,
  Decisions, Inventory, Purchase orders, Diagnostics and the Network. Nine rules had to move to
  reach that, including `.na` — "Not available", this product's honesty marker, which appears in
  every table and measured **2.39:1**.
* **Motion** — the three looping or entrance animations (skeleton, spinner, drawer) are already
  behind `prefers-reduced-motion`.
* **Print** — there was no print stylesheet at all, so ⌘P on any workspace page put the navigation
  rail, the sticky header, the phone tab bar and every button on paper. There is one now: it hides
  the chrome, repeats a table's header on each page, keeps a row from breaking across pages, prints
  a disclosure open and writes out link targets. The considered printable artefact is still the PDF
  export; this is for the times someone prints the screen.

**Six of those classes were broken when this session started and are fixed here.** What was *not*
done: a pass with an actual screen reader, a browser-zoom pass (reflow at 320 px is the stronger
evidence, but it is not the same criterion), and any check of the marketing site — only the
workspace was swept. Those are open, and the table above should not be read as
claiming otherwise. One residual contrast failure is left deliberately: React Flow's own
"React Flow" attribution link, at 2.85:1, which the library styles and the licence asks to keep.

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
| `tests/integration/test_operating_product_api.py` | 44 passed |
| `tests/unit/test_product_exporting.py` | 25 passed |
| `tests/unit/test_product_evaluation.py` | 26 passed |
| `tests/unit/test_product_drafts_schema.py` | 14 passed |
| `tests/unit/test_product_catalog_labels.py` | 6 passed |
| Whole integration shard (`tests/integration`) | **324 passed** |
| Whole local suite (`tests/unit` + `tests/integration`) | **2,089 passed, 2 skipped** |
| Frontend (`npm test`) | **99 passed**, 38 new |
| Frontend typecheck / production build | green |
| Frontend lint | green **in CI** — see §10.13 |
| `ruff`, `mypy`, `bandit`, `pip-audit`, `gitleaks` | green |
| **zaad frozen regression** | **green** — in CI, and run directly on the handoff head |

New frontend test files: `standing.test.ts` (12), `crowding.test.ts` (13), `abandoned.test.ts` (6),
`format.test.ts` (7), plus tests added to `canonical.test.ts`.

## 6. Scale

Fixtures: `python3 scripts/zaad_qa_workspaces.py {corridor|scale} --db <path> [--skus N]`.
Benchmark: `python3 scripts/zaad_product_scale_bench.py <db> [<db>…]`.

| | 10,000 products / 800k rows | 50,000 products / 4.0M rows |
|---|---|---|
| slowest median query | 61 ms | **298 ms** (re-measured on the final head: **305 ms**) |
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
* **The two runs' stored requests were then diffed field by field**, which is the check that
  decides whether the comparison means anything. `as_of`, `seed` (41001 on both), `horizon`, the
  product set, the sources, the locations, the services, the scenarios and the stresses are
  **identical**. The pipeline differs by exactly one entry:

  ```
  id            proposal_draft_7a91c0d8…_1
  stage         placed
  options       [ keep · fee_per_unit 0.0 · remaining_invoice_per_unit 1.05
                  · max_quantity 360.0 · provenance OPERATOR_DECLARED
                  · contract_reference draft_7a91c0d8… ]
  ```

  That is the proposal, at the buyer's own quantity and price, treated as an order that has been
  placed and may be kept. Nothing else about the two runs differs, so the difference between their
  reports is the order and nothing else. **This is the claim to re-check first if you doubt the
  evaluation**, and it is checkable from the job store without reading any application code.
* **Then every cell of a finished comparison was re-derived from the two stored reports.** For all
  **11 ledger rows**: the left column equals that report's `economics.incumbent_costs[key]`, the
  middle equals `economics.selected_costs[key]` from the same run, the right equals the proposal
  run's `incumbent_costs[key]`, and the difference column equals right minus left to within a
  floating-point epsilon. Nothing in the comparison is computed by application code. That is the
  release's central honesty claim and it is now an observation rather than a design intention.
* **The whole lifecycle again, on a second workspace, start to finish:** a proposal created from a
  product on Inventory (supplier, pack size and unit cost prefilled from the master), evaluated
  (two engine runs, eight minutes, three columns of the engine's own ledger), approved with a
  recorded reason, and **exported** — a real CSV with `X-ZAAD-Transmitted: false`, a UTF-8 BOM, and
  the filename the profile's template produces. Then a **proposed amendment** to an imported order
  carrying three declared rights, from the drawer through the editor to the rights table.
* **The record surfaces reconciled against the raw vault, arithmetic by arithmetic.** Home's
  snapshot — 150 products, 8 suppliers, 127,465 units, USD 691,835.71, 205 open orders — computed
  independently in DuckDB against `stg_fmcg_inventory`, `stg_fmcg_skus`, `stg_fmcg_purchase_orders`
  and `stg_fmcg_receipts`: **identical to the last cent**. One product's row the same way: on hand
  5,669 (the three sites at the latest snapshot), in transit 1,536, value 5,725.69 (5,669 × 1.01),
  inbound 3,312 under the planner's own open-order rule, cover 3.26 weeks (5,669 ÷ 1,737). And one
  supplier's diagnostics the same way: 1,865 matched orders, fill rate **0.95666**, p50 lead 14
  days, p90 21 days, short-fill rate **0.5056** — every figure identical to an independent
  computation over `stg_fmcg_purchase_orders` and `stg_fmcg_receipts`. What the screen says is what
  the vault holds, and it can be shown rather than asserted.
* **The spreadsheet path** end to end through the API: headings read, a mapping proposed, a wrong
  field name refused by name, and a file with one broken row read into two lines with
  `Row 4 (not-a-sku): 'abc' is not a quantity.`
* **Mobile** at 375×812, measuring `document.scrollWidth` against `clientWidth` on twelve
  surfaces — Home, Decisions, Inventory, both Purchase orders tabs, the imported-order drawer, one
  proposal, Create, Export formats, Upload, Diagnostics, a supplier's page and Data — then the
  heaviest of them in **RTL** (`dir="rtl"`, `lang="ar"`, reached through the product's own language
  switch, not by setting an attribute), then RTL at 375×812 as well. Zero horizontal overflow
  everywhere, after one fix (see below).
* **Every table's heading row read back out of the live DOM** rather than out of the source, and
  every column set in `web/src/` checked for a label used twice in one table. One table was showing
  two columns called "Ordered" — the date and the quantity. Both are now unambiguous.
* **Deep links followed, including ones that point at something gone.** Every internal `href` on
  four surfaces resolves (36 distinct paths, no 404). A link to a decision the current plan does not
  contain used to open a *different* decision under a heading reading "Selected decision" — the
  address bar naming one order and the panel showing another, which is how a colleague reads the
  wrong order's reasoning. It says so now.
* **Every page's controls listed from the DOM and checked for duplicates**, which is how the run
  control appearing twice on Decisions and "Cancel" twice on the order editor were found.
* **Screenshots taken and looked at**, not just text read back. That is also how the Value tab's
  two "Not available" rows turned out to carry their reason only in a `title` — readable by hovering
  a mouse, and by nothing else. On a panel whose whole purpose is to say why a number is missing,
  the reason is now printed under it. That is how the network panel's
  metric captions turned out to be drawn as a 22px-padded green panel: `.note` is a marketing-site
  class, both stylesheets load on a workspace page, and `.facts .note` overrode the colours without
  taking back the padding or the background. Every class the workspace uses was then checked
  against `site.css`; `.note` was the only real collision (`.exposed` and `.zfield` are scoped
  under a marketing ancestor and cannot reach a workspace page).
* **Every rendered page scanned for leaked internal tokens** (`undefined`, `NaN`, `[object Object]`,
  snake_case identifiers) — **and every `aria-label` scanned for the same thing**, which is a
  channel nothing visible would have shown. Tabbing the network graph with a screen reader
  announced React Flow's default labels: "Edge from sup:SUP-001 to port:aqaba". Every node and edge
  already carried the sentence a person would say, and now says it.
* **Contrast computed from the rendered DOM** — every text node against its own resolved
  background, at the AA threshold for its size and weight. `.na`, the "Not available" marker this
  product puts in every table to say it does not know something, measured **2.39:1**: the least
  readable text on the page was the one carrying the honesty. Nine rules moved; the sweep is now
  clean on six surfaces.
* **The keyboard path walked with the mouse untouched**: a table row focused, Enter pressed, the
  drawer opened, focus confirmed inside it, Escape pressed. That is how closing a drawer turned out
  to drop focus on `<body>` — a reader who opened the fourth product in a fifty-row table was
  returned to the top of the page. The drawer restores focus to whatever opened it, and so does
  the search palette — but only when it is dismissed; when it opens something, that page owns the
  focus and is left alone. The skip link had the same shape of problem from the other end: it moved
  the *page* to the content and left the keyboard on the link, so the next Tab went to the second
  nav item. `<main>` takes focus now.
* **The product's front door walked with a wrong token, and with the API stopped.** A refused token
  said "Connection failed: Error: Invalid API token" in a toast that was gone in three seconds —
  the word "Error:" is the language's, not ours, and a blocking failure at the front door should
  not disappear while the person is looking at the keyboard. It is a sentence now, beside the
  field, with `role="alert"`, and it stays. With the API stopped, every surface said "Your
  workspace could not be reached … your access may have been rotated" — true of a refused token,
  wrong for a dropped connection, and it sent the reader to re-enter a credential that was fine.
  The two are told apart by the message the browser already produced.
* **Every confirmation the product gives was silent to a screen reader.** "Proposal created",
  "Approved. Nothing has been sent to a supplier", "Format saved" — the toast stack had no live
  region, so an action a person could not see appeared to do nothing at all. It is a polite live
  region now, announcing only the new message, and it sits in the trailing corner in Arabic rather
  than always on the right. One leak: `de_expedite` in the declared-rights table. The route id
  `road_saudi` also appears — that one is the operator's own declared value and is left verbatim,
  because inventing a display name for it would be fabrication.
* **Every workspace surface opened against a vault created before migration 023.** Export formats
  answered `500`. See below.
* **Every refusal path on the proposal endpoint probed by hand** — a negative quantity, zero, a
  quantity that is not a number, an unknown origin, no lines, an unknown product, and a quantity of
  10¹⁸. All but the last two were already answered in words. A quantity of a quintillion was stored
  and would have reached the optimizer as a number it had to solve with; it is refused now. An
  unknown product is deliberately a **warning**, not a refusal — a buyer may order something the
  master has not caught up with — and the module docstring, which claimed it was refused, was
  corrected to match the behaviour rather than the behaviour changed to match the docstring.
* **A proposal edited after it was evaluated.** The page kept the old comparison on screen with no
  sign that the lines above it had changed — a draft stays editable and an edit does not start a
  new revision, so nothing in the record said the answer was out of date. The read now reports it
  and the page says so before the table.
* **Every write verb exercised from a browser, watching the network tab**, which is the only way
  the CORS defects below could have been found. POST, PATCH, PUT and DELETE all answer 200/204 now;
  three of them could not be sent at all before, and no exported file carried its own name.
* **All three export formats produced and opened.** The CSV read back field by field, the XLSX
  loaded with `openpyxl` and its cells checked, **and the PDF rendered and looked at** — which is
  how the last defect below was found. A file that is bytes on disk is not evidence that it is a
  document anyone can use.

**Thirty-six defects were found this way and fixed**; they are listed in the PR description. The
six most serious were invisible to the build and to the existing tests:

* **Editing a proposal, deleting one, and updating or removing an export format could not work from
  a browser at all.** The CORS allowlist in `api/main.py` said
  `allow_methods=["GET", "POST", "OPTIONS"]` — true of the API before this product, and this
  product declares PATCH, PUT and DELETE. A browser answers its own preflight for an unlisted
  method with a 400 and never sends the request, so "Save changes" failed with `net::ERR_FAILED`
  and nothing was stored. **No server-side test could have caught it**: a test client does not
  preflight, so all 43 integration tests passed against an API three of whose write paths were
  unreachable. Found by watching the network tab while clicking Save. The allowlist now names
  every method the API serves — still an allowlist, still no wildcard, still no credentials — and
  seven new tests preflight each method against the real app and check that a method the API does
  not serve is still refused.

  **The same rule broke export a second way.** Cross-origin JavaScript reads only the six "simple"
  response headers unless the server lists more, and the download helper reads the filename out of
  `Content-Disposition` — so every exported file landed as `purchase-order`, no extension, and the
  operator's own filename template was silently discarded. `X-Request-ID`, which the error copy
  tells a person to quote to support, and `X-ZAAD-Transmitted: false`, which is an assertion this
  product makes, were equally unreadable. All three are exposed now; measured from the browser
  afterwards, an export returns
  `Change_to_PO-016648_SUP-001_20260914.csv` and `x-zaad-transmitted: false`.

* **The printable order ran off the right edge of the page.** reportlab does not complain when a
  table is wider than its frame; it clips it. ZAAD's own standard format has twelve columns, and on
  A4 portrait the unit price was cut to "1.01" and the **currency column was not on the page at
  all** — on the one output a person is meant to print, sign and send to a supplier. Found by
  opening the PDF and looking at it, which no byte-count assertion would have done. A format wider
  than eight columns now prints landscape, the columns are measured at their natural width and
  scaled together to fit the frame, and cells are paragraphs so a long description wraps inside its
  column instead of being clipped. Five unit tests, one of them for a forty-column format where
  fitting the page has to win over per-column comfort.

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

* **A KEEP was reported as "no contractual right to change this order is declared."** In P4B's
  report, `contractual_basis` is the option the plan *chose*, and it is empty on every KEEP — the
  declared rights live in `amendment_windows`. The product read the first as the second, so on the
  common case, and the one where a buyer most wants to know what they may do instead, ZAAD told
  them their contract gave them nothing while the drawer one click earlier listed three rights with
  fees and deadlines. `amendment_view` now reads both, reports the eligible declared windows with
  the engine's own per-unit terms, marks the one being proposed, and distinguishes four cases in
  words. Six unit tests, one per branch.

* `ZaadBuild.fits` declared `fill`; every API response has always carried `fill_mean`. Supplier
  reliability therefore never reached the Network Twin's risk scoring, the Decisions evidence line
  or the Data page — and the frontend fixture had invented the same wrong name, so the tests agreed
  with the bug. **This is a defect in the released product, not in this pass's new code.**
* The product counted open purchase orders as "ordered minus received", leaving a sliver open on
  every order a supplier had ever under-shipped: 13,889 "open" orders where 205 were open.

## 8. API, tables and migrations

* **31 new endpoints** — 13 under `/api/zaad/workspace/*` (read-only) and 18 under
  `/api/zaad/orders/*` (writes, export, evaluation). Full list in `OPERATING_PRODUCT_V1.md` §12.
* **Migration 023** — additive, nullable, idempotent. Six new tables (`zaad_draft_orders`,
  `zaad_draft_lines`, `zaad_draft_events`, `zaad_export_profiles`, `zaad_export_log`,
  `zaad_evaluations`) and two nullable columns on `stg_fmcg_skus` (`brand`, `sub_category`). No
  existing column is altered and no historical migration is rewritten. Verified against both an
  empty database and an upgraded one (`scripts/setup_db.py` runs it in every test fixture).
* `api/product/drafts.py::ensure_tables` creates the product's own tables on first use for a vault
  created before this release. It never creates or alters a staging table, it verifies the six
  tables exist afterwards, and it refuses in words rather than letting a catalogue error reach a
  buyer. **It was broken and is the most serious defect this pass found** — see §7.
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
  `X-ZAAD-Transmitted: false` on every export — and that header is now readable from the browser,
  so the claim can be checked rather than taken on trust.
* **CORS names every method and header the API actually uses, and nothing more.** The allowlist was
  too narrow (three of this product's write paths could not be sent at all) and the exposed-header
  list was empty (the export filename could not be read). Both are corrected and covered by tests
  that preflight against the real app — including one method the API does not serve, so the tests
  fail if the allowlist ever becomes an opening. There is still no wildcard origin and
  `allow_credentials=False`.
* **Authentication is a bearer token in a header, never a cookie**, so there is no ambient authority
  for another origin to borrow. The JSON writes additionally demand `Content-Type: application/json`,
  which a cross-site form cannot send; the two multipart endpoints rely on the header auth alone.
* Hostile input probed by hand against the live API as well as in tests: `'; DROP TABLE …`,
  `%' OR '1'='1`, `../../etc/passwd`, an undeclared dataset, an undeclared sort column, a limit of
  100,000 and a negative offset. Each is refused by name or returns nothing, and the tables were
  still there afterwards.

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
   but the solve. Measured on a three-site, twelve-week QA workspace on 2026-09-14, each run to
   completion on the released jobs path:

   | products | sources | solve |
   |---|---|---|
   | 6 | 6 | **62 s** and **92 s** (the two runs of one evaluation) |
   | 8 | 8 | **108 s** |
   | 10 | 10 | **232 s** |

   Four points are not a growth law, and two runs of the same size differed by half a minute — but
   the direction is unambiguous and it is not linear: adding a quarter more products (8 → 10) more
   than doubled the solve. So the scope choices the
   product offers (5 / 10 / 25 / 50) are **not** interchangeable on a multi-site workspace: the
   larger ones will approach or exceed the budget the job is given, and the interface already says
   so beside the "all products" choice. **Record surfaces are unaffected:**
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
   evaluation record first, or to carry a purpose field on the job — see item 12.
7. **A proposed amendment is never priced outside a plan, by design, and that is a real gap in the
   product.** The declared terms are now shown — fee per unit, credit per unit, capacity, deadline,
   provenance — but ZAAD does not multiply them by the quantity affected, because the worth of a
   change is a plan-level question (what the units do instead, what the shortage costs, what the
   money is worth elsewhere) and the fee is only one term of it. A buyer who wants a number must
   have a plan that covers the order and reads its commitment block. Two consequences: an amendment
   cannot be sent through the proposal-evaluation path at all (`amendment_not_evaluated`, 422, with
   the reason), and on a KEEP the buyer sees the terms but no figure. **If you disagree with that
   boundary, this is the first place to look** — the honest alternative is a P4B-priced "what would
   this change be worth" run, which is new engine work, not a frontend change.
8. **XLSX writes numbers as text.** `cell.data_type = "s"` on every cell is what stops a value
   being re-typed as a formula or a date by whatever opens the file, which is the injection class
   §83 asks about. The cost is Excel's "number stored as text" marker on the quantity and price
   columns: the file imports correctly, and a person opening it to total a column sees the marker.
   Writing genuinely numeric fields as numbers would be safe (a float is never a formula) and is
   the obvious improvement; it was not made late in a pass, on the safety-critical path, without
   the evidence to justify it.
9. **Receipts that do not name a product** are attributed only when the order has one line; otherwise
   the line's received quantity is reported as unattributed, never apportioned.
10. **Sites are not placed on the map** in a multi-site workspace — the planning contract carries no
   coordinates and the operator's country would stack every site on one point.
11. **No supported delay driver** is produced: the canonical upload has no event timestamps between
    order and receipt. The five fields that would settle it are named on the page.
12. **The evaluation-run guard has two bases and neither is the job store itself.** The vault record
    is the normal answer; the overlaid run's own request is the fallback. A cleaner answer would be a
    purpose field on the job record — which is in `zaad/`, so not this pass.
13. **`npm run lint` could not be completed locally in the last hours of this session.** It ran in
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
* **The question this pass could not answer honestly: what is a proposed change to an existing
  order worth?** (§10.7.) The declared terms are shown; the number is not, because producing it
  means pricing the change through the engine, and P4B prices the amendment it *chooses*, not the
  one a buyer proposes. Deciding whether that number should exist — and if so, whether it is a new
  run or a new engine capability — is the largest open product question in this surface.
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

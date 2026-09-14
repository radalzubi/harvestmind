# ZAAD Operating Product V1

**What this document is.** The architecture record for the pass that turned ZAAD from four summary
surfaces into a product an importer can operate: see the business, diagnose it, inspect the
evidence, create and change proposed procurement actions, compare them against ZAAD and against
their own policy, approve them, and export them in their own format.

**What it is not.** It is not an optimizer document. `zaad/` is untouched by this work: no objective
function, no constraint, no phase, no economic assumption, and no frozen regression baseline
changed. Everything here is *application* code above a frozen engine.

Read alongside [`CURRENT_SYSTEM.md`](CURRENT_SYSTEM.md) (what is released) and
[`FRONTEND_UX_REBUILD.md`](FRONTEND_UX_REBUILD.md) (the surface this pass builds on).

---

## 1. The boundary this release keeps

> **The engine decides. The application fetches and formats.**

Three rules follow from it, and every file in `api/product/` and `web/src/lib/zaad/` is written to
them:

1. **No economics are computed outside `zaad/`.** The proposal comparison subtracts two numbers the
   engine itself reported under the same ledger key, from two runs sharing an information set. That
   is presentation. Modelling what an order would cost, or what an amendment is worth, would not be.
2. **A missing number stays missing.** `None` travels to the interface, which says "Not available"
   and, where it helps, what would make it available. No column is defaulted to zero to fill a table.
3. **Nothing executes.** ZAAD creates a document, evaluates it, records an approval and produces a
   file. It does not contact a supplier, submit an ERP order, or send anything anywhere. Every write
   response carries `executable: false`, and the export response carries `X-ZAAD-Transmitted: false`.

## 2. Navigation

Eight destinations in three groups. The group names the job, not the feature.

| Group | Destination | The question it answers |
|---|---|---|
| Operate | **Home** | What is happening and what needs me? |
| | **Decisions** | What does ZAAD recommend? |
| | **Inventory** | What do I have, what is coming, where is it, what is at risk? |
| | **Purchase orders** | What have I ordered, what should change, what should I order next? |
| Analyse | **Network** | How does my supply network connect and where is trouble propagating? |
| | **Diagnostics** | Why is performance changing, and where is the exposure? |
| Data | **Upload** | Bring information into ZAAD. |
| | **Data** | Inspect what ZAAD actually holds. |

Upload precedes Data because that is the order the work happens in; it used to be folded *inside*
Data, which put "add my files" behind a page called "inspect what I have".

On a phone the four Operate destinations are tabs and the rest sit one tap behind **More** — same
information architecture, different shape. No optimizer phase name appears anywhere in the product.

The raw engineering console stays outside primary navigation, under the workspace menu
(`/advanced/planner`).

## 3. One status ladder

`web/src/lib/zaad/standing.ts` is the only thing allowed to state how a workspace is doing:

```
1. BLOCKED   ZAAD cannot answer: a required upload is missing, or the run failed.
2. DECIDE    ZAAD has something for a person: a recommendation, or a proposal awaiting approval.
3. WATCH     Nothing to decide, but a measured condition is worth monitoring.
4. NORMAL    Neither.
```

The rungs are exclusive and ordered; a workspace at DECIDE still carries its watches, and they are
shown *underneath* the decision rather than beside it as a competing headline.

This exists because production could previously say **"Nothing ZAAD can improve right now"** beside
**"1 area needs attention"** beside a warehouse marked **Critical** whose service was projected at
100 % against a 95 % target. Every sentence was true of its own input. Two changes fix it:

* the ladder, above; and
* `web/src/lib/network/adapters/canonical.ts` no longer scores **planned protection** as risk. The
  `protect` stance is P0 holding cover where cover is justified — the system working, not a warning.
  A site's score now comes only from a measured service shortfall and a product it cannot resupply.
  Protection is still shown, as evidence, in the language of a plan working.

Pinned by `web/src/lib/zaad/__tests__/standing.test.ts` and two tests in `canonical.test.ts`.

## 4. The object model

### Proposed orders (migration 023)

One object, five ways in, one editor. There is deliberately no second code path: a product that
stores "ZAAD's orders" differently from "my orders" drifts within a month.

| `origin` | Where it comes from |
|---|---|
| `ZAAD_RECOMMENDATION` | a decision the optimizer produced |
| `CURRENT_POLICY` | the operator's own declared ordering rule |
| `MANUAL` | a buyer typing it |
| `UPLOADED_PROPOSAL` | a spreadsheet the buyer already has |
| `IMPORTED_AMENDMENT` | a proposed change to an order already in their system |

**Lifecycle.** `DRAFT → READY_FOR_REVIEW → APPROVED | REJECTED → EXPORTED`, with `SUPERSEDED` for a
revision that has been replaced.

| State | Editable | Deletable | How it changes |
|---|---|---|---|
| DRAFT | yes | yes | in place |
| READY_FOR_REVIEW | no | no | return it to draft |
| APPROVED / REJECTED / EXPORTED | no | no | a new revision that records what it supersedes |
| SUPERSEDED | no | no | — |

An approval requires a reason. An approval without one is not a decision anyone can review later.

**Tables:** `zaad_draft_orders`, `zaad_draft_lines`, `zaad_draft_events`, `zaad_export_profiles`,
`zaad_export_log`, `zaad_evaluations`. All live inside the operator's own DuckDB vault and carry
`operator_id`, which is filtered on in every statement — two independent isolations.

### Imported data is evidence

`stg_fmcg_purchase_orders` is **read-only** to this release. A change to an imported order is a
proposal *against* it (`source_po_id` + `amendment_action`), in the P4B V1 vocabulary and no other:
`KEEP`, `DEFER`, `EXPEDITE`, `REDUCE`, `CANCEL`, `SPLIT`. The original row is never rewritten,
merged or deleted by the product.

Held by `test_an_amendment_points_at_the_imported_order_and_never_edits_it`.

## 5. Proposal evaluation

Three columns, all from the engine, over one information set:

```
YOUR CURRENT PLAN        WHAT ZAAD RECOMMENDS        YOUR PROPOSAL
baseline.incumbent       baseline.selected           proposal-run.incumbent
```

* **One baseline run** of the workspace over the proposal's products. Its report carries both the
  incumbent projection and the selected plan — columns one and two from one run.
* **One proposal run** of the *same* request with the proposal overlaid on the open-order pipeline:
  the order treated as if it had been placed. Its incumbent projection is column three.

Both go through the released `POST /api/zaad/network/jobs` path, share `as_of`, seed, scenario
configuration and product set, and each evaluation therefore uses **two** of the workspace's daily
job allowance (`ZAAD_JOB_QUOTA_DAILY`, default 24; active quota 2).

**The overlay** (`api/product/evaluation.py`) attaches every line to an approved `Source` the
workspace already declares. A line with no approved source from that supplier is **refused**, with
the reason and what to do about it — never given invented terms. The overlay lives for the length of
one request object and is written nowhere.

**Scope.** The proposal's own products, plus any product carrying a declared amendment right (those
must travel together or the workspace adapter rightly refuses the build). Capped at 25; a proposal
needing more is refused with an explanation rather than silently trimmed. The scope and its
limitation are stated with every answer.

**Staleness.** A draft stays editable after it has been evaluated, and an edit does not start a new
revision, so the comparison can outlive the lines it was computed for. `GET /{id}/evaluation`
therefore reports `evaluated_at` and `stale`, and the page says so above the table rather than
presenting an engine answer about an order that is no longer on the screen. The comparison is still
shown: it is a true answer about a past state. `store_evaluation` writes the evaluation row and the
draft's `updated_at` from **one** timestamp, because two calls to `now()` would leave every
evaluation microseconds older than its own draft and therefore born stale.

**Amendments are not evaluated this way.** A change to an existing order is worth what the contract
says it is worth, so `POST /{id}/evaluate` refuses an `IMPORTED_AMENDMENT` (`amendment_not_evaluated`)
and points at the plan instead. What the page shows is the engine's own commitment block for that
order, read through `amendment_view`:

* **`contractual_basis` is the option the plan chose**, and it is empty on every KEEP. It is not a
  statement about what the contract allows. Reading it as one told a buyer their contract gave them
  nothing on the most common case.
* **`amendment_windows` is what the contract allows.** The eligible ones are reported with the
  engine's own per-unit terms — fee, credit, capacity, deadline, provenance — and the one matching
  the proposed change is marked. The built-in KEEP window is constructed from the order rather than
  declared by anyone, so it is excluded.
* Four cases are distinguished in words: no right declared; a right declared but not for this
  change; a change P4B has no option type for at all; rights declared and the plan still chose KEEP.
* **No total is produced.** The declared fee is one term of what a change is worth, not the answer,
  and multiplying it out here would be modelling. A buyer who wants the number needs a plan that
  covers the order.

## 6. Export — the last mile

```
APPROVE  →  EXPORT  →  (a person places the order)
```

Later this becomes `APPROVE → connector`; the workflow above does not change when it does.

**Export profiles** are per-workspace column mappings: heading, and either a ZAAD field from a fixed
vocabulary (`EXPORT_FIELDS` in `api/product/exporting.py`) or a constant. A profile that names a
field ZAAD does not hold is refused when it is saved, so an export can never be asked for something
that does not exist. Formats: **CSV**, **XLSX**, **printable PDF**. Date and number style, sheet
name, delimiter and filename template are per profile.

An operator can upload the template their own system already imports; ZAAD reads its **heading row
only** and proposes a mapping for a person to confirm. Nothing in the file is evaluated and no
spreadsheet is handed to a model to interpret.

**Safety.** Every cell goes through one function, `safe_cell`. A value beginning `=`, `+`, `-` or
`@` is a formula to Excel, Sheets and LibreOffice whatever wrote the file; it is prefixed so it
cannot be. Held by `test_a_formula_never_leaves_in_an_export` and the parametrised unit test.

Every export is recorded: profile, format, filename, actor, timestamp, revision. **Exporting is not
transmitting**, and the interface says so wherever a file is produced.

## 7. Inventory and scale

A distributor with ten thousand products does not browse. Inventory is a dense server-side table
with a detail panel: search, brand/category/supplier/cover filters, sortable columns, URL state.

Every figure is a column the operator uploaded or arithmetic over two of them:

* inventory value = on hand × unit cost
* weeks of cover = on hand ÷ average weekly demand over the last 12 weeks

Neither is an optimizer output and neither pretends to be. What ZAAD *recommends* lives in
Decisions, over the products the last run covered, and Inventory links to it rather than implying
the catalogue was evaluated.

**An order is open until its first receipt is recorded** — the planning adapter's own rule
(`zaad/full/workspace.py`), adopted here so the inbound units a person reads are the inbound units
the optimizer planned with. Counting "ordered minus received" instead left a permanent sliver open
on every order a supplier had ever under-shipped: on the released sample vault that was 13,889
"open" orders where 205 were open.

### Measured performance

`scripts/zaad_qa_workspaces.py` builds the fixtures; `scripts/zaad_product_scale_bench.py` measures
the endpoints' own work against them (median of three, developer laptop, DuckDB, not HTTP).

| Query | 10,000 products / 800k rows | 50,000 products / 4.0M rows |
|---|---|---|
| inventory first page | 44 ms | 108 ms |
| inventory sorted by stock value | 40 ms | 107 ms |
| inventory sorted by weeks of cover | 41 ms | 112 ms |
| inventory search | 61 ms | 298 ms |
| inventory deep page (offset 5,000) | 42 ms | 118 ms |
| one product | 46 ms | 118 ms |
| purchase orders, open | 33 ms | 153 ms |
| supplier diagnostics list | 27 ms | 73 ms |
| one supplier | 82 ms | 195 ms |
| data explorer page | 5 ms | 5 ms |
| data explorer deep page (offset 100,000) | 14 ms | 30 ms |
| global search | 13 ms | 38 ms |
| operating snapshot | 21 ms | 68 ms |

Slowest median 298 ms against an 800 ms budget; 0 queries over it.

**Platform catalogue scale and one optimization problem size are separate.** The product holds
50,000 products comfortably; a solve still covers a bounded selection, which is stated wherever a
scoped plan is shown and never silently applied.

## 8. Data explorer

An operator can read the records ZAAD holds — a row count is not evidence. The safety model is in
`api/product/queries.py` and is narrow on purpose:

* **Only names from that file reach SQL.** Dataset, column, sort column and direction are looked up
  in a declared table; anything else is a 400 before a statement is built.
* **Only values bind.** Search text and filter values are DuckDB parameters.
* **Every answer is bounded.** Page size ≤ 200; the row count is ceilinged at 100,000 and reported
  as "more than" beyond it.
* **Nothing is writable.** Writes live in `drafts.py`, which touches only the product's own tables.

Thirteen datasets are declared. A table a workspace has not uploaded is an empty dataset, not an
error.

Corrections belong in the source system and a fresh upload; the explorer is evidence, not a
workbench. Operating on the business happens in Inventory, Purchase orders, Decisions and Network.

## 9. Diagnostics

### Supplier lateness, in four separated registers

This is the discipline the page exists for:

| Register | What it is | Example |
|---|---|---|
| **OBSERVED FACT** | a count or quantile over matched orders | "Arrived after the promised date on 39 % of 148 orders that carried one." |
| **ASSOCIATION** | where lateness concentrates, labelled as such | "8 of 12 late arrivals were on QA-0007, QA-0013, QA-0031." — with *a pattern, not a cause* beside it |
| **SUPPORTED DRIVER** | only where event timestamps prove where the time went | **none in this release** |
| **UNKNOWN** | everything else, with the fields that would settle it | "ZAAD can measure the delay but cannot say where it happened." |

The canonical upload carries an order date, a promised date and a receipt date and **nothing between
them**. So the decomposition (supplier preparation / origin / ocean / port / clearance / inland) is
not attempted, and the five missing fields are named so an operator knows exactly what to add.

Everything is measured from `stg_fmcg_purchase_orders` matched to `stg_fmcg_receipts`. The legacy
HarvestMind produce tables are a different data family with different row counts and semantics;
mixing them once produced a number nobody could reconcile, so this module never reads them.

### Routes

Late arrivals grouped by the route each supplier declares — an association across suppliers, stated
as one. **ZAAD does not choose routes**: P7 route/port/mode optimisation is not released, and the
page says so.

### Product physics

Per-product supply and lead-time dispersion, declared shelf life and age at receipt, remaining life
on the stock snapshot, and demand variability — from migration 017's declared columns and the
operator's own history. Waste, spoilage and cold-chain excursions are **not** part of the canonical
upload and are listed as not measured rather than approximated.

### Value

The page most tempted to lie, so it is the most carefully worded. It reports the **modelled
difference between two plans** the optimizer produced, and names the three things it is not:

* not **realized savings** — nothing above has happened;
* not a **backtest** — no held-out replay of the operator's history is wired into this product;
* not a **percentage** — no saving rate, ROI multiple or accuracy claim is established.

The legacy `/backtest` surface (`backtesting/rolling_origin_engine`, `annual_savings_usd`,
`roi_multiple`) is the superseded HarvestMind produce engine and is deliberately not resurrected
here.

## 10. Network V2

The twin was a diagram: it told you a supplier was late and left you to find it again somewhere
else. Every selected object now leads somewhere real — supplier diagnostics, its products, its
orders, a proposed order against it; a site's stock and what is arriving; a customer's orders; a
lane's supplier and the products it carries. No control implies an action ZAAD does not take.

**Crowding** (`web/src/lib/network/groups.ts`). Two crowds collapse until opened: customers behind
one site (≥ 4) and suppliers behind one entry point (≥ 8). A collapsed group carries its **worst
member's** risk and names it, so collapsing can never hide a problem, and a supplier on two
corridors belongs to neither crowd and stays visible.

Measured in `crowding.test.ts`: at 8, 30 and 100 suppliers no two node boxes overlap and the
fit-to-view zoom stays above the legibility floor; ungrouped, 100 suppliers fit at a zoom under it —
which is why the grouping is load-bearing and the test says so.

**Corridors.** `geo.ts` gains Umm Qasr as a port and four declared corridors — `jeddah`, `dammam`,
`umm_qasr`, `iraq_overland` — alongside `aqaba` and `road_saudi`. These are published shipping paths
for a route tag an operator declares, not a routing decision: adding them lets the twin *draw* a
corridor an operator already uses.

**Map labels** move around their point (`text-variable-anchor`) before being given up, so a
supplier's name is not silently dropped in favour of a basemap city.

## 11. Engine connection

| Phase | Where it surfaces |
|---|---|
| **P0** protection / recovery | site state and stance in the Network panel; `no_replenishment` raises a site's risk; protection shown as evidence, never as alarm |
| **P1** purchasing economics | Decisions; the proposal comparison's ledger (goods, freight, ordering, receiving, carrying, financing, shortage); MOQ, case and capacity warnings in the PO editor |
| **P2** multi-echelon | multi-site Inventory and stock-by-site; transfer lanes in the twin; per-location service in the comparison |
| **Sector physics** | Diagnostics → Product physics (shelf life, age at receipt, storage state, remaining life) |
| **P3** sourcing | declared alternative sources on the SKU panel and the supplier page, with the note that ZAAD weighs cost, capacity, reliability and shared risk together rather than unit price |
| **P4** adaptive recourse | the engine's own limitations travel with every plan and every comparison ("future actions are replanning guidance") |
| **P5** ATP / allocation | customer service lines in the comparison and the twin's customer nodes |
| **P4B V1** open-PO intervention | the imported-order panel's declared amendment rights, the engine's recommended action for that order, and the amendment vocabulary the proposal editor uses |

## 12. API surface added

Read-only, `/api/zaad/workspace/*` (`api/routers/zaad_workspace.py`):

```
GET  /summary                      operating snapshot
GET  /inventory                    paged catalogue with stock position
GET  /inventory/{sku}              one product
GET  /purchase-orders              imported orders, one row per order
GET  /purchase-orders/{po_id}      one imported order and its declared rights
GET  /suppliers                    measured supplier diagnostics
GET  /suppliers/{id}               one supplier, with the lateness account
GET  /sector                       declared product physics
GET  /corridors                    lateness by declared route
GET  /datasets                     what the explorer serves
GET  /datasets/{dataset}           one page of one dataset
GET  /datasets/{d}/values/{column} the values a declared filter can take
GET  /search                       products, suppliers, orders, customers
```

Writes, `/api/zaad/orders/*` (`api/routers/zaad_orders.py`):

```
GET|POST   /                              list, create
GET|PATCH|DELETE /{id}                    read, edit, delete a draft
POST       /{id}/actions/{action}         submit | reopen | approve | reject
POST       /{id}/revise                   the next revision
POST       /{id}/evaluate                 two jobs on the released path
GET        /{id}/evaluation               state, then the comparison
GET        /{id}/amendment                the engine's block for an amended order
POST       /{id}/export                   the file
GET|POST|PUT|DELETE /profiles[/{id}]      export formats
POST       /profiles/read-template        heading row of an operator's template
POST       /read-proposal                 a proposed order from a spreadsheet
GET        /evaluation-jobs               which job ids are evaluation runs, not plans
```

**Rate limiting.** These are indexed reads a page makes on every view, so they are not on the
recommendation limiter (the precedent set by job status and `/directory`): sharing it would let a
table scroll spend the budget and answer 429 for a lookup that costs nothing. The configurable
per-IP limiter still applies, and `POST /{id}/evaluate` — which starts two solves — *is* on the
bounded limiter.

## 13. Tenant safety

* Every product table lives in the operator's own vault **and** carries `operator_id`, filtered on
  in every statement.
* A draft belonging to another workspace is **absent**, not forbidden-with-detail: 404 with no
  metadata about it, on read, edit and delete.
* Every surface requires an authenticated operator; anonymous is 401.
* The explorer's allowlist means no request string ever reaches SQL as an identifier, and a hostile
  search value binds as a parameter (held by a test that checks the table still exists afterwards).
* Uploads are bounded: file size, sheet count, column count, row count, cell length. Formulas in an
  uploaded workbook are read as cached text, never evaluated.
* **CORS names every method the API serves and nothing more.** It used to say GET/POST/OPTIONS,
  which was true of the API before this product; PATCH, PUT and DELETE are this product's, and a
  browser refuses its own preflight for a method the server has not listed — so editing a proposal,
  deleting one, and updating or removing an export format could not work at all. There is still no
  wildcard origin, no credentials, and no method the API does not serve. Preflight tests cover
  each method, including one the API does not serve, because a test client never preflights and so
  none of the other tests can see this.

## 14. What this release does not do

Stated here so nobody has to discover it:

* **No transmission.** No supplier is contacted, no ERP is written, no email is sent. Approve and
  export are the end of the loop.
* **No route optimisation.** Corridors are displayed and diagnosed, never chosen.
* **No amendment pricing without a declared right.** ZAAD never infers that an order can be
  cancelled, deferred or reduced from the fact that others were.
* **No backtest in the product.** The engineering evidence in this repository is synthetic and
  demo-scale; no customer savings claim is established by it.
* **No RBAC.** `session.tsx` keeps the capability seam (`view`, `review`, `approve`, `manageData`);
  the pilot grants all of them. Roles, teams, billing and invitations are deliberately absent.
* **Bulk creation across suppliers** is not built: grouping recommended purchases into one draft per
  supplier and destination is only safe where both are unambiguous in the report, and where they are
  not, guessing would put the wrong lines on the wrong order.

## 15. Migration 023

Additive, nullable, idempotent. Six new tables, none of them touched by the optimizer, plus two
nullable columns on the product master (`brand`, `sub_category`) that a workspace may declare and
which are shown only when present. An existing vault keeps every row it has and plans exactly as
before. `api/product/drafts.py::ensure_tables` creates the product's own tables on first use for a
vault created before this release; it never creates or alters a staging table.

That fallback is the one part of this release that a test suite alone would not have caught, so it
is worth stating how it works. The migration file is a real SQL file with `COMMENT ON … IS '…;…'`
strings and `--` comments in it, so it cannot be split on `";"` — `drafts.statements()` walks the
text and does not end a statement inside a quoted string or a line comment. Afterwards
`ensure_tables` **checks that all six tables exist** and raises `DraftRefused` naming the missing
ones if they do not; `api/main.py` answers that with a 422 carrying the message, so a vault that
cannot be prepared (a read-only file, a permissions problem) tells the buyer what is wrong instead
of producing a catalogue error. `tests/unit/test_product_drafts_schema.py` pins both halves.

## 16. Known limits

1. **Evaluation costs two jobs.** With the default daily quota of 24, a workspace can evaluate
   twelve proposals a day. Visible in the 429 message, not hidden.
2. **An evaluation covers the proposal's products only.** Interactions that reach other products —
   a supplier's weekly capacity shared with other orders — are outside the comparison, and every
   answer says so.
3. **Receipts that do not name a product** can only be attributed when the order has one line.
   Otherwise the line's received quantity is reported as unattributed rather than apportioned.
4. **Sites are not placed on the map** in a multi-site workspace: the planning contract carries no
   coordinates, and the operator's own country would stack every site on one point.
5. **No supported delay driver** is produced by this release; see §9.
6. **Bulk PO creation** and **transfer proposals** are not implemented; the first is §14, the second
   would need a recorded-transfer workflow the engine does not currently offer.
7. **A refused commitment declaration degrades the read.** One row in `stg_po_options` declaring a
   right on an order the planning adapter drops (`po_date >= origin`) makes the whole workspace read
   refuse. The product retries once without `commitments` and reports the engine's refusal verbatim,
   so the rest of the workspace survives — but in that state no open-order recommendation can be
   produced, and ZAAD cannot say whether there would have been one.
8. **The evaluation-job exclusion is not atomic with submission.** `POST /orders/{id}/evaluate`
   submits both runs and only then writes the `zaad_evaluations` row that marks them. A workspace
   read landing in that window would adopt the baseline run as the current plan — a real plan, but
   over the proposal's products rather than the workspace's, and not one the operator asked for.

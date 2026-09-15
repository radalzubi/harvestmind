# ZAAD Operating Product V2

**What this document is.** The architecture record for Operating Product V2: the pass that closes
the loop from a recommendation to an operator's action to what actually happened, and makes the
product robust enough for real pilot data. It builds on [`OPERATING_PRODUCT_V1.md`](OPERATING_PRODUCT_V1.md)
(read that first) and on the corrections of [`FABLE_V1_AUDIT.md`](FABLE_V1_AUDIT.md).

**What it is not.** Not an optimizer phase. No objective function, constraint, phase or economic
assumption under `zaad/` changes; the one file under `zaad/` this release touches is
`zaad/full/jobs.py`, and only its job infrastructure. P4B V2, P6, P7, P8, P9 and P10 are not
started. Where V2 needed the engine to express something it does not, this document says so
rather than approximating it in application code.

**Status of each section** is marked as it lands: *(designed)* until implemented, then the
section describes the tree.

---

## 1. The loop V2 closes

```
STATE → DIAGNOSIS → DECISION → ACTION → OUTCOME → LEARNING
```

V1 ended at APPROVED → EXPORTED. V2 continues: what the operator actually did outside ZAAD
(recorded by a person, never claimed by ZAAD), what happened afterwards (observed, never
attributed), and what all of it was worth, in five strictly separated registers (§8).

## 2. Runtime reliability (landed in the V1 corrective pass)

* One anchor connection per vault file for the life of the process; every request a cursor on
  it; checkpoints after DDL, at idle and on shutdown (`infrastructure/db_manager.py`).
* Job lifecycle with owner leases and heartbeats; `ABANDONED` as an explicit terminal state;
  queued work resumed after a restart; a persisted purpose and reference on every job
  (`zaad/full/jobs.py`).
* Evaluation submission record-first; staleness by content hash and workspace data version;
  approval names the evaluation it was made against (`api/product/{drafts,evaluation}.py`).

## 3. Governance

**Audit log.** One append-only table, `zaad_audit_log`, written by every user-created operational
action through one helper: actor, workspace, object type and id, action, before and after
revision, request id, timestamp, bounded context. No user-facing delete. Read through
`GET /api/zaad/audit`, tenant-scoped, paged.

**Actors and roles.** The registry keeps its one-token-per-workspace pilot model and gains
per-actor tokens carrying a name and a role: `VIEWER`, `BUYER`, `APPROVER`, `ADMIN`. A token
without actor metadata (every existing token) is the workspace's pilot administrator, so nothing
deployed changes behaviour on upgrade. `/me` returns the actor, the role and the capability set;
the interface's capability seam (`session.tsx`) reads it instead of a constant. Every write
endpoint checks a capability; no capability exists that nothing checks.

| capability | VIEWER | BUYER | APPROVER | ADMIN |
|---|---|---|---|---|
| view | ✓ | ✓ | ✓ | ✓ |
| manageData | | ✓ | | ✓ |
| createProposal, editDraft, evaluate | | ✓ | ✓ | ✓ |
| review (submit, reopen) | | ✓ | ✓ | ✓ |
| approve, reject | | | ✓ | ✓ |
| export | | ✓ | ✓ | ✓ |
| recordExternal, recordOutcome | | ✓ | ✓ | ✓ |
| manageProfiles, manageSettings, manageActors | | | | ✓ |

Landed as `api/product/governance.py` (`Actor`, `ROLE_CAPABILITIES`, `need`, `record_audit`,
`read_audit`, settings allowlist, idempotency `recall`/`remember`), per-actor tokens in
`infrastructure/operator_registry.py` (`issue_actor_token`, `list_actors`, `revoke_actor`),
`POST /admin/operators/{id}/actors`, and `api/routers/zaad_history.py` for the audit, settings and
actor routes. Tests: `tests/integration/test_operating_product_v2_governance.py`.

**Self-approval policy.** A workspace setting (`zaad_workspace_settings`, ADMIN-managed):
`self_approval = allowed | different_approver`. Default `allowed` (a pilot must not lock itself
out); under `different_approver` the creator of a draft cannot approve it (`self_approval_not_allowed`),
and the policy in force is written into the approval event.

**Concurrency.** Every draft carries an integer `version`, incremented on every write; a write
may carry `expected_version` and is refused with `409 stale_write` when the draft has moved. The
interface sends the version it read, so two people editing the same draft cannot silently
overwrite each other.

**Idempotency.** `POST …/evaluate`, `…/actions/*`, `…/export`, `…/external-status` and
`…/outcomes` accept an `Idempotency-Key` header; a replay with the same key on the same path
returns the recorded response instead of acting twice (`zaad_idempotency`, 24 h).

## 4. The closed-loop action model

Draft lifecycle after EXPORTED, all human-recorded:

```
EXPORTED → PLACED_EXTERNALLY → ACKNOWLEDGED → PARTIALLY_FULFILLED → FULFILLED
                             ↘ CANCELLED_EXTERNALLY
```

`POST /api/zaad/orders/{id}/external-status` records `{status, external_reference?, note?,
observed_at?}` with the actor and time; transitions are validated; every record is an event and
an audit row. ZAAD never sets one of these itself. The Purchase orders surface filters on them and
shows provenance (from your system / proposal / amendment) beside state.

## 5. Decision history and outcomes

A decision is a rendering of a plan report (job id + decision id); it is reproducible from the
job store. What V2 persists is the operator's response to it: `zaad_decision_responses`
(job id, decision id, target, ZAAD's verb, status `REVIEWED | ACCEPTED | OVERRIDDEN | REJECTED`,
structured reason code, free text, the draft created from it, actor, time). The Decisions surface
shows lifecycle: NEW → REVIEWED → ACCEPTED / OVERRIDDEN / REJECTED → ACTION CREATED → EXECUTED
EXTERNALLY (from the linked draft's external status) → OUTCOME AVAILABLE. The recommendation itself
is never marked "executed".

Override reason codes: `supplier_relationship`, `contract_not_represented`, `cash_constraint`,
`customer_commitment`, `promotion`, `management_decision`, `data_wrong`, `capacity_unavailable`,
`other`; optional; free text optional.

`zaad_outcomes` records observations after an action: a metric name from a fixed vocabulary
(receipt quantity, receipt date, purchase cost, fill, lead time, stockout, expedite, waste,
working capital, customer allocation), a value, when it was observed, its source (`recorded` by a
person, or `matched` from receipts that name the exported order's reference), and a note.

## 6. Provenance

Every historical decision links to: engine version, information hash, workspace data version,
as-of, seed, scenario configuration, scope, the report (job id), the approval record, the
execution state and the outcome window. The proposal page's "Where each column comes from"
disclosure gains the data version and the job ids; the Decision History surface shows the same for
each decision.

## 7. Amendment counterfactual

The question: *what would my proposed change to this existing order be worth?* V1 refused to
evaluate an amendment and showed the declared terms only. V2 evaluates the operator's amendment
as a **fixed counterfactual state** through the same engine, without touching its mathematics
(`api/product/evaluation.py::amendment_overlay`, `POST /api/zaad/orders/{id}/evaluate`):

* BASELINE — the workspace request as read: the order as it stands, with every right the contract
  declares still available to the engine (so the "What ZAAD recommends" column keeps its meaning).
* OVERLAY — the same request with the order's pipeline entry rewritten under the terms of the
  **declared** option that matches the proposed change, and KEEP-only afterwards (the right has
  been used). DEFER / EXPEDITE move `current_eta` to the option's own `due_in` period and take the
  option's invoice and payment terms; CANCEL removes the open quantity (the entry leaves the
  pipeline when nothing was received); REDUCE is a partial cancel through a declared cancel right,
  lowering `ordered`, `expected_accepted_remaining` and the keep cap proportionally.
* The contract's fee and credit for using the right are the declared per-unit terms × the units
  changed. The engine never sees them (in the overlay nobody chooses an option — the change has
  already happened), so they are stored with the evaluation (`zaad_evaluations.amendment_json`,
  migration 026) and shown as their own lines in `comparison.contract_terms`, with
  `modelled_difference` (the engine's TOTAL, proposal vs current), `fee_total`, `credit_total` and
  `net_difference` labelled *"two stated numbers added, not a model"*, basis
  `DECLARED_CONTRACT_TERMS`.

Nothing is inferred, and each refusal names its reason: no declared right of that kind; a right
whose deadline has passed or whose allowed stages exclude the order's stage; a requested receipt
date that is not one of the declared windows (the windows are listed); several windows and no date
chosen; an expedite that is not earlier or a deferral that is not later; a cancellation or
reduction beyond the declared cap (the cap is stated; a reduction inside it is suggested); a
reduction below the contractual floor; a reduction that is not one; KEEP (nothing to compare);
SPLIT (no declared option type in P4B V1 — refused with the reason, before any run is built).
Tests: `tests/unit/test_amendment_counterfactual.py` (10) and the two route tests in
`tests/integration/test_evaluation_atomicity.py`, which check that the baseline job carries the
declared right and the overlay job carries the order already changed and KEEP-only.

The order page shows the declared terms (V1's view) and, underneath, the same evaluation panel
new orders have: "Ask ZAAD to evaluate this change", the three-column ledger, and "Your contract's
terms for this change" with the fee beside the engine's difference.

## 8. Realized value

Five registers, never collapsed:

| register | what it is | where it comes from |
|---|---|---|
| MODELED DIFFERENCE | two engine runs over one information set | the evaluation comparison |
| BACKTESTED OPPORTUNITY | a held-out replay of history | **none in this product**; stated |
| OPERATOR-APPROVED EXPECTED DIFFERENCE | the modelled difference the approver saw | the comparison at `approved_evaluation_id` |
| REALIZED OUTCOME | what was observed after the action | `zaad_outcomes`, "observed after action" |
| REALIZED SAVINGS | a defensible comparator against an observed cost | only when an outcome carries both the observed figure and a stated comparator basis; otherwise absent |

The Outcomes surface says "observed after action", never "caused by ZAAD". Landed: the History
surface (`web/src/app/history/page.tsx`) shows the five registers by name, decision responses,
decided proposals with the evaluation state they were approved against, and outcomes with their
comparator basis or "no comparator — an observation only"; `GET /api/zaad/history` and
`realized_value()` classify each outcome. V2 adds a sixth stated number for amendments only —
the contract's declared fee beside the modelled difference (§7) — which is neither a model nor a
realized figure and is labelled as the operator's own term.

## 9. Location-aware inventory

`GET /api/zaad/workspace/inventory?location=<site>` (`api/product/catalog.py::inventory_page`):
every figure on the page is that site's own. Stock comes from the site's rows on the latest
snapshot date (the same rule the planning adapter reads); units on order from open orders whose
`destination_id` is that site; units coming from other sites from `stg_fmcg_transfers` rows into
the site with no `received_date` (`transfer_units`, a column only a site view has — across all
sites a transfer is a move, not an arrival); weekly demand from order lines whose `location_id`
is that site; cover from those two. A site column is only *usable* when at least one of its
values names a site with stock rows (`catalog.site_column_usable`): the staging schema defaults
`stg_fmcg_orders.location_id` and `stg_fmcg_purchase_orders.destination_id` to `'MAIN'`, so a
column that exists can still be a placeholder. When a column is not usable for one site the
figure is null and `location_notes` says why in words; the interface shows a dash carrying that
reason, never the all-sites number under a site heading. An unknown site is an empty page, not
the total. `GET /api/zaad/workspace/locations` lists the sites with their declared kind.

The Inventory page keeps the site in the URL (`?location=`), names it in the heading, the caption
and the column headers ("On hand at NORTH", "Due at NORTH", "Coming from other sites", "NORTH per
week", "Value at NORTH"), and offers the site filter only when the workspace has more than one
site. The SKU detail reconciles: `reconciliation` carries the all-sites total, the sum of the
site positions shown (older rows included, since that is what a reader adds up), the sites on the
latest snapshot, the sites whose latest row is older, and a note when they differ. Verified on
the Acme Importers workspace: SKU-0001 all sites 5,669 = DC 2,835 + NORTH 1,417 + SOUTH 1,417;
NORTH view shows 1,417 on hand, nothing due (every order is delivered to the DC), 931 per week
against 1,737 across the business. Tests: `tests/integration/test_location_inventory_and_readiness.py`.

Transfers and positioning: P2 reports transfers the *plan* would make; a Transfer draft object is
built only if the report gives origin, destination, SKU and quantity — see §10.

## 10. Transfer proposals

P2's network report carries concrete transfers — an `action: transfer` with a lane id and a
quantity, and the lane in the request names origin, destination and product — so the condition
is met and a MOVE recommendation can become a proposal. A transfer proposal is a draft with
`transfer_origin_id` (migration 027) and `destination_id`, no supplier, `kind = TRANSFER`
(`api/product/drafts.py::_prepare_draft` refuses a supplier, a missing destination, a site moving
to itself, and any amendment field). It exports through the same profiles; `origin_site` is an
export field. Bulk creation groups moves by origin and destination (`web/src/lib/zaad/bulk.ts`).
A transfer is refused an evaluation with the reason (`transfer_not_evaluated`): the released
request carries lanes the engine may use, not moves already in flight, so a manual transfer cannot
be re-planned on its own without inventing an object the contract does not have; the order page
points at the decision that priced it. A move whose lane is not in the current request is listed
as not creatable, never guessed.

## 11. Data readiness and quality

`GET /api/zaad/workspace/readiness` (`api/product/readiness.py`), counted from the vault and
labelled `COUNTED_FROM_THE_VAULT`: per source — the fields ZAAD reads with required/optional,
present, coverage (share of rows with a value), validity (share of values that pass the kind's
check: non-negative number, plausible date, non-blank text), which capabilities each field feeds;
plus row count, date range and last upload. A capability matrix over fourteen capabilities
(PURCHASING, INVENTORY_VALUE, SUPPLIER_LATENESS, SUPPLIER_ROOT_CAUSE, PERISHABILITY,
OPEN_PO_INTERVENTION, MULTI_SITE, ALTERNATIVE_SOURCING, CUSTOMER_ALLOCATION, SERVICE_HISTORY,
SHORTAGE_ECONOMICS, NETWORK, REALIZED_VALUE, WASTE), each `READY | PARTIAL | BLOCKED |
UNAVAILABLE` with the source and column that decides it and the coverage that decided it.
`BLOCKED` names a column the canonical upload could carry; `UNAVAILABLE` means nothing the upload
carries could answer it (where a delay happened needs dispatch, vessel, port and customs
timestamps; waste needs write-off adjustments) and the reason says which fields are missing from
the upload itself. Quality checks — duplicate products and order lines, orders and stock for
unknown products, unknown suppliers, negative quantities and costs, extreme quantities, promised
before ordered, received before ordered, unmatched receipts, shipped above ordered, mixed
currencies — each `BLOCKING | MATERIAL | INFORMATIONAL` by whether ZAAD cannot plan, plans
differently, or merely notices, with the source and column.

Surfaced on Upload ("What ZAAD can do with this data", and the status line now derives its
sentence from the same counted answer instead of saying "nothing needs your attention" above a
table of blocked capabilities), on Data (the matrix, per-source field completeness, quality
checks) and on Home (one line under "Your data" when anything is blocked or partial, naming the
first gap). On the Acme workspace this reads: 6 ready, 1 partial, 5 blocked, 2 not in the upload
— supplier lateness blocked by `expected_delivery_date` missing on every purchase order, which is
the fact V1's diagnostics reported three ways and V1's readiness never did.

## 12. Bulk proposal creation

`POST /api/zaad/orders/bulk` takes `{"drafts": [...]}` (at most 50, same shape as a single
create) and creates all of them in one transaction or none (`drafts.create_drafts`: every
proposal is checked before any is written; a refused one names itself and "Nothing was
created."). It needs `createProposal`, honours `Idempotency-Key`, and every proposal carries
`batch` in its audit context. The client's grouping is deterministic and pure
(`web/src/lib/zaad/bulk.ts`, tested): one proposal per supplier and destination for purchases,
one per origin and destination for transfers; groups ordered by supplier, origin, destination;
lines by product; the same product twice in a group is one line with the quantities summed and
the decision ids recorded. What cannot become a line without guessing — a HOLD, an amendment, a
source or lane not in the request — is listed on the review sheet with the reason and never
created. Decisions shows checkboxes on purchase and transfer recommendations for anyone with
`createProposal`, a "Review and create" sheet with the exact groups, and a single "Create N drafts
— all or none" button; the created drafts start as DRAFT. The new-order form now prefills its
lines from `?decision=` through the same rule (its header comment claimed it did in V1; it set
only the provenance).

## 13. Exports and the integration seam

Declared-numeric fields (`exporting.NUMERIC_FIELDS`: quantity, units per case, cases, unit
price, line value, line number, revision) are written as numeric xlsx cells with an Excel number
format from the profile's `number_format`; every other cell, including any constant column, stays
text through `safe_cell` and is typed as a string. CSV is unchanged. A profile can be scoped to a
supplier and marked `is_default`; the formats page shows "Workspace default" / "Default for
SUP-x", and the export line on an order says which rule chose the format (chosen → supplier
default → workspace default → ZAAD standard). The outbound seam is unchanged from the V1
corrective pass: `FileExportAdapter` is the one real adapter; `TestConnector` is labelled test;
nothing is named after an ERP it does not integrate with. `X-ZAAD-Transmitted: false` on every
export.

## 14. Telemetry

`POST /api/zaad/telemetry` accepts only allowlisted event names (`zaad_history.TELEMETRY_EVENTS`,
now including `bulk_created` and `inventory_opened`) and allowlisted property keys (ids,
surface, tab, node, kind, count, locale); anything else is dropped and counted. Page opens are
recorded on Home, Inventory (with the site), the SKU panel, Upload/Data readiness, Diagnostics
(with the tab), the supplier page, the network panel (object id and kind), History, and on the
actions already covered in V1. No record contents, prices, customer names or supplier secrets
travel: an id and a surface name at most.

## 15. Arabic and bidi

The workspace chrome reads its labels from `web/src/lib/i18n` (`workspace.groups`,
`workspace.nav`, search, help, skip link, footer) with a locale toggle in the rail; the provider
already sets `lang` and `dir` on the document. Figures are bidi-isolated in RTL by CSS
(`globals.css`: numeric table cells, definition values, chips, fact values, `.fig`, `code`, `kbd`
get `unicode-bidi: isolate; direction: ltr`), so "27 d lead" and "USD 1,794" keep their order in
an Arabic page without invisible isolate characters in every formatter. Page copy inside the
workspace surfaces remains English in this release; the chrome, direction and figures are the V2
scope, and the limit is recorded in §17.

## 16. Solve orchestration

Profiled from outside the engine with `scripts/v2_solve_profile.py` (cProfile around the released
`plan_network`; nothing under `zaad/` instrumented or changed). Fixture workspace, 10 products,
sourcing and commitments on, `max_solve_seconds=15`, one solver thread:

| stage | wall time | share |
|---|---|---|
| data build (`build_network_request`) | 0.22 s | 0.1 % |
| model build (`model.matrix`, `var`, `row`) | ~1.7 s | 0.8 % |
| solver (`scipy.optimize._highspy._core.run`, 50 MILP runs over 30 candidate solves) | 211.4 s | 95.8 % |
| settlement, forecast draws, serialisation | < 1 s | < 0.5 % |
| **total `plan_network`** | **220.7 s** | |

The time is the solver's, not the product's: 96 % of the wall clock is inside HiGHS, and the
candidate ladder runs the MILP fifty times for one plan (thirty candidate solves, some with
several worlds). The coupling graph over the request gives 8 components across the 10 products
(two pairs share a supplier capacity resource; the rest are singletons) — *decomposable in the
graph* — but the request also carries a global tie (a site's storage capacity is shared by every
product held there, and opening cash / financing spans every product), so solving the components
separately is **not the same problem** and no decomposition is shipped. `decomposition_equivalent:
false` is the script's own verdict, and it is the honest one. What V2 ships instead is the
statement of scope: the scope notice reads the request's couplings (`web/src/lib/zaad/scope.ts`,
tested) and says *catalogue / evaluated / solved together as one problem*, so a reader knows the
ten products were planned jointly and why. A faster plan for this workspace is solver time
(threads, the candidate ladder, the time cap), which is engine work under `zaad/` and outside
this release's remit; the numbers above are the baseline for it. On this fixture the engine
returned ABSTAIN (the incumbent and most network candidates infeasible under the declared
commitments, `base_stock` optimal) — a property of the fixture's commitments, reported as such.

## 17. Known limits

Recorded as they are established, from the V2 build and its audit (`FABLE_V2_RELEASE_AUDIT.md`).

1. **Amendments: only declared rights, only P4B V1's vocabulary.** DEFER, EXPEDITE, CANCEL and
   REDUCE (as a partial cancel) are evaluable against a declared option; SPLIT is refused; a
   requested date must be one of the declared windows. The contract fee is added to the engine's
   difference as two stated numbers, never modelled.
2. **Transfers are proposals, not re-planned moves.** A transfer proposal exports and is tracked
   like a purchase, but cannot be evaluated on its own: the request carries lanes, not moves in
   flight. The move's economics are those of the plan that recommended it.
3. **Solve time is the solver's.** 96 % of a 10-product plan's wall clock is inside HiGHS; no
   decomposition is shipped because the request carries global ties (site capacity, cash) that
   make separate solves a different problem. The scope notice states the joint-problem structure
   instead.
4. **Readiness describes the commercial upload.** A fresh-produce workspace is told so and shown
   no capability rows; produce readiness stays with the produce diagnostics.
5. **Site columns that only carry the schema default.** `location_id` / `destination_id`
   default to `'MAIN'`; a site view treats such a column as undeclared and says so. A workspace
   whose real site is literally named MAIN with stock rows under it is read correctly (the rule
   is "names a site with stock rows"), but a workspace mixing placeholder and real values will
   see the placeholder rows counted as a site called MAIN.
6. **Arabic covers the chrome, direction and figures, not page copy.** Workspace pages remain
   English; the copy module carries the workspace navigation, search, help and footer in both
   languages, and figures are bidi-isolated by CSS.
7. **Realized outcomes are recorded or matched, never attributed.** Receipts matched to an
   exported order's reference populate a REALIZED OUTCOME; "realized savings" appears only when
   an observation carries its comparator and basis. No backtested opportunity exists in this
   product.
8. **Bulk creation is all-or-none within one workspace call, at most 50 proposals.** A larger
   selection is refused with the count.
9. **The live QA workspaces produced no purchase or move recommendation in their current plans**
   (both retained the incumbent), so the bulk-creation checkboxes and review sheet were verified
   by their unit tests and the endpoint's integration tests, and by their absence on a plan with
   only KEEP decisions; they were not exercised end to end in a browser in this release.
10. **Telemetry carries ids and surface names only.** No record contents; unknown event names and
    keys are dropped and counted.

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

## 3. Governance *(designed)*

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
| manageProfiles, manageSettings | | | | ✓ |

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

## 4. The closed-loop action model *(designed)*

Draft lifecycle after EXPORTED, all human-recorded:

```
EXPORTED → PLACED_EXTERNALLY → ACKNOWLEDGED → PARTIALLY_FULFILLED → FULFILLED
                             ↘ CANCELLED_EXTERNALLY
```

`POST /api/zaad/orders/{id}/external-status` records `{status, external_reference?, note?,
observed_at?}` with the actor and time; transitions are validated; every record is an event and
an audit row. ZAAD never sets one of these itself. The Purchase orders surface filters on them and
shows provenance (from your system / proposal / amendment) beside state.

## 5. Decision history and outcomes *(designed)*

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

## 6. Provenance *(designed)*

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

## 8. Realized value *(designed)*

Five registers, never collapsed:

| register | what it is | where it comes from |
|---|---|---|
| MODELED DIFFERENCE | two engine runs over one information set | the evaluation comparison |
| BACKTESTED OPPORTUNITY | a held-out replay of history | **none in this product**; stated |
| OPERATOR-APPROVED EXPECTED DIFFERENCE | the modelled difference the approver saw | the comparison at `approved_evaluation_id` |
| REALIZED OUTCOME | what was observed after the action | `zaad_outcomes`, "observed after action" |
| REALIZED SAVINGS | a defensible comparator against an observed cost | only when an outcome carries both the observed figure and a stated comparator basis; otherwise absent |

The Outcomes surface says "observed after action", never "caused by ZAAD".

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

## 10. Transfer proposals *(designed, conditional)*

Built only if P2's network report carries concrete `transfers` with origin, destination, SKU and
quantity. Otherwise recorded here as not expressible.

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

## 12. Bulk purchase creation *(designed)*

Select recommendations → ZAAD proposes groupings on deterministic dimensions only (supplier,
destination, currency, compatible order dates) → the buyer reviews → one canonical draft per
group. A recommendation whose supplier or destination the report does not state is listed as
"needs a choice" and is not grouped. MOQ, case, pack and capacity warnings come from the master
and are labelled hard / economic / unknown.

## 13. Exports and the integration seam *(designed)*

Profile selection: explicit choice → the supplier's default profile → the workspace default →
ask. The page shows which will be used before the button is pressed. XLSX: fields declared
numeric are numeric cells; everything else is text through `safe_cell`. An outbound adapter
interface (`validate`, `preview`, `submit`, `get_status`) with one real adapter (file export) and
one labelled mock; an inbound seam over the existing upload path. No connector named for a system
it does not integrate with.

## 14. Telemetry *(designed)*

`POST /api/zaad/telemetry`: an allowlisted event name and allowlisted identifier keys only;
stored in the vault; no line contents, names, prices or records.

## 15. Arabic and bidi *(designed)*

Workspace chrome and operational labels through the existing dictionary (`lib/i18n`); one set
of formatters isolates a value and its unit with Unicode bidi isolates so `27 d` and `USD 5,726`
read correctly under `dir="rtl"`; raw codes stay untranslated.

## 16. Solve orchestration *(designed)*

Profiled from outside the engine (no instrumentation inside `zaad/`): data build, model build,
solver, settlement and serialisation as wall-clock shares. A coupling graph over the request
(shared supplier capacity, MOV, shared inventory and lanes, shared customer allocation, shared
capital) reports catalogue size / evaluated scope / joint solve size. Decomposition is shipped
only where monolithic and decomposed results are equal within tolerance; otherwise it is not.

## 17. Known limits

Recorded as they are established.

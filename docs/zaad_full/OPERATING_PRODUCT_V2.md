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

## 7. Amendment counterfactual *(designed)*

The question: *what would my proposed change to this existing order be worth?* V1 showed the
declared terms and priced only what P4B itself chose. V2 evaluates the operator's amendment as a
**fixed counterfactual state**, through the same engine, without touching its mathematics:

* CURRENT OPEN-PO STATE — the workspace request as read (baseline run, incumbent projection).
* FIXED OPERATOR-PROPOSED AMENDMENT OVERLAY — the same request with the amended order's pipeline
  entry rewritten as if the amendment had already been exercised: DEFER moves `current_eta` to the
  declared option's `due_in` period; EXPEDITE moves it earlier likewise; REDUCE lowers `ordered`
  and `expected_accepted_remaining`; CANCEL removes the remaining quantity. The entry's options
  become KEEP-only (the right has been used). The declared per-unit fee or credit for that option,
  which the engine books as `<action>_fee` / `commitment_credit` when *it* chooses the option, is
  reported as its own line — *"Contract fee: the declared USD x per unit × the units changed, your
  contract's term, not a model"* — beside the engine's counterfactual ledger, and the two are
  summed under a label that says both were added. Nothing is inferred: an amendment with no
  declared eligible right is refused, as in V1.

Only the options P4B V1 declares are expressible: KEEP, DEFER (`de_expedite` / `reschedule`),
EXPEDITE, CANCEL. REDUCE and SPLIT have no declared option type in P4B V1; a REDUCE overlay is
expressible as a quantity change with no fee term (and says so); SPLIT is not expressible and is
refused with the reason.

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

## 9. Location-aware inventory *(designed)*

`GET /inventory?location=<site>`: stock from that site's latest snapshot rows; inbound from open
orders whose `destination_id` is that site (absent when orders carry no destination — stated);
weekly demand from order lines with that `location_id` (absent when orders carry no site —
stated, and cover with it). The table header names the site; the URL keeps it; the SKU detail
reconciles the all-site total with the sum of site positions and says when they differ.
Transfers and positioning: P2 reports transfers the *plan* would make; a Transfer draft object is
built only if the report gives origin, destination, SKU and quantity — see §10.

## 10. Transfer proposals *(designed, conditional)*

Built only if P2's network report carries concrete `transfers` with origin, destination, SKU and
quantity. Otherwise recorded here as not expressible.

## 11. Data readiness and quality *(designed)*

`GET /api/zaad/workspace/readiness`: per source — required and optional fields, present fields,
coverage % per important field, validity %, date range, row count, last upload; and a
capability matrix computed from them (PURCHASING, SUPPLIER_LATENESS, SUPPLIER_ROOT_CAUSE,
PERISHABILITY, OPEN_PO_INTERVENTION, MULTI_SITE, ALTERNATIVE_SOURCING, CUSTOMER_ALLOCATION,
REALIZED_VALUE) each `READY | PARTIAL | BLOCKED | UNAVAILABLE` with the field that decides it.
Quality checks: duplicates, orphan keys, impossible dates, negative quantities, extremes, unknown
products and suppliers, unmatched receipts; each `BLOCKING | MATERIAL | INFORMATIONAL`. Surfaced
on Upload (with the path: which source, which column) and on Data; Home carries one line when
something is BLOCKED.

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

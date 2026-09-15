# Fable 5.1 — release audit of ZAAD Operating Product V1 + V2

**Auditor and release owner:** Claude Fable 5.1. **Date:** 2026-09-15.
**Subject:** PR #81, branch `feat/zaad-operating-product-v1`, from the V1 audited checkpoint
`77b7185b24417d9c3976f4b802320475660c2934` (13/13 CI jobs green, `FABLE_V1_AUDIT.md`) through the
V2 commits listed in §3.

**Overall verdict: see §7.** This document records what V2 built, what was reproduced live,
what was attacked, what every gate returned, and what is deliberately not claimed. Nothing in it
is taken from a handoff: the V1 checkpoint was audited by reproducing it, and every V2 claim
below names the test or the live walk that backs it.

---

## 1. Scope delivered against §114 of the brief

| required item | status | where |
|---|---|---|
| job orphan recovery | done in the V1 corrective pass | `zaad/full/jobs.py`, `tests/unit/test_zaad_job_lifecycle.py` |
| evaluation job purpose / contamination fix | done in the V1 corrective pass | `PROPOSAL_BASELINE` / `PROPOSAL_OVERLAY`, `GET /jobs?purpose=` |
| location-aware inventory | **done** | `catalog.inventory_page(location=)`, `/locations`, SKU reconciliation — `OPERATING_PRODUCT_V2.md` §9 |
| capability-based data readiness | **done** | `api/product/readiness.py`, `/workspace/readiness` — §11 |
| decision / action history | done (governance pass) + lifecycle chips on cards | `zaad_decision_responses`, History surface — §5 |
| external-action status tracking | done (governance pass) + shown on the network panel | `external-status`, `EXTERNAL_TRANSITIONS` — §4 |
| realized-value framework | done (governance pass) | five registers, `realized_value()` — §8 |
| audit log | done (governance pass) | `zaad_audit_log`, `/api/zaad/audit` — §3 |
| roles / capabilities enforcement | done (governance pass) | `ROLE_CAPABILITIES`, `need()` — §3 |
| supplier profile export selection | done (governance pass) + formats page default / per-supplier UI | `profile_choice()`, `is_default` — §13 |
| numeric XLSX safety | **done** | `NUMERIC_FIELDS`, `build_cells`, `to_xlsx` — §13 |
| V2 browser QA | **done** over two workspaces (§4) with one recorded gap (§17.9 of the record) | |
| V2 release docs | this document; `OPERATING_PRODUCT_V2.md` rewritten from *(designed)* to landed; `OPERATING_PRODUCT_V1.md` corrected in the V1 pass | |
| user-proposed amendment valuation (attempt required) | **done, not blocked** — a fixed counterfactual under declared terms; SPLIT refused | §7, `tests/unit/test_amendment_counterfactual.py` |
| bulk PO creation (attempt required) | **done** — all-or-none endpoint, deterministic client grouping | §12 |
| transfer proposal (conditional on a concrete P2 move) | **done** — P2 emits concrete moves, so transfer proposals exist | §10 |

Also delivered: Arabic chrome and bidi-isolated figures (§15), the external solve profile and
the joint-problem scope statement (§16), executed actions on the network panel, supplier
diagnostics → decisions, proposals in global search, Data column visibility, telemetry on page
opens (§14).

## 2. Constraints honoured

* **Optimizer mathematics untouched.** `git diff --stat 77b7185..HEAD -- zaad/` is empty: no
  file under `zaad/` changed after the V1 checkpoint. The amendment counterfactual rewrites the
  *request* (`api/product/evaluation.py`) and runs the released planner unchanged; the profiler
  instruments from outside. The frozen canonical regression therefore stands at the checkpoint's
  result (`CANONICAL REGRESSION PASS`, `FABLE_V1_AUDIT.md` §6) and was not re-run for V2, which
  is the honest statement of what the gate covers.
* **Validation7 / Validation8 / holdout4 not accessed.** No script or test in the diff names them.
* **No P4B/P6–P10 phase started.** No new port, carrier, mode or route object exists; a transfer
  proposal names a lane the request already carries.
* **No fake integrations.** `FileExportAdapter` remains the one real adapter; the test connector
  is labelled test; nothing is named after an ERP.
* **ZAAD does not send orders.** Every export carries `X-ZAAD-Transmitted: false`; external
  status is human-recorded; a transfer is a proposal someone exports.
* **Realized value.** "Observed after action" wording kept; the amendment fee is labelled the
  operator's own contract term and "two stated numbers added, not a model".
* **Audit append-only; telemetry allowlisted; no secrets or record contents logged.**
* **Fail closed.** Amendment refusals name their reason before any run is built; a transfer is
  refused an evaluation; an unknown site is an empty page; an undeclared site column is null with
  a note; a produce workspace gets no commercial capability rows.
* **Migrations additive and idempotent:** 026 (`amendment_json`) and 027 (`transfer_origin_id`),
  both `ADD COLUMN IF NOT EXISTS`, applied lazily by `ensure_tables` and checkpointed. No
  historical migration rewritten.
* **No test deleted.** Tests added: 13 (location/readiness) + 5 (exporting) + 2 (bulk) + 10
  (amendment unit) + 2 (amendment route) + 1 (readiness family) + 3 (transfers) backend;
  bulk (4), scope (5) frontend.

## 3. Commits since the V1 checkpoint

| commit | what it carries |
|---|---|
| `560066a` | location-aware inventory, capability readiness, numeric xlsx cells, bulk proposals |
| `c2ce9f4` | amendment evaluated as a fixed counterfactual under its declared terms (migration 026) |
| `<web surfaces>` | Arabic chrome, executed actions, lifecycle chips, telemetry, formats defaults, Data columns, search |
| `<scope>` | joint-problem scope sentence; external solve profiler |
| `69325b3` | transfer proposals (migration 027) |
| `<record>` | scope fix; V2 record sections 10, 12–16 |
| `<family>` | readiness names its upload family; silent on a produce workspace |
| `d012ce0` | uncoupled products said to be separable |
| *(this document's commit)* | release audit; V2 record §3–§8 landed, §17 known limits |

(Short hashes for the middle rows are in `git log 77b7185..HEAD --oneline`; they are not
repeated here to avoid a stale copy.)

## 4. What was walked live

Two workspaces, one API (`python -m uvicorn`, guarded entry point), one production build of the
web app served by `next start`, browser sessions signed in through the pilot key page.

**Acme Importers** (`op_eb4f2c4f`, 150 products, sites DC / NORTH / SOUTH, 18 declared amendment
options on six open orders):

* Inventory at NORTH: heading *"Stock at NORTH (branch) only"*; SKU-0001 shows 1,417 on hand at
  NORTH against 5,669 across all sites, nothing due at NORTH (every purchase order is delivered to
  the DC — a dash with that reason, not the DC's 3,312), 931 per week at NORTH against 1,737 across
  the business, cover 1.5 weeks from those two figures. The SKU drawer reconciles: *"The sites add
  up to the 5,669 units on hand above, all counted on 22 Dec 2025."*
* Readiness (Upload, Data, Home): 6 ready, 1 partial, 5 blocked, 2 not in the upload; supplier
  lateness BLOCKED by `expected_delivery_date` missing on every purchase order — the fact V1's
  diagnostics stated and V1's readiness never did. The Upload status line now derives from the same
  counted answer. Field completeness per source and quality checks on Data.
* Amendment counterfactual, end to end: a DEFER of PO-016648 (1,776 units, declared right
  *Master supply agreement §7.2*, fee 0.20/unit) evaluated through two real solves. Baseline job
  carried the declared right; overlay job carried the order deferred and KEEP-only (checked in the
  job store). Result on the page: modelled difference **−USD 6.90** (financing, the engine's own
  ledger, fee excluded), declared fee **USD 355.20** (0.20 × 1,776, "from your contract, not a
  model"), together **USD 348.30** with the stated basis. Arrival 6 Jan → 19 Jan 2026.
* SPLIT amendment: refused `amendment_not_evaluated` with the reason, no job submitted.
* Decisions: the approver's earlier response shows as an *Accepted* chip on PO-016648's card;
  scope line reads *Catalogue 150 · evaluated 10 …*. No purchase or move recommendation in the
  current plan, so no bulk checkbox is offered (correct).
* Purchase orders list: the amendment draft appears with provenance *Change to an existing order*.
* Formats: *New format* opens the editor with *For one supplier only* and the default toggle.
* Data: *Columns* chooser on a wide dataset; hidden columns remembered per dataset.
* Network, SUP-001: *What has been done* lists proposals with state and recorded external status.
* Diagnostics, SUP-001: *What ZAAD decided about this supplier* (none in this plan, with the
  honest sentence and a link to its open orders).
* Arabic: toggle → `dir=rtl`, `lang=ar`, navigation in Arabic, numeric cells `direction: ltr`
  (1,417 reads as 1,417); toggle back → `ltr en`.

**Fable Fixture Network** (`op_857568fd`, created for this audit from the network fixture with
a promised date on half the history; 8-product plan run through the API, `RETAIN_INCUMBENT`):

* Home: readiness line *"5 of 12 things ZAAD can do fully available, 3 partly, 4 not yet. First
  gap: shelf life…"*; scope line *evaluated 8 · none of them share supplier capacity or order
  terms; … each could be planned on its own*.
* Inventory at SOUTH with the SKU-0003 drawer: DC 867 + NORTH 434 + SOUTH 434 = 1,734, reconciled.
* Supplier SUP-001: lateness measured on the 948 orders that carry a promised date (23 % late),
  the rest excluded and said so; readiness reports lateness PARTIAL at 50 %.
* Found and fixed during this walk: the new operator defaulted to the *produce* sector, and the
  Upload page showed produce sources missing above a commercial capability matrix saying Ready —
  two answers on one screen. The readiness endpoint now names its upload family and returns no
  capability rows for a produce workspace (`<family>` commit, tested).

## 5. Adversarial checks (brief §102)

| attack | result |
|---|---|
| bulk create as VIEWER | 403 `forbidden` (test); as APPROVER 201 — APPROVER holds `createProposal` by the V1 role table, by design |
| bulk with one refused line among good ones | 422, *"… Nothing was created."*, count unchanged (test) |
| bulk replay with the same `Idempotency-Key` | `Idempotent-Replay: true`, no second batch (test); 51 proposals → 422 |
| site name shaped as SQL (`NORTH' OR '1'='1`) | bound as a literal: empty site page, every figure null |
| site name over 200 characters | 422 at the route |
| no token / bad token on readiness and bulk | 401 / 401 |
| amendment with no declared right; expired right; right barred by stage; date outside the declared windows; cancel beyond the cap; reduction below the floor; KEEP; SPLIT | each refused with its reason before any run (10 unit tests + 2 route tests) |
| transfer with a supplier; without a destination; to itself; as an amendment | each refused with its reason (parametrised test) |
| evaluate a transfer | 422 `transfer_not_evaluated`, pointing at the plan that priced it |
| produce workspace asks for readiness | `applies: false` with the note; no capability rows |
| stale site row in a SKU's positions | reconciliation says which site and that the total omits it (test) |

## 6. Gates on the release tree

| gate | result |
|---|---|
| whole backend suite, `python3 -m pytest tests -q -x -p no:cacheprovider` on `d012ce0` | **2,188 passed, 2 skipped** in 439 s — 2,134 at the V1 checkpoint, 54 added, none removed |
| frozen canonical regression | stands at the V1 checkpoint result (`CANONICAL REGRESSION PASS`); no `zaad/` file changed since |
| `ruff check api tests` | clean |
| `mypy` at CI's scope (`optimization risk backtesting api ingestion domain adaptive zaad/full --ignore-missing-imports`) | Success on the touched modules; CI's run on the pushed head is the one that counts (§7) |
| `bandit -ll` over `api infrastructure zaad/full` | no issues, exit 0 |
| `pip-audit` as CI runs it | no vulnerability reported; the local package itself is "not on PyPI" (expected) |
| `gitleaks` | not installed locally; CI's secret-scan job runs on the pushed head |
| frontend `tsc --noEmit` | clean |
| frontend `npm test` | 138 passed (129 at V1 + bulk 4 + scope 5) |
| frontend `eslint src` | 0 errors (56 pre-existing warnings) |
| frontend `npm run build` | green on every commit walked; the served build is the final one |
| docker image | built by CI on the pushed head |
| exact-head CI | **PENDING — recorded in §7** |

## 7. Release decision

*Written after CI on the exact head.*

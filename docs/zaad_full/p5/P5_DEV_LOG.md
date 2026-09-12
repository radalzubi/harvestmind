# P5 development log (parallel phase, TRACK B)

Branch `claude/zaad-atp-p5`, worktree `harvestmind-p5`, base `main` `adf45e4` (runtime `8c813ac`).
TRACK A (P4 performance closure) owns `zaad/full/model.py`, the P4 node indexing, the P3 shared-order
rows and the candidate orchestration; none of them is touched here.

## 2026-09-12 — audit, architecture, isolated engine

* Audit (`P5_EXISTING_CAPABILITIES.md`): the frozen core already carries `Customer.priority`,
  `Service` economics (`selling_price`, `sla_per_unmet`, metrics up to order OTIF), dated `OrderLine`
  records with promised dates, approved `Substitute` rules, `Stock.reserved`, sector physics, and a
  per-period allocation inside the MILP (`allocate`, `depleted`, `fefo`, `priority`, `direct_first`);
  settlement distributes served units to lines in `(promised_at, id)` order. Missing: ATP / CTP as a
  quantity, reservations bound to an order, promise-date decisions, backorders, partial / minimum-ship
  rules, economic classes with provenance, incumbent policies, a "who got what and why" report.
* Architecture (`P5_ARCHITECTURE.md`): `zaad/atp/` isolated engine (contracts, state ladder,
  economics on the shared ledger, incumbent policies, exact MILP through scipy's HiGHS, validation,
  report, fixtures, vault adapter), `Request.atp` default None, migration 020, isolated endpoint
  `POST /api/zaad/atp/promise` behind `ZAAD_ATP_ENABLED=1` (404 otherwise).
* Ownership decisions (which phase decides what): protection P0, purchase P1, movement P2 (P5 only
  prices an alternative ship-from with the approved lane's cost / lead / capacity and emits no
  transfer), sourcing P3, conditionality P4 (the future `promise[line, ..., node]` interface is
  documented, not built), physics = sector layer (P5 reads `sellable` / `location_ok` / `lane_ok`).
* Economics decisions: unmet = lost sale (declared lost margin, else the Service selling price - the
  settlement's own basis) + Service SLA + class shortage penalty; refused (CANCEL_IF_LATE shortfall)
  = lost sale + declared refusal cost; late = periods late x class late penalty (`backorder_carry`);
  substitute = frozen `Substitute` penalty; alternative ship-from = lane cost (`transfer`). Each unit
  in exactly one state; ledger total = objective (invariant 13).
* Promise semantics decided while building: a promise period is a delivery period >= the requested
  period (no unrequested early delivery) and <= requested + the order's backorder window; supply is
  drawn from a dated lot only when the lot is available and sellable both at departure and at the
  promise period.
* Fairness decided while building: `PROPORTIONAL_WHEN_INDIFFERENT` is a declared tie rule applied
  to the recommendation (optimised or incumbent) among lines with identical drivers, dates, SKU,
  eligibility and rules; it never changes the ledger and is never a redistribution for value.
  Without it the documented tie is (promise period, order period, line id).

### Fixture corrections (logged; definitions otherwise frozen at registration)

* N (cold chain): the frozen contract refuses chilled stock declared at a non-chilled location
  outright (recorded as adversarial evidence "cold-chain invalid shipment"), so N keeps every
  location chilled-capable and declares the central -> north lane AMBIENT-only; the principle is
  unchanged (no unit crosses an ineligible lane; only north's own stock is promised).
* I / J (future inbound): built on `inbound_transfers` (dated arrivals) rather than an `OpenPO`
  record (22 required fields); the state builder counts open POs the same way (expected arrival
  period from `current_eta`, `expected_accepted_remaining` x declared confidence).

### Results (isolated engine, local)

* fixtures `benchmarks/p5_isolated`: 24 / 24 (A-V incl. L2, P1 / P2, S refused at the contract),
  three runs identical, invariants 1-19 on every recommended allocation;
* adversarial: 16 / 16 fail closed;
* tests `tests/unit/test_zaad_atp.py`: 9 (disabled-path identity, contract refusals, economics and
  ledger reconciliation, reservations, time and physics, incumbent-first and ties, strategic flag
  through economics, migration 020 + adapter, API off by default / 422 / 403 / 413 / 200);
* ruff (CI scope), mypy (CI scope, 137 files), bandit clean.

### Not done in the parallel phase (by rule)

No change to `zaad/full/model.py`, `zaad/full/planner.py`, the P4 node indexing, the P3 shared-order
formulation or the candidate orchestration; no `atp=true` on the from-workspace endpoints; no
threading of promises through P4 nodes; no real-data claims. Shared-core integration starts only
after TRACK A closes and this branch is rebased onto that main.

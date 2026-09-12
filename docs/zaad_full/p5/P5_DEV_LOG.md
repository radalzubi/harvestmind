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

## 2026-09-12 — rebased onto the TRACK A merge

TRACK A closed with one accepted exact change (warm-started adaptive tree solve), merged as
`main` `6b58764` (PR #69). This branch was rebased onto that main without conflict (P5 touched
no TRACK A file): `ae7001a`. Isolated re-run on the rebased head: tests 9 / 9,
fixtures 24 / 24 (`benchmarks/p5_isolated_rebased`), adversarial 16 / 16. Shared-core
integration is NOT started in this stage; it needs its own authorization.


## 2026-09-12 — shared-core integration (this stage)

Starting state verified: `main` `50980fc`, production runtime `6b58764` (tag
`p4-performance-closure-runtime`), P4 closed. Isolated HEAD reconciled: `claude/zaad-atp-p5` at
`660e5fc` on `50980fc`, pushed, tagged **`p5-isolated-baseline`** (immutable). Re-run from that exact
SHA before any shared code changed: tests 9 / 9, fixtures 24 / 24 (`benchmarks/p5_isolated_baseline`),
adversarial 16 / 16 (evidence byte-identical to the committed record).

### State-contract decisions (`P5_INTEGRATION.md` section 1)

* Allocatable envelope: physical -> minus damaged / quarantined -> minus sector-unsellable at the
  promise period and ineligible locations -> minus `Stock.reserved` (the frozen contract's only hard
  reservation; the frozen model and settlement plan on `Stock.usable`, which excludes it) -> ATP.
* No hard protection commitment exists in the frozen contract: P0 protection is a service-level
  construct inside the planner's candidate solves. P5 subtracts nothing for it and reports the
  planner's protection profile as an overlay (`hard_reservation: false`) on the planner path.
* Firm versus non-firm: `InboundTransfer` (fixed variable in the frozen model, deterministic
  arrival in the settlement) is firm and promisable at or after `due_in`; `OpenPO` (fill and lead
  drawn per world) is non-firm, never promised, reported. `inbound_confidence` other than 1 is
  refused at the contract (the isolated engine multiplied inbound by it: removed).
* Direct versus transfer: `fulfilment` DIRECT | ALTERNATIVE_SHIP_FROM on every shipment;
  `p2_transfers_created: 0`; `blocked_supply` names stock that would need an implicit transfer.
* Reservations: one PROPOSED reservation per shipment, traceable to customer / order / line / SKU /
  lot (frozen record) / location / promise period; release semantics documented (operator records
  `Stock.reserved` on approval).

### Ledger decisions (`P5_INTEGRATION.md` section 2)

* `shortage_penalty` split out of `sla` (the isolated engine folded the class penalty into the
  Service SLA key; both now visible, each owned).
* `transfer` renamed `alternative_ship_from` (no movement is created; the settlement's `transfer`
  key is for real P2 movements).
* Lost-sale basis labelled per line (`service_selling_price` = the frozen settlement convention,
  or a declared line / class margin); the driver text says "lost sale per unit (basis)" instead of
  "lost margin".
* Owners reported in the block (`ledger_owner`). Unresolved question recorded: netting the retained
  unit's asset value (the frozen net content) in the P5 comparison.

### Tie rules made explicit while running the integration matrix (not economics)

* I02 first run: both eligible direct locations at equal cost, the incumbent's lexical lot order
  served everything from `central`. Documented tie added: the service's own location first among
  equal-cost direct channels (`TIE_HOME` in the optimiser, `not c.home` in the incumbent sort). The
  registered pass condition (30 north + 50 central) is met by the tie rule; no fixture changed.
* I15 first run: the proportional-fairness group was keyed on the class id, so two classes with
  identical numbers were not "indifferent". Corrected: indifference is keyed on the declared numbers
  (lost sale, SLA, shortage, late, refusal, floor) never on a class id, name or tier.
* FEFO among cohorts of one location added as a tie (`TIE_FEFO`), the frozen model's `fefo` rule;
  I04 passed on the first run with it.
* I19 first run: the API fixture exceeded the frozen interactive solver-time envelope
  (`max_solve_seconds x (10 + services) > 180`) before the P5 gate; the fixture now declares 5 s.
  The planner API 200-path test uses I01 (the released request's own customers carry the demand
  history the planner forecasts from; `scene()` fixtures add history-less services and are
  engine-only).

### Results on the integrated code

* integration matrix I01-I20: 20 / 20 (`evidence/p5/integration/p5_integration`), invariants 1-19
  on every recommendation, I20 identical to the pre-P5 runtime `6b58764` (report from the deploy
  checkout, timing and hashes stripped) and to `enabled: false`;
* isolated matrix on the integrated engine: 24 / 24 (`benchmarks/p5_integrated`), adversarial
  17 / 17 (new case: probabilistic inbound refused);
* tests: `tests/unit/test_zaad_atp.py` 9, `tests/unit/test_zaad_atp_integration.py` 9;
* profile (`evidence/p5/integration/P5_PROFILE`): up to 500 lines / 26 periods / 2 locations /
  firm inbound: 787 rows, 4,709 columns, 189 binaries, build 0.007 s, solve 0.19 s, root-node
  optimal, first incumbent at 0.0 s, peak RSS 142 MB - no performance work attempted;
* ruff (CI scope), mypy (CI scope + `zaad/atp`), bandit (`-ll`) clean.

### Candidate, frozen regressions, CI

Product commit `b984543`, evidence `2c87fb0`, PR #71 (open, not merged, nothing deployed). Frozen
regression chain in one pass on `b984543`: P3 snapshot identical, P1 canonical + 720 invariants,
P2 1,720 / 1,720, sector 416 / 416, P3 30 / 30, 34 / 34, 23 / 23, 2,304 / 2,304, P0 120 / 120
(`evidence/p5/integration/gates/`). Full suite 1,964 passed / 2 skipped. CI once on `2c87fb0`: run
34708783613 green on every gate (CodeQL environment defect as always). Release strategy honoured:
isolated baseline -> integration -> validation -> frozen regressions -> CI; the P5 release audit and
any release need their own authorization.

## 2026-09-12 — release audit (branch `release/p5-atp-release-audit` from `17d2d74`)

* A. Lost-sale basis corrected to the lost contribution (`selling_price - asset_value`, the frozen
  allocation-ranking basis) with declared margins as overrides; ledger key `lost_contribution`;
  gross selling price reported as information; `TIE_UNMET` keeps zero-contribution demand served
  when serving is free. Classified as a P5 semantic correction; no verdict changed on the 24 + 20
  matrices (costs fall by the asset value per unmet unit); R01-R03 pre-registered and pass.
* B. `ServiceClass.shortage_penalty_basis` (ADDITIONAL_TO_SERVICE_SLA with a reference and
  CONTRACT / OPERATOR_DECLARED provenance, or REPLACES_SERVICE_SLA), required whenever a class
  penalty meets a stream SLA; migration 021 (additive column); adversarial case 18 (four refusals).
  Fixture classes now declare the basis explicitly (`cls()` helper default with a fixture policy
  reference); principles unchanged.
* C. `plan/from-workspace` forwards every phase flag by keyword (the released code dropped
  `recourse`); R16 / R17 and `test_workspace_plan_forwards_every_phase_flag_by_keyword`.
* `fly.toml` `[env]` gains `ZAAD_ATP_ENABLED = '1'` for the production environment (release
  configuration, versioned; the code default stays off; every request must declare its block).

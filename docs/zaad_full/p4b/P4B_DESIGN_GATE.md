# P4B — Open PO / Commitment Recourse: design gate

Status: DESIGN GATE ONLY (no implementation authorized). Starting state: `main` `9ae66ab`, production
runtime `2fc7b50` (tag `p5-release-runtime`). No released semantic, contract, migration, API, deployment
or evidence is modified by this gate; this document and `P4B_PREREGISTRATION.md` are the only outputs.

## 1. Repository audit (what exists today)

Source inspected: `zaad/full/contracts.py` (`OpenPO`, `POOption`, `Source`, `Terms`, `SupplierTerms`,
`Liquidity`), `zaad/full/model.py` (amendment block, lines 836-877), `zaad/full/settlement.py`
(84-115), `zaad/full/planner.py` (`action_rows`, incumbent amendments), `zaad/full/replay.py`
(262-310), `zaad/full/worlds.py` / `uncertainty.py` / `eta.py` (PO ETA and fill per world),
`zaad/full/economics.py` (`COMPONENT_OF`), `zaad/full/workspace.py` (460-492), `zaad/recourse/*`
(`Action`, `NodeMap`), `zaad/sourcing/*`, `db/migrations/013`, `api/routers/*`, `zaad/full/demo.py`.

| existing capability | current owner | P4B gap | new modeling needed |
|---|---|---|---|
| `OpenPO`: ordered / confirmed / shipped / received / rejected, `expected_accepted_remaining`, `placed_at` / `confirmed_at` / `departed_at`, `current_eta`, `stage`, `carrier`, `cancellation_status`, `prepaid_per_remaining_unit`, `allow_split_amendments`, `options` | frozen contract (P0) | `stage` and `cancellation_status` are free text; no minimum-remaining field (expressible as `cancel.max_quantity = remaining - minimum`); no refundable-deposit credit; no supplier capacity for an expedite | contract additions only: `credit_per_unit` on an option, a declared stage vocabulary; no new record |
| `POOption`: `action` keep / cancel / expedite / de_expedite / reschedule, `due_in`, `fee_per_unit` (>= 0), `remaining_invoice_per_unit`, `payment_due_in`, `max_quantity`, `deadline`, `allowed_stages`, `contract_reference` | frozen contract (P0) | the windows the brief asks for exist per option (deadline, stage eligibility, quantity cap); DEFER = de_expedite / reschedule, EXPEDITE = expedite, REDUCE = partial cancel with `allow_split_amendments`, SPLIT = keep + reschedule with split allowed; no REROUTE | none for KEEP / DEFER / EXPEDITE / REDUCE / CANCEL / SPLIT; REROUTE is P7 |
| Frozen model: one continuous column per (PO, option) `amend[po, option]`, conservation `Σ = remaining`, exclusivity binary `po_option[po, option]` when split is not allowed, fee expensed at period 0, remaining invoice at `payment_due_in`, arrival at the option's `due_in` plus the world's own ETA error relative to keep, terminal credit past the horizon, prepaid x remaining as a constant (sunk), per-action ablation switch, `po_closed` dust rule | P0 / P1 joint MILP (`zaad/full/model.py`) | here-and-now intervention decisions ALREADY exist and are solved jointly with purchases, transfers, allocation and cash; they are scenario-invariant (decided at period 0 only) | none for the here-and-now decision; node-indexed amendment columns would be new (section 8) |
| Settlement: fees to ledger keys `cancel_fee` / `expedite_fee` / `de_expedite_fee` / `reschedule_fee`, remaining invoice to `procurement`, payments dated, arrival shift, conservation and exclusivity re-checked, prepaid into `opening_assets` | P0 ledger (`settlement.py`) | `*_fee` keys are not in `economics.COMPONENT_OF` (reported as `unmapped_ledger_keys` / OTHER); no operator-language explanation of an amendment; no credit key | ledger mapping and report only |
| Planner: incumbent = keep every PO; candidates may choose options; `action_rows` emits `po_option` rows (period 0, first_review); approval flags | P0 / P1 planner | no KEEP-first materiality verdict for interventions; no "why" block; no incumbent comparator beyond keep | orchestration / explanation only |
| Uncertainty: PO ETA from the right-censored Kaplan-Meier `conditional_eta` (stage- and carrier-stratified), `po_due` / `po_fill` per world, recent fill runs, backlog-implied lead | P0 / P6 (future) | changed ETAs inherit the keep ETA's error (contractual target + world error) - correct and already implemented | none |
| Causal replay: after a review, an amended PO is re-issued as a keep-only PO (`cancellation_status: no_new_amendment_quote`, `committed_after_review`) | benchmark harness | no re-quoting of options across reviews by design (no invented flexibility); multi-review intervention evidence therefore does not exist | replay convention only if a V2 recourse action is built |
| P4: `Action = purchase \| transfer`; `NodeMap.adapts(kind)`; "no cancellation in V1 (committed = committed)"; pipeline PO options listed as irreversible | P4 (frozen) | a future amendment decision that depends on observed information is not representable | new column kind `amend` in the node map (section 8) - the only genuine new modelling |
| P3 sourcing: shares, switching, risk groups over `Source` records; no `OpenPO` interplay | P3 | reroute-to-another-source = cancel option + new purchase from an approved source (P1 + P3 composition, expressible today subject to the cancel option) | none |
| Workspace: `stg_fmcg_purchase_orders` (po_id, po_date, supplier, sku, qty, unit_cost, expected_delivery_date); adapter declares the KEEP option only | workspace adapter / migration 013 | no declaration path for options, deadlines, stages, deposits, credits, fees | migration (additive declaration table) + adapter |
| API: `/plan`, `/jobs`, from-workspace; `executable_purchase_order: false` everywhere; no amendment endpoint | API | no declaration or explanation surface for commitments | plumbing only |
| Economics: `Terms` (deposit fraction, balance trigger, net days, LC fraction, financing fee) for NEW purchases; `Liquidity.cost_of_capital_per_period` on dated payments | P1 | PO payment timing already flows through `payment_due_in`; deposit sunk treatment exists (forfeited on cancel through the asset delta); refundable deposit missing | `credit_per_unit` |
| Fixtures / tests: `demo.py` "recovery" case (PO 100 with keep / cancel 0.25 / de_expedite 0.10), `test_unapproved_substitution_and_cancel_cannot_run`, ablations with the cancel switch, INDUSTRY_STANDARD_V8 cell 21 "order cancelled entirely" | P0 evidence | no pre-registered intervention matrix, no adversarial matrix for commitments | evidence only |

## 2. Exact capability gap

The here-and-now question "KEEP / DEFER / EXPEDITE / REDUCE / CANCEL / SPLIT an existing PO, given
declared options" is **already solved** by the frozen P0 / P1 model whenever the request declares the
options. What is missing is not the mathematics but:

1. **Declaration**: no vault path can declare anything but KEEP, so production never sees an option.
2. **Refundable deposits / credits**: `fee_per_unit >= 0`; a cancellation credit or refundable deposit
   cannot be expressed; the prepaid deposit is always sunk.
3. **Reporting and comparator**: no KEEP-first materiality verdict, no operator-language "why", the
   `*_fee` keys are unmapped in the cost breakdown.
4. **Information timing**: an amendment that should be decided at a review epoch on observed
   information (a cancel window that is still open at period 3, say) is not representable; P4 V1
   holds committed = committed.
5. **REROUTE** (itinerary / mode / port change) is not a commitment decision but a logistics one and
   belongs to P7; reroute-to-another-source is a composition of a cancel option and a P1 / P3 purchase.

## 3. Recommended ownership boundary

| decision | owner |
|---|---|
| what to commit to initially (quantity, timing, source split) | P1 / P3 |
| which future purchase / transfer adapts to observed information | P4 |
| which declared change to an existing commitment to take now (keep, defer, expedite, reduce, cancel, split) | **P4B V1** = the existing P0 / P1 amendment columns, made usable (declaration, credits, explanation, comparator) |
| which declared change to take at a later review epoch on observed information | **P4B V2** = an `amend` column kind in the P4 node map (gated separately, section 17) |
| route / mode / port / sailing of the commitment | P7 (not P4B) |
| cash rationing across commitments | P9 (not P4B; P4B prices payment timing through the released cost of capital only) |
| container composition | P8 |

## 4. Action taxonomy

| action | decision variable | feasibility | declared data | economics | owner | P4 interaction | in P4B? |
|---|---|---|---|---|---|---|---|
| KEEP | `amend[po, keep]` (exists) | always (the keep option is mandatory) | keep option: `due_in`, `remaining_invoice_per_unit`, `payment_due_in` | remaining invoice at its date; arrival at the world's ETA | P0 / P1 (exists) | irreversible today; KEEP is the incumbent | yes (baseline) |
| DEFER | `amend[po, de_expedite]` / `amend[po, reschedule]` (exist) | `deadline >= as_of`, `stage in allowed_stages`, `q <= max_quantity` | option with later `due_in`, `fee_per_unit`, invoice terms | fee now; carrying avoided and service risk taken through the joint model; payment shift through `payment_due_in` | P0 / P1 (exists) | V2: node-indexed when the deadline outlasts an epoch | yes |
| EXPEDITE | `amend[po, expedite]` (exists) | as above; supplier capacity for the earlier date is NOT modeled (only `max_quantity`) | option with earlier `due_in`, premium as `fee_per_unit` and / or higher invoice | premium now; shortage avoided through the model; the world's ETA error still applies | P0 / P1 (exists) | V2 as above | yes (capacity stays a declared cap) |
| REDUCE | `amend[po, cancel]` partial with `allow_split_amendments` (exists) | `q <= cancel.max_quantity` (= remaining - contractual minimum) | cancel option with `max_quantity`, fee, credit (new) | fee per unit reduced; credit per unit (new); deposit share on the reduced units forfeited unless credited | P0 / P1 (exists) + credit | V2 as above | yes |
| CANCEL | `amend[po, cancel] = remaining` (exists) | as REDUCE with `max_quantity = remaining` | cancel option; credit (new) | fee; deposit forfeited (sunk) or credited (new) | P0 / P1 (exists) + credit | V2 as above | yes |
| SPLIT | keep + reschedule / expedite with `allow_split_amendments` (exists) | split allowed by the supplier; each part within its option's cap | two or more options with split allowed | each part priced by its option | P0 / P1 (exists) | V2 as above | yes (a combination, not a new variable) |
| REROUTE | none | itinerary / mode / port change | route capacity, cutoffs, transit distributions, demurrage | freight, transit, demurrage | **P7** | - | **no** (rejected from P4B; reroute-to-another-source is CANCEL + P1 / P3 purchase) |

Rejected as un-modelable from declared data: any "supplier goodwill" or relationship cost that is not a
declared fee; "vessel cutoff" as an implicit window (only an option `deadline` counts); expedite capacity
beyond `max_quantity`.

## 5. Required data model (contract additions only, additive, default-neutral)

```
POOption (existing) +
  credit_per_unit: float = 0            # refund / credit-note per amended unit (refundable deposit, restocking credit); <= prepaid + invoice already paid
  provenance: CONTRACT | OPERATOR_DECLARED | CONFIGURED_ASSUMPTION   # today only contract_reference
OpenPO (existing) +
  stage: Literal[placed, confirmed, in_production, shipped, arrived, received]   # today free text; stage-eligibility rules need a vocabulary
  minimum_remaining_quantity: float = 0 # convention today: cancel.max_quantity = remaining - minimum; made explicit and validated
  deposit_refundable_fraction: 0..1 = 0 # share of prepaid_per_remaining_unit credited on cancel / reduce (else sunk)
Vault: stg_po_options (declaration rows per PO: action, due offset, fee, credit, invoice, payment terms, max quantity, deadline, allowed stages, contract reference, provenance) - additive migration; adapter attaches options only when declared; absent -> KEEP only (identity)
```

Irreversibility ladder derived from these fields (no invented flexibility):

| state | rule |
|---|---|
| editable | an option other than keep exists with `deadline >= as_of` and `stage in allowed_stages` |
| partially editable | `allow_split_amendments` true and `max_quantity < remaining` on some option |
| financially committed | `prepaid_per_remaining_unit > 0` (deposit) and / or `Terms.letter_of_credit_fraction > 0`; sunk unless `deposit_refundable_fraction` / `credit_per_unit` says otherwise |
| physically committed | `departed_at` set or stage `shipped` / `arrived` |
| shipped | stage `shipped` / `arrived`: only options whose `allowed_stages` include it (typically none) |
| non-cancellable | no cancel option, or its deadline passed, or its stage excluded |

## 6. Mathematical formulation sketch (V1 = the existing block, V2 = node-indexed)

For PO `p` with remaining `R_p`, options `O_p` (keep in `O_p`), worlds `w`, node `n` (V1: the root only):

```
amend[p, o, n] >= 0,  amend[p, o, n] <= cap(o) = min(R_p, max_quantity(o)) if allowed(o) else 0
Σ_o amend[p, o, n] = R_p                                        (conservation, per node)
allow_split false: amend[p, o, n] <= R_p * z[p, o, n],  Σ_o z[p, o, n] = 1,  z binary   (exclusivity)
cost: Σ_o amend[p, o, n] * (fee(o) - credit(o)) at period 0 + remaining_invoice(o) at payment_due_in(o)
arrival in world w: amend[p, o, n] * po_fill_w[p] at due_w(o) = due_in(o) + max(0, po_due_w[p] - keep.due_in)   (cancel: none)
sunk: prepaid * R_p constant; refundable: credit(o) <= prepaid * refundable_fraction + paid invoice share
V2 only: n ranges over the information-set nodes of the epoch at which the option is decided
         (decision period = max(0, latest epoch <= deadline period)); non-anticipativity by construction:
         two worlds with the same observable history share the node and therefore the same amend[p, o, n].
```

Nothing else changes: purchases (P1), transfers (P2), allocation, cash and service rows read the
arrivals as today. No separate MILP: the coupling (arrival -> inventory -> service -> purchases ->
cash) is real and already solved jointly.

## 7. Shared-ledger ownership (no double count)

| term | ledger key | owner | note |
|---|---|---|---|
| cancellation penalty | `cancel_fee` (exists, unmapped) | P4B declaration -> P0 ledger | map to a `COMMITMENT` component |
| amendment fee (defer / reschedule / expedite) | `de_expedite_fee` / `reschedule_fee` / `expedite_fee` (exist, unmapped) | same | |
| expedite premium on price | `procurement` via `remaining_invoice_per_unit` (exists) | P1 ledger | not also a fee unless declared as one |
| defer cost | none directly: carrying (`holding`) and service (`lost_sales_opportunity`, `sla`) through the joint model | P0 ledger | never a second "defer" key |
| carrying cost | `holding` (exists) | P0 | amended units are held once, after arrival |
| working-capital timing | dated `payments` + `Liquidity.cost_of_capital_per_period` (exist) | P1 | P9 is the hard constraint, not built |
| sunk deposit | `opening_assets` constant (exists): forfeited on cancel through the asset delta | P0 | correct sunk treatment |
| refundable deposit / credit note | `commitment_credit` (new, negative cost) | P4B | bounded by what was paid |
| non-refundable freight | declared inside `cancel_fee` by the operator, or P7 | P4B / P7 | never inferred |
| demurrage / storage | P7 | - | out of P4B |
| supplier relationship penalty | only as a declared fee with provenance | P4B | never inferred |

## 8. P4 interaction

V1 (here-and-now): amendments stay scenario-invariant root decisions - no change to information sets,
node indexing or non-anticipativity; P4's "committed = committed" stays true for periods after the root.
V2 (recourse amendments): a new column kind `amend` in `NodeMap.adapts`, declared through
`recourse.actions` ("amend"), with the decision epoch of an option = the latest review epoch at or
before its deadline; exclusivity binaries per (PO, node); `world_plan` / `lookup` read amendments per
node exactly as purchases; REPLAN_REQUIRED semantics unchanged. Non-anticipativity holds by
construction (fixtures 18 / 19). V2 is gated on evidence that amendment windows outlast the first
review epoch on real declarations.

## 9. P1 / P3 / P7 / P9 boundaries

P1 keeps the initial commitment decision and every economics of new purchases (terms, deposits, lots,
cadence); P4B never creates a purchase. P3 keeps source selection; a "reroute to another supplier" is
CANCEL (P4B option) plus a P1 / P3 purchase, both already expressible, never a P4B variable. P7 owns
route / mode / port / sailing / demurrage: REROUTE is rejected from P4B. P9 owns cash rationing; P4B
prices payment timing through the released cost of capital only and adds no capital constraint.

## 10-12. Fixture matrix, invariants, adversarial cases

Pre-registered in `P4B_PREREGISTRATION.md` (20 fixtures, 18 invariants, 14 adversarial cases).

## 13. Expected performance risks

| growth | V1 (root only) | V2 (node-indexed) |
|---|---|---|
| columns | Σ_p \|O_p\| (exists today) | Σ_p \|O_p\| x nodes(epoch(p)) |
| binaries | Σ_{p not split} \|O_p\| (exists today) | x nodes; e.g. 40 POs x 4 options x 8 nodes = 1,280 binaries |
| supplier coupling | none: amendments do not enter the P3 supplier-order (MOV / fixed-cost) rows | same |
| transport coupling | none in P4B (P7) | same |

V1 adds nothing to the released dimensions when no option is declared (identity) and, when declared,
only what the frozen model already builds. V2 adds binaries in the class where binaries are already
the bottleneck (P3 + P4 shared-order: 624 binaries at 12 worlds, time-limited at 16): a V2 on that
class is expected to make it materially worse and must be measured before any promise; V2 must be
batch-only there, as P4 already is.

## 14. Commercial value (import-distributor wedge)

* customer pain: high and import-specific - capital is committed 8-16 weeks before receipt; the
  released stack recommends new orders while treating open POs as fixed except in requests that
  declare options, which no production path can do today;
* data availability: medium - cancellation windows, deposits and fees are known to buyers but rarely
  recorded as data; P4B needs a declaration surface (the vault table) and will run KEEP-only until
  operators declare terms (identity);
* differentiation: high once declared (competitors treat open orders as fixed inputs);
* implementation burden: **low for V1** (the model exists; declaration, credits, mapping, explanation,
  comparator, fixtures), medium-high for V2;
* validation burden: medium (synthetic fixtures 1-20; no real supplier terms available);
* sales usefulness: high ("should we cancel or expedite the container" is the importer's question);
* import specificity: highest of the candidates alongside P7 / P8.

## 15. Comparison with P6 / P7 / P8

| next phase | value | burden | dependency | verdict |
|---|---|---|---|---|
| P4B V1 | high, import-specific, existing maths | low | none | first |
| P6 uncertainty engine | foundational for every phase, high credibility value | high | none, but broad | second (independent of P4B) |
| P8 container / load portfolio | high where customers control containers | medium-high (cross-SKU load rows on the P3 shared-order class) | P1 / P3 | third |
| P7 import logistics | high if operators control routing; often forwarder-controlled | high (route / mode data) | P6 for transit distributions | fourth |

## 16. Recommended architecture

**B with the existing joint solve**: a commitment-state module (`zaad/commitments/`: irreversibility
ladder, windows, credits, KEEP incumbent, explanation, materiality) that produces / validates the
released `POOption` records and reads the released amendment columns' results; declaration path
(migration + adapter); ledger mapping. No new optimizer, no giant MILP: the coupling is real and is
already solved jointly. V2 = option A (an `amend` action kind inside P4) only after the separate gate.

## 17. Implementation scope if authorized (V1)

1. contract additions (`credit_per_unit`, provenance, stage vocabulary, `minimum_remaining_quantity`,
   `deposit_refundable_fraction`), default-neutral, identity proven;
2. model: credit term on the existing amendment columns (a negative cost bounded by what was paid);
   no other change to `zaad/full/model.py`;
3. settlement: `commitment_credit` key; `COMPONENT_OF` mapping of the `*_fee` keys and the credit;
4. planner / explain: KEEP incumbent comparator, materiality verdict `NO MATERIAL COMMITMENT
   IMPROVEMENT AVAILABLE`, operator-language "why" per PO;
5. migration (additive `stg_po_options`) + adapter + from-workspace flag `commitments=true`;
6. fixtures 1-20, invariants, adversarial matrix, frozen regression chain (identity on every released
   request), profile;
7. explicitly NOT in V1: node-indexed amendments (V2), REROUTE (P7), capacity for expedite, demurrage.

## 18. Verdict

The gap is real but narrower than the roadmap's framing: the here-and-now commitment decision is
already modelled and validated inside P0 / P1; what is missing is the declaration path, refundable
credits, ledger mapping, the KEEP-first comparator and explanation - a bounded, low-risk build with
high import specificity - while the recourse form (V2) is the only genuinely new modelling and
carries the performance risk, so it stays gated. P6, P7 and P8 are not blocked by P4B V1.

**P4B DESIGN GATE — BUILD** (V1 scope of section 17 only; V2 requires its own gate; implementation
requires separate authorization).

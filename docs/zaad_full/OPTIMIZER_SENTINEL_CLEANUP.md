# Optimizer numerical-formulation cleanup — undeclared capacity and capital are absent constraints, not 10⁹

**Status: IN PROGRESS (2026-09-22).** Branch `fix/optimizer-sentinel-cleanup` from `main` `34221d4` (= the
Diagnostic V3.1 runtime `0cad5de` plus its docs commit). Tracker written before any code change.

Principle of the brief: a missing business constraint is represented as a missing constraint. The optimizer
abstains because the business problem is unsupported or infeasible, never because an adapter inserted 10⁹
and destabilised the model. This is not a loosening: where a customer declares capacity or capital, the
formulation is kept verbatim (bit for bit) and the declared value is enforced exactly as before.

## 1. Sentinel audit (repo review, before code)

Search: `1e9`, `1_000_000_000`, `UNBOUNDED`, `inf`, default capacity / cash values, across `zaad/`, `api/`,
`synthetic/`, `scripts/`. Fixtures declare finite values (`1e6`) by construction and are not sentinels of the
adapter; they are listed where they matter for the frozen gates.

| field | current default | where introduced | where used | semantic meaning | can the constraint be omitted? | big-M consequence |
|---|---|---|---|---|---|---|
| `Location.capacity_volume` (single-location workspace) | `UNBOUNDED = 1e9` | `zaad/full/workspace.py:529` (the adapter never reads a location table) | `model.py`: inventory column upper bound `(cap − locked)/volume`; end-of-period volume row `≤ cap − locked`; before-serving volume row; **big-M of `depleted` (`Σ stock + M·empty ≤ M`), `fefo` (`Σ older + M·active ≤ M`), `priority` (`Σ lower_units + M·active ≤ M`), `direct_first` (stock row)** with M = cap / volume; `settlement.py:153` receiving-capacity check; `meio/topology.py` node view | **not declared → no storage constraint** (the adapter records nothing; the single-location adapter does not read `stg_fmcg_locations`) | yes: omit the two volume rows and the column bound; the four binary linkages need a *valid* finite bound on stock, derived from the flow that can reach the location (§3) | M = 10⁹ / volume in every depleted / fefo / priority / direct_first row: with thousands of such rows HiGHS declares the 25–50-product requests infeasible (V3.1 record §3.3: OPTIMAL at 10⁸ / 10⁷ / 10⁶) |
| `Location.capacity_volume` (network workspace) | `UNBOUNDED_LOCATION_UNITS = 1e7` | `zaad/meio/workspace.py:46,117` (when `capacity_units` is absent on the location row) | same | same: "no declared capacity" (its own comment) | same | same family, 10⁷ (chosen because 10⁹ already failed there) |
| `Liquidity.opening_cash` | `UNBOUNDED = 1e9` | `workspace.py:545` when `stg_fmcg_economics.opening_cash` is absent; provenance `NOT_AVAILABLE` | `model.py` cash / debt columns, balance rows, LC reserve rows, terminal-solvency row, **objective `−cost_of_capital × cash_t` per period (working capital)**; `settlement.py` cash trace, borrowing, `working_capital` ledger; `policies.apply_cash_cap`; `economics.working_capital`; `replay.py` carries closing cash into the next snapshot | **not declared → no cash balance is tracked: no cash floor, no borrowing, no facility; purchases are financed as they fall due; the cost of capital is charged on the cash deployed since the plan's start** (this is exactly what the 10⁹ computed, minus the constant) | yes: the cash and debt columns and every liquidity row can be removed exactly; the working-capital charge becomes a coefficient on each payment (§4) | the objective carries a constant `−rate × (opening + credit) × H` ≈ −5.1 × 10⁷ on the demo request (rate 0.11 / 52, H 12): the 1e-6 relative gap is ≈ 50 cost units, and every `comparable_gap` (2 %) judgement is measured against a fake 5 × 10⁷ |
| `Liquidity.credit_limit` | `UNBOUNDED = 1e9` | `workspace.py:546` when `credit_limit` is absent | debt column upper bound, terminal-solvency row rhs; settlement limit check and terminal headroom; `apply_cash_cap`; `Request` validator `opening_debt ≤ credit_limit` | with opening cash declared: **no facility ceiling** (borrowing unbounded at the declared interest); with opening cash undeclared: irrelevant | yes: unbounded debt column, terminal row omitted | with `interest_per_period = 0` (the adapter default) the model borrows the whole 10⁹ to hold cash the working-capital term rewards → the objective constant doubles (measured −5.0 × 10⁷ against a cash-only constant of 2.5 × 10⁷) |
| `Source.capacity_by_period`, `Source.maximum`, `Resource.capacity_by_period` (supplier capacity) | `UNBOUNDED = 1e9` | `workspace.py:299` only when a supplier has no declared capacity **and** no purchase order before the origin (provenance `NOT_AVAILABLE`); otherwise `1.25 × peak weekly PO` (INFERRED) or the declared value | purchase column bound, `packs` bound, `active` (MOQ / fixed-fee) big-M `min(cap, tight)`, supplier-order rows, resource row rhs; `historical._conform`, `_conform_shared` | not declared → no supplier constraint | partly: the column bound and the resource row can be omitted; the MOQ / fixed-fee activation row needs a finite M, which only the dominance argument of `activation_bounds` supplies (P3, guarded) — **deferred, §2** | on the demo (5 suppliers, all declared) and the sample (8, all inferred) no source carries it; it enters nothing in the profiled failures |
| `TransferArc.capacity` (network lanes) | `LANE_CAPACITY_WEEKS × demand rate` | `meio/workspace.py:255` | lane rows, transfer packs / dispatch big-M | a declared assumption (ten weeks of demand), documented, finite and data-scaled | n/a (not a sentinel) | none |
| fixtures (`fixtures_p1`, `fixtures_p2`, `sourcing/fixtures`, `demo.py`) | `1e6` capacities and cash, or small declared values | test fixtures | the frozen gates | declared values | must stay verbatim | none (the frozen decision paths depend on them) |

The objective constant was measured on the demo request: `cost_of_capital_per_period × opening_cash × H`
= 0.00212 × 10⁹ × 12 = 2.54 × 10⁷, and the solver's objective of ≈ −5.0 × 10⁷ (V3.1 §3.2) is that constant
doubled by the credit limit at zero interest — the whole magnitude is adapter sentinel, none of it economics.

## 2. Business semantics (established before the formulation change)

| missing field | meaning | basis | decision |
|---|---|---|---|
| warehouse capacity (single-location and network adapters) | **A. not constrained** | the adapter never reads a capacity for the single location and records no provenance; the network adapter's own comment reads "No declared capacity"; the report's readiness ledger lists storage capacity as an input the customer may supply, never as a limitation applied | represent as no constraint (`capacity_volume=None`) |
| opening cash | **A. not constrained** (no cash balance is tracked); the cost-of-capital economics stay | provenance `liquidity.opening_cash = NOT_AVAILABLE`; the adapter chose 10⁹ for cash *and* credit, i.e. purchases are never cash-limited; `CASH_FLOW_MODEL.md`'s "missing critical financial fields cause schema refusal" refers to the contract's required fields (deposit fraction, net days), which the adapter fills from terms, not to a balance the customer never uploads | represent as `opening_cash=None`: no cash floor, no borrowing, no facility; the working-capital charge on deployed cash is kept exactly |
| credit limit (with opening cash declared) | **A. no facility ceiling** | provenance `NOT_AVAILABLE`; the adapter's 10⁹ | `credit_limit=None`: debt unbounded at the declared interest |
| credit limit (with opening cash undeclared) | irrelevant: nothing to borrow against | | `None`; a declared credit limit without opening cash is recorded as a warning and ignored |
| supplier capacity | A. not constrained | provenance `NOT_AVAILABLE` | **semantics clear, exact formulation not closed in this pass**: the MOQ / fixed-fee activation row needs a finite M and the only bound-free derivation is the dominance argument (`activation_bounds`, proven for the P3 order class under guards). Kept as is; recorded in the big-M audit; not on the profiled failures' path (§1) |
| storage / pallet / location volume beyond the above | none found | | |

Nothing here changes what a *declared* value means or does.

## 3. Warehouse capacity — formulation

When `capacity_volume is None` for a location:

- the inventory columns of that location have no upper bound (was `(10⁹ − locked)/volume`, never binding);
- the end-of-period and before-serving volume rows are not built (were `≤ 10⁹ − …`, never binding);
- the `depleted`, `fefo` and `direct_first` stock rows use `M = stock_bound(sku, location, t)`: the most stock
  of the SKU that can be at the location at the end of period t in any feasible plan = opening usable stock
  of the SKU there (all cohorts) + every inbound transfer of the SKU to it + every open order's remaining
  units for its sources + Σ_{s<t} Σ_{sources of the SKU to it} min(maximum, capacity_by_period[s]) + Σ_{lanes
  into it for the SKU} capacity × t. A purchase placed at s lands at s+1 or later and a fill ratio is ≤ 1, so
  the sum over-counts and never under-counts: valid for every feasible point, hence the feasible set is
  unchanged (§7);
- the `priority` row and the `direct_first` substitute row use `M = Σ conversion × upper(allocation column)`:
  each allocation column is bounded by its service's demand in that period and world, so the sum is the
  exact maximum of the row's left-hand side (tight and valid).

When `capacity_volume` is declared, every row is built exactly as released (`M = capacity / volume`).

The settlement skips the receiving-capacity check for such a location; the network view carries `None`.

## 4. Opening cash / capital — formulation

When `opening_cash is None`:

- no cash or debt columns, no balance rows, no letter-of-credit reserve rows, no terminal-solvency row;
- the working-capital charge is kept **exactly**: the released objective term Σ_t −rate × cash_t, with
  cash_t = opening + Σ_{s≤t}(receivables_s − other_s) − Σ_{s≤t} pay_s(x), equals a constant that does not
  depend on the plan plus rate × Σ_s (H − s) × pay_s(x). The new formulation charges rate × (H − s) on every
  payment column at period s (purchases, fees, order binaries, amendments, SLA payments alike), i.e. the cost
  of capital on the cash deployed from that period to the end of the horizon;
- `projected_cost` no longer carries the constant (which was −rate × Σ_t (opening + credit + …), fake);
- the CVaR rows see the same per-world costs up to a world-independent constant, so the tail variables and
  the threshold shift together: unchanged optimum;
- the settlement tracks the cash position from 0, never borrows, applies no floor or ceiling, and charges
  `working_capital = rate × max(0, −cash)` (identical to the released `rate × max(0, opening − cash)` with a
  never-exhausted opening balance); the projected `apply_cash_cap` of the rule policies is a no-op; the
  replay carries `None` forward instead of the closing balance.

When `opening_cash` is declared and `credit_limit is None`: the debt column is unbounded and the
terminal-solvency row is omitted (it read `≤ credit − minimum_cash`); the settlement skips the limit check.
When both are declared: verbatim.

## 5. Objective-scale audit, 6. big-M audit, 7. equivalence, 9. abstention repro, 10. phase-two proof

*(filled as measured; tool `scripts/formulation_audit.py`)*

## 8. Declared constraints preserved

*(tests; frozen regression)*

## 12–14. Replay retest, stress cases, numerical health

*(filled as measured)*

## 19. Release record

*(pending)*

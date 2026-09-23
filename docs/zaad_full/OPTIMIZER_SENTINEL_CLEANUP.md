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

## 5. Objective-scale audit (measured, `scripts/formulation_audit.py`, Python 3.12 / highspy 1.15.1)

BEFORE = the released adapter's request with its placeholders as declared values (the verbatim released
formulation on identical data); AFTER = the same request with the constraints absent.

| request | solve | BEFORE objective (solver) | BEFORE by family | AFTER objective | AFTER by family |
|---|---|---|---|---|---|
| demo 5 products, deterministic joint phase one | service objective; cost of the returned point | cost of the point: **cash −46,508,343**, purchase 4,125,640, inventory −2,809,388, unmet 208,928, amend 6,990 | | cost of the point: purchase 639,163, unmet 208,928, inventory −20,506, amend 7,164 (phase one is degenerate in cost; the two points differ) | |
| demo 5, three-world joint, phase two (cost) | BEFORE: **INFEASIBLE** (numerical) — no phase two | — | — | **838,190**: purchase 694,793 (landed price + the deployed-capital charge), unmet 206,596, inventory −70,363 (holding less terminal value), amendments 7,164 | proven at gap 9.8e-7 = 0.8 cost units |
| demo 5, planner's `joint_recovery` phase two (4 worlds) | BEFORE: INFEASIBLE | — | — | 837,351: purchase 694,713, unmet 209,297, inventory −73,824, amend 7,164 | |

Why the objective was ≈ −5 × 10⁷: the working-capital term `−rate × cash_t` summed over 12 periods with
cash ≈ opening 10⁹ *plus* the drawn credit 10⁹ (interest 0, so the model borrowed the whole facility to hold
cash the term rewards): −0.00212 × 2 × 10⁹ × 12 ≈ −5.1 × 10⁷. Every real term (purchase ≈ 7 × 10⁵, unmet
≈ 2 × 10⁵) was two orders of magnitude below the sentinel. AFTER, the objective is the plan's economics.

## 6. Big-M audit (per binary family; M = the linking coefficient)

| request | family | rows | BEFORE min / median / max | AFTER min / median / max | AFTER source |
|---|---|---|---|---|---|
| demo 5 (7.7 k columns) | depleted | 360 | 95 / 5.0 × 10⁸ / **10⁹** | 95 / 2,372 / 661,122 | flow bound: opening stock + 60,000 / week supplier capacity × periods so far |
| | fefo | 4,464 | 95 / 5.0 × 10⁸ / 10⁹ | 95 / 2,367 / 661,122 | same |
| | active (MOQ / fee) | 120 | 60 / 9,960 / 60,000 | unchanged | declared line capacity (not a sentinel) |
| | po_option | 2 | 168 / 453 / 738 | unchanged | the order's remaining units |
| sample 25 (14 k columns) | depleted | 600 | 61 / 5.0 × 10⁸ / 10⁹ | 61 / 2,210 / 142,624 | flow bound: 12,540 / week supplier capacity |
| | fefo | 7,776 | 61 / 5.0 × 10⁸ / 10⁹ | 61 / 2,319 / 142,624 | same |
| sample 50 (28 k columns) | depleted / fefo | 1,200 / 15,552 | … / 10⁹ | … / 181,597 | same |

Coefficient ranges of the largest matrix: BEFORE max 10⁹, max/min ratio 1.1–1.4 × 10⁹, largest finite bound
10⁹, largest rhs 10⁹; AFTER max 1.4–6.6 × 10⁵, ratio 1.6–9.4 × 10⁵, largest bound = the supplier's weekly
capacity (12,540–60,000), largest rhs = the flow bound. The remaining ratio is the flow bound against unit
coefficients; a demand-dominance bound (the `activation_bounds` argument) would tighten it further and is
recorded, not applied (§2, supplier capacity).

## 7. Mathematical equivalence

**Volume rows and inventory bounds (capacity None).** The released rows read Σ volume × stock ≤ 10⁹ − locked
and stock ≤ (10⁹ − locked)/volume. On the workspace requests the left-hand sides are bounded by the flow
bound B(sku, location, t) (§3) ≤ 6.6 × 10⁵ ≪ 10⁹, so the rows are slack at every feasible point: removing
them leaves the feasible set unchanged. Replacing the column bound by B is likewise exact: B is an upper
bound on stock in every feasible point (conservation), so no feasible point is cut.

**Linkage rows.** `Σ stock + M·empty ≤ M` with M ≥ every feasible Σ stock encodes exactly `empty = 1 ⇒ Σ
stock = 0` and is vacuous at `empty = 0`; any two valid M give the same feasible set in the original
variables (the binaries are auxiliary). B is valid, 10⁹ was valid: same feasible set, same optimal set,
same objective. The `priority` rows: `Σ ratio × alloc + M·active ≤ M` with M = Σ ratio × upper(alloc) is
the exact maximum of the left-hand side: same argument.

**Cash (opening None).** With opening 10⁹ and credit 10⁹ the released balance rows are never binding at
any feasible point (payments ≤ 10⁷ over the horizon), so the cash and debt columns are free variables
whose only effect is the objective term Σ_t (−rate × cash_t + i × debt_{t−1}). Substituting the balance
rows, cash_t = opening + credit_used_t + Σ_{s≤t}(decl_s) − Σ_{s≤t} pay_s(x) (debt at its bound or zero
depending on interest), so the term is a plan-independent constant plus rate × Σ_s (H − s) × pay_s(x): the
AFTER objective. Argmin sets and objective differences between any two plans are identical; the CVaR rows
shift by the same constant in every world. **Not bit-identical**: the solver sees a different LP (no
constant, no cash columns), so on an objective-flat tie its search may return another optimal point —
the same exposure the frozen gates test for declared values, which are untouched (§16).

**Evidence.** `tests/unit/test_zaad_sentinel_cleanup.py`: identical decisions, service and settlement
between the verbatim released formulation with non-binding declared values (10⁶, the frozen fixtures'
value) and the clean model, and projected costs that differ by exactly the placeholder's constant
(identity checked to 1e-9); the demo-fixture reproduction (10⁹ → INFEASIBLE, 10⁶ / None → OPTIMAL, the
cash placeholder alone benign); a declared capacity that binds on a thin-opening fixture and is enforced by
the settlement; a declared cash ceiling that binds. Frozen canonical regression: identical (§16).

## 9. The 25–50-product abstention, reproduced and fixed

| request | BEFORE (released placeholders) | AFTER (constraints absent) |
|---|---|---|
| demo 5, three-world joint | INFEASIBLE in 0.02 s | OPTIMAL |
| demo 5, planner | RETAIN_INCUMBENT in 1.4 s: every joint solve INFEASIBLE, the planner decided on nothing | RETAIN_INCUMBENT: joint recovery proven (5,845 nodes, 39.6 s), decision made on solved candidates |
| sample 25, deterministic joint phase one | INFEASIBLE in 0.4 s (14,120 cols, 4,529 integer, matrix max 10⁹) | OPTIMAL at the root in 0.8 s (service 0.956) |
| sample 50, deterministic joint phase one | INFEASIBLE in 0.9 s (28,140 cols, 9,032 integer) | *(planner-level run in §9.1)* |
| demo six-period fixture, two worlds | INFEASIBLE | OPTIMAL (and OPTIMAL with a declared 1,000 or 10⁶) |

The false verdicts are numerical: the feasible set with 10⁹ contains the one with 10⁶, which HiGHS solves;
the released model was infeasible only in floating point. Reproduced in `tests/unit` and `tests/integration`.

### 9.1 Planner level (`formulation_audit --plan`, the full released planner on the request; local arm64, contended machine)

| request | BEFORE | AFTER |
|---|---|---|
| sample 25 (largest model 53 k columns, 17 k integer, 250 k non-zeros) | **ABSTAIN** in 4.6 s: incumbent, base-stock proxy and all six candidate classes INFEASIBLE; "incumbent itself has no verified feasible projection; no executable fallback is fabricated" | **RETAIN_INCUMBENT** in 165 s (35 MILPs, 1 time-limited, 860 MB): incumbent OPTIMAL, proxy OPTIMAL, the six candidate classes INFEASIBLE (service floors unreachable from the opening position — a genuine verdict, 0.0–0.1 s each), joint recovery FEASIBLE_TIME_LIMIT at gap 1.5e-4 (362 cost units on 2.44 M) |
| sample 50 (110 k columns, 35 k integer, 527 k non-zeros) | **ABSTAIN** in 13.8 s, same pattern | **RETAIN_INCUMBENT** in 746 s (59 MILPs, 3 time-limited, **2.04 GB peak RSS**): the same candidate pattern, joint recovery evaluated |
| demo 5 | RETAIN_INCUMBENT in 1.4 s: every joint solve INFEASIBLE, nothing evaluated | RETAIN_INCUMBENT in 55 s: joint recovery proven (11,034 nodes, 53 s) |
| demo 10 | RETAIN_INCUMBENT in 4.3 s: same | RETAIN_INCUMBENT in 94 s: joint recovery FEASIBLE_TIME_LIMIT at gap 5.7e-3 |

The false abstentions are gone; what replaces them is the real cost of solving the request. The 50-product
plan's 2.04 GB peak RSS exceeds the production machine's 2 GB (`shared-cpu-2x`): the request that used to
abstain in 14 s would now be killed by memory on production before it decides (§17–18).

## 10. Phase-two proof at the same 1e-6 (measured; the honest answer is "harder")

| request, joint recovery phase two | BEFORE (sentinel objective ≈ −5 × 10⁷; V3.1 profile on the same requests) | AFTER (objective = economics) |
|---|---|---|
| demo 5 (4 worlds, 10 k columns) | 24–30 s, proven, gap ≤ 1e-6 = **≈ 50 cost units** of band (V3.1 §3.1 — on the replay's requests; on the audit's request the solve was INFEASIBLE and never ran) | 53 s, proven, 11,034 nodes, gap 0 (band 0.8 units); the three-world joint 36 s / 8,754 nodes at gap 9.8e-7 |
| demo 10 (21 k columns) | at the 90 s cap, gap 5.7e-5 (≈ 2,800 units of band on 5 × 10⁷ — reported as "nearly proven") | at the 90 s cap, gap 5.7e-3 (**8,113 units** on 1.43 M — the same solve, honestly measured) |
| sample 25 (53 k columns) | never reached (INFEASIBLE) | at the 90 s cap, gap 1.5e-4 (362 units on 2.44 M) |

Removing the constant does not make the same tolerance easier to prove: the relative gap is now measured
against the plan's economics, so the absolute band shrinks 60× and the solver needs more nodes, not fewer.
What the cleanup fixes is the *meaning* of every gap and comparability judgement (a 2 % `comparable_gap`
is now 2 % of the plan's cost, not of 5 × 10⁷); it does not change `solver_mip_gap` (unchanged, 1e-6) and
does not claim a speed-up. The prior pass's owner decision D (gap 1e-5) is where the phase-two time goes.

## 8. Declared constraints preserved

*(tests; frozen regression)*

## 12. Replay retest (`scripts/replay_profile.py`, `--sentinel` = the released placeholders declared on the initial request, the released formulation verbatim; local arm64, contended by other benchmark processes, so walls are relative)

### 12.1 Before / after on identical dates (demo company, window from 2026-04-27, 8 weekly decision dates)

| scope | formulation | dates | total | plan wall median / p90 / max | MILPs (time-limited) | ZAAD outcomes | executed orders vs the other formulation | window cost ZAAD / actual | service |
|---|---|---|---|---|---|---|---|---|---|
| 5 × 8 | BEFORE (10⁹) | 8 / 8 | 720 s | 67 / 334 / 334 s | 118 (6) | **ABSTAIN × 1 (date 1, false)**, RETAIN × 7 | — | 666,574 / 665,099 | 0.6406 |
| 5 × 8 | AFTER | 8 / 8 | 932 s | 86 / 334 / 334 s | 118 (7) | RETAIN × 8 | **identical on 8 / 8 dates** | 666,574 / 665,099 (identical) | 0.6406 (identical) |
| 10 × 8 | BEFORE | 8 / 8 | 1,490 s | 95 / 467 / 467 s | 158 (16) | ABSTAIN × 1 (date 1, false), RETAIN × 7 | — | 1,153,279 / 1,158,341 | 0.6838 |
| 10 × 8 | AFTER | 8 / 8 | 2,278 s | 274 / 543 / 543 s | 158 (25) | RETAIN × 8 | identical on 8 / 8 dates | identical | identical |

Reading. The executed decisions are the same on every date (the false ABSTAIN fell back to the same rule
orders the clean planner retained), so the settled economics are identical to the last digit. The clean
replay is **slower**: candidate classes that the sentinel formulation declared INFEASIBLE in 0.02 s, or
solved before the false constant, now run to their 66–90 s caps (5 × 8: `stochastic` / `cvar` / `protected`
/ `hedged` 73–75 s → 93–129 s each over 8 dates; 10 × 8: `joint_recovery` 270 → 449 s, 3 → 5 time-limited).
Nothing was gained in speed and nothing should have been: the brief's criterion is that the request is
evaluated rather than falsely abstained, and the honest 1e-6 on the real objective is a tighter proof (§10).

### 12.2 Coverage matrix (AFTER)

*(filled as the runs complete)*

## 13. Genuinely coupled stress cases

*(filled as measured)*

## 14. Numerical health (largest model of each planner run; `formulation_audit`)

| request | BEFORE matrix max / finite bound max / rhs max | AFTER matrix max / bound max / rhs max | HiGHS verdicts BEFORE → AFTER |
|---|---|---|---|
| demo 5 | 10⁹ / 10⁹ / 10⁹ | 6.6 × 10⁵ / 6.6 × 10⁵ / 6.6 × 10⁵ (the flow bound: 60,000 / week × 11 weeks + stock) | joint solves "Infeasible" (Status 8) → "Optimal" (Status 7), integrality violation 0, primal infeasibility 0 |
| sample 25 | 10⁹ / 10⁹ / 10⁹ (ratio 3 × 10¹³ against the smallest planner coefficient) | 1.4 × 10⁵ (ratio 4 × 10⁹) | Infeasible → Optimal / Time limit |
| sample 50 | 10⁹ | 1.8 × 10⁵ | Infeasible → Optimal / Time limit |

The remaining max/min ratio (≈ 10⁹–10¹⁰ at planner level) is the flow bound against the planner's smallest
legitimate coefficients (holding rates ≈ 10⁻³, the timing tie-break 10⁻⁴ of price, the P1 smoothing
charge); the joint solves alone sit at 10⁵–10⁶. Two exact tightenings remain available for a later pass:
a demand-dominance stock bound (the `activation_bounds` argument) and a per-period rather than cumulative
purchasable quantity. Neither was needed for the verdicts to be right.

## 19. Release record

*(pending)*

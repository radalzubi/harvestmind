# MEIO Recovery V6

Development cycle 6 of the ZAAD full optimizer, stacked on the V5 network-recovery branch (PR #35,
verdict NEEDS FURTHER MULTI-ECHELON / RECOVERY ENGINEERING). Scope is narrow by design: true
multi-echelon placement (local versus pooled versus source versus temporary versus inherited
stock), duplicated-buffer detection, service-window-aware placement, joint network service
feasibility, an independent MEIO-style comparator, recovery as an explicit optimization regime,
per-driver recovery exit, the terminal-horizon interaction, procurement timing, and a per-cell
failure decomposition for central-plus-branch breaches. Forecasting is untouched; protection is
not lowered globally; holdout4 stays frozen and unrun.

Every adverse result is retained. No historical evidence file is rewritten.

## 0. Governance

| Item | Value |
| --- | --- |
| Branch | `claude/zaad-meio-recovery-v6` on `claude/zaad-network-recovery-v5` (tip 0708670) |
| Manifest | `docs/zaad_full/evidence/v6/PHASE0_MANIFEST.json`, committed before any engine change (e440722) |
| Development6 seed | 34001 (fresh) |
| Validation6 seeds | 35001, 35002 (fresh) |
| Holdout4 | 31001, 31002: frozen, **unrun** |
| Never tuned against | development1–5, validation1–5, holdout1–3 |
| Matrix | `v6`: the 72 v4 cells unchanged (ids 0–71) plus 25 explicit cells: a one-central / two-branch network (independent or correlated branch demand, transfer lead 1–3 reviews, constrained capacity, branch-specific SLA, central stock sufficient or absent, high / low inventory, volatile and intermittent demand, deterioration / closure / promotion / level-shift recoveries) and 26-review single-location recovery scenarios |
| Comparators | `gated_pr24`, `gated_pr30`, `gated_v4`, `gated_v5` (V5 engine, v6 rules off), `base_stock`, `echelon_base_stock` (new, independent), `stochastic`, `robust` (validation6, where solvable; time-outs kept visible) |

`protection_v6=False` reproduces the V5 engine exactly (`gated_v5`), so V6 is compared on identical
worlds except where a rule changes the world it plans against (terminal continuation).

## 1. What V6 changes

All rules are additive and switched by `Request.protection_v6`.

1. **Echelon accounting, explicit.** Every recommended protection unit is partitioned into local
   service stock (demand spread over the transfer lead at the branch), pooled network stock (the
   remainder that can sit upstream when an arc feeds the branch), source protection (declared lead
   and fill spread) and temporary risk protection (the active-driver increment). Inherited stock
   is reported separately from what ZAAD bought (benchmark rows: purchased, served, inherited
   units) and is never counted as protection.
2. **Duplicated-buffer detection.** `duplicated_buffer_units` on every SKU/location state: the
   overlap between what the branch holds beyond its local need and what the origin holds beyond
   the pooled need, counted only when the transfer lands within two reviews with capacity for at
   least one period of demand. Otherwise the branch stock is local by necessity, not duplication.
   Each count carries a sentence naming the two stocks and the arc.
3. **Recovery as an optimization regime.** When a temporary risk driver has gone quiet (RECOVER,
   or LEAN with stock above the lean baseline and no incremental protection), every candidate solve
   charges inventory held above the lean baseline plus one period of demand at twice the holding
   rate. Service floors stay; the plan runs temporary stock down through demand, cancels, defers
   and transfers instead of replenishing it. Nothing is disposed of.
4. **Per-driver recovery exit.** Late-but-full receipts (route or transit trouble) retire the
   supply driver after three clean receipts; short receipts (fill deterioration) after six; an
   overdue open order holds the driver active whatever the run says. The state reports the active
   risk source, its kind, the last adverse evidence, the clean receipts seen, the receipts needed
   and the reviews remaining until LEAN is eligible.
5. **Bounded terminal continuation.** End-of-horizon stock and arrivals due after the horizon may
   serve the demand expected during the next replenishment lead (fitted mean × (lead + 1), from the
   declared lead only) at the service margin instead of salvage. Late-horizon decisions are no
   longer artificially idle because their benefit falls outside the window. The original behaviour
   is the comparator (`gated_v5`).
6. **Joint network service frontier.** Per service: requested target, jointly feasible service (the
   joint recovery solve, which shares central stock across branches), expected achieved, incumbent
   achieved and selected achieved. When the network cannot meet every target the selector already
   ranks by priority-weighted shortfall; the frontier makes that visible per branch.
7. **Procurement-timing audit.** For every planned purchase: arrival period, the first period the
   location would otherwise run short, periods early and cash committed early. Aggregated per
   replay as `early_periods_mean` and `cash_committed_early_total`.
8. **Independent MEIO comparator.** `echelon_base_stock`: local base stock at fed branches over the
   transfer lead at the branch's own quantile; echelon base stock at the buying location over
   supplier lead + review + downstream transfer lead with the safety term pooled as the root of the
   summed branch variances; transfers refill branches subject to arc capacity and what the origin
   holds; purchases refill the echelon position. Projected deterministically and executed through
   the common model as purchase and transfer targets. It uses the fitted mean and spread only.

Not changed: the MILP objective for timing beyond the existing holding, financing and smoothing
terms; the forecast; the incumbent proxy (the operator's projected base stock).

## 2. Development6

### 2.1 Run A (`dev6_a.jsonl`: 97 cells × base_stock, echelon_base_stock, gated_v5, gated)

| Method | Rows | Median service | Mean | p10 | Meeting target | Median inventory | Quiet median | Two-branch median | Duplicated buffer (network cells) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base_stock | 97 | .896 | .851 | .568 | 27% | 1.38 | 1.71 | 2.26 | – |
| echelon_base_stock | 94 (3 time-outs) | .916 | .869 | .619 | 32% | 1.35 | 1.66 | 1.88 | – |
| gated_v5 | 97 | .918 | .890 | .689 | 41% | 1.85 | 1.82 | 2.19 | 0.0 |
| gated (V6, run A) | 97 | **.927** | .889 | .634 | **45%** | **1.72** | **1.58** | **1.97** | 4.7 |

Recovery on the 33 long-horizon cells with an activated driver: V6 returns to LEAN on 20 (61%)
against V5's 17 (52%); residual temporary protection at review 10 / 20 is 4.0 / 4.6 units
against V5's 9.8 / 8.9; median excess units at the end 15.7 against 12.7 (worse). Cost: V6
cheaper than V5 on 57 cells, dearer on 34; median cost 2146 against 2152.

Adverse, retained: V6 is below V5 by more than .02 on ten cells, all in the closure / severe /
correlated / deterioration families (91: .613 vs .791; 21: .600 vs .704; 49; 17; 20; 19 and 41;
43; 95; 71), and on every one of them V6 carried **less** inventory (21: 0.40 vs 1.45 periods).
That is the pattern the absolute rule forbids (leaner by weakening protection), so it was
ablated rule by rule before anything else (§2.2). The p10 fell from .689 to .634 for the same
reason.

### 2.2 Two-branch cells: a forecast defect, not a placement defect

Every planner breached most two-branch cells (median .880 at .95 targets; base stock .873, the
echelon comparator .913). The per-review replay of cell 72 (stable demand, fast transfer,
central 80 units) showed the south branch forecast at **mean 14.0, spread 0.0**: its first two
observations were both 14 (against a history near 20), the change-point detector opened a
two-point segment, and the segment's own standard deviation was zero. Every scenario then read
14 for the south branch, the deterministic proxy transferred exactly enough for 14, the branch
sold 20, and the selector saw no candidate that met the targets on those certain worlds
(recovery mode, incumbent retained). The failure decomposition labelled these reviews
"inventory at wrong echelon / selector retained plan", which is what they look like from the
outside and not what they are.

Fix (applies to every method, because it is a degenerate estimator and not a tuning): a young
change-point segment's spread is bounded below by the pre-change spread fading with age,
`sd ≥ sd_pre × √(1 − n/8)`, in both the fitted spread and the effective spread. A second finding
from the same replay: the "jointly feasible" service reported to the operator came from the
joint-recovery solve, which hedges the declared stress at equal weight and therefore understates
what the network can do on the fitted worlds; the frontier now comes from a service-first solve
on the fitted worlds alone.

### 2.3 Ablation of the run-A losses (one rule at a time, cells 21, 70, 68)

| Cell | V5 | V6 run A | without excess penalty | without exit rules | without continuation |
| --- | --- | --- | --- | --- | --- |
| 21 closure_recovery, no alternate | .704 / 133 | .600 / 37 | .600 / 37 | .600 / 37 | **.704 / 133** |
| 70 severe, central+branch, transfer | .768 / 206 | .896 / 215 | .896 / 215 | .896 / 215 | **.768 / 206** |
| 68 correlated, central+branch, shared route | .877 / 333 | .942 / 230 | – | – | **.877 / 333** |

(service / mean inventory value). The excess penalty and the exit rules changed nothing on these
cells; the terminal continuation alone produced both the losses and the gains. As first written it
credited *new purchases landing after the horizon* at the service margin, so the planner learned to
buy late for post-horizon demand: on the severe cell that timing happened to land after the shock
(a gain), on the closure cell it deferred the only purchases that could have beaten the closure
(a loss). That is the timing shift the absolute rule forbids when it weakens protection.

**Change kept:** continuation demand may be served by stock held to the end of the horizon and by
orders already committed (pipeline, transfers in flight), never by a plan to buy late. Re-ablated:
cell 21 **.730** (above V5's .704, inventory 115), cell 70 **.896** (gain kept), cell 68 .874 (the
late-buying gain given up, level with V5). The anti-idleness effect survives; the deferral does
not.

### 2.4 Run B (network cells after the spread guard): the guard was necessary, not sufficient

`dev6_b_network.jsonl` (29 central-plus-branch cells, 4 methods, continuation still in its first
form). The two-branch cells did not move: cell 72 stayed at .901 for base stock, V5 and V6 alike,
while the echelon comparator reached .932 at **less** inventory (1.85 against 1.98 periods). The
tie between ZAAD and base stock is the tell: ZAAD retained the projected base-stock proxy on every
review, and the proxy's transfers are a just-in-time deterministic projection, so every safety unit
the proxy buys sits at the central location one transfer lead away from the branch demand it is
meant to protect. The candidates that would have moved it could not beat the proxy on the fitted
worlds, whose spread is calibrated on the few observations available early in the replay. That is
the multi-echelon placement defect this cycle exists for, and it is in the *placement policy*, not
in the optimizer's network model.

**Change kept (v6):** the projected operator policy keeps every transfer-fed branch at a local base
stock over the transfer lead plus one review at the branch's own quantile (calibrated spread),
refilled from the projected purchases, capped by arc capacity and by what the origin holds; fed
demand counts at the origin only up to what the arc can carry per period. Local service units in
the echelon accounting span the same window. Per-cell replays before run C: cell 72 (fast transfer)
.901 → **.955** at 188 inventory value (from 223); cell 74 (two-review transfer) .882 → .915; cell
76 (capacity 12 against demand 20 per branch) .741 → .687 with central stock 450 → 141: the
capacity-constrained cell is structurally capped near .70 and the change stops the central
pile-up. A second guard came out of cell 76: in recovery mode the stress-hedged joint-recovery plan
was buying 48–51 units per review into a network that can move 24, so the recovery ranking now
takes the least inventory among candidates within the material shortfall gap.

### 2.5 Run C (`dev6_c.jsonl`: all 97 cells, placement in the proxy, restricted continuation)

92 cell×seed pairs paired (V5 and V6 both complete); 5 V6 rows **ABSTAIN** (cells 83–87, the
26-review two-branch cells) and 3 echelon comparator time-outs, all kept visible.

| Method | Rows | Median service | Mean | p10 | Meeting target | Median inventory | Quiet median | Two-branch median | Median cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base_stock | 92 | .898 | .854 | .610 | 28% | 1.42 | 1.71 | 2.34 | 2232 |
| echelon_base_stock | 92 | .920 | .873 | .623 | 33% | 1.36 | 1.65 | 1.98 | 2226 |
| gated_v5 | 92 | .933 | .895 | .693 | 43% | 1.85 | 1.82 | 2.19 | 2079 |
| gated (V6, run C) | 92 | **.957** | **.909** | .687 | **52%** | **1.77** | **1.59** | **1.98** | **2062** |

Network groups (median service / inventory): central + two branches V6 **.946 / 1.98** against V5
.895 / 2.19, echelon comparator .925 / 1.98, base stock .894 / 2.34; two-branch independent .947,
correlated .945, slow or constrained transfer .876 (V5 .832), central shortage .959 (V5 .895);
central + one branch .901 / 2.47 (V5 .877 / 2.29). Network breaches (decomposition, V6 against V5):
20 against 29; "inventory at wrong echelon" as primary cause 5 against 11. Recovery on 28
activated long-horizon pairs: returned to LEAN 50% (V5 43%), residual temporary protection at
review 20 4.0 units (V5 8.9), but median excess units at the end 30.9 (V5 14.5): the branch base
stock the proxy now keeps counts as stock above the lean baseline.

Two defects found in run C and fixed before run D:

- **ABSTAIN on the 26-review two-branch cells.** Pinning transfer targets for every period made the
  proxy MILP time out (5 s cap, gap .91 on cell 83 review 0); with transfers pinned for the first
  four periods only the same solve is optimal in .5 s. Period 0 is what executes.
- **The continuation still deferred buying on closure and severe cells.** Ablation on cells 91
  (.649 vs V5 .802) and 49 (.653 vs .727): removing the continuation alone restores V5's figures
  exactly; the excess penalty and the exit rules change nothing on them. Even restricted to end
  stock and committed orders, valuing post-horizon demand let the planner run stock down to the
  horizon and buy later, which is the wrong side of a closure. The rule is now opt-in
  (`Request.terminal_continuation`, default off) and stays in the code with its test as the
  investigated, adverse treatment of the horizon artifact.

### 2.6 Run D (`dev6_d_gated.jsonl`: V6 rerun on the frozen engine, comparators from run C)

_Filled in below._

## 3. Central-plus-branch failure decomposition

_`scripts/decompose_zaad_network_breaches.py` output on development6 and validation6._

## 4. Long-horizon recovery experiments

_First PROTECT / RECOVER / LEAN reviews, residual temporary protection at 10 and 20 reviews,
cancelled / deferred / transferred quantity, service during the unwind._

## 5. Freeze

_Commit and source hash before validation6._

## 6. Validation6

_SERVICE / INVENTORY / NETWORK / RECOVERY / COST / TIMEOUTS / ABSTENTIONS / FAILURES._

## 7. Tests

`tests/unit/test_zaad_meio_recovery_v6.py` (13): duplicate buffers only inside the window and with
capacity, none when the central is empty; comparator keeps more local on slower arcs, respects
capacity and branch SLA, cannot send what the central lacks, runs through the common model;
terminal continuation removes late-horizon idleness; late-only trouble retires after three clean
receipts and short receipts after six; an open backlog blocks the exit; exit fields on the state;
the excess penalty runs temporary stock down without breaking the floor; the timing audit; the
per-service network frontier. V5 (16) and V4 suites unchanged and passing.

## 8. Answers

_1. central+branch service · 2. total inventory · 3. quiet inventory · 4. duplicated buffers ·
5. local vs pooled · 6. recovery to LEAN · 7. procurement timing · 8. service reliability ·
9. holdout4 justified?_

## 9. Verdict

_Exactly one of: READY FOR UNTOUCHED HOLDOUT4 · NEEDS FURTHER MULTI-ECHELON / RECOVERY ENGINEERING._

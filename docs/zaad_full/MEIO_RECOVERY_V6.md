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

### 2.6 Run D (`dev6_d_gated.jsonl` merged with run C comparators as `dev6_final.jsonl`)

V6 rerun with the continuation off and the proxy transfers pinned for the first periods; the
comparators are unchanged from run C. 96 pairs; one V6 ABSTAIN remained (cell 85, 26-review
two-branch promotion: the proxy solve sat at the 5-second cap with four pinned periods), which is
why the pinned window was reduced to two periods before the freeze (cell 85 then completes at
.908; cells 72 and 74 hold at .955 and .942).

| Method | Rows | Median service | Mean | p10 | Meeting target | Median inventory | Quiet median | Two-branch median | Median cost | Mean cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base_stock | 96 | .896 | .851 | .568 | 27% | 1.37 | 1.71 | 2.19 | 2373 | 2628 |
| echelon_base_stock | 94 | .917 | .869 | .619 | 32% | 1.34 | 1.65 | 1.85 | 2320 | 2481 |
| gated_v5 | 96 | .923 | .891 | .689 | 42% | 1.82 | 1.82 | 2.11 | 2138 | 2526 |
| gated (V6) | 96 | **.949** | **.907** | **.704** | **47%** | 1.78 | 1.76 | 2.22 | 2138 | **2484** |

Paired V6 against V5: service better on 24 cells, worse on 3 (76 capacity-constrained, 71, and one
within .02); inventory lower on 14, higher on 20; cost cheaper on 6, dearer on 29 (median equal).
Network: central + two branches **.940 / 2.22** (V5 .887 / 2.11; echelon comparator .918 / 1.85),
independent branches .936, correlated .940, slow or constrained transfer .876 (V5 .832), central
shortage .963 (V5 .895); central + one branch .872 / 2.27 (V5 .877 / 2.29, flat). Network breaches
23 against 29; "inventory at wrong echelon" as the primary cause 4 against 11. Recovery on 32
activated long-horizon pairs: returned to LEAN 17 (53%) against 16 (50%); median first LEAN after
the peak review 15 against 18; residual temporary protection at 10 / 20 reviews 7.8 / 8.9, the
same as V5.

Read plainly: on development6 the placement rule fixed the two-branch family (+.05 median service
at +5% inventory on those cells, and above the independent echelon comparator on service though
not on inventory), recovery moved a little, and overall and quiet inventory did **not** fall
(−2% and −3%). Cells where V6 carries less stock and loses service: none beyond the structurally
capped cell 76.

## 3. Central-plus-branch failure decomposition

`scripts/decompose_zaad_network_breaches.py` classifies every breach review of every breached
network cell from the per-review network trace (on hand per location, transfer spend, unmet,
remaining horizon), the review status and mode, and the cell's arc. It is heuristic and says so:
it points the next diagnosis, it does not settle it. Primary cause = most frequent label over the
cell's breach reviews; outputs kept as `evidence/v6/*.network_breaches.<method>.json`.

| Validation6 (55 network cell×seed pairs) | V6 | V5 | V4 | Echelon comparator |
| --- | --- | --- | --- | --- |
| Breached network pairs | **45** | 60 | 61 | 59 |
| primary: inventory at wrong echelon | **13** | 31 | 32 | 30 |
| primary: selector retained plan | 24 | 23 | 21 | – |
| primary: insufficient total inventory | 2 | 1 | 2 | 13 |
| primary: jointly impossible | 3 | 2 | 2 | – |
| primary: scenario misspecification (closure / correlated, no alternate) | 3 | 3 | 4 | 6 |
| primary: benchmark horizon artifact | 0 | 0 | 0 | 10 |

The "wrong echelon" family, the one this cycle targeted, falls from 31 to 13 pairs. What remains is
mostly "selector retained plan" during shortfalls (24 pairs): the incumbent kept while every
candidate was rejected on confirmation or in the recovery ranking, which on development6 was
traced to the calibrated spread being too narrow early in a replay (§2.4) and is where the next
cycle should look. The echelon comparator's breaches are "insufficient total inventory" and
"horizon artifact": it carries the least stock and buys nothing for demand beyond the window.

## 4. Long-horizon recovery experiments

Validation6 26-review cells (per cell table in `evidence/v6/val6.summary.json` and the report
script output). Across the 63 long-horizon pairs with an activated driver:

| Method | Returned to LEAN after the peak | Median first PROTECT | Median first LEAN after peak | Median reviews outside LEAN | Median excess units at end | Residual temporary protection @10 / @20 |
| --- | --- | --- | --- | --- | --- | --- |
| gated_pr24 | 0 (0%) | 0 | never | 20 | 12.3 | 0 / 0 (no state machine) |
| gated_pr30 | 0 (0%) | 0 | never | 20 | 15.4 | 14.7 / 10.5 |
| gated_v4 | 27 (43%) | 6 | 20 | 10 | 15.8 | 13.9 / 6.3 |
| gated_v5 | 27 (43%) | 5 | 20 | 12 | 10.3 | 13.6 / 6.3 |
| gated (V6) | **30 (48%)** | 5 | 20 | 12 | 14.6 | 13.6 / 6.3 |

Scenario by scenario (V6 against V5, seed 35002 unless noted): supplier delay then long tail on
the two-branch network (cell 83) .845 vs .791 with unmet after the peak 0 vs 6; route closure with
alternate (84) .556 vs .569 (both seeds level, unmet after the peak equal); promotion end (85) not
paired (V6 ABSTAIN on one seed, see §6); demand level up (86) .922 vs .868, unmet after the peak 42
vs 125; demand level down (87) 1.000 vs .934 at 6.55 vs 4.97 periods (the placement rule holds
branch base stock while the level falls: **more** stock, retained as adverse); central shortage
then transfer response (81) .914 vs .873 at 1.59 vs 1.13. Residual temporary protection declines
from 13.6 units at review 10 to 6.3 at review 20 for V4, V5 and V6 alike: the exit rules changed
when the driver retires on the late-only and backlog cases, but on these cells the driver is
fill deterioration (six clean receipts) or demand, so the median path is unchanged. Recovery
reaches LEAN on 48%: better than V5's 43% and the V5 validation figure of 32%, still **not a
majority**. Cancelled and deferred quantities are not separately recorded on the benchmark rows
(the ledger carries keep fees only); transfer spend is.

## 5. Freeze

`evidence/v6/DESIGN_FREEZE.json`: commit c972c5d, `zaad/full` source hash 0739690bb2856a1b…,
engine flags `protection_v6=True`, `terminal_continuation=False`. One post-development change is
recorded in the file (transfer pinning reduced from four periods to two after cell 85 sat at the
solve cap; spot-checked on cells 72, 74, 85). No engine change after the record.

## 6. Validation6

`evidence/v6/val6.jsonl`: 97 cells × seeds 35001, 35002 × 9 methods = 1746 rows. Nothing was tuned
on it. Summary `val6.summary.json`.

### TIMEOUTS / ABSTENTIONS / FAILURES (every row counted)

| Method | Rows | COMPLETE | TIME_LIMIT | ABSTAIN | INFEASIBLE |
| --- | --- | --- | --- | --- | --- |
| base_stock | 194 | 194 | 0 | 0 | 0 |
| echelon_base_stock | 194 | 192 | 2 | 0 | 0 |
| stochastic | 194 | 154 | 39 | 0 | 1 |
| robust | 194 | 112 | 82 | 0 | 0 |
| gated_pr24 | 194 | 193 | 0 | 1 | 0 |
| gated_pr30 | 194 | 194 | 0 | 0 | 0 |
| gated_v4 | 194 | 193 | 0 | 1 | 0 |
| gated_v5 | 194 | 192 | 0 | 2 | 0 |
| gated (V6) | 194 | 192 | 0 | 2 | 0 |

The paired tables below use the 191 cell×seed pairs where V5 and V6 both completed; the
stochastic and robust rows are their own completed subsets (robust times out on 82 rows at the
5-second cap, mostly the long-horizon cells) and are not paired where a row is missing.

### SERVICE

| Method | Median | Mean | p10 | Meeting target | Avoidable breaches (summary) | Breaches | Median stockout periods |
| --- | --- | --- | --- | --- | --- | --- | --- |
| base_stock | .901 | .852 | .614 | 29% | 58 | 138 | 5 |
| echelon_base_stock | .922 | .869 | .641 | 35% | 47 | 126 | 4 |
| stochastic (154) | .915 | .870 | .649 | 39% | 38 | 94 | 3 |
| robust (112) | .956 | .909 | .667 | 58% | 11 | 47 | 1 |
| gated_pr24 | .907 | .858 | .645 | 31% | 54 | 133 | 5 |
| gated_pr30 | .936 | .874 | .649 | 39% | 40 | 120 | 3 |
| gated_v4 | .935 | .880 | .658 | 40% | 38 | 117 | 3 |
| gated_v5 | .937 | .888 | .699 | 40% | 38 | 116 | 3 |
| gated (V6) | **.953** | **.903** | **.708** | **48%** | **23** | **101** | **2** |

Per seed: 35001 V6 .954 / V5 .938 / PR30 .940; 35002 V6 .946 / V5 .935 / PR30 .934. Paired V6
against V5: service better on 38 pairs, worse on 9. Breach classes: MODEL_FAILURE 55 and
UNAVOIDABLE 23 are shared by every core method; V6 turns 15 AVOIDABLE breaches into MET.

### INVENTORY

| Method | Median inventory (periods) | Mean | Quiet-cell median (56 pairs) | Two-branch median (33) | Purchase / demand |
| --- | --- | --- | --- | --- | --- |
| base_stock | 1.40 | 2.37 | 1.60 | 1.83 | .865 |
| echelon_base_stock | 1.28 | 2.19 | 1.32 | **1.44** | .914 |
| stochastic | 1.22 | 1.86 | 1.18 | 1.91 | .763 |
| robust | 2.79 | 3.38 | 3.10 | 5.92 | .908 |
| gated_pr24 | 1.34 | 2.25 | 1.54 | 1.79 | .842 |
| gated_pr30 | 1.65 | 2.44 | 1.60 | 1.79 | .855 |
| gated_v4 | 1.65 | 2.39 | 1.60 | 1.79 | .852 |
| gated_v5 | 1.64 | 2.36 | 1.60 | 1.79 | .865 |
| gated (V6) | 1.67 | 2.40 | 1.60 | 1.81 | .879 |

Total inventory did **not** fall: median 1.67 against V5 1.64 (+2%), quiet cells unchanged at
1.60 (every gated method sits on the same lean baseline there), two-branch cells 1.81 against
1.79. Paired: V6 lower on 33 pairs, higher on 34. Echelon accounting on the 56 V6 network pairs:
local service units 16.8, pooled 24.2, source 0, temporary 0 (mean over reviews); duplicated
buffer units 6.0 per review on average, present in 75% of reviews. The comparators report 0
because the diagnostic is v6-only, so the duplicated-buffer *reduction* cannot be shown against
V5 on this run: what can be said is that V6 places 16.8 of its 41 protection units locally and
still finds 6 units buffered twice on the typical network review. Purchased units on network
cells: V6 435 against V5 401 (+8%), served 451 against a shared 142 inherited.

### NETWORK (median service / inventory)

| Group | Pairs | base_stock | echelon_base_stock | gated_pr24 | gated_pr30 | gated_v4 | gated_v5 | gated (V6) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| central + one branch | 22 | .824 / 1.81 | .877 / 2.09 | .845 / 1.81 | .826 / 1.96 | .845 / 1.91 | .816 / 1.89 | **.936 / 1.90** |
| central + two branches | 33 | .882 / 1.83 | .932 / 1.44 | .882 / 1.79 | .895 / 1.79 | .890 / 1.79 | .890 / 1.79 | **.952** / 1.81 |
| two-branch, independent demand | 31 | .895 | .932 / 1.44 | .895 | .903 | .897 | .897 | **.960 / 1.68** |
| two-branch, correlated demand | 2 | .821 | .886 | .821 | .829 | .829 | .829 | **.913** |
| two-branch, slow or constrained transfer | 6 | .854 / 1.94 | .859 / 1.63 | .854 | .854 | .854 | .854 | **.871 / 1.44** |
| central shortage → transfer response | 2 | .913 / 1.37 | .943 / 1.05 | .913 | .919 | .919 | .919 | **.964 / 1.46** |
| two locations | 24 | .890 | .912 | .895 | .947 | .950 | .954 | .954 |
| closure / deterioration recovery | 32 | .790 | .803 | .789 | .818 | .818 | .833 | **.840** |
| severe / correlated supply | 20 | .637 | .656 | .641 | .642 | .683 | .668 | .668 |
| 26-review cells | 23 | .895 | .921 | .895 | .895 | .897 | .897 | **.928** |

Central-plus-branch service moves from .816 (V5) to .936 on the one-branch network and from .890
to .952 on the two-branch network at the same inventory; against the independent echelon
comparator V6 is above on service (.952 vs .932) and below on inventory (1.81 vs 1.44 periods).
Pooled stock is used where it is physically valid: on the slow or constrained arcs V6 holds
**less** (1.44 vs 1.94) and serves more; on the fast arcs it holds local base stock at the
branches and slightly more in total. The severe and correlated family is unchanged from V5
(.668), so no disruption protection was traded for the inventory statistics.

### COST

| Method | Median cost | Mean cost | Cheaper / dearer than V5 (pairs) | Service better / worse than V5 | Inventory lower / higher than V5 |
| --- | --- | --- | --- | --- | --- |
| base_stock | 2113 | 2582 | 32 / 154 | 32 / 127 | 108 / 75 |
| echelon_base_stock | 2100 | 2497 | 52 / 137 | 65 / 103 | 138 / 51 |
| gated_pr24 | 2094 | 2554 | 45 / 141 | 33 / 127 | 120 / 63 |
| gated_pr30 | 2051 | 2519 | 59 / 125 | 47 / 86 | 56 / 128 |
| gated_v4 | 2051 | 2502 | 41 / 91 | 23 / 47 | 34 / 92 |
| gated_v5 | 2067 | 2488 | – | – | – |
| gated (V6) | 2067 | **2461** | 50 / 18 | 38 / 9 | 33 / 34 |

Median cost equal to V5, mean 1% lower; V6 is dearer than V5 on 50 pairs and cheaper on 18 by
small amounts (the branch base stock), and better on service on 38 pairs against 9. Procurement
timing (V6 only): orders land 0.79 periods early on average with 11,900 of cash committed early
per replay; no comparator figure exists because the audit is v6-only.

### Against the V6 targets

| Target | Validation6 | Met |
| --- | --- | --- |
| Median service ≈ ≥ .93 | .953 (V5 .937, V4 .935) | yes |
| Avoidable breaches no worse than V4 / V5 | 23 vs 38 / 38 | yes |
| p10 service not materially degraded | .708 (V5 .699) | yes |
| Inventory materially below V4 / V5 | 1.67 vs 1.65 / 1.64 (+2%) | **no** |
| Quiet-cell inventory materially below V5 | 1.60 = 1.60 | **no** |
| Duplicated network buffer materially reduced | 6.0 units/review on V6; not measurable on V5 | **not shown** |
| Central + branch service materially above .756 | .936 / .952 | yes |
| Fewer avoidable network breaches | 45 vs 60 network breaches; wrong-echelon 13 vs 31 | yes |
| Pooled stock used where physically valid | slow / constrained arcs: less stock, more service | yes |
| Majority of temporary-risk long-horizon cells return to LEAN | 48% (V5 43%) | **no** |
| Residual temporary protection declines steadily | 13.6 → 6.3 units, same as V4 / V5 | yes, unchanged |
| Total modelled cost not materially worse | median equal, mean −1% | yes |
| No weakening of real disruption protection | severe / correlated .668 = V5; closure family +.007 | yes |

## 7. Tests

`tests/unit/test_zaad_meio_recovery_v6.py` (16): duplicate buffers only inside the window and with
capacity, none when the central is empty; the comparator keeps more local on slower arcs, respects
capacity and branch SLA, cannot send what the central lacks, runs through the common model;
terminal continuation removes late-horizon idleness in the model (the rule stays opt-in);
late-only trouble retires after three clean receipts and short receipts after six; an open backlog
blocks the exit; exit fields on the state; the excess penalty runs temporary stock down without
breaking the floor; the timing audit; the per-service network frontier; two identical post-change
points never make demand certain; the v6 proxy keeps fed branches at a local base stock, caps
transfers by capacity, buys less on a constrained arc, and serves both branches on a calm network.
V5 (16), V4 and the full ZAAD unit set: 228 passed, 1 skipped. `ruff` clean on every touched
file; `mypy` at the 8 pre-existing stub errors. Benchmark integrity guards unchanged (frozen
splits refuse filters, limits and stale manifests; the v6 filters are refused there too).

## 8. Answers

1. **Did central+branch service materially improve?** Yes. Validation6 median .936 on the
   one-branch network (V5 .816) and .952 on the two-branch network (V5 .890), above the
   independent echelon comparator on service (.932) at the same inventory as V5; network breaches
   45 against 60, wrong-echelon breaches 13 against 31.
2. **Did total inventory materially fall?** No. Median 1.67 periods against V5's 1.64 and V4's
   1.65; paired lower on 33 cells, higher on 34.
3. **Did quiet inventory fall?** No. 1.60 for V4, V5 and V6 alike: quiet cells sit on the lean
   baseline in all three, and V6 changes nothing there.
4. **Did duplicated buffers fall?** Not shown. The diagnostic exists only on V6 (6.0 units per
   review, in 75% of network reviews). The wrong-echelon breach family fell from 31 to 13 pairs,
   which is the behaviour the diagnostic was built to catch, but a V5 baseline of the units
   themselves was not produced.
5. **Does the optimizer distinguish local vs pooled stock correctly?** Partly. The projected policy
   now holds local base stock over transfer lead + one review at each fed branch and pools the
   rest; on slow or constrained arcs V6 holds less stock (1.44 vs 1.94) and serves more, on fast
   arcs it holds slightly more in total than V5. The echelon comparator reaches .932 at 1.44
   periods on the two-branch cells, so a leaner placement that keeps V6's service exists.
6. **Did recovery-to-LEAN materially improve?** Marginally: 48% of activated long-horizon pairs
   against 43% for V4 and V5 (and 32% on the V5 validation matrix). Residual temporary protection
   declines on the same path as V4 and V5. Not a majority.
7. **Did procurement timing improve?** Measured, not shown to improve: V6 orders land 0.79 periods
   early on average with ~11,900 of cash committed early per replay; no comparator figure exists
   because the audit is v6-only, and no timing preference was added to the objective.
8. **Did service reliability remain intact?** Yes, and improved: avoidable breaches 23 against 38,
   p10 .708 against .699, severe and correlated cells level with V5, closure family +.007, per seed
   consistent, median cost equal and mean cost 1% lower.
9. **Is holdout4 now justified?** No. Three of the qualification criteria are unmet (total
   inventory, quiet inventory, majority recovery to LEAN) and one is unshown (duplicated buffers).
   The design that would justify the holdout keeps V6's placement and service and takes the
   inventory the echelon comparator shows is available.

## 9. Verdict

**NEEDS FURTHER MULTI-ECHELON / RECOVERY ENGINEERING**

Holdout4 (31001, 31002) remains frozen and unrun.

Where the next cycle should look, from the retained evidence: (1) the calibrated spread early in
a replay, which keeps the confirmation worlds too narrow for any candidate to beat the proxy and
leaves "selector retained plan" as the dominant network breach cause; (2) a leaner local base
stock at fast-arc branches, since the echelon comparator holds 1.44 periods at .932 where V6 holds
1.81 at .952; (3) recovery exit for fill-deterioration and demand drivers, which set the median
recovery path and were not changed by the late-only and backlog rules; (4) recording cancelled
and deferred quantities on the benchmark rows so the unwind can be measured in actions, not only
in stock; (5) a V5 baseline for the duplicated-buffer diagnostic so its reduction can be shown.

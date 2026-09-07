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

### 2.3 Run B (network cells after the guard)

_`dev6_b_network.jsonl`: the 29 central-plus-branch cells rerun._

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

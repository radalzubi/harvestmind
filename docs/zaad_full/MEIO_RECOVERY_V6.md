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

_Filled in from `evidence/v6/dev6_a.jsonl` (base_stock, echelon_base_stock, gated_v5, gated)._

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

# Network Recovery V5

Development cycle 5 of the ZAAD full optimizer, stacked on the calibrated-protection V4 branch
(PR #33, verdict NEEDS FURTHER CALIBRATION ENGINEERING). Scope: true multi-echelon placement,
network risk pooling, the central-plus-branch failure family, explicit recovery, source-specific
protection half-life, procurement timing, marginal inventory value, intermittent demand, a formal
state machine and a selector rejection audit. Holdout4 stays frozen and unrun.

Every adverse result in this cycle is retained below. Nothing in the frozen splits was touched.

## 0. Governance

| Item | Value |
| --- | --- |
| Branch | `claude/zaad-network-recovery-v5` on `claude/zaad-calibrated-protection-v4` |
| Manifest | `docs/zaad_full/evidence/v5/PHASE0_MANIFEST.json` (committed before any engine change, aceabf0) |
| Starting commit | 060c881 (validation4 evidence and V4 verdict) |
| Development5 seed | 32001 (new, no overlap with any earlier split) |
| Validation5 seeds | 33001, 33002 (new) |
| Holdout4 | 31001, 31002: frozen, **unrun** |
| Consumed, never tuned against | development1–4, validation1–4, holdout1–3 |
| Comparators | `gated_pr24` (frozen PR24 profile), `gated_pr30` (`protection_decay=False, carry_incumbent=False, protection_v5=False`), `gated_v4` (`protection_v5=False`), `base_stock`, plus stochastic / robust where the matrix runs them |

`protection_v5=False` reproduces the V4 engine exactly on every rule below, so V4 and V5 are
compared on identical worlds except where the rule itself changes the world (overdue orders).

## 1. What V5 changes (and what it does not)

V5 does not redesign the optimizer. The MILP, the settlement, the causal replay and the
incumbent-first gate are unchanged. The rules below are additive and each one is switched by
`Request.protection_v5`.

1. **Recency-weighted supply state.** The risk *state* of a source follows its last six receipts
   (`RECENT_RECEIPTS`), the *distribution* keeps the whole record. A route that closed and
   reopened shows clean recent receipts long before its full history looks clean, so protection
   retires on the source's own evidence (source-specific half-life) rather than on a global clock.
2. **Overdue orders are late now, not later.** An open order past the declared lead-time tail
   counts as a late record in the recent window. Before this, a closure was invisible to the
   risk state until the dead orders finally landed.
3. **Overdue-order survival in the worlds.** With too little history for a conditional ETA, an
   order already past the declared tail is no longer assumed to land next period forever. Each
   overdue period halves the chance it lands inside the horizon; the remaining mass stays outside
   it. This is what lets the planner source from an alternate during a closure instead of waiting.
4. **Flexibility credit only inside the service window.** An approved alternate earns resilience
   credit only if it can arrive inside the replenishment window with at least half the window's
   demand in capacity. A slow or tiny alternate is a theoretical one and earns nothing.
5. **Inventory-burden ranking within a cost band.** Among candidates whose hedged cost is within
   `downside_cost_tolerance / 5` of the cheapest, the one carrying the least inventory wins.
6. **Echelon accounting.** Every recommended protection unit is partitioned into local service
   stock (transfer-lead demand spread at the branch), pooled network stock (the remainder that
   can sit upstream), source protection (declared lead and fill spread) and temporary risk
   protection (the active-driver increment). The partition never exceeds the recommendation.
7. **Formal state machine with transition reasons.** LEAN / PROTECT / RECOVER with hysteresis,
   each transition carrying a sentence naming the driver (or the quiet run and the units left to
   drain). ALLOCATE remains the selector's mode when targets are jointly infeasible.
8. **Selector rejection audit with deltas.** Every rejected candidate records its service delta per
   service, fitted cost delta, inventory delta and stress-service pairs against the incumbent,
   next to the reason.
9. **Unit-based inventory metrics.** Purchased, served and inherited units, purchase-to-demand
   ratio and inventory turn periods on every benchmark row, so "excess" can be attributed to
   buying rather than to inherited opening stock.

Not done in this cycle: a re-derivation of the MILP objective for procurement timing, or a change
to the intermittent demand model beyond V4's occurrence × capped size mixture (its unit and period
service are reported, not re-modelled).

## 2. Diagnosis that drove the cycle

### 2.1 Validation4 central-plus-branch failures

The V4 report listed central+branch cells below target. Re-reading them by cause:

- **Structural, all methods.** Transfer-constrained cells (branch transfer capacity 12 against
  demand 20) sit at ~.70 for every planner including base stock; closure cells without an
  alternate cannot be served. These are UNAVOIDABLE under the scenario, not engine failures.
- **Intermittent central cells.** Service is bounded by the occurrence model; the V4 report's
  unit-and-period reporting applies.
- **One real regression.** Cell 70 (severe delay plus transfer, high inventory): `gated_pr24`
  .95 at 3.5 periods against V4 .66 at 1.9 periods. V4 traded service for inventory where the
  transfer arc could have carried the service. This cell family is the target of rules 1–3 and 6.

### 2.2 Development5 cell 42: the idle planner

`closure_recovery` with an approved alternate supplier (capacity 50/period against demand ~19.5):
every planner, base stock included, scored .44–.47 with 12–15 stockout periods out of 20.
Per-review replay showed the mechanism. The main route closes at period 1 (fill 0, +10 days);
the planner buys from main through review 3, then buys **nothing for eight reviews** (4–11) while
the shelf is empty, then resumes at 12 and only reaches the alternate at 13. The dead orders had
too little history for a conditional ETA, so every world assumed they would land next period; the
incumbent and every candidate agreed, so "no candidate materially improves service" was true
inside the model and false in the world. The supply state stayed LEAN (activity 0) throughout
because only *arrived* receipts fed it.

With rules 2 and 3 the same cell sources the alternate from review 6 and holds it through the
closure. Reviews 4–5 remain idle: an order becomes "overdue" only once it is past the declared
tail, which is the honest earliest point.

## 3. Development5, run A (engine before the overdue rules)

72 cells × 5 methods, seed 32001, `docs/zaad_full/evidence/v5/dev5_a.jsonl`.

| Method | Median service | Median inventory (periods) | Quiet-cell inventory | Avoidable breaches | Breaches (72) |
| --- | --- | --- | --- | --- | --- |
| base_stock | .919 | 1.35 | .40 | 10 | 44 |
| gated_pr24 | .937 | 1.22 | .40 | 7 | 41 |
| gated_pr30 | .951 | 1.86 | .71 | 3 | 37 |
| gated_v4 | .947 | 1.90 | .69 | 4 | 38 |
| gated (V5, run A) | .947 | 1.75 | .67 | 4 | 38 |

Paired, V5 against V4 on 71 comparable cells: inventory lower on 56, higher on 15; service
losses 26 against wins 17 (mostly quiet cells where V5 accepts .979 instead of .991 at a .95
target, holding 1.94 instead of 2.63 periods). Against PR30: cost wins 38 / losses 33.

Adverse: quiet-cell inventory .67 is still far from the .50–.60 target; median service .947 sits
just under the .95 reference; 26 MODEL_FAILURE classifications are shared by every method
(scenario families where the modelled state cannot be served).

## 4. Development5, run B (engine with rules 2 and 3)

`dev5_b.jsonl`: gated and base_stock rerun on the same 72 cells; the three frozen comparators are
unaffected by V5-gated rules and are reused from run A (`dev5_merged.jsonl`).

| Method | Median service | Mean service | Median inventory | Mean inventory | Median cost |
| --- | --- | --- | --- | --- | --- |
| base_stock | .919 | .863 | 1.17 | 2.98 | 1762 |
| gated_pr24 | .937 | .877 | 1.22 | 2.93 | 1730 |
| gated_pr30 | .951 | .891 | 1.85 | 3.06 | 1705 |
| gated_v4 | .947 | .893 | 1.90 | 2.99 | 1683 |
| gated (V5, run B) | **.953** | **.905** | **1.75** | **2.89** | 1707 |

Run A → run B, gated, cells that moved by .02 or more:

| Cell | Family | Run A | Run B | V4 |
| --- | --- | --- | --- | --- |
| 42 | closure_recovery, alternate supplier | .443 / 0.12 | **.743 / 0.30** | .454 / 0.12 |
| 52 | closure_recovery, constrained transfer | .690 / 1.28 | **.879 / 1.00** | .689 / 1.30 |
| 21 | closure_recovery, no alternate | .497 / 0.20 | **.675 / 1.14** | .497 / 0.20 |
| 56 | closure_recovery, two locations, constrained transfer | .883 / 6.01 | **.972 / 5.31** | .883 / 6.01 |
| 49 | severe, alternate route | .560 / 0.55 | **.730 / 0.83** | .560 / 0.55 |
| 63 | correlated, two locations, shared route | .563 / 2.42 | .640 / 2.24 | .563 / 2.42 |
| 58 | correlated, no alternate | .617 / 0.54 | .691 / 0.65 | .669 / 0.67 |
| 68 | correlated, central+branches, shared route | .712 / 3.72 | .736 / 3.78 | .712 / 3.72 |
| 20, 43 | deterioration_recovery | .815 / 2.65, .861 / 0.40 | .837 / 2.46, .881 / 0.46 | .815, .849 |
| 19, 41 | correlated, no alternate / shared route | .727 / 0.23 | **.685 / 0.32** | .727 / 0.27 |
| 71 | correlated, alternate route | .779 / 1.23 | **.731 / 1.23** | .725 / 1.24 |
| 70 | severe, central+branches, transfer | .828 / 2.17 | **.777 / 2.12** | .828 / 2.17 |
| 17 | severe, no alternate | .495 / 0.18 | **.385 / 0.14** | .495 / 0.18 |

Adverse and retained: the four **severe / correlated** cells got worse (17, 70, 19/41, 71). The
service figure is the closure-family gain minus a severe-family loss. Quiet-cell inventory is
unchanged at .67 (V4 .69, PR30 .71); central+branches median service on the 10 such cells is
.785 (V4 .802, PR30 .821, PR24 .865), i.e. **not improved** in run B.

### 4.1 Why the severe cells got worse, and what is and is not fixable

Per-review replay of cell 70 (`diag3`, review 8): the one receipt that has arrived since the
shock took 49 days; five orders are outstanding at 14–42 days. The censored Kaplan–Meier ETA
therefore says, correctly, "orders from this source take 49 days now" and sequences the open
orders one period apart at half fill. New orders inherit the same 7-period lead. The replay's
planning horizon at review 8 of a 12-review cell is **4 periods** (the replay horizon shrinks by
one each review so that no financial data is fabricated; `horizon_note` in every replay). With a
7-period lead and a 4-period window no purchase can land inside the window, so every candidate
plans the same zero, the recovery ranking finds nothing "materially better" and the base-stock
incumbent (which counts the dead pipeline as inventory position) is retained.

Two further V5 rules were added on top of run B for the part that *is* the engine's:

- **Recent fill run.** A run of short receipts (three or more recent records, at least half of
  them short) sets the fill expectation for new and open orders, even when the whole record is
  too short (< 6 records) or too long (diluted) to show it. Before this, five consecutive
  half-filled receipts left the planner expecting the quoted .97.
- **Backlog-implied lead.** When a source's recent orders are all late and some are already
  overdue, its outstanding orders are assumed to ship in sequence: no younger order can land
  before the oldest overdue one would. The freshest order stops being "due next period" while
  the backlog stands, which is what let cell 42 reach its alternate one review earlier (5 not 6).

The horizon interaction is **not** changed: extending the replay window would fabricate
receivables and payments the operator has not supplied, which the replay design forbids, and
production replanning already takes a fresh full-horizon snapshot. It is recorded here as a
benchmark property that penalises every method equally in the late reviews of long shocks; PR24's
.976 on cell 70 comes from buying 47 units at review 0 and carrying 3.8 periods, not from
recovery intelligence.

## 4.2 Development5, run C (frozen engine)

`dev5_c.jsonl` (gated, base_stock) merged with the run A comparators (`dev5_merged_c.jsonl`,
summary `dev5_c.summary.json`).

| Method | Median service | Mean service | Median inventory | Quiet-cell inventory | Avoidable | Breaches (72) | Emergency review share |
| --- | --- | --- | --- | --- | --- | --- | --- |
| base_stock | .919 | .863 | 1.17 | .40 | 11 | 44 | .20 |
| gated_pr24 | .937 | .877 | 1.22 | .40 | 8 | 41 | .24 |
| gated_pr30 | .951 | .891 | 1.85 | .71 | 4 | 37 | .34 |
| gated_v4 | .947 | .893 | 1.90 | .69 | 5 | 38 | .34 |
| gated (V5, frozen) | **.953** | **.907** | **1.75** | .67 | **3** | **36** | .37 |

Run B → run C, gated: 21 (.675 → .752), 42 (.743 → .784), 52 (.879 → .906), 20 (.837 → .866),
71 (.731 → .782, now above V4's .725); 19 and 41 (.685 → .643) moved further down. Cells 17 and
70 are unchanged from run B. Breach classes are identical across methods except AVOIDABLE / MET
(25 MODEL_FAILURE and 8 UNAVOIDABLE are scenario properties).

Recovery on the 20 long-horizon cells (protection trajectories): V5 returns to LEAN on 35% (V4
35%, PR30 0%, PR24 0%); median reviews spent in PROTECT 15 (V4 12) because overdue orders now
keep the supply state active while a backlog stands; median excess units remaining at the end
11.7 (V4 15.0).

Against the cycle targets on development5: median service .953 (target ≈ .93, met); avoidable
3 against PR30's 4 (met); median inventory 1.75 against 1.79–1.81 (−2 to −3%, not material);
quiet-cell inventory .67 (target .50–.60, **not met**); central+branches median service .778
against V4 .802 (**not improved**); recovery to LEAN 35% (**not "mostly"**).

## 5. Freeze

`docs/zaad_full/evidence/v5/DESIGN_FREEZE.json`.

- **Freeze 1**: commit 1afdb67, `zaad/full` source hash fc851a49af34320d…, recorded before
  validation5 was launched.
- **Validation5 run 1 crashed** at 657 of 1008 rows (cell 46, seed 33002, gated): the V5
  inventory-burden band was `cheapest × (1 + tol/5)`; with a negative hedged cost (closing assets
  above spend) the band lies below the cheapest candidate and `min()` of an empty band raised.
  The run is retained as `val5_run1_crashed.jsonl` and is **not** used for selection. On its 93
  complete gated cell×seed pairs it read V5 .956 / V4 .961 median service, for the record.
- **Crash-only fix**: the band is now `cheapest + tol/5 × max(|cheapest|, 1)` and falls back to
  the feasible set if empty (identical behaviour for positive costs). Regression test added.
- **Freeze 2**: the commit after the fix, recorded in the same file with the run-1 outcome;
  validation5 rerun in full as `val5.jsonl`. No engine change after this record.

## 6. Validation5

`docs/zaad_full/evidence/v5/val5.jsonl` (run 2 on freeze 2): 72 cells × seeds 33001 and 33002 ×
7 methods = 1008 rows, no failures on the five core methods. `stochastic` timed out on 21 rows and
`robust` on 44 (HiGHS time limit); their figures below are on their own completed rows and are
not paired against the others where a row is missing. Summary: `val5.summary.json`.

Validation5 is the pre-holdout selection run. Nothing was tuned on it.

## 7. Report by dimension

### SERVICE

| Method | Median service | Mean service | p10 service | Cell×seed pairs meeting target | Median stockout periods | Avoidable breaches | Rows |
| --- | --- | --- | --- | --- | --- | --- | --- |
| base_stock | .900 | .840 | .588 | 34% | 3 | 39 | 144 |
| stochastic | .919 | .841 | .608 | 31% | 3 | 45 | 130 |
| robust | .959 | .887 | .646 | 56% | 1 | 13 | 106 |
| gated_pr24 (PR24) | .899 | .846 | .639 | 31% | 3 | 42 | 144 |
| gated_pr30 (PR30) | .931 | .862 | .614 | 43% | 2 | 24 | 144 |
| gated_v4 (V4) | **.945** | .871 | .613 | 45% | 2 | 23 | 144 |
| gated (V5) | .937 | **.883** | **.694** | 45% | 2 | 23 | 144 |

Breach classes are identical for the five core methods except AVOIDABLE / MET (44 MODEL_FAILURE
and 12 UNAVOIDABLE are scenario properties). Per seed: 33001 V5 .929 / V4 .933 / PR30 .937;
33002 V5 .947 / V4 .949 / PR30 .912.

V5 against V4, paired on 144 cell×seed pairs: service wins 24, losses 24, ties 96. The mean and
the tenth percentile move up because the closure-recovery family moves up; the median moves down
.008 because three quiet-adjacent cells give back a point or two of service above target and
the severe family (cell 17, both seeds) gives back .07.

### INVENTORY

| Method | Median inventory (periods) | Mean inventory | Quiet-cell median (34 pairs) | Median purchase / demand | Median working capital |
| --- | --- | --- | --- | --- | --- |
| base_stock | 1.50 | 2.66 | .47 | .886 | 154 |
| stochastic | 1.33 | 1.87 | .73 | .628 | 145 |
| robust | 3.34 | 3.27 | 3.47 | .797 | 343 |
| gated_pr24 (PR24) | 1.50 | 2.45 | .47 | .800 | 159 |
| gated_pr30 (PR30) | 2.02 | 2.66 | .99 | .841 | 222 |
| gated_v4 (V4) | 1.88 | 2.70 | .80 | .851 | 213 |
| gated (V5) | 1.87 | 2.69 | .80 | .853 | 202 |

Paired against V4: inventory lower on 69 pairs, higher on 36. Against PR30: lower on 82, higher
on 60. The **quiet-cell inventory does not move** on validation5 (.80 for both V4 and V5,
against PR30's .99 and PR24's .47): the burden ranking within the cost band changes the winner
on development5's quiet cells but on the validation seeds the candidates inside the band carry
the same stock. Working capital is 5% below V4 at the median.

### ECONOMICS

| Method | Median cost | Mean cost | Cost cheaper / dearer than V4 (pairs) | Service better / worse than V4 | Inventory lower / higher than V4 |
| --- | --- | --- | --- | --- | --- |
| base_stock | 1849 | 2077 | 35 / 108 | 42 / 88 | 94 / 45 |
| stochastic | 1688 | 1864 | 68 / 55 | 32 / 93 | 103 / 27 |
| robust | 1594 | 1734 | 42 / 58 | 55 / 29 | 39 / 67 |
| gated_pr24 (PR24) | 1819 | 2030 | 52 / 92 | 38 / 92 | 99 / 43 |
| gated_pr30 (PR30) | 1793 | 2011 | 78 / 64 | 69 / 45 | 58 / 83 |
| gated_v4 (V4) | 1790 | 2004 | – | – | – |
| gated (V5) | **1780** | **1977** | 72 / 44 | 24 / 24 | 69 / 36 |

V5 is the cheapest gated planner at the median and the mean; robust is cheaper on its completed
subset because its 44 time-outs are concentrated in the expensive long-horizon cells. Against
PR30 (144 pairs, from `val5.summary.json`): cost wins 75 / losses 67, service wins 56 / losses 58.

### NETWORK

| Group | Pairs | PR24 service / inventory | PR30 | V4 | V5 |
| --- | --- | --- | --- | --- | --- |
| central + branches | 20 | .750 / 2.06 | .739 / 2.20 | .751 / 2.19 | **.756 / 2.11** |
| two locations | 24 | .876 / 4.75 | .896 / 4.53 | **.951** / 4.12 | .948 / **4.06** |
| transfer alternatives (all networks) | 30 | .947 / 4.12 | .920 / 3.90 | **.956** / 3.88 | .953 / **3.86** |
| closure / deterioration recovery | 22 | .798 / 1.75 | .802 / 1.74 | .807 / 1.60 | **.835** / 1.95 |
| severe / correlated supply | 20 | .642 / 0.90 | .646 / 1.10 | .649 / 1.10 | **.670** / 1.15 |
| intermittent demand | 24 | .941 / 6.13 | .875 / 6.12 | .989 / 6.06 | **1.000 / 5.93** |

Central-plus-branches moves from .751 to .756 with .08 periods less inventory: **not a material
improvement**. The families the rules were built for move: closure / deterioration recovery
+.028 at the median (cells 52, 42, 21 and 49 gain .13 to .36 on both seeds), severe / correlated
+.021 at the median while cell 17 (severe, no alternate, near-zero stock) loses .07 on both seeds
and cell 70 / 33002 loses .04. Intermittent cells sit at 5.9–6.1 periods for every gated method;
that stock is inherited opening stock, not purchasing (purchase-to-demand on those cells is below
1 for all methods), as in the V4 analysis.

Cells that got worse than V4 by more than .02 (10 of 144 pairs): 17 (both seeds), 18 / 33001
(partial supply, V5 holds .75 periods against V4's 2.03 and gives back .05), 68 / 33002, 70 /
33002, 50 / 33002, 48 / 33001, 71 / 33001, 56 / 33001, 51 / 33002. Cells that got better by more
than .02: 52 (both), 49 (both), 42 (both), 70 / 33001, 21 / 33001, plus 8 more.

### RECOVERY (40 long-horizon cell×seed pairs with an activated driver)

| Method | Returned to LEAN after the peak | Median reviews outside LEAN | Median excess units at the end |
| --- | --- | --- | --- |
| gated_pr24 (PR24) | 0 (0%) | 20 | 14.1 |
| gated_pr30 (PR30) | 0 (0%) | 20 | 19.2 |
| gated_v4 (V4) | 12 (30%) | 15 | 12.9 |
| gated (V5) | 13 (32%) | 15 | 14.1 |

Recovery reaches LEAN on a third of the disrupted long-horizon cells, the same as V4. Overdue
orders now keep the supply state active while a backlog stands, which is correct while it
stands, but the state only retires once the backlog has landed *and* six clean receipts follow
(`RECENT_RECEIPTS`), so on a 20-review cell with a 6–7 review shock the return to LEAN lands in
the last two or three reviews or not at all. Median excess units at the end are unchanged.

### Against the cycle targets

| Target | Validation5 | Met |
| --- | --- | --- |
| Median service ≈ .93 | .937 (V4 .945) | yes, below V4 |
| Avoidable breaches no worse than PR30 | 23 vs 24 | yes |
| Inventory materially below 1.79–1.81 | 1.87 (V4 1.88 on these seeds) | **no** |
| Quiet-cell inventory materially below .70, toward .50–.60 | .80 (V4 .80) | **no** |
| Central + branches improved | .756 vs .751 | **not materially** |
| Recovery mostly reaching LEAN | 32% | **no** |
| No pathological intermittent purchasing | purchase / demand < 1 on intermittent cells; inherited stock 5.9 periods | yes (purchasing), stock unchanged |

## 8. Tests

`tests/unit/test_zaad_network_recovery_v5.py` (16 tests, none skipped; every test constructs its
own receipts and open orders): recency retirement and reaction, overdue-as-late (V5 only), overdue
survival moves arrival mass outside the horizon (fresh orders untouched), recent fill run needs a
run, open orders fill the way the source fills now, backlog-implied lead, flexibility credit only
inside the window, echelon partition bound on four demo networks, transition sentences, rejection
deltas on audited candidates, V5 burden ≤ V4 burden on a quiet cell, pooling follows the transfer
lead, additive cost band on negative costs (the validation5 run-1 crash), comparator
reachability. Full ZAAD unit set: 212 passed, 1 skipped. `ruff` clean; `mypy` at the 8
pre-existing stub errors.

## 9. Verdict

**NEEDS FURTHER MULTI-ECHELON / RECOVERY ENGINEERING**

Holdout4 (seeds 31001, 31002) remains frozen and **unrun**.

What V5 established: the closure-recovery family was an engine failure (dead pipeline assumed to
land next period; the risk state blind to open orders) and is now handled, with the gain
reproduced on two fresh seeds; the mean and tenth-percentile service are the best of any gated
planner at the lowest gated cost; the state machine, echelon accounting and rejection audit are
in place and tested. What it did not establish: any material inventory reduction on validation
(median −0.5%, quiet cells unchanged), a material central-plus-branches improvement, or recovery
that mostly reaches LEAN. Three of the six targets are unmet, so the engine does not go to the
untouched holdout.

Where the next cycle should look, from the retained evidence: (1) quiet cells — the burden band
is too narrow to change the winner on validation seeds; a marginal inventory value that prices
protection against the lean baseline directly, rather than a cost band, is the missing piece;
(2) severe supply with no alternate (cell 17) — the backlog rule delays the freshest order
correctly but the planner has nothing to buy from, so the honest fix is earlier protection
sizing from the first two late receipts, not later sourcing; (3) recovery — retire the supply
driver on the first clean receipt after a backlog has landed instead of after six, and drain the
temporary echelon through transfers before purchases resume; (4) the shrinking replay horizon
interaction, which is a benchmark property and should be reported per cell (remaining horizon
versus current lead) so late-review idleness is classified rather than counted against the
engine.

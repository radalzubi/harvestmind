# P1 planner ownership: purchasing economics against frozen protection / recovery

Pre-registered on 2026-09-09 on `claude/zaad-cycle-stock-p1` at the restored clean baseline
(planner and contracts identical to `4f6aedc`; only the replay's per-review orchestration log and the
cell tracer differ). Written BEFORE any fixture or P0 cell was run with the router. The rule below is
not to be tuned after seeing P / C / P0 results unless a genuine semantic bug is found, and any such
change must be recorded here with its reason.

## 1. Why a boundary is needed (from pass H of `P1_CLOSEOUT.md`)

The screen's NO_ACTION label is produced both in a true calm purchasing state (fixture P, every
decisive review) and while frozen-P0 risk context is load-bearing (review 0 of every P0 cell before
its declared disruption; post-disruption reviews holding 47-252 units of inherited protection under
FALSE_PROTECTION_RISK). One candidate matrix keyed on that label cannot serve both: giving NO_ACTION
the stochastic class fixed P (+2.04% -> +0.29%, robust on 60 varied truths) and broke the P0 gate
(cell 20 .884 -> .837) through the frozen recovery machinery's path sensitivity. Planner responsibility
must be decided before candidate assembly, from semantic state, and a P1 candidate must have no side
effect on a P0-owned review.

## 2. Ownership inputs available at decision time (stage 2)

| field | source | timing | known before candidate assembly | fixture-specific | product semantic | stable for routing |
|---|---|---|---|---|---|---|
| `req.stresses` (declared envelopes: `fill_multiplier`, `extra_lead_days`, `demand_multiplier`, `recovery_period`, `shared_failure`) | request (operator declaration; mandatory, at least one) | every review | yes | no: it is the operator's protection mandate; the P1 fixtures declare the identity envelope `nil` and the P0 benchmark declares `operator_adverse` | yes: "protect against this disruption" | yes |
| `stress_credibility(req, supply)` -> `credibility`, `effective_stress_weight`, `floor` | `uncertainty.py`, from observed lateness / partial deliveries / signals | every review | yes | no | yes (how much the declared envelope deserves now) | partly: floored at .1 while a source has no observed record, so at review 0 it is .1 for P0 cells and P1 fixtures alike and cannot separate them |
| screen state (`NO_ACTION`, `NORMAL_REPLENISHMENT`, `CAPITAL_OPTIMIZATION`, `NETWORK_ALLOCATION`, `PROTECT`, `RECOVER`, `ESCALATE_UNKNOWN`) with `joint_recovery_required_by_rule`, `incumbent_service_deficit` | `screen.py` from protection rows and the incumbent's projected outcome | every review | yes | no | yes | yes |
| per SKU/location risk state: `regime` (LEAN / PROTECT / RECOVER), `activity`, `risk_active` (activity > .05), `decaying`, `active_drivers`, `flags` (incl. FALSE_PROTECTION_RISK), `demand_decline_confirmed`, `periods_to_lean`, `protection_units`, `lean_baseline_units`, `incremental_protection_units`, `exit.backlog_open` | `protection.py` `protection_profile` | every review | yes | no | yes | yes |
| `explicit_order_economics(req)` (supplier terms or per-line fixed order fee) | `model.py` | every review | yes | no | yes (order-level economics declared) | yes, but it is about lumpiness pricing, not about risk: P and the P0 cells both have it False |
| `req.inherited_on_hand` | replay bookkeeping of the stock a review inherited from the previous one | every review | yes | benchmark-only (replay sets it) | no: it is the provenance of *opening* stock, not of protection | not usable for ownership |
| `req.adaptive_escalation` | request | every review | yes | no | legacy switch: off means the full V7 candidate set | yes |
| supply profiles (`scope` declared / observed, `late_probability`, `partial_probability`, `driver_kind`, `backlog_open`, `recent_clean_run`) | `uncertainty.py` from receipts | every review | yes | no | yes | yes, already folded into `activity` and `stress_credibility` |

Values at the reviews that matter (measured on the clean baseline, `scripts` ad hoc, 2026-09-09):

| review | declared stress | credibility / effective weight | regime, activity, flags | incremental protection | screen state |
|---|---|---|---|---|---|
| P0 cell 20 / 90 / 108 review 0 | `operator_adverse`: fill x0.7, +28 days, demand x1.1, shared | .10 / .02 (floor: no observed record) | LEAN, 0, none | 0.4 | NO_ACTION |
| P0 cell 15 review 0 | same | .55 / .11 | PROTECT, .41, none | 0.3 | PROTECT |
| P review 0 and 4 | `nil`: fill x1.0, +0 days, demand x1.0 | .10 / .02 (floor) | LEAN, 0, none | 0.2-0.3 | CAPITAL_OPTIMIZATION, NO_ACTION |
| C review 0 and 4, A review 0 and 4 | `nil` | .10 / .02 | LEAN, 0, none | 0.2-0.3 | NO_ACTION |
| P0 cell 90 review 20 / 24, cell 108 review 28 / 29, cell 21 review 19 (from pass H traces) | `operator_adverse` | - | LEAN, 0, **FALSE_PROTECTION_RISK** | 43-248 | NO_ACTION |

On risk-state fields alone, review 0 of cell 20 and review 4 of P are the same state. The one
canonical, operator-supplied, review-0-available difference is the declared stress envelope.

## 3. Planner responsibilities (stage 3)

**P1 purchasing planner** owns the question "what is the economically correct replenishment decision
under normal purchasing conditions?": whether, when and how much to order; MOQ, case, pallet, MOV,
freight, order cost, financing and carrying; ordinary demand uncertainty from the fitted distribution;
ordinary supplier fill and lead-time spread as declared; comparison with the incumbent. Its candidate
frontier is the normal economic one: the incumbent and projected base stock, the mean-world plan, the
scenario (stochastic) plan, and the cadence plans when order-level economics are declared. It uses the
existing selector and gates.

**P0 protection / recovery planner** owns the question "how do we protect or recover service under a
declared or credible stress, or unwind protection that earlier decisions created?": the declared
disruption envelope and its credibility, active demand or supply drivers, recovery deficits and the
service-first joint plan, inherited protection under FALSE_PROTECTION_RISK or a RECOVER regime,
network scarcity, the hedged / stress / protected / CVaR classes, and every frozen P0 gate. Its path is
the frozen one, bit-identical to `4f6aedc`.

## 4. The pre-registered ownership rule (stage 4)

`planner_owner(req, protection_rows, screen_result)` returns `PROTECTION_RECOVERY` when ANY of the
following holds, else `PURCHASING_ECONOMICS`:

1. **Declared protection mandate.** Any declared stress envelope is not the identity
   (`fill_multiplier < 1`, or `extra_lead_days > 0`, or `demand_multiplier != 1`). The operator has
   asked for protection against a disruption; protection economics are in scope for every review of
   the request, whatever the current credibility (credibility scales P0's hedge, it does not decide
   whether the mandate exists).
2. **Legacy full-set path.** `adaptive_escalation` is off (the V7 architecture requests every class).
3. **Risk-classified review.** The screen state is not one of the three calm states
   (NO_ACTION, NORMAL_REPLENISHMENT, CAPITAL_OPTIMIZATION).
4. **Active or decaying driver, or a non-lean regime, on any SKU/location.** `risk_active`
   (activity > .05), `decaying`, `regime != LEAN`, `demand_decline_confirmed`, or the flag
   FALSE_PROTECTION_RISK (inherited protection under management).
5. **Recovery obligation.** The screen reports `joint_recovery_required_by_rule` or a positive
   `incumbent_service_deficit`.

Conditions 3 and 4 are exactly the existing `lean_review` condition (calm state, no activity above .05),
so a P1-owned review is always a lean review; conditions 1, 2 and 5 are added. The rule reads no
fixture name, cell, seed, benchmark cost, service outcome, inventory cut-off, variance threshold or
time-to-disruption.

## 5. Declared future stress: what is legitimately known (stage 5)

The P0 cells' truth carries a supply state (`deterioration_recovery`, `closure_recovery`) that begins
at review 1; the planner never sees it. What the planner does see at review 0 is the request's
declared stress `operator_adverse`, an operator input that the frozen P0 stress gate already applies at
every review. Condition 1 uses that declaration and nothing else; the credibility machinery (floored
at .1 for both the P0 cells and the P1 fixtures at review 0) is deliberately not used because it
cannot separate the two and because it measures how much to hedge, not whether protection is mandated.
Consequence, accepted and recorded: a request that declares any non-identity stress (including the
P1 sensitivity arm `late`, one week late) is P0-owned at every review, and the P1 frontier applies only
to requests whose declared envelope is the identity. The nil envelope is the P1 fixtures' declared
primary arm (close-out section 4, deviation 3), not a device introduced here.

## 6. Inventory provenance (stage 6)

No per-unit provenance exists: `inherited_on_hand` records the opening stock a replay review inherited,
whatever created it, and `Stock` lots carry no origin. What exists is the risk state's account of
protection: `protection_units` against `lean_baseline_units` (`incremental_protection_units`), the
regime (RECOVER when protection is being unwound), and the FALSE_PROTECTION_RISK flag. Condition 4
uses the regime and the flag, which are the model's own statements that protection or recovery logic
is managing the stock, and no unit threshold on `protection_units`. Limitation recorded: stock created
by an earlier protection decision that has already returned to LEAN with no flag is treated as ordinary
cycle stock.

## 7. Candidate matrix under P1 ownership (stage 8)

| screen state (P1-owned review) | required | optional |
|---|---|---|
| NO_ACTION | deterministic_network, **stochastic_network** | - |
| NORMAL_REPLENISHMENT | deterministic_network, stochastic_network (unchanged) | cvar_network (unchanged) |
| CAPITAL_OPTIMIZATION | deterministic_network, stochastic_network, cvar_network (unchanged) | protected_network, joint_recovery (unchanged) |

Incumbent and projected base stock always; cadence classes when order-level economics are declared
(unchanged). The only change the router makes anywhere is the NO_ACTION row. Under P0 ownership the
frozen matrix and the frozen path apply unchanged, and the report carries
`orchestration.planner_owner`, `ownership_reasons` and `p1_classes_added` (0 on every P0-owned review).

## 8. Gates this pass will apply, in order

1. Router unit tests (twelve, listed in the brief) before any fixture.
2. P0 six cells, decision-level bit-identity where the router assigns P0 ownership: same requested
   set, same built set, same selected action, same status, same period-0 order, same recovery
   admission, same materiality verdict, per review, against the clean reference recorded at the same
   instrumentation level. Time-limit variation with identical inputs is classed as frozen numerical
   variability, not a router defect.
3. Cell 20 review 0: report the owner and whether the assignment is semantically right on review-0
   information.
4. P targeted; then C / O / I / A / G / Q / T; then the freeze gate.

## 9. Architecture documentation (stage 18)

**P1 purchasing planner** (`zaad/full/ownership.py`, owner `PURCHASING_ECONOMICS`): responsibility is
normal purchasing economics. It runs on reviews with no declared protection mandate, a calm screen
state, no active or decaying driver, every SKU/location LEAN and unflagged, and no recovery obligation.
Its frontier is the incumbent, the projected base stock, the mean-world plan, the scenario plan and the
cadence plans; its selector, gates and materiality verdict are the existing ones.

**P0 protection / recovery planner** (owner `PROTECTION_RECOVERY`): responsibility is stress
protection, recovery and protection unwind. It runs on every other review, on the frozen `4f6aedc`
path with the frozen candidate matrix, selector, gates and recovery rules; the router adds nothing to
it and the report proves it (`orchestration.p1_classes_added == []`).

Ownership inputs: the declared stress envelopes (`req.stresses`), `adaptive_escalation`, the screen
state and its recovery fields (`joint_recovery_required_by_rule`, `incumbent_service_deficit`), and
the per-SKU/location risk state (`regime`, `activity`, `risk_active`, `decaying`,
`demand_decline_confirmed`, `flags`). Decided before candidate assembly; reported as
`orchestration.planner_owner` with `ownership_reasons`.

Why NO_ACTION was removed as the architectural boundary: it is a screen label computed from the
incumbent's projected service, drivers, excess and scarcity only; pass H showed it produced in a true
calm purchasing state (P, C) and, identically, at review 0 of every P0 cell before a declared
disruption and during the unwind of 47-252 units of inherited protection. Deciding candidate classes
from that label alone gave the same class two meanings and let a purchasing candidate steer the frozen
recovery machinery.

Rejected approaches, each with its evidence in `P1_CLOSEOUT.md`: fixed-tail weighted scenario world
(cell 90 inventory pathology, D1-D3); per-period Latin-hypercube worlds as default (cannot cover the
95th percentile with three equal-weight worlds, E-pass); more scenario worlds (S=10, four times the
runtime, breaks I, E-pass); analytic expected shortage inside the mean-world solve (fixes P, regresses
P0 cells 20 / 21 / 90 / 108 in every scope, F-pass); materiality inventory base of one period of demand
(fires on P0 cells 20 / 21, F7); a common-valuation selector (the selector already agrees with the
common lens at every decisive review, G-pass and H9); NO_ACTION stochastic escalation as a request
mode (fixes P, fails the P0 gate on cell 20 and C, H-pass); fixture, cell or seed keyed scoping (never
built).

## 10. Outcomes of the gates in section 8 (recorded after the runs; the rule was not changed)

1. Router tests 14 / 14 (`tests/unit/test_zaad_planner_ownership.py`).
2. P0 six cells: every review P0-owned (declared mandate), zero classes added, decision-identical to
   the clean reference on 120 / 120 reviews once cell 90's first run was rerun (its review-4 difference
   was a wall-clock-limited hedged solve returning no plan; the rerun and a rerun of the clean code
   both reproduce the reference on 26 / 26). Cells 15, 16, 20, 21, 108 identical on the first run.
3. Cell 20 review 0: PROTECTION_RECOVERY by the declared mandate; the assignment is semantically right
   on review-0 information (the envelope is declared in the request; the truth is not read).
4. P +2.04% -> +0.29% (actions bit-identical to the pass-H robust arm); C +3.61% under the realised
   ledger and +0.77% under the continuation evaluation; O / I / A / G / Q / T safe under the realised
   ledger; I and S fail under the continuation evaluation. Full record in `P1_CLOSEOUT.md`, pass I.

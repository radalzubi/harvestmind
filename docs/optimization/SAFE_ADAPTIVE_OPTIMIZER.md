# The safe adaptive optimizer

*Optimization that knows when not to optimize.*

HarvestMind departs from what an operator already does only when there
is statistically and economically credible evidence, on the operator's
own history, that the departure improves the operator's objective. A
calm period in which it recommends the incumbent policy is a successful
result. This document is the mathematical design; the validation is in
`docs/validation/SAFE_POLICY_VALIDATION.md`; the audit that motivated the
redesign is in §1.

## 1. Audit of the previous SELECTED logic

Each suspected weakness was checked in code before anything was changed.

| # | suspicion | finding | evidence |
|---|---|---|---|
| 1 | one trailing holdout → winner's curse | **confirmed** | `policy_selected` built a single `_inner_fold(fi, h)` and chose the minimum-cost candidate on it |
| 2 | inner truth used mean fill and mean lead, not recorded outcomes | **confirmed** | `_inner_fold`: `truth_f = mean_fill[s]`, `truth_l = lead_of[s]` for every period |
| 3 | inner supply training could include post-origin observations | **confirmed** | `_inner_fold` passed `train_fill=fi.train_fill`, the full pre-real-origin list, into a fold whose own origin was earlier |
| 4 | insufficient history fell back to the stochastic optimizer | **confirmed** | `policy_selected`: `if min(len) < h + 8: return policy_stochastic_sp(...)` |
| 5 | live fill constant across a scenario's horizon | **confirmed** | `_scenarios`: `fills[(w, s)] = rng.choice(train_fill[s])`, one draw per scenario |
| 6 | live lead = mean, not stochastic | **confirmed** | `leads[(w, s)] = int(fi.lead_of[s])` |
| 7 | no cross-SKU / cross-supplier / route correlation in live scenarios | **confirmed** | suppliers sampled independently; no route tag reached the planner although the simulator has correlated disruption |
| 8 | capacity = arbitrary multiple of mean demand | **confirmed** | `build_inputs`: `cap = {j: max(mean_dem[j] * 3.0, 1.0)}` |
| 9 | missing price → synthetic markup and margin | **confirmed** | `price = ... or cost * 1.2` |
| 10 | closed-loop validation vs a full schedule returned as if executable | **confirmed** | `/fmcg/plan` returned every horizon week with no executable/advisory distinction |
| 11 | portfolio-wide policy choice while SKUs sit in different regimes | **confirmed** | one winner for the whole fold |
| 12 | expected-cost objective with no downside constraint vs incumbent | **confirmed** | objective = weighted recourse cost; no regret term |

All twelve were confirmed. Items 1–4 and 8–10 are corrected in this pass;
5–7 and 12 are corrected in the model; 11 is addressed at the level of
per-SKU anchoring (§6) and per-SKU regime diagnostics (§7), not per-SKU
policy switching, which would let a mixture of policies silently share
one warehouse constraint.

## 2. The incumbent is first-class

`backtesting/incumbent.py::IncumbentPolicy`. Two sources:

- **configured** — the operator states their rule (order-up-to cover and
  review cadence, per SKU or global) or supplies a schedule;
- **inferred** — from their PO history: per SKU, cover = median over POs
  of (order quantity + inventory position at PO date) / mean demand, and
  cadence = median gap between POs. Every output that uses it says
  **INFERRED**; it is a statistical description of behaviour, not the
  operator's policy.

## 3. Multi-fold, nested, leakage-free selection

`backtesting/safe_selector.py::safe_select`. Let $H$ be the training
window before the real origin $0$. Selection folds have origins
$o_k = -(m+k)\,h$ for $k = 1..K$ and hold-out folds $o'_k = -k\,h$ for
$k = 1..m$, with $h$ the fold length. For each fold:

- **train**: demand $d_{j,t}$ for $t < o$; supplier events
  $(\text{fill}, \text{lead})$ with PO period $< o$;
- **truth**: demand for $t \in [o, o+h)$; the **recorded** supplier fill and
  lead for POs placed in $[o, o+h)$, carried forward from the last recorded
  event where a period has none (counted and reported).

Every candidate $c$ and the incumbent $b$ are settled on the same truth
with the same settlement, capacity binding both. Per fold,
$\delta_c = (C_b - C_c)/C_b$.

**Inference.** A moving-block bootstrap over folds (block length 2,
folds overlap) gives the one-sided lower bound $\underline{\delta}_c$ at
confidence $1-\gamma$. Reported per candidate: mean, median, sd, p5, p25,
p75, p95, worst, best, win rate, lower bound, service difference,
inventory difference, downside regret $= \max(0, -\min_k \delta_{c,k})$.

**Gate.** $c$ may displace $b$ only if all hold:
1. $\underline{\delta}_c > \tau$ (default $\tau = 3\%$ of incumbent cost);
2. $\min_k (\text{fill}_c - \text{fill}_b) \ge -\epsilon$ (default 1 point);
3. downside regret $\le$ risk budget (default 10%);
4. at least two folds, and enough history ($\ge 26$ periods);
5. every solve usable with no relaxed floor or budget.

Ties within 1% of the best lower bound go to the simpler policy
(incumbent < order-up-to < deterministic < anchored < stochastic < DRO).

**Winner's curse.** The winner is re-evaluated on the $m$ hold-out folds
it was not chosen on; if its mean $\delta$ there is not positive, the
incumbent is returned. Insufficient history returns the incumbent, never
the stochastic model.

## 4. Value of information

`optimization/vss_evpi.py`. For the multi-period recourse model with
scenario weights $p$:
$\text{RP} = \min_x \mathbb{E}_p[c(x,\omega)]$;
$x_{EV} = \arg\min_x c(x, \bar\omega)$ (mean demand, weighted-mean fill, modal lead);
$\text{EEV} = \mathbb{E}_p[c(x_{EV},\omega)]$ via a fixed-schedule solve;
$\text{VSS} = \text{EEV} - \text{RP} \ge 0$;
$\text{WS} = \mathbb{E}_p[\min_x c(x,\omega)]$; $\text{EVPI} = \text{RP} - \text{WS} \ge 0$.
Both inequalities are tested. Classification: EVPI/RP < 2% →
LOW_INFORMATION_VALUE ("uncertainty currently has low economic value;
retaining incumbent policy"); VSS/RP < 2% → LOW_VSS; high VSS with weak
distributional confidence → HIGH_VSS_LOW_CONFIDENCE (robust candidate);
else HIGH_VSS. In-sample diagnostics, exposed on the API and in the audit
record, never a guarantee.

## 5. Baseline-relative regret and the anchored candidate

`optimization/multi_period_sp.py` accepts a baseline schedule $b$ and
evaluates it on the scenario set to get $c_w(b)$. For decision $x$,
$\text{regret}_w(x) = c_w(x) - c_w(b)$. The anchored objective is
$$\min\ \mathbb{E}_p[c_w(x)] + \lambda\,\text{CVaR}_\alpha(\text{regret}_w(x)) + \sum_{i,j,t}\rho_j\,|x_{ijt} - b_{ijt}|$$
with CVaR linearised as $\eta + \frac{1}{1-\alpha}\sum_w p_w z_w$,
$z_w \ge \text{regret}_w - \eta$, $z_w \ge 0$, and the L1 term as
$\text{dev}^+ + \text{dev}^-$. An optional hard budget
$\text{CVaR}_\alpha(\text{regret}) \le B$ is a constraint; if infeasible it
is relaxed and reported. If $b$ violates the model's constraints it is
refused as a reference with the reason, not pretended feasible. All of
this is in sample: no out-of-sample guarantee is claimed.

## 6. Policy trust: per-SKU anchoring

`backtesting/counterfactual.py::anchor_penalties`. $\rho_j$ is a multiple
of the SKU's per-unit holding cost by regime — CALM ×4, RECOVERY ×2,
VOLATILE ×0.5, SUPPLY_CONSTRAINED ×0.5, PROMOTION ×0.25, DISRUPTION
×0.25 — and ×10 when the SKU's margin is UNKNOWN. The penalty sits inside
the MILP, so MOQ, pallet and capacity constraints still hold; rounded
orders are never blended afterwards. Plan-change magnitude is measured in
validation.

## 7. Regimes

`backtesting/regime.py`: transparent thresholds on demand CV,
intermittency, drift, cover, supplier fill mean/sd and recent vs earlier
fill, and planned promotions, yielding CALM, VOLATILE_DEMAND,
SUPPLY_CONSTRAINED, DISRUPTION, RECOVERY, PROMOTION with a one-sentence
reason each. No fitted classifier.

## 8. Time-varying, correlated supply

`risk/supply_paths.py`: moving-block bootstrap over the joint per-period
vector of all suppliers' recorded (fill, lead), so persistence and
cross-supplier co-movement survive; optional route overlay with a
two-state Markov disruption per route group (rates estimated from
history where a route tag exists, otherwise ASSUMED from the disruption
presets). The optimizer accepts `(scenario, supplier, period)` keys with
the legacy `(scenario, supplier)` still honoured.

## 9. Distributionally robust candidate (experimental)

`optimization/safe_stochastic.py::solve_dro`: finite-scenario adversarial
reweighting — tilt the weights toward the costliest scenarios within a
total-variation ball of radius $r$, re-solve, three rounds. Behind an
explicit call; not marketed.

## 10. Rolling horizon in the product

`/fmcg/plan` executes only the first `commit_window_weeks`; later weeks
are ADVISORY and re-optimised at the next review. The response names the
cadence and the event triggers (demand shift, supplier fill, lead-time
change, inventory discrepancy, promotion change).

## 11. Economics provenance

Every decisive term carries OPERATOR / MEASURED / PUBLIC_BENCHMARK /
ASSUMED / UNKNOWN. A missing margin is UNKNOWN and anchors the SKU to the
incumbent; capacity is OPERATOR, else INFERRED from PO peaks (×1.25),
else ASSUMED, always labelled; carrying cost is entered as annual
components (`domain/carrying_cost.py`) and a sensitivity sweep is
returned with every plan.

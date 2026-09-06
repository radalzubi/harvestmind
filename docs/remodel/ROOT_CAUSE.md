# High service is not, by itself, a reason an optimizer must lose

Audit date: 2026-09-05. Code baseline: `2820a69`. Historical reports are
evidence of what those harnesses produced, not measurements of customer ROI.

## Diagnosis

**The defensible diagnosis is mixed: a missing-state defect plus genuine
economic and evaluation limitations.** The earlier explanation, “insurance
has no value when stock is deep,” is insufficient. A competent inventory
optimizer should also be able to buy less when stock is excessive.

| Mechanism | Code evidence | Consequence | Disposition |
|---|---|---|---|
| Pipeline hidden from optimizer | `backtesting/counterfactual.py::_optimizer_kwargs` formerly omitted `fi.pipeline`; incumbent and `settle` consumed it | New orders duplicate confirmed receipts; high-stock comparisons confounded | Fixed; common planner receives dated delivered-unit receipts |
| Underage reward dominates cheap holding | `optimization/multi_period_sp.py` recourse objective | Rationally purchases marginal service even above an operator's desired target | Added an explicit service-target candidate; do not silently change contract targets |
| Aggregate target is time-inconsistent under replanning | Removing shortage cost permits concentrating the horizon shortage allowance in the executable prefix | A target-only policy can repeatedly sacrifice early service | Retained failed aggregate variant; added separate per-period expected-fill experiment |
| Service constraint is not an OTIF promise | Same model's controllable-window expected-unit-fill constraint | Expected service can pass while individual weeks/customers fail | Report full-horizon realized unit fill separately; OTIF unavailable in this experiment |
| Two-stage ordering, scenario-wise recourse | Same model | Fixed future orders miss adaptive opportunities; recourse knows its scenario | Rolling common replay; removed incorrect universal bound claim |
| Missing end-state economics | Recourse objective has no terminal salvage valuation or PO cash ledger | Finite-horizon orders can look cheap; average-stock reduction is not cash collection | Preserve outstanding arrivals across reviews; residual terminal limitation disclosed |
| Procurement/source cost incompleteness | Recourse-only scoring uses margin, carry, waste, spot premium | No honest all-in sourcing-profit comparison if alternatives have different costs/terms | Not claimed; dual-source launch blocked on landed-cost ledger |
| Independent SKU supplier map | `FoldInputs.supplier_of` is one supplier per SKU | No feasible source-switch choice in this commercial replay | No route-diversification benefit claimed |
| Historical selection is not a future guarantee | `safe_selector.py` selection/confirmation/live gates | Bad confirmation service or a relaxed live solve could previously pass | Repeated all gates on held-out folds; reject relaxed/unusable live schedules |
| State trigger bypassed confirmation | Fresh demand-shift branch | Optimizer could be promoted without the evidence advertised by the gate | Default off; explicit experimental opt-in retained |
| Inner-fold leakage and overconfidence | Full-window fill fallback/lead/current stock; two-fold block spanning whole sample | Later information influenced training; confirmation interval could collapse to the mean | Training-only dated supplier history; standardized stock; rebased event dates; nondegenerate resampling |

A small regression isolates the pipeline mechanism without estimating market
value: four periods of demand 100, supplier fill 0.5, and four confirmed
receipts of 100 require **zero** new orders; omitting pipeline leads to 800
new committed units. That exact accounting test is stronger evidence of a
defect than a favorable stochastic median.

## Economic decomposition

The implemented comparable operating-loss ledger is

`C = holding + missed contribution + disposal + SLA penalties`.

For the new experiment spot, disposal and SLA rates are zero by design;
their reported zeros do **not** establish those features work. All candidates
have identical costs, external demand, supplier paths and capacity. The
same settlement applies yields once and carries their own inventories.

For a service increase from s to s+Δs, the approximate direct contribution
gain is `annual demand × contribution/unit × Δs`; compare it with incremental
carry, expiry, handling, expedite and contractual effects. A percentage
point is the same fraction of units but usually requires progressively more
inventory in the distribution's tail. Contractual penalties may be nonlinear;
this model does not infer them from a generic target.

For excess stock, the question is instead: **how much inventory can be
released while keeping the approved service target and downside tolerance?**
These are distinct optimization problems. Removing the shortage term is an
experimental way to trace that tradeoff, not proof that lost sales are free:
settlement still charges them. A service-target candidate may lose on cost.

Report `Δholding`, `Δshortage`, realized service, inventory change and failed
solves alongside percent savings. If baseline operating loss is small, a
large relative percentage can represent very few dollars. It is never a
percentage of the operator's sales or all procurement spend.

## Claims that must be retired or narrowed

- “Above 95% reliability there is nothing to sell”: not established. Mean
  supplier fill is not customer fill; mean alone does not identify tail risk.
  Inventory right-sizing may matter in a reliable network.
- “The stochastic layer fails because it buys useless insurance”: a possible
  economic effect, not a sufficient causal account while pipeline was missing.
- “No-harm”: an acceptance discipline on observed folds, **not a guarantee**
  that the next realized path cannot be worse. Defaults still allow a defined
  service tolerance and regret budget, rather than exact dominance.
- “Validated on real data”: public aggregate demand and port-arrival signals
  in `REAL_DATA_VALIDATION_PROJECT_B.md` are real inputs; SKU/supplier orders,
  counterfactual decisions, margins and port-to-fill mapping remain simulated.
  None is real operator savings validation. Monthly inventory/sales ratios
  also mix an inventory valuation basis with sales revenue, not physical cover.
- “Aqaba must be reached through Bab el-Mandeb”: the historical report is too
  broad. Approach direction matters; a Mediterranean/Suez approach to Aqaba
  does not require Bab el-Mandeb. Geographic route alternatives need explicit
  origin-to-destination paths, not a port-name multiplier.
- “The gate is deployable because it follows the incumbent closely”: the
  saved adaptive report includes losses and tuning on the same evaluation
  seeds. That is developmental evidence, not an untouched final holdout.

The previous reports remain preserved. This audit supersedes their causal
interpretations and marketing implications, not their recorded arithmetic.

The first audit sweep itself was rejected: physical pending receipts exposed
eventual fill and lead to the next review, and supplier outcomes were dated by
PO rather than receipt. The replacement `evidence/causal/` separates expected
open POs from private realized pipeline and trains on receipt-available evidence.
The earlier reported zero-harm result cannot be used as evidence. This is the
same class of information-set error the audit is intended to prevent.

## Remaining scientific risks

The inner replay standardizes opening stock to one training week plus a
training-mean lead pipeline. It does not reconstruct historical inventory.
Prices, capacity and policy rules are treated as known fixed constraints;
real deployments need their as-of versions. The new generator therefore uses
time-invariant exogenous capacity rather than capacity inferred from later
demand. Small confirmation samples remain weak despite fixing the bootstrap.

Other existing limitations were not disguised as fixes: transfer recourse
is scenario-wise, terminal valuation is absent, perishable decay timing and
emergency settlement need separate parity work, and anchored reference
evaluation relaxes certain physical constraints. Our no-warehouse,
unit-pack, no-transfer experiment does not validate these configurations.
Do not extrapolate it into a full production economic optimizer.

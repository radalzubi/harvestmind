# Method choice and implementation boundary

## Recommendation

Keep a **rolling, incumbent-first candidate portfolio**, with common physical
settlement and explicit human approval. Add service-target right-sizing as
an experimental candidate, not a replacement default. Keep the existing
distributional optimizer for shortage-sensitive cases only when it earns
its place against a fill-aware incumbent. Do not build a general ERP, MEIO,
vehicle router or reinforcement-learning platform before customer evidence.

## Alternatives, critically compared

Scores are engineering judgments, not measured vendor rankings. Weighted
score out of five = 30% fit to a single-echelon distributor + 25% auditability
+ 20% near-term implementation + 15% data feasibility + 10% decision flexibility.
The five component scores are shown so the preference is inspectable.

| Method | Components | Weighted | Appropriate use / limitation | Decision |
|---|---|---:|---|---|
| Fill-aware base-stock / (s,S) | 4/5/5/5/2 | 4.40 | Competent cheap incumbent; weak shared constraints | Required baseline |
| Service-constrained inventory | 5/5/4/4/3 | 4.45 | Right-size to an explicit metric; expected fill not SLA certainty | Add experimental candidate |
| MEIO / guaranteed service | 2/4/2/2/4 | 2.70 | Optimize where buffers sit across connected echelons; needs network data | Partner/defer |
| Two-stage stochastic | 4/4/4/3/3 | 3.75 | Shared first stage with uncertain demand/fill/lead; scenario recourse information issue | Retain candidate |
| Multistage stochastic | 3/3/1/2/5 | 2.65 | Causal future purchases; scenario tree growth | Defer until rolling control inadequate |
| CVaR-regularized SP | 4/4/4/3/3 | 3.75 | Tail loss or regret, risk appetite explicit; in-sample tail not calibrated guarantee | Retain, ablate |
| Chance constraints | 3/3/2/2/3 | 2.65 | Probability of SLA failure; harder mixed-integer/coverage questions | Defer until contract requires it |
| Budgeted robust LP | 3/4/4/3/2 | 3.35 | Transparent bounded-error protection; may overstock | Optional stress comparator |
| Distributionally robust | 3/3/2/2/3 | 2.65 | Distribution uncertainty; radius selection can dominate result | Research only |
| Rolling horizon / MPC | 5/4/5/4/5 | 4.60 | Replans using actual stock/pipeline; terminal and switching costs matter | Core execution method |
| Adjustable robust | 3/3/1/2/4 | 2.55 | Restricted adaptive decisions against uncertainty sets | Defer |
| Dual-source / base-surge | 4/4/3/3/4 | 3.65 | Slow cheap source plus feasible quick expensive source | Next only with alternate quotes |
| Inventory-routing | 2/3/1/2/4 | 2.25 | Vehicle capacity and replenishment jointly | Partner with route software |
| Transshipment | 3/4/3/3/4 | 3.35 | Rebalance between real locations with stock/lead/cost data | Later, not surrogate SKU trick alone |
| DP / approximate DP | 3/3/1/2/4 | 2.55 | Long-run policy and state value; dimensionality and approximation | Small oracle research only |
| Reinforcement learning | 2/2/1/1/5 | 1.90 | Large repeated decision datasets and safe training environment | Do not build now |
| Incumbent-first hybrid | 5/5/4/4/5 | 4.65 | Select complexity only with evidence; switching/state mismatch risk | Chosen architecture |

This is not a claim that sophisticated methods cannot work. Guaranteed-service
network buffer placement has a long research history; a standard method can
still support a useful product. [Graves and Willems (2000)](https://pubsonline.informs.org/doi/abs/10.1287/msom.2.1.68.23267)

CVaR represents average tail loss through an auxiliary threshold and excess
variables, while budgeted robustness trades nominal performance for protection
over a specified uncertainty set. Neither is an automatic out-of-sample
improvement. [Rockafellar publication list](https://sites.math.washington.edu/~rtr/papers.html),
[Bertsimas publication list](https://www.mit.edu/~dbertsim/papers.html)

Wasserstein DRO has tractable reformulations under stated assumptions. The
repository's scenario-reweighting experiments must not be advertised as an
implementation of every DRO guarantee. [Mohajerin Esfahani and Kuhn](https://arxiv.org/abs/1505.05116)

Research from Amazon demonstrates that learned inventory control is a serious
industrial approach, but does not establish that this startup has the data,
simulator fidelity or operating scale to outperform simpler policies with it.
[Amazon Science](https://www.amazon.science/publications/deep-inventory-management-with-supply-and-capacity-risk-awareness)

## Decision flow

As-of data → reconcile inventory and open POs → establish incumbent → generate
candidate schedules → common dated replay → cost/service/regret gates → separate
confirmation folds → live feasibility check → operator approval → commit only
the review window → record outcomes and remaining pipeline → repeat.

Abstain when essential units, dates, capacities, service definitions or supplier
history are unavailable. A null recommendation is not permission to run SP.
An operator-approved incumbent is the fallback, not a claim it satisfies every
SLA during physical shortages.

## Mathematical contract for the implemented addition

For product j, supplier i, order period t, scenario w:

`arrival[j,t,w] = pipeline[j,t] + Σ_(i,k: k+L[i,k,w]=t) fill[i,k,w] x[i,j,k]`.

Pipeline is **already delivered-equivalent** scheduled stock. If its quantity
is only an uncertain outstanding PO, the importer must not mislabel it as
confirmed; a scenario-dependent pipeline model is a separate extension.

Balance uses previous surviving stock plus arrivals and permitted recourse
against demand, carried inventory, waste and unmet demand. New orders share
one scenario-independent schedule, capacity and lot constraints. Opening stock
and pipeline are common inputs for every candidate, but each policy retains
its own rolling state after its first decision.

Standard candidate objective is expected recourse loss, with optional existing
L1 anchoring, CVaR regret and stability penalties. The service-target candidate
sets the shortage coefficient to zero **inside selection only**, retains
holding/waste/recourse costs, and imposes explicit per-product service floors:

`Σ_w p[w] Σ_(t>=t0[j]) unmet[j,t,w] <= (1-alpha[j]) Σ_w p[w] Σ_(t>=t0[j]) demand[j,t,w]`.

Here t0 is the existing model's earliest controllable arrival period, not the
whole observed window. The external score still charges missed contribution
over **all** periods. Positive inventory carrying cost is mandatory. Infeasible
targets return unusable results; this wrapper never silently lowers them.

`stock_service_frontier` reports every requested target, solver status,
in-sample expected fill, average inventory value, schedule and dominance flag.
It is a planning frontier, not an empirical service guarantee. The experiment
adds realized curves and seed ranges, including infeasible/fallback cases.
Flat or nonmonotone realized curves are possible; do not smooth them into a
sales story. Do not lower a contracted SLA to make a point look attractive.

The selector requires complete selection and confirmation folds, conservative
relative-cost improvement, service noninferiority within tolerance, bounded
worst-fold regret and no relaxed/unusable solve. Ties prefer simplicity.
Both confirmation and the live solve are checked. The state-evidence bypass
is disabled by default. The bootstrap now prevents a full-sample block from
producing false certainty on two folds; two folds still cannot support a
strong statistical guarantee or a calibrated 99.9% service claim.

## Four required operator behaviors

| Operator | Candidate behavior | Permission to deploy |
|---|---|---|
| Understocked | Protect contribution/approved service where future capacity can help | Only feasible causal benefit vs competent incumbent |
| Overstocked | Run down stock and avoid duplicate pipeline orders | Preserve approved service and downside limits; do not call disposal a saving |
| Balanced | Retain incumbent, possibly small approved exceptions | A solver finding a different optimum is insufficient |
| Disrupted then recovering | Condition on observed supplier evidence, shorten exposure, unwind after recovery | No invented lead signal; no automatic source switch without feasible alternate |

The benchmark reports whether these behaviors actually occur; failing a row
blocks the corresponding commercial claim. Regime labels do not select the
correct answer using future truth. Historical state-aware modules remain
experimental and are separately ablated against ungated and gated plans.

## Feature priorities and customer traceability

| Customer problem | Component | KPI / evidence needed | Priority |
|---|---|---|---|
| Buyer cannot reconcile open orders | Dated pipeline, unit/pack checks | Duplicate-order rate; inventory balance | P0, fixed |
| Already high service but costly stock | Service-target candidate + frontier | Same-service carry reduction and inventory release separately | P0 experiment, not automatic promotion |
| Optimizer loses to buyer | Incumbent + confirmation/live gates | Harm rate, service downside, abstention, switch cost | P0, hardened |
| Seasonal/erratic demand | Existing probabilistic forecast/segmentation | Calibration AND decision value | Retain, no forecast-only ROI claim |
| Supplier short/late shipments | Existing fill/lead distributions | Supplier PO-to-receipt calibration | Retain with dated evidence |
| Route disruption | Existing state diagnostics, optional adaptive candidate | Lead over operator information; actionable alternative value | P1, pilot evidence required |
| Lost margin differs by SKU | Measured cost ledger / per-class targets | Contribution after avoidable cost, not revenue uplift alone | P0 data requirement |
| Cash tied up | Inventory-value reporting | Release, annual carry, PO payments and budget separately | Reporting now; financing constraints later |
| MOQ/case/pallet/calendar | Existing pack MILP; calendars need operating mapping | Executable PO acceptance and order-count cost | Retain/test on actual packs before live use |
| Alternate source / expedite | Landed costs, delay and available capacity | Net margin after premium, availability confirmation | P1 gated customer need |
| Cancellation/de-expedite | Contract-aware actions and penalties | Avoided cost net fees, supplier approval | P1, never cancel automatically |
| Multiple warehouses | Transfers and MEIO | Delivered stock after transfer cost/time, no double counting | P2 or partner |
| Expiry/salvage/obsolescence | Lot age, actual shelf-life, terminal realization | Writeoff and residual value under common settlement | P0 for fresh produce; outside shelf-stable experiment |
| Payment terms/FX/financing | Dated currency and cash ledger | Cash-at-risk, financing cost without carry double count | P1 after ledger reconciliation |
| Broad resilience intelligence | Port feeds/public news | Incremental causal decision benefit | Do not build a news dashboard as the moat |

ERP integrations, model interpretability, audit logs, exports and overrides are
product requirements. The mathematical additions do not make autonomous PO
write-back safe. Security remains least-privilege read-only intake, isolated
operator storage, retention/deletion controls and explicit approval before
external writes. No operator or synthetic benchmark data was added to the
production training vault in this work.

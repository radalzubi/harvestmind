# ZAAD resilience engine

## Implemented control, not geopolitical prediction

Inputs are historical accepted supplier fill/lead, an explicit approved route graph, and licensed timestamped structured signals. Output is an economically evaluated first-review quantity and primary/alternate allocation. Physical/official severity shifts only exposed routes. News is displayed as corroboration and **cannot order or change physical uncertainty by itself**. This prevents a panic-buying rule but leaves the empirical incremental value of news untested.

Modes are descriptive workflow labels, not calibrated regime posteriors. Positive relevant physical stress→PROTECT; no feasible service-qualified family→ALLOCATE/ABSTAIN; a fresh relevant recovery signal after protection→RECOVER; ordinary state→LEAN. Missing/expired data after protection causes abstention, not an assumption of recovery. It does not implement a learned HMM, Bayesian hazard posterior or persistent hysteresis store.

## What can change

Buffer, order size, immediate review timing through order-up-to shortfall, approved-source share and spill into actual spare capacity. A cheaper but slower path is compared with a premium alternate on the same ledger. All paths require contiguous origin-specific itineraries and current operator clearance. More supplier names do not remove a shared port/carrier/route failure domain.

Transfers, product substitution, actual cancellation/rescheduling, de-expediting booked shipments, mode switching without a quoted route, and multi-echelon balancing are deferred. A tested standalone contractual-minimum/priority/fair-tie shortage allocation helper exists in `zaad/allocation.py`; it is not integrated customer-order OTIF optimization. ALLOCATE does not fabricate missing supply.

## Risk method comparison and current choice

| Method | Current role / reason |
|---|---|
| Historical empirical fill/lead + structural shared-domain ranks | Implemented transparent small-data baseline; not a fitted copula |
| Finite-policy expected-cost search | Implemented baseline, forecasts/pipeline same as competitors |
| CVaR90 finite-policy search | Benchmark comparison; tail sample small, not a production guarantee |
| Continuous SAA / original Pyomo SP | Preserved separately; legacy non-work-conserving failure excludes reuse for this proof |
| Chance constraints | Per-SKU expected unit-fill filtering is implemented; a probability guarantee is not |
| Robust/DRO | Deferred until uncertainty sets can be justified; no complexity premium without evidence |
| HMM/Bayesian/change-point/survival risk estimator | Existing experiments audited; not promoted as calibrated route probabilities |
| Full multi-stage stochastic network/RL | Deferred; useful decisions can first be tested with finite policies and human review |

## Recovery

All outstanding POs remain in the expected pending book; new orders cannot consume private actual arrival knowledge. Explicit recovery removes the current route stress and stock protection should run down through demand, rather than remaining a permanent target. Excess stock results in zero initial orders in the recovery acceptance fixture. Frozen traces in `evidence/recovery_traces.csv` reconstruct exactly the original saved costs. They do not establish real recovery time, shipment cancellation ability or a calibrated glidepath.

## What the final stress says

Disruption cost superiority alone is insufficient: 35/60 gated disruption cases miss at least one requested service target; severe, shared-route and no-alternative cells all fail service5/5. Model confirmation cannot catch a misspecified route-delay model because both Monte Carlo samples share it. The stage7 recovery in synthetic outcomes is an explicit assumed observed update, not a predicted end to a real crisis. Therefore the prototype is useful for engineering and operator discovery, not operational service promises.

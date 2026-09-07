# ZAAD Industry Standard V8 — commercial graduation framework

What ZAAD has to be able to say, and prove, before a distributor should trust it with replenishment
decisions. This document defines the standard; it does not report against it.

Written at the start of the V8 cycle on `claude/zaad-industry-standard-v8`, based on
`claude/zaad-capital-recovery-v7` (0e278c3).

## 0. How the sources are used

The brief requires that vendor marketing, independently supported practice, mathematical principle
and customer case-study outcome be kept apart. They are, and the separation matters because the
inventory-reduction numbers in this market vary by an order of magnitude depending on which
category they come from.

### 0.1 Mathematical planning principles (the load-bearing layer)

Multi-echelon inventory theory has two families, and which one a system implements determines what
its safety stock *means*:

- **Stochastic-service model (SSM)**, from Clark and Scarf (1960). Each stage holds enough stock to
  meet its own service target, and a stage fed by an upstream stage must characterise its
  replenishment time including the probability that the upstream stage is itself out of stock.
- **Guaranteed-service model (GSM)**, from Simpson (1958), developed by Graves and Willems (2000,
  2003). Each stage commits a service *time* to its downstream stages and holds enough stock to
  always honour that commitment; demand beyond a bound is handled outside the model.

GSM is tractable on large networks and is what most commercial MEIO tools implement. SSM is more
faithful when upstream stockouts are common — which is exactly the disrupted-supply case ZAAD
targets. ZAAD is closer to SSM: it plans against explicit scenario worlds in which upstream supply
can fail, rather than assuming a guaranteed upstream service time.

This is the reason ZAAD cannot simply adopt published MEIO safety-stock formulas as a target. It
also means ZAAD's numbers are not directly comparable to a GSM tool's, and the report must say so.

**Consequence for V8:** the `echelon_base_stock` comparator is a GSM-flavoured policy and should be
described as such, not as "the MEIO answer".

### 0.2 Independently supported practice

- Fill-rate targets are segmented, not global. The common practice is ABC-style differentiation —
  A items in the high 90s, C items materially lower — because the marginal inventory cost of the
  last point of service is not worth paying on a slow tail item. A single global service threshold
  is *not* industry practice, and V8 must not use one.
- Reported general distribution fill-rate ranges cluster around 92–98%, with 97–99% cited as a good
  target and pharmaceutical distribution higher (98–99%) than consumer electronics (92–95%).
- Perishable operations carry structural loss. Reported "normal" spoilage for perishable items is
  around 2–5%, with retail-level fresh produce shrink far higher and enormously item-dependent
  (single-digit for bananas, tens of percent for leafy greens). FEFO rather than FIFO is the
  baseline expectation for expiry-managed stock.

### 0.3 Customer case-study outcomes (specific, attributable)

- **P&G**, published in *Interfaces* (Farasyn et al., 2011): multi-echelon models produced about a
  **7% average inventory reduction** across business units, as part of a broader programme.
- **Farnell** (electronics/MRO distributor, via Logility): about **5% inventory reduction** with
  service maintained.

These are the two most defensible anchors: both are attributable, both are single-digit, and both
were achieved alongside a change in planning process rather than by software alone.

### 0.4 Vendor marketing claims (treated as claims, not evidence)

Figures of "20–25% network inventory reduction with 3–7 points of service improvement", and
segmented-MEIO claims of "up to 63% inventory value reduction", circulate widely in vendor and
aggregator content. They are not usable as a target. They are typically not baselined against a
*competent* incumbent, rarely separate one-time working-capital release from recurring saving, and
are not independently verifiable.

**ZAAD will not claim a number in that range**, and V8's capital gate is set from the case-study
anchors, not the marketing ones.

## 1. Operating regimes — no single global threshold

The framework separates two regimes because the same service number means opposite things in them.

### 1.1 Normal feasible operations

A cell is *normal feasible* when the network is physically capable of meeting the requested service
with the supply, capacity and lead times available.

| dimension | standard |
| --- | --- |
| service | approximately 97–99% where physically achievable, at the segment's own target |
| avoidable service failures | near zero — a failure with a feasible alternative plan is a defect |
| segmentation | the requested target is per customer/SKU class, never one global number |
| inventory | economically rational, not minimal |
| stability | recommendations do not churn between reviews without a reason |
| feasibility | no physically impossible action is ever recommended |

99% is not forced. Where the economics or the declared service policy do not justify it, the
correct behaviour is to meet the declared target and stop.

### 1.2 Constrained / disrupted operations

A cell is *constrained* when the requested service vector is not physically reachable.

Absolute service is the wrong measure here. The standard is:

| dimension | standard |
| --- | --- |
| frontier gap | ZAAD service against the best physically achievable service |
| incumbent | ZAAD against a competent incumbent under the same disruption |
| priority | priority-weighted shortfall, not unweighted average service |
| allocation | scarce stock goes to the highest-priority obligations first |

**Avoidable and unavoidable shortage are reported separately, always.** A 90% outcome is a defect
if 99% was reachable and excellent if 90.5% was the ceiling.

## 2. Capital standard

The commercial objective is a **10–15% inventory improvement against a competent baseline where the
physical and economic system permits it**.

Two guards on that number:

1. It is measured against a *competent* incumbent — reorder-point with properly sized safety stock,
   periodic order-up-to, projected base stock, echelon base stock — never against a deliberately
   weak policy. Beating a bad baseline is not evidence.
2. Where a properly optimised incumbent is already efficient, the required output is
   **`NO MATERIAL IMPROVEMENT AVAILABLE`**. That is a commercially better answer than a manufactured
   saving, and V7's evidence already shows it is sometimes the true one: on quiet cells ZAAD sits at
   1.07 inventory periods against an independent echelon policy's 1.18, at better service — there is
   no 15% sitting there to find.

Note the tension with §0.3 deliberately: the defensible published anchors are 5–7%, and the target
here is 10–15%. The target is therefore **aspirational and conditional**, and the report must state
which cells had improvement available at all before quoting any percentage.

## 3. Economic standard

Inventory reduction that raises total economics is a failure, not a success. The measured cost must
include purchasing, transport, expedite, transfer, carrying, financing, storage, expiry and
write-off, shortage contribution loss, cancellation and amendment fees, supplier premiums and
modelled customer penalties.

**One-time working-capital release and recurring annual saving are never added together.** They are
different economic objects and must be reported on separate lines.

## 4. Runtime standard — measured, then set

The brief requires profiling before picking numbers. Measured on this branch, seed 36001, one
`plan()` call (three repetitions, warm process):

| cell shape | horizon | median latency |
| --- | --- | --- |
| single location, stable | 12 | 3.1 s |
| central + one branch, intermittent | 12 | 3.9 s |
| single location, supplier fill risk | 12 | 7.2 s |
| central + two branches, intermittent | 12 | 7.3 s |
| central + two branches, stable | 12 | 19.7 s |
| single location, closure recovery | 20 | 30.4 s |
| central + two branches, decline | 26 | 28.2 s |
| single location, deterioration recovery | 30 | 31.4 s |

Two structural facts behind those numbers, both measured:

- **Essentially 100% of the time is inside the MILP.** Model build and all of the V7 diagnosis
  (decomposition, duplication, pooling, timing) together account for under 1%. Model-structure reuse
  is therefore **not** a worthwhile speed lever, and the brief's caution against a risky solver
  rewrite for speed applies with full force.
- **A recommendation costs 10–11 separate MILP solves**, one per candidate policy plus the
  incumbent, the frontier and the confirmation solves.

### 4.1 Proposed service-level objectives

Set against the measurement, not invented:

| operation | target | rationale |
| --- | --- | --- |
| single operational recommendation, simple SKU | < 2 s p90 | needs adaptive escalation; today 3.1 s with the full candidate set |
| single operational recommendation, network SKU under disruption | < 30 s p90 | roughly today's behaviour; acceptable for an exception queue |
| interactive what-if on one SKU-location | < 5 s p90 | industry expectation for interactive planning is seconds, not batch |
| portfolio/batch run, 10,000 SKU-locations | overnight window, < 8 h | at today's ~13 s median this is 36 h — escalation is mandatory, not optional |
| diagnostic replay, one SKU-location, 26 reviews | < 5 min | today ~112 s median, 685 s worst |
| high-risk robust solve | < 60 s, explicitly flagged | reserved for genuine disruption cells |

The portfolio row is the binding constraint and it is the justification for adaptive escalation:
running the full ten-candidate policy set on every boring SKU is roughly a 4× overrun of an
overnight window.

## 5. Solve quality — a standard V7 did not have

Profiling produced a finding that belongs in the standard rather than in a performance note.

The engine asks HiGHS for `mip_rel_gap = 1e-6` under a 5-second per-solve wall-clock cap. On long
or networked cells that gap is not reachable in the time allowed:

| cell | horizon | solves hitting the 5 s cap | worst reported optimality gap |
| --- | --- | --- | --- |
| 0 | 12 | 0 of 10 | 1.7e-12 |
| 15 | 12 | 0 of 10 | 4.8e-16 |
| 35 | 12 | 0 of 11 | 3.4e-10 |
| 72 | 12 | 3 of 11 | 1.2e-02 |
| 21 | 20 | 6 of 10 | **8.9e-01** |
| 108 | 30 | 6 of 10 | **1.0e+00** |

Meanwhile the selector discriminates between candidates on modelled cost differences of roughly
41–1071 currency units, and accepts a candidate on a bootstrapped cost benefit with a threshold of
`1e-6`.

**The decision layer is discriminating at a finer resolution than the solutions it is comparing are
guaranteed to.** On a 30-review cell, at least one "candidate" carries a 100% optimality gap — it is
a feasible point the solver never optimised — and the selector nonetheless ranks it on cost against
others.

A direct experiment confirms the consequence. Re-running the same cells at looser gaps changes the
*operational recommendation* on four of eight cells while saving very little time:

| cell | gap 1e-6 | gap 1e-3 | change |
| --- | --- | --- | --- |
| 15 | buy 100.0, `hedged_network` | buy 100.0 | different action set |
| 21 | buy 9.2 | **buy 0.0** | order cancelled entirely |
| 35 | buy 23.4, `stochastic_network` | buy 23.4, `cvar_network` | different policy |
| 108 (at 1e-2) | buy 9.2 | **buy 18.4** | order doubled |

So a bounded MIP gap is **rejected as a speed lever** for this engine: it is decision-unstable, and
on the cells that are actually slow it saves under 10% because those solves are wall-clock bound
rather than proof bound.

**The V8 standard therefore adds a solve-quality requirement:**

1. Every candidate carries its achieved optimality gap and termination reason.
2. A candidate whose gap exceeds a declared threshold is **not economically comparable** and must
   not be ranked against others on cost. It may still be used for feasibility and service evidence.
3. If the selected plan rests on an under-solved candidate, the recommendation is downgraded in
   confidence and says so.
4. Benchmark evidence reports the distribution of achieved gaps, not just wall time.

This is a correctness standard, not a performance one, and it takes precedence over every speed
optimisation in the cycle.

### 5.1 What the gate actually caught — and what it did not

Implementing the gate and measuring it corrected the first reading above, and the correction is
more important than the original claim.

The wide gaps (0.89, 1.00) belong to solves that return a **non-`OPTIMAL`** status, and those
candidates were *already* excluded from ranking in V6/V7, because `feasible` is built only from
candidates that solved. At the default threshold of 0.02 the number of `OPTIMAL`-but-under-solved
candidates on the measured cells is **zero**, and service and inventory are identical with the gate
on and off (cell 0: 0.921 service, 0.43 inventory periods, both ways).

**The gate is therefore currently a no-op on measured cells.** It is retained as a guard against a
failure mode that would otherwise be silent, not presented as a fix that changed an outcome.

The real exposure the profiling uncovered is different, and worse:

| cell | horizon | candidate solves | solves at the wall cap | candidate slots lost to non-`OPTIMAL` |
| --- | --- | --- | --- | --- |
| 0 | 12 | 102 over 12 reviews | 0 | 13 |
| 121 | 26 | 222 over 26 reviews | 35 | 64 |
| 108 | 30 | ~300 over 30 reviews | 37 | **79** |

On a 30-review cell, seventy-nine candidate slots simply vanish from the selector's choice set
because their solve ran out of wall clock — and nothing in V6 or V7 reported it. **ZAAD is
systematically choosing from a smaller candidate set on exactly the hardest cells, and silently.**

That is a plausible mechanical explanation for the V7 adverse case (cell 108 held a full extra
period of cover at identical service), and it is the finding V8 should act on: the remedy is more
solve budget on large cells, smaller models, or an explicit confidence downgrade when the candidate
set was truncated — not a gap threshold. The reporting added here is the prerequisite for choosing
between those.

## 6. Baseline standard

ZAAD is measured against competent policies, at minimum: reorder point with safety stock, periodic
order-up-to, projected base stock, echelon base stock, a competent network replenishment heuristic,
frozen ZAAD V6 and V7, a stochastic optimiser, and a robust optimiser where appropriate.

The commercial question is whether ZAAD beats what a reasonably competent planner could already do.

## 7. Abstention standard

A system that always recommends something is not trustworthy. Where no material improvement exists,
the correct output is to retain the incumbent with a reason code. Reason codes:
`NO_ACTION_ALREADY_EFFICIENT`, `SERVICE_IMPROVEMENT`, `INVENTORY_REDUCTION`, `WORKING_CAPITAL`,
`RISK_PROTECTION`, `NETWORK_REALLOCATION`, `SUPPLIER_CHANGE`, `RECOVERY`,
`INFEASIBLE_SERVICE_RECOVERY`.

## 8. What this framework forbids

- One global service threshold across all customers and SKUs.
- Reporting a service failure without saying whether it was avoidable.
- Quoting an inventory percentage without stating whether improvement was available at all.
- Adding one-time working-capital release to recurring saving.
- Comparing against a weak baseline.
- Loosening validation settings to improve reported runtime.
- Ranking candidates on cost differences smaller than the solver's own optimality gap.
- Describing synthetic benchmark results as customer results.

## 9. Attribution standard (Part C progress)

Unexplained inventory is not an acceptable category. The V7 decomposition left 12.0% of units
unit-weighted (3.5% median per cell) with no operational reason.

Locating the residue rather than guessing at it found two causes, both defects in the attribution
rather than real excess:

1. **The decomposition disagreed with the engine.** It recomputed protection from the fitted
   standard deviation, while the engine sizes protection from its own echelon partition — and on
   intermittent demand the engine works from an occurrence/size decomposition that is far wider
   than the raw fitted sd. The attribution therefore under-claimed and dumped the difference into
   `unexplained`. The largest single residue was cell 35's branch: 109.9 units on hand against a
   45.6-unit local-service claim. Reading the claims straight off the protection row's echelon
   partition makes attribution and recommendation agree by construction.
2. **Inherited stock had no category.** Opening position is now tracked through the replay per
   SKU/location, capped at what is physically present, drawn down by served demand before purchased
   units, and surfaced as `inherited_excess` — units from the opening position still on hand after
   every operating obligation is met.

Measured on six diagnostic cells, seed 38001, from the first fix alone:

| | before | after |
| --- | --- | --- |
| unexplained, unit-weighted | 8.0% | **2.4%** |
| at echelon-origin locations | 8.5% | **0.0%** |
| at service locations | 7.7% | 3.9% |

The residue that remains is concentrated in one place and has a known cause. On cell 35 at reviews
6 and 8 the branch holds 84–110 units while `demand_cycle` claims **zero**, because cycle stock is
claimed as `mean demand × window` and the fitted mean of an intermittent series collapses toward
zero after a run of empty periods — while the branch is quite correctly still holding stock for the
next spike.

**That is the honest open item: the mean is the wrong basis for cycle stock on intermittent
demand.** The fix is to claim cycle stock from the same occurrence/size model the engine already
uses for spread, and it is not yet done. It is recorded here rather than papered over by widening
some other category to absorb it.

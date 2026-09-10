# Zaad: competitive baseline and the commercially useful subset

Research checked 2026-09-05. This is a **capability/design baseline**, not an
Oracle benchmark, a claim of Oracle feature parity, or evidence of customer
savings. Public vendor documentation describes supported/marketed functions;
it does not reveal proprietary algorithms, enabled modules, implementation
quality, or out-of-sample performance. Unknown is not absent.

This updates, rather than discards, the broader
[previous competitor audit](../remodel/COMPETITORS_AND_SAVINGS.md). Its warning
about confusing inventory release with recurring profit still applies. The
company is **Zaad**; historical repository names are not company branding.

## Executive decision

Build an ERP-adjacent planning assistant for a stock-owning distributor with
one accountable inventory owner. Start with **executable, fill-aware,
time-phased replenishment** and a small set of quote-backed route/source
alternatives. Use rolling replanning, explicit human approval and an
incumbent-first policy comparison. Add stochastic sophistication only when it
improves held-out decisions after equal physical and economic treatment.

Service-target stock reduction, probabilistic forecasts, segmentation,
scenario comparisons and supply-risk response are established category
features. The credible wedge is narrower: low-friction operator reconciliation
plus route-specific evidence that leads to an actionable decision, with its
cost, confidence and recovery plan visible. Whether this is easier to sell
or produces incremental savings is **not yet measured**.

## 1. Oracle: distinguish three different planning jobs

| Product/documented function | What the official material establishes | Zaad implication |
|---|---|---|
| Fusion Inventory Management min/max | Nets available quantities; uses minimum/maximum levels, MOQ, maximum order size and fixed lot multiples | A baseline must net stock and open supply and respect order modifiers, not simply order forecast demand |
| Fusion Replenishment Planning | Segment/item-location policy assignments, min/max, ROP/EOQ, fixed-order-cycle policies, service/day-cover safety stock and overrides | Replenishment policy tuning and executable orders are table stakes |
| Fusion Supply Planning | Time/capacity-aware supply plans, alternates, exception-driven rescheduling and cancellation, demand prioritization | Match distributor-relevant decisions without building factory scheduling |
| Fusion Inventory Optimization, 26C release documentation | Time-phased safety stock, demand/lead variability, service targets, MEIO postponement and risk pooling | Strategic target-stock placement is distinct from operational PO execution |

Primary references:
[Inventory Management min/max](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/famml/how-min-max-planning-replenishment-quantities-are-calculated.html),
[Replenishment policy assignments](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faurp/policy-assignment-sets.html),
[Supply Planning](https://www.oracle.com/scm/supply-chain-planning/supply-planning/),
[26C inventory optimization](https://docs.oracle.com/en/cloud/saas/readiness/scm/26c/sop26c/26C-sales-ops-wn-f45784.htm).

Two details materially change the implementation specification:

- Oracle's 26C strategic inventory-optimization plan uses forecast/manual
  demand, not sales orders, and does not consume existing supplies or apply
  order modifiers when generating its new planned orders. It is not the same
  object as a reconciled live procurement schedule. Zaad must never turn an
  ideal buffer calculation directly into a PO without pipeline netting.
  [26C scope](https://docs.oracle.com/en/cloud/saas/readiness/scm/26c/sop26c/26C-sales-ops-wn-f45784.htm)
- Oracle documents supplier/resource capacity as soft in the cited constrained
  Supply Planning logic: after earlier production/supply and alternates are
  exhausted it may overload capacity to prioritize due dates. That is a
  disclosed planning exception, **not evidence that real capacity exists**.
  Zaad's executable recommendations must use confirmed hard capacities and
  disclose unmet demand, or request approval for an explicitly unconfirmed
  capacity exception. No baseline gets phantom supply.
  [Constraint behavior](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fausp/overview-of-constraint-based-supply-planning.html)

Oracle also documents recommendations to cancel nonfirm unneeded orders,
bring supply forward, push it out, and expose alternate usage. These do not
mean a legally firm vendor order can be canceled without permission or cost.
[26B exceptions](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/fausp/exceptions-in-a-constrained-supply-plan.html)

Replenishment documentation differentiates regular-demand and intermittent
safety-stock inputs, and reports missing-data failures. It does not justify
labeling a normal-distribution quantile as an empirically achieved unit-fill
rate. Product/version-specific service semantics must be verified in any
actual comparator deployment.
[Safety-stock calculation](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/faurp/how-safety-stock-is-calculated-in-oracle-replenishment-planning.html),
[missing-data messages](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faurp/guidelines-for-working-with-plan-messages-for-replenishment.html)

These are Fusion references. They do not silently inherit capabilities from
Oracle E-Business Suite Inventory Optimization or NetSuite. A release note
is not proof a specific customer's tenant has the module or configuration.

## 2. Competent competitors, not strawmen

| Vendor | Verified relevant subset | What Zaad must not claim |
|---|---|---|
| [GAINS](https://gainsystems.com/platform/inventory-optimization/) | SKU/location service policies, demand/supply/lead variability, MEIO, stocking decisions, policy simulation and working-capital tradeoffs | That dynamic inventory/resilience or explicit tradeoffs are unique to Zaad |
| [ToolsGroup](https://www.toolsgroup.com/solutions/inventory-optimization-software/) | Probabilistic inventory positioning, service classes, replenishment timing, network constraints and capital tradeoffs | That all commercial planners use deterministic averages |
| [RELEX](https://www.relexsolutions.com/solutions/fresh-inventory-software/) | Fresh replenishment weighing waste against missed sales margin; inventory expiration information | That a generic shortage penalty is an adequate fresh-food benchmark |
| [Netstock](https://www.netstock.com/pricing/) | ERP-connected inventory planning offered with publicly stated starting pricing of $900/month | That only very large enterprises can buy planning software; $10,800/year is the derived starting subscription, not a like-for-like project quote |
| [Kinaxis](https://www.kinaxis.com/en/solutions/inventory-management) | Inventory/service scenario simulation, risk monitoring and exception dashboards | That competitors cannot compare alternative plans before acting |
| [o9](https://o9solutions.com/solutions/merchandise-planning/allocation-replenishment) | Capacity-aware allocation/replenishment, multi-horizon flow planning and MEIO | That route-aware constrained planning as a broad concept is novel |
| [Blue Yonder](https://blueyonder.com/solutions/supply-chain-planning/inventory-optimization) | Dynamic segmentation, service-aware placement, MEIO and inventory allocation | That high-service stock reduction is an unserved category |
| [SAP IBP](https://learning.sap.com/courses/discovering-sap-ibp-harmonized-planning-area/overview-of-inventory-optimization) | Safety-stock breakdown by demand/lead variability, internal service optimization, historical supplier/transit lead statistics | That a competent ERP-connected baseline ignores uncertain lead times |

Exact customer-specific route-fusion models, calibration quality, cancellation
fees, unit-fill definitions, cash-payment constraints and safety-gate behavior
remain **unverified** from these pages. Ask for written demo answers rather
than converting unavailable evidence into missing features. Vendor marketing
improvement percentages are not Zaad revenue forecasts or independent trials.

## 3. P0/P1/P2/DO NOT BUILD

Priorities are design requirements, **not a claim every item is implemented**.
Implementation status and observed failures belong in the execution/evidence
reports. Do not enable a scenario requiring a deferred constraint.

| Capability | Priority | Required boundary / acceptance |
|---|---|---|
| As-of stock, reservations/backlog, open-PO reconciliation, units and currency | P0 | No duplicate pipeline; posted/known dates distinguished from eventual receipt truth |
| ABC/XYZ and criticality segmentation; item/class service targets | P0 | Operator-owned targets and service metric; do not optimize away contracts |
| Seasonal-naive / moving / intermittent baselines; existing probabilistic forecasts | P0 | Chronological calibration, bias, pinball/WIS and decision-value comparison |
| Separate supplier accepted-quantity fill and stage lead distributions | P0 | Right censor open POs; shrink thin history; do not treat unreceived as permanent zero fill |
| Min/max, reorder-point and order-up-to candidates | P0 | Fill-aware, time-phased, pack/MOQ/calendar/capacity/budget feasible |
| Stock/service curve and replenishment right-sizing | P0 | Cost and achieved unit fill on unseen rolls; infeasible points retained |
| Planned POs and recommendation exceptions | P0 | Near-term actions only; no automatic external order submission |
| Landed cost, missed contribution, holding and cash ledger | P0 | One accounting convention; financing not charged twice |
| Quote-backed alternate source/route shortlist | P0 for resilience claim | Product approval, capacity, transport/cold chain, customs/legal clearance and valid quote |
| Evidence, explainability, overrides, approvals and audit history | P0 | Actor, timestamp, snapshot, reason and stale-data status retained |
| Shelf-life/lot aging and expiry | P0 if perishable; otherwise scoped out | No perishable sales claim before common age-aware settlement works |
| Emergency supply | P0 if used in benchmark | Only physically available, dated, costed alternatives with same recourse for all policies |
| Cancellation, reschedule, de-expedite of existing POs | P1 | Vendor terms, cutoff times, fees and confirmation; until then advise/flag, never enact |
| Item substitution and customer-level backlog allocation | P1 | Explicit acceptable substitutes, conversion factors, SLA/criticality rules and approval |
| Transfers between a few real locations | P1 for multi-location pilot | Both ends, travel time, capacity and cash effects modeled; no stock creation |
| Stocking/nonstock policies and obsolescence treatment | P1 | Demand abandonment/phaseout and supplier MOQ evidence |
| ERP write-back | P1 | Tenant isolation, scoped credentials, idempotency, approval and reversible workflow |
| Full MEIO/risk pooling | P2 | Earn with actual linked-echelon inventory and replenishment data |
| Deep payment-terms/FX optimization, carbon objectives | P2 | Basic dated cost/currency required now; optimize further only for measured decision value |
| Fully integrated multicommodity network flow | P2 | Required only if shortlist/shared-resource formulation misses valuable feasible plans |
| Complete ERP, manufacturing BOM scheduling, vehicle dispatch/TMS replacement | DO NOT BUILD | Partner/integrate; not initial distributor pain |
| Generic geopolitical news portal, uncalibrated risk score, autonomous LLM purchasing | DO NOT BUILD | No verified action/value chain; fabricated precision and authority risks |
| RL, general multistage/DRO platform before operator evidence | DO NOT BUILD now | No demonstrated advantage over simpler causal rolling control |

## 4. Strong normal-engine formulation

### Forecast and supply evidence

Retain existing models until a chronological bake-off earns replacement.
Evaluate seasonal naive, moving/expanding means, smoothing, Croston/SBA/TSB
for appropriate intermittent series and existing quantile/boosted forecasts.
Select by segment with nested time splits: calibration, bias, pinball/WIS,
zero-demand behavior **and** same-ledger replenishment outcomes. Account for
lost-sales censoring; invoiced sales are not necessarily unconstrained demand.
Do not make MAPE the selector for zero-heavy demand.

PO ordered, confirmed, received and accepted quantities are different stages.
Estimate accepted fill from reconciled PO lines including partial receipts;
estimate dispatch, transit and receiving delays separately where timestamps
exist. Open orders are censored observations, not completed long leads or
permanent failures. Thin suppliers borrow strength from a relevant segment
with visible sample sizes. Five receipts cannot substantiate a 99.9% tail.

### Required simple policy

At review time, construct each SKU-location's dated inventory trajectory from
usable on-hand, known reservations/backlog and **as-of expected open receipts**.
Do not add all future receipts to today's usable stock. The aggregate
inventory-position check is a reconciliation aid, not a substitute for dates:

`position = usable on-hand + expected outstanding receipts - unserved obligations`.

For a periodic-review base-stock candidate, search a modest grid of stock
targets/order-up-to parameters using training-only simulated/replayed lead,
demand and fill paths. A mean-fill division is a useful starting candidate:
`ordered quantity ≈ desired additional accepted units / estimated fill`.
It is **not** the final feasible solution: respect receipt timing, supplier
capacity, MOQ/case rounding, ordering calendar and shared cash/space, then
measure resulting shortages. Never allocate the residual to invented capacity.

Measure the candidate's unit fill as
`1 - total units not served by their required time / total requested units`.
Define whether later backlog service counts before running the test. A
zero-demand evaluation window is N/A for service, not a fabricated 100% pass.
An alpha demand quantile targets a distributional coverage event under its
assumptions; it does **not** directly calibrate alpha unit fill. A periodic
stock policy needs its own replenishment-cycle evaluation. Line fill, order
fill, availability and OTIF require their respective event/line data.

At each approved target, retain the minimum-cost **feasible** candidate and
show inventory investment versus expected unit fill, then its untouched
holdout outcome. Do not impose a service reduction without operator approval;
already-balanced operators should frequently receive no change.

### One economic ledger

Use either a complete profit/cash-flow ledger or a carefully derived
incremental-loss ledger. Do not mix both. A clear full-ledger finite-horizon
objective is:

`min E[new purchase/landed commitments + noncapital holding + financing`
`      + disposal/expedite/transfer/change costs + explicit SLA penalties`
`      - realized sales contribution before modeled purchase costs`
`      - conservative residual inventory/pipeline value]`.

The sales term must be precisely defined: use sales revenue less only costs
**not already charged elsewhere**, not a margin already net of the same
procurement. If charging purchases in full, do not also charge their full
unit cost as an additional writeoff; physical expiry removes residual value,
and only incremental disposal is added. Do not additionally charge missed
gross margin after already modeling lost sales revenue and saved procurement.
Opening asset value is common/sunk for the decision but must be included in
reconciled accounting and terminal comparisons. Do not reward hoarding with
terminal valuation above justified realizable value; test longer rollouts and
terminal-value sensitivity.

Cash feasibility uses dated payment commitments/deposits and credit limits,
not merely warehouse inventory value. Financing is separated from storage,
handling and insurance, or documented as included in an all-in carry rate.
Explicitly include route freight, duties and nonrecoverable taxes once;
recoverable taxes affect cash timing rather than permanent operating cost.
Any simplified ledger must list omitted terms before its results are quoted.

The CFO view has four nonadditive/appropriately reconciled lines: one-time
working-capital release; recurring operating benefit; temporary resilience
investment; modeled protection benefit. Avoided tail loss is not booked
realized savings. A gainshare fee applies only to an agreed attributable
benefit definition, never automatically to every dollar released each year.

## 5. Method choice: MPC is not a competing probability model

| Method | Use / tradeoff | Decision |
|---|---|---|
| Feasible inventory-position/base-stock | Strong cheap normal baseline; shared resources need allocation step | Required |
| Expected-value optimization | Captures costs/capacities; may miss uncertainty interactions | Required comparator |
| SAA two-stage SP | Scenario-based route/order choice; finite samples and recourse information can mislead | Candidate, equal settlement and held-out test |
| CVaR SP | Explicit monetary tail-loss aversion; may buy expensive unnecessary stock | Opt-in risk appetite; report incremental protection cost and tail reduction separately |
| Chance constraints | Contractually defined probability of failure | Later unless actual SLA semantics/data justify; expected unit fill is not a chance constraint |
| Budgeted robust optimization | Transparent stress budget with bounded errors | Useful stress comparator, not default proof of robustness |
| DRO | Accounts for distribution ambiguity under a specified set/radius | Research until radius calibration and incremental decision gain demonstrated |
| Multistage SP | Causal scenario-tree actions | Defer dimensional burden; two-stage future recourse cannot claim multistage causality |
| Rolling-horizon MPC | Observe, replan, commit near term, settle, repeat | Required execution architecture for any selected policy |
| Hybrid portfolio | Incumbent first, complexity only with cost/service/downside evidence | Chosen, no claim future harm is impossible |

Existing mathematical references and caveats remain in
[methods and architecture](../remodel/METHODS_AND_ARCHITECTURE.md). In
particular, distribution reweighting is not automatically a solved
Wasserstein-DRO program with its theoretical guarantees.

Route construction should first filter a bounded number of supplied or
k-shortest feasible paths by approved mode/product, direction, carrier,
departure availability, customs/legal clearance, cold-chain compatibility,
capacity and valid quotes. Feed those alternatives, time-varying lead/fill
scenarios and shared-edge capacities into inventory/source selection. Do not
rank by distance alone. Use min-cost network flow when actual shared-edge
competition needs it; full multicommodity stochastic flow is not a first
customer requirement. Path generation itself never authorizes a booking.

**Bounded prototype option:** enumerate a frozen, interpretable set of
closed-loop inventory policies (base-stock target, approved route split,
expedite trigger and recovery target). Evaluate each with common random
numbers and the same causal, work-conserving simulator, using only the state
available at each future review within the simulated path. Select with
separate confirmation evidence and execute only the next review action.
Work-conserving service means usable unreserved stock serves due demand;
the policy cannot deliberately withhold it to exploit aggregate-horizon
service arithmetic. Reservations/priorities, if implemented, must be explicit.
This finite-policy stochastic search is often more transparent than a long
open-loop SAA order schedule. It is **not** a globally optimal continuous-action
stochastic program, multistage optimization, or proof of performance outside
the finite policy set. Risk-aware variants must beat their otherwise-identical
risk-blind counterparts before credit is assigned to external information.

## 6. Origin-specific route topology, not a regional alarm

The following are **structural examples**, not currently bookable itineraries
or fitted probabilities. Infer chokepoint membership from an explicit path;
verify actual transshipments/carrier operations before use. The EIA maps
establish the geography of Suez, Bab el-Mandeb and Hormuz, not container
delay probabilities. [EIA chokepoint geography](https://www.eia.gov/international/content/analysis/special_topics/World_Oil_Transit_Chokepoints/)

| Origin → destination / possible path | Exposure that follows from this path | What does not automatically follow |
|---|---|---|
| East Asia → Indian Ocean → Bab el-Mandeb → Aqaba → Amman | Bab el-Mandeb, Red Sea/Aqaba and inland Jordan | Suez or Hormuz exposure |
| Mediterranean origin → Suez → Aqaba → Amman | Suez and northern Red Sea/Aqaba | Bab el-Mandeb exposure |
| East Asia → Hormuz → Jebel Ali → Saudi road → Riyadh | Hormuz, Jebel Ali and actual border/road | Red Sea or Suez exposure |
| East Asia → Bab el-Mandeb → Jeddah → Riyadh | Bab el-Mandeb, Jeddah and Saudi inland path | Hormuz exposure |
| East Asia → Khor Fakkan/Fujairah → UAE inland | Port/road capacity on Gulf of Oman side | Hormuz, absent a separate Gulf transshipment leg |
| East Asia → Salalah/Sohar → quoted inland destination | Named Omani port plus actual road/borders | An always-open route to every GCC country |
| Mediterranean supplier → Beirut or North African Mediterranean port | Named port, origin and inland corridor | Suez/Bab el-Mandeb for an intra-Mediterranean sailing |
| Supplier in Turkey → specifically approved land crossings → Jordan/Iraq/GCC buyer | The actual crossings, permissions and shared road segments | That an overland route is legally feasible, independent or faster merely by drawing a line |
| Asia → LA/Long Beach → western rail/road → US distribution center | Pacific port plus inland rail/road dependencies | Panama or Suez exposure |
| Asia → Panama → US East/Gulf port → inland | Panama plus named port and inland route | Identical risk to an East Coast itinerary sailing via Suez/Cape |
| Europe → New York/New Jersey or Savannah → inland | Atlantic port/rail/road | Panama/Suez solely because destination is the US |

The prompt's China→Jebel Ali and China→Jeddah example can share upstream
carrier/hub congestion, but the **direct paths have different chokepoints**.
A Red Sea event must not automatically shock both. Conversely different port
names do not guarantee independence if both use the same transshipment hub,
ocean service, land border or inland bottleneck. Model shared-edge/common
cause shocks, not a country-wide Kendall-tau label.

Actual available alternatives are time-sensitive. Maersk's March 2026
landbridge notice listed multiple GCC connections. Its August 14 update
paused some Jeddah and Omani cross-border connections while continuing to
list Saudi Jeddah→Riyadh/Dammam and Aqaba→Iraq services subject to capacity
and acceptance. A March notice therefore cannot establish September booking
availability. Store carrier, direction, cargo category, published/known time,
expiry and superseding notice; obtain a current operator quote before an
action. [March notice](https://www.maersk.com/news/articles/2026/03/18/middle-east-landbridge-solutions-maersk),
[August operational update](https://www.maersk.com/news/articles/2026/08/14/middle-east-operational-update-42)

US port alternatives likewise require complete inland quotes. Los Angeles
documents on-/near-dock rail connectivity, and Savannah documents CSX/NS
access into inland markets. These establish possible transport links, not
equal lead time, rates or available capacity. [Los Angeles rail](https://portoflosangeles.org/business/supply-chain/rail),
[Savannah terminal](https://gaports.com/facilities/port-of-savannah/garden-city-terminal/)
Port labor, hurricanes, customs and rail bottlenecks should affect only the
dated exposed legs; a West Coast substitution may still share inland hubs.

Saudi Arabia, UAE, Kuwait, Qatar, Bahrain and Oman therefore need separate
port/land graphs. Jordan, Iraq and Lebanon need explicit crossing and
port-access records. Egypt, Morocco, Algeria and Tunisia need origin-specific
Mediterranean/Atlantic/Red Sea paths, not inherited Gulf disruption rates.
No fitted probabilities or sales claims transfer from Project A's US grower
weather model to any of these distribution networks.

## 7. Commercial traceability and initial ICP

| Market pain | Actual decision | Method | Necessary data | Feature → measurable value |
|---|---|---|---|---|
| Excess stock despite good service | Buy less, defer approved replenishment | Calibrated base-stock/frontier | Stock, open POs, demand, target and costs | Lean recommendation → inventory value/carry down at noninferior service |
| Buyer repeatedly receives short/late | Order timing/quantity or quote-backed source split | Fill/lead model + causal rolling comparison | PO lines, receipt/acceptance dates, capacity and quotes | Supply-aware PO → missed units and expedite cost down net of carry |
| Relevant import lane deteriorates | Pay for an alternate, bring order forward, or do nothing | Path exposure + bounded scenarios + economic comparison | Shipment itinerary, as-of evidence, feasible alternatives and decision deadline | Protect action → net contribution protected after premium/false alarms |
| Scarcity cannot be fixed in time | Allocate scarce units | Constrained approved-priority allocation | Customer demand, SLA, substitutes and contribution | Allocation → transparent policy compliance, not fictitious full service |
| Disruption ends while stock is high | Stop new protection; run down stock; approved deferral | State persistence/hysteresis + normal-policy re-evaluation | Current receipts, pipeline, expiry and order terms | Recover action → temporary capital/carry unwinds without renewed shortage |
| Planner cannot explain optimizer | Approve, override, or abstain | Reconciled same-ledger alternatives and provenance | Snapshot, scenario assumptions, reasons and actor logs | Decision card → acceptance/override quality, not model accuracy alone |

Initial ICP remains a **screening hypothesis**: roughly $20M–$250M revenue,
meaningful owned inventory, hundreds/thousands of SKUs, an existing ERP but
material buyer/rule/spreadsheet replenishment, accessible PO/receipt history,
approved alternative supply channels, and one accountable owner. Revenue is
not sufficient: inventory investment, avoidable loss, decision lead time and
actual ability to change the plan determine value.

Start with one shelf-stable importer/distributor, one decision owner and a
small number of locations. This avoids pretending incomplete age-aware
settlement serves perishable operations. Jordan-first is a relationship/data
access hypothesis from Project B, not evidence of easier procurement or a
larger underserved market. Saudi/UAE named deployments in the earlier audit
disprove an empty-market thesis. The US shares the mathematical machinery,
not the same geography, costs or calibrated probabilities.

Disqualify a pilot if there is no actionable decision before the signal,
unreconciled core stock/PO data, no inventory ownership/benefit owner, no
feasible alternate for the resilience claim, or a fully functioning incumbent
that Zaad cannot improve. If inventory right-sizing works but external signals
add no held-out value, sell the former and do not fabricate a resilience moat.
If both lose to a competent incumbent, abstention is correct but not product
market fit.

The next proof is an operator-approved shadow pilot, not a new headline TAM:
freeze incumbent rules, monetary ledger, service metric and decision times;
replay normal/disrupted/false-alarm/recovery periods causally; record every
rejected action and implementation burden; then agree the attainable benefit
and fee. Any pricing/savings promise remains contingent on this evidence.

# ZAAD Optimizer Product Strategy, Industry Gap Analysis, and Long-Term Roadmap

**Status:** Strategy / product architecture document  
**Repository baseline:** `main` at `ebcd1d0`  
**Verified:** 2026-09-11  
**Audience:** Founders, optimization engineering, product, technical recruiting, future design reviews  
**Validation status of ZAAD:** **ENGINEERING VALIDATED; NOT REAL-DATA VALIDATED.** No customer savings claims are made in this document.

---

## 1. Executive summary

ZAAD should aim to become the **decision layer between a distributor's ERP and its real-world operating decisions**.

The long-term product is broader than inventory optimization. The coherent decision surface is:

1. how much protection to hold,
2. when and how much to buy,
3. where inventory should sit,
4. which suppliers should provide it,
5. what should change when new information arrives,
6. what to do with open commitments already in motion,
7. who gets scarce inventory,
8. how uncertainty should be modeled,
9. which route, mode, port, carrier, sailing, and load configuration to use,
10. how limited working capital should be allocated,
11. how product lifecycle, substitution, and supersession should change the plan.

The industry already treats many of these decisions as connected planning problems. ToolsGroup markets probabilistic forecasting, replenishment, service-driven multi-echelon inventory optimization (MEIO), service-class optimization, and connected supply planning.[^tg-meio] Slimstock markets automatic replenishment, MEIO, allocation, network balancing, open-to-buy, and shelf-life-aware planning.[^slim-inventory] Kinaxis explicitly lists supply/demand allocation, sourcing mix, order promising, transportation, and inventory optimization as optimization decisions.[^kinaxis-opt] Blue Yonder markets order promising and fulfillment-path optimization.[^by-order] Lokad documents probabilistic demand/lead-time modeling, cross-SKU MOQ/container constraints, financially prioritized purchasing, and capital constraints.[^lokad-inventory][^lokad-moq][^lokad-economic] Netstock and RELEX document forecasting, replenishment, lifecycle, promotion, open-order, and supersession workflows.[^netstock-forecast][^netstock-openpo][^netstock-super][^relex-home][^relex-promo]

Therefore, ZAAD is **not missing a secret single algorithm**. It is missing several operating decisions that become essential if the company wants to own the full importer decision chain.

The recommended expansion is:

- **P4 — Adaptive Recourse**
- **P4B — Open PO / Commitment Recourse**
- **P5 — ATP + Scarce-Supply Allocation + Economic Service Classes**
- **P6 — Decision-Aware Uncertainty + Demand/Supply Calibration**
- **P7 — Import Logistics Optimization**
- **P8 — Container & Load Portfolio Optimization**
- **P9 — Portfolio Capital Optimization**
- **P10 — Product Lifecycle, Substitution & Supersession**

Two capabilities should be treated as **foundational planning infrastructure rather than standalone phases**:

- forecast consumption / firm-order netting,
- a canonical shared state + economic ledger used by every optimizer.

This roadmap should **not** delay market work. Real operator interviews, historical diagnostics, data onboarding, and paid/shadow pilots should run in parallel. Feature sequencing should be allowed to move when actual operator evidence shows that one decision class has materially higher value.

---

## 2. Current ZAAD decision stack

ZAAD already has a serious optimization core. The current validated stack is:

### P0 — Protection & Recovery

**Business question:** How much inventory protection is economically justified under uncertainty, and when should temporary protection come back down?

P0 owns disruption protection, recovery behavior, service protection, incumbent comparison, and abstention. The important design principle is that uncertainty does not automatically imply more inventory: protection must earn its economic cost.

Internal evidence: [`docs/zaad_full/evidence/v8/P0_CLOSEOUT.md`](./evidence/v8/P0_CLOSEOUT.md).

### P1 — Purchasing Economics

**Business question:** When should we order, how much should we order, and should we order at all?

P1 owns dynamic cadence and total purchasing commitment under real purchasing economics, including MOQ, MOV, packs, pallets, fixed ordering economics, freight effects, payment timing, carrying/financing economics, and continuation value.

Internal evidence: [`docs/zaad_full/evidence/p1/P1_CLOSEOUT.md`](./evidence/p1/P1_CLOSEOUT.md).

### P2 — Multi-Echelon / Network Optimization

**Business question:** Where should inventory sit across the network?

P2 owns network inventory, transfers, shared stock, location-level service consequences, cross-location conservation, and the network consequences of correlated demand.

Internal evidence: [`docs/zaad_full/evidence/p2/P2_CLOSEOUT.md`](./evidence/p2/P2_CLOSEOUT.md).

### Three-Sector Physics

The same decision engine is conditioned by sector-specific physical reality:

- **COMMERCIAL**
- **PRODUCE**
- **MEAT_SEAFOOD**

Sector physics covers cases/pallets, shelf life, age at receipt, FEFO, cold-chain/storage/lane eligibility, and other physical constraints without forking the core optimizer into separate products.

Internal evidence: [`docs/zaad_full/evidence/sectors/SECTOR_PHYSICS_CLOSEOUT.md`](./evidence/sectors/SECTOR_PHYSICS_CLOSEOUT.md).

### P3 — Supplier / Sourcing Portfolio Optimization

**Business question:** Which approved supplier or supplier mix should fulfill the purchase commitment?

P3 owns source decomposition, supplier capacity, shared capacity, supplier MOQ/MOV, source-share constraints, switching cost, payment/source economics, and declared common-cause source risk. The objective is not forced diversification; it is better total economics under supply uncertainty.

Internal evidence: [`docs/zaad_full/evidence/p3/P3_CLOSEOUT.md`](./evidence/p3/P3_CLOSEOUT.md).

P3's production performance closure is recorded in [`docs/zaad_full/evidence/p3/perf_closure/P3_PRODUCTION_PERF_AFTER.md`](./evidence/p3/perf_closure/P3_PRODUCTION_PERF_AFTER.md). The original `p3-release-runtime` remains historical; the corrected production runtime is recorded by `p3-performance-closure-runtime`.

### Current strategic interpretation

P0-P3 answer four linked decisions:

> **How much protection? → When/how much to buy? → Where should it sit? → Who should supply it?**

The next phases should extend this same economic system rather than create unrelated optimizers.

---

## 3. What the industry evidence says

### 3.1 Probabilistic uncertainty is already an industry baseline

ToolsGroup publicly describes full probability distributions for SKU-location demand and explicitly positions probabilistic forecasting as input to inventory, replenishment, and service decisions.[^tg-forecast] Lokad likewise documents probabilistic demand and probabilistic lead-time forecasting as inputs to inventory decisions.[^lokad-inventory]

**Implication for ZAAD:** probabilistic uncertainty is necessary, but it is not by itself a differentiated market position. ZAAD's differentiation has to come from the decisions it connects, the importer physics it models, how it validates recommendations, and how it abstains when the incumbent is already efficient.

### 3.2 MEIO, allocation, and network balancing are established capabilities

ToolsGroup describes network-wide MEIO that jointly considers inventory positioning rather than optimizing each node independently.[^tg-meio] Slimstock markets MEIO, allocation, transfers, and network balancing.[^slim-inventory][^slim-network]

**Implication for ZAAD:** P2 is strategically necessary and correctly placed. The differentiator is not the existence of MEIO; it is how ZAAD couples network decisions to purchasing, sourcing, perishability, importer constraints, and future recourse.

### 3.3 Replenishment already means "when and how much," not merely safety stock

ToolsGroup states that its replenishment recommendations determine when, where, and how much inventory to replenish.[^tg-replen] Slimstock describes order recommendations using demand, lead times, MOQ, supplier constraints, and grouping/shipping logic.[^slim-supply] Netstock markets recommended orders that combine forecasts, current stock, lead time, and safety-stock requirements.[^netstock-order]

**Implication for ZAAD:** P1 is core table stakes, but ZAAD's dynamic ordering cadence and total-economic treatment remain useful product framing. "Fixed calendars are a convenience, not an optimization strategy" remains a strong operating principle.

### 3.4 Order promising and scarce-supply allocation are core planning/execution decisions

Kinaxis explicitly lists supply/demand allocation and ATP/CTP order promising as optimization decisions, including prioritization based on margin, priority, SLAs, and scarce supply.[^kinaxis-opt] Blue Yonder markets order promising and fulfillment optimization that balances availability, route, speed, inventory utilization, and cost.[^by-order]

**Implication for ZAAD:** P5 is not optional if ZAAD intends to influence downstream execution. It should be treated as an essential optimizer capability, not a distant add-on.

### 3.5 Transportation decisions are part of modern supply-chain optimization

Kinaxis explicitly lists transportation optimization: route, carrier, mode mix, landed cost, lead time, and delivery windows.[^kinaxis-opt] Lokad lists purchase decisions that may include transportation mode choice, including sea versus air, alongside supplier and order constraints.[^lokad-decision]

**Implication for ZAAD:** for an importer-focused product, treating transport only as a coefficient is eventually insufficient. Route/mode/port/sailing decisions should become explicit decisions in the optimizer.

### 3.6 Container and cross-SKU order composition are real optimization problems

Lokad documents cross-SKU MOQ constraints combined with container constraints and supplier-level target container capacity.[^lokad-moq] Its technical and strategy material also treats containerized purchasing as a constrained composition problem across SKUs.[^lokad-container][^lokad-decision]

**Implication for ZAAD:** P8 should be a first-class importer capability. Container fill cannot remain only a freight threshold if the customer actually controls container composition.

### 3.7 Capital constraints and open-to-buy belong inside inventory decisions

Slimstock markets open-to-buy as a capability for aligning orders with budgets and cash-flow constraints.[^slim-inventory] Lokad explicitly treats capital availability as a supply-chain constraint and documents financially prioritized purchasing under a budget.[^lokad-economic][^lokad-priority]

**Implication for ZAAD:** working-capital economics should eventually move from a cost coefficient to a portfolio-level hard constraint when a customer has limited cash/credit.

### 3.8 Product lifecycle, obsolescence, and supersession are mature requirements

ToolsGroup describes lifecycle, phase-in/phase-out, supersession, and last-time-buy control in service-parts planning.[^tg-lifecycle] Netstock documents supersession logic that transfers history from old to replacement items, prevents unwanted orders for discontinued items, and consolidates stock/open orders through the transition.[^netstock-super] RELEX describes new-product introductions, seasonal changes, range changes, and end-of-lifecycle inventory workflows.[^relex-electronics][^relex-clearance]

**Implication for ZAAD:** commercial-goods customers with changing catalogs will eventually require lifecycle and substitution logic. This should be explicit in P10.

### 3.9 Promotions, seasonality, lost sales, and lifecycle effects must be part of uncertainty generation

ToolsGroup describes seasonality, promotions, external signals, intermittent/long-tail demand, and full probability distributions.[^tg-forecast] Netstock documents lost-sales compensation, promotions, seasonal effects, and per-item forecasting models.[^netstock-forecast][^netstock-lost] RELEX describes promotion forecasting, store-level signals, seasonality, new products, and replenishment consequences.[^relex-promo][^relex-connected]

**Implication for ZAAD:** P6 should be broader than model-risk scoring. ZAAD needs a credible demand/supply uncertainty layer capable of ingesting raw operator history when a customer does not already have a probabilistic planning system.

### 3.10 Forecast consumption is basic planning infrastructure

Oracle defines forecast consumption as replacing forecast demand with actual sales-order demand so the same demand is not counted twice.[^oracle-consumption] SAP similarly documents forecast consumption as the mechanism controlling how forecast and actual demand are considered in supply planning.[^sap-consumption]

**Implication for ZAAD:** forecast consumption / firm-order netting should be implemented as foundational planning logic before broad real-customer deployment. It should not be marketed as a glamorous optimizer phase, but missing it can corrupt every downstream recommendation.

### 3.11 Open purchase orders are part of the decision state, not just history

Netstock's planning documentation explicitly uses stock on hand, open purchase/sales orders, receipts, and projected orders in replenishment calculations.[^netstock-projection] Its exception guidance recommends expediting or bringing forward existing purchase orders when projected stockouts occur and identifies surplus open orders that may create excess.[^netstock-openpo]

**Implication for ZAAD:** once P4 establishes valid recourse and information timing, ZAAD should optimize economically feasible interventions on open commitments rather than treating every committed PO as permanently immutable.

---

## 4. Competitive capability matrix

This table records **publicly described capabilities**, not an independent ranking of implementation quality.

| Capability | ToolsGroup | Slimstock | Netstock | Kinaxis | Blue Yonder | Lokad | RELEX |
|---|---|---|---|---|---|---|---|
| Probabilistic / advanced demand uncertainty | Yes[^tg-forecast] | Forecasting platform[^slim-platform] | Per-item forecasting + demand signals[^netstock-forecast] | Broader planning platform | Broader planning platform | Probabilistic demand + lead time[^lokad-inventory] | AI forecasting + demand signals[^relex-home] |
| Replenishment recommendations | Yes[^tg-replen] | Yes[^slim-supply] | Yes[^netstock-order] | Yes / supply planning | Fulfillment-focused | Purchase optimization[^lokad-decision] | Yes[^relex-home] |
| MEIO / network inventory | Yes[^tg-meio] | Yes[^slim-inventory] | Multi-location planning | Yes / inventory optimization[^kinaxis-opt] | Fulfillment network decisions | Can be modeled quantitatively | Multi-echelon deployments documented[^relex-home] |
| Allocation / ATP / promising | Service-class + network positioning[^tg-meio] | Allocation + balancing[^slim-inventory] | Distribution planning | Explicit ATP/CTP + allocation[^kinaxis-opt] | Explicit order promising[^by-order] | Decision modeling possible | Allocation documented in retail planning |
| Supplier/source optimization | Supplier constraints/collaboration[^tg-meio] | Supplier rules/constraints[^slim-supply] | Supplier performance / order logic | Explicit sourcing mix[^kinaxis-opt] | Broader order sourcing | Explicit supplier purchasing decisions[^lokad-decision] | Supply planning |
| Route/mode transportation decision | Connected planning, not core claim here | Limited in cited planning pages | Shipping-cost optimization | Explicit route/carrier/mode optimization[^kinaxis-opt] | Fulfillment-path optimization[^by-order] | Explicit mode choice (sea/air)[^lokad-decision] | Logistics inputs, not core cited claim |
| Container / cross-SKU order composition | Not core cited claim | Grouping/shipping logic[^slim-supply] | Shipping-cost optimization | Can be modeled in execution stack | Not core cited claim | Explicit MOQ + container constraints[^lokad-moq] | Not core cited claim |
| Capital / budget constraint | Working-capital balancing[^tg-meio] | Open-to-buy[^slim-inventory] | Cash-flow visibility | Financial constraints in planning | Cost-to-serve | Explicit capital constraint[^lokad-economic] | Financially linked planning |
| Lifecycle / supersession | Explicit lifecycle + supersession[^tg-lifecycle] | Product lifecycle stocking policy[^slim-inventory] | Explicit supersession[^netstock-super] | Supersession in service parts | Retail lifecycle capabilities | Modelable | New-product / lifecycle / clearance[^relex-electronics][^relex-clearance] |
| Perishability / shelf life | Industry-specific support | Explicit fresh/shelf-life management[^slim-inventory] | Item policy dependent | Industry solution dependent | Industry solution dependent | Modelable | Fresh / expiry planning documented[^relex-home] |

**Strategic reading:** ZAAD should not market ordinary category features as unique. The stronger wedge is the **importer-specific coupling and proof discipline**: purchase + source + network + recourse + correlated physical risk + historical replay + incumbent-first abstention.

---

## 5. The essential optimizer features ZAAD is still missing

The gaps below are ordered by strategic importance for an import-heavy distribution wedge.

| Capability | Current ZAAD status | Priority | Recommended home |
|---|---|---:|---|
| Adaptive recourse / non-anticipative future actions | Planned | Critical | P4 |
| Open-PO / commitment intervention | Missing | Critical | P4B |
| ATP / scarce-supply allocation / promise dates | Planned | Critical | P5 |
| Economic service segmentation | Partial | Critical/High | P5 |
| Demand + supply uncertainty calibration | Partial | Critical | P6 |
| Forecast consumption / firm-order netting | Not yet first-class | Critical infrastructure | Foundation |
| Route / port / carrier / sailing / mode optimization | Partial parameters only | Critical for importer wedge | P7 |
| Cross-SKU container/load composition | Partial economics only | High | P8 |
| Portfolio cash / credit / working-capital rationing | Partial economic treatment | High | P9 |
| Product lifecycle / supersession / substitution | Missing | High | P10 |
| Promotions / events | Inputs exist conceptually | Medium/High | P6 |
| Returns / reverse logistics | Missing | Medium; vertical-dependent | Later / evidence-gated |
| Production planning / detailed scheduling | Missing | Do not prioritize | Out of current wedge |
| S&OP / IBP suite | Missing | Do not prioritize | Partner/integrate |
| Price / markdown optimization | Missing | Do not prioritize | Separate product category |

---

## 6. Recommended expanded roadmap

## P4 — Adaptive Recourse

**Question:** What should ZAAD change later when new information becomes observable?

P4 should introduce:

- explicit review epochs,
- observable state,
- information sets,
- non-anticipativity,
- conditional future purchases,
- conditional source changes for uncommitted quantity,
- conditional transfers,
- conditional protection/recovery actions,
- static vs adaptive vs perfect-information diagnostics.

The governing rule is:

> **Commit only what must be committed now. Preserve flexibility where waiting has economic value.**

P4 must never use latent future information. If two worlds are observationally identical at a decision epoch, they must share the same recourse action.

**Why this is foundational:** every later "change the plan after something happens" feature depends on a correct information structure. Open-PO intervention, rerouting, emergency sourcing, and late customer allocation all require the optimizer to know what was observable when the decision was made.

---

## P4B — Open PO / Commitment Recourse

**Question:** What can still be changed about commitments already in motion?

The initial action set should be evidence-gated and operationally explicit:

- **KEEP**
- **DEFER**
- **EXPEDITE**
- **REDUCE**
- **CANCEL**
- **SPLIT**
- **REROUTE**

No action is free. Each action requires declared feasibility and economics such as:

- supplier cancellation policy,
- deposit already paid,
- production stage,
- cancellation fee,
- expedite premium,
- vessel cutoff,
- latest change date,
- rescheduling penalty,
- remaining supplier capacity,
- customer/service consequence.

The existing P4 rule "committed = committed" is correct for P4 V1. P4B should relax that only when the operator explicitly declares that a commitment remains modifiable.

**Why it matters:** importer working capital is often committed weeks or months before receipt. A system that optimizes only new orders while ignoring economically modifiable open POs can recommend the wrong action.

---

## P5 — ATP, Scarce-Supply Allocation, and Economic Service Classes

**Question:** When supply is constrained, who gets what inventory, when, and under what promise?

P5 should cover:

- available-to-promise (ATP),
- capable-to-promise where the data supports it,
- customer/order priority,
- promised dates,
- service class,
- SLA / OTIF penalty,
- margin,
- strategic account weight,
- partial fulfillment,
- backorder,
- future-arrival awareness,
- substitutions,
- cross-location fulfillment,
- expedite options where allowed.

The key progression is from fixed service targets to **economic service differentiation**.

Instead of assuming every SKU/customer receives the same fill target, P5 should allow service protection to reflect declared economic consequences such as:

- contractual penalties,
- margin,
- criticality,
- customer tier,
- substitution availability,
- strategic commitments.

Kinaxis and ToolsGroup both publicly frame service/priority decisions as explicit optimization concerns rather than a universal fixed service percentage.[^kinaxis-opt][^tg-meio]

---

## P6 — Decision-Aware Uncertainty + Demand/Supply Calibration

**Question:** Which uncertainty representation produces the best downstream decisions?

P6 should become the uncertainty engine underneath P0-P5 rather than a narrow forecast-accuracy project.

### Demand uncertainty

Support or ingest models for:

- trend,
- seasonality,
- intermittent/lumpy demand,
- promotions,
- special events,
- stockout censoring,
- lost-sales correction,
- new-item / cold-start behavior,
- customer-level changes,
- hierarchical reconciliation where useful,
- cross-SKU / cross-location covariance.

### Supply uncertainty

Estimate or ingest:

- supplier fill distributions,
- lead-time distributions,
- partial-fill behavior,
- delay tails,
- supplier covariance,
- shared-plant / route / port / carrier dependence,
- yield / usable-quantity distributions for perishables.

### Model evaluation

Do not optimize only for RMSE, MAE, or forecast bias.

Evaluate:

- calibration,
- probability integral transform / coverage diagnostics where appropriate,
- distributional stability,
- decision loss,
- regret versus a benchmark policy,
- service consequences,
- total economic consequence.

The core ZAAD angle should remain:

> **A statistically better forecast can still produce a worse operating decision.**

---

## P7 — Import Logistics Optimization

**Question:** Which physical inbound path should carry the commitment?

Potential decision variables:

- transport mode,
- route,
- origin port,
- destination port,
- carrier,
- sailing,
- departure date,
- transshipment path,
- alternate destination,
- expedite / premium mode,
- consolidation choice.

The optimizer should connect:

> **source + quantity + timing + route + mode**

rather than selecting a supplier while treating transport as a fixed surcharge.

Constraints and economics may include:

- route capacity,
- mode capacity,
- carrier availability,
- sailing calendars,
- cutoff dates,
- port closures,
- transit-time distribution,
- delay correlation,
- freight,
- handling,
- demurrage/detention where data is reliable,
- customs/border timing,
- customer/service consequences,
- product temperature/state feasibility.

Kinaxis and Lokad both explicitly position transportation or mode choice as part of the supply-chain decision surface.[^kinaxis-opt][^lokad-decision]

---

## P8 — Container & Load Portfolio Optimization

**Question:** Given finite container/load capacity, which mix of SKUs deserves the space?

This should be a **cross-SKU portfolio decision**, not a single-SKU order constraint.

Relevant state:

- cube,
- weight,
- pallet positions,
- pack/pallet integrity,
- hazardous/incompatible product rules where relevant,
- temperature state,
- supplier,
- container type,
- existing partial load,
- sailing cutoff,
- demand uncertainty,
- shelf life,
- service risk,
- working capital.

The core optimization is:

> **Which incremental units create the highest expected economic value per constrained unit of container capacity?**

This should connect directly to P1 and P3. Purchase quantity and source selection are often not separable from load construction.

Lokad's public documentation explicitly treats MOQ and container constraints as cross-SKU purchasing constraints.[^lokad-moq][^lokad-container]

---

## P9 — Portfolio Capital Optimization

**Question:** If the economically desirable purchases exceed available cash or credit, where should limited capital go?

Make capital a first-class shared constraint when the customer declares one:

- cash budget,
- credit line,
- supplier credit,
- letter-of-credit limit,
- payment date,
- currency exposure where supported,
- category/customer commitments,
- inventory borrowing base if relevant.

The optimizer should choose the portfolio of commitments that maximizes expected economic value subject to the constraint.

This is different from merely including financing cost. A capital-cost term says money is expensive. A hard portfolio constraint says **the money is unavailable beyond a limit**.

Slimstock markets open-to-buy / budget-constrained ordering, and Lokad explicitly documents capital availability as a supply-chain constraint.[^slim-inventory][^lokad-economic]

---

## P10 — Product Lifecycle, Substitution, and Supersession

**Question:** How should the plan change when the identity or commercial life of the product changes?

Support:

- new-item introductions,
- phase-in,
- phase-out,
- discontinuation,
- end-of-life,
- replacement SKU,
- one-way supersession,
- two-way substitution where operationally valid,
- cannibalization,
- seasonal lifecycle,
- last-time-buy decisions.

This matters because a demand decline caused by product phase-out is not the same thing as a stochastic demand decline in a continuing SKU.

Netstock, ToolsGroup, and RELEX all publicly document lifecycle/supersession/phase-out workflows.[^netstock-super][^tg-lifecycle][^relex-clearance]

---

## 7. Foundational capabilities that should not wait for a numbered phase

### 7.1 Forecast consumption / firm-order netting

This must become explicit before broad real-data deployment.

If forecast demand already includes expected customer demand, a firm customer order should not automatically be added on top of the forecast. Oracle and SAP both document forecast-consumption logic specifically to prevent overstatement/double counting of demand.[^oracle-consumption][^sap-consumption]

ZAAD should define:

- forecast bucket,
- backward/forward consumption windows,
- customer/item/channel consumption level where applicable,
- treatment of transfer orders,
- treatment of backorders,
- treatment of promotions,
- late/past-due order behavior,
- audit trail showing what consumed what.

This logic must be deterministic and testable.

### 7.2 Canonical shared state model

Every optimizer should consume the same authoritative representation of:

- SKUs,
- lots/cohorts,
- inventory,
- open purchase commitments,
- sales/customer orders,
- forecasts,
- suppliers,
- supplier resources,
- locations,
- lanes/routes,
- containers/loads,
- service classes,
- customers,
- prices/costs,
- payment terms,
- review epochs,
- uncertainty provenance.

Avoid phase-specific shadow copies of state.

### 7.3 Shared economic ledger

Every phase should use one authoritative economic model for:

- purchase cost,
- freight,
- fixed order cost,
- carrying cost,
- financing cost,
- shortage/service penalty,
- expiry/spoilage,
- transfer cost,
- switching cost,
- cancellation/defer/expedite cost,
- transport-mode premium,
- customer/SLA penalty,
- salvage/residual value.

The same economic event must never be charged twice by different phases.

### 7.4 Provenance and decision audit

For every recommendation, preserve:

- input snapshot,
- uncertainty model/version,
- source provenance,
- constraints active,
- incumbent policy,
- candidate policies,
- objective components,
- solver status/gap,
- approval status,
- final operator action.

This is necessary for historical replay, debugging, customer trust, and eventual auditability.

---

## 8. Architecture: do not build one gigantic MILP

Adding the full roadmap does **not** imply one monolithic model containing every SKU, supplier, customer, route, container, world, location, and review epoch.

That would create unnecessary complexity and poor debuggability.

ZAAD should preserve a **composable optimizer architecture**.

### Layer 1 — Canonical state

One shared data/state model.

### Layer 2 — Uncertainty engine

P6 supplies calibrated distributions/scenarios/information sets with explicit provenance.

### Layer 3 — Shared economics

One authoritative ledger.

### Layer 4 — Decision modules

- P0 protection/recovery
- P1 purchasing
- P2 network
- P3 sourcing
- P4 recourse
- P4B open commitments
- P5 allocation/promising
- P7 logistics
- P8 load composition
- P9 capital
- P10 lifecycle

### Layer 5 — Joint solves only where coupling is economically real

Examples of strong coupling:

- **P1 + P3:** quantity and source under shared supplier constraints.
- **P1 + P8:** quantity and container fill.
- **P3 + P7:** source and route/mode.
- **P2 + P5:** network inventory and customer allocation.
- **P4 + all modules:** future conditional actions.
- **P9 + P1/P3/P7/P8:** capital limits across purchasing/logistics decisions.

Examples that may decompose:

- independent product families with no shared capacity, capital, supplier, container, location, or customer constraints,
- disconnected geographic subnetworks,
- independent suppliers/resources.

The default engineering question should be:

> **What decisions actually share a constraint or economic consequence?**

Only those decisions need to be solved jointly.

---

## 9. Long-term product position

The strongest long-term ZAAD positioning is not:

> "AI inventory optimization."

It is:

> **ZAAD is the optimization layer between a distributor's ERP and its real-world decisions — from supplier commitment to customer fulfillment.**

For import-heavy distributors, the end-to-end decision sequence becomes:

1. estimate uncertainty,
2. determine how much protection is justified,
3. decide when/how much to commit,
4. choose supplier/source mix,
5. choose container/load composition,
6. choose route/mode/sailing,
7. decide where inventory should land,
8. decide what remains flexible,
9. intervene on open commitments if conditions change,
10. reallocate inventory across the network,
11. promise/allocate scarce supply to customers,
12. unwind protection during recovery.

The long-term moat is the **economic coupling between these decisions**.

A cheaper supplier changes:

- lead time,
- inventory requirement,
- route options,
- container economics,
- working capital,
- service risk.

A faster route changes:

- safety/protection requirement,
- customer promise,
- source economics,
- capital duration.

A larger MOQ changes:

- container fill,
- expiry,
- storage,
- capital allocation,
- customer service.

A customer SLA changes:

- service penalty,
- inventory protection,
- source choice,
- expedite value.

The product becomes more defensible when the same economic system can see those interactions.

---

## 10. Competitive positioning: what ZAAD should and should not claim

### Do claim

- purpose-built focus on import-heavy distributors,
- decision coupling across purchase/source/network/recourse,
- sector-aware operating physics,
- human-approved recommendations,
- historical replay before asking the operator to change policy,
- incumbent-first abstention,
- explicit common-cause supply risk,
- total economic decisions rather than unit-price minimization,
- ERP overlay rather than mandatory replacement.

### Do not claim

- that competitors do not use optimization,
- that "decision intelligence" is unique,
- that probabilistic forecasting is unique,
- that MEIO is unique,
- that source optimization is unique,
- customer savings before real-data validation,
- "predicting war" or geopolitical events,
- autonomous execution unless the product explicitly changes.

ToolsGroup now describes itself as an always-on decision-intelligence platform; Kinaxis, Blue Yonder, Slimstock, Netstock, RELEX, and Lokad all publicly market prescriptive/optimization capabilities in overlapping areas.[^tg-platform][^kinaxis-opt][^by-order][^slim-inventory][^netstock-order][^relex-home][^lokad-decision]

The credible ZAAD claim is therefore narrower:

> **We specialize in the decisions importers make when supply is normal, when it starts going wrong, and when it recovers — and we prove those decisions against the operator's own history before asking them to change anything.**

---

## 11. What should remain out of scope for now

### Production planning / detailed scheduling

Major vendors combine production planning with supply-chain planning.[^tg-solutions][^slim-platform] That does not mean ZAAD should.

Manufacturing introduces:

- BOMs,
- WIP,
- setup/changeover,
- machine capacity,
- yield,
- labor,
- production sequencing,
- campaign scheduling.

That is a separate operating physics problem. Do not broaden from distributors into manufacturers unless customer evidence proves the opportunity.

### Full S&OP / IBP suite

ToolsGroup and Slimstock market S&OP/IBP capabilities.[^tg-solutions][^slim-platform] ZAAD should integrate with those processes rather than attempt to recreate executive planning workflows before proving the core decision engine.

### Pricing / markdown optimization

ToolsGroup and RELEX both market pricing/markdown capabilities.[^tg-solutions][^relex-clearance] These are real optimization categories but are not necessary to win the importer procurement/inventory wedge.

### Warehouse execution

Do not build WMS labor, slotting, picking, wave sequencing, or yard execution as part of the optimizer roadmap. Those can be integration surfaces.

---

## 12. Real-data commercialization must run in parallel

The technical roadmap should **not** become a reason to delay customer validation.

The correct company structure from this point forward is two parallel tracks.

### Track A — Optimizer expansion

Technical work proceeds through P4 and later phases with frozen-regression discipline.

### Track B — Commercial proof

In parallel:

1. operator interviews,
2. data-access conversations,
3. historical diagnostic,
4. paid diagnostic where possible,
5. shadow recommendations,
6. operator review,
7. limited live deployment.

The first real distributor datasets should be allowed to reorder the optimizer roadmap.

Examples:

- If multiple operators say open POs and expediting dominate their pain, **P4B moves up**.
- If customers directly control container composition and repeatedly cite low fill / bad SKU mix, **P8 moves up**.
- If freight forwarders already make route decisions and customers have no control, **P7 moves down**.
- If cash/credit constraints dominate purchasing, **P9 moves up**.
- If catalogs have high replacement/discontinuation rates, **P10 moves up**.

The roadmap is a hypothesis. Operator economics determine final sequencing.

---

## 13. Suggested gating logic for feature priority

| Feature | Move earlier when... | Move later when... |
|---|---|---|
| P4B Open-PO Recourse | open orders are routinely expedited, deferred, changed, or canceled | commitments are operationally irreversible |
| P5 ATP / Allocation | stockouts create customer prioritization disputes or SLA penalties | customers are homogeneous and fill is rarely constrained |
| P6 Uncertainty | customer forecasting is weak/raw and ZAAD must generate scenarios itself | customer supplies high-quality calibrated probabilistic inputs |
| P7 Logistics | customer controls route/mode/carrier/sailing choices | 3PL/forwarder fully controls decisions |
| P8 Container | customers regularly build mixed-SKU import containers | purchasing is mostly domestic/LTL/parcels or supplier-packed |
| P9 Capital | cash/credit routinely limits otherwise-desirable purchasing | capital is effectively unconstrained |
| P10 Lifecycle | high SKU churn, supersession, new items, phase-outs | catalog is stable |

---

## 14. Validation philosophy for the expanded system

Every added phase should follow the existing ZAAD pattern:

1. define ownership boundaries,
2. pre-register fixtures,
3. define invariants,
4. define adversarial cases,
5. prove frozen neutrality when the phase is disabled,
6. build tiny causal fixtures before broad simulations,
7. benchmark performance,
8. run frozen regression against prior phases,
9. freeze exact semantics,
10. release separately,
11. validate later on real history.

### Specific additional invariants

As the roadmap expands, add invariants for:

- forecast consumption does not double-count demand,
- open-PO recourse cannot change an order after the declared modification cutoff,
- cancellation/defer/expedite economics reconcile exactly,
- ATP never promises inventory already allocated elsewhere,
- substitute allocation respects eligibility and conversion factors,
- route decisions obey mode/port/lane/product eligibility,
- container cube/weight never exceed physical capacity,
- capital spend never exceeds the declared financing envelope,
- lifecycle transitions do not replenish discontinued items,
- recourse actions obey non-anticipativity,
- no action silently bypasses human approval.

---

## 15. End-state example

A mature ZAAD system could eventually process a state like:

- three approved suppliers,
- two ports,
- several sailings,
- ocean and air options,
- open purchase orders,
- warehouse and branch inventory,
- customer commitments,
- supplier MOQ/MOV,
- container cube/weight,
- payment terms,
- working-capital ceiling,
- supplier reliability,
- route reliability,
- demand distributions,
- service classes.

And produce an operator policy such as:

> Commit 62% of the next requirement to Supplier A and 38% to Supplier B.  
> Commit Supplier A now because its production window closes first.  
> Keep part of Supplier B flexible until the next review epoch.  
> Fill the remaining container cube with SKUs whose incremental expected economic value exceeds their carrying/expiry risk.  
> Use ocean service through the lower-risk route; do not expedite the existing PO.  
> Hold part of the receipt centrally rather than pre-positioning it at every branch.  
> Reassess when Supplier A confirms fill.  
> If confirmed fill falls below the protection threshold, activate the approved alternate source.  
> If available supply is still constrained at arrival, allocate first to high-penalty / high-priority customer commitments.

That is the long-term product thesis:

> **uncertainty → physical consequence → economic decision → observable review → human-approved action**

---

## 16. Recommended roadmap summary

### Built and frozen/released

- **P0 — Protection & Recovery** ✅
- **P1 — Purchasing Economics** ✅
- **P2 — Multi-Echelon / Network Optimization** ✅
- **Three-Sector Physics** ✅
- **P3 — Supplier / Sourcing Portfolio Optimization** ✅

### Build next

- **P4 — Adaptive Recourse**
- **P4B — Open PO / Commitment Recourse**
- **P5 — ATP + Scarce-Supply Allocation + Economic Service Classes**
- **P6 — Decision-Aware Uncertainty + Demand/Supply Calibration**
- **P7 — Import Logistics Optimization**
- **P8 — Container & Load Portfolio Optimization**
- **P9 — Portfolio Capital Optimization**
- **P10 — Product Lifecycle, Substitution & Supersession**

### Build as cross-cutting infrastructure

- forecast consumption / firm-order netting,
- canonical state,
- shared economic ledger,
- decision provenance,
- audit/approval,
- deterministic complexity bounds,
- async/batch path for genuinely large supported workloads.

### Continue in parallel

- customer discovery,
- real operator datasets,
- historical diagnostics,
- paid pilots,
- shadow recommendations.

### Later system phases

- dashboard/workspace uplift,
- website uplift,
- Network Twin integration if it materially improves decisions,
- full correctness audit,
- major deletion/deprecation,
- security hardening,
- global performance optimization,
- untouched validation,
- real operator diagnostic,
- shadow pilot,
- limited live deployment.

---

## 17. Final strategic conclusion

ZAAD should add essentially all of the identified optimizer capabilities **if real operators validate that they control and care about those decisions**.

The mistake would not be ambition. The mistake would be sequencing every feature ahead of customer evidence.

The correct long-term architecture is:

> **one canonical state + one economic ledger + one uncertainty layer + composable decision modules + joint optimization only where coupling is real**

The correct company sequencing is:

> **build the shared optimizer core → get real operator evidence → expand the decision surface around the highest-value proven problems**

If this works, ZAAD is not merely an inventory optimizer. It becomes:

> **the economic optimization layer from importer commitment through customer fulfillment.**

---

# Evidence base and citations

## ZAAD internal evidence

- [P0 closeout](./evidence/v8/P0_CLOSEOUT.md)
- [P1 closeout](./evidence/p1/P1_CLOSEOUT.md)
- [P2 closeout](./evidence/p2/P2_CLOSEOUT.md)
- [Sector physics closeout](./evidence/sectors/SECTOR_PHYSICS_CLOSEOUT.md)
- [P3 architecture](./evidence/p3/P3_ARCHITECTURE.md)
- [P3 closeout](./evidence/p3/P3_CLOSEOUT.md)
- [P3 production performance closure](./evidence/p3/perf_closure/P3_PRODUCTION_PERF_AFTER.md)

## External-source interpretation rule

External sources below are primarily **official vendor documentation / product pages**. They verify that a capability is publicly described or supported by that vendor; they do **not** independently verify implementation quality, customer ROI, competitive superiority, or market share. ZAAD should not use vendor marketing claims as proof of expected ZAAD performance.

[^tg-meio]: ToolsGroup, “Multi-Echelon Inventory Optimization Software,” accessed 2026-09-11. https://www.toolsgroup.com/solutions/inventory-optimization-software/
[^tg-forecast]: ToolsGroup, “Probabilistic Demand Forecasting Software,” accessed 2026-09-11. https://www.toolsgroup.com/solutions/probabilistic-demand-forecasting/
[^tg-replen]: ToolsGroup, “Replenishment Planning Software for Supply Chains,” accessed 2026-09-11. https://www.toolsgroup.com/solutions/automated-replenishment/
[^tg-lifecycle]: ToolsGroup, “Aftermarket Parts Planning Software,” accessed 2026-09-11. https://www.toolsgroup.com/industries/aftermarket/
[^tg-platform]: ToolsGroup, “Decion: AI Decision Intelligence Platform,” accessed 2026-09-11. https://www.toolsgroup.com/platform/
[^tg-solutions]: ToolsGroup, “AI-Driven Supply Chain Planning Solutions,” accessed 2026-09-11. https://www.toolsgroup.com/solutions/

[^slim-inventory]: Slimstock, “Inventory Management Software | Slim4,” accessed 2026-09-11. https://www.slimstock.com/solutions/inventory-management-software/
[^slim-network]: Slimstock, “Network Balancing Software for Supply Chain,” accessed 2026-09-11. https://www.slimstock.com/solutions/network-balancing-software/
[^slim-supply]: Slimstock, “Advanced Supply Planning Software,” accessed 2026-09-11. https://www.slimstock.com/solutions/supply-planning-platform/
[^slim-platform]: Slimstock, “Slim4 – Integrated Operations & Strategic Planning Platform,” accessed 2026-09-11. https://www.slimstock.com/platform/

[^netstock-forecast]: Netstock, “Stock and Inventory Forecasting Software,” accessed 2026-09-11. https://www.netstock.com/solutions/inventory-forecasting/
[^netstock-order]: Netstock, “AI-Driven Automated Inventory Replenishment Software,” accessed 2026-09-11. https://www.netstock.com/solutions/inventory-ordering/
[^netstock-openpo]: Netstock Help Center, “Stock Statuses & Critical Review Explained,” accessed 2026-09-11. https://help.netstock.com/en/articles/12470752-stock-statuses-critical-review-explained
[^netstock-projection]: Netstock Help Center, “Projection Tab Explained,” accessed 2026-09-11. https://help.netstock.com/en/articles/12529813-projection-tab-explained
[^netstock-super]: Netstock Help Center, “Supersessions Explained,” accessed 2026-09-11. https://help.netstock.com/en/articles/12441710-supersessions-explained
[^netstock-lost]: Netstock Help Center, “Demand Planning: Refining the Forecast,” accessed 2026-09-11. https://help.netstock.com/en/articles/12889781-demand-planning-refining-the-forecast

[^lokad-inventory]: Lokad, “FAQ: Inventory Optimization,” accessed 2026-09-11. https://www.lokad.com/inventory-optimization/
[^lokad-moq]: Lokad Technical Documentation, “MOQs and Other Ordering Constraints,” accessed 2026-09-11. https://docs.lokad.com/legacy/moqs-and-other-ordering-constraints/
[^lokad-container]: Lokad, “Optimizing Container Shipments,” accessed 2026-09-11. https://www.lokad.com/blog/2015/11/18/optimizing-container-shipments/
[^lokad-decision]: Lokad, “Decision-Driven Optimization in Quantitative Supply Chain,” accessed 2026-09-11. https://www.lokad.com/decision-driven-optimization
[^lokad-economic]: Lokad, “Economic Drivers in Supply Chain,” accessed 2026-09-11. https://www.lokad.com/economic-drivers-in-supply-chain/
[^lokad-priority]: Lokad Technical Documentation, “How to Prioritize Purchases Economically,” accessed 2026-09-11. https://docs.lokad.com/how-to/economic-purchase-prioritization/

[^kinaxis-opt]: Kinaxis, “What Is Supply Chain Optimization?,” accessed 2026-09-11. https://www.kinaxis.com/en/what-sc-optimization
[^kinaxis-order]: Kinaxis, “Order Management,” accessed 2026-09-11. https://www.kinaxis.com/en/solutions/order-management-system

[^by-order]: Blue Yonder, “Omnichannel Order Promising & Optimization,” accessed 2026-09-11. https://blueyonder.com/solutions/order-management-and-commerce/order-promising-and-optimization

[^relex-home]: RELEX Solutions, “AI-Native Platform for End-to-End Planning,” accessed 2026-09-11. https://www.relexsolutions.com/
[^relex-promo]: RELEX Solutions, “How Accurate Promotion Forecasting and Replenishment Drive Retail Success,” accessed 2026-09-11. https://www.relexsolutions.com/resources/promotion-forecasting-and-replenishment/
[^relex-connected]: RELEX Solutions, “Retail Connected Planning: Make Decisions Before the Gaps Appear,” accessed 2026-09-11. https://www.relexsolutions.com/resources/retail-connected-planning-demo-teaser/
[^relex-electronics]: RELEX Solutions, “RELEX for Electronics Retailers,” accessed 2026-09-11. https://www.relexsolutions.com/industries/retail/electronics/
[^relex-clearance]: RELEX Solutions, “Seasonal Planning / Clearance Optimization,” accessed 2026-09-11. https://www.relexsolutions.com/solutions/markdown-pricing-and-optimization-software/

[^oracle-consumption]: Oracle Supply Chain Planning, “Forecast Consumption,” accessed 2026-09-11. https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/fausp/forecast-consumption.html
[^sap-consumption]: SAP Help Portal, “Demand Management and Forecast Consumption,” version August 2026, accessed 2026-09-11. https://help.sap.com/docs/SAP_BUSINESS_BYDESIGN/2754875d2d2a403f95e58a41a9c7d6de/2cbb5f06722d1014a01de7ad3b4e853d.html

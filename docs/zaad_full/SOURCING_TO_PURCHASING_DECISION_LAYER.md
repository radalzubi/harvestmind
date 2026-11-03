# ZAAD Sourcing-to-Purchasing Decision Layer

**Status:** Strategy / market-research / product-identity document  
**Research date:** 2026-10-03  
**Customer-discovery trigger:** Founder-reported feedback from Mohammad Al Darweesh, Abu Odeh Bros., 2026-10-03  
**Implementation status:** **STRATEGIC DIRECTION / NOT A CLAIM OF CURRENT PRODUCTION CAPABILITY**

---

## 1. Executive conclusion

There is a real and valuable operating layer between strategic sourcing and purchase-order execution, but it is **not an empty software category**.

Existing products already cover important parts of this chain:

- Source-to-Pay suites connect sourcing, contracts, buying, invoicing, and payment.
- Procure-to-Pay systems convert approved demand/requisitions into purchase orders and downstream execution.
- Procurement-orchestration products coordinate approvals and workflows across procurement, legal, finance, IT, security, and vendor setup.
- Direct-material procurement platforms connect BOMs, forecasts, suppliers, sourcing, planned orders, and ERP/MRP execution.
- Sourcing-optimization tools optimize supplier awards and sourcing-event scenarios.
- Commodity-intelligence products provide price benchmarks, forecasts, and buying-timing intelligence.
- MRP / PP-DS systems translate demand forecasts and BOMs into material requirements and procurement proposals.

The opportunity for ZAAD is therefore **not** to claim that nobody connects sourcing and purchasing.

The sharper identity is:

> **ZAAD is the decision layer between what sourcing knows and what purchasing commits.**

ZAAD should specialize in converting market, supplier, logistics, production, inventory, and working-capital information into a concrete purchase commitment:

> **what to buy, how much, when, from whom, by which mode, at what exposure, and what existing commitment should change.**

This extends the existing ZAAD thesis rather than replacing it:

> **Optimize the commitment, not the forecast.**

---

## 2. The operating gap

A typical import-heavy distributor or manufacturer has several decision systems and teams:

### Sourcing / category management

Owns or monitors:

- approved suppliers,
- supplier negotiations,
- RFQs / RFPs,
- contracts,
- supplier terms,
- price breaks,
- origin options,
- commodity markets,
- FX exposure,
- freight conditions,
- supplier capacity and risk,
- alternative materials or suppliers.

### Planning / manufacturing

Owns or monitors:

- finished-goods forecast,
- production plan,
- BOMs,
- factory calendars,
- line / work-center capacity,
- production rates,
- setup / changeover time,
- yield / scrap,
- material requirement dates.

### Purchasing / procurement execution

Owns:

- requisitions,
- PO quantities,
- PO dates,
- supplier selection within policy,
- open-PO amendments,
- delivery follow-up,
- expedites,
- receipts,
- ERP transaction execution.

### Finance / working capital

Constrains:

- available cash / credit,
- payment timing,
- inventory investment,
- financing cost,
- budget / open-to-buy,
- currency exposure.

### The practical failure mode

These functions often have relevant information without one common economic decision model.

A sourcing team may know that a commodity is moving, a quote expires, or one origin is becoming more attractive. A planner may know exactly when a raw material is required. Purchasing may know the open POs and actual supplier behavior. Finance may know capital is constrained.

The decision that matters is not merely any one of those facts. It is:

> **Given all of them together, what commitment should change now?**

That is the layer ZAAD should own.

---

## 3. What the market already calls the surrounding categories

### 3.1 Source-to-Pay (S2P)

SAP defines Source-to-Pay as the end-to-end procurement process from identifying a need and sourcing / contracting a supplier through buying, invoicing, and payment.[^sap-s2p]

**Interpretation for ZAAD:** S2P is broader than ZAAD. It is a transaction/process umbrella, not a useful differentiated category name for ZAAD.

### 3.2 Procure-to-Pay (P2P)

SAP describes P2P as the downstream purchasing lifecycle including requisition, purchase order, receipt, invoice, and payment.[^sap-p2p] JAGGAER similarly describes P2P as the process after the supplier/contract is established, covering requisition through payment.[^jaggaer-p2p]

**Interpretation for ZAAD:** P2P is the execution system ZAAD should feed; ZAAD should not rebuild accounts payable or generic buying workflows.

### 3.3 Procurement orchestration

Zip describes procurement orchestration as a common workflow layer that coordinates intake and the many cross-functional systems/approvals needed before purchase execution.[^zip-orchestration]

**Interpretation for ZAAD:** this term is already associated strongly with workflow orchestration. ZAAD may integrate with procurement orchestration, but should not use the term as its primary identity unless the product actually becomes a workflow platform.

### 3.4 Direct materials procurement / direct spend management

Ivalua explicitly connects direct-material sourcing, procurement execution, BOM-level cost visibility, supplier collaboration, forecasts, capacity, planned orders, inventory, ERP/MRP/PLM, and supply continuity.[^ivalua-direct] JAGGAER similarly markets direct-material/BOM sourcing and a connected Source-to-Pay environment in which sourcing decisions carry into purchasing.[^jaggaer-s2p]

**Interpretation for ZAAD:** the market already recognizes the need to bridge sourcing and direct-material purchasing. ZAAD cannot claim the bridge itself is unique. It must differentiate on the **economic commitment decision** and importer/manufacturer operating physics.

### 3.5 Sourcing optimization

Keelvar describes sourcing optimization as choosing supplier award allocations under constraints and total-value criteria, with direct-material use cases.[^keelvar-opt] Coupa also markets sourcing optimization for direct materials and logistics using scenario modeling and supplier collaboration.[^coupa-sourcing]

**Interpretation for ZAAD:** sourcing optimization is adjacent, especially around supplier award decisions. ZAAD's target is more continuous and operational: a sourcing award/contract is an input; the output is the actual purchase commitment and how it should adapt through time.

### 3.6 Commodity and purchasing intelligence

S&P Global's Pricing and Purchasing service explicitly provides price forecasts, historical prices, cost models, and guidance around purchase timing / forward pricing.[^spg-purchasing] Mintec/Expana provides commodity price data, forecasts, currencies/freight data, and market intelligence used by procurement teams.[^mintec]

**Interpretation for ZAAD:** commodity intelligence is an input layer. ZAAD should not pretend it can forecast every commodity better than specialist data providers. It should ingest or connect to credible market intelligence and translate it into inventory/purchasing decisions.

### 3.7 MRP / PP-DS

SAP MRP translates forecasts and other requirements through BOM levels, nets against inventory and open supply, applies planning rules such as MOQ and lead times, and generates procurement recommendations.[^sap-mrp] SAP PP/DS extends this toward resource/component availability, procurement proposals, and detailed order timing for critical materials/products.[^sap-ppds]

**Interpretation for ZAAD:** BOM explosion and backward timing are not novel. For manufacturers, ZAAD should consume the customer's approved finished-goods forecast and production constraints, then add richer economic and uncertainty-aware commitment decisions rather than positioning as a replacement for mature MRP/APS.

---

## 4. The strategic white space for ZAAD

The market research does **not** support the claim:

> "There is no system between sourcing and purchasing."

That claim would be false or at least materially overstated.

The stronger opportunity is:

> **A continuous commitment-intelligence layer specialized for import-heavy distributors and manufacturers, where sourcing market intelligence, physical supply uncertainty, production/material requirements, logistics, inventory, service, and capital are jointly translated into purchase actions.**

The differentiated question is not merely:

> Which supplier should win the sourcing event?

or:

> Which purchase requisition should become a PO?

It is:

> **Given the approved demand/material requirement, current inventory/open POs, supplier economics, commodity/FX/freight scenarios, transport choices, and service/capital constraints, what commitment should we make or change now?**

---

## 5. Recommended ZAAD identity

### Short external position

> **ZAAD connects sourcing intelligence to purchasing decisions.**

### Product position

> **ZAAD is a sourcing-to-purchasing decision layer for import-dependent distributors and manufacturers.**

### Internal technical name

> **Commitment Intelligence Layer**

### Core promise

> **Turn sourcing signals and operating requirements into economically justified purchase commitments.**

### Existing principle retained

> **Optimize the commitment, not the forecast.**

### Important boundary

ZAAD should not become a generic Source-to-Pay suite. It should sit above or beside ERP/MRP/procurement systems and improve the decisions those systems execute.

---

## 6. Canonical operating flow

```text
CUSTOMER FORECAST / ORDERS / DEMAND SIGNALS
                |
                v
DISTRIBUTION REQUIREMENTS OR BOM / MATERIAL REQUIREMENTS
                |
                v
PRODUCTION / FACTORY CONSTRAINTS (when manufacturing)
                |
                v
SOURCING INTELLIGENCE
  - supplier quotes / contracts
  - commodity market scenarios
  - FX
  - freight
  - origin risk
  - supplier capacity / reliability
  - alternate suppliers / materials
                |
                v
CURRENT OPERATING STATE
  - inventory
  - open POs
  - receipts
  - customer service exposure
  - working capital / credit
                |
                v
ZAAD COMMITMENT OPTIMIZER
  - quantity
  - timing
  - source
  - transport mode
  - commitment split
  - open-PO action
                |
                v
PURCHASE REQUISITION / PO PROPOSAL
                |
                v
HUMAN APPROVAL
                |
                v
ERP / PROCUREMENT EXECUTION
                |
                v
RECEIPTS / ACTUAL OUTCOMES / REALIZED VALUE
                |
                +------> feedback into ZAAD
```

---

## 7. First-class decision inputs added by the customer discovery

### 7.1 Transport mode: AIR / LAND / SEA / MULTIMODAL

Transport mode should become a first-class lane/PO attribute and, where the customer has declared alternatives, a future decision variable.

Relevant inputs:

- origin,
- destination,
- port / airport / border,
- transport mode,
- departure / arrival dates,
- transit-time distribution,
- customs / clearance time,
- freight cost,
- minimum shipment / container / truck constraints,
- reliability,
- expedite alternatives,
- capacity.

Example decision:

> Ship the base requirement by sea but cover the short-term material gap by air.

This belongs naturally with the existing P7 Import Logistics direction; it should not be confused with building a full TMS or route-optimization suite.

### 7.2 Commodity / market price exposure

For commodity-sensitive materials such as oils, grains, sugar, coffee, pulses, chemicals, metals, or packaging inputs, ZAAD should represent market-price uncertainty explicitly.

Relevant inputs:

- spot / benchmark price,
- contracted price,
- supplier quote and expiration,
- historical volatility,
- forward / forecast scenarios where available,
- FX,
- freight,
- tariff / duty exposure,
- price-break structure,
- contract / hedge coverage,
- expected material requirement timing.

The product should not market itself as a speculative commodity-price oracle.

Preferred model:

> **market scenarios -> purchase commitment decision**

Possible actions include:

- commit now,
- wait,
- split the commitment over time,
- lock a percentage of the requirement,
- change supplier/origin,
- use an alternate transport mode,
- do nothing.

### 7.3 Customer-owned demand forecast -> BOM-driven material timing

For manufacturing customers, the customer remains the owner of the approved finished-goods forecast.

ZAAD can use:

- finished-goods forecast,
- BOM,
- raw-material inventory,
- open POs,
- production line / work-center eligibility,
- production time / rate,
- changeover / setup,
- calendar / shifts,
- yield / scrap,
- material requirement dates,
- supplier lead-time distributions,
- transport mode,
- MOQ / order multiples,
- commodity / FX / freight economics.

Then ZAAD can recommend when each raw material/component must be ordered and from which source so it is available for the production requirement.

**Scope boundary:** this does not automatically mean ZAAD should become a full MES, finite-capacity APS, labor scheduler, or factory digital twin. The near-term manufacturing extension should be **BOM-aware procurement planning / commitment optimization**. Full factory scheduling requires separate validation.

### 7.4 Sourcing-to-purchasing handoff

The key customer insight is organizational as much as mathematical:

- sourcing sees markets, suppliers, terms, origins, and negotiations;
- purchasing sees demand, inventory, open POs, quantities, dates, and execution;
- those views need a common decision surface.

ZAAD should make the handoff explicit.

---

## 8. Proposed product surfaces

### Sourcing Intelligence

Primary questions:

- Which markets/materials are moving?
- What spend / BOM / SKU exposure is affected?
- Which suppliers/origins/quotes/contracts are attractive?
- Which contracts or quotes expire soon?
- Where are capacity/reliability risks increasing?
- What decisions may need to change?

Possible modules:

- commodity / raw-material watch,
- supplier quote comparison,
- landed-cost comparison,
- FX/freight exposure,
- contract / quote expiration,
- supplier/origin concentration,
- sourcing scenarios.

### Material Requirements / Manufacturing Procurement

Primary questions:

- What raw materials/components are required?
- When must they be physically available?
- Which requirement dates are at risk?
- What is already covered by stock/open POs?
- Which requirements require new commitments?

### Purchasing Decisions

Primary questions:

- What should I order now?
- How much?
- Which supplier?
- Which mode?
- What expected arrival?
- What should be deferred, expedited, reduced, cancelled, or split?
- Why?
- What is the inventory/service/working-capital consequence?

The three surfaces should use one canonical state and one economic ledger.

---

## 9. Decision vocabulary

ZAAD should eventually support a controlled vocabulary such as:

### New commitment

- BUY_NOW
- WAIT
- BUY_MORE
- BUY_LESS
- SPLIT_COMMITMENT

### Sourcing

- KEEP_SOURCE
- SOURCE_SWITCH
- SOURCE_SPLIT
- REQUEST_NEW_QUOTE / SOURCING_EVENT_TRIGGER (workflow signal, not autonomous sourcing)

### Transport

- KEEP_MODE
- MODE_SWITCH
- MODE_SPLIT
- EXPEDITE_PARTIAL

### Open PO

- KEEP
- DEFER
- EXPEDITE
- REDUCE
- CANCEL
- SPLIT

The exact production vocabulary should remain compatible with existing P4B semantics where possible.

---

## 10. Competitive map

| Layer | Representative products | What they already do | ZAAD implication |
|---|---|---|---|
| ERP / P2P execution | SAP / Ariba and similar | PR -> PO -> receipt -> invoice/payment, source assignment, execution | Integrate; do not rebuild generic transaction processing |
| Source-to-Pay | SAP, Ivalua, JAGGAER, Coupa | sourcing, suppliers, contracts, purchasing, AP; direct-material capabilities in some suites | "Connecting sourcing and purchasing" alone is not differentiation |
| Procurement orchestration | Zip and similar | intake, routing, approvals, cross-system workflow | Adjacent workflow layer; not ZAAD's primary identity |
| Sourcing optimization | Keelvar, Coupa Sourcing Optimization, Arkestro and others | supplier bidding/award scenarios, negotiation, constraint-aware awards | ZAAD should consume sourcing outcomes and continuously optimize actual commitments |
| Direct-material procurement | Ivalua, JAGGAER, LevaData and others | BOM/direct-material sourcing, supplier collaboration, cost/risk data | Close adjacency; differentiation must be importer economics + commitment optimization + proof discipline |
| Commodity intelligence | S&P Global Pricing & Purchasing, Mintec/Expana | prices, forecasts, cost models, market intelligence, timing insight | Data/input partner or connector category; do not rebuild all market data |
| MRP / PP-DS | SAP and similar | BOM explosion, requirements, order timing/procurement proposals, resource-aware planning | ZAAD should add stochastic economic commitment decisions rather than claim BOM math as unique |
| ZAAD target layer | ZAAD | **continuous quantity/timing/source/mode/open-PO commitment decision across market + physical + inventory + capital state** | Specialize and prove on importer/direct-material use cases |

---

## 11. What is actually differentiated vs. what is not

### Not differentiated by itself

- connecting sourcing to purchasing,
- BOM explosion,
- assigning a source of supply,
- converting requisitions to POs,
- displaying commodity prices,
- showing supplier scorecards,
- running RFQs,
- purchase-order workflow,
- procurement approvals,
- generic AI procurement assistant.

### Potentially differentiated as a system

- importer-specific quantity + timing + source + mode decisions,
- continuous decisions rather than episodic sourcing events,
- explicit uncertainty across demand, lead time, fill, price, freight, and FX,
- open-PO recourse,
- shared economic ledger across sourcing and purchasing,
- BOM-driven material commitments without owning the demand forecast,
- working-capital-aware prioritization,
- historical replay of what should have been committed using only then-known information,
- incumbent-first abstention,
- human-approved execution.

The moat, if one develops, is the **coupled operating model + customer outcome history**, not the label.

---

## 12. Pilot implication: Abu Odeh-style manufacturer/distributor

A useful first pilot should not attempt to model the whole company.

Prefer one imported material or product family with meaningful purchasing economics.

Two possible pilot shapes:

### A. Distribution / imported finished goods

Use:

- sales/orders,
- inventory,
- POs/receipts,
- suppliers,
- costs,
- origin,
- air/land/sea mode,
- freight,
- commodity/market exposure where relevant.

Question:

> Could ZAAD have made better quantity/timing/source/mode commitments than the historical process?

### B. Manufacturing / BOM-driven raw material

Use:

- customer-provided finished-goods forecast,
- BOM,
- production calendar / run times,
- raw-material inventory,
- open POs,
- supplier quotes/contracts,
- lead times,
- transport modes,
- commodity / FX / freight scenarios.

Question:

> Given the approved production requirement, when should each material have been committed, from which source, in what quantity, and by which mode?

Do not promise full factory optimization in the first pilot.

---

## 13. Discovery questions that must be answered before building a new phase

1. How are sourcing and purchasing organizationally separated today?
2. What data does sourcing maintain that purchasing cannot see in the PO workflow?
3. What data does purchasing maintain that sourcing does not incorporate in negotiations/commitments?
4. Who owns the final "buy now vs wait" decision?
5. Is the supplier already selected before purchasing decides quantity/timing?
6. How often can purchasing deviate from sourcing's preferred supplier?
7. How are commodity and FX views converted into actual buying actions today?
8. Are supplier quotes/contracts stored structurally or in emails/Excel?
9. How often is air used to recover from a sea/land supply gap?
10. Which transport modes are genuine alternatives vs mandatory routes?
11. For manufacturing: is the forecast approved externally to ZAAD, and at what cadence?
12. Are BOMs/versioning/yields reliable enough to support material planning?
13. What production constraints actually influence material order dates?
14. Does the ERP/MRP already generate usable purchase requisitions? If yes, what decisions are still manual?
15. What economic error is most costly: price, quantity, timing, supplier, mode, or working-capital allocation?

These answers should determine the build sequence.

---

## 14. Roadmap implications

### Strengthen existing phases

- **P1 Purchasing Economics:** add richer price/quote/market exposure and customer-provided material requirements.
- **P3 Sourcing Portfolio:** connect supplier awards/approved alternatives to purchasing decisions; do not become a full RFx suite by default.
- **P4B Open PO:** preserve intervention vocabulary and expose sourcing/logistics reasons for change.
- **P7 Import Logistics:** make transport mode (air/land/sea/multimodal) and declared route alternatives first-class.
- **P9 Capital:** prioritize commitments under cash/credit constraints.

### New strategic capability to validate

**BOM-aware Direct Material Commitment Planning**

This should begin as a customer-forecast-driven procurement layer:

> forecast -> BOM/material requirement -> production timing -> sourcing intelligence -> commitment optimizer -> PO proposal

Do not create a full manufacturing phase solely from one interview. Validate with additional operators and one real dataset first.

### Sourcing intelligence capability

Begin with **ingestion and scenario linkage**, not with building a proprietary commodity forecasting business.

Recommended sequence:

1. ingest supplier quotes/contracts,
2. ingest commodity/FX/freight benchmarks or user scenarios,
3. calculate customer exposure,
4. translate scenarios into commitment economics,
5. validate buy-now/wait/split decisions historically,
6. only then consider proprietary forecasting if customer evidence supports it.

---

## 15. Product identity guardrails

ZAAD should remain:

- a decision layer,
- economics-first,
- uncertainty-aware,
- importer/direct-material specific,
- ERP/MRP overlay,
- human-approved,
- evidence/provenance driven.

ZAAD should not become, without explicit validation:

- a generic procurement workflow suite,
- accounts-payable software,
- a supplier marketplace,
- a complete RFx suite,
- a generic commodity terminal,
- a full TMS,
- a full MES,
- a general finite-capacity factory scheduler,
- a replacement ERP.

---

## 16. Research-backed conclusion

The customer feedback points toward a coherent expansion, not random feature accumulation.

Transport mode, commodity/market exposure, BOM-driven material timing, and sourcing/purchasing coordination all converge on the same decision:

> **What economic commitment should the company make now, given what sourcing knows and what operations will need?**

That is strategically consistent with ZAAD's strongest existing identity.

The key change is that the "commitment" is no longer framed only as distributor replenishment. It can also be a **direct-material commitment** generated from customer-owned demand and production requirements.

The implementation rule remains:

> **Do not build the whole adjacent category. Own the commitment decision.**

---

## References

[^sap-s2p]: SAP, "What is source-to-pay (S2P)?" https://www.sap.com/resources/what-is-source-to-pay
[^sap-p2p]: SAP, "SAP Ariba Buying and Invoicing | Procure-to-Pay Applications." https://www.sap.com/products/spend-management/procure-to-pay.html
[^jaggaer-p2p]: JAGGAER, "Procure to Pay (P2P) Software Solutions." https://www.jaggaer.com/solutions/procure-to-pay
[^zip-orchestration]: Zip, "The Executive Guide to Procurement Orchestration." https://lp.ziphq.com/rs/195-QFD-187/images/Zip_Executive_Guide.pdf?version=0
[^ivalua-direct]: Ivalua, "Direct Materials Procurement Software." https://www.ivalua.com/solutions/process/direct-spend-management/
[^jaggaer-s2p]: JAGGAER, "Source to Pay Platform & S2P Procurement Software." https://www.jaggaer.com/solutions/source-to-pay
[^keelvar-opt]: Keelvar, "Making the Case for Sourcing Optimization" and Direct Materials Sourcing pages. https://www.keelvar.com/documents/making-the-case-for-sourcing-optimization
[^coupa-sourcing]: Coupa, "Unlocking Efficiency: Achieve Savings with Coupa Sourcing." https://www.coupa.com/events/unlocking-efficiency-achieve-savings-with-coupa-sourcing/
[^spg-purchasing]: S&P Global Market Intelligence, "Global Pricing and Purchasing Service." https://www.spglobal.com/market-intelligence/en/solutions/products/global-pricing-purchasing-service
[^mintec]: Mintec / Expana, commodity price data and market intelligence. https://www.mintecglobal.com/
[^sap-mrp]: SAP Business One, "How to Configure and Use MRP," current public guide. https://help.sap.com/doc/df83341c66ca42f492d7c5f611b042a8/10.0/en-US/How_to_Configure_and_Use_MRP_in_SAP_Business_One.pdf
[^sap-ppds]: SAP Help Portal, "Production Planning and Detailed Scheduling (PP/DS)." https://help.sap.com/docs/SAP_S4HANA_ON-PREMISE/21aead0c98bd4755abdacd91c99e3393/f431c95360267614e10000000a174cb4.html

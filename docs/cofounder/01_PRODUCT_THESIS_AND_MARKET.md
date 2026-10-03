# ZAAD Product Thesis and Market Brief

## 1. What ZAAD is

ZAAD is a **B2B stochastic decision layer for import-heavy distributors and direct-material manufacturers**. It is designed to sit above existing ERP, MRP, sourcing, and planning systems and recommend economically justified, human-approved commitments.

Core line:

> **Optimize the commitment, not the forecast.**

Current product-positioning line:

> **ZAAD connects sourcing intelligence to purchasing decisions.**

Long-term position:

> **ZAAD is the commitment-intelligence layer between what sourcing knows, what operations will need, and what purchasing commits.**

ZAAD is not primarily a forecasting product. Forecasts, BOM/material requirements, supplier performance, commodity markets, FX, freight, route risk, inventory, open POs, and other signals are inputs. The product is the **decision**.

A useful internal principle is:

> **Signals are inputs. Decisions are the product.**

Another:

> **External signal → physical/economic impact → inventory/service/capital consequence → commitment decision.**

ZAAD should never claim to predict geopolitical events or commodity prices with certainty. It should model observable data, customer forecasts, specialist market intelligence, declared scenarios, and uncertainty ranges, then determine what commitment is justified.

The full research note supporting this identity is:

- [`docs/zaad_full/SOURCING_TO_PURCHASING_DECISION_LAYER.md`](../zaad_full/SOURCING_TO_PURCHASING_DECISION_LAYER.md)

---

## 2. Initial customer wedge

Primary target customers are import-heavy distributors, importers, and selected direct-material manufacturers, especially businesses with:

- meaningful imported raw materials or finished goods,
- long/variable replenishment,
- multiple suppliers, origins, or transport modes,
- material working capital tied in inventory,
- commodity / FX / freight exposure,
- ERP/MRP plus spreadsheets and manual judgment,
- enough historical data to replay decisions,
- a real operational pain around quantity, timing, source, transport, or open commitments.

Relevant early verticals include:

- commercial / FMCG goods,
- food ingredients and dry goods,
- fresh produce,
- meat and seafood,
- frozen/chilled food,
- manufacturers with imported direct materials,
- mixed distribution/manufacturing businesses with meaningful imported supply.

The wedge is **not all procurement** and not all manufacturing. It is the economically consequential commitment decision under import and supply uncertainty.

---

## 3. Core problems ZAAD is meant to solve

- ordering too early or too late,
- ordering too much or too little,
- committing when waiting would be more economic,
- waiting when market/service risk justifies committing,
- fixed ordering calendars that ignore economics,
- sourcing intelligence not translating cleanly into PO actions,
- supplier quotes/contracts not being evaluated against physical requirements and open supply,
- buying from the nominally cheapest source when total landed economics are worse,
- failing to account for commodity / FX / freight scenarios in actual commitments,
- using air, land, or sea reactively rather than economically,
- carrying duplicated protection across multiple locations,
- holding too much inventory during calm periods,
- being under-protected during disruption,
- failing to unwind protection when supply recovers,
- treating correlated suppliers/routes as independent,
- poor network allocation,
- spoilage/expiry caused by ignoring sellable life,
- poor decisions around open POs, future commitments, transport, container capacity, and scarce supply,
- for manufacturers: disconnect between approved finished-goods forecasts, BOM/material requirements, production timing, sourcing conditions, and purchase timing.

---

## 4. Current product philosophy

### Incumbent-first

ZAAD does not assume the customer is wrong.

If the current policy is already materially efficient, the system should be able to return:

> **NO MATERIAL IMPROVEMENT AVAILABLE**

### Human-approved

ZAAD recommends actions. It does not autonomously place purchase orders.

### Overlay, not rip-and-replace

The product should ingest and work with existing ERP/MRP/procurement outputs rather than require replacement of Oracle, SAP, Dynamics, NetSuite, Manhattan, Ariba, or similar systems.

A strong commercial line is:

> **Keep your ERP. Keep your sourcing system. Improve the commitment decision.**

### Customer-owned forecast where appropriate

For manufacturing customers, ZAAD does not need to own the finished-goods forecast. The customer can provide the approved demand forecast. ZAAD can then translate that through BOM/material requirements, production timing, supplier/logistics constraints, and economics into purchase commitments.

### Historical proof before live trust

The preferred deployment sequence is:

1. ingest 12–24 months of history,
2. reconstruct operator state,
3. run causal historical replay,
4. identify credible opportunities,
5. shadow recommendations,
6. operator review,
7. limited live use.

### One shared economic objective

ZAAD should optimize total economics, not one local KPI.

Relevant components include:

- purchase cost,
- commodity / market exposure,
- FX,
- freight,
- transport-mode economics,
- fixed ordering cost,
- receiving,
- carrying,
- financing,
- shortage/service penalties,
- spoilage/expiry,
- transfer cost,
- switching cost,
- cancellation/defer/expedite economics,
- continuation/residual value.

---

## 5. Decision thesis by operating context

### DISTRIBUTION / COMMERCIAL

Core problem:

> **When should we buy, how much, from whom, and whether to buy at all under total landed economics?**

Important physics:

- MOQ,
- MOV,
- packs/cases,
- pallets,
- freight tiers,
- shipment/container limits,
- payment terms,
- import lead times,
- air/land/sea alternatives,
- storage capacity,
- working capital,
- supplier quotes/contracts,
- commodity / FX / freight exposure.

Strong line:

> **ZAAD converts sourcing and market information into the purchase commitment the buyer should make now.**

### MANUFACTURING / DIRECT MATERIALS

Core problem:

> **Given the customer's approved finished-goods forecast, when should every required material be committed, in what quantity, from which source, and by which mode?**

Important physics:

- BOMs,
- yields / scrap,
- material requirement dates,
- production rates / run times,
- work-center or line eligibility,
- changeovers where material to ordering timing is affected,
- raw-material inventory,
- open POs,
- supplier lead times/capacity,
- commodity / FX / freight economics,
- MOQ / lot / container constraints,
- transport mode.

Near-term scope is **BOM-aware procurement / commitment planning**, not full MES or detailed factory scheduling.

### PRODUCE

Core problem:

> **The right amount of product, with enough life left to sell it.**

Important physics:

- age at receipt,
- remaining sellable life,
- FEFO,
- spoilage,
- supplier fill,
- lead variability,
- transfer aging,
- demand uncertainty.

### MEAT / SEAFOOD

Core problem:

> **Protect service without turning uncertainty into unnecessary aging, expiry, and working capital.**

Important physics:

- chilled/frozen state,
- cold-chain eligibility,
- lot age,
- expiry,
- long replenishment,
- constrained allocation,
- storage/lane feasibility.

---

## 6. Sourcing-to-purchasing decision layer

The market already contains Source-to-Pay suites, procurement orchestration, sourcing optimization, direct-material procurement, commodity intelligence, and MRP/APS systems. ZAAD should not claim the bridge between sourcing and purchasing is an empty category.

The strategic position is narrower:

> **Sourcing knows markets, suppliers, contracts, origins, and prices. Purchasing owns quantities, dates, open POs, and execution. ZAAD owns the economic decision that connects them.**

The canonical decision flow is:

> **Forecast / demand → BOM or distribution requirement → sourcing intelligence → inventory/open POs → commitment optimizer → PO proposal → human approval → ERP execution → outcome feedback.**

First-class sourcing inputs should include:

- supplier quotes and quote expirations,
- contracts and price breaks,
- commodity benchmarks/scenarios,
- FX,
- freight,
- supplier capacity and reliability,
- origin risk,
- approved alternatives,
- transport alternatives.

First-class outputs should include:

- buy now / wait,
- buy more / buy less,
- quantity,
- timing,
- supplier/source,
- commitment split,
- transport mode or mode split,
- open-PO keep/defer/expedite/reduce/cancel/split.

---

## 7. Competitive positioning

ZAAD should not claim that established planning/procurement vendors lack optimization or that nobody connects sourcing and purchasing. They do.

The credible differentiation is the **combination** of:

- continuous commitment decisions rather than only episodic sourcing events,
- importer/direct-material operating physics,
- quantity + timing + source + mode coupling,
- commodity / FX / freight uncertainty as decision inputs,
- BOM-aware material commitments without requiring ZAAD to own the customer's demand forecast,
- open-PO recourse,
- cross-location inventory decisions,
- correlated physical supply risk,
- working-capital-aware prioritization,
- sector-aware perishability,
- incumbent-first abstention,
- historical replay before changing policy,
- human approval,
- ERP/MRP overlay.

The industry-backed comparison and future capability map are in:

- [`docs/zaad_full/OPTIMIZER_PRODUCT_STRATEGY_AND_INDUSTRY_ROADMAP.md`](../zaad_full/OPTIMIZER_PRODUCT_STRATEGY_AND_INDUSTRY_ROADMAP.md)
- [`docs/zaad_full/SOURCING_TO_PURCHASING_DECISION_LAYER.md`](../zaad_full/SOURCING_TO_PURCHASING_DECISION_LAYER.md)

---

## 8. Commercial validation status

Current status:

> **Economically promising, technically credible, commercially unproven.**

The sourcing-to-purchasing and manufacturing/direct-material extensions are currently **customer-discovery-driven hypotheses**, not validated product claims.

Do not convert synthetic fixture performance into customer claims.

Do not state guaranteed inventory reductions or savings.

Real proof requires:

- real operator data,
- causal historical replay,
- untouched holdout evaluation,
- shadow recommendations,
- measured implementation outcomes.

---

## 9. Initial commercial offer hypothesis

A practical early offer is a historical diagnostic or scoped material-commitment pilot.

### Distributor pilot

Customer provides sales, inventory, POs, receipts, supplier history, SKU data, freight/mode/origin data where relevant, and costs.

ZAAD reconstructs historical decisions and asks:

> **Could quantity, timing, source, mode, or open-PO actions have produced better economics using only information available at the time?**

### Manufacturing/direct-material pilot

Customer provides:

- approved finished-goods forecast,
- BOM,
- production/material requirement timing,
- raw-material inventory,
- open POs,
- supplier quotes/contracts,
- lead times,
- transport modes,
- commodity / FX / freight inputs where material.

ZAAD asks:

> **When should each material have been committed, in what quantity, from which source, and by which mode?**

Preferred sequence:

> **Historical diagnostic → shadow recommendations → limited live pilot**

The exact pricing model is a commercial hypothesis and must be validated separately from optimizer engineering.

---

## 10. What ZAAD should not become right now

Do not broaden prematurely into:

- a generic Source-to-Pay suite,
- RFx/event-management software,
- accounts payable,
- generic procurement workflow/orchestration,
- a supplier marketplace,
- a generic commodity-price terminal,
- full manufacturing scheduling,
- MES,
- broad BOM/WIP execution,
- labor scheduling,
- warehouse execution,
- full TMS,
- full S&OP/IBP suite,
- pricing/markdown optimization,
- generic "AI supply chain" software.

BOM-aware material commitment planning is now an explicit strategic hypothesis, but **full factory scheduling remains out of scope until separately validated**.

---

## 11. The long-term product thesis

If the roadmap succeeds, ZAAD eventually helps an operator answer:

- what future material requirement is economically uncovered,
- how much protection is justified,
- when to order,
- how much to order,
- whether to order at all,
- who to source from,
- whether to split the source,
- which quote/contract exposure should be locked now,
- where stock should sit,
- what to change when market or operating conditions change,
- what to do with open POs,
- which route/mode/container to use,
- how to allocate scarce stock,
- where limited capital should go.

The long-term moat is not any one algorithm. It is the **economic coupling between sourcing, physical requirements, purchasing, logistics, inventory, and capital decisions that are usually planned separately**.

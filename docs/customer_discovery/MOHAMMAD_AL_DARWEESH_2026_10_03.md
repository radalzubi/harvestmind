# Customer Discovery — Mohammad Al Darweesh

**Date:** 2026-10-03  
**Company context:** Abu Odeh Bros.  
**Source:** Founder-reported notes from live customer discovery conversation  
**Status:** Qualitative discovery input; **not independently verified operational fact**  

---

## 1. Why this note exists

This document preserves the product-identity changes triggered by customer discovery with Mohammad Al Darweesh so they are not lost in chat history or silently converted into product claims.

The feedback should be treated as a **strategic hypothesis generator**. It is strong enough to update discovery priorities and product framing, but not strong enough by itself to justify a broad manufacturing/procurement build.

---

## 2. Key feedback themes

### A. Transport mode must be explicit

Purchasing/import decisions should account for whether material moves by:

- AIR,
- LAND,
- SEA,
- MULTIMODAL.

Transport affects:

- lead time,
- lead-time variability,
- landed cost,
- minimum shipment/container/truck quantities,
- recovery / expedite choices,
- customs and border/port timing.

**Product implication:** transport mode should become a first-class lane/PO field and a decision variable only where the customer has real declared alternatives.

---

### B. Commodity / market-price fluctuation matters to sourcing

Commodity-sensitive materials such as oils and other raw materials should not be planned using only static purchase prices.

Relevant information can include:

- benchmark / spot price,
- supplier quote,
- quote expiration,
- contract price,
- price volatility,
- FX,
- freight,
- tariff/duty where relevant,
- market scenarios / external price forecasts.

**Product implication:** do not position ZAAD as a universal commodity-price predictor. Ingest customer or specialist market intelligence and optimize the commitment across plausible price scenarios.

---

### C. Manufacturing customers may supply the demand forecast

For manufacturing, the customer/company can remain the owner of the finished-goods demand forecast.

ZAAD's role can begin downstream of that forecast:

> approved finished-goods forecast -> BOM/material requirement -> production timing -> sourcing/logistics constraints -> raw-material purchase timing/quantity/source/mode

Relevant factory inputs may include:

- BOM,
- production rates / run times,
- line/work-center eligibility,
- calendar / shifts,
- changeovers where material timing is affected,
- yield / scrap,
- material requirement dates.

**Product implication:** validate **BOM-aware direct-material commitment planning**. Do not infer that ZAAD should immediately become a full APS/MES or factory scheduler.

---

### D. Stronger connection between sourcing and purchasing

A key organizational insight is that sourcing and purchasing may work with different information and time horizons.

Sourcing may own:

- markets,
- supplier alternatives,
- quotes,
- contracts,
- origins,
- commodity exposure,
- negotiation intelligence.

Purchasing may own:

- actual order quantities,
- order dates,
- open POs,
- receipts,
- expedites,
- ERP transaction execution.

The desired layer is one that translates sourcing intelligence into actual purchasing commitments.

**Product implication:** investigate a sourcing-to-purchasing / commitment-intelligence layer rather than treating sourcing as only a supplier selector inside replenishment.

---

## 3. Updated working product identity

The discovery feedback is consistent with an evolved ZAAD identity:

> **ZAAD connects sourcing intelligence to purchasing decisions.**

Internal technical framing:

> **Commitment Intelligence Layer**

Longer product description:

> **ZAAD is a sourcing-to-purchasing decision layer for import-dependent distributors and manufacturers. It combines demand/material requirements, supplier and market intelligence, inventory/open POs, logistics, and working-capital constraints to recommend what to buy, how much, when, from whom, by which mode, and what existing commitment should change.**

Existing thesis retained:

> **Optimize the commitment, not the forecast.**

---

## 4. What is not yet validated

Do **not** treat this conversation as proof that:

- all Abu Odeh workflows operate exactly this way,
- BOM-aware procurement is the highest-value ZAAD wedge,
- commodity forecasting should be built internally,
- full production scheduling is required,
- all target customers have sourcing and purchasing separated organizationally,
- transport mode is selectable for every material,
- customers will pay for this specific expanded scope.

These need additional interviews and real data.

---

## 5. Questions for next operator interviews

1. Who owns sourcing vs purchasing?
2. Who makes the final buy-now/wait decision?
3. How are supplier quotes/contracts transferred into the purchasing workflow?
4. How are commodity/FX/freight views converted into PO quantity/timing changes?
5. Are air/land/sea true alternatives or predetermined by supplier/lane?
6. What causes emergency air freight today?
7. Does MRP already generate purchase requisitions? If yes, what judgment remains manual?
8. How reliable are BOMs, yields, production calendars, and requirement dates?
9. Which decision creates the largest financial error: price, quantity, timing, supplier, transport mode, or capital allocation?
10. What data can be exported without a new integration?

---

## 6. Build gate

Do not open a broad new manufacturing/procurement engineering phase from this interview alone.

Before a large implementation, require at least:

- additional operator validation,
- one real customer dataset,
- confirmation of the current manual decision gap,
- proof that existing ERP/MRP/S2P tooling does not already solve the customer's actual problem adequately,
- a scoped historical or shadow test of the commitment decision.

---

## 7. Related strategy docs

- `docs/cofounder/01_PRODUCT_THESIS_AND_MARKET.md`
- `docs/zaad_full/SOURCING_TO_PURCHASING_DECISION_LAYER.md`
- `docs/zaad_full/OPTIMIZER_PRODUCT_STRATEGY_AND_INDUSTRY_ROADMAP.md`

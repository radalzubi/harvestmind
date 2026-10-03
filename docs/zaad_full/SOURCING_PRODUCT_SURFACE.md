# ZAAD Sourcing Product Surface

**Status:** Product architecture / customer-discovery follow-up  
**Date:** 2026-10-03  
**Trigger:** Founder-reported feedback from Mohammad Al Darweesh, Abu Odeh Bros.  
**Implementation status:** **PROPOSED — NOT CURRENT PRODUCTION CAPABILITY**

---

## 1. Purpose

ZAAD should expose a dedicated **Sourcing** area that sits upstream of Purchasing and turns market/supplier intelligence into purchase-commitment decisions.

The Sourcing area is not a generic procurement suite. Its purpose is to answer:

> **Given market prices, supplier options, inventory, future material requirements, lead times, transport, and available capital, should we buy now, wait, split, or change source?**

This is the operational bridge between sourcing intelligence and purchasing execution.

---

## 2. Top-level information architecture

**Sourcing**

1. **Overview**
2. **Market Prices**
3. **Market Intelligence / News**
4. **Buy / Wait Decisions**
5. **Suppliers**
6. **Alternative Suppliers**
7. **Quotes & Contracts**
8. **Exposure**

The exact navigation can be simplified for V1, but these are the conceptual surfaces.

---

## 3. Overview

The overview should answer, at a glance:

- Which raw materials are financially material?
- Which commodity-linked inputs moved today / this week / this month?
- Which materials have a near-term purchase decision?
- Which materials are under-covered relative to production or demand needs?
- Which materials have potentially favorable buying conditions?
- Which quotes/contracts expire soon?
- Which suppliers/origins are becoming more or less attractive?
- What sourcing decisions need human attention now?

Suggested cards:

- **Spend at risk**
- **Materials with significant market moves**
- **Buy-now candidates**
- **Wait candidates**
- **Supplier alternatives requiring review**
- **Quotes expiring soon**
- **FX/freight exposure**
- **Upcoming material requirements not yet covered**

No card should imply a recommendation unless the data and decision model support it.

---

## 4. Market Prices

### 4.1 Commodity/material mapping

ZAAD should maintain a mapping between the customer's internal raw-material SKUs and external market instruments/benchmarks.

Example:

```text
Customer SKU: RM-OIL-PALM-RBD-001
Customer description: RBD Palm Olein
Commodity family: Palm oil
External benchmark(s): approved licensed benchmark(s)
Relevant origin(s): customer-declared origins
Currency exposure: USD / local currency
Freight lane(s): declared customer lanes
```

The **AI ingestion layer may propose this mapping**, but it must not invent the raw-material universe.

Preferred source of truth:

1. customer item master,
2. BOM/raw-material master,
3. historical purchase lines,
4. supplier quotes/contracts,
5. AI-assisted normalization/classification,
6. human confirmation for ambiguous mappings.

AI should be used to normalize descriptions such as:

- `PALM OLEIN RBD CP8`
- `RBD PALM OIL`
- `VEG OIL PALM`

into one approved sourcing category where appropriate.

### 4.2 Price view

For each material, show where licensing/data permits:

- current benchmark/market price,
- previous close / prior day,
- 7-day move,
- 30-day move,
- 90-day move,
- historical range,
- volatility,
- customer last purchase price,
- current supplier quote(s),
- quote expiration,
- contracted price where applicable,
- FX impact,
- freight impact,
- estimated landed-price range.

The UI should make clear whether a value is:

- **MARKET BENCHMARK**
- **SUPPLIER QUOTE**
- **CUSTOMER ACTUAL**
- **MODELLED / ESTIMATED**

Do not blend them without provenance.

---

## 5. Abu Odeh palm-oil example

Customer-discovery feedback indicates that edible-oil purchasing can involve very large quantities where relatively small unit-price changes create material savings.

The product question is therefore not simply:

> "What is today's palm-oil price?"

It is:

> **"Given our requirement, inventory cover, production timing, supplier lead times, current quotes, market-price distribution, freight, FX, and available capital, should we commit now, wait, or split the purchase?"**

Possible recommendation structure:

```text
Material: Palm oil / approved customer SKU family
Requirement horizon: next 12 weeks
Required quantity: 1,800 MT
Current inventory + committed inbound: 900 MT equivalent coverage
Uncovered requirement: 900 MT

Recommendation:
PARTIAL_COMMIT
- Lock 550 MT now
- Keep 350 MT uncommitted for next review window

Why:
- current price is below recent 30-day reference range
- inventory cover allows partial delay without violating service/production requirements
- full immediate commitment creates unnecessary price exposure if market softens
- waiting on all 900 MT would create unacceptable replenishment risk

Economic comparison:
BUY_ALL_NOW vs WAIT_ALL vs PARTIAL_COMMIT
```

The system should present scenario ranges rather than claim certainty about the future commodity price.

### Origin note

Founder-reported discovery notes referenced Malaysia, Indonesia, and Ukraine in the edible-oil sourcing discussion. Before encoding these as palm-oil production origins, ZAAD should verify the customer's actual commodity/origin mapping. Ukraine may refer to another edible oil, trader/intermediary origin, or a different sourcing relationship. **Do not silently normalize customer discovery into an incorrect commodity-origin assumption.**

---

## 6. Buy / Wait Decision Engine

This should become one of the central Sourcing subtabs.

For each material requiring attention, ZAAD should return a controlled action vocabulary:

- **BUY_NOW**
- **WAIT**
- **PARTIAL_COMMIT**
- **BUY_MORE**
- **BUY_LESS**
- **KEEP_CURRENT_PLAN**
- **REQUEST_NEW_QUOTE**
- **SOURCE_REVIEW_REQUIRED**

The recommendation should combine:

### Requirement state

- forecast / customer demand,
- BOM-driven material requirements,
- production timing,
- safety/protection requirement,
- current inventory,
- open POs,
- usable stock / expiry where relevant.

### Market state

- benchmark price,
- supplier quote,
- market volatility,
- scenario distribution,
- FX,
- freight,
- duties/tariffs where applicable.

### Supply state

- supplier lead time,
- supplier reliability/fill,
- capacity,
- origin risk,
- air/land/sea alternatives,
- MOQ/MOV/container rules.

### Financial state

- cash/credit available,
- payment terms,
- working-capital cost,
- quantity discount,
- cost of waiting,
- expected cost of shortage or emergency expedite.

The objective is not to buy at the absolute market bottom. That is impossible to guarantee.

The objective is:

> **choose the commitment with the strongest expected economics while preserving required service/production protection.**

---

## 7. Market Intelligence / News

A sourcing user should not need to manually monitor dozens of commodity and logistics feeds.

Potential inputs:

- licensed commodity-market feeds,
- FX feeds,
- freight indices / market feeds,
- customer supplier communications where permitted,
- news APIs,
- trusted public regulatory / trade / weather sources,
- customer-uploaded market reports.

### AI role

AI can:

- ingest and classify relevant articles,
- map an article to affected commodity/material/origin/supplier/lane,
- summarize the likely physical/economic mechanism,
- identify which customer SKUs/BOMs are exposed,
- flag a decision for re-evaluation.

AI should **not** directly generate an ungrounded buy order from news.

Required chain:

```text
NEWS / MARKET SIGNAL
       ->
VERIFIED SOURCE + PROVENANCE
       ->
MAPPED COMMODITY / SUPPLIER / ORIGIN / LANE
       ->
PARAMETER OR SCENARIO IMPACT
       ->
ZAAD ECONOMIC RE-EVALUATION
       ->
BUY / WAIT / SPLIT / SOURCE REVIEW / NO CHANGE
```

Example:

```text
Signal: export restriction / weather disruption affecting an origin
Affected material: customer-approved edible-oil SKU family
Physical effect: possible supply reduction / lead-time shift
Decision effect: rerun commitment scenarios
Result: NO CHANGE or revised commitment
```

The product should never equate "bad news" with "buy more" automatically.

---

## 8. Suppliers

This tab should show the customer's **known/approved** suppliers and sourcing economics.

For each supplier/material combination:

- approved status,
- material/specification eligibility,
- country/origin,
- quoted/current price,
- price history,
- MOQ/MOV,
- capacity if known,
- lead-time distribution,
- on-time performance,
- fill performance,
- quality performance,
- payment terms,
- transport modes,
- freight/landed cost,
- contract state,
- concentration/exposure,
- customer qualification status.

ZAAD can then compare the **total landed and risk-adjusted economics**, not merely unit price.

---

## 9. Alternative Suppliers

This should be a separate subtab because discovery and qualification are different from optimization among already-approved suppliers.

### 9.1 Core rule

> **ZAAD may suggest a candidate supplier. It must never present an unqualified supplier as approved or immediately usable.**

Alternative-supplier discovery should begin from the customer's own qualification policy.

### 9.2 Customer qualification profile

Examples of customer-defined requirements:

- material specification / grade,
- food-safety certifications,
- halal requirements where applicable,
- regulatory approvals,
- audit requirements,
- approved countries/origins,
- minimum production capacity,
- minimum trading history,
- financial/credit criteria,
- ESG / ethical sourcing standards if required,
- minimum quality score,
- sample/testing requirement,
- required Incoterms,
- required logistics capability,
- required documentation,
- excluded countries/entities,
- sanctions/compliance screening.

### 9.3 Candidate discovery

Potential sources:

- customer's existing supplier master,
- previously used/inactive suppliers,
- supplier databases,
- trade/import-export datasets,
- industry directories,
- certification databases,
- company websites,
- approved market-data providers,
- human sourcing-team entries.

AI can assist with:

- entity matching,
- material/category matching,
- certificate/document extraction,
- location/origin normalization,
- initial evidence gathering,
- comparing candidates to the customer's qualification checklist.

### 9.4 Qualification states

Suggested states:

- **KNOWN_APPROVED**
- **KNOWN_NOT_APPROVED**
- **CANDIDATE_UNVERIFIED**
- **CANDIDATE_PREQUALIFIED**
- **QUALIFICATION_IN_PROGRESS**
- **APPROVED**
- **REJECTED**

Only `APPROVED` / customer-authorized suppliers should enter the production sourcing optimizer by default.

A candidate supplier can trigger:

> **SOURCE_REVIEW_REQUIRED**

but should not automatically trigger:

> **SOURCE_SWITCH**

until customer qualification is complete.

---

## 10. Supplier-alternative economics

After qualification, ZAAD should compare supplier alternatives on:

- unit price,
- landed cost,
- freight,
- duties,
- FX,
- MOQ,
- lead time,
- lead-time variability,
- fill reliability,
- capacity,
- payment terms,
- quality/yield implications,
- switching cost,
- concentration/common-cause risk,
- transport mode,
- inventory impact,
- working-capital impact.

The cheapest quoted supplier should not automatically win.

Example:

```text
Supplier A: lower unit price, 70-day lead time, higher MOQ
Supplier B: +2.5% price, 35-day lead time, better fill reliability
Supplier C: cheapest ex-works, but higher freight and working-capital exposure

ZAAD decision:
SOURCE_SPLIT or KEEP_SOURCE based on total economics
```

---

## 11. AI ingestion architecture

The sourcing product should use AI as an **ingestion/mapping/analysis layer**, not as an uncontrolled source of truth.

```text
CUSTOMER DATA
  item master
  BOM
  POs
  quotes
  contracts
  supplier master
       |
       v
AI-ASSISTED NORMALIZATION
  material classification
  commodity mapping
  supplier entity matching
  origin / lane extraction
       |
       v
VERIFIED SOURCING MODEL
       |
       +---- MARKET DATA FEEDS
       +---- NEWS / EXTERNAL SIGNALS
       +---- FX / FREIGHT
       |
       v
PROVENANCE-AWARE ANALYSIS
       |
       v
ZAAD COMMITMENT OPTIMIZER
       |
       v
HUMAN-APPROVED DECISION
```

Every externally derived fact should retain:

- source,
- timestamp,
- material/supplier mapping,
- confidence,
- measured vs inferred vs AI-extracted status.

---

## 12. Data model additions

Proposed entities / fields:

### `material_market_mapping`

- tenant
- sku/material_id
- commodity_family
- benchmark_id
- benchmark_provider
- currency
- approved_origin_set
- mapping_status
- confidence
- reviewed_by

### `market_price_observation`

- benchmark_id
- timestamp
- value
- currency
- unit
- provider
- provenance

### `supplier_quote`

- supplier_id
- material_id
- quoted_price
- currency
- unit
- incoterm
- quote_date
- expiration
- MOQ
- lead_time
- origin
- transport assumptions

### `supplier_qualification`

- supplier_id
- material/category
- status
- qualification_ruleset_version
- evidence
- last_reviewed
- reviewer

### `market_signal`

- source
- publication_time
- affected_entity
- signal_type
- extracted_claim
- confidence
- approved_parameter_effect

No AI-extracted field should silently overwrite customer master data.

---

## 13. UX recommendation

The most important sourcing screen should not be a generic commodity chart.

It should be a **decision workspace**.

Example material detail page:

```text
PALM OIL

Current market
- benchmark
- 7d / 30d / 90d move
- supplier quotes
- FX
- freight

Our position
- on hand
- inbound
- weeks of cover
- production requirement
- uncovered requirement
- cash required

ZAAD decision
- PARTIAL_COMMIT
- buy 550 MT now
- review 350 MT in 7 days

Why
- economics / service / market scenarios

Alternatives
- approved Supplier A
- approved Supplier B
- 2 unverified supplier candidates

Recent intelligence
- 3 relevant market/news events
```

This keeps the sourcing tab tied to action rather than turning ZAAD into Bloomberg for commodities.

---

## 14. V1 / V2 sequencing

### Sourcing V1

Build only after customer/data validation:

1. customer raw-material ingestion,
2. AI-assisted material/commodity mapping,
3. market-price feed for selected pilot commodities,
4. supplier quotes/contracts,
5. inventory/open-PO/material-requirement linkage,
6. **BUY_NOW / WAIT / PARTIAL_COMMIT / KEEP_CURRENT_PLAN** decision,
7. simple market/news feed with provenance,
8. approved-supplier comparison.

### Sourcing V1.5

- FX/freight scenario integration,
- quote-expiry alerts,
- market-exposure dashboard,
- sourcing decision history,
- what-if scenarios.

### Sourcing V2

- alternative-supplier discovery,
- customer-specific qualification workflow,
- qualified supplier alternatives into P3,
- richer commodity scenario generation,
- contract/hedge coverage,
- deeper transport-mode coupling.

Do **not** build a broad supplier marketplace or proprietary commodity-news company before the commitment decision is validated.

---

## 15. Validation metrics

For the first sourcing pilot, track:

- price paid vs relevant benchmark/quote set,
- savings from timing decisions,
- savings from source decisions,
- avoided emergency purchases/expedites,
- inventory/service consequences of waiting,
- working capital committed,
- buyer acceptance/rejection rate,
- time saved in market/supplier research,
- number of AI mappings requiring correction,
- alternative-supplier candidates that survive customer qualification,
- realized vs recommended action.

Do not report "savings" from a lower hypothetical future price unless the counterfactual is rigorous and the operational requirement could actually have waited.

---

## 16. Product guardrails

1. **Do not predict an exact commodity bottom.** Optimize commitment under price uncertainty.
2. **Do not let news directly create purchase orders.** News changes evidence/scenarios; optimization evaluates the decision.
3. **Do not invent raw-material SKUs.** Ingest customer masters/BOMs and use AI for mapping/normalization.
4. **Do not recommend an unqualified supplier as usable.** Candidate discovery and customer qualification remain separate.
5. **Do not optimize price in isolation.** Quantity, timing, inventory, service, lead time, freight, FX, and capital must remain coupled.
6. **Do not claim supplier qualification on ZAAD's authority.** The customer owns standards and approval.
7. **Do not turn the Sourcing tab into a passive dashboard.** Every major signal should connect to an exposure or decision.

---

## 17. Core identity

The Sourcing tab should make ZAAD's updated identity tangible:

> **Sourcing tells ZAAD what the market and supplier landscape looks like. Planning tells ZAAD what the business will need. ZAAD decides what commitment purchasing should make.**

That is the product bridge between sourcing and purchasing.

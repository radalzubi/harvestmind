# Commercial Pilot Readiness — Research

Last updated: 2026-08-31

## Decision

HarvestMind should enter the market as a **paid, operator-specific loss and
planning diagnostic for regional perishable distributors and food hubs**. The
first sale is not an autonomous replenishment system. It is a four-week,
human-reviewed engagement that converts existing exports into:

1. an auditable waste, shortage, service, supplier, and traceability baseline;
2. a backtested recommendation showing which policy actually wins on that
   operator's history; and
3. a monitored planning trial with explicit override and rollback controls.

The software must fail closed when data or model gates are weak. Synthetic
results are product tests, never customer proof.

## Indiana evidence used for the synthetic market test

Only public, primary sources set the external frame. Parameters that no public
source can establish—operator revenue, margins, supplier fill distributions,
spot-market premiums, buyer mix, and record error rates—remain labeled modeled
assumptions and are swept in sensitivity tests.

| Evidence | How it is used | Source |
|---|---|---|
| Indiana has commercially harvested vegetables, potatoes, and melons, with state and county reporting by crop. | Select an Indiana-relevant produce basket; do not infer an individual operator's volumes. | USDA NASS, 2022 Census of Agriculture, Indiana Table 36: https://data.nass.usda.gov/Publications/AgCensus/2022/Full_Report/Volume_1%2C_Chapter_1_State_Level/Indiana/ |
| Indiana's fresh produce harvest windows vary strongly by product and month. | Shape modeled local-availability seasons for sweet corn, tomato, cucumber, pepper, greens, squash, pumpkin, apples, berries, and roots. | Purdue Extension FoodLink seasonal chart: https://extension.purdue.edu/foodlink/includes/marketing/rackcard.pdf |
| Central Indiana's official climate reference is the 1991–2020 normal, with seasonally changing temperature and precipitation. | Introduce season-correlated supply volatility; weather is not claimed to predict a particular farm. | National Weather Service Indianapolis climate normals: https://www.weather.gov/ind/Climate_Normals |
| Evansville seasonal normals differ from central Indiana. | Include a southern-Indiana supplier cluster with a slightly different season and correlated risks. | National Weather Service Paducah seasonal normals: https://www.weather.gov/pah/SeasonalNormals |
| A food hub aggregates, distributes, and markets source-identified products from multiple producers to multiple buyers. | Define the simulated operator and the initial customer profile. | USDA AMS Local Food Directories: https://www.ams.usda.gov/services/local-regional/food-directories-listings |
| Food Traceability Rule records center on Key Data Elements at Critical Tracking Events, with records producible to FDA within 24 hours. Congress directed FDA not to enforce before July 20, 2028. | Keep lot/traceability completeness in the diagnostic; never call the product compliance certification. | FDA Food Traceability Rule: https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-final-rule-requirements-additional-traceability-records-certain-foods |
| US farms sold nearly $10.7B through direct and intermediary channels in 2020; 73% of that value used intermediary supply chains. | Establish that intermediary local-food trade is material; not a bottom-up TAM for HarvestMind. | USDA ERS: https://ers.usda.gov/data-products/charts-of-note/104408 |

## Competitive boundary

Afresh publicly offers sophisticated fresh forecasting, ordering, inventory,
production planning, and distribution-center buying for grocery enterprises.
That validates the pain but makes large grocers a poor first wedge. HarvestMind
must win below that enterprise tier: independent regional distributors, food
hubs, cooperatives, and institutional produce suppliers that can export data but
cannot justify a large transformation program.

Source: https://www.afresh.com/departments/produce

## Hidden operator pain the product must handle

- Product identity and units do not match across orders, deliveries, lots, and
  waste sheets.
- Experienced buyers carry policy in their heads; software recommendations
  without provenance or override explanations will not be adopted.
- Short history and seasonal assortment changes make a complex model look
  impressive in-sample while losing to a run-rate rule out-of-sample.
- Spot availability and premium change the optimum more than a dashboard makes
  obvious. A single assumed spot price is commercially unsafe.
- Missing lot, supplier, transformation, or ship-to records create traceability
  exposure, but a planning product cannot certify legal compliance.
- The buyer with authority to share data may not own IT, procurement, food
  safety, and finance. The pilot must produce value for all four without asking
  for an ERP replacement.

## First commercial offer

**Offer:** Indiana Perishable Margin Diagnostic

- Four weeks, one facility, up to 50 active products, 26–104 weeks of exports.
- Required minimum: orders and deliveries. Waste and inventory lots improve the
  result but are not prerequisites for the initial data-quality report.
- Deliverables: data-quality score, loss map, service and supplier risk,
  traceability-gap inventory, four-policy rolling-origin benchmark, spot-cost
  sensitivity, and a 30-day monitored action list.
- Price: **$5,000 fixed diagnostic**, credited toward a later implementation.
- Success gate: at least one decision with a measurable, operator-approved
  baseline and a backtest that beats the incumbent policy after realistic
  costs. No savings guarantee.
- Expansion: $1,500–$3,000 per month for monitored planning and reporting only
  after a real-data gate passes. Gain-share is optional and secondary because
  attribution disputes slow early sales.

## Go/no-go evidence still missing

1. Three operator data samples with permission and at least 26 weeks of orders
   and receipts.
2. One paid diagnostic or equivalent signed design-partner commitment.
3. A buyer-confirmed incumbent workflow and quantified cost of one bad decision.
4. Out-of-sample superiority—or an honest deterministic fallback—on each real
   dataset.
5. Security, retention, incident response, and deletion terms accepted before
   partner uploads.


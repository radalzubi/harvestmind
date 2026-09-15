# ZAAD Operating Product V2.1A — Visual Insights + Canonical Connectivity + Customer Demand Intelligence

**What it is.** A first-class *Insights* section in the Analyse group, built as

    OPERATIONAL DATA → SERVER-SIDE AGGREGATION → VISUAL INSIGHTS

and, separately,

    LATEST COMPLETED ZAAD PLAN / REPORT → ENGINE-BACKED VISUALS

Insights reads the operator's uploaded records and the most recent *completed* workspace plan in
the job store. It never starts a solve to have something to draw, it never recomputes an optimizer
number, and when the workspace's data has moved since that plan finished it says so on every
optimizer-derived surface ("Latest ZAAD plan: … Workspace data changed afterward."). Nothing under
`zaad/` that computes a decision changed.

Release line: V2.1A follows the V2 operating product (`OPERATING_PRODUCT_V2.md`) and the planner
recovery pass (`PRODUCTION_SOLVE_PERFORMANCE_RECOVERY.md`). The planner's default-scope latency is
still an open owner decision; V2.1A was built so that it does not depend on it (§1 of the brief).

## 1. Architecture

| layer | where | what |
|---|---|---|
| aggregation service | `api/product/insights.py` | bounded DuckDB aggregations over the vault (one `conn` = the caller's own vault); the latest plan read from the job store, filtered by operator; provenance on every payload |
| router | `api/routers/zaad_insights.py`, prefix `/api/zaad/insights` | `summary`, `plan`, `demand`, `demand/period`, `inventory`, `supply`, `suppliers`, `service`, `decisions`, `value`, `connectivity`; one `Scope` of filters for all; `422 insights_scope_invalid` on a bad bucket, date or id |
| web library | `web/src/lib/zaad/insights.ts` | types, fetchers, URL ⇄ filter state, honest-null rendering (`shown`), link builders (chart → surface, action → insights), `planSentence`, `scopeSentence` |
| page | `web/src/app/insights/page.tsx` | six tabs (+ Perishability when a sector is declared), one filter bar, a period drill-down drawer, no dead-end chart |
| chart kit | `web/src/components/charts.tsx` (`MultiLine`, `StackedBars`, existing `HBars`), `web/src/components/insights/ChartCard.tsx` | title + description on every chart, "Show as table", "Data & scope" disclosure |
| Home | `web/src/app/home/page.tsx` → *At a glance* | three summaries only: observed orders (12 weeks), inventory exposure, decisions and actions — from the same `/summary` the page uses |
| decision → insights | `web/src/components/workspace/DecisionDetail.tsx` | *See demand behind this decision · See inventory position · See supplier history · See value breakdown*, with the decision's product and supplier as filters (`insightsLinksFor`, tested) |
| demo company | `synthetic/fmcg/demo_company.py`, `POST /intake/load-demo-company`, `scripts/zaad_demo_workspace.py` | one coherent, deterministic, clearly labelled DEMO distributor; the loop through the public API |

### Filters and URL state

`bucket` (day / week / month), `start`, `end`, `sku`, `category`, `brand`, `customer`, `location`,
`supplier` — all live in the URL (`/insights?tab=demand&bucket=month&customer=…`), all bind as
parameters on the server (identifiers are validated for length and control characters, names of
buckets and sort keys are code literals). A chart's links out carry the same filters: Inventory
(`?sku=&category=&brand=&supplier=&location=`), Purchase orders (`?tab=imported&postate=open&po=`),
Data (`?dataset=&fcol=&fval=`), Decisions (`?decision=`), a supplier's page (`/diagnostics?tab=suppliers&q=`).

### Source-of-truth rule, per number

| kind | rule |
|---|---|
| measured | a sum, count or ratio over uploaded rows; the payload names the rows, numerator and denominator |
| optimizer-reported | read verbatim from the latest DONE plan's report (`economics`, `commitments.orders`, `actions`, `atp`, `sourcing`, `network`, `recourse`); the plan's id, `as_of`, finish time and staleness travel with it |
| documented aggregation | a stated formula over measured numbers (weeks of cover = units on hand ÷ average weekly units ordered over 12 weeks — the Inventory page's own rule; service level = shipped ÷ ordered on measured lines) |
| unavailable | `null` with a reason: `UNKNOWN`, `NOT_MEASURED`, `NOT_APPLICABLE`, `NO_DATA`, `BLOCKED_BY_DATA`, `NOT_IN_PLAN` — never `0`. An empty table is `NO_DATA`; customer orders without a site make demand-by-site `BLOCKED_BY_DATA`; a supplier with no promised dates has lateness `NOT_MEASURED` |

No optimizer economics are reproduced in TypeScript; the web formats what the server sent.

## 2. The tabs

**Overview.** Plan line (which plan, when, stale or not); observed orders over the last twelve
weeks with last-period change and largest-customer share; inventory position (on hand, inbound,
weeks of cover, by site); open supply (open orders, past their date — with the count of orders that
carry no promised date and are *not* counted late — open value, by supplier); recommendations by
verb with responses, proposals, external placements and outcomes.

**Demand.** *OBSERVED CUSTOMER ORDERS* — the label the page uses, never "demand" and never "true
demand". Ordered, shipped and unfulfilled per bucket where the upload records a shipped quantity
(lines without one are counted as unmeasured, never as fulfilled or lost); totals, period-over-period
change, concentration (largest customer, top five, HHI); top customers, products, categories and
sites (each bar filters the page). **Drill-down:** a click on a period opens the customers,
products and sites behind it, the largest increases and declines against the period before, the
stock and cover behind the products involved, their open purchase orders, and the latest plan's
decisions that touch them — with links into Inventory, Purchase orders, Data and Decisions.

**Inventory.** Units on hand over time and value over time from the uploaded snapshots (the last
snapshot in each bucket; nothing reconstructed); units by site, period by period (site rows sum to
the total); latest position with on hand vs inbound and weeks of cover; by category.

**Supply & suppliers.** Open orders by expected arrival (orders without a promised date shown
apart, never dated); received per period; open-order aging; open supply by supplier and by
destination; the supplier table — fill (units received ÷ units ordered on matched orders), short
fills, lead p50/p90, lateness (orders after their promised date ÷ orders that carry one, with
coverage), share of units ordered, open exposure, declared amendment rights on open orders,
declared alternatives — and a month-by-month trend for the filtered supplier.

**Service & customers.** Ordered / shipped / unfulfilled per period, service level per period, by
customer (with a class only where the P5 declarations name that customer; the released contract declares open orders against one aggregate customer, so this reads *not declared* until a per-customer declaration exists), by
declared class with the declared floors, the latest plan's allocation block when it carries one
(else `NOT_IN_PLAN`). No invented customer risk score: the page says so.

**Decisions & value.** The latest plan's verdicts on open orders by verb (KEEP · DEFER · EXPEDITE ·
REDUCE · CANCEL · SPLIT) plus purchases and moves, read verbatim; the six columns *recommended /
approved / rejected / overridden / externally executed / outcome available*, each a count of rows of
its own kind, not a funnel; **five value registers, each its own card and never one number**:

| register | source | basis stated on the card |
|---|---|---|
| MODELED_DIFFERENCE | latest plan `economics.incumbent_costs.TOTAL − selected_costs.TOTAL` and the ledger | a modelled difference, not a saving |
| BACKTESTED_OPPORTUNITY | — | not measured: no held-out replay is wired in |
| APPROVED_EXPECTED_DIFFERENCE | each approved proposal's evaluation (`evaluation.compare` over its two stored runs) | expected at approval time, not observed |
| OBSERVED_AFTER_ACTION | `zaad_outcomes` by metric | observed after action; not attributed to ZAAD |
| REALIZED_VALUE | outcomes with a comparator *and* its stated basis | only these may be called realized |

and the **engine connectivity matrix** (§3).

**Perishability** appears only when the SKU master declares a sector; it points to the sector
diagnostics rather than drawing a second reading of them.

## 3. Optimizer connectivity matrix

Served live by `GET /api/zaad/insights/connectivity` (status computed from the latest plan's blocks
and the workspace's declarations) and shown on Decisions & value:

| family | backend source | API exposure | visualization | drilldown | status rule |
|---|---|---|---|---|---|
| P0 protection / recovery | `report.protection`, `status`, `reasons` | jobs read; `/insights/decisions` | plan status and verdict; Decisions | Decision detail | VISUALIZED when a plan exists |
| P1 purchasing economics | `report.economics` | `/insights/value` | MODELED_DIFFERENCE ledger | Decision detail economics | VISUALIZED when the plan carries `economics` |
| P2 multi-echelon network | `report.network`, transfer actions, `request.locations/transfers` | `/insights/inventory?location=`, `/workspace/locations` | inventory by site and the site series; Network | Inventory filtered by site; transfer decisions | VISUALIZED / NOT_IN_PLAN / NOT_DECLARED |
| Sector physics | `stg_fmcg_skus` sector columns | `/workspace/sector` | Perishability tab (only when declared); Diagnostics | Diagnostics sector table | VISUALIZED / NOT_DECLARED |
| P3 sourcing portfolio | `report.sourcing`, `stg_fmcg_sources` | `/insights/suppliers` | declared alternatives and share; recommended split on Decisions | supplier page | VISUALIZED / NOT_IN_PLAN / NOT_DECLARED |
| P4 adaptive recourse | `report.recourse`, `stg_recourse_spec` | jobs read | **not visualized** (the value of adaptation is in the plan's recourse block only) | — | IN_PLAN_NOT_VISUALIZED / NOT_IN_PLAN / NOT_DECLARED |
| P5 ATP / allocation | `report.atp`, `stg_atp_*` | `/insights/service` | allocation block and declared classes | customer rows | VISUALIZED / NOT_IN_PLAN / NOT_DECLARED |
| P4B open PO intervention | `report.commitments.orders`, `stg_po_commitments/options` | `/insights/decisions` | verdicts by verb | Decision detail; Purchase orders | VISUALIZED / NOT_IN_PLAN / NOT_DECLARED |

## 4. Provenance ("Data & scope")

Every chart card carries a disclosure with: metric definition, numerator, denominator, scope (date
range, bucket, filters, rows), source tables, coverage (e.g. lines without a shipped quantity, open
orders without a promised date, rows without a cost), last updated (the newest upload stamp across
the staging tables), and — when the number is optimizer-derived — the plan (id, finished, `as_of`,
stale). It is the same `provenance` object the API returns; the web formats it.

## 5. Accessibility, Arabic, security

* Each chart is a `<figure>` with a title and a one-sentence description (`aria-labelledby` /
  `aria-describedby`); a *Show as table* toggle gives the values without colour or a pointer;
  series differ by dash pattern as well as hue; drill-downs open in the existing keyboard-safe
  `Drawer`; period chips duplicate the click-on-a-point interaction for keyboards.
* Copy for the section, tabs, filters and the plan line is in `web/src/lib/i18n/{en,ar}.ts`
  (`workspace.insights`; the nav key `insights`); identifiers and codes are never translated;
  numbers and period labels keep ISO digits and are isolated `dir="ltr"` inside RTL text.
* Tenant safety: `get_conn` yields the caller's vault; the latest plan is `JobStore.list(operator)`;
  commitments, options and ATP declarations are read `WHERE operator_id = ?`; filter values bind;
  there is no shared cache. Tests pin that another operator's plan is not visible and that an
  injected filter value returns no rows.

## 6. The demo company (DEMO / SYNTHETIC DATA)

`synthetic/fmcg/demo_company.py` builds *Al-Bahr Trading (DEMO)*: 36 products in six categories
and brands, 6 suppliers on declared corridors (Aqaba from Germany and China, Jeddah, the Saudi road,
Umm Qasr, the Iraq overland route), 8 customers (six of them behind open customer orders declared in three service classes against the contract's aggregate customer), 3 sites with two
lanes and a transfer history, 104 weeks of customer orders with what was shipped (≈21,000 lines),
weekly site-level inventory snapshots (≈11,200 rows), fortnightly purchase orders with promised
dates (≈1,900) and receipts (≈1,950, partial receipts included), declared alternative sources
(P3), amendment rights on three open orders (P4B), service classes and open customer orders (P5),
and economics. Scenarios built in and test-pinned (`tests/integration/test_demo_company.py`):
a stable, a growing, a declining, a seasonal and a new customer; one demand spike five weeks
before the as-of date; a deteriorating supplier, a reliable one, a short-filling one, and one
whose orders sometimes carry no promised date; one excess product, one shortage exposure, one
site imbalance; an open order the engine is likely to defer, one to expedite, one to keep.

`scripts/zaad_demo_workspace.py --api …` creates a throwaway workspace through the self-serve
path, loads the company, runs the plan over the scenario products through the released jobs path,
records three responses (accepted, rejected, overridden with a reason), creates a proposal from a
purchase the plan recommends, evaluates it, submits, approves, exports, records the external status
and two outcomes (one with a stated comparator). Recommendations come from the engine; nothing is
hard-coded. It refuses to replace an existing workspace's data without an explicit flag and never
runs by itself.

## 7. Performance

Server-side only; every series is capped at 400 points, every breakdown at 10 rows, supplier
tables at 50. Measured with `scripts/insights_scale_qa.py` on the QA scale fixtures (in process,
five runs each, median / p95):

| products | rows (orders / POs / receipts / snapshots) | summary | demand (week) | inventory (month) | supply (week) | suppliers (month) | service (month) |
|---|---|---|---|---|---|---|---|
| 10,000 | 520k / 120k / 100k / 30k | 100–160 ms | ~40 ms | ~30 ms | ~70 ms | ~30 ms | 14 ms |
| 50,000 | 2.6M / 600k / 500k / 150k | 437 ms | 116 ms | 108 ms | 265 ms | 98 ms | 31 ms |

Everything is under the ~800 ms median budget at 50,000 products; payloads are 2–25 KB (the
supplier table with its monthly trend, 236 KB at 50 suppliers × 25 months, is the largest and is
bounded). The demo workspace (36 products) answers in 1–80 ms.

## 8. Tests

Backend (`tests/integration/test_zaad_insights.py`, 15): observed orders equal the rows; weekly and
monthly buckets carry the same total; filters narrow and bind (an injected value returns nothing);
concentration and period-over-period; a period opens to its customers and products; inventory from
snapshots with sites summing to the total; supply agrees with the Purchase Orders rule; supplier
denominators; lateness `NOT_MEASURED` without promised dates; service level on measured lines; the
latest plan read verbatim and tenant-scoped; staleness; nothing claimed without a plan; an empty
workspace says `NO_DATA`; unauthenticated refused. Demo integrity
(`tests/integration/test_demo_company.py`, 7): references resolve, quantities reconcile, sites sum,
dates and currency, every scenario is in the rows, Insights aggregates equal raw sums.
Frontend (`web/src/lib/zaad/__tests__/insights.test.ts`, 9): URL ⇄ filters, malformed URLs, honest
nulls, plan sentence, scope sentence, links, period labels, the tab list, action → insights links.

## 9. Known limits

* P4 adaptive recourse is in the matrix as *not visualized*; its value-of-adaptation stays in the
  plan's recourse block.
* Perishability is a pointer to the sector diagnostics, not a second chart set.
* The demo's plan loop depends on the released planner's latency: on the shared production
  machine a 5-product plan takes ~2–3 minutes when rested (see the recovery record).
* Backtested opportunity remains `NOT_MEASURED` by design.

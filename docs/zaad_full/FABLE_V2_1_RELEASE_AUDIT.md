# Fable V2.1A release audit — Visual Insights + Canonical Connectivity + Customer Demand Intelligence

Branch `feat/zaad-insights-canonical-connectivity` from `main` `3a25b52` (production `d2a3cb5` plus
docs). Audited against the V2.1A brief (§1–45) by reproduction: every number below was produced by a
command in this repository, and the sections that could not be produced say so.

## 1. Rules the brief sets, and where each is met

| rule | met by | evidence |
|---|---|---|
| Insights must not start a solve to render | `api/product/insights.latest_plan` reads the job store; no route calls the planner | `tests/integration/test_zaad_insights.py::test_without_a_plan_nothing_is_claimed`; the router imports nothing from `zaad.full.planner` |
| the latest plan older than the data is shown honestly | `stale` = any staging table written after the plan finished; the plan line reads "Workspace data changed afterward." | `test_a_plan_older_than_the_data_is_said_to_be_stale`; `web/.../insights.test.ts` plan sentence |
| customer orders are OBSERVED CUSTOMER ORDERS, never true demand; no invented lost demand | label on the payload and the page; unfulfilled = ordered − shipped only on lines that record a shipped quantity; unmeasured lines counted | `test_demand_is_observed_orders_and_equals_the_rows` |
| never 0 late when promised dates are missing | lateness denominator = orders with a promised date; `NOT_MEASURED` when none | `test_lateness_is_not_measured_when_no_order_carries_a_promise`; `test_supplier_metrics_carry_their_denominators` (coverage < 1 on the partial-promise supplier) |
| NULL is never zero; 0 / UNKNOWN / NOT MEASURED / NOT APPLICABLE / NO DATA / BLOCKED BY DATA / NOT IN PLAN distinct | `_null(reason, why)` on the server; `shown(value, format, reason)` on the web | `test_an_empty_workspace_says_no_data_not_zero`; `insights.test.ts` "a missing number is shown as its reason" |
| five value registers never combined | separate register objects, `never_combined` sentence, five cards | `test_decisions_and_value_read_the_latest_plan_verbatim`; the Decisions & value tab |
| no optimizer economics in TypeScript | the web formats server fields; no arithmetic on ledger values | grep: `insights.ts` and the page contain no cost formulas |
| every engine family visible or documented as not visualized | `GET /api/zaad/insights/connectivity`, matrix on the page and in `OPERATING_PRODUCT_V2_1_INSIGHTS.md` §3 | `test_decisions_and_value_read_the_latest_plan_verbatim` (P4B VISUALIZED, P4 NOT_DECLARED, P5 NOT_IN_PLAN on the fixture) |
| server-side aggregation, no huge raw datasets to the browser | series capped at 400 points, breakdowns at 10, tables at 50; payloads 2–25 KB (236 KB max for the supplier trend at 50 suppliers) | `scripts/insights_scale_qa.py` output, §4 |
| ~800 ms median target | measured at 10k and 50k products | §4 |
| tenant isolation | vault per `conn`; plan lookup by operator; declarations `WHERE operator_id = ?`; filters bind | `test_decisions_and_value_read_the_latest_plan_verbatim` (another operator's plan, a third operator with none); `test_filters_narrow_the_rows_and_bind_as_values` (injected value → no rows) |
| chart → action, action → insights | `linksFor`, `insightsLinksFor`; leads on every card; decision detail links | `insights.test.ts` "every chart leads somewhere", "a decision opens the demand, inventory and supplier views behind it" |
| one complete demo company, labelled, deterministic, reconciling | `synthetic/fmcg/demo_company.py`; `POST /intake/load-demo-company`; `scripts/zaad_demo_workspace.py` | `tests/integration/test_demo_company.py` (7) |
| Arabic / RTL | `workspace.insights` copy in `en.ts` / `ar.ts`; numbers isolated `dir="ltr"`; ids untranslated | browser walk §6 |
| accessibility | figure/figcaption with title + description, table alternative, dash-distinguished series, keyboard chips, existing Drawer | browser walk §6 |
| no optimizer mathematics changed | no file under `zaad/` in the diff | `git diff --stat main...HEAD -- zaad/` is empty |

## 2. Backend tests

`tests/integration/test_zaad_insights.py` — 15 tests; `tests/integration/test_demo_company.py` — 7
tests. Both green locally (22 passed). Full suite and the frozen regression run in CI on the exact
head (§7).

## 3. Frontend tests

`web/src/lib/zaad/__tests__/insights.test.ts` — 9 tests (URL ⇄ filters, malformed input, honest
nulls, plan sentence, scope sentence, links, period labels, tab list, action → insights). Whole web
suite: 149 passed; `tsc --noEmit` clean; eslint 0 errors.

## 4. Scale QA

`python3 -m scripts.insights_scale_qa --skus 10000,50000` (in process, five runs each):

| products | orders / POs / receipts / snapshots | summary | demand week | demand month+category | period | inventory month | inventory week+site | supply week | suppliers month | service month |
|---|---|---|---|---|---|---|---|---|---|---|
| 10,000 | 520,000 / 120,000 / 100,000 / 30,000 | 157.4 ms | 48.4 ms | 33.9 ms | 32.5 ms | 36.3 ms | 40.3 ms | 84.9 ms | 41.7 ms | 14.2 ms |
| 50,000 | 2,600,000 / 600,000 / 500,000 / 150,000 | 436.5 ms | 116.3 ms | 71.1 ms | 68.4 ms | 107.6 ms | 91.2 ms | 264.7 ms | 98.4 ms | 30.6 ms |

`over_budget: []` at both sizes. The demo workspace answers every query in 1–80 ms.

## 5. Cross-surface reconciliation

Checked by test against the same vault: Insights inventory latest units = the Inventory page's
snapshot rule (`_stock_cte`), sites sum to the total; Insights open units = the Purchase Orders rule
(`_open_po_cte`: open until the first receipt); supplier fill and lateness use Diagnostics'
`_matched_cte` and thresholds; demand totals = `sum(qty_ordered)` over the rows; decision counts =
the plan's `commitments.orders` and `actions` read verbatim; value = the plan's ledger and the
evaluations' `compare`. Production check on the deployed runtime in §8.

## 6. Browser QA

Recorded below after the live walk (local dev server on the demo workspace; production after deploy).

## 7. CI, merge, deploy

Recorded below.

## 8. Production

Recorded below.

## 9. Release decision

Recorded below.

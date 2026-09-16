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

Local (`next dev` on :3000 against the API on :8001 run from the version-matched 3.12 venv with a job
store; demo workspaces created by `scripts/zaad_demo_workspace.py`):

| check | result |
|---|---|
| Insights in the Analyse group, between Purchase orders and Network | yes (desktop rail and phone "More") |
| Overview on the data-only demo workspace | plan line "No completed ZAAD plan yet … run one from Home"; observed orders 12 weeks (549,264 ordered, 35,214 unfulfilled, −1.9 % last week, largest customer 24 %); inventory position (434,522 on hand as counted 13 Sept 2026, 173,304 inbound, 9.2 weeks of cover, three sites summing); open supply (73 open orders, 43 past their date with 6 without a promised date *not counted*, JOD 857,660); decisions card reads *Not in plan* |
| Demand, weekly, whole history | OBSERVED CUSTOMER ORDERS label; 4,137,864 ordered over 21,011 lines, 4,064,902 shipped; concentration 86 % top 5 / HHI 0.17; top customers / products / categories / sites; "Data & scope: the whole history, by week · no filters · 21,011 rows" |
| period drill-down on the spike week (w/c 2026-08-03) | DEMO-CUST-GROW on top (14,436 units); largest increases DEMO-0013 (+2,532), DEMO-0033, DEMO-0001 (+768), DEMO-0007 (+528) — the three spike products among them; affected inventory, open purchase orders, related decisions ("no completed plan yet, so nothing is claimed"); links to Inventory, Data, Decisions |
| Demand, monthly, category = Beverages | 795,276 ordered over 3,522 lines; the newest month is partial and the comparison says so (after the fix in `e2796f7`) |
| Inventory, monthly | units and value over time (25 monthly points), by site stacked, latest position |
| Supply & suppliers with `supplier=DEMO-SUP-02` | **500 on the first walk** — aging query bound parameters out of order; fixed in `e2796f7` with a test; re-verified below |
| Service & customers, monthly | ordered / shipped / unfulfilled stacked, service level per period, by customer with denominators (RETAIL-A 97.5 %, GROW 99.1 %), class *not declared*, ATP *Not in plan* |
| Decisions & value without a plan | every card says *Not in plan* / *Not measured* / *No data*; the six columns read 0 as counts; connectivity matrix renders |
| Arabic | `dir=rtl`, nav الرؤى, tabs نظرة عامة · الطلب · المخزون · التوريد والموردون · الخدمة والعملاء · القرارات والقيمة, page title الرؤى; numbers and ids unchanged; plan line localized after `e2796f7` |
| Mobile (375 × 812) | filters wrap, chart fills the width, stat tiles two-up, period chips wrap, Data & scope readable; no horizontal scroll |
| console | no errors on the data tabs (the one 500 above, fixed) |

Plan-backed workspace (`op_8f0e526c`, after `scripts/zaad_demo_workspace.py` ran the loop through the API on the local server — plan `job_7180f6…` over DEMO-0008, DEMO-0010, DEMO-0025, DEMO-0021, DEMO-0001; the engine returned RETAIN_INCUMBENT with KEEP on all three declared rights, 18 purchases and 112 moves; a proposal from the engine's purchase on the shortage product, evaluated at +5,300 JOD versus current, submitted, approved, exported, placed externally, two outcomes recorded, one response rejected):

| check | result |
|---|---|
| plan line | "Latest ZAAD plan: 15 Sept 2026 · 5 products." (not stale: no upload after the plan) |
| Decisions & value — recommendations by action | KEEP 3 · BUY 18 · MOVE 112, read from the plan; decision list links to `/decisions?decision=…` |
| the six columns | Recommended 133 · Approved 1 · Rejected 1 · Overridden 0 · Externally executed 1 (placed externally) · Outcome available 1 (2 outcomes, 1 with a comparator) |
| five registers | Modelled difference JOD 476,724 − 476,724 = 0.00 ("a modelled difference, not a saving" — the plan retained the incumbent); Backtested *Not measured*; Approved expected difference: the proposal at +5,300 JOD; Observed after action: purchase_cost 1, received_units 1; Realized value: 19,800 observed vs 20,105 comparator with its stated basis |
| connectivity matrix | P0 VISUALIZED, P1 VISUALIZED, P2 VISUALIZED (after the `network_service` / transfer rule fix), sector NOT DECLARED, P3 VISUALIZED, P4 NOT DECLARED, P5 VISUALIZED, P4B VISUALIZED |
| Supply & suppliers with `supplier=DEMO-SUP-02` | renders; "DEMO-SUP-02 — month by month" trend present; no 500 (fixed) |
| decision detail → insights | "See demand behind this decision" → `/insights?bucket=week&sku=DEMO-0008&tab=demand` on the KEEP DEMO-PO-00416 decision; inventory, supplier and value links present |
| Home | "At a glance" section with the three summaries, from the same `/summary` |
| console | no errors after the API restart |



## 7. CI, merge, deploy

| step | result |
|---|---|
| exact-head CI | run 35011852846 on `2901ee9` (the PR head: code head `b882e0a` + two Markdown commits; the `pull_request` event ran the full workflow): **13 / 13** — gitleaks, ruff, mypy, bandit + pip-audit, unit-core, unit-zaad-1…4, integration, zaad frozen regression, frontend (typecheck, lint, test, build), docker build |
| earlier heads | `e2796f7`: ruff (one F541) and bandit (four B608 on `api/product/insights.py`) failed → fixed in `b882e0a`; runs on `b882e0a` / `9c2cfc0` were cancelled by `cancel-in-progress` when the next commit was pushed |
| ready + merge | PR #84 marked ready; `main` verified unchanged at `3a25b52`; merged as **`13dde49`** (`Merge PR #84: …`, parents `3a25b52` + `2901ee9`, tree `1b5cb85` = the tested head's) |
| backend deploy | `deploy-api` workflow run 35052495247 from the exact merge → Fly `zaad-api` **v28**, image `canonical-13dde49`, digest `sha256:374b4e91f061cce054a05749aa48f29be1e9707c2f4bd642ba712b18617c3381`; rolling restart clean (application startup 03:40:25 UTC, health passing) |
| Vercel | GitHub deployment records `Production – zaad` and `Production – harvestmind` for `13dde49`; `vercel ls --prod` Ready |

## 8. Production

| check | result |
|---|---|
| `GET /health` | 200, 0.45 s |
| release smoke on v28 (`scripts/operating_product_release_smoke.py --self-serve`, throwaway `op_15bc84a7`, 427,995-row sample) | **24 / 24**: the 19 V2 checks plus five Insights checks — summary answers; demand is labelled OBSERVED CUSTOMER ORDERS with provenance (36 months); lateness NOT_MEASURED for all eight sample suppliers (no promised dates in the sample — never 0 late); five value registers in order; the connectivity matrix lists every family |
| Fly logs | the rolling restart's usual uvicorn SIGINT trace, then startup and health; no application errors |
| demo on production (`scripts/zaad_demo_workspace.py --products 5`, throwaway `op_387d9787`) | the company loaded (42,280 rows); the 5-product plan over three sites reached **TIMEOUT at its 562 s cap** — the V2 planner's known limit on `shared-cpu-2x` (recovery record §3.1), not an Insights defect; the job row records it honestly and the workspace's Insights read *No completed ZAAD plan yet*. The full loop through the API (plan → responses → proposal → evaluation → approval → export → external status → outcomes) completed twice on the local server with the same code (§6). That solve spent the machine's burst balance (steal 990 s in the 17 min after the restart), so a plan-backed production demo has to wait for the balance and, for the default scope, for the owner's machine decision |
| Insights on production, browser walk (`https://zaadsupply.com/insights`, the smoke's sample workspace `op_15bc84a7`, 427,995 rows, machine throttled after the demo solve) | Insights in the Analyse rail; Overview: plan line *No completed ZAAD plan yet*, observed orders card empty for the last-12-weeks window with "Ordered —, 0 lines" (the sample ends 22 Dec 2025 — not a zero), inventory position 127,465 on hand as counted 22 Dec 2025 / 124,902 inbound / 2.1 weeks of cover / one site, open supply 205 orders with **205 without a promised date (not counted as late)**, USD 676,816, by supplier; decisions card *Not in plan*. Demand (monthly): OBSERVED CUSTOMER ORDERS, 9,895,044 units over 371,140 lines, 2 Jan 2023 → 22 Dec 2025, **Shipped: Not measured — 371,140 lines without a shipped quantity**, "2025-11 vs 2025-10 −1.7 % · the newest period is partial and left out", concentration 47 % top 5 of 25 customers; filter options from the vault (cat_0…5, 25 customers, MAIN, 8 suppliers). Console: no errors. Reads took 3–10 s on the throttled machine (idle band on a rested one, §4 of the recovery record) |

## 9. Release decision

V2.1A is judged on what the brief asks of Insights: server-side aggregation of the operator's
records, engine-backed visuals read from the latest completed plan, honest nulls, five registers
apart, connectivity documented, drill-downs and links in both directions, a complete demo company
that reconciles, scale under budget, tenant isolation, Arabic, accessibility, exact-head CI, merge,
deploy, production smoke. All of it is in place and verified; the one production step that did not
complete — the demo's own plan — is the planner latency the brief explicitly told this release not
to wait for ("Insights must NOT depend on starting a fresh optimizer run just to render"), and the
page behaves exactly as specified when no plan exists. **ZAAD OPERATING PRODUCT V2.1A — RELEASE
PASS**, with the planner's default-scope latency still the owner's decision recorded in the ledger.

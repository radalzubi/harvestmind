# ZAAD Enterprise Analytics V1 — implementation record

**Status: IN PROGRESS (2026-09-17).** This file tracks every requirement of the V1 brief against the
architecture (`ENTERPRISE_ANALYTICS_ARCHITECTURE.md`, `SEMANTIC_LAYER_ARCHITECTURE.md`,
`ASK_ZAAD_AI_ANALYTICS_ARCHITECTURE.md`) and where it landed in the repository. Branch
`feat/enterprise-analytics-v1` from `main` `ea08a93`. The optimizer (P0–P5, P4B, solver settings,
default scope, timeouts, MIP gap, service semantics, ledger, tie-breaks) is not touched; every gate
that proves that is listed in §6.

Statuses: **DONE** (implemented, tested), **PARTIAL** (implemented with a stated boundary), **DEFERRED**
(deliberately not built in V1; reason given), **N/A**.

## 1. Package layout (repository fit, architecture §39 / §55)

| layer | location | notes |
|---|---|---|
| semantic registry (entities, dimensions, metrics, relationships, grains, coverage, nulls, permissions, versions) | `api/analytics/semantic.py` | machine-readable dataclasses; served by `GET /api/zaad/analytics/model` |
| query contract, visual spec, result contract, error taxonomy | `api/analytics/contracts.py` | pydantic models; the only shapes the browser and the AI may send |
| validation (semantic, permission), planning | `api/analytics/validate.py`, `api/analytics/planner.py` | deterministic; refuses before any SQL exists |
| storage adapter boundary + DuckDB adapter | `api/analytics/engines/base.py`, `api/analytics/engines/duckdb_adapter.py` | `StorageAdapter.execute(PhysicalPlan)`; only the adapter names DuckDB |
| result assembly, coverage, null cells, provenance | `api/analytics/results.py` | cells are `value` or `{value: null, reason, why}` |
| dataset version, freshness | `api/analytics/freshness.py`, migration `db/migrations/028_enterprise_analytics.sql` | per-table max stamp + row count → deterministic id |
| tenant cache | `api/analytics/cache.py` | key = (tenant, dataset version, model version, permissions hash, spec hash) |
| permissions (analytics capabilities over the 4 roles) | `api/product/governance.py` (+7 capabilities), `api/analytics/permissions.py` | one auth system |
| saved analyses, dashboards, audit | `api/analytics/saved.py`, migration 028 | validated on save and on open |
| exports | `api/analytics/exports.py` | CSV / XLSX with provenance sheet; print via the page |
| Ask ZAAD (provider boundary, planner, validator, interpretation, context) | `api/analytics/ai/` | provider-neutral; deterministic planner when no model |
| deterministic signals | `api/analytics/signals.py` | supplier deterioration, cover exposure |
| optimizer hand-off | `api/analytics/handoff.py` | builds a `DecisionContext`, routes to the existing jobs path |
| Insights bridge (one definition) | `api/analytics/insights_bridge.py` | representative Insights series served through the engine |
| API | `api/routers/zaad_analytics.py` | `/api/zaad/analytics/*` |
| web: client, state, visual mapping | `web/src/lib/analytics/` | typed client; no SQL; URL-safe state |
| web: components | `web/src/components/analytics/` | model panel, canvas, renderer, config, filters, pivot, KPI, dashboard grid, ask panel |
| web: pages | `web/src/app/explore`, `web/src/app/dashboards`, `web/src/app/ask`, `web/src/app/settings/shortcuts` | |
| destination registry, commands, shortcuts, preferences | `web/src/lib/commands/` | one registry feeds sidebar, tabs, More, palette, shortcuts, quick actions |

## 2. Requirement tracker — Enterprise Analytics V1

| § | requirement | implementation | status | evidence | deviation |
|---|---|---|---|---|---|
| 4–5 | governed semantic layer, machine-readable registries, metric contract with the listed fields | `api/analytics/semantic.py` | DONE | `tests/unit/test_analytics_semantic.py` | — |
| 6 | initial metric catalogue (ordered / fulfilled / unfulfilled / fill rate, inventory, open PO, supplier metrics, customer, decisions, five registers); unsupported classified | `semantic.py` `METRICS` with `status` EXISTS / DERIVABLE / REQUIRES_NEW_DATA / FUTURE | DONE | same | `backtested_opportunity` FUTURE, `lead_time_variability` DERIVABLE (p90 − p50), `forecast_accuracy` FUTURE — not manufactured |
| 7 | one metric definition (Insights consumes governed metrics) | `insights_bridge.py` (`INSIGHTS_DEFINITIONS` maps every Insights payload to its `metric_id@version`) | PARTIAL | `tests/integration/test_analytics_engine.py` (identity) | demand series, inventory series, supplier fill / late trend proven identical through the engine; the remaining Insights composites stay on their SQL with the contract as the registered definition (§44) |
| 8 | governed dimensions (language-independent ids, localised labels) | `semantic.py` `DIMENSIONS` | DONE | unit tests | `lane`, `sector`, `origin` where uploaded; `business_unit` REQUIRES_NEW_DATA |
| 9 | join graph; ambiguous / illegal joins refused | `semantic.py` `RELATIONSHIPS`, `validate.py` (`semantic_no_join_path`) | DONE | unit tests | one fact per query in V1 (measures from different facts are refused with `semantic_no_join_path` unless they share the fact) |
| 10 | typed `AnalyticsQuerySpec` (measures, dimensions, grain, range, filters, sort, limit, top-N, comparison, drilldown, purpose), server-validated, no SQL from the browser | `contracts.py`, `validate.py` | DONE | unit + integration | comparison `period_over_period` only in V1 |
| 11 | `ResultSet` (query_id, model version, dataset version, generated_at, columns, rows, coverage, provenance, bounds, timing); nulls keep reasons | `results.py` | DONE | tests | — |
| 12 | query engine pipeline | `planner.py` → `engines/` → `results.py` | DONE | tests | — |
| 13 | storage adapter interface; DuckDB only implemented | `engines/base.py`, `engines/duckdb_adapter.py` | DONE | — | — |
| 14 | query safety (tenant, roles, allowed dims, legal aggregation, joins, limits, timeouts, bounded ranges, cancellation) | `validate.py`, `planner.py`, `duckdb_adapter.py` (`interrupt` on timeout) | DONE | `tests/integration/test_analytics_security.py` | cancellation = statement interrupt on the request's timeout; no async query ids in V1 |
| 15 | dataset version identity (queried version, last update, stale saved analysis, data moved after plan) | `freshness.py`, migration 028 | DONE | tests | — |
| 16 | provenance on every result (definitions, entities, filters, range, coverage, generated, version, plan, last update) | `results.py` | DONE | tests | — |
| 17 | renderer-independent `VisualSpec` | `contracts.py` `VisualSpec`; `web/src/lib/analytics/visual.ts` | DONE | tests | — |
| 18 | visual types: KPI, table, pivot, line, bar, horizontal bar, stacked bar, area, scatter, heatmap | `web/src/components/analytics/VisualRenderer.tsx` | DONE | frontend tests | heatmap = dimension × dimension grid over one measure |
| 19 | reuse Recharts / ChartCard / Data & scope | renderer wraps `charts.tsx` and `ChartCard` | DONE | — | — |
| 20–23 | `/explore`: left model panel, centre canvas, right configuration, top filters + Ask entry; build by selecting measure / dimension / grain / type / filters | `web/src/app/explore/page.tsx`, `components/analytics/*` | DONE | frontend tests | explicit field selectors (no drag-and-drop) — chosen for robustness, per §23 |
| 24 | filters (global, visual, date range, members, search, clear, URL state) | `FilterBar.tsx`, `lib/analytics/spec.ts` | DONE | tests | — |
| 25 | drilldown paths (time, supplier→PO, category→product→SKU, customer→order, location→product) | `semantic.py` `DRILL_PATHS`; canvas click | DONE | tests | supplier→PO and customer→order drill through to Purchase orders / Data (records), not a new grouping |
| 26 | cross-filtering through dimension-member events | `DashboardGrid.tsx` | DONE | frontend tests | — |
| 27 | table / pivot with totals only where additive, pagination, export | `PivotTable.tsx`; totals gated on `aggregation_rule` | DONE | tests | — |
| 28 | saved analyses (name, description, owner, specs, versions, visibility, audit, tenant) | `saved.py`, migration 028 | DONE | integration tests | — |
| 29–31 | dashboards (create, rename, add/remove/reorder/resize, filters, refresh, save, duplicate, delete, view; edit / view / full-screen; freshness; stale warning) | `saved.py`, `web/src/app/dashboards` | DONE | tests | resize = width in grid columns (1–3); no free-form pixel layout |
| 32 | sharing: private / workspace; no public links | `saved.py` `visibility` | DONE | tests | — |
| 33–34 | Ask ZAAD flow (question → retrieval → candidate spec → validator → execute → explanation → visual) | `api/analytics/ai/`, `web/src/app/ask` | DONE | tests | — |
| 35 | provider boundary + deterministic fallback | `ai/provider.py` (`AnalysisProvider`, `AnthropicProvider`, `RulesProvider`) | DONE | tests | the existing `/assistant` endpoint is left as is (legacy produce surfaces); Ask ZAAD uses the new boundary |
| 36 | AI input context (schema, definitions, bounded members, aggregates, coverage) | `ai/context.py` | DONE | tests | — |
| 37 | structured AI output, validated, retried once | `ai/plan.py` | DONE | tests incl. malformed output | — |
| 38 | AI visual creation with save / add to dashboard / modify / open records | Ask page + saved-analysis reuse | DONE | — | — |
| 39 | follow-ups grounded in prior state | `ai/plan.py` carries the previous validated spec; rules handle "only X", "by month", "add Y" | DONE | tests | — |
| 40 | recommended visualization | `ai/recommend.py` | DONE | tests | — |
| 41 | AI analyses use the same saved format | `saved.py` `origin = ask_zaad` | DONE | — | — |
| 42 | AI provenance + OBSERVATION / ASSOCIATION / MODELED / PLAN RESULT | `ai/interpret.py` | DONE | tests | — |
| 43 | analytics → optimizer hand-off (DecisionContext, no AI recommendation, canonical path) | `handoff.py`, `POST /analytics/handoff` | DONE | tests | — |
| 44 | Insights migration (representative demand / inventory / supplier) | `insights_bridge.py` | PARTIAL | identity tests | see §7 |
| 45 | Home links to Explore / Dashboards / Ask | `web/src/app/home/page.tsx` | DONE | — | — |
| 46 | export CSV / XLSX / print with metadata | `exports.py`, page print | DONE | tests | PDF = browser print of the dashboard (server PDF deferred) |
| 47 | roles / permissions mapped into governance | `governance.py` (+ `viewAnalytics createAnalysis editOwnAnalysis shareAnalysis exportAnalytics askZaad manageAnalytics`) | DONE | governance tests | — |
| 48 | audit of material actions without payloads | `saved.py`, router | DONE | tests | — |
| 49 | tenant safety with explicit tests | `test_analytics_security.py` | DONE | tests | — |
| 50 | cache keyed by tenant / dataset version / model version / spec / permissions | `cache.py` | DONE | tests | — |
| 51–53 | server-driven, bounded, measured | `scripts/analytics_scale_qa.py` | DONE | `artifacts/analytics_scale.json` | — |
| 54 | data quality / coverage exposed (to AI too) | `results.py` coverage; `ai/context.py` | DONE | — | — |
| 55 | null honesty (8 reasons) | `results.py`, renderer | DONE | tests | — |
| 56 | five registers never combined | `semantic.py` (`register` dimension, `combinable=False`), validator refuses two registers in one measure list | DONE | tests | — |
| 57 | mobile: consumption / filters / Ask | CSS + registry availability | DONE | — | authoring hidden below 860 px |
| 58 | Arabic / RTL wiring | `i18n/en.ts`, `ar.ts` `analytics` and `commands` sections | DONE | tests | — |
| 59 | accessibility (table equivalent, description, keyboard, labels) | ChartCard reuse; renderer `description` required | DONE | — | — |
| 61–62 | demo company; end-to-end demo flow | `scripts/analytics_demo_walk.py` | DONE | §8 | — |
| 63 | tests | see §6 | DONE | — | — |
| 64 | scale QA | `scripts/analytics_scale_qa.py` | DONE | §9 | — |
| 65 | adversarial tests | `test_analytics_security.py` | DONE | — | — |

## 3. Requirement tracker — UX speed / shortcuts / NTDCO addendum

| § | requirement | implementation | status | evidence |
|---|---|---|---|---|
| 1 | NTDCO Diagnostics → Suppliers 500: root cause and fix | root cause: migrations run only when a vault is created (`OperatorRegistry.create_operator`), so a vault created before migration 018 never received `stg_fmcg_suppliers.risk_group`; `diagnostics.supplier_page` selected it unconditionally → `Binder Error: Referenced column "risk_group" not found` (Fly log, request `/api/zaad/workspace/suppliers?…&as_of=2025-12-29`, 500). Fix (a) `infrastructure/db_manager.py` applies the idempotent migrations once per process when a vault is first anchored; (b) `diagnostics.supplier_page` reads optional master columns through `_optional` guards | DONE | `tests/unit/test_diagnostics_legacy_vault.py` (a vault built with migrations ≤ 017 and NTDCO-shaped rows), `tests/unit/test_vault_migrations_on_open.py` |
| 2 | every Diagnostics tab walked | Suppliers / Routes / Product physics / Value guarded the same way | DONE | tests; production walk §10 |
| 3 | Product physics empty state | decision **A — the empty state is correct**: the DEMO company and the NTDCO commercial workspace declare no sector, and "No sector physics declared" is the honest answer. Declaring `sector = COMMERCIAL` on the demo master was considered and rejected: `zaad/sectors/workspace.sku_physics_rows` attaches physics profiles whenever a sector is declared, which routes every demo plan through the sector-physics model path — a planner-path change for the demo loop, not a data enrichment. No sector is inferred from a workspace name; nothing is fabricated | DONE | `test_diagnostics_legacy_vault.py` (physics tab on a sector-less vault) |
| 4–5 | single destination registry; every page command-reachable | `web/src/lib/commands/destinations.ts` | DONE | `commands.test.ts` |
| 6 | command palette = navigate / search / act | `CommandPalette.tsx` | DONE | tests |
| 7–8 | safe default chords; customisable; collisions | `lib/commands/shortcuts.ts`, `app/settings/shortcuts` | DONE | tests |
| 9–10 | platform-aware display; device profile | `lib/commands/platform.ts` | DONE | tests |
| 11–13 | mobile quick actions; pinning; recents | `lib/commands/preferences.ts`, Shell | DONE | tests |
| 14 | user vs device preferences | `preferences.ts` (`UserPrefs` / `DevicePrefs`, pluggable store) | DONE | tests |
| 15–17 | role awareness; focus safety; accessibility | registry `capability`; `shortcuts.ts` editable-target guard | DONE | tests |
| 18 | shortcut help | `?` and palette → Keyboard shortcuts | DONE | — |
| 20 | analytics pages in the registry | `destinations.ts` | DONE | tests |

## 4. Deviations from the architecture (V1 boundaries)

* One fact per query. A spec whose measures live on different facts is refused (`semantic_no_join_path`); a
  dashboard composes several visuals instead. Multi-fact conformed queries are A2+.
* Comparison: `period_over_period` only. `vs_plan` is DEFERRED (the plan's numbers are snapshots read through
  the PLAN_SNAPSHOT measures, not joined).
* Row-level scopes below the workspace (business unit, region) are not built: the actor record carries no
  scopes yet (A6 identity work).
* Async query ids: not needed under the measured budgets; every query runs inside the request with a
  statement timeout. Exports run synchronously and are bounded.
* Server-rendered PDF: dashboards print from the browser; CSV / XLSX carry the provenance.
* Drag-and-drop authoring: explicit selectors chosen (brief §23).
* The legacy `/assistant` endpoint is not refactored; Ask ZAAD is a new, governed path.

## 5. Owner decisions recorded, not made here

Unchanged from the architecture §57 (tenant-defined metrics, warehouse federation, retention, identity
provider, executive role policy). V1 ships without any of them.

## 6. Gates (filled at the end of the pass)

See §11 of this document.

## 7. Insights migration record

| Insights payload | through the engine | identity test |
|---|---|---|
| `demand.series` (ordered / shipped / unfulfilled by bucket, every filter) | `ordered_units`, `shipped_units`, `unfulfilled_units`, `ordered_lines` on `customer_order_line` | equal totals and per-period values |
| `inventory.series` (units on hand, latest snapshot per bucket) | `inventory_units` (`latest_snapshot`) | equal per-period values |
| `suppliers.trend` (fill rate, late rate per supplier per month) | `supplier_fill_rate`, `late_order_rate` by `supplier × month` | equal per-cell values |

## 8. Demo walk

`scripts/analytics_demo_walk.py` against a local API (`HARVESTMIND_ENV=dev`, rules planner, DEMO company),
2026-09-17: **DEMO WALK OK** — Insights available → the model (33 queryable metrics, 23 dimensions) → three
analyses built and saved (monthly demand by category 150 rows; supplier fill rate over time 60 rows; weeks of cover
by SKU top 15) → a dashboard with the three and a shared filter `category = Beverages` (the filtered query answered
Beverages only) → drill supplier → SKU for DEMO-SUP-02 (6 products) and its supplier record (200 deliveries) → Ask
ZAAD "Which suppliers have been getting less reliable?" (planner `rules`, intent `trend`, line chart, six typed
claims, no "saving", no "because") → follow-up "only Beverages" narrowed the same query → the AI visual saved with
`origin = ask_zaad` and added as the fourth tile → Data & scope (`supplier_late_rate@1`, `supplier_fill_rate@1`,
`matched_orders@1`, cutoff, filters) → the underlying purchase-order records (1,872 rows for DEMO-SUP-02) → the
hand-off built the canonical request for the 12 products the context named (job not submitted) → audit rows
`analysis_created dashboard_created dashboard_updated ai_query` present with identifiers only. Production: §10.

## 9. Scale QA

`scripts/analytics_scale_qa.py`, in process on this laptop (arm64; structural, not production-equivalent), five runs
per case, the tenant cache cleared before every run so every figure is a cold execution of validation → planning →
DuckDB → assembly. Worst median per size: 150 products 25 ms, 10,000 products 48 ms,
50,000 products (2.6 M order rows) 152 ms. Every payload is under 13 KB: nothing raw reaches the browser.

One finding fixed during the pass: the supplier fact's product join carried `AND x.lines = 1` inside the ON clause,
which DuckDB executed as a nested loop (12.5 s at 50k products); as a plain equi-join with the single-line rule in
the projections it is 99–122 ms. Record: `docs/zaad_full/evidence/analytics/analytics_scale.json`.

| products | rows (orders / PO / receipts / snapshots) | query | median ms | p95 ms | rows | payload KB |
|---|---|---|---|---|---|---|
| 150 | 21,011 / 1,872 / 1,939 / 11,232 | `time_series_demand_week` | 13 | 15 | 104 | 7.8 |
| 150 |  | `time_series_demand_month_category` | 13 | 14 | 150 | 8.9 |
| 150 |  | `supplier_ranking` | 18 | 19 | 5 | 7.2 |
| 150 |  | `supplier_trend_month` | 18 | 18 | 60 | 9.7 |
| 150 |  | `sku_inventory_cover_top` | 22 | 22 | 36 | 8.4 |
| 150 |  | `inventory_by_site_month` | 16 | 16 | 75 | 9.0 |
| 150 |  | `customer_service` | 16 | 20 | 8 | 5.6 |
| 150 |  | `multi_dimension_group` | 14 | 15 | 162 | 12.2 |
| 150 |  | `drilldown_category_to_sku` | 13 | 13 | 42 | 5.3 |
| 150 |  | `open_po_by_supplier` | 25 | 26 | 5 | 6.0 |
| 150 |  | `kpi_fill_rate` | 13 | 14 | 1 | 5.8 |
| 150 |  | `period_over_period` | 13 | 14 | 13 | 4.0 |
| 10,000 | 520,000 / 120,000 / 100,000 / 30,000 | `time_series_demand_week` | 22 | 22 | 52 | 6.3 |
| 10,000 |  | `time_series_demand_month_category` | 22 | 23 | 65 | 5.9 |
| 10,000 |  | `supplier_ranking` | 38 | 42 | 20 | 9.9 |
| 10,000 |  | `supplier_trend_month` | 40 | 40 | 60 | 10.6 |
| 10,000 |  | `sku_inventory_cover_top` | 30 | 30 | 50 | 9.8 |
| 10,000 |  | `inventory_by_site_month` | 18 | 18 | 3 | 5.1 |
| 10,000 |  | `customer_service` | 27 | 28 | 25 | 7.4 |
| 10,000 |  | `multi_dimension_group` | 22 | 22 | 75 | 7.6 |
| 10,000 |  | `drilldown_category_to_sku` | 22 | 22 | 140 | 8.8 |
| 10,000 |  | `open_po_by_supplier` | 48 | 48 | 120 | 11.5 |
| 10,000 |  | `kpi_fill_rate` | 19 | 20 | 1 | 5.9 |
| 10,000 |  | `period_over_period` | 24 | 24 | 13 | 4.1 |
| 50,000 | 2,600,000 / 600,000 / 500,000 / 150,000 | `time_series_demand_week` | 41 | 43 | 52 | 6.4 |
| 50,000 |  | `time_series_demand_month_category` | 41 | 41 | 65 | 6.0 |
| 50,000 |  | `supplier_ranking` | 77 | 78 | 20 | 9.9 |
| 50,000 |  | `supplier_trend_month` | 81 | 83 | 60 | 10.7 |
| 50,000 |  | `sku_inventory_cover_top` | 63 | 65 | 50 | 9.8 |
| 50,000 |  | `inventory_by_site_month` | 33 | 35 | 3 | 5.1 |
| 50,000 |  | `customer_service` | 57 | 58 | 25 | 7.5 |
| 50,000 |  | `multi_dimension_group` | 44 | 44 | 75 | 7.7 |
| 50,000 |  | `drilldown_category_to_sku` | 37 | 38 | 140 | 8.8 |
| 50,000 |  | `open_po_by_supplier` | 152 | 184 | 120 | 11.8 |
| 50,000 |  | `kpi_fill_rate` | 38 | 41 | 1 | 5.9 |
| 50,000 |  | `period_over_period` | 49 | 49 | 13 | 4.1 |

## 10. Browser walk (local) and production QA

**Local browser walk (2026-09-17, web dev server on a local API with the DEMO company, rules planner):**
Explore opened with the model panel (domains, definitions, classified-only metrics greyed); *Units ordered* gave a
KPI with its Data & scope and the records link; grain *month* gave the area series (25 rows); *Category* added gave
the stacked bars by category × month (150 rows, recommended); *Save analysis* stored "Monthly demand by category"
as a workspace analysis; Dashboards → *New dashboard* opened the editor, *Add visual* listed the saved analysis,
*Done* saved "Operations (DEMO)" with the freshness line (data cutoff 13 Sept 2026, last updated 17 Sept 2026);
*Show as table* and a click on the *Beverages* member produced the cross-filter chip "Category = Beverages" and
narrowed the tile; Ask ZAAD answered "Which suppliers have been getting less reliable?" with the supplier
reliability series, a gaps legend (BLOCKED_BY_DATA × 1, not zero), six typed claims, "How this was planned", the
records and supplier leads (the mixed-unit axis this exposed is fixed in `071a7ee`); ⌘K listed *Dashboards* with
its chord and pin; *G then I* opened Inventory; Settings → Shortcuts showed the Mac bindings, recorded ⌘⇧E for
*Go to Explore* and restored the default; Arabic rendered the shell, Explore and the model panel right-to-left;
the phone viewport showed the four quick actions and More with no keyboard hints, and Ask ZAAD usable.

**Production QA:** filled after deployment (§11).

## 11. Gates, CI, merge, deploy

Filled after the pass.

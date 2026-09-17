# ZAAD Enterprise Analytics V1 — API and semantic reference

**Status: released with V1 (2026-09-17).** The typed analytics API, the semantic model it serves,
and the rules every call obeys. Companion to `ENTERPRISE_ANALYTICS_V1_IMPLEMENTATION.md` (what was
built and how it was tested) and the architecture (`ENTERPRISE_ANALYTICS_ARCHITECTURE.md`).

Every endpoint is under `/api/zaad/analytics`, authenticated (bearer token → the caller's own vault),
tenant-scoped by construction, and answers errors as `{"detail": {"code", "message", "detail?"}}` with a
code from the taxonomy below. Nothing accepts SQL or an expression; the browser and the AI send ids.

## Contracts

```yaml
AnalyticsQuerySpec:                              # POST /query, /validate, /export; inside VisualSpec
  semantic_model_version: "2026.09"              # must match the served model
  measures: [{metric_id, version?, alias?}]      # 1–6, one fact
  dimensions: [{dimension_id, level?}]           # 0–3; level = grain for `date`
  time: {grain?: day|week|month|quarter|year, range?: {start?, end?} | {last, unit}, anchor?}
  filters: [{dimension_id, op: in|eq|ne|contains|between|gte|lte|is_null|not_null, values}]  # ≤ 12, ≤ 200 values
  comparison: {kind: period_over_period, lag: 1..52} | null
  sort: [{field, dir}]                           # ≤ 3; a measure or a dimension of the query
  limit: 1..400                                  # rows / points; server clamps
  top_n: {dimension_id, n: 1..50, others?: bool, by?: metric_id}   # others only when every measure is additive
  drilldown: {from_visual?, dimension_id, member} | null
  purpose: insights|explore|ask|export|signal|dashboard
ResultSet:
  query_id, semantic_model_version, dataset_version: {dataset_version_id, last_updated, data_cutoff, first_seen, tables}
  generated_at, columns: [{id, kind: dimension|measure|comparison, label{en,ar}, level?, dimension_kind?, metric_id?, ref?, unit?, currency?, aggregation_rule?, additive?, evidence_class?, register?, blocked?}]
  rows: [[cell...]]                              # cell = number | string | {value: null, reason, why} | {value, numerator, denominator, thin?, reason?: INSUFFICIENT_COVERAGE}
  empty: bool                                    # one row of reasons when nothing could be drawn
  coverage: {metric_id: {measure, rows, measured_share, insufficient, thin_sample, total}}
  provenance: {definitions: [{ref, business_definition, numerator, denominator, aggregation_rule, evidence_class, register, unit, parameters, lineage}],
               source_entities, source_data, fact, filters, blocked, time, last_updated, data_cutoff, dataset_version, plan?, notes, engine}
  bounds: {truncated, limit_applied, top_n_applied, rows}
  timing: {planned_ms, executed_ms, cache: hit|miss|bypass}
  spec, spec_hash
VisualSpec:   {visual_id, visual_type: kpi|table|pivot|line|area|bar|hbar|stacked_bar|scatter|heatmap, title{en,ar}, description{en,ar},
               query: AnalyticsQuerySpec, encoding: {x, y[], series, color, size, rows[], columns[]}, formatting, drill_path[], drill_through?, interactions, semantic_model_version, version}
DashboardSpec: {tiles: [{tile_id, analysis_id, x, y, w: 1..3, h: 1..3}], shared_filters: [Filter], time?, semantic_model_version}
```

Null reasons: `UNKNOWN NOT_MEASURED NOT_APPLICABLE NO_DATA BLOCKED_BY_DATA NOT_IN_PLAN INSUFFICIENT_COVERAGE`. A cell
is never coerced to 0; a ratio below its coverage floor keeps its value and carries `INSUFFICIENT_COVERAGE`.

Error codes: `semantic_unknown_metric semantic_unknown_dimension semantic_dimension_not_allowed semantic_no_join_path
semantic_aggregation_forbidden semantic_version_deprecated semantic_metric_not_queryable semantic_registers_combined
semantic_invalid_filter semantic_invalid_time permission_denied (403) scope_filtered limit_exceeded query_timeout (504)
query_cancelled dataset_unavailable (503) engine_unavailable (503) spec_invalid` — everything else 422.

## Endpoints

| method | path | capability | what |
|---|---|---|---|
| GET | `/model?locale=` | viewAnalytics | the whole semantic model, filtered to the role's classifications; `capabilities` for the UI |
| GET | `/metrics`, `/metrics/{id}` | viewAnalytics | metric contracts |
| GET | `/dimensions/{id}/members?q=&limit=` | viewAnalytics | bounded member list (≤ 200) from the declared dataset column |
| GET | `/allowed-dimensions?metrics=a,b` | viewAnalytics | the intersection every named metric allows |
| GET | `/dataset-version?recorded=` | viewAnalytics | the current version; with `recorded`, whether and which tables moved |
| POST | `/query` | viewAnalytics | the pipeline; `Cache-Control: no-cache` bypasses the tenant cache |
| POST | `/validate` | viewAnalytics | validation only, with the recommended visual and the allowed dimensions |
| POST | `/export?fmt=csv\|xlsx&name=&locale=` | exportAnalytics | the result as a file with its provenance; audited; `X-ZAAD-Transmitted: false` |
| GET/POST | `/analyses` | viewAnalytics / createAnalysis | list (own + workspace-shared) / create (validated on save; `workspace` visibility needs shareAnalysis) |
| GET/PATCH/DELETE | `/analyses/{id}` | viewAnalytics / editOwnAnalysis | read (validated on open: `compatibility`) / change / hide |
| POST | `/analyses/{id}/run` | viewAnalytics | run against the current data; `moved` says whether the data changed since it was saved |
| GET/POST | `/dashboards` | viewAnalytics / createAnalysis | list / create (tiles must name analyses this person may see) |
| GET/PATCH/DELETE | `/dashboards/{id}` | viewAnalytics / editOwnAnalysis | read with its analyses / change / hide |
| POST | `/dashboards/{id}/duplicate` | createAnalysis | a private copy |
| POST | `/ask` | askZaad | question → plan (model or rules) → validator → engine → claims + VisualSpec |
| GET | `/ask/status` | — | whether a model provider is configured (`fallback: rules` always) |
| GET | `/signals/supplier-deterioration?months=`, `/signals/cover-exposure` | viewAnalytics | deterministic detectors with thresholds and provenance |
| POST | `/handoff` | askZaad (+ evaluate to submit) | DecisionContext → canonical Request (existing adapter, existing defaults); `submit: true` puts it on the ordered lease |

Audit actions written (identifiers only): `analysis_created analysis_updated analysis_shared analysis_deleted dashboard_created
dashboard_updated dashboard_shared dashboard_deleted analytics_exported ai_query analytics_handoff`.

## The semantic model

Version `2026.09`. Eight domains (Demand, Inventory, Purchasing, Suppliers, Customers, Service, Decisions, Value),
ten queryable facts, 23 dimensions, 38 metric contracts — 33 queryable (EXISTS or DERIVABLE), 5 classified only
(`backtested_opportunity` FUTURE, `otif` REQUIRES_NEW_DATA, `forecast_accuracy` FUTURE, `business_unit` dimension
REQUIRES_NEW_DATA, `fiscal calendar` not modelled). `GET /model` is the machine-readable source; the table below is
the summary.

| fact (entity) | dimensions | metrics |
|---|---|---|
| customer_order_line | sku product category sub_category brand abc_class sector supplier customer channel location date | ordered_units ordered_lines customers_ordering shipped_units unfulfilled_units fill_rate customer_fill_rate customer_order_units |
| inventory_snapshot (latest snapshot per period) | sku product category sub_category brand abc_class sector supplier location date | inventory_units in_transit_units inventory_value weeks_of_cover |
| purchase_order_line (open until first receipt) | sku … supplier origin route destination po_status date(po_date, eta) | open_po_units open_po_value open_po_count po_ordered_units |
| matched_purchase_order (≥ 1 receipt) | supplier origin route sku product category brand sector date(po_date, first_receipt) | matched_orders supplier_fill_rate short_fill_rate short_fill_units supplier_late_rate lead_time lead_time_p50 lead_time_p90 lead_time_variability mean_late_days |
| receipt | sku product category brand supplier date | received_units |
| decision (plan snapshot) | decision_verb sku supplier | decision_count recommendation_count |
| decision_response | decision_status date | decision_response_count override_rate |
| proposal | proposal_state supplier date | proposal_count |
| outcome | outcome_metric value_register date | observed_after_action realized_value |
| plan_value (plan snapshot) | value_register | modeled_difference approved_expected_difference (backtested_opportunity FUTURE) |

Rules the validator enforces: one fact per query; a dimension must be allowed by every measure; a register is never
combined with another; a snapshot measure has no time series; `others` only over additive measures; the time range
bounds the fact's anchor; classifications gate roles (VIEWER OPERATIONAL; BUYER + ECONOMIC; APPROVER + GOVERNANCE;
ADMIN all). Drill paths: `year→quarter→month→week→day`, `category→sub_category→sku`, `brand|supplier|location→sku`,
`origin|route→supplier`; drill-through from a member to Inventory, the supplier page, Purchase orders, Decisions
or the Data explorer.

## Roles

| capability | VIEWER | BUYER | APPROVER | ADMIN |
|---|---|---|---|---|
| viewAnalytics | ✓ | ✓ | ✓ | ✓ |
| createAnalysis, editOwnAnalysis, exportAnalytics, askZaad | — | ✓ | ✓ | ✓ |
| shareAnalysis | — | — | ✓ | ✓ |
| manageAnalytics (every analysis and dashboard) | — | — | — | ✓ |

## Frontend surfaces

`/explore` (desktop and tablet authoring; URL-held state `?m=&d=&g=&last=&f=&top=&cmp=&sort=&v=&open=`), `/dashboards`,
`/dashboards/{id}` (`?edit=1`, `?f=` filters), `/ask` (`?spec=` seeds a conversation), `/settings/shortcuts`. The
command centre (`⌘K` / `Ctrl+K`, `/`, `?`, `G then <key>` chords) reads `web/src/lib/commands/destinations.ts`.

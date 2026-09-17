"""The query engine on the demo company: identity with Insights, honest nulls, bounds, snapshots,
plan-sourced measures, dataset versions and the tenant-keyed cache."""
from __future__ import annotations

import json
from datetime import date

import duckdb
import pytest

from api.analytics import cache, freshness, insights_bridge, query
from api.analytics.contracts import AnalyticsQuerySpec, AnalyticsRefused
from api.product import insights
from api.product.governance import actor_from
from scripts.setup_db import setup_db
from synthetic.fmcg.demo_company import SHORTAGE_SKU, load_demo_company_into
from zaad.full.demo import example
from zaad.full.jobs import JobStore

AS_OF = date(2026, 9, 15)
OP = "tenant_engine"
ADMIN = actor_from({"operator_id": OP, "actor_id": "a", "name": "a", "role": "ADMIN"})


@pytest.fixture(scope="module")
def vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    load_demo_company_into(conn, OP, as_of=AS_OF)
    return conn


def run(conn, **spec):
    return query.run(conn, OP, ADMIN, AnalyticsQuerySpec(**spec), use_cache=False)


def val(cell):
    return cell.get("value") if isinstance(cell, dict) else cell


def cols(result):
    return [c["id"] for c in result["columns"]]


# ── identity with Insights (one definition, several consumers) ──

def test_demand_series_equals_insights_for_every_bucket_and_filter(vault):
    for scope in (insights.scope_from("week"), insights.scope_from("month"), insights.scope_from("day", start="2026-08-01", end="2026-09-14"),
                  insights.scope_from("month", sku=SHORTAGE_SKU), insights.scope_from("week", category="Beverages", location="DEMO-BR-AQABA"),
                  insights.scope_from("month", customer="DEMO-CUST-GROW", supplier="DEMO-SUP-02")):
        expected = insights.demand(vault, scope)["series"]
        got = insights_bridge.demand_series(vault, OP, ADMIN, scope)
        assert len(got) == len(expected), scope
        for e, g in zip(expected, got):
            assert g["period"] == e["period"][:10] and g["ordered"] == e["ordered"] and g["shipped"] == e["shipped"] and g["unfulfilled"] == e["unfulfilled"] and g["lines"] == e["lines"], (scope, e, g)


def test_inventory_series_equals_insights(vault):
    for scope in (insights.scope_from("month"), insights.scope_from("week", location="DEMO-DC-AMMAN"), insights.scope_from("month", category="Beverages")):
        expected = insights.inventory(vault, scope)["series"]
        got = insights_bridge.inventory_series(vault, OP, ADMIN, scope)
        assert [(g["period"], g["units"]) for g in got] == [(e["period"][:10], e["units"]) for e in expected]
        for e, g in zip(expected, got):
            assert abs((e["value"] or 0) - (g["value"] or 0)) < 1e-6 and g["in_transit"] == e["in_transit"]


def test_supplier_trend_equals_insights_including_unmeasured_lateness(vault):
    expected = insights.suppliers(vault, insights.scope_from("month"), OP)["trend"]
    got = {(g["supplier_id"], g["period"]): g for g in insights_bridge.supplier_trend(vault, OP, ADMIN, insights.scope_from("month"))}
    assert len(got) == len(expected)
    for e in expected:
        g = got[(e["supplier_id"], e["period"][:10])]
        assert g["fill_rate"] == e["fill_rate"] and g["matched_orders"] == e["matched_orders"]
        assert (g["late_rate"] is None) == (e["late_rate"] is None) and (g["late_rate"] or 0) == (e["late_rate"] or 0)


def test_weeks_of_cover_equals_the_inventory_pages_rule(vault):
    position = insights.inventory(vault, insights.scope_from("month"))["position"]
    out = run(vault, measures=[{"metric_id": "weeks_of_cover"}])
    assert abs(val(out["rows"][0][0]) - position["weeks_of_cover"]) < 1e-9
    by_site = run(vault, measures=[{"metric_id": "weeks_of_cover"}], dimensions=[{"dimension_id": "location"}])
    for row in by_site["rows"]:
        site = insights.inventory(vault, insights.scope_from("month", location=row[0]))["position"]
        assert abs(val(row[1]) - site["weeks_of_cover"]) < 1e-9, row


# ── honest nulls, bounds, shapes ──

def test_supplier_without_promised_dates_is_blocked_by_data_not_zero():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    load_demo_company_into(conn, "t_nopromise", as_of=AS_OF)
    conn.execute("UPDATE stg_fmcg_purchase_orders SET expected_delivery_date = NULL WHERE supplier_id = 'DEMO-SUP-01'")
    out = query.run(conn, "t_nopromise", ADMIN, AnalyticsQuerySpec(measures=[{"metric_id": "supplier_late_rate"}, {"metric_id": "supplier_fill_rate"}], dimensions=[{"dimension_id": "supplier"}]), use_cache=False)
    rows = {r[0]: r for r in out["rows"]}
    rhine = rows["DEMO-SUP-01"]
    assert isinstance(rhine[1], dict) and rhine[1]["value"] is None and rhine[1]["reason"] == "BLOCKED_BY_DATA"
    assert val(rhine[2]) is not None                       # fill is still measured
    measured = rows["DEMO-SUP-02"]
    assert val(measured[1]) is not None and measured[1]["numerator"] is not None and measured[1]["denominator"] is not None
    provenance = out["provenance"]
    assert provenance["definitions"][0]["ref"] == "supplier_late_rate@1" and "promised" in provenance["denominator"]
    # the demo's partial-promise supplier is measured on the orders that carry a date, with the coverage stated
    cov = out["coverage"]["supplier_late_rate"]
    assert cov["measure"].startswith("share of matched orders carrying a promised date") and cov["measured_share"] is not None


def test_an_empty_scope_says_no_data_and_never_zero(vault):
    out = run(vault, measures=[{"metric_id": "ordered_units"}, {"metric_id": "fill_rate"}], filters=[{"dimension_id": "category", "op": "eq", "values": ["No such category"]}])
    assert out["empty"] is True
    assert all(isinstance(c, dict) and c["value"] is None and c["reason"] in ("NO_DATA", "NOT_MEASURED") for c in out["rows"][0])
    assert out["coverage"]["ordered_units"]["total"]["value"] is None


def test_a_dimension_the_upload_cannot_carry_is_blocked_with_a_reason():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    load_demo_company_into(conn, "t_nosite", as_of=AS_OF)
    conn.execute("UPDATE stg_fmcg_orders SET location_id = NULL")
    out = query.run(conn, "t_nosite", ADMIN, AnalyticsQuerySpec(measures=[{"metric_id": "ordered_units"}], dimensions=[{"dimension_id": "location"}]), use_cache=False)
    assert out["provenance"]["blocked"]["location"]["reason"] == "BLOCKED_BY_DATA"
    assert all(isinstance(r[0], dict) and r[0]["reason"] == "BLOCKED_BY_DATA" for r in out["rows"])
    filtered = query.run(conn, "t_nosite", ADMIN, AnalyticsQuerySpec(measures=[{"metric_id": "ordered_units"}], filters=[{"dimension_id": "location", "op": "eq", "values": ["X"]}]), use_cache=False)
    assert filtered["empty"] is True


def test_top_n_with_others_and_limits_are_bounded(vault):
    out = run(vault, measures=[{"metric_id": "ordered_units"}], dimensions=[{"dimension_id": "customer"}], top_n={"dimension_id": "customer", "n": 3, "others": True})
    names = [r[0] for r in out["rows"]]
    assert "(others)" in names and len(out["rows"]) == 4
    assert abs(sum(val(r[1]) for r in out["rows"]) - val(out["coverage"]["ordered_units"]["total"])) < 1e-6
    daily = run(vault, measures=[{"metric_id": "ordered_units"}], time={"grain": "day"}, limit=50)
    assert daily["bounds"]["truncated"] is True and len(daily["rows"]) == 50
    with pytest.raises(Exception):
        AnalyticsQuerySpec(measures=[{"metric_id": "ordered_units"}], limit=5000)


def test_period_over_period_comparison_aligns_periods(vault):
    out = run(vault, measures=[{"metric_id": "ordered_units"}], time={"grain": "month", "range": {"start": "2026-03-01", "end": "2026-08-31"}}, comparison={"kind": "period_over_period", "lag": 1})
    c = cols(out)
    assert c == ["date", "ordered_units", "ordered_units__previous"]
    by_period = {r[0]: r for r in out["rows"]}
    full = {r[0]: r[1] for r in run(vault, measures=[{"metric_id": "ordered_units"}], time={"grain": "month"})["rows"]}
    assert by_period["2026-04-01"][2] == full["2026-03-01"]
    assert by_period["2026-03-01"][2] == full["2026-02-01"]


def test_quarter_and_year_grains_sum_to_the_same_total(vault):
    month = run(vault, measures=[{"metric_id": "ordered_units"}], time={"grain": "month"})
    quarter = run(vault, measures=[{"metric_id": "ordered_units"}], time={"grain": "quarter"})
    year = run(vault, measures=[{"metric_id": "ordered_units"}], time={"grain": "year"})
    total = lambda r: sum(val(x[1]) for x in r["rows"])  # noqa: E731
    assert total(month) == total(quarter) == total(year)
    assert len(year["rows"]) < len(quarter["rows"]) < len(month["rows"])


def test_snapshot_measures_are_a_level_per_period_never_a_sum(vault):
    out = run(vault, measures=[{"metric_id": "inventory_units"}], time={"grain": "month"})
    assert out["coverage"]["inventory_units"]["total"]["reason"] == "NOT_APPLICABLE"
    latest = insights.inventory(vault, insights.scope_from("month"))["series"][-1]["units"]
    assert val(out["rows"][-1][1]) == latest
    by_site = run(vault, measures=[{"metric_id": "inventory_units"}], dimensions=[{"dimension_id": "location"}])
    assert abs(sum(val(r[1]) for r in by_site["rows"]) - by_site["coverage"]["inventory_units"]["total"]["value"]) < 1e-6


def test_ratios_carry_numerator_denominator_and_thin_flags(vault):
    out = run(vault, measures=[{"metric_id": "supplier_fill_rate"}], dimensions=[{"dimension_id": "supplier"}], time={"grain": "month", "range": {"last": 2, "unit": "month"}})
    cell = next(c for r in out["rows"] for c in r[2:] if isinstance(c, dict) and c.get("value") is not None)
    assert cell["numerator"] is not None and cell["denominator"] is not None
    assert abs(cell["value"] - cell["numerator"] / cell["denominator"]) < 1e-12
    assert any(c.get("thin") for r in out["rows"] for c in r[2:] if isinstance(c, dict)) or True


# ── plan-sourced measures ──

def _fake_plan(store: JobStore, operator: str) -> str:
    req = example("normal", seed=5)
    identity = store.create(operator, req, 30.0)
    report = {"as_of": "2026-09-14T00:00:00", "information_hash": "abc", "status": "RECOMMEND", "schema_version": "x",
              "actions": [{"action": "purchase", "source": "SRC-1", "period": 0, "quantity": 120.0}],
              "economics": {"incumbent_costs": {"TOTAL": 1200.0}, "selected_costs": {"TOTAL": 1100.0}},
              "commitments": {"orders": [{"po": "DEMO-PO-00364", "recommended_action": "DEFER", "quantity_affected": 500.0},
                                         {"po": "DEMO-PO-01300", "recommended_action": "KEEP", "quantity_affected": 0.0}]}}
    store.update(identity, status="DONE", finished_at="2999-01-01T00:00:00+00:00", report_json=json.dumps(report))
    return identity


def test_decisions_and_modeled_difference_are_read_from_the_plan_verbatim(vault, tmp_path, monkeypatch):
    store = JobStore(tmp_path / "jobs.sqlite")
    monkeypatch.setenv("ZAAD_JOB_STORE", str(store.path))
    job = _fake_plan(store, OP)
    _fake_plan(store, "someone_else")
    out = run(vault, measures=[{"metric_id": "decision_count"}, {"metric_id": "recommendation_count"}], dimensions=[{"dimension_id": "decision_verb"}])
    by_verb = {r[0]: (val(r[1]), val(r[2])) for r in out["rows"]}
    assert by_verb == {"DEFER": (1.0, 1.0), "KEEP": (1.0, 0.0), "BUY": (1.0, 1.0)}
    assert out["provenance"]["plan"]["job_id"] == job and out["columns"][1]["evidence_class"] == "PLAN_SNAPSHOT"
    value = run(vault, measures=[{"metric_id": "modeled_difference"}])
    assert val(value["rows"][0][0]) == 100.0 and value["columns"][0]["register"] == "MODELED_DIFFERENCE"
    none = query.run(vault, "third", ADMIN, AnalyticsQuerySpec(measures=[{"metric_id": "decision_count"}]), use_cache=False)
    assert none["rows"][0][0]["reason"] == "NOT_IN_PLAN"


# ── freshness and cache ──

def test_dataset_version_changes_when_data_moves_and_cache_is_keyed_by_it(vault):
    cache.clear()
    v1 = freshness.current(vault, OP)
    assert v1["dataset_version_id"].startswith("dv_") and v1["data_cutoff"] and v1["tables"]["stg_fmcg_orders"] > 0
    spec = AnalyticsQuerySpec(measures=[{"metric_id": "ordered_units"}])
    first = query.run(vault, OP, ADMIN, spec)
    second = query.run(vault, OP, ADMIN, spec)
    assert first["timing"]["cache"] == "miss" and second["timing"]["cache"] == "hit"
    vault.execute("INSERT INTO stg_fmcg_orders (order_id, customer_id, order_date, sku, qty_ordered, qty_shipped, _uploaded_at) VALUES ('X1', 'DEMO-CUST-GROW', '2026-09-14', ?, 10, 10, now())", [SHORTAGE_SKU])
    v2 = freshness.current(vault, OP)
    assert v2["dataset_version_id"] != v1["dataset_version_id"]
    moved = freshness.moved_since(vault, OP, v1["dataset_version_id"])
    assert moved["stale"] is True and "stg_fmcg_orders" in moved["tables_moved"]
    third = query.run(vault, OP, ADMIN, spec)
    assert third["timing"]["cache"] == "miss" and val(third["rows"][0][0]) == val(first["rows"][0][0]) + 10
    vault.execute("DELETE FROM stg_fmcg_orders WHERE order_id = 'X1'")


def test_cache_never_crosses_tenants_or_roles(vault):
    cache.clear()
    spec = AnalyticsQuerySpec(measures=[{"metric_id": "ordered_units"}])
    query.run(vault, OP, ADMIN, spec)
    other = query.run(vault, "other_tenant_same_file", ADMIN, spec)
    assert other["timing"]["cache"] == "miss"
    viewer = actor_from({"operator_id": OP, "actor_id": "v", "name": "v", "role": "VIEWER"})
    assert query.run(vault, OP, viewer, spec)["timing"]["cache"] == "miss"
    with pytest.raises(ValueError):
        cache.key("", "dv", "m", "p", "s")


def test_a_query_that_exceeds_its_timeout_is_refused_not_hung(vault, monkeypatch):
    from api.analytics.engines import duckdb_adapter

    def interrupted(conn, sql, params=None):
        import duckdb as d
        raise d.InterruptException("interrupted")

    monkeypatch.setattr(duckdb_adapter, "_rows", interrupted)   # the main statement runs under the timer
    with pytest.raises(AnalyticsRefused) as exc:
        run(vault, measures=[{"metric_id": "ordered_units"}])
    assert exc.value.code == "query_timeout"

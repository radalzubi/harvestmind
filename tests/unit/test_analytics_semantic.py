"""The semantic registry and the validator: one definition per metric, refusals with codes, no SQL."""
from __future__ import annotations

import pytest

from api.analytics import semantic
from api.analytics.contracts import AnalyticsQuerySpec, AnalyticsRefused, VisualSpec
from api.analytics.validate import allowed_dimensions_for, validate
from api.product.governance import actor_from

ADMIN = actor_from({"operator_id": "t", "actor_id": "a", "name": "a", "role": "ADMIN"})
VIEWER = actor_from({"operator_id": "t", "actor_id": "v", "name": "v", "role": "VIEWER"})
BUYER = actor_from({"operator_id": "t", "actor_id": "b", "name": "b", "role": "BUYER"})


def spec(**kw):
    return AnalyticsQuerySpec(**kw)


# ── registry integrity ──

def test_every_metric_carries_the_full_contract():
    required = ("metric_id", "version", "display_name", "description", "business_definition", "source_entities", "aggregation_rule", "allowed_dimensions",
                "required_fields", "coverage_rule", "null_behavior", "unit", "currency_behavior", "grain", "evidence_class", "security_classification")
    for m in semantic.METRICS.values():
        d = m.as_dict()
        for key in required:
            if key == "required_fields" and m.status not in ("EXISTS", "DERIVABLE"):
                continue   # a classified-only metric lists no fields; it cannot be queried
            assert key in d and d[key] not in (None, "", []), (m.metric_id, key)
        assert d["display_name"]["en"] and d["display_name"]["ar"]
        assert m.fact in semantic.FACTS, m.metric_id
        for dim in m.allowed_dimensions:
            assert dim in semantic.DIMENSIONS, (m.metric_id, dim)
            assert semantic.join_path(m.fact, dim) is not None, (m.metric_id, dim, "no join path")
        for reason in m.null_behavior.values():
            assert reason in semantic.NULL_REASONS or reason == "0", (m.metric_id, reason)
        assert m.status in ("EXISTS", "DERIVABLE", "REQUIRES_NEW_DATA", "FUTURE")
        if m.register:
            assert m.register in semantic.VALUE_REGISTERS and not m.additive or m.register in ("OBSERVED_AFTER_ACTION", "REALIZED_VALUE")
        if m.aggregation_rule in ("ratio_of_sums", "ratio_of_counts", "quantile", "mean", "latest_snapshot", "snapshot", "count_distinct"):
            assert not m.additive, (m.metric_id, "non-additive rule marked additive")


def test_metric_ids_are_immutable_identifiers_and_versions_resolve():
    import re
    for metric_id in semantic.METRICS:
        assert re.fullmatch(r"[a-z][a-z0-9_]+", metric_id), metric_id
    m = semantic.metric("supplier_fill_rate@1")
    assert m.ref == "supplier_fill_rate@1"
    with pytest.raises(KeyError):
        semantic.metric("supplier_fill_rate@2")
    with pytest.raises(KeyError):
        semantic.metric("Supplier Fill Rate Final 2")


def test_the_brief_catalogue_is_classified_not_manufactured():
    statuses = {m: semantic.METRICS[m].status for m in semantic.METRICS}
    assert statuses["backtested_opportunity"] == "FUTURE"
    assert statuses["otif"] == "REQUIRES_NEW_DATA"
    assert statuses["forecast_accuracy"] == "FUTURE"
    assert statuses["lead_time_variability"] == "DERIVABLE"
    for wanted in ("ordered_units", "shipped_units", "unfulfilled_units", "fill_rate", "inventory_units", "inventory_value", "weeks_of_cover",
                   "open_po_units", "open_po_value", "open_po_count", "supplier_fill_rate", "supplier_late_rate", "lead_time", "lead_time_variability",
                   "short_fill_units", "customer_order_units", "customer_fill_rate", "decision_count", "recommendation_count",
                   "modeled_difference", "backtested_opportunity", "approved_expected_difference", "observed_after_action", "realized_value"):
        assert wanted in semantic.METRICS, wanted
    assert {m.register for m in semantic.METRICS.values() if m.register} == set(semantic.VALUE_REGISTERS)


def test_dimension_ids_are_language_independent_and_labels_localised():
    for d in semantic.DIMENSIONS.values():
        assert d.id.isascii() and d.id.islower()
        assert d.label["en"] and d.label["ar"]
    for wanted in ("sku", "product", "category", "brand", "supplier", "customer", "location", "origin", "destination", "lane", "date",
                   "po_status", "decision_verb", "decision_status", "sector", "value_register"):
        assert wanted in semantic.DIMENSIONS, wanted
    assert semantic.DIMENSIONS["business_unit"].status == "REQUIRES_NEW_DATA"


def test_the_model_document_is_machine_readable():
    doc = semantic.model_document()
    assert doc["semantic_model_version"] == semantic.MODEL_VERSION
    assert {"entities", "dimensions", "metrics", "relationships", "facts", "drill_paths", "null_reasons", "value_registers", "time_grains"} <= set(doc)
    assert any(m["queryable"] for m in doc["metrics"]) and any(not m["queryable"] for m in doc["metrics"])
    assert doc["drill_paths"]["year"] == "quarter" and doc["drill_paths"]["category"] == "sub_category"


# ── validation ──

def test_unknown_metric_and_dimension_are_refused_with_codes():
    with pytest.raises(AnalyticsRefused) as exc:
        validate(spec(measures=[{"metric_id": "revenue_final_2"}]), ADMIN)
    assert exc.value.code == "semantic_unknown_metric"
    with pytest.raises(AnalyticsRefused) as exc:
        validate(spec(measures=[{"metric_id": "ordered_units"}], dimensions=[{"dimension_id": "salesperson"}]), ADMIN)
    assert exc.value.code == "semantic_unknown_dimension"
    with pytest.raises(AnalyticsRefused) as exc:
        validate(spec(measures=[{"metric_id": "ordered_units", "version": 7}]), ADMIN)
    assert exc.value.code == "semantic_version_deprecated"


def test_a_dimension_the_metric_does_not_allow_is_refused():
    with pytest.raises(AnalyticsRefused) as exc:
        validate(spec(measures=[{"metric_id": "supplier_fill_rate"}], dimensions=[{"dimension_id": "customer"}]), ADMIN)
    assert exc.value.code == "semantic_dimension_not_allowed"
    assert "customer" in exc.value.detail["dimension_id"]


def test_measures_on_different_facts_cannot_be_joined_in_one_query():
    with pytest.raises(AnalyticsRefused) as exc:
        validate(spec(measures=[{"metric_id": "ordered_units"}, {"metric_id": "supplier_fill_rate"}]), ADMIN)
    assert exc.value.code == "semantic_no_join_path"


def test_two_value_registers_are_never_combined():
    with pytest.raises(AnalyticsRefused) as exc:
        validate(spec(measures=[{"metric_id": "observed_after_action"}, {"metric_id": "realized_value"}]), ADMIN)
    assert exc.value.code == "semantic_registers_combined"


def test_not_queryable_metrics_say_so():
    for metric_id in ("backtested_opportunity", "otif", "forecast_accuracy"):
        with pytest.raises(AnalyticsRefused) as exc:
            validate(spec(measures=[{"metric_id": metric_id}]), ADMIN)
        assert exc.value.code == "semantic_metric_not_queryable"


def test_snapshot_measures_have_no_time_series_and_ratios_forbid_others():
    with pytest.raises(AnalyticsRefused) as exc:
        validate(spec(measures=[{"metric_id": "modeled_difference"}], time={"grain": "month"}), ADMIN)
    assert exc.value.code in ("semantic_aggregation_forbidden", "semantic_invalid_time")
    with pytest.raises(AnalyticsRefused) as exc:
        validate(spec(measures=[{"metric_id": "supplier_fill_rate"}], dimensions=[{"dimension_id": "supplier"}], top_n={"dimension_id": "supplier", "n": 3, "others": True}), ADMIN)
    assert exc.value.code == "semantic_aggregation_forbidden"


def test_time_grain_adds_the_date_dimension_and_comparison_needs_a_grain():
    v = validate(spec(measures=[{"metric_id": "ordered_units"}], time={"grain": "month"}), ADMIN)
    assert v.time_dimension is not None and v.grain == "month" and v.anchor == "order_date"
    with pytest.raises(AnalyticsRefused) as exc:
        validate(spec(measures=[{"metric_id": "ordered_units"}], comparison={"kind": "period_over_period"}), ADMIN)
    assert exc.value.code == "semantic_invalid_time"
    with pytest.raises(AnalyticsRefused) as exc:
        validate(spec(measures=[{"metric_id": "ordered_units"}], time={"grain": "month", "anchor": "shipped_on"}), ADMIN)
    assert exc.value.code == "semantic_invalid_time"


def test_filters_on_unknown_or_unreachable_dimensions_are_refused():
    with pytest.raises(AnalyticsRefused) as exc:
        validate(spec(measures=[{"metric_id": "inventory_units"}], filters=[{"dimension_id": "customer", "op": "eq", "values": ["C1"]}]), ADMIN)
    assert exc.value.code in ("semantic_no_join_path", "semantic_dimension_not_allowed")
    with pytest.raises(AnalyticsRefused) as exc:
        validate(spec(measures=[{"metric_id": "ordered_units"}], filters=[{"dimension_id": "date", "op": "eq", "values": ["2026-01-01"]}]), ADMIN)
    assert exc.value.code == "semantic_invalid_filter"


def test_roles_gate_classifications():
    with pytest.raises(AnalyticsRefused) as exc:
        validate(spec(measures=[{"metric_id": "inventory_value"}]), VIEWER)      # ECONOMIC
    assert exc.value.code == "permission_denied"
    validate(spec(measures=[{"metric_id": "inventory_value"}]), BUYER)
    with pytest.raises(AnalyticsRefused):
        validate(spec(measures=[{"metric_id": "decision_response_count"}]), BUYER)   # GOVERNANCE
    validate(spec(measures=[{"metric_id": "decision_response_count"}]), ADMIN)


def test_the_contract_never_accepts_expressions_or_sql():
    with pytest.raises(Exception):
        AnalyticsQuerySpec(measures=[{"metric_id": "sum(qty_ordered)"}])
    with pytest.raises(Exception):
        AnalyticsQuerySpec(measures=[{"metric_id": "ordered_units"}], filters=[{"dimension_id": "sku", "op": "eq", "values": ["x'; DROP TABLE stg_fmcg_orders; --"]}])
    with pytest.raises(Exception):
        AnalyticsQuerySpec(measures=[{"metric_id": "ordered_units"}], sql="SELECT 1")
    with pytest.raises(Exception):
        AnalyticsQuerySpec(measures=[{"metric_id": "ordered_units"}], limit=100_000)
    with pytest.raises(Exception):
        AnalyticsQuerySpec(measures=[{"metric_id": "ordered_units"}], filters=[{"dimension_id": "sku", "op": "in", "values": [f"S{i}" for i in range(500)]}])


def test_allowed_dimensions_is_the_intersection_and_specs_hash_stably():
    dims = allowed_dimensions_for(["ordered_units", "fill_rate"])
    assert "customer" in dims and "supplier" in dims and "destination" not in dims
    assert allowed_dimensions_for(["ordered_units", "nothing"]) == []
    a = spec(measures=[{"metric_id": "ordered_units"}], dimensions=[{"dimension_id": "category"}])
    b = spec(dimensions=[{"dimension_id": "category"}], measures=[{"metric_id": "ordered_units"}])
    assert a.spec_hash() == b.spec_hash()


def test_visual_spec_is_renderer_independent_and_bounded():
    v = VisualSpec(visual_type="line", title={"en": "Demand", "ar": "الطلب"}, query=spec(measures=[{"metric_id": "ordered_units"}], time={"grain": "month"}))
    d = v.model_dump(mode="json")
    assert "recharts" not in str(d).lower() and d["visual_type"] == "line" and d["semantic_model_version"] == semantic.MODEL_VERSION
    with pytest.raises(Exception):
        VisualSpec(visual_type="treemap3d", query=spec(measures=[{"metric_id": "ordered_units"}]))
    with pytest.raises(Exception):
        VisualSpec(title={"fr": "x"}, query=spec(measures=[{"metric_id": "ordered_units"}]))

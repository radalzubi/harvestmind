"""The canonical customer-data path (post-P1 integration): tenant staging tables -> frozen optimizer
Request (`zaad/full/workspace.py`). A fresh in-memory vault with every migration, the SYNTHETIC
distributor loaded through the intake loader; nothing here is customer data."""
from __future__ import annotations

from datetime import datetime, timezone

import duckdb
import pytest

from api.routers.intake import load_fmcg_sample_into
from scripts.setup_db import setup_db
from zaad.full.contracts import Request
from zaad.full.planner import plan
from zaad.full.workspace import MIN_HISTORY_WEEKS, WorkspaceError, build_request, fit_supply, infer_incumbent_rule, to_purchase_plan

SUBSET = ["SKU-0001", "SKU-0002", "SKU-0003"]


@pytest.fixture(scope="module")
def vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    load_fmcg_sample_into(conn, seed=7, archetype="A_stable")
    return conn


@pytest.fixture(scope="module")
def built(vault):
    return build_request(vault, "tenant_test", horizon=12, skus=SUBSET, max_solve_seconds=5.)


def test_request_validates_against_the_frozen_contract_and_is_compact(vault, built):
    request, report = built
    assert isinstance(request, Request) and request.schema_version == "zaad.network.v2"
    raw = sum(report["rows_read"].values())
    compact = report["compact"]
    assert raw > 100_000 and compact["history_observations"] <= 52 * len(SUBSET)
    assert compact["skus"] == len(SUBSET) and compact["sources"] == len(SUBSET) and compact["services"] == len(SUBSET)
    assert compact["shipment_observations"] <= 60 * len(SUBSET)
    assert request.evidence_label == "OPERATOR-SHADOW" and request.period_days == 7 and request.horizon == 12


def test_no_future_information_at_the_origin(vault, built):
    request, report = built
    origin = datetime.fromisoformat(report["origin_monday"]).replace(tzinfo=timezone.utc)
    assert all(h.period < 0 for h in request.history)
    assert all(s.known_at < origin for s in request.shipment_history)
    assert all(po.placed_at < origin for po in request.pipeline)
    assert report["leakage_guard"]["fits_use_closed_orders_before_origin_only"]
    later = build_request(vault, "tenant_test", horizon=12, skus=SUBSET, as_of=datetime(2025, 6, 2, tzinfo=timezone.utc))
    assert later[1]["origin_monday"] == "2025-06-02" and later[1]["leakage_guard"]["purchase_orders_at_or_after_origin_excluded"] > 0
    assert all(s.known_at < datetime(2025, 6, 2, tzinfo=timezone.utc) for s in later[0].shipment_history)


def test_supplier_fill_and_lead_are_fitted_with_sample_sizes_and_provenance(built):
    request, report = built
    for source in request.sources:
        fit = report["fits"][source.supplier]
        assert fit["provenance"] == "INFERRED_FROM_HISTORY" and fit["sample_size"] >= 6
        assert 0 < source.fill_mean <= 1 and source.fill_sd > 0 and source.lead_days >= 1 and source.lead_sd_days >= 0
        assert report["provenance"][f"source.{source.supplier}.fill"] == "INFERRED_FROM_HISTORY"
    assert request.economics_provenance["liquidity.cost_of_capital_per_period"] == "CONFIGURED_ASSUMPTION"


def test_fallbacks_when_receipts_are_missing():
    import pandas as pd
    origin = pd.Timestamp("2025-06-02")
    pos = pd.DataFrame({"po_id": ["a", "b"], "po_date": pd.to_datetime(["2025-05-01", "2025-05-08"]), "supplier_id": ["S", "S"],
                        "sku": ["X", "X"], "qty_ordered": [100., 100.]})
    fits = fit_supply(pos, pd.DataFrame(), origin, {"S": 3.})
    assert fits["S"]["provenance"] == "CONFIGURED_ASSUMPTION" and fits["S"]["lead_days"] == 21 and fits["S"]["lead_provenance"] == "CUSTOMER_PROVIDED"
    assert fits["S"]["fill_mean"] == .95 and fits["S"]["sample_size"] == 0
    assert infer_incumbent_rule(pos, origin) == ("reorder_point", "NOT_AVAILABLE")


def test_open_orders_become_pipeline_with_a_keep_option(built):
    request, report = built
    assert report["compact"]["open_purchase_orders"] == len(request.pipeline)
    for po in request.pipeline:
        assert po.remaining > 0 and sum(o.action == "keep" for o in po.options) == 1
        assert po.expected_accepted_remaining <= po.remaining and po.source in {s.id for s in request.sources}


def test_workspace_without_history_is_refused_with_an_operator_message():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    with pytest.raises(WorkspaceError, match="Upload"):
        build_request(conn, "empty")
    assert MIN_HISTORY_WEEKS >= 8


def test_frozen_plan_runs_on_the_workspace_request_and_keeps_approval_with_the_operator(built):
    request, build = built
    report = plan(request)
    assert report["approval_required"] is True and report["executable_purchase_order"] is False
    assert report["orchestration"]["planner_owner"] in ("PURCHASING_ECONOMICS", "PROTECTION_RECOVERY")
    purchase_plan = to_purchase_plan(request, report, build, run_id="t")
    assert purchase_plan["mode_run"] == "canonical_p1" and purchase_plan["approval_required"] is True
    assert purchase_plan["currency"] == request.currency and isinstance(purchase_plan["orders"], list)
    for order in purchase_plan["orders"]:
        assert order["sku"] in SUBSET and order["week_offset"] < 4 and order["order_units"] > 0

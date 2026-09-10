"""P2 network workspace adapter: a synthetic vault with declared locations and lanes becomes a network
request with provenance and no future leakage; a vault with fewer than two locations is the frozen
single-location request unchanged; the network plan shape carries transfers and explanations."""
from __future__ import annotations

from datetime import datetime, timezone

import duckdb
import pytest

from api.routers.intake import load_fmcg_sample_into
from scripts.setup_db import setup_db
from zaad.full.workspace import build_request
from zaad.meio.workspace import build_network_request, estimate_demand_correlation, to_network_plan

SKUS = ["SKU-0001", "SKU-0002"]


@pytest.fixture(scope="module")
def network_vault():
    from scripts.zaad_network_workspace_smoke import make_network_vault
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    make_network_vault(conn, seed=7)
    return conn


@pytest.fixture(scope="module")
def single_vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    load_fmcg_sample_into(conn, seed=7)
    return conn


def test_migration_adds_the_network_tables_and_location_columns(single_vault):
    tables = {r[0] for r in single_vault.execute("SELECT table_name FROM information_schema.tables").fetchall()}
    assert {"stg_fmcg_locations", "stg_fmcg_lanes", "stg_fmcg_transfers"} <= tables
    cols = {r[1] for r in single_vault.execute("PRAGMA table_info('stg_fmcg_orders')").fetchall()}
    assert "location_id" in cols


def test_fewer_than_two_locations_is_the_frozen_single_location_request(single_vault):
    frozen, frozen_build = build_request(single_vault, "tenant", skus=SKUS, max_solve_seconds=5.)
    req, build = build_network_request(single_vault, "tenant", skus=SKUS, max_solve_seconds=5.)
    assert req.model_dump(mode="json") == frozen.model_dump(mode="json")
    assert build["network"]["mode"] == "single_location" and len(req.locations) == 1 and not req.transfers


def test_declared_locations_and_lanes_become_a_network_with_provenance(network_vault):
    req, build = build_network_request(network_vault, "tenant", skus=SKUS, max_solve_seconds=5.)
    assert {loc.id: loc.kind for loc in req.locations} == {"DC": "central_dc", "NORTH": "branch", "SOUTH": "branch"}
    assert {s.location for s in req.services} == {"NORTH", "SOUTH"} and len(req.services) == 4
    assert all(s.destination == "DC" for s in req.sources)
    lanes = {a.id: a for a in req.transfers}
    assert len(lanes) == 4 and all(a.origin == "DC" for a in lanes.values())
    north = lanes["dc_north@SKU-0001"]
    south = lanes["dc_south@SKU-0001"]
    assert north.lead_periods == 1 and north.cost_per_unit == pytest.approx(.12)
    assert south.lead_periods == 2 and south.cost_per_unit == pytest.approx(.18)        # fitted from 30 receipts: 10 days
    assert build["network"]["lead_fits"]["DC->SOUTH"]["sample_size"] == 30
    prov = build["provenance"]
    assert prov["transfer.dc_north@SKU-0001.lead"] == "CUSTOMER_PROVIDED" and prov["transfer.dc_south@SKU-0001.lead"] == "INFERRED_FROM_HISTORY"
    assert prov["transfer.dc_north@SKU-0001.capacity"] == "CONFIGURED_ASSUMPTION" and north.capacity > 0
    assert prov["location.DC.holding_per_value_period"] == "CUSTOMER_PROVIDED" and prov["location.NORTH.holding_per_value_period"] == "CONFIGURED_ASSUMPTION"
    assert req.incumbent_rule == "network:rop" and build["network"]["demand_correlation"]["provenance"] == "INFERRED_FROM_HISTORY"
    assert 0. <= req.demand_correlation <= 1.
    assert {x.location for x in req.stock} == {"DC", "NORTH", "SOUTH"}
    origin = datetime.fromisoformat(build["origin_monday"]).replace(tzinfo=timezone.utc)
    assert all(h.period < 0 for h in req.history) and all(po.placed_at < origin for po in req.pipeline)
    assert build["compact"]["locations"] == 3 and build["compact"]["lanes"] == 4


def test_source_maximum_is_a_legal_pack_so_every_policy_projection_is_physical(network_vault):
    req, _ = build_network_request(network_vault, "tenant", skus=SKUS, max_solve_seconds=5.)
    for s in req.sources:
        pack = s.case_multiple or s.multiple
        if pack:
            assert abs(s.maximum / pack - round(s.maximum / pack)) < 1e-9
    from zaad.full.policies import baseline_plan
    from zaad.full.settlement import settle
    from zaad.full.worlds import draw
    from dataclasses import replace
    proj = baseline_plan(req, "network:rop")
    out = settle(req, replace(proj, status="OPTIMAL"), draw(req, req.seed, 1, deterministic=True)[0])
    assert abs(out["conservation_residual"]) < 1e-6


def test_demand_correlation_estimate_is_bounded_and_needs_two_locations():
    import pandas as pd
    weekly = pd.DataFrame({"sku": ["A"] * 40, "location_id": ["N", "S"] * 20, "week": [w for w in range(-20, 0) for _ in (0, 1)],
                           "qty_ordered": [100. + (w % 3) * 10 for w in range(-20, 0) for _ in (0, 1)]})
    rho, pairs = estimate_demand_correlation(weekly)
    assert pairs == 1 and rho == pytest.approx(1., abs=1e-9)
    assert estimate_demand_correlation(weekly[weekly["location_id"] == "N"]) == (None, 0)


def test_network_plan_shape_carries_transfers_and_explanations(network_vault):
    from zaad.meio.planner import plan_network
    req, build = build_network_request(network_vault, "tenant", skus=["SKU-0001"], max_solve_seconds=5.)
    report = plan_network(req)
    plan = to_network_plan(req, report, build, run_id="t")
    assert plan["approval_required"] is True and plan["executable_purchase_order"] is False
    assert plan["mode_run"] == "canonical_p2_network" and plan["network"] is not None
    assert set(plan["network_service"]) == {"svc_SKU-0001@NORTH", "svc_SKU-0001@SOUTH"}
    for row in plan["transfers"]:
        assert row["origin"] == "DC" and row["week_offset"] < 4 and row["units"] > 0 and row["arrives_week"] > row["week_offset"]
    import json
    json.dumps(plan, allow_nan=False)

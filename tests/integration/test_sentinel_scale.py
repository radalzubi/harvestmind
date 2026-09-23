"""Sentinel cleanup at scale: a 25-product workspace request that the released adapter's placeholders made numerically
infeasible solves normally; a genuinely infeasible request (declared capacity below the opening stock) still returns
INFEASIBLE; the replay runs on the cleaned request with the point-in-time protection, scope and settlement unchanged."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import duckdb
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.fixture(scope="module")
def sample():
    from api.routers.intake import load_fmcg_sample_into
    from scripts.setup_db import setup_db
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    load_fmcg_sample_into(conn, seed=7)
    yield conn
    conn.close()


def _request(conn, n: int):
    import zaad.full.historical as H
    from zaad.full.workspace import build_request
    as_of = datetime(2025, 8, 11, tzinfo=timezone.utc)
    probe, _ = build_request(conn, "scale", as_of=as_of, horizon=12)
    sel = H.select_scope(conn, probe, n, origin=pd.Timestamp("2025-08-11"), periods=19)
    req, _ = build_request(conn, "scale", as_of=as_of, horizon=12, skus=sel["skus"], seed=41001)
    return req


def test_25_products_no_longer_false_abstain(sample):
    from zaad.full.contracts import Request
    from zaad.full.model import solve
    from zaad.full.worlds import draw
    req = _request(sample, 25)
    assert all(loc.capacity_volume is None for loc in req.locations) and req.liquidity.opening_cash is None
    worlds = draw(req, req.seed, 1, deterministic=True)
    clean = solve(req, worlds, service_first="all", service_only=True)
    assert clean.status == "OPTIMAL"
    # the released placeholders on the identical data: the verbatim released formulation, declared INFEASIBLE by HiGHS
    data = req.model_dump(mode="python")
    data["locations"] = [{**loc, "capacity_volume": 1e9} for loc in data["locations"]]
    data["liquidity"].update(opening_cash=1e9, credit_limit=1e9)
    sentinel = solve(Request.model_validate(data), worlds, service_first="all", service_only=True)
    assert sentinel.status == "INFEASIBLE"


def test_genuine_infeasibility_still_reported(sample):
    from zaad.full.contracts import Request
    from zaad.full.model import solve
    from zaad.full.worlds import draw
    req = _request(sample, 25)
    opening_volume = sum(lot.usable * next(s.volume for s in req.skus if s.id == lot.sku) for lot in req.stock)
    data = req.model_dump(mode="python")
    data["locations"] = [{**loc, "capacity_volume": opening_volume * 0.5} for loc in data["locations"]]
    tight = solve(Request.model_validate(data), draw(req, req.seed, 1, deterministic=True), service_first="all", service_only=True)
    assert tight.status == "INFEASIBLE"


def test_replay_on_the_cleaned_request_keeps_its_protections(sample, monkeypatch):
    import zaad.full.historical as H
    from zaad.full.policies import baseline_plan
    from zaad.full.replay import NETWORK_METHODS

    def stub(req, method):
        if method in NETWORK_METHODS:
            return NETWORK_METHODS[method](req)
        assert req.liquidity.opening_cash is None and all(loc.capacity_volume is None for loc in req.locations)
        sol = baseline_plan(req, req.incumbent_rule or "reorder_point")
        sol.warnings = ["PENDING_REVIEW", "stub", *sol.warnings]
        return sol
    monkeypatch.setattr(H, "choose", stub)
    out = H.run_historical_replay(sample, "scale", skus=25, reviews=4, horizon=8, budget_s=600.0)
    assert out["status"] == "complete" and out["coverage"]["reviews_completed"] == 4
    assert all(v["all_clean"] and v["snapshots"] == 4 for v in out["attestation"].values())
    assert out["scope"]["selection"]["rule"] == "window_value" and out["scope"]["sku_count"] == 25
    assert {k: v["status"] for k, v in out["legs"].items()} == {"actual": "COMPLETE", "rule": "COMPLETE", "zaad": "COMPLETE"}
    assert all(r["cost"] == r["cost"] for leg in out["per_review"].values() for r in leg)     # settled, finite

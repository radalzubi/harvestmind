"""The read-only `network` block on /fmcg/state: the links the Network Twin
draws. It is a projection of the inputs already built for the state estimate,
so it must be complete when the upload is, honest when it is not, and never
raise on a partial workspace."""
from __future__ import annotations

from types import SimpleNamespace

from api.routers.fmcg import _network_block


def _inputs(**over):
    base = dict(
        products=["A", "B", "C"],
        supplier_of={"A": "s1", "B": "s1", "C": "s2"},
        route_of={"s1": "aqaba"},
        lead_of={"s1": 2, "s2": 3.5},
        opening={"A": 10.0, "B": 0.0, "C": 4.0},
        pipeline={("A", 1): 5.0, ("A", 2): 2.0, ("C", 1): 1.0},
        unit_cost={"A": 1.5, "B": 2.0, "C": 0.75},
    )
    base.update(over)
    return SimpleNamespace(**base)


def test_populated_block_links_every_product_to_its_supplier_lane_and_stock():
    report = {"supplier_master": {"s1": {"name": "Alpha", "route": "aqaba", "origin_iso3": "TUR", "capacity_per_week": 900.0},
                                  "s2": {"name": None, "route": None, "origin_iso3": None, "capacity_per_week": None}}}
    out = _network_block(_inputs(), report)
    assert out["products"] == ["A", "B", "C"]
    assert out["supplier_of"] == {"A": "s1", "B": "s1", "C": "s2"}
    assert out["route_of"] == {"s1": "aqaba"}
    assert out["lead_of"] == {"s1": 2.0, "s2": 3.5}
    assert out["opening"] == {"A": 10.0, "B": 0.0, "C": 4.0}
    # pipeline is summed across periods per product; products with nothing in transit are absent
    assert out["pipeline"] == {"A": 7.0, "C": 1.0}
    assert out["unit_cost"] == {"A": 1.5, "B": 2.0, "C": 0.75}
    assert out["suppliers"] == report["supplier_master"]
    assert "scope" in out


def test_missing_optional_inputs_yield_empty_maps_not_errors():
    out = _network_block(_inputs(route_of={}, opening={}, pipeline={}), {})
    assert out["route_of"] == {} and out["opening"] == {} and out["pipeline"] == {}
    assert out["suppliers"] == {}
    # route_of / opening / pipeline may be None on older input objects
    out = _network_block(_inputs(route_of=None, opening=None, pipeline=None), {"supplier_master": {}})
    assert out["route_of"] == {} and out["opening"] == {} and out["pipeline"] == {}


def test_incomplete_supplier_master_is_passed_through_verbatim():
    report = {"supplier_master": {"s1": {"name": None, "route": None, "origin_iso3": None, "capacity_per_week": None}}}
    out = _network_block(_inputs(), report)
    assert out["suppliers"] == report["supplier_master"]
    # a supplier the master does not know is still in supplier_of and lead_of
    assert "s2" in set(out["supplier_of"].values()) and "s2" in out["lead_of"]


def test_no_route_tags_means_no_lanes_but_all_links_survive():
    out = _network_block(_inputs(route_of={}), {"supplier_master": {"s1": {"name": "Alpha", "route": None, "origin_iso3": None, "capacity_per_week": None}}})
    assert out["route_of"] == {}
    assert set(out["supplier_of"].values()) == {"s1", "s2"}


def test_empty_workspace_is_an_empty_block():
    out = _network_block(_inputs(products=[], supplier_of={}, route_of={}, lead_of={}, opening={}, pipeline={}, unit_cost={}), {})
    assert out["products"] == [] and out["supplier_of"] == {} and out["lead_of"] == {} and out["unit_cost"] == {}


def test_values_are_plain_json_types():
    import json
    import numpy as np
    out = _network_block(_inputs(lead_of={"s1": np.float64(2.0), "s2": np.int64(3)}, opening={"A": np.float64(1.0)},
                                 pipeline={("A", np.int64(1)): np.float64(2.0)}, unit_cost={"A": np.float64(1.5)}), {})
    json.dumps(out)  # must not raise
    assert out["lead_of"] == {"s1": 2.0, "s2": 3.0} and out["pipeline"] == {"A": 2.0}

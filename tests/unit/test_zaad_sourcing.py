"""P3 sourcing portfolio: contract, hooks (model, worlds, settlement, projections), report and legacy neutrality."""
from __future__ import annotations

import json

import numpy as np
import pytest

from zaad.full.contracts import Request
from zaad.full.model import solve
from zaad.full.planner import plan
from zaad.full.settlement import settle
from zaad.full.worlds import draw
from zaad.meio.fixtures_p2 import p2_request
from zaad.sourcing.contracts import resolve
from zaad.sourcing.fixtures import FIXTURES, build, variant

DECL = "OPERATOR_DECLARED"


def _two_source(**b_fields) -> dict:
    p = p2_request(max_solve_seconds=5).model_dump(mode="json")
    a = next(s for s in p["sources"] if s["id"] == "src_A")
    p["sources"].append({**a, "id": "src_B", "supplier": "supplier_b", "route": ["supplier_b", "central"], "resources": ["cap_b"], **b_fields})
    p["resources"].append({**p["resources"][0], "id": "cap_b", "failure_domains": ["supplier_b"]})
    return p


def _with(p: dict, **sourcing) -> Request:
    return Request.model_validate({**p, "sourcing": sourcing})


def _worlds(req: Request, n: int = 3):
    return draw(req, req.seed, n)


# ── contract ───────────────────────────────────────────────────────────────

def test_legacy_request_has_no_sourcing_and_resolves_to_none():
    req = p2_request()
    assert req.sourcing is None and resolve(req) is None


@pytest.mark.parametrize("bad, match", [
    ({"risk_groups": [{"id": "g", "kind": "PLANT", "members": ["src_A", "src_B"], "provenance": "UNKNOWN"}]}, "provenance"),
    ({"risk_groups": [{"id": "g", "kind": "PLANT", "members": ["src_A", "src_A"], "provenance": DECL}]}, "duplicate member"),
    ({"risk_groups": [{"id": "g", "kind": "PLANT", "members": ["src_A", "src_Z"], "provenance": DECL}]}, "unknown source"),
    ({"risk_groups": [{"id": "g", "kind": "PLANT", "members": ["src_A", "src_B"], "provenance": DECL},
                      {"id": "h", "kind": "PORT", "members": ["src_B", "src_A"], "provenance": DECL}]}, "duplicates another group"),
    ({"share_constraints": [{"sku": "A", "destination": "central", "source": "src_B", "minimum_share": .6, "maximum_share": .4, "provenance": DECL}]}, "minimum share above"),
    ({"share_constraints": [{"sku": "A", "destination": "central", "source": "src_B", "minimum_share": .6, "provenance": DECL},
                            {"sku": "A", "destination": "central", "source": "src_A", "minimum_share": .6, "provenance": DECL}],
      "incumbent_shares": [{"sku": "A", "destination": "central", "source": "src_A", "share": .6, "provenance": DECL}]}, "sum above 100"),
    ({"share_constraints": [{"sku": "A", "destination": "central", "source": "src_B", "maximum_share": .3, "provenance": DECL},
                            {"sku": "A", "destination": "central", "source": "src_A", "maximum_share": .3, "provenance": DECL}],
      "incumbent_shares": [{"sku": "A", "destination": "central", "source": "src_A", "share": .3, "provenance": DECL}]}, "below 100"),
    ({"share_constraints": [{"sku": "A", "destination": "central", "source": "src_B", "minimum_share": .3, "provenance": DECL}]}, "no declared incumbent shares"),
    ({"share_constraints": [{"sku": "A", "destination": "central", "source": "src_B", "minimum_share": .3, "provenance": DECL}],
      "incumbent_shares": [{"sku": "A", "destination": "central", "source": "src_A", "share": 1., "provenance": DECL}]}, "does not meet"),
    ({"share_constraints": [{"sku": "A", "destination": "north", "source": "src_B", "minimum_share": .3, "provenance": DECL}]}, "supplies A to central"),
    ({"switching_costs": [{"source": "src_B", "cost": 10., "provenance": DECL}, {"source": "src_B", "cost": 20., "provenance": DECL}]}, "duplicate switching"),
    ({"switching_costs": [{"source": "src_B", "cost": -1., "provenance": DECL}]}, "greater than or equal"),
    ({"incumbent_shares": [{"sku": "A", "destination": "central", "source": "src_A", "share": .7, "provenance": DECL},
                           {"sku": "A", "destination": "central", "source": "src_B", "share": .7, "provenance": DECL}]}, "sum above 100"),
    ({"incumbent_shares": [{"sku": "A", "destination": "central", "source": "src_Q", "share": .7, "provenance": DECL}]}, "unknown source"),
])
def test_malformed_sourcing_is_refused_at_the_contract(bad, match):
    with pytest.raises(ValueError, match=match):
        _with(_two_source(), **bad)


def test_total_group_correlation_above_one_is_refused():
    p = _two_source()
    a = next(s for s in p["sources"] if s["id"] == "src_A")
    p["sources"].append({**a, "id": "src_C", "supplier": "supplier_c", "route": ["supplier_c", "central"], "resources": ["cap_c"]})
    p["resources"].append({**p["resources"][0], "id": "cap_c", "failure_domains": ["supplier_c"]})
    with pytest.raises(ValueError, match="above 1"):
        _with(p, risk_groups=[{"id": "g", "kind": "PLANT", "members": ["src_A", "src_B"], "correlation": .7, "provenance": DECL},
                              {"id": "h", "kind": "PORT", "members": ["src_A", "src_C"], "correlation": .5, "provenance": DECL}])


def test_non_finite_and_unqualified_declarations_are_refused():
    p = _two_source(approved=False)
    with pytest.raises(ValueError, match="not qualified"):
        _with(p, share_constraints=[{"sku": "A", "destination": "central", "source": "src_B", "minimum_share": .2, "provenance": DECL}],
              incumbent_shares=[{"sku": "A", "destination": "central", "source": "src_B", "share": .2, "provenance": DECL}])
    with pytest.raises(ValueError):
        _with(_two_source(), switching_costs=[{"source": "src_B", "cost": float("inf"), "provenance": DECL}])
    with pytest.raises(ValueError):
        _with(_two_source(), risk_groups=[{"id": "g", "kind": "PLANT", "members": ["src_A", "src_B"], "correlation": float("nan"), "provenance": DECL}])


def test_committed_units_above_capacity_are_refused():
    p = _two_source(capacity_by_period=[100.] * 12)
    with pytest.raises(ValueError, match="exceed its capacity"):
        _with(p, share_constraints=[{"sku": "A", "destination": "central", "source": "src_B", "committed_units": 5000., "provenance": DECL}],
              incumbent_shares=[{"sku": "A", "destination": "central", "source": "src_B", "share": .5, "provenance": DECL}])


# ── model hooks ────────────────────────────────────────────────────────────

def test_share_constraint_rows_bind_and_are_reported():
    req = _with(_two_source(unit_price=5.3),
                share_constraints=[{"sku": "A", "destination": "central", "source": "src_B", "minimum_share": .3, "scope": "period", "provenance": DECL}],
                incumbent_shares=[{"sku": "A", "destination": "central", "source": "src_A", "share": .7, "provenance": DECL},
                                  {"sku": "A", "destination": "central", "source": "src_B", "share": .3, "provenance": DECL}])
    sol = solve(req, _worlds(req), service_floor=True)
    assert sol.usable_plan
    for t in range(req.horizon):
        total = sol.purchases.get(("src_A", t), 0.) + sol.purchases.get(("src_B", t), 0.)
        if total > 1e-6:
            assert sol.purchases.get(("src_B", t), 0.) >= .3 * total - 1e-6
    assert sum(sol.purchases.get(("src_B", t), 0.) for t in range(req.horizon)) > 0


def test_switching_cost_is_charged_once_and_reconciles_in_settlement():
    p = _two_source(unit_price=4.5)
    free = _with(p, incumbent_shares=[{"sku": "A", "destination": "central", "source": "src_A", "share": 1., "provenance": DECL}])
    priced = _with(p, incumbent_shares=[{"sku": "A", "destination": "central", "source": "src_A", "share": 1., "provenance": DECL}],
                   switching_costs=[{"source": "src_B", "cost": 250., "provenance": DECL}])
    worlds = _worlds(free)
    a = solve(free, worlds, service_floor=True)
    b = solve(priced, worlds, service_floor=True)
    assert a.usable_plan and b.usable_plan
    b_units = sum(q for (s, _), q in a.purchases.items() if s == "src_B")
    assert b_units > 0, "the cheaper source is used when switching is free"
    # the settlement charges the declared cost exactly once when B is used, and never otherwise
    for sol, req in ((a, free), (b, priced)):
        row = settle(req, sol, worlds[0])
        uses_b = any(s == "src_B" and q > 1e-9 for (s, _), q in sol.purchases.items())
        expected = 250. if (uses_b and req is priced) else 0.
        assert abs(row["ledger"].get("switching", 0.) - expected) < 1e-9
    # the model's projected cost carries the same charge (no double counting: one binary, one ledger line)
    if any(s == "src_B" and q > 1e-9 for (s, _), q in b.purchases.items()):
        assert b.projected_cost is not None and a.projected_cost is not None and b.projected_cost >= a.projected_cost


def test_zero_capability_pruning_is_exact_on_the_plan():
    p = _two_source(unit_price=4.5, compliance="blocked", minimum=100., case_multiple=12.)
    on = _with(p, prune_zero_capability=True)
    off = _with(p, prune_zero_capability=False)
    worlds = _worlds(on)
    a, b = solve(on, worlds, service_floor=True), solve(off, worlds, service_floor=True)
    assert a.usable_plan and b.usable_plan
    assert a.variables < b.variables
    assert {k: round(v, 6) for k, v in a.purchases.items()} == {k: round(v, 6) for k, v in b.purchases.items()}
    assert abs((a.projected_cost or 0.) - (b.projected_cost or 0.)) <= 1e-6 * max(1., abs(b.projected_cost or 1.))


def test_source_commitments_are_scenario_invariant_and_nonnegative():
    req = _with(_two_source(unit_price=5.2), incumbent_shares=[{"sku": "A", "destination": "central", "source": "src_A", "share": 1., "provenance": DECL}])
    worlds = _worlds(req, 4)
    sol = solve(req, worlds, service_floor=True)
    assert sol.usable_plan and all(q >= 0 for q in sol.purchases.values())
    # one purchase column per source and period, shared by every world: settling on each world receives
    # different fills but the same commitments
    received = []
    for w in worlds:
        row = settle(req, sol, w)
        assert row["economic_cost"] is not None
        received.append(round(row["ledger"]["procurement"], 6))
    # the commitment (and its procurement value) is the same in every world; only the physical receipts vary
    assert len(set(received)) == 1


# ── worlds hook ────────────────────────────────────────────────────────────

def test_risk_group_correlates_members_and_preserves_marginals_and_frozen_stream():
    base = _two_source(fill_sd=.2, lead_sd_days=0.)
    base["sources"][0]["fill_sd"] = .2
    legacy = Request.model_validate(base)
    grouped = _with(base, risk_groups=[{"id": "plant", "kind": "PLANT", "members": ["src_A", "src_B"], "correlation": 1., "provenance": DECL}])
    ungrouped = _with(base)
    n = 200
    w0, w1, w2 = draw(legacy, 7, n), draw(grouped, 7, n), draw(ungrouped, 7, n)
    # the sourcing block alone changes nothing; the frozen stream (demand, PO draws) is untouched by a group
    assert all(a.fills == c.fills and a.demand == c.demand for a, c in zip(w0, w2))
    assert all(a.demand == b.demand and a.po_due == b.po_due for a, b in zip(w0, w1))
    fa = np.array([w.fills["src_A", 0] for w in w1])
    fb = np.array([w.fills["src_B", 0] for w in w1])
    la = np.array([w.fills["src_A", 0] for w in w0])
    lb = np.array([w.fills["src_B", 0] for w in w0])
    assert np.corrcoef(la, lb)[0, 1] < .3, "independent suppliers in the frozen draw"
    assert np.corrcoef(fa, fb)[0, 1] > .99, "a declared plant group makes the members fail together"
    # marginals: same mean and spread as the frozen draw (within sampling error of 200 worlds)
    assert abs(fa.mean() - la.mean()) < .03 and abs(fa.std() - la.std()) < .03


def test_partial_correlation_and_sources_outside_groups_keep_frozen_draws():
    base = _two_source(fill_sd=.2)
    base["sources"][0]["fill_sd"] = .2
    p = dict(base)
    a = next(s for s in p["sources"] if s["id"] == "src_A")
    p["sources"].append({**a, "id": "src_C", "supplier": "supplier_c", "route": ["supplier_c", "central"], "resources": ["cap_c"], "fill_sd": .2})
    p["resources"].append({**p["resources"][0], "id": "cap_c", "failure_domains": ["supplier_c"]})
    legacy = Request.model_validate(p)
    half = _with(p, risk_groups=[{"id": "plant", "kind": "PLANT", "members": ["src_A", "src_B"], "correlation": .5, "provenance": DECL}])
    n = 400
    w0, w1 = draw(legacy, 11, n), draw(half, 11, n)
    # C is in no group: its shocks are bit-identical to the frozen draw
    assert all(a.fills["src_C", t] == b.fills["src_C", t] for a, b in zip(w0, w1) for t in range(legacy.horizon))
    fa = np.array([w.fills["src_A", 1] for w in w1])
    fb = np.array([w.fills["src_B", 1] for w in w1])
    rho = np.corrcoef(fa, fb)[0, 1]
    assert .3 < rho < .7, rho


# ── projections, planner and report ─────────────────────────────────────────

def test_incumbent_mix_splits_the_rule_projection_and_legacy_rule_is_unchanged():
    from zaad.meio.baselines import network_rule_plan
    p = _two_source(unit_price=5.2)
    legacy = Request.model_validate(p)
    mixed = _with(p, incumbent_shares=[{"sku": "A", "destination": "central", "source": "src_A", "share": .6, "provenance": DECL},
                                       {"sku": "A", "destination": "central", "source": "src_B", "share": .4, "provenance": DECL}])
    plain = _with(p)
    a, b, c = network_rule_plan(legacy, "network:rop"), network_rule_plan(mixed, "network:rop"), network_rule_plan(plain, "network:rop")
    assert a.purchases == c.purchases, "a sourcing block without declared shares leaves the projection untouched"
    assert all(s == "src_A" for (s, _) in a.purchases)
    b_units = sum(q for (s, _), q in b.purchases.items() if s == "src_B")
    total = sum(b.purchases.values())
    assert total > 0 and abs(b_units / total - .4) < .1


def test_report_carries_sourcing_block_reasons_and_approval_flags():
    req = _with(_two_source(unit_price=4.6, freight_per_unit=.6, handling_per_unit=.1),
                incumbent_shares=[{"sku": "A", "destination": "central", "source": "src_A", "share": 1., "provenance": DECL}])
    rep = plan(req)
    json.dumps(rep, allow_nan=False)
    blk = rep["sourcing"]
    assert blk["approval_required"] is True and blk["executable_purchase_order"] is False
    assert rep["approval_required"] is True and rep["executable_purchase_order"] is False
    pair = blk["pairs"][0]
    assert {o["source"] for o in pair["options"]} == {"src_A", "src_B"}
    assert all(abs(sum(o["quantity_plan"] for o in pair["options"]) - pair["total_committed_plan"]) < 1e-6 for pair in blk["pairs"])
    assert any("lower unit price" in s and "total landed economics" in s for s in blk["explanations"])
    b = next(o for o in pair["options"] if o["source"] == "src_B")
    assert b["landed"]["landed_unit_cost"] > next(o for o in pair["options"] if o["source"] == "src_A")["landed"]["landed_unit_cost"]
    assert rep["economics"]["reconciled"] is True and rep["economics"]["unmapped_ledger_keys"] == []


def test_legacy_report_has_no_sourcing_block():
    rep = plan(p2_request(max_solve_seconds=5))
    assert "sourcing" not in rep


def test_fixtures_build_and_variants_are_consistent():
    for name in FIXTURES:
        req = build(name, 41001)
        assert req.sourcing is not None and req.evidence_label == "SYNTHETIC"
        single = variant(name, 41001, "single:supplier")
        assert all((not s.approved) for s in single.sources if s.supplier != "supplier" and (s.sku, s.destination) in {(x.sku, x.destination) for x in single.sources if x.supplier == "supplier"})
        legacy = variant(name, 41001, "gated_legacy")
        assert legacy.sourcing is None

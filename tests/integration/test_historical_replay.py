"""The rolling historical replay of the production optimizer (zaad/full/historical.py).

Point-in-time correctness is proved by perturbation: rows dated after a decision date, and truth after a
review, change nothing the planner saw at that date. The mechanics (three legs through one loop and one
settlement, state that evolves with the decisions, the budget stop, the abstain fallback, counterfactual
labels) run with the planner stubbed; one test runs the real production planner on two products and two
decision dates."""
from __future__ import annotations

import io
import json
import time
from dataclasses import replace

import pytest

import infrastructure.operator_registry as orm
from synthetic.fmcg.distributor_sim import ARCHETYPES, ArchetypeSpec, build_history


@pytest.fixture(scope="module")
def vault(tmp_path_factory):
    """A commercial workspace with 70 weeks of synthetic history, loaded through the intake so the vault is
    exactly what an operator's upload produces."""
    root = tmp_path_factory.mktemp("data")
    mp = pytest.MonkeyPatch()                      # module-scoped, undone at teardown: nothing leaks into later modules
    mp.setattr(orm, "DEFAULT_DATA_ROOT", root)
    mp.setenv("HARVESTMIND_AUTH_REQUIRED", "true")
    mp.setenv("HARVESTMIND_SOLVER_THREADS", "1")
    mp.setenv("HARVESTMIND_WORKER_MACHINES", "false")
    reg = orm.OperatorRegistry(data_root=root)
    op = reg.create_operator("Replay Co", sector="commercial")
    tok = reg.issue_token(op.operator_id)
    from fastapi.testclient import TestClient
    import api.main as api_main
    cl, h = TestClient(api_main.app), {"Authorization": f"Bearer {tok}"}
    spec = ArchetypeSpec(**{**ARCHETYPES["A_stable"].__dict__, "n_skus": 4, "n_suppliers": 2, "n_customers": 4, "weeks": 70})
    hist = build_history("A_stable", seed=11, spec=spec)
    skus = hist.skus[["sku", "supplier_id", "unit_cost", "unit_price", "units_per_case", "moq_units"]]
    orders = hist.order_lines.merge(hist.customer_orders[["order_id", "customer_id", "order_date"]], on="order_id")
    pos = hist.purchase_orders[["po_id", "po_date", "supplier_id", "sku", "qty_ordered", "unit_cost"]]
    rec = hist.receipts[["po_id", "receipt_date", "sku", "qty_received"]]
    inv = hist.inventory_snapshots.rename(columns={"week_start": "snapshot_date"})[["snapshot_date", "sku", "on_hand", "in_transit"]]
    for table, df in (("stg_fmcg_skus", skus), ("stg_fmcg_orders", orders[["order_id", "customer_id", "order_date", "sku", "qty_ordered"]]),
                      ("stg_fmcg_purchase_orders", pos), ("stg_fmcg_receipts", rec), ("stg_fmcg_inventory", inv)):
        r = cl.post(f"/intake/upload/{table}", headers=h, files={"file": (f"{table}.csv", io.BytesIO(df.to_csv(index=False).encode()), "text/csv")})
        assert r.status_code == 200, r.text
    from infrastructure.db_manager import DBManager
    dbm = DBManager(reg)
    conn = dbm.get_operator_connection(op.operator_id)
    yield {"conn": conn, "op": op.operator_id, "root": root, "client": cl, "headers": h}
    dbm.close_all()
    mp.undo()


def _rule_or_nothing(req, method):
    """A stand-in for the planner: the operator's rule on odd reviews, nothing on even ones, so ZAAD's
    decisions differ from the rule's and the state evolves differently."""
    from zaad.full.historical import _fixed_solution
    from zaad.full.policies import baseline_plan
    from zaad.full.replay import NETWORK_METHODS
    if method in NETWORK_METHODS:
        return NETWORK_METHODS[method](req)
    if req.as_of.isocalendar()[1] % 2 == 0:      # alternate by ISO week: differs from the rule on every other review
        return _fixed_solution(req, {}, "STUB_EMPTY")
    sol = baseline_plan(req, req.incumbent_rule or "reorder_point")
    sol.warnings = ["PENDING_REVIEW", "stub", *sol.warnings]
    return sol


# ── point-in-time correctness ────────────────────────────────────────────────
def test_future_rows_do_not_change_the_point_in_time_request(vault):
    """Orders, purchase orders, receipts and stock counts dated after the decision date leave the request
    byte-identical: no future demand, receipt, fill, lead-time or PO-status leakage."""
    from datetime import datetime, timezone
    from zaad.full.workspace import build_request
    conn, op = vault["conn"], vault["op"]
    last = conn.execute("SELECT MAX(order_date) FROM stg_fmcg_orders").fetchone()[0]
    as_of = datetime(last.year, last.month, last.day, tzinfo=timezone.utc) - __import__("datetime").timedelta(weeks=20)
    before, _ = build_request(conn, op, as_of=as_of, horizon=8)
    sku = before.skus[0].id
    sup = before.sources[0].supplier
    # rows strictly after the decision date, in every table the planner reads
    conn.execute("INSERT INTO stg_fmcg_orders (order_id, customer_id, order_date, sku, qty_ordered) VALUES ('leak-o', 'c', ?, ?, 99999)", [as_of.date() + __import__("datetime").timedelta(days=3), sku])
    conn.execute("INSERT INTO stg_fmcg_purchase_orders (po_id, po_date, supplier_id, sku, qty_ordered, unit_cost) VALUES ('leak-po', ?, ?, ?, 88888, 1.0)", [as_of.date() + __import__("datetime").timedelta(days=1), sup, sku])
    conn.execute("INSERT INTO stg_fmcg_receipts (po_id, receipt_date, sku, qty_received) VALUES ('leak-po', ?, ?, 88888)", [as_of.date() + __import__("datetime").timedelta(days=10), sku])
    conn.execute("INSERT INTO stg_fmcg_inventory (snapshot_date, sku, on_hand, in_transit) VALUES (?, ?, 777777, 0)", [as_of.date() + __import__("datetime").timedelta(days=2), sku])
    try:
        after, build = build_request(conn, op, as_of=as_of, horizon=8)
    finally:
        conn.execute("DELETE FROM stg_fmcg_orders WHERE order_id = 'leak-o'")
        conn.execute("DELETE FROM stg_fmcg_purchase_orders WHERE po_id = 'leak-po'")
        conn.execute("DELETE FROM stg_fmcg_receipts WHERE po_id = 'leak-po'")
        conn.execute("DELETE FROM stg_fmcg_inventory WHERE on_hand = 777777")
    assert after.model_dump_json() == before.model_dump_json()
    assert build["leakage_guard"]["purchase_orders_at_or_after_origin_excluded"] >= 1
    # and a receipt dated after the decision date for an order placed before it is NOT observed
    assert all((not r.arrived) or r.known_at <= before.as_of for r in before.shipment_history)


def test_truth_after_a_review_does_not_reach_that_review(vault, monkeypatch):
    """Perturb demand, fills and arrivals for every period after review k: the planning snapshots of
    reviews 0..k are byte-identical."""
    from datetime import datetime, timezone
    import zaad.full.historical as H
    from zaad.full.replay import replay
    from zaad.full.workspace import build_request
    conn, op = vault["conn"], vault["op"]
    last = conn.execute("SELECT MAX(order_date) FROM stg_fmcg_orders").fetchone()[0]
    as_of = datetime(last.year, last.month, last.day, tzinfo=timezone.utc) - __import__("datetime").timedelta(weeks=24)
    as_of = as_of - __import__("datetime").timedelta(days=as_of.weekday())
    initial, _ = build_request(conn, op, as_of=as_of, horizon=8, skus=[s.id for s in build_request(conn, op, as_of=as_of, horizon=8)[0].skus][:2])
    reviews = 4
    truth, _ = H.build_truth(conn, initial, periods=reviews - 1 + 8, seed=1)
    # review t's snapshot carries demand up to period t-1 (a week enters the history after it settles), so a
    # perturbation from period k+1 on can first appear in the snapshot of review k+2
    k = 1
    demand = {s: tuple(v if t <= k else v * 3 + 50 for t, v in enumerate(vals)) for s, vals in truth.demand.items()}
    fills = {key: (v if key[1] <= k else max(0.05, v * 0.5)) for key, v in truth.fills.items()}
    arrival = {key: (v if key[1] <= k else v + 3) for key, v in truth.arrival.items()}
    perturbed = replace(truth, demand=demand, fills=fills, arrival=arrival)
    monkeypatch.setattr(H, "choose", _rule_or_nothing)
    a, b = [], []
    replay(initial, truth, reviews, "incumbent", keep_requests=a, rolling=True)
    replay(initial, perturbed, reviews, "incumbent", keep_requests=b, rolling=True)
    for t in range(k + 2):
        assert a[t].model_dump_json() == b[t].model_dump_json(), f"review {t} saw the future"
    assert a[k + 2].model_dump_json() != b[k + 2].model_dump_json(), "the perturbation did reach later reviews"
    att = H.attest(a)
    assert att["all_clean"] and att["snapshots"] == reviews


# ── mechanics with the planner stubbed ───────────────────────────────────────
def test_three_legs_state_evolves_and_labels(vault, monkeypatch):
    import zaad.full.historical as H
    from zaad.full.replay import NETWORK_METHODS
    conn, op = vault["conn"], vault["op"]
    seen = []

    def stub(req, method):
        seen.append(method)
        return _rule_or_nothing(req, method)
    monkeypatch.setattr(H, "choose", stub)
    before = set(NETWORK_METHODS)
    out = H.run_historical_replay(conn, op, skus=2, reviews=4, horizon=8, budget_s=600.0, progress=lambda st, info: None)
    assert set(NETWORK_METHODS) == before, "registered leg methods must be removed after the run"
    assert out["status"] == "complete", out
    assert out["coverage"]["reviews_completed"] == 4 and out["coverage"]["reviews_planned"] == 4
    assert set(out["legs"]) == {"actual", "rule", "zaad"} and all(v["reviews"] == 4 for v in out["legs"].values())
    # the optimizer stand-in was called once per decision date with the real planning snapshot
    assert seen.count("gated") == 4 and len(out["zaad_reviews"]) == 4
    # decisions: one row per date per product; the ZAAD column differs from the rule on even reviews
    rows = out["decisions"]
    assert len(rows) == 4 * 2 and {r["review"] for r in rows} == {0, 1, 2, 3}
    empty_weeks = {r["review"] for r in rows if (r["zaad_qty"] or 0) == 0 and (r["rule_qty"] or 0) > 0}
    assert empty_weeks, "the stand-in ordered nothing on alternate weeks where the rule ordered"
    # state evolves with the decisions: end stock under ZAAD differs from the rule where orders differed
    z, ru = out["per_review"]["zaad"], out["per_review"]["rule"]
    assert any(abs(z[t]["end_stock_units"] - ru[t]["end_stock_units"]) > 1e-6 for t in range(1, 4))
    # labels: every ZAAD order carries a settlement label from the four; shares sum to one
    labels = [r["settlement"] for r in rows if (r["zaad_qty"] or 0) > 0]
    assert labels and set(labels) <= {"MEASURED", "INFERRED", "SIMULATED", "ASSUMED"}
    shares = out["settlement_provenance"]["shares_by_zaad_order"]
    assert abs(sum(shares.values()) - 1.0) < 1e-6
    assert out["settlement_provenance"]["demand"].startswith("MEASURED")
    # attestation on every leg's snapshots
    assert all(v["all_clean"] for v in out["attestation"].values())
    # scores are the endpoint scores of the completed prefix and the differences reconcile with them
    da = out["differences"]["zaad_vs_actual"]
    assert da["periods"] == 4 and abs(da["window"]["difference"] - (out["legs"]["actual"]["realized_cost"] - out["legs"]["zaad"]["realized_cost"])) < 1e-6
    assert out["confidence"]["level"] in ("High", "Moderate", "Low") and out["performance"]["optimizer_solves"] == 4
    assert json.dumps(out, default=str)   # serialisable


def test_counterfactual_labels(vault, monkeypatch):
    """MEASURED where the operator's own received order exists in that week; INFERRED from the supplier's
    nearby orders otherwise; SIMULATED when no order is near; ASSUMED when the supplier was never observed.
    A different quantity on a MEASURED cell is counted as INFERRED for that decision."""
    from datetime import datetime, timezone
    import zaad.full.historical as H
    from zaad.full.workspace import build_request
    conn, op = vault["conn"], vault["op"]
    last = conn.execute("SELECT MAX(order_date) FROM stg_fmcg_orders").fetchone()[0]
    as_of = datetime(last.year, last.month, last.day, tzinfo=timezone.utc) - __import__("datetime").timedelta(weeks=20)
    as_of = as_of - __import__("datetime").timedelta(days=as_of.weekday())
    initial, _ = build_request(conn, op, as_of=as_of, horizon=8)
    truth, prov = H.build_truth(conn, initial, periods=12, seed=3)
    labels = set(prov["supply"].values())
    assert "MEASURED" in labels and "INFERRED" in labels
    # every measured cell is a week the operator actually ordered that SKU
    actual = H.actual_orders_by_review(conn, initial, 12)
    for key, label in prov["supply"].items():
        src, t = key.split("|")
        if label == "MEASURED":
            assert actual[int(t)].get(src, 0) > 0
    # no nearby order at all -> SIMULATED from the supplier's own record
    monkeypatch.setattr(H, "NEAREST_WEEKS", -1)
    _, prov2 = H.build_truth(conn, initial, periods=12, seed=3)
    assert "SIMULATED" in set(prov2["supply"].values()) and "INFERRED" not in set(prov2["supply"].values())
    # a supplier never observed -> ASSUMED (declared / assumed lead and fill)
    src0 = initial.sources[0]
    ghost = initial.model_copy(update={"sources": (src0.model_copy(update={"supplier": "NEVER-SEEN"}),) + initial.sources[1:]})
    # 40 periods run past the end of the recorded history, where no order of the operator's exists
    _, prov3 = H.build_truth(conn, ghost, periods=40, seed=3)
    own = {k for k, v in prov3["supply"].items() if k.startswith(src0.id + "|") and v == "MEASURED"}   # the operator's own received orders stay measured
    assert all(v == "ASSUMED" for k, v in prov3["supply"].items() if k.startswith(src0.id + "|") and k not in own)
    assert any(k not in own for k in prov3["supply"] if k.startswith(src0.id + "|"))
    # a MEASURED cell with a different quantity counts as INFERRED for that decision
    per = {"actual": [{"purchases": {src0.id: 100.0}, "as_of": "d", "service_by_sku": {}, "end_stock_by_sku": {}}],
           "zaad": [{"purchases": {src0.id: 60.0}, "as_of": "d", "service_by_sku": {}, "end_stock_by_sku": {}}]}
    key = f"{src0.id}|0"
    fake_prov = {"supply": {key: "MEASURED"}, "supply_actual_qty": {key: 100.0}}
    methods = H._LegMethods(initial, {0: {src0.id: 100.0}})
    rows = H._decision_rows(initial, per, methods, fake_prov, 1)
    row = next(r for r in rows if r["sku"] == src0.sku)
    assert row["settlement_cell"] == "MEASURED" and row["settlement"] == "INFERRED" and row["zaad_action"] == "less"
    per["zaad"][0]["purchases"][src0.id] = 100.0
    row = next(r for r in H._decision_rows(initial, per, methods, fake_prov, 1) if r["sku"] == src0.sku)
    assert row["settlement"] == "MEASURED" and row["zaad_action"] == "same"


def test_budget_stops_the_zaad_leg_and_scores_the_common_prefix(vault, monkeypatch):
    import zaad.full.historical as H
    conn, op = vault["conn"], vault["op"]

    def slow(req, method):
        time.sleep(0.05)
        return _rule_or_nothing(req, method)
    monkeypatch.setattr(H, "choose", slow)
    monkeypatch.setattr(H, "DEFAULT_BUDGET_S", 0.01)
    out = H.run_historical_replay(conn, op, skus=2, reviews=4, horizon=8, budget_s=0.01)
    assert out["status"] == "partial" and out["coverage"]["stopped_by_budget"] is True
    W = out["coverage"]["reviews_completed"]
    assert 1 <= W < 4 and all(v["reviews"] == W for v in out["legs"].values())
    assert len(out["per_review"]["actual"]) == W == len(out["per_review"]["zaad"])
    assert any("planned decision dates completed within the time budget" in r for r in out["confidence"]["reasons"])


def test_abstaining_planner_keeps_the_rule(vault, monkeypatch):
    import zaad.full.historical as H
    from zaad.full.model import Solution
    conn, op = vault["conn"], vault["op"]

    def abstain(req, method):
        if method == "gated":
            return Solution("ABSTAIN", {}, {}, {}, {}, None, [], 0.0, 0, 0, None, None, ["ABSTAIN", "operator_rule:periodic:2", "mode=ALLOCATE"])
        return _rule_or_nothing(req, method)
    monkeypatch.setattr(H, "choose", abstain)
    out = H.run_historical_replay(conn, op, skus=2, reviews=3, horizon=8, budget_s=600.0)
    assert out["status"] == "complete"
    assert all(e["fallback_to_rule"] for e in out["zaad_reviews"]) and all(e["status"] == "ABSTAIN" for e in out["zaad_reviews"])
    z, ru = out["per_review"]["zaad"], out["per_review"]["rule"]
    assert all(abs(z[t]["cost"] - ru[t]["cost"]) < 1e-6 for t in range(3)), "an abstaining review executes the operator's rule"


def test_unavailable_when_history_is_too_short(vault):
    import zaad.full.historical as H
    conn, op = vault["conn"], vault["op"]
    from datetime import datetime, timezone
    first = conn.execute("SELECT MIN(order_date) FROM stg_fmcg_orders").fetchone()[0]
    out = H.run_historical_replay(conn, op, skus=2, reviews=26, horizon=12, budget_s=1.0,
                                  end_before=datetime(first.year, first.month, first.day, tzinfo=timezone.utc) + __import__("datetime").timedelta(weeks=20))
    assert out["status"] == "unavailable" and "not enough history" in out["reason"]


# ── the real production planner ──────────────────────────────────────────────
def test_real_planner_two_products_two_dates(vault):
    """The production optimizer itself, re-run at two decision dates on two products; slow (real MILPs)."""
    import zaad.full.historical as H
    conn, op = vault["conn"], vault["op"]
    out = H.run_historical_replay(conn, op, skus=2, reviews=2, horizon=8, budget_s=900.0)
    assert out["status"] == "complete", out
    assert out["engine"]["optimizer"].startswith("zaad.full.planner.plan")
    assert out["performance"]["optimizer_solves"] == 2 and all(e["status"] for e in out["zaad_reviews"])
    assert all(v["all_clean"] for v in out["attestation"].values())
    assert out["legs"]["zaad"]["status"] == "COMPLETE"


# ── security ─────────────────────────────────────────────────────────────────
def test_replay_result_is_scoped_to_the_workspace_and_routes_stay_isolated(vault):
    """The replay only ever reads the connection it is given; another workspace's key gets 404 on the job routes
    and the replay result carries no operator id."""
    cl = vault["client"]
    reg = orm.OperatorRegistry(data_root=vault["root"])
    other = reg.create_operator("Other Co", sector="commercial")
    h2 = {"Authorization": f"Bearer {reg.issue_token(other.operator_id)}"}
    assert cl.get("/jobs/latest", headers=h2).json() == {"job": None}
    assert cl.get("/jobs/job_nope", headers=h2).status_code == 404
    assert cl.get("/jobs/latest").status_code == 401
    import zaad.full.historical as H
    out = H.run_historical_replay(vault["conn"], vault["op"], skus=1, reviews=1, horizon=8, budget_s=0.001)
    assert "operator_id" not in json.dumps({k: v for k, v in out.items() if k != "build"})

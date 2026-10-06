"""Diagnostic V3.1 — replay scale: study selection, engine choice, shared-capacity conformance of the
reconstructed rule, decision-change accounting, evidence basis, operating regimes and a full 26-date
completion with a fast stub in place of the optimizer. The optimizer itself is not exercised here (its
equivalence is pinned in tests/unit/test_zaad_tie_certificate.py and the frozen regression)."""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone

import duckdb
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# The demo company is generated around an anchor date (`as_of`, by default the wall-clock date): the week
# grid, which orders are still open and therefore the seeded random stream all follow it. Left unpinned,
# this vault changed with the calendar, and on 2026-10-05 the 2026-06-08 snapshot below carried a
# different label set than on the days around it. The anchor is pinned to that day: it is the dataset on
# which the behaviour was diagnosed, it reproduces the three supplier orders received partly before and
# partly after 2026-06-08 that tests/integration/test_replay_regime_receipt_defect.py records, and every
# other test in this module ran on it in hosted CI.
DEMO_AS_OF = date(2026, 10, 5)
DEMO_SEED = 7


def demo_vault(as_of: date = DEMO_AS_OF, seed: int = DEMO_SEED):
    from scripts.setup_db import setup_db
    from synthetic.fmcg.demo_company import load_demo_company_into
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    load_demo_company_into(conn, "scale", as_of=as_of, seed=seed)
    return conn


@pytest.fixture(scope="module")
def vault():
    conn = demo_vault()
    yield {"conn": conn, "op": "scale"}
    conn.close()


def _rule_stub(req, method):
    """The reconstructed rule with every other week empty: cheap, and different from the rule on alternate dates."""
    from zaad.full.replay import NETWORK_METHODS
    if method in NETWORK_METHODS:
        return NETWORK_METHODS[method](req)
    import zaad.full.historical as H
    from zaad.full.policies import baseline_plan
    if req.as_of.isocalendar()[1] % 2 == 0:
        return H._fixed_solution(req, {}, "STUB_EMPTY")
    sol = baseline_plan(req, req.incumbent_rule or "reorder_point")
    sol.warnings = ["PENDING_REVIEW", "stub", *sol.warnings]
    return sol


# ── study selection ──────────────────────────────────────────────────────────
def test_scope_selection_is_deterministic_labelled_and_reports_coverage(vault):
    import zaad.full.historical as H
    from zaad.full.workspace import build_request
    conn, op = vault["conn"], vault["op"]
    as_of = datetime(2026, 6, 8, tzinfo=timezone.utc)
    probe, _ = build_request(conn, op, as_of=as_of, horizon=12)
    a = H.select_scope(conn, probe, 5, origin=pd.Timestamp("2026-06-08"), periods=14)
    b = H.select_scope(conn, probe, 5, origin=pd.Timestamp("2026-06-08"), periods=14)
    assert a == b and len(a["skus"]) == 5 and a["rule"] == "window_value"
    assert a["information"].startswith("STUDY SELECTION")
    cov = a["coverage"]
    assert 0 < cov["window_demand_value_share"] <= 1 and 0 < cov["d0_demand_value_share"] <= 1 and 0 <= cov["purchase_order_line_share"] <= 1
    assert cov["sku_count"] == 5 and cov["skus_in_workspace"] == len(probe.skus)
    assert a["strata"]["intermittent"] + a["strata"]["regular"] == 5
    d0 = H.select_scope(conn, probe, 5, origin=pd.Timestamp("2026-06-08"), periods=14, rule="d0_value")
    assert d0["skus"] == sorted(H.select_skus(probe, 5)[0], key=lambda k: (-0, k)) or set(d0["skus"]) == set(H.select_skus(probe, 5)[0])
    with pytest.raises(ValueError):
        H.select_scope(conn, probe, 5, origin=pd.Timestamp("2026-06-08"), periods=14, rule="favourable")


def test_scope_selection_never_reads_outcomes_and_requests_stay_point_in_time(vault, monkeypatch):
    """The study selection reads the window's customer demand; it never reads purchase orders' outcomes or the
    optimizer, and the decision requests built for the chosen products carry nothing after their own date."""
    import zaad.full.historical as H
    from zaad.full.workspace import build_request
    conn, op = vault["conn"], vault["op"]
    as_of = datetime(2026, 6, 8, tzinfo=timezone.utc)
    probe, _ = build_request(conn, op, as_of=as_of, horizon=12)
    before = H.select_scope(conn, probe, 4, origin=pd.Timestamp("2026-06-08"), periods=14)
    # receipts and stock counts after the origin do not change the selection (only demand and cost do)
    conn.execute("INSERT INTO stg_fmcg_receipts (po_id, receipt_date, sku, qty_received) VALUES ('leak-r', '2026-07-01', ?, 999999)", [before["skus"][0]])
    conn.execute("INSERT INTO stg_fmcg_inventory (snapshot_date, sku, on_hand, in_transit) VALUES ('2026-07-01', ?, 999999, 0)", [before["skus"][-1]])
    try:
        after = H.select_scope(conn, probe, 4, origin=pd.Timestamp("2026-06-08"), periods=14)
    finally:
        conn.execute("DELETE FROM stg_fmcg_receipts WHERE po_id = 'leak-r'")
        conn.execute("DELETE FROM stg_fmcg_inventory WHERE on_hand = 999999")
    assert after == before
    req, build = build_request(conn, op, as_of=as_of, horizon=12, skus=before["skus"])
    assert {s.id for s in req.skus} == set(before["skus"])
    assert all(r.known_at <= req.as_of for r in req.history) and all(r.known_at <= req.as_of for r in req.stock)
    assert build["leakage_guard"]["purchase_orders_at_or_after_origin_excluded"] >= 0


# ── rule conformance against shared capacity ─────────────────────────────────
def test_reconstructed_rule_is_scaled_to_shared_supplier_capacity(vault):
    import zaad.full.historical as H
    from zaad.full.workspace import build_request
    from zaad.full.policies import baseline_plan
    conn, op = vault["conn"], vault["op"]
    as_of = datetime(2026, 6, 15, tzinfo=timezone.utc)
    probe, _ = build_request(conn, op, as_of=as_of, horizon=12)
    sel = H.select_scope(conn, probe, 25, origin=pd.Timestamp("2026-06-15"), periods=14)
    req, _ = build_request(conn, op, as_of=as_of, horizon=12, skus=sel["skus"])
    plan = baseline_plan(req, req.incumbent_rule or "periodic:2")
    conformed, notes = H._conform_shared(req, plan.purchases)
    sources = {s.id: s for s in req.sources}
    volume = {s.id: s.volume for s in req.skus}
    for res in req.resources:
        for t in range(req.horizon):
            load = sum(q * volume[sources[sid].sku] for (sid, k), q in conformed.items() if k == t and res.id in sources[sid].resources)
            assert load <= res.capacity_by_period[min(t, len(res.capacity_by_period) - 1)] + 1e-6
    for (sid, t), q in conformed.items():
        assert q <= plan.purchases[sid, t] + 1e-9          # never scaled up
        src = sources[sid]
        step = max(src.case_multiple, src.multiple, 0.0)
        if step > 0 and q > 0:
            assert abs(q / step - round(q / step)) < 1e-6   # still a whole number of cases
    assert all("scaled by" in n["note"] for n in notes)


# ── a full 26-date replay with the stub, accounting and regimes ──────────────
def test_full_26_date_replay_completes_with_accounting(vault, monkeypatch):
    import zaad.full.historical as H
    monkeypatch.setattr(H, "choose", _rule_stub)
    conn, op = vault["conn"], vault["op"]
    out = H.run_historical_replay(conn, op, skus=3, reviews=26, horizon=8, budget_s=600.0)
    assert out["status"] == "complete" and out["coverage"]["reviews_completed"] == 26 and out["coverage"]["stopped_by_budget"] is False
    assert out["performance"]["optimizer_solves"] == 26 == out["performance"]["decision_points"]
    sel = out["scope"]["selection"]
    assert sel["rule"] == "window_value" and sel["information"].startswith("STUDY SELECTION")
    assert out["engine"]["formulation"] == "network" and out["engine"]["certificates"] is None
    ch = out["decision_changes"]
    assert ch["available"] and ch["reviews"] == 26
    ro = ch["review_outcomes"]
    assert ro["retained_rule"] + ro["own_plan"] + ro["abstained_or_fallback"] == 26
    assert ch["lines_total"] == 26 * len(out["scope"]["skus"]) and sum(ch["lines"].values()) == ch["lines_total"]
    assert ch["changed_lines"] == sum(v for k, v in ch["lines"].items() if k != "same")
    assert ch["material_lines"] <= ch["changed_lines"] and ch["material_reviews"] <= 26
    assert "one source per product" in ch["source_changes"] and ch["magnitude"]["units_added"] >= 0
    ev = out["evidence_basis"]
    for leg in ("actual", "rule", "zaad"):
        shares = ev["by_leg"][leg]["shares"]
        assert set(shares) == {"MEASURED", "INFERRED", "SIMULATED", "ASSUMED"}
        assert ev["by_leg"][leg]["units"] == 0 or abs(sum(shares.values()) - 1) < 1e-3
    assert ev["demand"].startswith("MEASURED")
    reg = out["regimes"]
    assert len(reg["labels_per_review"]) == 26 and all(lab for lab in reg["labels_per_review"])
    assert set(reg["definitions"]) == {"supplier_deterioration", "intermittent_demand", "constrained_inventory", "stable"}
    for v in reg["by_operating_regime"].values():
        assert v["periods"] >= 3 and 0 <= v["share_improved"] <= 1
    # the attestation covers every leg and every date
    assert all(v["all_clean"] and v["snapshots"] == 26 for v in out["attestation"].values())


def test_engine_choice_rides_on_the_request(vault, monkeypatch):
    import zaad.full.historical as H
    seen = []

    def spy(req, method):
        seen.append(req.fefo_symmetry_scope)
        return _rule_stub(req, method)
    monkeypatch.setattr(H, "choose", spy)
    conn, op = vault["conn"], vault["op"]
    out = H.run_historical_replay(conn, op, skus=2, reviews=4, horizon=8, budget_s=600.0, fefo="certified")
    assert out["status"] == "complete" and out["engine"]["formulation"] == "certified"
    assert seen and all(s == "certified" for s in seen)
    with pytest.raises(ValueError):
        H.run_historical_replay(conn, op, skus=2, reviews=4, horizon=8, budget_s=600.0, fefo="fast")


def test_regime_labels_are_valid_and_stable_is_exclusive(vault):
    """Structure of the label set only: every label is a known regime, and "stable" is the whole answer or
    absent. Whether the labels are point in time is not proved here; the receipt path that makes them
    depend on later receipts is recorded in tests/integration/test_replay_regime_receipt_defect.py."""
    import zaad.full.historical as H
    from zaad.full.workspace import build_request
    conn, op = vault["conn"], vault["op"]
    req, _ = build_request(conn, op, as_of=datetime(2026, 6, 8, tzinfo=timezone.utc), horizon=12)
    labels = H._review_regimes(req)
    assert labels and set(labels) <= {"supplier_deterioration", "intermittent_demand", "constrained_inventory", "stable"}
    assert labels == ["stable"] or "stable" not in labels


# ── the fixture does not depend on the day the tests run ─────────────────────
TABLES = ("stg_fmcg_skus", "stg_fmcg_suppliers", "stg_fmcg_orders", "stg_fmcg_purchase_orders", "stg_fmcg_receipts",
          "stg_fmcg_inventory", "stg_fmcg_sources", "stg_fmcg_economics", "stg_po_commitments", "stg_po_options")


# columns that record when ZAAD wrote the row (ingestion time), not what the row says
INGESTION_COLUMNS = {"imported_at", "declared_at", "_uploaded_at", "_upload_session_id", "_source_file"}


def _rows(conn) -> dict[str, list]:
    out = {}
    for t in TABLES:
        columns = [r[0] for r in conn.execute(f"DESCRIBE {t}").fetchall() if r[0] not in INGESTION_COLUMNS]
        out[t] = conn.execute(f"SELECT {', '.join(columns)} FROM {t} ORDER BY ALL").fetchall()
    return out


def _pretend_today(monkeypatch, today: date) -> None:
    """The generator reads `date.today()` only to default its anchor; make that read return `today`."""
    import synthetic.fmcg.demo_company as demo

    class FrozenDate(date):
        @classmethod
        def today(cls):
            return today
    monkeypatch.setattr(demo, "date", FrozenDate)


@pytest.mark.parametrize("today", [date(2026, 10, 4), date(2026, 10, 5), date(2026, 10, 6), date(2027, 3, 1)])
def test_the_pinned_fixture_is_the_same_vault_and_request_on_any_calendar_day(vault, monkeypatch, today):
    from zaad.full.workspace import build_request
    _pretend_today(monkeypatch, today)
    other = demo_vault()
    try:
        assert _rows(other) == _rows(vault["conn"])
        a, _ = build_request(vault["conn"], "scale", as_of=datetime(2026, 6, 8, tzinfo=timezone.utc), horizon=12)
        b, _ = build_request(other, "scale", as_of=datetime(2026, 6, 8, tzinfo=timezone.utc), horizon=12)
        assert a.model_dump_json() == b.model_dump_json()
    finally:
        other.close()


def test_without_the_pin_the_vault_follows_the_calendar(monkeypatch):
    """Why the pin exists: the default anchor is the wall-clock date, and one day's difference changes the data."""
    from scripts.setup_db import setup_db
    from synthetic.fmcg.demo_company import load_demo_company_into
    seen = []
    for today in (date(2026, 10, 5), date(2026, 10, 6)):
        _pretend_today(monkeypatch, today)
        conn = duckdb.connect(":memory:")
        setup_db(conn)
        load_demo_company_into(conn, "scale", seed=DEMO_SEED)        # no as_of: the generator asks for today
        seen.append(_rows(conn))
        conn.close()
    assert seen[0]["stg_fmcg_receipts"] != seen[1]["stg_fmcg_receipts"]

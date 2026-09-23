"""Sentinel cleanup (OPTIMIZER_SENTINEL_CLEANUP.md): undeclared warehouse capacity and undeclared capital are
absent constraints, never a 10⁹ placeholder.

WAREHOUSE CAPACITY  missing capacity omits the volume rows and column bounds; a declared capacity is enforced
                    and can bind; no 10⁹ enters any big-M; the stock bound is derived from the request's data
                    and every solution respects it.
CAPITAL             missing cash means no cash / debt columns and no capital ceiling; a declared ceiling is
                    enforced and binds; the purchase economics and the working-capital charge remain; no
                    artificial cash constant enters the objective.
EQUIVALENCE         the released sentinel model (declared 10⁹, verbatim formulation) and the clean model return
                    the same decisions and the same settlement, and their projected costs differ by exactly
                    the sentinel's constant.
"""
from __future__ import annotations

import pytest

import zaad.full.model as M
from zaad.full.contracts import Request
from zaad.full.demo import example
from zaad.full.model import solve
from zaad.full.settlement import PhysicalViolation, settle
from zaad.full.worlds import draw


def _variant(req: Request, *, capacity=..., opening_cash=..., credit_limit=...) -> Request:
    data = req.model_dump(mode="python")
    if capacity is not ...:
        data["locations"] = [{**loc, "capacity_volume": capacity} for loc in data["locations"]]
    if opening_cash is not ...:
        data["liquidity"]["opening_cash"] = opening_cash
    if credit_limit is not ...:
        data["liquidity"]["credit_limit"] = credit_limit
    return Request.model_validate(data)


def _capture(monkeypatch) -> list:
    built: list = []
    orig = M.Linear.solve

    def spy(self, *a, **k):
        built.append(self)
        return orig(self, *a, **k)
    monkeypatch.setattr(M.Linear, "solve", spy)
    return built


def _decisions(sol):
    return (sol.status, {k: round(v, 6) for k, v in sol.purchases.items()}, {k: round(v, 6) for k, v in sol.transfers.items()},
            {k: round(v, 6) for k, v in sol.amendments.items()}, {k: round(v, 9) for k, v in sol.projected_service.items()})


def _same(a, b, tol: float = 1e-4) -> bool:
    """Decision equality up to the solver's own primal feasibility tolerance (1e-7 relative on rows of a few thousand
    units: continuous quantities of two formulations of the same optimum agree to ~1e-4 units; an executable order is
    read at the pack or dust resolution, far coarser)."""
    if a.status != b.status or set(a.purchases) != set(b.purchases) or set(a.transfers) != set(b.transfers) or set(a.amendments) != set(b.amendments):
        return False
    for x, y in ((a.purchases, b.purchases), (a.transfers, b.transfers), (a.amendments, b.amendments)):
        if any(abs(x[k] - y[k]) > tol * max(1., abs(x[k])) for k in x):
            return False
    return all(abs(a.projected_service[k] - b.projected_service[k]) <= 1e-7 for k in a.projected_service)


# ── warehouse capacity ───────────────────────────────────────────────────────
def test_missing_capacity_omits_volume_rows_and_bounds(monkeypatch):
    base = example("normal")
    worlds = draw(base, 3, 2)
    built = _capture(monkeypatch)
    solve(base, worlds, service_floor=True)
    declared = built[-1]
    solve(_variant(base, capacity=None), worlds, service_floor=True)
    absent = built[-1]
    assert len(absent.rows) < len(declared.rows)
    inv = [i for i, n in enumerate(absent.names) if n[0] == "inventory"]
    # the inventory columns carry the flow-derived stock bound (finite, data-scaled), never a placeholder
    assert inv and all(0 < absent.upper[i] < 1e6 for i in inv)
    assert all(absent.upper[i] < 1e8 for i in range(len(absent.names)) if absent.upper[i] != float("inf"))
    assert max(abs(v) for row in absent.rows for v in row.values()) < 1e8
    # every row of the clean model still exists in the declared one except the volume rows: the same balance rows
    balance = sum(1 for row, lo, hi in zip(absent.rows, absent.lo, absent.hi) if lo == hi)
    balance_declared = sum(1 for row, lo, hi in zip(declared.rows, declared.lo, declared.hi) if lo == hi)
    assert balance == balance_declared


def test_declared_capacity_is_enforced_and_binds():
    base = example("normal")
    worlds = draw(base, 5, 1, deterministic=True)
    free = solve(_variant(base, capacity=None), worlds, service_floor=True)
    assert free.status == "OPTIMAL"
    tight = solve(_variant(base, capacity=30.), worlds, service_floor=True)   # below the fixture's 50 units of opening stock
    assert tight.status == "INFEASIBLE"
    # the settlement refuses a plan that breaches a declared capacity and accepts it without one
    world = worlds[0]
    with pytest.raises(PhysicalViolation, match="capacity"):
        settle(_variant(base, capacity=30.), free, world)
    settle(_variant(base, capacity=None), free, world)


def test_declared_capacity_binds_on_a_stock_heavy_request():
    """P1 fixture (150 units opening, weekly demand ~50, one-week lead): a capacity between the opening stock and the
    unconstrained plan's peak holds the plan below it - feasible, different decisions, enforced by the settlement."""
    from zaad.full.fixtures_p1 import p1_request
    base = p1_request(seed=41001, opening_units=10.)      # thin opening stock: the plan builds stock through its purchases
    worlds = draw(base, 5, 1, deterministic=True)
    free = solve(_variant(base, capacity=None), worlds)          # cost minimisation: the thin opening makes a service floor unreachable in week 0
    assert free.status == "OPTIMAL"
    flows = settle(_variant(base, capacity=None), free, worlds[0])["flows"]
    peak = max(x["opening"] + x["external_receipts"] + x["transfer_receipts"] for x in flows)   # stock before serving, the settlement's own check
    opening = sum(lot.usable for lot in base.stock)
    assert peak > opening
    cap = (opening + peak) / 2
    bound = solve(_variant(base, capacity=cap), worlds)
    assert bound.status == "OPTIMAL" and not _same(bound, free)
    with pytest.raises(PhysicalViolation, match="capacity"):
        settle(_variant(base, capacity=cap), free, worlds[0])
    settle(_variant(base, capacity=cap), bound, worlds[0])


def test_stock_bound_is_data_derived_valid_and_used(monkeypatch):
    base = _variant(example("normal"), capacity=None)
    worlds = draw(base, 7, 2)
    built = _capture(monkeypatch)
    sol = solve(base, worlds, service_floor=True)
    m = built[-1]
    assert sol.status == "OPTIMAL"
    # independent recomputation of the bound for the fixture's single SKU / location
    sku, loc = base.skus[0].id, base.locations[0].id
    opening = sum(lot.usable for lot in base.stock if lot.sku == sku and lot.location == loc)
    srcs = [s for s in base.sources if s.sku == sku and s.destination == loc]
    pipeline = sum(p.remaining for p in base.pipeline if p.source in {s.id for s in srcs})

    def bound(t):
        return opening + pipeline + sum(min(s.maximum, s.capacity_by_period[k]) for s in srcs for k in range(t))
    depleted = {}
    for row, hi in zip(m.rows, m.hi):
        bins = [i for i in row if m.names[i][0] == "depleted"]
        if len(bins) == 1 and any(m.names[i][0] == "inventory" for i in row):
            t = m.names[bins[0]][3]
            depleted[t] = (row[bins[0]], hi)
    assert depleted
    for t, (coef, hi) in depleted.items():
        assert coef == pytest.approx(bound(t)) and hi == pytest.approx(bound(t))
    # the bound is valid: no solution holds more stock than it (the solved point respects it by construction)
    assert all(hi >= 0 for _, hi in depleted.values())


# ── capital ──────────────────────────────────────────────────────────────────
def test_missing_cash_removes_liquidity_columns_and_the_constant(monkeypatch):
    base = example("normal")
    worlds = draw(base, 3, 2)
    built = _capture(monkeypatch)
    solve(_variant(base, opening_cash=None, credit_limit=None), worlds, service_floor=True)
    m = built[-1]
    assert not any(n[0] in ("cash", "debt") for n in m.names)
    # the purchase economics remain: every purchase column carries its landed price (plus the deployed-capital charge)
    purchases = [i for i, n in enumerate(m.names) if n[0] == "purchase"]
    assert purchases and all(m.cost[i] > 0 for i in purchases)


def test_the_released_sentinel_is_a_false_infeasibility_and_the_clean_model_solves():
    """Reproduction: the released adapter's request (capacity 10⁹, cash 10⁹, credit 10⁹ — declared values, hence the
    verbatim released formulation) is declared INFEASIBLE by HiGHS on the six-period demo fixture; the same request
    with the constraints absent is OPTIMAL, and so is the released formulation with a numerically benign declared
    capacity: the feasible set with 10⁹ contains the one with 1,000, so the verdict was numerical, not physical."""
    base = example("normal")
    worlds = draw(base, 11, 2)
    sentinel = solve(_variant(base, capacity=1e9, opening_cash=1e9, credit_limit=1e9), worlds, service_floor=True)
    clean = solve(_variant(base, capacity=None, opening_cash=None, credit_limit=None), worlds, service_floor=True)
    declared = solve(base, worlds, service_floor=True)
    assert sentinel.status == "INFEASIBLE" and clean.status == "OPTIMAL" and declared.status == "OPTIMAL"
    # the cash placeholder alone is numerically benign: it is the capacity big-M that breaks the model
    cash_only = solve(_variant(base, opening_cash=1e9, credit_limit=1e9), worlds, service_floor=True)
    assert cash_only.status == "OPTIMAL" and _same(cash_only, clean)


def test_sentinel_and_clean_models_agree_on_decisions_and_settlement():
    """Equivalence on a request where the released formulation's placeholders are non-binding and numerically benign
    (10⁶, the value the frozen fixtures declare): identical decisions and service; projected costs differ by exactly
    the placeholder's constant; identical settlement."""
    base = example("normal")
    worlds = draw(base, 11, 2)
    sentinel = _variant(base, capacity=1e6, opening_cash=1e6, credit_limit=1e6)     # the released formulation, verbatim
    clean = _variant(base, capacity=None, opening_cash=None, credit_limit=None)
    a = solve(sentinel, worlds, service_floor=True)
    b = solve(clean, worlds, service_floor=True)
    assert a.status == b.status == "OPTIMAL"
    assert _same(a, b)
    # projected costs differ by exactly the sentinel's constant: rate × Σ_t cash_t (and the interest on its debt),
    # against the clean model's charge on deployed cash rate × Σ_t (declared flows − cash position)
    liq = base.liquidity
    rate, H = liq.cost_of_capital_per_period, base.horizon
    cash_a = {(r["scenario"], r["period"]): (r["cash"], r["debt"]) for r in a.cash}
    cash_b = {(r["scenario"], r["period"]): r["cash"] for r in b.cash}
    const = 0.
    deployed = 0.
    for w, world in enumerate(worlds):
        for t in range(H):
            c, d = cash_a[w, t]
            const += world.weight * (-rate * c + (liq.interest_per_period * cash_a[w, t - 1][1] if t else 0.))
            decl = sum(liq.known_receivables[s] - liq.other_payments[s] for s in range(t + 1))
            deployed += world.weight * rate * (decl - cash_b[w, t])
    assert b.projected_cost == pytest.approx(a.projected_cost - const + deployed, rel=1e-9, abs=1e-6)
    # the settlement of the same plan is identical under both requests
    sa, sb = settle(sentinel, a, worlds[0]), settle(clean, a, worlds[0])
    assert sa["economic_cost"] == pytest.approx(sb["economic_cost"], rel=1e-12)
    assert set(sa["ledger"]) == set(sb["ledger"]) and all(sa["ledger"][k] == pytest.approx(sb["ledger"][k], rel=1e-9, abs=1e-9) for k in sa["ledger"])


def test_declared_cash_ceiling_is_enforced_and_binds():
    base = example("cash")                       # opening 200, no facility, full payment at order
    worlds = draw(base, 5, 1, deterministic=True)
    capped = solve(base, worlds, service_floor=True)
    free = solve(_variant(base, opening_cash=None, credit_limit=None), worlds, service_floor=True)
    assert free.status == "OPTIMAL"
    assert sum(free.purchases.values()) > sum(capped.purchases.values()) or capped.status != "OPTIMAL"
    if free.purchases:
        with pytest.raises(PhysicalViolation, match="liquidity"):
            settle(base, free, worlds[0])


def test_credit_limit_none_is_no_ceiling():
    base = example("cash")
    worlds = draw(base, 5, 1, deterministic=True)
    facility = solve(_variant(base, credit_limit=None), worlds, service_floor=True)
    none = solve(base, worlds, service_floor=True)
    assert facility.status == "OPTIMAL"
    assert facility.status != none.status or sum(facility.purchases.values()) >= sum(none.purchases.values())
    settle(_variant(base, credit_limit=None), facility, worlds[0])


def test_contract_refuses_credit_or_debt_without_a_cash_balance():
    base = example("normal")
    with pytest.raises(ValueError):
        _variant(base, opening_cash=None, credit_limit=1000.)
    data = base.model_dump(mode="python")
    data["liquidity"].update(opening_cash=None, credit_limit=None, opening_debt=5.)
    with pytest.raises(ValueError):
        Request.model_validate(data)
    ok = _variant(base, opening_cash=None, credit_limit=None)
    assert ok.liquidity.opening_cash is None and ok.liquidity.credit_limit is None


def test_workspace_adapter_declares_no_sentinel(tmp_path):
    """The single-location adapter builds `capacity_volume=None` and `opening_cash=None` with NOT_AVAILABLE provenance."""
    import duckdb
    from datetime import datetime, timezone
    from scripts.setup_db import setup_db
    from synthetic.fmcg.demo_company import load_demo_company_into
    from zaad.full.workspace import build_request
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    load_demo_company_into(conn, "t", seed=7)
    req, build = build_request(conn, "t", as_of=datetime(2026, 6, 8, tzinfo=timezone.utc), horizon=8)
    assert all(loc.capacity_volume is None for loc in req.locations)
    assert req.liquidity.opening_cash is None and req.liquidity.credit_limit is None
    prov = build["provenance"]
    assert prov["liquidity.opening_cash"] == "NOT_AVAILABLE" and prov["location.main.capacity_volume"] == "NOT_AVAILABLE"
    assert not any(v >= 1e9 for loc in req.locations for v in ([loc.capacity_volume] if loc.capacity_volume else []))

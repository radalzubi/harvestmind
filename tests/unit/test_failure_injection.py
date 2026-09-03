"""Break the dependencies on purpose. Failures must be safe, clear, and
free of secrets; nothing may be corrupted on the way down."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import api.main as api_main


def test_ready_reports_database_unavailable_without_leaking_path(monkeypatch, tmp_path):
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "does" / "not" / "exist.duckdb"))
    r = TestClient(api_main.app).get("/ready")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "not_ready" and body["database"].startswith("unavailable")
    assert str(tmp_path) not in r.text


def test_solver_unavailable_is_a_status_not_a_crash():
    import pyomo.environ as pyo
    from optimization.solve_status import run_solver
    m = pyo.ConcreteModel()
    m.x = pyo.Var(bounds=(0, 1))
    m.o = pyo.Objective(expr=m.x)
    out = run_solver(m, solver="definitely_not_installed_solver")
    assert out.status == "error" and not out.usable and out.warnings


def test_real_llm_flag_without_key_fails_loudly(monkeypatch):
    import importlib
    import config.llm_config as cfg          # import first, under the safe default
    monkeypatch.setenv("USE_REAL_LLM", "true")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # The module checks at import as well as on demand; either must refuse.
    with pytest.raises(EnvironmentError):
        importlib.reload(cfg)
        cfg.check_real_llm_config()
    monkeypatch.setenv("USE_REAL_LLM", "false")
    importlib.reload(cfg)


def test_bad_api_key_is_401_not_500(tmp_path, monkeypatch):
    import infrastructure.operator_registry as orm
    monkeypatch.setattr(orm, "DEFAULT_DATA_ROOT", tmp_path / "data")
    orm.OperatorRegistry(data_root=tmp_path / "data")
    monkeypatch.setenv("HARVESTMIND_AUTH_REQUIRED", "true")
    r = TestClient(api_main.app).get("/data/products", headers={"X-API-Key": "garbage"})
    assert r.status_code == 401 and "Traceback" not in r.text


def test_empty_dataset_optimizer_returns_cleanly():
    import pandas as pd
    from optimization.multi_period_sp import MultiPeriodStochasticLP
    scen = pd.DataFrame([{"scenario_index": 0, "scenario_weight": 1.0, "product_id": "A",
                          "period": t, "demand_kg": 0.0} for t in range(3)])
    sup = pd.DataFrame([{"supplier_id": "S", "product_id": "A", "capacity_kg": 0.0, "price_per_kg": 1.0}])
    r = MultiPeriodStochasticLP(n_periods=3, spot_capacity_factor=0.0, spot_cost_multiplier=1.0,
                                waste_cost_by_product={"A": 1.0}, unmet_cost_by_product={"A": 1.0},
                                holding_cost_by_product={"A": 0.01}, decay_rate_by_product={"A": 0.0}
                                ).solve(scen, sup, lead_times={(0, "S"): 1})
    assert r["usable"] and r["objective"] == pytest.approx(0.0, abs=1e-9)
    assert all(v == 0.0 for v in r["x"].values())


def test_external_download_failure_is_reported_not_swallowed(monkeypatch):
    import subprocess
    from scripts import fetch_real_data as frd
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 7, "", "boom"))
    with pytest.raises(RuntimeError):
        frd._curl("https://example.invalid/x")

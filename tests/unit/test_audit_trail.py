import json

import pandas as pd

from optimization.audit_trail import record_run


def test_record_is_reproducible_and_free_of_customer_data(tmp_path):
    df = pd.DataFrame({"product_id": ["A"], "demand_kg": [123.4], "customer": ["ACME Foods"]})
    res = {"status": "optimal", "usable": True, "objective": 12.5, "gap": 0.0, "runtime_s": 0.01,
           "warnings": []}
    rec = record_run(domain="fmcg", config={"n_periods": 12}, inputs={"demand": df}, result=res,
                     operator_id="op_x", seed=7, scenario_config={"n": 30},
                     objective_breakdown={"holding": 10.0, "shortage": 2.5}, data_root=tmp_path)
    path = tmp_path / "runs" / f"{rec.run_id}.json"
    assert path.exists()
    body = json.loads(path.read_text())
    assert body["input_hashes"]["demand"] == rec.input_hashes["demand"]
    assert "ACME" not in path.read_text()
    assert body["seed"] == 7 and body["status"] == "optimal"
    rec2 = record_run(domain="fmcg", config={"n_periods": 12}, inputs={"demand": df.copy()}, result=res,
                      data_root=tmp_path)
    assert rec2.input_hashes["demand"] == rec.input_hashes["demand"]

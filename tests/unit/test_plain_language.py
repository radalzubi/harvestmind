from adaptive.plain_language import explain_state, plain_reason, plain_trigger, state_summary_text

STATE = {
    "mode": "EFFICIENCY",
    "portfolio": {"probabilities": {"WATCH": .52, "NORMAL": .33, "CALM": .05, "PORT_DISRUPTION": .02, "DEMAND_VOLATILE": .02},
                  "dominant": "WATCH", "stress": .20, "data_quality": .93,
                  "reasons": ["SKU-0126: demand CV 1.15, zero-share 50%"]},
    "posture": {"commit_window": 3, "cvar_lambda": .28, "scenario_width": .95, "autonomy": .24, "candidates": ["order_up_to", "adaptive_sp"]},
    "outlooks": {"aqaba": {"risk": .64, "quality": .96, "missing": [],
                           "reasons": ["Bab el-Mandeb Strait transits at 77% of their trailing norm", "gscpi elevated (1.06)", "fuel_index elevated (1.31)"]}},
    "replan_triggers": ["portfolio p(disruptive) crosses 0.60 (enter)", "inventory discrepancy above 10%", "something new"],
}


def test_every_number_survives_and_no_jargon_leaks():
    p = explain_state(STATE)
    assert "52%" in p["regime"] and "0.20" in p["regime"] and "0.93" in p["regime"]
    assert "3 weeks" in p["posture"][0] and "0.28" in p["posture"][1] and "0.24" in p["posture"][3]
    assert "state-aware optimizer" in p["posture"][4] and "adaptive_sp" not in p["posture"][4]
    lane = p["lanes"][0]
    assert lane["lane"] == "Aqaba (sea)" and "64%" in lane["sentence"] and "0.96" in lane["sentence"]
    assert lane["reasons"][0] == "Ships passing the Bab el-Mandeb Strait are at 77% of their usual number."
    assert lane["reasons"][2] == "Fuel prices are 31% above their trailing norm."
    assert p["triggers"][0].startswith("The chance that your suppliers or lanes are disrupted rises above 60%")
    assert p["triggers"][2] == "something new"          # unknown triggers pass through untouched
    assert "Aqaba" in p["headline"]
    text = state_summary_text(p)
    assert "cvar" not in text.lower() and "incumbent" not in text.lower()


def test_reason_rewrites_keep_numbers():
    assert "1.15" in plain_reason("SKU-0126: demand CV 1.15, zero-share 50%")
    assert plain_reason("unknown text") == "unknown text"
    assert plain_trigger("demand level shift beyond 2 sd on any SKU (CUSUM)").startswith("Demand for any SKU moves more than 2")

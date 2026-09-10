"""FMCG purchase plan: whole-lot orders with the reasons, from staged exports."""
from __future__ import annotations

import os

import pandas as pd
import requests
import streamlit as st

API = os.getenv("HARVESTMIND_API_URL", "http://localhost:8000")

st.title("FMCG purchase plan")
st.caption("Shelf-stable distribution: whole cases and pallets, MOQ, fill and lead-time risk. "
           "The plan is a recommendation on your uploaded history, not a realised saving.")

token = st.text_input("Operator API token", type="password",
                      value=st.session_state.get("fmcg_token", ""))
if token:
    st.session_state["fmcg_token"] = token
headers = {"Authorization": f"Bearer {token}"} if token else {}

with st.expander("1. Upload exports (CSV, eaches)", expanded=False):
    table = st.selectbox("Table", ["stg_fmcg_skus", "stg_fmcg_orders", "stg_fmcg_purchase_orders",
                                   "stg_fmcg_receipts", "stg_fmcg_inventory", "stg_fmcg_promotions"])
    up = st.file_uploader("CSV file", type=["csv"])
    if up is not None and st.button("Upload"):
        r = requests.post(f"{API}/intake/upload/{table}", headers=headers,
                          files={"file": (up.name, up.getvalue(), "text/csv")}, timeout=120)
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if r.status_code == 200 and body.get("rows_inserted"):
            st.success(f"{body['rows_inserted']} rows loaded")
        else:
            st.error("Not loaded")
        for w in body.get("warnings", []):
            st.warning(w)
        for e in body.get("errors", []):
            st.error(e)

try:
    status = requests.get(f"{API}/fmcg/status", headers=headers, timeout=30).json()
    st.write({k: v for k, v in status.get("tables", {}).items()})
    ready = status.get("ready_to_plan", False)
except Exception:  # noqa: BLE001
    st.error("API not reachable")
    ready = False

st.subheader("2. Plan")
c1, c2, c3, c4 = st.columns(4)
mode = c1.selectbox("Mode", ["selected", "stochastic", "deterministic", "order_up_to"])
horizon = c2.number_input("Horizon (weeks)", 4, 26, 12)
service = c3.slider("Service target", 0.80, 0.995, 0.97, 0.005)
holding = c4.number_input("Holding %/week of cost", 0.0, 10.0, 0.46, 0.01) / 100
currency = st.text_input("Currency", "USD", max_chars=3)

if st.button("Build plan", disabled=not ready):
    with st.spinner("Solving"):
        r = requests.post(f"{API}/fmcg/plan", headers=headers, timeout=600,
                          params={"mode": mode, "horizon_weeks": int(horizon), "service_level": service,
                                  "holding_rate_per_week": holding, "currency": currency.upper()})
    if r.status_code != 200:
        st.error(f"Plan not produced (HTTP {r.status_code}). Quote request id "
                 f"{r.headers.get('X-Request-ID', '?')} to support.")
    else:
        plan = r.json()
        st.success(f"Mode run: {plan['mode_run']}  ·  solver: {plan['solver_status']}  ·  "
                   f"run {plan['run_id']}")
        if plan.get("selection_backtest_costs"):
            st.caption("Trailing-history backtest costs by candidate (lower won): "
                       + ", ".join(f"{k}: {v['amount']} {v['currency']}"
                                   for k, v in plan["selection_backtest_costs"].items()))
        df = pd.DataFrame([{"SKU": o["sku"], "Supplier": o["supplier_id"], "Week": o["week_offset"],
                            "Units": o["order_units"], "Lots": o["lots"], "Lot": o["lot_unit"],
                            "Value": f"{o['purchase_value']['amount']} {o['purchase_value']['currency']}"}
                           for o in plan["orders"]])
        st.dataframe(df, use_container_width=True)
        st.metric("Purchase value", f"{plan['purchase_value']['amount']} {plan['purchase_value']['currency']}")
        for o in plan["orders"][:25]:
            with st.expander(f"Why {o['order_units']:,.0f} of {o['sku']} in week {o['week_offset']}"):
                for line in o["explanation"]:
                    st.write("- " + line)
        for w in plan.get("warnings", []):
            st.warning(w)
        st.download_button("Export plan (CSV)", df.to_csv(index=False), "fmcg_plan.csv")

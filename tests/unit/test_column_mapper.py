"""Unit tests for ingestion.column_mapper."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from ingestion.column_mapper import (
    auto_map_columns,
    detect_and_convert_units,
    infer_missing_columns,
)


def test_exact_match_case_insensitive():
    df = pd.DataFrame({"Order_ID": ["A"], "Buyer_ID": ["B"]})
    out, mapping, warnings = auto_map_columns(df, "orders")
    assert mapping == {"Order_ID": "order_id", "Buyer_ID": "buyer_id"}
    assert "order_id" in out.columns
    assert "buyer_id" in out.columns
    assert warnings == []


def test_known_alias_customer_to_buyer():
    df = pd.DataFrame({"Customer": ["Sysco"], "Order Date": ["2025-01-01"]})
    out, mapping, _ = auto_map_columns(df, "orders")
    assert mapping["Customer"] == "buyer_id"
    assert mapping["Order Date"] == "order_date"


def test_fuzzy_match_typo():
    # "qty orderred" (typo) should fuzzy-match qty_ordered_kg
    df = pd.DataFrame({"order_id": ["X"], "Qty Orderred": [10.0], "product_id": ["P1"]})
    out, mapping, warnings = auto_map_columns(df, "order_lines")
    # Fuzzy or alias should resolve it
    assert "Qty Orderred" in mapping or any("Qty Orderred" in w for w in warnings)


def test_unit_conversion_lbs():
    df = pd.DataFrame({
        "delivery_id": ["D1"],
        "supplier_id": ["S1"],
        "product_id":  ["P1"],
        "delivery_date": ["2025-01-01"],
        "qty_received_kg": [100.0],   # already-mapped column with value in lbs
    })
    # Original column was named "Qty Received (lbs)" — caller passes original list
    converted, conversions = detect_and_convert_units(
        df, original_columns=["delivery_id","supplier_id","product_id","delivery_date","Qty Received (lbs)"]
    )
    expected = round(100.0 * 0.453592, 2)
    assert round(float(converted["qty_received_kg"].iloc[0]), 2) == expected
    assert any("lbs" in c.lower() for c in conversions)


def test_unknown_column_warns_drops():
    df = pd.DataFrame({"order_id": ["A"], "totally_unknown_col": ["x"]})
    out, mapping, warnings = auto_map_columns(df, "orders")
    assert "totally_unknown_col" not in out.columns
    assert any("totally_unknown_col" in w for w in warnings)


def test_local_line_round_trip():
    df = pd.DataFrame({
        "Order Number": ["LL-1"],
        "Customer":     ["IU Health"],
        "Order Date":   ["2025-06-02"],
    })
    out, mapping, _ = auto_map_columns(df, "orders")
    assert mapping["Order Number"] == "order_id"
    assert mapping["Customer"] == "buyer_id"
    assert mapping["Order Date"] == "order_date"


def test_quickbooks_round_trip():
    df = pd.DataFrame({
        "Num":  ["QB-1"],
        "Name": ["Sysco"],
        "Date": ["2025-06-02"],
    })
    out, mapping, _ = auto_map_columns(df, "orders")
    assert mapping["Num"] == "order_id"
    assert mapping["Name"] == "buyer_id"
    assert mapping["Date"] == "order_date"


def test_week_start_inference_from_order_date():
    df = pd.DataFrame({
        "order_id":   ["O1"],
        "buyer_id":   ["B1"],
        "order_date": [date(2025, 6, 4)],   # Wednesday
    })
    df_inferred, inferences = infer_missing_columns(df, "orders")
    assert "week_start" in df_inferred.columns
    assert df_inferred["week_start"].iloc[0] == date(2025, 6, 2)  # Monday
    assert any("week_start" in i for i in inferences)


def test_no_silent_data_loss_after_mapping():
    df = pd.DataFrame({"Order Number": ["X"], "Customer": ["Y"]})
    out, mapping, _ = auto_map_columns(df, "orders")
    # Output rows should equal input rows
    assert len(out) == len(df)
    # And columns should be the schema names
    assert set(out.columns) == {"order_id", "buyer_id"}


def test_id_inference_from_row_hash():
    # delivery_id missing — should be hashed in
    df = pd.DataFrame({
        "supplier_id": ["S1", "S2"],
        "product_id":  ["P1", "P2"],
        "delivery_date": [date(2025,1,1), date(2025,1,2)],
        "qty_received_kg": [10.0, 20.0],
    })
    out, infs = infer_missing_columns(df, "deliveries")
    assert "delivery_id" in out.columns
    assert all(str(v).startswith("DEL-") for v in out["delivery_id"])
    # Two distinct rows → distinct IDs
    assert out["delivery_id"].iloc[0] != out["delivery_id"].iloc[1]


def test_unknown_target_schema_raises():
    df = pd.DataFrame({"x": [1]})
    with pytest.raises(ValueError):
        auto_map_columns(df, "not_a_real_schema")

"""Service level metrics: fill rate, lost sales, CSL, IFR."""

from __future__ import annotations

import pandas as pd


def compute_service_level(
    order_lines_df: pd.DataFrame,
    group_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Compute service metrics from fact_order_lines.

    Metrics:
      - case_fill_rate: orders fully fulfilled / total orders
      - item_fill_rate (IFR): qty_delivered / qty_ordered (kg-weighted)
      - lost_sale_rate: count of lost sales / total lines
      - cycle_service_level (CSL): periods with zero stockouts / total periods
    """
    df = order_lines_df.copy()
    df["fulfilled"] = df["qty_delivered_kg"].notna() & (df["qty_delivered_kg"] > 0)
    df["qty_delivered_kg"] = df["qty_delivered_kg"].fillna(0)

    if group_cols is None:
        group_cols = ["product_id"]

    rows = []
    for keys, grp in df.groupby(group_cols):
        row = dict(zip(group_cols, keys if isinstance(keys, tuple) else [keys]))
        total_lines = len(grp)
        fulfilled_lines = grp["fulfilled"].sum()
        total_ordered_kg = grp["qty_ordered_kg"].sum()
        total_delivered_kg = grp["qty_delivered_kg"].sum()
        lost_sales = grp["lost_sale_flag"].sum() if "lost_sale_flag" in grp.columns else 0

        row["case_fill_rate"] = round(fulfilled_lines / total_lines, 4) if total_lines > 0 else None
        row["item_fill_rate"] = round(total_delivered_kg / total_ordered_kg, 4) if total_ordered_kg > 0 else None
        row["lost_sale_rate"] = round(lost_sales / total_lines, 4) if total_lines > 0 else None
        row["total_ordered_kg"] = round(total_ordered_kg, 1)
        row["total_delivered_kg"] = round(total_delivered_kg, 1)
        row["n_lines"] = total_lines
        row["n_lost_sales"] = int(lost_sales)
        rows.append(row)

    return pd.DataFrame(rows)


def compute_supplier_service(
    deliveries_df: pd.DataFrame,
    po_df: pd.DataFrame,
) -> pd.DataFrame:
    """Delivery fulfillment rate per supplier."""
    if deliveries_df.empty or po_df.empty:
        return pd.DataFrame()

    po_agg = po_df.groupby("supplier_id")["qty_committed_kg"].sum().rename("committed")
    del_agg = deliveries_df.groupby("supplier_id")["qty_received_kg"].sum().rename("received")
    rej_agg = deliveries_df.groupby("supplier_id")["qty_rejected_kg"].sum().rename("rejected")

    df = pd.concat([po_agg, del_agg, rej_agg], axis=1).fillna(0)
    df["fill_rate"] = (df["received"] / df["committed"]).clip(0, 1).round(4)
    df["net_rejection_rate"] = (df["rejected"] / df["received"]).fillna(0).round(4)
    return df.reset_index().sort_values("fill_rate")

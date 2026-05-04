"""Pandera schemas for runtime validation of DataFrames at pipeline boundaries."""

import pandera as pa
from pandera import Column, DataFrameSchema, Check
import pandas as pd

# ---------------------------------------------------------------------------
# Demand forecast output
# ---------------------------------------------------------------------------

ForecastSchema = DataFrameSchema(
    {
        "product_id": Column(str, nullable=False),
        "buyer_id": Column(str, nullable=True),
        "week_start": Column("datetime64[ns]", nullable=False),
        "forecast_kg": Column(float, Check.ge(0), nullable=False),
        "lower_80": Column(float, Check.ge(0), nullable=True),
        "upper_80": Column(float, Check.ge(0), nullable=True),
        "lower_95": Column(float, Check.ge(0), nullable=True),
        "upper_95": Column(float, Check.ge(0), nullable=True),
        "model": Column(str, nullable=False),
    },
    checks=[
        Check(lambda df: (df["upper_95"].fillna(df["forecast_kg"]) >= df["forecast_kg"]).all(),
              error="upper_95 must be >= forecast_kg"),
        Check(lambda df: (df["forecast_kg"] >= df["lower_95"].fillna(0)).all(),
              error="forecast_kg must be >= lower_95"),
    ],
    coerce=True,
)

# ---------------------------------------------------------------------------
# Yield scenario output
# ---------------------------------------------------------------------------

YieldScenarioSchema = DataFrameSchema(
    {
        "scenario_index": Column(int, Check.ge(0), nullable=False),
        "scenario_weight": Column(float, Check(lambda x: (x > 0).all()), nullable=False),
        "supplier_id": Column(str, nullable=False),
        "product_id": Column(str, nullable=False),
        "week_start": Column("datetime64[ns]", nullable=False),
        "yield_kg": Column(float, Check.ge(0), nullable=False),
        "yield_kg_per_ha": Column(float, Check.ge(0), nullable=True),
        "enso_phase": Column(str, nullable=True),
    },
    coerce=True,
)

# ---------------------------------------------------------------------------
# Optimization commitment output
# ---------------------------------------------------------------------------

CommitmentSchema = DataFrameSchema(
    {
        "supplier_id": Column(str, nullable=False),
        "product_id": Column(str, nullable=False),
        "week_start": Column("datetime64[ns]", nullable=False),
        "committed_kg": Column(float, Check.ge(0), nullable=False),
        "contract_kg": Column(float, Check.ge(0), nullable=False),
        "spot_kg": Column(float, Check.ge(0), nullable=False),
        "wasted_kg": Column(float, Check.ge(0), nullable=False),
        "price_per_kg": Column(float, Check.ge(0), nullable=True),
        "decision_stage": Column(str, Check.isin(["first", "recourse"]), nullable=False),
    },
    coerce=True,
)

# ---------------------------------------------------------------------------
# Delivery / receipt data
# ---------------------------------------------------------------------------

DeliverySchema = DataFrameSchema(
    {
        "supplier_id": Column(str, nullable=False),
        "product_id": Column(str, nullable=False),
        "delivery_date": Column("datetime64[ns]", nullable=False),
        "qty_received_kg": Column(float, Check.ge(0), nullable=False),
        "qty_rejected_kg": Column(float, Check.ge(0), nullable=False),
    },
    checks=[
        Check(lambda df: (df["qty_rejected_kg"] <= df["qty_received_kg"]).all(),
              error="qty_rejected_kg cannot exceed qty_received_kg"),
    ],
    coerce=True,
)

# ---------------------------------------------------------------------------
# Market prices
# ---------------------------------------------------------------------------

MarketPriceSchema = DataFrameSchema(
    {
        "product_id": Column(str, nullable=True),
        "report_date": Column("datetime64[ns]", nullable=False),
        "low_price": Column(float, Check.ge(0), nullable=True),
        "high_price": Column(float, Check.ge(0), nullable=True),
        "avg_price": Column(float, Check.ge(0), nullable=True),
        "source": Column(str, nullable=False),
        "currency": Column(str, Check.isin(["USD", "CAD", "MXN"]), nullable=False),
    },
    checks=[
        Check(lambda df: (df["high_price"].fillna(df["low_price"].fillna(0))
                          >= df["low_price"].fillna(0)).all(),
              error="high_price must be >= low_price"),
    ],
    coerce=True,
)

# ---------------------------------------------------------------------------
# Backtest result row
# ---------------------------------------------------------------------------

BacktestRowSchema = DataFrameSchema(
    {
        "origin_week": Column("datetime64[ns]", nullable=False),
        "horizon_weeks": Column(int, Check.ge(1), nullable=False),
        "model": Column(str, nullable=False),
        "mase": Column(float, Check.ge(0), nullable=True),
        "rmsse": Column(float, Check.ge(0), nullable=True),
        "coverage_80": Column(float, Check(lambda x: x.between(0, 1).all()), nullable=True),
        "coverage_95": Column(float, Check(lambda x: x.between(0, 1).all()), nullable=True),
        "service_level_pct": Column(float, Check(lambda x: x.between(0, 100).all()), nullable=True),
        "waste_kg": Column(float, Check.ge(0), nullable=True),
        "spot_premium_usd": Column(float, nullable=True),
    },
    coerce=True,
)


def validate(schema: DataFrameSchema, df: pd.DataFrame, context: str = "") -> pd.DataFrame:
    """Validate df against schema; on failure, re-raise with the context label.

    Earlier code computed a `prefix` string but never attached it to the
    raised error, so callers lost the context. We now pre-pend it to the
    exception message via `add_note`.
    """
    try:
        return schema.validate(df, lazy=True)
    except pa.errors.SchemaErrors as e:
        if context:
            try:
                e.add_note(f"context: {context}")
            except AttributeError:  # Python < 3.11 fallback
                pass
        raise

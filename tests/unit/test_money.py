from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from domain.money import Money, money_breakdown


def test_quantises_to_minor_unit_and_reconciles():
    b = money_breakdown({"holding": 10.005, "shortage": 2.004999, "disposal": 0.0}, "USD")
    assert b["holding"]["amount"] == "10.00"      # half-even
    assert b["shortage"]["amount"] == "2.00"
    assert Decimal(b["total"]["amount"]) == sum(Decimal(b[k]["amount"]) for k in ("holding", "shortage", "disposal"))


def test_three_decimal_currencies():
    assert Money.of(1.2345, "JOD").amount == Decimal("1.234")
    assert Money.of(1.5, "JPY").amount == Decimal("2")


def test_cross_currency_refused_and_explicit_conversion_works():
    with pytest.raises(ValueError):
        Money.of(1, "USD") + Money.of(1, "JOD")
    assert (Money.of(10, "USD").convert("0.709", "JOD")).amount == Decimal("7.090")


def test_rejects_garbage():
    for bad in (float("nan"), float("inf"), "abc"):
        with pytest.raises(ValueError):
            Money.of(bad, "USD")
    with pytest.raises(ValueError):
        Money.of(1, "usd")


@settings(max_examples=300, deadline=None)
@given(st.lists(st.floats(min_value=-1e7, max_value=1e7, allow_nan=False, allow_infinity=False), min_size=1, max_size=8))
def test_total_always_equals_sum_of_quantised_parts(vals):
    comps = {f"c{i}": v for i, v in enumerate(vals)}
    b = money_breakdown(comps, "USD")
    assert Decimal(b["total"]["amount"]) == sum(Decimal(b[k]["amount"]) for k in comps)
    assert all(Decimal(b[k]["amount"]).as_tuple().exponent == -2 for k in b)

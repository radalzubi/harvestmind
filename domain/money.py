"""Decimal money for anything a person will reconcile.

The solver works in floats and must; a linear program does not know what
a cent is. Everything that leaves the engine as a cost, a saving, a
penalty or an inventory value passes through ``Money`` at the boundary:
a Decimal quantised to the currency's minor unit, tagged with its
currency, refusing to be added to another currency without an explicit
rate. Float never reaches a report or an invoice.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

_MINOR_UNITS = {"JOD": 3, "KWD": 3, "BHD": 3, "OMR": 3, "JPY": 0, "KRW": 0}


def _quantum(currency: str) -> Decimal:
    return Decimal(1).scaleb(-_MINOR_UNITS.get(currency, 2))


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if not (isinstance(self.currency, str) and len(self.currency) == 3
                and self.currency.isalpha() and self.currency.isupper()):
            raise ValueError(f"currency must be a 3-letter ISO code, got {self.currency!r}")
        try:
            amt = Decimal(str(self.amount)) if not isinstance(self.amount, Decimal) else self.amount
        except InvalidOperation as exc:
            raise ValueError(f"not a money amount: {self.amount!r}") from exc
        if not amt.is_finite():
            raise ValueError(f"money must be finite, got {amt}")
        object.__setattr__(self, "amount", amt.quantize(_quantum(self.currency), rounding=ROUND_HALF_EVEN))

    @classmethod
    def of(cls, value, currency: str) -> "Money":
        """From a float or string at the boundary. Quantises once, here."""
        try:
            amt = Decimal(repr(float(value))) if isinstance(value, float) else Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError(f"not a money amount: {value!r}") from exc
        return cls(amt, currency)

    def _check(self, other: "Money") -> None:
        if not isinstance(other, Money):
            raise TypeError("Money can only combine with Money")
        if other.currency != self.currency:
            raise ValueError(f"cannot combine {self.currency} with {other.currency} "
                             "without an explicit exchange rate")

    def __add__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, k) -> "Money":
        return Money(self.amount * Decimal(str(k)), self.currency)

    __rmul__ = __mul__

    def __neg__(self) -> "Money":
        return Money(-self.amount, self.currency)

    def __bool__(self) -> bool:
        return self.amount != 0

    def convert(self, rate, to_currency: str) -> "Money":
        return Money(self.amount * Decimal(str(rate)), to_currency)

    def to_float(self) -> float:
        return float(self.amount)

    def __str__(self) -> str:
        return f"{self.amount:,} {self.currency}"

    def as_dict(self) -> dict:
        return {"amount": str(self.amount), "currency": self.currency}


def money_breakdown(components: dict, currency: str) -> dict:
    """Float cost components from the engine -> quantised Money with a
    total that reconciles EXACTLY to the sum of the parts (each part is
    quantised, then summed, so no rounding residue hides in the total)."""
    parts = {k: Money.of(v, currency) for k, v in components.items()}
    total = Money(Decimal(0), currency)
    for p in parts.values():
        total = total + p
    out = {k: v.as_dict() for k, v in parts.items()}
    out["total"] = total.as_dict()
    return out

"""P5 fail-closed checks beyond the contract validators: interactive bounds (413 at the API) and
state-level refusals the engine must never work around."""
from __future__ import annotations

from zaad.atp.contracts import INTERACTIVE_LIMITS, Atp
from zaad.atp.state import SupplyState


class AtpRefused(ValueError):
    """A declared P5 input the engine refuses to allocate on (fail closed)."""


def within_interactive_limits(atp: Atp) -> tuple[bool, str]:
    spec = atp.spec
    n_lines = sum(len(o.lines) for o in spec.orders)
    if len(spec.orders) > INTERACTIVE_LIMITS["orders"]:
        return False, f"orders {len(spec.orders)} over the interactive limit {INTERACTIVE_LIMITS['orders']}"
    if n_lines > INTERACTIVE_LIMITS["lines"]:
        return False, f"lines {n_lines} over the interactive limit {INTERACTIVE_LIMITS['lines']}"
    if spec.promise_horizon > INTERACTIVE_LIMITS["promise_horizon"]:
        return False, f"promise horizon {spec.promise_horizon} over the interactive limit {INTERACTIVE_LIMITS['promise_horizon']}"
    if len(spec.service_classes) > INTERACTIVE_LIMITS["service_classes"]:
        return False, f"service classes {len(spec.service_classes)} over the interactive limit {INTERACTIVE_LIMITS['service_classes']}"
    return True, ""


def check_state(req, atp: Atp, state: SupplyState) -> None:
    """Refuse declared states the engine must not reinterpret."""
    for stock in req.stock:
        if stock.reserved > stock.quantity + 1e-9:
            raise AtpRefused(f"atp: stock {stock.id} declares more reserved units than it holds (double reservation attempt)")
        if stock.damaged + stock.quarantined > stock.quantity + 1e-9:
            raise AtpRefused(f"atp: stock {stock.id} declares more damaged / quarantined units than it holds")
    for order in atp.spec.orders:
        for line in order.lines:
            if line.requested_period > state.horizon:
                raise AtpRefused(f"atp: line {line.id} requests delivery beyond the promise horizon")

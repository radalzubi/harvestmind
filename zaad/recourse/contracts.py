"""P4 adaptive recourse: declared recourse specification and the resolved view.

A request without a `recourse` block, or with `enabled` false, reaches no P4 code path: every
frozen P0-P3 semantic is bit-identical. A declared block is validated aggressively (422 at the
API) and capped before any model is built (413 at the API).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import Field, model_validator

from zaad.contracts import Record

Observable = Literal["demand", "receipts"]
Action = Literal["purchase", "transfer"]

MAX_REVIEW_EPOCHS = 2
# Interactive (synchronous /plan) bounds, derived from the measured V1 matrix (P4_PERFORMANCE.md): a
# scenario tree of at most 8 worlds, and never the P3 shared-supplier-order class (12 - 39 s static,
# 33 - 192 s adaptive locally); larger trees and that class go through the asynchronous jobs path,
# itself capped structurally at BATCH_LIMITS.
INTERACTIVE_LIMITS = {"review_epochs": 2, "observables": 2, "actions": 2, "scenarios": 4, "tree_worlds": 8}
BATCH_LIMITS = {"review_epochs": 2, "observables": 2, "actions": 2, "tree_worlds": 16}


def tree_worlds(req) -> int:
    """Worlds of the recourse scenario tree a request would build (0 without enabled recourse)."""
    spec = getattr(req, "recourse", None)
    if spec is None or not spec.enabled:
        return 0
    return int(req.scenarios) * int(spec.continuations) ** len(spec.review_periods)
OBSERVABLES: tuple[str, ...] = ("demand", "receipts")
ACTIONS: tuple[str, ...] = ("purchase", "transfer")


class RecourseSpec(Record):
    """Declared conditionality. `review_periods` are the epochs (period indices) at which the
    declared `actions` may depend on the declared `observables` realised before that period."""
    enabled: bool = False
    review_periods: tuple[int, ...] = Field(default=(), max_length=MAX_REVIEW_EPOCHS)
    observables: tuple[Observable, ...] = ("demand", "receipts")
    actions: tuple[Action, ...] = ("purchase", "transfer")
    # canonicalisation of observable values (explicit, discrete): demand per service per period is
    # quantised to `demand_grid` units; a confirmed fill fraction to `fill_grid`
    demand_grid: float = Field(default=1., gt=0)
    fill_grid: float = Field(default=.05, gt=0, le=1)
    # receipts are confirmed `confirmation_lag` periods after they land (0 = on arrival)
    confirmation_lag: int = Field(default=0, ge=0, le=12)
    # scenario tree: every branch at a review epoch carries this many independent futures that share
    # the branch's observable history exactly (worlds = scenarios x continuations ** epochs)
    continuations: int = Field(default=2, ge=1, le=3)
    # the perfect-information diagnostic (report-only lower bound); one extra solve when true
    perfect_information: bool = True
    provenance: Literal["OPERATOR_DECLARED", "CONFIGURED_ASSUMPTION"] = "OPERATOR_DECLARED"

    @model_validator(mode="after")
    def coherent(self):
        periods = list(self.review_periods)
        if periods != sorted(periods) or len(set(periods)) != len(periods):
            raise ValueError("recourse: review_periods must be strictly increasing without duplicates")
        if any(p < 1 for p in periods):
            raise ValueError("recourse: a review period must be at least 1 (period 0 is the here-and-now commitment)")
        if len(set(self.observables)) != len(self.observables) or len(set(self.actions)) != len(self.actions):
            raise ValueError("recourse: duplicate observable or action")
        if self.enabled and not self.observables:
            raise ValueError("recourse: enabled recourse needs at least one observable")
        if self.enabled and not self.actions:
            raise ValueError("recourse: enabled recourse needs at least one adaptive action")
        return self


@dataclass(frozen=True)
class InformationSet:
    epoch: int
    id: str
    members: tuple[int, ...]        # sorted world indices of the solve's world list
    probability: float              # sum of member weights
    signature: tuple                # canonical observable history through epoch-1


@dataclass(frozen=True)
class Recourse:
    spec: RecourseSpec
    epochs: tuple[int, ...]

    def epoch_for(self, t: int) -> int | None:
        """The latest review epoch at or before period t, or None for a here-and-now period."""
        latest = None
        for e in self.epochs:
            if e <= t:
                latest = e
        return latest

    @property
    def first_epoch(self) -> int | None:
        return self.epochs[0] if self.epochs else None


def resolve(req) -> Recourse | None:
    """The request's recourse view, or None for a frozen request (absent or disabled)."""
    spec = getattr(req, "recourse", None)
    if spec is None or not spec.enabled:
        return None
    return Recourse(spec=spec, epochs=tuple(spec.review_periods))


def validate_request(req) -> None:
    """Request-level checks (pydantic model validator): epochs inside the horizon, actions the
    request can carry, observables the request can produce."""
    spec = req.recourse
    if spec is None:
        return
    if any(p >= req.horizon for p in spec.review_periods):
        raise ValueError("recourse: every review period must lie inside the horizon (at most horizon - 1)")
    if spec.enabled and "transfer" in spec.actions and not any(a.approved for a in req.transfers) and len(req.locations) > 1:
        raise ValueError("recourse: the transfer action needs at least one approved lane")
    if spec.enabled and "purchase" in spec.actions and not any(s.approved for s in req.sources):
        raise ValueError("recourse: the purchase action needs at least one approved source")
    if spec.enabled and "demand" in spec.observables and not req.services:
        raise ValueError("recourse: the demand observable needs at least one service")
    if spec.enabled and "receipts" in spec.observables and not req.sources and not req.pipeline:
        raise ValueError("recourse: the receipts observable needs a source or a pipeline order")

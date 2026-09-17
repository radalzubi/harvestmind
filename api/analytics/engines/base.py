"""The storage-adapter boundary: an engine-neutral physical plan in, rows out.

Nothing above this module names DuckDB. The planner emits a `PhysicalPlan` — the fact to read,
the dimensions to group by (with the route each is reached through), the measures as contract
references, the filters as (dimension, op, values), the time grain and anchor, the bounds — and an
adapter renders it in its own dialect. A second adapter (Postgres, ClickHouse, a customer's
warehouse) implements `StorageAdapter` without any change to Explore, Ask ZAAD, `VisualSpec` or the
metric contracts.

An adapter also reports what it could *not* answer: a dimension the vault cannot carry (orders
without a site) comes back in `blocked` with the reason, so the result says BLOCKED_BY_DATA rather
than silently dropping the breakdown.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from api.analytics.semantic import MetricContract


@dataclass(frozen=True)
class PlanDimension:
    id: str
    route: str
    level: str | None = None       # time grain for the time dimension
    kind: str = "member"


@dataclass(frozen=True)
class PlanFilter:
    dimension_id: str
    route: str
    op: str
    values: tuple[str, ...]


@dataclass(frozen=True)
class PhysicalPlan:
    fact: str
    fact_source: str                       # sql | plan
    metrics: tuple[MetricContract, ...]
    dimensions: tuple[PlanDimension, ...]
    filters: tuple[PlanFilter, ...]
    grain: str | None
    anchor: str
    range_start: str | None
    range_end: str | None
    limit: int
    top_n: dict[str, Any] | None
    sort: tuple[tuple[str, str], ...]
    comparison_lag: int | None
    timeout_s: float
    #: rows supplied by a Python source (plan snapshots) — never recomputed by the engine
    supplied_rows: tuple[dict[str, Any], ...] = ()
    supplied_columns: tuple[str, ...] = ()
    #: contract parameters the adapter must honour
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class EngineResult:
    #: one dict per row: dimension ids → member, metric ids → number | None, plus per-metric
    #: coverage helpers named f"{metric_id}__num" / "__den" / "__n" where the contract needs them
    rows: list[dict[str, Any]]
    #: dimensions the engine could not carry, with the reason word and a sentence
    blocked: dict[str, tuple[str, str]]
    #: whole-result coverage: metric id → {"numerator", "denominator", "n"} over all rows
    coverage: dict[str, dict[str, float | None]]
    executed_ms: float
    truncated: bool = False
    #: the engine's own statement, for the provenance disclosure and for tests (never for the browser)
    statement: str = ""
    #: the last business date represented in the fact (data cutoff)
    data_cutoff: str | None = None
    #: rows for the comparison period, keyed like `rows`, when a comparison was asked for
    comparison_rows: list[dict[str, Any]] | None = None


class StorageAdapter(Protocol):
    name: str

    def execute(self, plan: PhysicalPlan) -> EngineResult: ...

    def members(self, dimension_id: str, *, search: str | None, limit: int) -> list[str]: ...

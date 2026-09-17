"""The typed contracts every surface speaks: the only shapes the browser and the AI may send.

`AnalyticsQuerySpec` is the request; `VisualSpec` is a renderer-independent description of one
visual over one query; `ResultSet` is the answer. Nothing here names a database, a table or a
chart library, and nothing here accepts an expression: measures and dimensions are ids the
semantic registry resolves, values bind as parameters.

Every field is bounded. Limits are clamps a caller can lower, never raise; the error taxonomy is
the architecture's (§5): a refusal names its code so the interface and the AI planner can act on
it rather than parse a sentence.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from api.analytics.semantic import MODEL_VERSION, TIME_GRAINS

MAX_MEASURES = 6
MAX_DIMENSIONS = 3
MAX_FILTERS = 12
MAX_FILTER_VALUES = 200
MAX_LIMIT = 400          # points / rows a single sync query may return
DEFAULT_LIMIT = 400
MAX_TOP_N = 50
MAX_ID_CHARS = 120
MAX_TITLE_CHARS = 160
MAX_TEXT_CHARS = 600
MAX_QUESTION_CHARS = 1000

Purpose = Literal["insights", "explore", "ask", "export", "signal", "dashboard"]
FilterOp = Literal["in", "eq", "ne", "contains", "between", "gte", "lte", "is_null", "not_null"]
VisualType = Literal["kpi", "table", "pivot", "line", "area", "bar", "hbar", "stacked_bar", "scatter", "heatmap"]

ERROR_CODES = ("semantic_unknown_metric", "semantic_unknown_dimension", "semantic_dimension_not_allowed", "semantic_no_join_path",
               "semantic_aggregation_forbidden", "semantic_version_deprecated", "semantic_metric_not_queryable", "semantic_registers_combined",
               "semantic_invalid_filter", "semantic_invalid_time", "permission_denied", "scope_filtered", "limit_exceeded",
               "query_timeout", "query_cancelled", "dataset_unavailable", "engine_unavailable", "spec_invalid")

_ID = re.compile(r"^[A-Za-z0-9 _.:@+\-\/&()'#,]{1,120}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class AnalyticsRefused(ValueError):
    """A request the semantic layer, the permission layer or the engine will not run. Carries a code."""

    def __init__(self, code: str, message: str, detail: dict[str, Any] | None = None):
        assert code in ERROR_CODES, code
        super().__init__(message)
        self.code = code
        self.detail = detail or {}

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), **({"detail": self.detail} if self.detail else {})}


class Measure(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric_id: str = Field(min_length=1, max_length=64)
    version: int | None = Field(default=None, ge=1)
    alias: str | None = Field(default=None, max_length=64)

    @field_validator("metric_id", "alias")
    @classmethod
    def _ident(cls, v: str | None) -> str | None:
        if v is not None and not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", v):
            raise ValueError("an identifier is lower-case letters, digits and underscores")
        return v

    @property
    def ref(self) -> str:
        return f"{self.metric_id}@{self.version}" if self.version else self.metric_id


class DimensionRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dimension_id: str = Field(min_length=1, max_length=64)
    #: for the time dimension: the grain; ignored elsewhere
    level: str | None = Field(default=None, max_length=16)

    @field_validator("dimension_id")
    @classmethod
    def _ident(cls, v: str) -> str:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", v):
            raise ValueError("an identifier is lower-case letters, digits and underscores")
        return v


class TimeRange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: str | None = None
    end: str | None = None
    #: relative window: the last N units ending at the data's last date (or `end`)
    last: int | None = Field(default=None, ge=1, le=520)
    unit: Literal["day", "week", "month", "quarter", "year"] | None = None

    @field_validator("start", "end")
    @classmethod
    def _date(cls, v: str | None) -> str | None:
        if v is not None and not _DATE.match(v):
            raise ValueError("a date is YYYY-MM-DD")
        return v

    @model_validator(mode="after")
    def _order(self) -> "TimeRange":
        if self.start and self.end and self.end < self.start:
            raise ValueError("end is before start")
        if (self.last is None) != (self.unit is None):
            raise ValueError("a relative window names both last and unit")
        return self


class TimeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    grain: Literal["day", "week", "month", "quarter", "year"] | None = None
    range: TimeRange | None = None
    #: which date on the fact anchors the time dimension (the metric's default when absent)
    anchor: str | None = Field(default=None, max_length=32)

    @field_validator("grain")
    @classmethod
    def _grain(cls, v: str | None) -> str | None:
        if v is not None and v not in TIME_GRAINS:
            raise ValueError(f"grain is one of {', '.join(TIME_GRAINS)}")
        return v


class Filter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dimension_id: str = Field(min_length=1, max_length=64)
    op: FilterOp = "in"
    values: list[str] = Field(default_factory=list, max_length=MAX_FILTER_VALUES)

    @field_validator("values")
    @classmethod
    def _values(cls, v: list[str]) -> list[str]:
        for value in v:
            text = str(value)
            if len(text) > MAX_ID_CHARS or not _ID.match(text):
                raise ValueError("a filter value is a bounded identifier or label")
        return [str(x) for x in v]

    @model_validator(mode="after")
    def _arity(self) -> "Filter":
        if self.op in ("is_null", "not_null") and self.values:
            raise ValueError(f"{self.op} takes no values")
        if self.op in ("eq", "ne", "contains", "gte", "lte") and len(self.values) != 1:
            raise ValueError(f"{self.op} takes exactly one value")
        if self.op == "between" and len(self.values) != 2:
            raise ValueError("between takes two values")
        if self.op == "in" and not self.values:
            raise ValueError("in takes at least one value")
        return self


class Sort(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str = Field(min_length=1, max_length=64)
    dir: Literal["asc", "desc"] = "desc"


class TopN(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dimension_id: str = Field(min_length=1, max_length=64)
    n: int = Field(default=10, ge=1, le=MAX_TOP_N)
    #: fold the rest into one "others" member — only for additive measures (validated)
    others: bool = False
    #: the measure the ranking is on; the first measure when absent
    by: str | None = Field(default=None, max_length=64)


class Comparison(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["period_over_period"] = "period_over_period"
    lag: int = Field(default=1, ge=1, le=52)


class Drilldown(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_visual: str | None = Field(default=None, max_length=64)
    dimension_id: str = Field(min_length=1, max_length=64)
    member: str = Field(min_length=1, max_length=MAX_ID_CHARS)


class AnalyticsQuerySpec(BaseModel):
    """The only thing a surface may send. Server-validated against the semantic model on every run."""
    model_config = ConfigDict(extra="forbid")
    semantic_model_version: str = MODEL_VERSION
    measures: list[Measure] = Field(min_length=1, max_length=MAX_MEASURES)
    dimensions: list[DimensionRef] = Field(default_factory=list, max_length=MAX_DIMENSIONS)
    time: TimeSpec | None = None
    filters: list[Filter] = Field(default_factory=list, max_length=MAX_FILTERS)
    comparison: Comparison | None = None
    sort: list[Sort] = Field(default_factory=list, max_length=3)
    limit: int = Field(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)
    top_n: TopN | None = None
    drilldown: Drilldown | None = None
    purpose: Purpose = "explore"

    @model_validator(mode="after")
    def _distinct(self) -> "AnalyticsQuerySpec":
        refs = [m.ref for m in self.measures]
        if len(set(refs)) != len(refs):
            raise ValueError("a measure appears twice")
        dims = [d.dimension_id for d in self.dimensions]
        if len(set(dims)) != len(dims):
            raise ValueError("a dimension appears twice")
        return self

    def canonical(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def spec_hash(self) -> str:
        return hashlib.sha256(json.dumps(self.canonical(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]


class Encoding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: str | None = Field(default=None, max_length=64)
    y: list[str] = Field(default_factory=list, max_length=MAX_MEASURES)
    series: str | None = Field(default=None, max_length=64)
    color: str | None = Field(default=None, max_length=64)
    size: str | None = Field(default=None, max_length=64)
    #: pivot: which dimensions go to rows and which to columns
    rows: list[str] = Field(default_factory=list, max_length=MAX_DIMENSIONS)
    columns: list[str] = Field(default_factory=list, max_length=MAX_DIMENSIONS)


class Formatting(BaseModel):
    model_config = ConfigDict(extra="forbid")
    number_style: Literal["plain", "grouped", "compact"] = "grouped"
    unit_display: bool = True
    decimals: int | None = Field(default=None, ge=0, le=4)
    show_totals: bool = False


class DrillThrough(BaseModel):
    model_config = ConfigDict(extra="forbid")
    surface: Literal["inventory", "orders", "data", "decisions", "diagnostics", "supplier"]
    params_from: list[str] = Field(default_factory=list, max_length=4)


class VisualSpec(BaseModel):
    """One visual over one query, independent of any chart library."""
    model_config = ConfigDict(extra="forbid")
    visual_id: str = Field(default="", max_length=64)
    visual_type: VisualType = "table"
    title: dict[str, str] = Field(default_factory=dict)
    description: dict[str, str] = Field(default_factory=dict)
    query: AnalyticsQuerySpec
    encoding: Encoding = Field(default_factory=Encoding)
    formatting: Formatting = Field(default_factory=Formatting)
    drill_path: list[str] = Field(default_factory=list, max_length=6)
    drill_through: DrillThrough | None = None
    interactions: Literal["emit", "receive", "both", "none"] = "both"
    semantic_model_version: str = MODEL_VERSION
    version: int = Field(default=1, ge=1)

    @field_validator("title", "description")
    @classmethod
    def _text(cls, v: dict[str, str]) -> dict[str, str]:
        out: dict[str, str] = {}
        for k, text in v.items():
            if k not in ("en", "ar"):
                raise ValueError("titles are localised en / ar")
            out[k] = str(text)[:MAX_TEXT_CHARS]
        return out

    @field_validator("visual_id")
    @classmethod
    def _vid(cls, v: str) -> str:
        if v and not re.fullmatch(r"[A-Za-z0-9_\-]{1,64}", v):
            raise ValueError("a visual id is letters, digits, _ and -")
        return v


class DashboardTile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tile_id: str = Field(min_length=1, max_length=64)
    analysis_id: str = Field(min_length=1, max_length=64)
    #: grid position and size in columns (1–3 of 3) and rows
    x: int = Field(default=0, ge=0, le=2)
    y: int = Field(default=0, ge=0, le=200)
    w: int = Field(default=1, ge=1, le=3)
    h: int = Field(default=1, ge=1, le=3)

    @field_validator("tile_id", "analysis_id")
    @classmethod
    def _ident(cls, v: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_\-]{1,64}", v):
            raise ValueError("an id is letters, digits, _ and -")
        return v


class DashboardSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tiles: list[DashboardTile] = Field(default_factory=list, max_length=24)
    #: dashboard-level filters, applied to every tile whose query allows the dimension
    shared_filters: list[Filter] = Field(default_factory=list, max_length=MAX_FILTERS)
    time: TimeSpec | None = None
    semantic_model_version: str = MODEL_VERSION

    @model_validator(mode="after")
    def _unique_tiles(self) -> "DashboardSpec":
        ids = [t.tile_id for t in self.tiles]
        if len(set(ids)) != len(ids):
            raise ValueError("a tile id appears twice")
        return self


class SavedAnalysisIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=MAX_TITLE_CHARS)
    description: str | None = Field(default=None, max_length=MAX_TEXT_CHARS)
    visual: VisualSpec
    visibility: Literal["private", "workspace"] = "private"
    origin: Literal["user", "ask_zaad", "zaad_curated"] = "user"
    #: for AI-created analyses: the validated plan the answer was built from (identifiers only)
    notes: str | None = Field(default=None, max_length=MAX_TEXT_CHARS)


class DashboardIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=MAX_TITLE_CHARS)
    description: str | None = Field(default=None, max_length=MAX_TEXT_CHARS)
    spec: DashboardSpec = Field(default_factory=DashboardSpec)
    visibility: Literal["private", "workspace"] = "private"


class AskIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    locale: Literal["en", "ar"] = "en"
    #: the previous validated spec, so a follow-up modifies rather than restarts
    previous: AnalyticsQuerySpec | None = None
    previous_visual_type: VisualType | None = None
    #: the conversation id the client keeps; stored only as an identifier in the audit row
    conversation_id: str | None = Field(default=None, max_length=64)


class HandoffIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: AnalyticsQuerySpec
    #: what the analysis observed, in the requester's words (bounded; recorded, never sent to a model)
    observed_issue: str = Field(default="", max_length=MAX_TEXT_CHARS)
    skus: list[str] = Field(default_factory=list, max_length=50)
    suppliers: list[str] = Field(default_factory=list, max_length=20)
    locations: list[str] = Field(default_factory=list, max_length=20)
    submit: bool = False

    @field_validator("skus", "suppliers", "locations")
    @classmethod
    def _ids(cls, v: list[str]) -> list[str]:
        for x in v:
            if not _ID.match(str(x)):
                raise ValueError("an identifier is bounded")
        return v

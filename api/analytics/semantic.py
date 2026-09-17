"""The governed semantic layer: the one place a business definition lives.

Machine-readable registries for entities, dimensions, measures (metric contracts), relationships
(the join graph), time grains, coverage rules, null semantics, security classifications and
versions. Insights, Explore, Ask ZAAD, exports and the optimizer hand-off read from here; none of
them defines a KPI of its own, and the AI may only *reference* a `metric_id`.

Three rules the registry enforces by construction:

  * **The aggregation is part of the contract.** A requester picks grain and dimensions, never
    `sum` versus `avg`; a ratio is always a ratio of sums at the requested grain.
  * **A register is a dimension no query may sum across.** The five value measures are separate
    metric ids and are never combinable in one measure list.
  * **Plan-sourced measures are snapshots.** They are read from the stored report and carry the
    plan's identity; the analytics engine never recomputes them.

Every metric is classified against what the vault holds: EXISTS (computed today by a released
module with this exact meaning), DERIVABLE (computable from today's rows under this contract),
REQUIRES_NEW_DATA, FUTURE. Nothing is manufactured for data the vault does not hold: a metric whose
status is not EXISTS or DERIVABLE cannot be queried and says why.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

MODEL_VERSION = "2026.09"

Status = Literal["EXISTS", "DERIVABLE", "REQUIRES_NEW_DATA", "FUTURE"]
Aggregation = Literal["sum", "count", "count_distinct", "ratio_of_sums", "ratio_of_counts", "quantile",
                      "latest_snapshot", "snapshot", "mean"]
EvidenceClass = Literal["OBSERVED_FACT", "ASSOCIATION", "MODELED", "PLAN_SNAPSHOT"]
Classification = Literal["OPERATIONAL", "ECONOMIC", "GOVERNANCE", "RESTRICTED"]
Grain = Literal["day", "week", "month", "quarter", "year"]

TIME_GRAINS: tuple[Grain, ...] = ("day", "week", "month", "quarter", "year")
NULL_REASONS: tuple[str, ...] = ("UNKNOWN", "NOT_MEASURED", "NOT_APPLICABLE", "NO_DATA", "BLOCKED_BY_DATA",
                                 "NOT_IN_PLAN", "INSUFFICIENT_COVERAGE")
VALUE_REGISTERS: tuple[str, ...] = ("MODELED_DIFFERENCE", "BACKTESTED_OPPORTUNITY", "APPROVED_EXPECTED_DIFFERENCE",
                                    "OBSERVED_AFTER_ACTION", "REALIZED_VALUE")
DOMAINS: tuple[str, ...] = ("Demand", "Inventory", "Purchasing", "Suppliers", "Customers", "Service", "Decisions", "Value")

#: Contract parameters that used to be hidden constants. Named here, read from the released modules.
THIN_SAMPLE = 6            # diagnostics.THIN_SAMPLE
SHORT_FILL_TOLERANCE = 0.96  # diagnostics.SHORT_FILL_TOLERANCE
COVER_WEEKS = 12           # catalog._demand_cte default


def _t(en: str, ar: str | None = None) -> dict[str, str]:
    return {"en": en, "ar": ar or en}


# ── entities ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Entity:
    id: str
    label: dict[str, str]
    description: str
    source: str                      # the vault table, or the store the rows come from
    key: tuple[str, ...]
    status: Status = "EXISTS"


ENTITIES: dict[str, Entity] = {e.id: e for e in (
    Entity("product", _t("Product", "المنتج"), "One SKU of the product master (latest import per SKU).", "stg_fmcg_skus", ("sku",)),
    Entity("supplier", _t("Supplier", "المورد"), "One supplier: from the supplier master, or known by id from purchase orders.", "stg_fmcg_suppliers", ("supplier_id",)),
    Entity("customer", _t("Customer", "العميل"), "One customer id on customer order lines (no customer master today).", "stg_fmcg_orders", ("customer_id",)),
    Entity("location", _t("Site", "الموقع"), "One site: a warehouse or branch.", "stg_fmcg_locations", ("location_id",)),
    Entity("customer_order_line", _t("Customer order line", "سطر طلب عميل"), "One order line: what a customer ordered and, where recorded, what was shipped.", "stg_fmcg_orders", ("order_id", "sku")),
    Entity("inventory_snapshot", _t("Inventory snapshot", "لقطة المخزون"), "Stock per product and site on one snapshot date (latest import per key).", "stg_fmcg_inventory", ("snapshot_date", "sku", "location_id")),
    Entity("purchase_order_line", _t("Purchase order line", "سطر أمر شراء"), "One purchase-order line and what has been received against it.", "stg_fmcg_purchase_orders", ("po_id", "sku")),
    Entity("matched_purchase_order", _t("Received purchase order", "أمر شراء مستلَم"), "One purchase order with at least one receipt: the rows supplier performance is measured on.", "stg_fmcg_purchase_orders + stg_fmcg_receipts", ("po_id",)),
    Entity("receipt", _t("Receipt", "سند استلام"), "One receipt line against a purchase order.", "stg_fmcg_receipts", ("receipt_id",)),
    Entity("transfer", _t("Transfer", "تحويل"), "One movement between sites.", "stg_fmcg_transfers", ("transfer_id",), "EXISTS"),
    Entity("lane", _t("Lane", "خط النقل"), "One origin → destination lane.", "stg_fmcg_lanes", ("lane_id",)),
    Entity("plan", _t("Plan", "الخطة"), "One completed workspace plan, read from the job store verbatim.", "job store", ("job_id",)),
    Entity("decision", _t("Decision", "القرار"), "One verdict or action inside a plan (flattened from the report).", "job store", ("job_id", "decision_id"), "DERIVABLE"),
    Entity("decision_response", _t("Decision response", "الرد على القرار"), "What a person did with a decision.", "zaad_decision_responses", ("response_id",)),
    Entity("proposal", _t("Proposal", "المقترح"), "A proposed order and its state.", "zaad_draft_orders", ("draft_id",)),
    Entity("evaluation", _t("Evaluation", "التقييم"), "A proposal's two-run comparison.", "zaad_evaluations", ("evaluation_id",)),
    Entity("outcome", _t("Outcome", "النتيجة"), "An observed result after an action, with an optional stated comparator.", "zaad_outcomes", ("outcome_id",)),
    Entity("upload_session", _t("Upload session", "جلسة رفع"), "One upload of one file (per-row lineage stamps).", "stg_* lineage columns", ("_upload_session_id",)),
    Entity("business_unit", _t("Business unit", "وحدة الأعمال"), "A scoping dimension the vault does not hold yet.", "none", ("business_unit_id",), "REQUIRES_NEW_DATA"),
)}


# ── dimensions ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Dimension:
    id: str
    label: dict[str, str]
    entity: str
    description: str
    kind: Literal["member", "time", "register"] = "member"
    #: for a member dimension: where its value list comes from (a Data-explorer dataset and column)
    members: tuple[str, str] | None = None
    #: the parent in a drill hierarchy (drilling *down* goes from parent to child)
    parent: str | None = None
    status: Status = "EXISTS"
    classification: Classification = "OPERATIONAL"
    #: how the browser can drill *through* to records from a member of this dimension
    drill_through: str | None = None


DIMENSIONS: dict[str, Dimension] = {d.id: d for d in (
    Dimension("sku", _t("SKU", "رمز المنتج"), "product", "The product code.", members=("products", "sku"), parent="category", drill_through="inventory"),
    Dimension("product", _t("Product", "المنتج"), "product", "The product's description (its SKU when none).", members=("products", "sku_name"), parent="category", drill_through="inventory"),
    Dimension("category", _t("Category", "الفئة"), "product", "The product's category.", members=("products", "category")),
    Dimension("sub_category", _t("Sub-category", "الفئة الفرعية"), "product", "The product's sub-category.", members=("products", "sub_category"), parent="category"),
    Dimension("brand", _t("Brand", "العلامة"), "product", "The product's brand.", members=("products", "brand")),
    Dimension("abc_class", _t("ABC class", "تصنيف ABC"), "product", "The product's declared ABC class.", members=("products", "abc_class")),
    Dimension("supplier", _t("Supplier", "المورد"), "supplier", "The supplier id (name from the master where uploaded).", members=("suppliers", "supplier_id"), drill_through="supplier"),
    Dimension("origin", _t("Origin country", "بلد المنشأ"), "supplier", "The supplier's declared origin (ISO3).", members=("suppliers", "origin_iso3"), parent="supplier"),
    Dimension("route", _t("Route", "المسار"), "supplier", "The route the supplier master declares.", members=("suppliers", "route")),
    Dimension("customer", _t("Customer", "العميل"), "customer", "The customer id on the order line.", members=("customer_orders", "customer_id"), drill_through="orders"),
    Dimension("channel", _t("Channel", "القناة"), "customer", "The sales channel on the order line.", members=("customer_orders", "channel")),
    Dimension("location", _t("Site", "الموقع"), "location", "The site on the row (stock site, order site).", members=("inventory", "location_id"), drill_through="inventory"),
    Dimension("destination", _t("Destination site", "موقع الوصول"), "location", "The site a purchase order is delivered to.", members=("purchase_orders", "destination_id")),
    Dimension("po_status", _t("PO status", "حالة أمر الشراء"), "purchase_order_line", "open (no receipt yet), received, or late (open past its expected date).", status="DERIVABLE"),
    Dimension("date", _t("Date", "التاريخ"), "customer_order_line", "The row's date, at the requested grain (day, week, month, quarter, year).", kind="time"),
    Dimension("decision_verb", _t("Decision verb", "فعل القرار"), "decision", "KEEP, DEFER, EXPEDITE, REDUCE, CANCEL, SPLIT, BUY, MOVE.", drill_through="decisions"),
    Dimension("decision_status", _t("Response status", "حالة الرد"), "decision_response", "REVIEWED, ACCEPTED, OVERRIDDEN, REJECTED."),
    Dimension("proposal_state", _t("Proposal state", "حالة المقترح"), "proposal", "DRAFT, READY_FOR_REVIEW, APPROVED, REJECTED, EXPORTED, SUPERSEDED."),
    Dimension("outcome_metric", _t("Outcome metric", "مقياس النتيجة"), "outcome", "The metric an outcome was recorded against."),
    Dimension("value_register", _t("Value register", "سجل القيمة"), "outcome", "Which of the five registers a value belongs to. Never summed across.", kind="register"),
    Dimension("sector", _t("Sector", "القطاع"), "product", "The sector a product declares (COMMERCIAL, PRODUCE, MEAT_SEAFOOD).", members=("products", "sector")),
    Dimension("lane", _t("Lane", "خط النقل"), "lane", "An origin → destination lane.", members=("lanes", "lane_id")),
    Dimension("business_unit", _t("Business unit", "وحدة الأعمال"), "business_unit", "Not in the vault yet.", status="REQUIRES_NEW_DATA"),
)}

#: Drill-down paths: from a dimension (or time level) to the next level down.
DRILL_PATHS: dict[str, str] = {
    "year": "quarter", "quarter": "month", "month": "week", "week": "day",
    "category": "sub_category", "sub_category": "sku", "brand": "sku", "supplier": "sku", "location": "sku", "origin": "supplier", "route": "supplier",
}


# ── relationships (the join graph) ──────────────────────────────────────────

@dataclass(frozen=True)
class Relationship:
    from_entity: str
    to_entity: str
    on: str
    cardinality: str  # many_to_one | one_to_many | one_to_one


RELATIONSHIPS: tuple[Relationship, ...] = (
    Relationship("customer_order_line", "product", "sku", "many_to_one"),
    Relationship("customer_order_line", "customer", "customer_id", "many_to_one"),
    Relationship("customer_order_line", "location", "location_id", "many_to_one"),
    Relationship("inventory_snapshot", "product", "sku", "many_to_one"),
    Relationship("inventory_snapshot", "location", "location_id", "many_to_one"),
    Relationship("purchase_order_line", "product", "sku", "many_to_one"),
    Relationship("purchase_order_line", "supplier", "supplier_id", "many_to_one"),
    Relationship("purchase_order_line", "location", "destination_id", "many_to_one"),
    Relationship("matched_purchase_order", "supplier", "supplier_id", "many_to_one"),
    Relationship("matched_purchase_order", "product", "first_sku (single-line orders only)", "many_to_one"),
    Relationship("receipt", "purchase_order_line", "po_id, sku", "many_to_one"),
    Relationship("product", "supplier", "supplier_id (primary supplier)", "many_to_one"),
    Relationship("transfer", "lane", "lane_id", "many_to_one"),
    Relationship("decision", "plan", "job_id", "many_to_one"),
    Relationship("decision", "product", "sku (via the request's sources)", "many_to_one"),
    Relationship("decision_response", "decision", "decision_id", "many_to_one"),
    Relationship("proposal", "decision", "source_decision_id", "many_to_one"),
    Relationship("evaluation", "proposal", "draft_id", "many_to_one"),
    Relationship("outcome", "proposal", "draft_id", "many_to_one"),
)


# ── facts (logical views the engine can query) ──────────────────────────────

@dataclass(frozen=True)
class Fact:
    """A logical fact the engine can read: which entity a row is, which dimensions it can carry
    and how, and which date anchors the time dimension. The SQL lives in the DuckDB adapter; the
    fact only names what is legal."""
    id: str
    entity: str
    #: dimension id → how the adapter finds it: "product" (via the product master), "supplier"
    #: (via the supplier master), "row" (a column on the fact), "derived"
    dimensions: dict[str, str]
    time_anchor: str
    time_anchors: tuple[str, ...] = ()
    #: python-sourced facts (plan snapshots) are materialised as rows, never recomputed
    source: Literal["sql", "plan"] = "sql"


FACTS: dict[str, Fact] = {f.id: f for f in (
    Fact("customer_order_line", "customer_order_line",
         {"sku": "row", "product": "product", "category": "product", "sub_category": "product", "brand": "product", "abc_class": "product",
          "sector": "product", "supplier": "product", "customer": "row", "channel": "row", "location": "row", "date": "row"},
         "order_date", ("order_date", "requested_delivery_date")),
    Fact("inventory_snapshot", "inventory_snapshot",
         {"sku": "row", "product": "product", "category": "product", "sub_category": "product", "brand": "product", "abc_class": "product",
          "sector": "product", "supplier": "product", "location": "row", "date": "row"},
         "snapshot_date"),
    Fact("purchase_order_line", "purchase_order_line",
         {"sku": "row", "product": "product", "category": "product", "sub_category": "product", "brand": "product", "abc_class": "product",
          "sector": "product", "supplier": "row", "origin": "supplier", "route": "supplier", "destination": "row", "po_status": "derived", "date": "row"},
         "po_date", ("po_date", "eta")),
    Fact("matched_purchase_order", "matched_purchase_order",
         {"supplier": "row", "origin": "supplier", "route": "supplier", "sku": "row", "product": "product", "category": "product", "brand": "product",
          "sector": "product", "date": "row"},
         "po_date", ("po_date", "first_receipt")),
    Fact("receipt", "receipt", {"sku": "row", "product": "product", "category": "product", "brand": "product", "supplier": "row", "date": "row"},
         "receipt_date"),
    Fact("decision", "decision", {"decision_verb": "row", "sku": "row", "supplier": "row"}, "", source="plan"),
    Fact("decision_response", "decision_response", {"decision_status": "row", "date": "row"}, "created_at"),
    Fact("proposal", "proposal", {"proposal_state": "row", "supplier": "row", "date": "row"}, "updated_at"),
    Fact("outcome", "outcome", {"outcome_metric": "row", "value_register": "derived", "date": "row"}, "observed_at"),
    Fact("plan_value", "plan", {"value_register": "derived"}, "", source="plan"),
)}


# ── metric contracts ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Coverage:
    measure: str                    # what coverage means, in words
    insufficient_below: float | None = None
    thin_sample_below: int | None = None


@dataclass(frozen=True)
class MetricContract:
    metric_id: str
    version: int
    display_name: dict[str, str]
    description: dict[str, str]
    business_definition: str
    source_entities: tuple[str, ...]
    fact: str
    aggregation_rule: Aggregation
    allowed_dimensions: tuple[str, ...]
    required_fields: tuple[str, ...]
    coverage_rule: Coverage
    null_behavior: dict[str, str]
    unit: str                         # units | lines | orders | ratio | days | money | count
    currency_behavior: str            # none | workspace_currency
    grain: str                        # the row the measure is defined on
    evidence_class: EvidenceClass
    security_classification: Classification
    domain: str
    numerator: str
    denominator: str
    status: Status = "EXISTS"
    disallowed_dimensions: tuple[str, ...] = ()
    #: whether summing the measure over rows/periods is meaningful (totals, stacked bars, "others")
    additive: bool = True
    register: str | None = None
    time_anchor: str | None = None
    lineage: tuple[str, ...] = ()
    owner: str = "ZAAD product"
    compat_since: str = MODEL_VERSION
    deprecates: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    #: where a released module computes the same number today
    implemented_today: str = ""

    @property
    def ref(self) -> str:
        return f"{self.metric_id}@{self.version}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id, "version": self.version, "ref": self.ref, "display_name": self.display_name,
            "description": self.description, "business_definition": self.business_definition,
            "numerator": self.numerator, "denominator": self.denominator, "source_entities": list(self.source_entities),
            "fact": self.fact, "aggregation_rule": self.aggregation_rule, "allowed_dimensions": list(self.allowed_dimensions),
            "disallowed_dimensions": list(self.disallowed_dimensions), "required_fields": list(self.required_fields),
            "coverage_rule": {"measure": self.coverage_rule.measure, "insufficient_below": self.coverage_rule.insufficient_below,
                              "thin_sample_below": self.coverage_rule.thin_sample_below},
            "null_behavior": dict(self.null_behavior), "unit": self.unit, "currency_behavior": self.currency_behavior,
            "grain": self.grain, "evidence_class": self.evidence_class, "security_classification": self.security_classification,
            "domain": self.domain, "status": self.status, "additive": self.additive, "register": self.register,
            "time_anchor": self.time_anchor, "lineage": list(self.lineage), "owner": self.owner,
            "compat": {"since": self.compat_since, "deprecates": self.deprecates}, "parameters": dict(self.parameters),
            "implemented_today": self.implemented_today, "queryable": self.status in ("EXISTS", "DERIVABLE"),
        }


_PRODUCT_DIMS = ("sku", "product", "category", "sub_category", "brand", "abc_class", "sector", "supplier")
_ORDER_DIMS = (*_PRODUCT_DIMS, "customer", "channel", "location", "date")
_STOCK_DIMS = (*_PRODUCT_DIMS, "location", "date")
_PO_DIMS = (*_PRODUCT_DIMS, "origin", "route", "destination", "po_status", "date")
_MATCHED_DIMS = ("supplier", "origin", "route", "sku", "product", "category", "brand", "sector", "date")


def _m(**kw: Any) -> MetricContract:
    return MetricContract(**kw)


METRICS: dict[str, MetricContract] = {m.metric_id: m for m in (
    # ── Demand (observed customer orders) ──
    _m(metric_id="ordered_units", version=1, display_name=_t("Units ordered", "الوحدات المطلوبة"), description=_t("Units on customer order lines (observed orders, not a demand estimate).", "الوحدات على سطور طلبات العملاء (طلبات مرصودة وليست تقديراً للطلب)."),
       business_definition="Sum of qty_ordered over customer order lines that carry a quantity.", source_entities=("customer_order_line",), fact="customer_order_line",
       aggregation_rule="sum", allowed_dimensions=_ORDER_DIMS, required_fields=("order_date", "sku", "qty_ordered"),
       coverage_rule=Coverage("share of order lines carrying a quantity"), null_behavior={"no_order_lines": "NO_DATA"},
       unit="units", currency_behavior="none", grain="customer_order_line", evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL", domain="Demand",
       numerator="sum(qty_ordered) of order lines", denominator="every order line after filters", time_anchor="order_date",
       lineage=("stg_fmcg_orders", "stg_fmcg_skus"), implemented_today="insights.demand"),
    _m(metric_id="ordered_lines", version=1, display_name=_t("Order lines", "سطور الطلبات"), description=_t("Customer order lines.", "عدد سطور طلبات العملاء."),
       business_definition="Count of customer order lines that carry a quantity.", source_entities=("customer_order_line",), fact="customer_order_line",
       aggregation_rule="count", allowed_dimensions=_ORDER_DIMS, required_fields=("order_date", "sku", "qty_ordered"),
       coverage_rule=Coverage("every order line"), null_behavior={"no_order_lines": "NO_DATA"}, unit="lines", currency_behavior="none", grain="customer_order_line",
       evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL", domain="Demand", numerator="count(order lines)", denominator="—", time_anchor="order_date",
       lineage=("stg_fmcg_orders",), implemented_today="insights.demand"),
    _m(metric_id="customers_ordering", version=1, display_name=_t("Customers ordering", "العملاء الطالبون"), description=_t("Distinct customers with at least one order line.", "عدد العملاء المميزين الذين لديهم سطر طلب واحد على الأقل."),
       business_definition="Count of distinct customer ids on order lines.", source_entities=("customer_order_line", "customer"), fact="customer_order_line",
       aggregation_rule="count_distinct", allowed_dimensions=_ORDER_DIMS, required_fields=("customer_id",), coverage_rule=Coverage("every order line"),
       null_behavior={"no_order_lines": "NO_DATA"}, unit="count", currency_behavior="none", grain="customer", evidence_class="OBSERVED_FACT",
       security_classification="OPERATIONAL", domain="Customers", numerator="count(distinct customer_id)", denominator="—", additive=False, time_anchor="order_date",
       lineage=("stg_fmcg_orders",), implemented_today="insights.demand"),
    _m(metric_id="shipped_units", version=1, display_name=_t("Units shipped", "الوحدات المشحونة"), description=_t("Units shipped on lines that record a shipped quantity.", "الوحدات المشحونة على السطور التي تسجّل كمية مشحونة."),
       business_definition="Sum of qty_shipped over lines where it is recorded; lines without it are NOT_MEASURED, never zero.", source_entities=("customer_order_line",), fact="customer_order_line",
       aggregation_rule="sum", allowed_dimensions=_ORDER_DIMS, required_fields=("qty_shipped",), coverage_rule=Coverage("share of order lines recording a shipped quantity", insufficient_below=0.5),
       null_behavior={"no_shipped_quantity_recorded": "NOT_MEASURED", "no_order_lines": "NO_DATA"}, unit="units", currency_behavior="none", grain="customer_order_line",
       evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL", domain="Service", numerator="sum(qty_shipped) where recorded", denominator="—", time_anchor="order_date",
       lineage=("stg_fmcg_orders",), implemented_today="insights.demand, insights.service"),
    _m(metric_id="unfulfilled_units", version=1, display_name=_t("Unfulfilled units", "الوحدات غير الملبّاة"), description=_t("Ordered minus shipped on lines that record a shipped quantity.", "المطلوب ناقص المشحون على السطور التي تسجّل كمية مشحونة."),
       business_definition="Sum of (qty_ordered − qty_shipped) over lines that record a shipped quantity.", source_entities=("customer_order_line",), fact="customer_order_line",
       aggregation_rule="sum", allowed_dimensions=_ORDER_DIMS, required_fields=("qty_shipped",), coverage_rule=Coverage("share of order lines recording a shipped quantity", insufficient_below=0.5),
       null_behavior={"no_shipped_quantity_recorded": "NOT_MEASURED", "no_order_lines": "NO_DATA"}, unit="units", currency_behavior="none", grain="customer_order_line",
       evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL", domain="Service", numerator="sum(qty_ordered − qty_shipped) on measured lines", denominator="—", time_anchor="order_date",
       lineage=("stg_fmcg_orders",), implemented_today="insights.demand, insights.service"),
    _m(metric_id="fill_rate", version=1, display_name=_t("Customer fill rate", "نسبة تلبية العملاء"), description=_t("Units shipped ÷ units ordered on lines that record a shipped quantity.", "الوحدات المشحونة ÷ الوحدات المطلوبة على السطور التي تسجّل كمية مشحونة."),
       business_definition="shipped_units / ordered_units over measured lines (ratio of sums, never an average of ratios). Insights calls this the service level.",
       source_entities=("customer_order_line",), fact="customer_order_line", aggregation_rule="ratio_of_sums", allowed_dimensions=_ORDER_DIMS, required_fields=("qty_shipped",),
       coverage_rule=Coverage("share of order lines recording a shipped quantity", insufficient_below=0.5, thin_sample_below=THIN_SAMPLE),
       null_behavior={"no_shipped_quantity_recorded": "NOT_MEASURED", "no_order_lines": "NO_DATA", "zero_ordered": "NOT_APPLICABLE"}, unit="ratio", currency_behavior="none",
       grain="customer_order_line", evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL", domain="Service", numerator="sum(qty_shipped)",
       denominator="sum(qty_ordered) on lines that record a shipped quantity", additive=False, time_anchor="order_date", lineage=("stg_fmcg_orders",), implemented_today="insights.service"),
    _m(metric_id="customer_fill_rate", version=1, display_name=_t("Fill rate by customer", "نسبة التلبية حسب العميل"), description=_t("The customer fill rate, defined once; alias of fill_rate for the customer view.", "نسبة تلبية العميل، بتعريف واحد؛ اسم بديل لـ fill_rate."),
       business_definition="Identical to fill_rate; kept as a named entry so the customer view and the service view cannot drift.", source_entities=("customer_order_line",), fact="customer_order_line",
       aggregation_rule="ratio_of_sums", allowed_dimensions=_ORDER_DIMS, required_fields=("qty_shipped",), coverage_rule=Coverage("share of order lines recording a shipped quantity", insufficient_below=0.5, thin_sample_below=THIN_SAMPLE),
       null_behavior={"no_shipped_quantity_recorded": "NOT_MEASURED", "no_order_lines": "NO_DATA"}, unit="ratio", currency_behavior="none", grain="customer_order_line",
       evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL", domain="Customers", numerator="sum(qty_shipped)", denominator="sum(qty_ordered) on measured lines", additive=False,
       time_anchor="order_date", lineage=("stg_fmcg_orders",), implemented_today="insights.service"),
    _m(metric_id="customer_order_units", version=1, display_name=_t("Customer order units", "وحدات طلبات العملاء"), description=_t("Units ordered, for the customer view (same definition as ordered_units).", "الوحدات المطلوبة في عرض العملاء (التعريف نفسه لـ ordered_units)."),
       business_definition="Identical to ordered_units.", source_entities=("customer_order_line",), fact="customer_order_line", aggregation_rule="sum", allowed_dimensions=_ORDER_DIMS,
       required_fields=("qty_ordered",), coverage_rule=Coverage("every order line"), null_behavior={"no_order_lines": "NO_DATA"}, unit="units", currency_behavior="none",
       grain="customer_order_line", evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL", domain="Customers", numerator="sum(qty_ordered)", denominator="—",
       time_anchor="order_date", lineage=("stg_fmcg_orders",), implemented_today="insights.demand"),
    # ── Inventory ──
    _m(metric_id="inventory_units", version=1, display_name=_t("Units on hand", "الوحدات المتاحة"), description=_t("Units on hand at the latest snapshot in each period.", "الوحدات المتاحة في آخر لقطة ضمن كل فترة."),
       business_definition="Sum of on_hand over the latest snapshot date in the period (latest import per product × site); never a sum of snapshots.",
       source_entities=("inventory_snapshot",), fact="inventory_snapshot", aggregation_rule="latest_snapshot", allowed_dimensions=_STOCK_DIMS, required_fields=("snapshot_date", "on_hand"),
       coverage_rule=Coverage("snapshot rows on the latest date"), null_behavior={"no_snapshots": "NO_DATA"}, unit="units", currency_behavior="none", grain="inventory_snapshot",
       evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL", domain="Inventory", numerator="sum(on_hand) on the latest snapshot", denominator="—", additive=False,
       time_anchor="snapshot_date", lineage=("stg_fmcg_inventory",), implemented_today="catalog._stock_cte, insights.inventory"),
    _m(metric_id="in_transit_units", version=1, display_name=_t("Units in transit", "الوحدات في الطريق"), description=_t("Units in transit at the latest snapshot in each period.", "الوحدات في الطريق في آخر لقطة ضمن كل فترة."),
       business_definition="Sum of in_transit over the latest snapshot date in the period.", source_entities=("inventory_snapshot",), fact="inventory_snapshot", aggregation_rule="latest_snapshot",
       allowed_dimensions=_STOCK_DIMS, required_fields=("in_transit",), coverage_rule=Coverage("snapshot rows on the latest date"), null_behavior={"no_snapshots": "NO_DATA"},
       unit="units", currency_behavior="none", grain="inventory_snapshot", evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL", domain="Inventory",
       numerator="sum(in_transit) on the latest snapshot", denominator="—", additive=False, time_anchor="snapshot_date", lineage=("stg_fmcg_inventory",), implemented_today="insights.inventory"),
    _m(metric_id="inventory_value", version=1, display_name=_t("Inventory value", "قيمة المخزون"), description=_t("Units on hand × unit cost from the product master.", "الوحدات المتاحة × تكلفة الوحدة من ملف المنتجات."),
       business_definition="Sum of on_hand × unit_cost over the latest snapshot; rows without a unit cost are counted and excluded (NOT_MEASURED where none carries a cost).",
       source_entities=("inventory_snapshot", "product"), fact="inventory_snapshot", aggregation_rule="latest_snapshot", allowed_dimensions=_STOCK_DIMS, required_fields=("on_hand", "unit_cost"),
       coverage_rule=Coverage("share of snapshot rows carrying a unit cost", insufficient_below=0.5), null_behavior={"no_snapshots": "NO_DATA", "no_unit_cost": "NOT_MEASURED"},
       unit="money", currency_behavior="workspace_currency", grain="inventory_snapshot", evidence_class="OBSERVED_FACT", security_classification="ECONOMIC", domain="Inventory",
       numerator="sum(on_hand × unit_cost)", denominator="—", additive=False, time_anchor="snapshot_date", lineage=("stg_fmcg_inventory", "stg_fmcg_skus"), implemented_today="insights.inventory"),
    _m(metric_id="weeks_of_cover", version=1, display_name=_t("Weeks of cover", "أسابيع التغطية"), description=_t("Units on hand ÷ average weekly units ordered over the trailing 12 weeks.", "الوحدات المتاحة ÷ متوسط الوحدات المطلوبة أسبوعياً خلال آخر 12 أسبوعاً."),
       business_definition="inventory_units at the latest snapshot divided by (ordered_units over the last 12 weeks of order history ÷ 12), per product and summed as a ratio of sums over the group. The Inventory page's rule.",
       source_entities=("inventory_snapshot", "customer_order_line"), fact="inventory_snapshot", aggregation_rule="ratio_of_sums", allowed_dimensions=("sku", "product", "category", "sub_category", "brand", "abc_class", "sector", "supplier", "location"),
       required_fields=("on_hand", "qty_ordered"), coverage_rule=Coverage("share of products with any order in the trailing 12 weeks", insufficient_below=0.5),
       null_behavior={"no_snapshots": "NO_DATA", "no_recent_orders": "NOT_MEASURED", "zero_weekly_demand": "NOT_APPLICABLE"}, unit="weeks", currency_behavior="none",
       grain="product", evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL", domain="Inventory", numerator="sum(on_hand) at the latest snapshot",
       denominator="sum(weekly demand) = sum(qty_ordered over the last 12 weeks) ÷ 12", additive=False, parameters={"weeks": COVER_WEEKS},
       lineage=("stg_fmcg_inventory", "stg_fmcg_orders"), implemented_today="catalog.inventory_page, insights.inventory"),
    # ── Purchasing ──
    _m(metric_id="open_po_units", version=1, display_name=_t("Open PO units", "وحدات أوامر الشراء المفتوحة"), description=_t("Units still owed on open purchase orders (open until the first receipt).", "الوحدات المستحقة على أوامر الشراء المفتوحة (مفتوحة حتى أول استلام)."),
       business_definition="Sum of open units per PO line; an order is open until its first receipt is recorded (the Purchase Orders page's rule).", source_entities=("purchase_order_line", "receipt"),
       fact="purchase_order_line", aggregation_rule="sum", allowed_dimensions=_PO_DIMS, required_fields=("po_id", "qty_ordered"), coverage_rule=Coverage("every purchase-order line"),
       null_behavior={"no_purchase_orders": "NO_DATA"}, unit="units", currency_behavior="none", grain="purchase_order_line", evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL",
       domain="Purchasing", numerator="sum(open units)", denominator="—", time_anchor="po_date", lineage=("stg_fmcg_purchase_orders", "stg_fmcg_receipts"), implemented_today="catalog._open_po_cte, insights.supply"),
    _m(metric_id="open_po_value", version=1, display_name=_t("Open PO value", "قيمة أوامر الشراء المفتوحة"), description=_t("Open units × unit cost from the product master.", "الوحدات المفتوحة × تكلفة الوحدة."),
       business_definition="Sum of open units × unit_cost; NOT_MEASURED where no line carries a cost.", source_entities=("purchase_order_line", "product"), fact="purchase_order_line",
       aggregation_rule="sum", allowed_dimensions=_PO_DIMS, required_fields=("qty_ordered", "unit_cost"), coverage_rule=Coverage("share of open lines carrying a unit cost", insufficient_below=0.5),
       null_behavior={"no_purchase_orders": "NO_DATA", "no_unit_cost": "NOT_MEASURED"}, unit="money", currency_behavior="workspace_currency", grain="purchase_order_line",
       evidence_class="OBSERVED_FACT", security_classification="ECONOMIC", domain="Purchasing", numerator="sum(open units × unit_cost)", denominator="—", time_anchor="po_date",
       lineage=("stg_fmcg_purchase_orders", "stg_fmcg_skus"), implemented_today="insights.supply"),
    _m(metric_id="open_po_count", version=1, display_name=_t("Open purchase orders", "أوامر الشراء المفتوحة"), description=_t("Purchase orders with units still owed.", "أوامر الشراء التي لا تزال عليها وحدات مستحقة."),
       business_definition="Count of distinct po_id with open units > 0.", source_entities=("purchase_order_line",), fact="purchase_order_line", aggregation_rule="count_distinct",
       allowed_dimensions=_PO_DIMS, required_fields=("po_id",), coverage_rule=Coverage("every purchase order"), null_behavior={"no_purchase_orders": "NO_DATA"}, unit="orders",
       currency_behavior="none", grain="purchase_order", evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL", domain="Purchasing", numerator="count(distinct po_id) where open",
       denominator="—", additive=False, time_anchor="po_date", lineage=("stg_fmcg_purchase_orders",), implemented_today="insights.supply"),
    _m(metric_id="po_ordered_units", version=1, display_name=_t("PO units ordered", "الوحدات المطلوبة من الموردين"), description=_t("Units ordered on purchase orders.", "الوحدات المطلوبة على أوامر الشراء."),
       business_definition="Sum of qty_ordered over purchase-order lines.", source_entities=("purchase_order_line",), fact="purchase_order_line", aggregation_rule="sum", allowed_dimensions=_PO_DIMS,
       required_fields=("qty_ordered",), coverage_rule=Coverage("every purchase-order line"), null_behavior={"no_purchase_orders": "NO_DATA"}, unit="units", currency_behavior="none",
       grain="purchase_order_line", evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL", domain="Purchasing", numerator="sum(qty_ordered)", denominator="—",
       time_anchor="po_date", lineage=("stg_fmcg_purchase_orders",), implemented_today="insights.suppliers (share basis)"),
    _m(metric_id="received_units", version=1, display_name=_t("Units received", "الوحدات المستلمة"), description=_t("Units received on receipts.", "الوحدات المستلمة على سندات الاستلام."),
       business_definition="Sum of qty_received over receipt lines.", source_entities=("receipt",), fact="receipt", aggregation_rule="sum", allowed_dimensions=("sku", "product", "category", "brand", "supplier", "date"),
       required_fields=("qty_received",), coverage_rule=Coverage("every receipt line"), null_behavior={"no_receipts": "NO_DATA"}, unit="units", currency_behavior="none", grain="receipt",
       evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL", domain="Purchasing", numerator="sum(qty_received)", denominator="—", time_anchor="receipt_date",
       lineage=("stg_fmcg_receipts",), implemented_today="insights.supply"),
    # ── Suppliers (measured on matched purchase orders) ──
    _m(metric_id="matched_orders", version=1, display_name=_t("Measured orders", "الأوامر المقاسة"), description=_t("Purchase orders with at least one receipt.", "أوامر الشراء التي لها استلام واحد على الأقل."),
       business_definition="Count of purchase orders that have at least one receipt: the sample every supplier measure is taken on.", source_entities=("matched_purchase_order",),
       fact="matched_purchase_order", aggregation_rule="count", allowed_dimensions=_MATCHED_DIMS, required_fields=("po_id", "receipt_date"), coverage_rule=Coverage("every matched order"),
       null_behavior={"no_matched_orders": "NO_DATA"}, unit="orders", currency_behavior="none", grain="purchase_order", evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL",
       domain="Suppliers", numerator="count(matched orders)", denominator="—", time_anchor="po_date", lineage=("stg_fmcg_purchase_orders", "stg_fmcg_receipts", "diagnostics._matched_cte"),
       implemented_today="diagnostics.supplier_page, insights.suppliers"),
    _m(metric_id="supplier_fill_rate", version=1, display_name=_t("Supplier fill rate", "نسبة تلبية المورد"), description=_t("Units received ÷ units ordered on matched orders.", "الوحدات المستلمة ÷ الوحدات المطلوبة على الأوامر المقاسة."),
       business_definition="sum(received) / sum(ordered) over purchase orders with at least one receipt (ratio of sums).", source_entities=("matched_purchase_order",), fact="matched_purchase_order",
       aggregation_rule="ratio_of_sums", allowed_dimensions=_MATCHED_DIMS, required_fields=("qty_ordered", "qty_received"),
       coverage_rule=Coverage("matched orders in the group", thin_sample_below=THIN_SAMPLE), null_behavior={"no_matched_orders": "NO_DATA", "zero_ordered": "NOT_APPLICABLE"},
       unit="ratio", currency_behavior="none", grain="purchase_order", evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL", domain="Suppliers",
       numerator="sum(qty_received)", denominator="sum(qty_ordered) on matched orders", additive=False, time_anchor="po_date",
       lineage=("stg_fmcg_purchase_orders", "stg_fmcg_receipts"), implemented_today="diagnostics.supplier_page, insights.suppliers"),
    _m(metric_id="short_fill_rate", version=1, display_name=_t("Short-fill rate", "نسبة النقص في التسليم"), description=_t("Share of matched orders that arrived short of the ordered quantity by more than the tolerance.", "حصة الأوامر المقاسة التي وصلت ناقصة عن الكمية المطلوبة بأكثر من حد التسامح."),
       business_definition=f"count(matched orders with received/ordered < {SHORT_FILL_TOLERANCE}) / count(matched orders).", source_entities=("matched_purchase_order",), fact="matched_purchase_order",
       aggregation_rule="ratio_of_counts", allowed_dimensions=_MATCHED_DIMS, required_fields=("qty_ordered", "qty_received"), coverage_rule=Coverage("matched orders in the group", thin_sample_below=THIN_SAMPLE),
       null_behavior={"no_matched_orders": "NO_DATA"}, unit="ratio", currency_behavior="none", grain="purchase_order", evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL",
       domain="Suppliers", numerator="count(short orders)", denominator="count(matched orders)", additive=False, parameters={"short_fill_tolerance": SHORT_FILL_TOLERANCE},
       time_anchor="po_date", lineage=("stg_fmcg_purchase_orders", "stg_fmcg_receipts"), implemented_today="diagnostics.supplier_page"),
    _m(metric_id="short_fill_units", version=1, display_name=_t("Short-fill units", "وحدات النقص"), description=_t("Units ordered but not received on matched orders that arrived short.", "الوحدات المطلوبة ولم تُستلم على الأوامر التي وصلت ناقصة."),
       business_definition="Sum of (ordered − received) over matched orders where received < ordered.", source_entities=("matched_purchase_order",), fact="matched_purchase_order", aggregation_rule="sum",
       allowed_dimensions=_MATCHED_DIMS, required_fields=("qty_ordered", "qty_received"), coverage_rule=Coverage("matched orders in the group"), null_behavior={"no_matched_orders": "NO_DATA"},
       unit="units", currency_behavior="none", grain="purchase_order", evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL", domain="Suppliers",
       numerator="sum(ordered − received) where short", denominator="—", time_anchor="po_date", lineage=("stg_fmcg_purchase_orders", "stg_fmcg_receipts"), status="DERIVABLE"),
    _m(metric_id="supplier_late_rate", version=1, display_name=_t("Late-order rate", "نسبة الأوامر المتأخرة"), description=_t("Share of matched orders that arrived after their promised date, among those that carry one.", "حصة الأوامر المقاسة التي وصلت بعد التاريخ الموعود، من بين التي تحمل تاريخاً موعوداً."),
       business_definition="count(first receipt after expected_delivery_date) / count(matched orders with an expected_delivery_date). An order without a promised date is outside the denominator, never counted on time.",
       source_entities=("matched_purchase_order",), fact="matched_purchase_order", aggregation_rule="ratio_of_counts", allowed_dimensions=_MATCHED_DIMS,
       required_fields=("po_date", "expected_delivery_date", "receipt_date"), coverage_rule=Coverage("share of matched orders carrying a promised date", insufficient_below=0.5, thin_sample_below=THIN_SAMPLE),
       null_behavior={"no_matched_orders": "NO_DATA", "no_promised_dates": "BLOCKED_BY_DATA", "zero_late_with_full_coverage": "0"}, unit="ratio", currency_behavior="none",
       grain="purchase_order", evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL", domain="Suppliers", numerator="count(orders received after the promised date)",
       denominator="count(matched orders carrying a promised date)", additive=False, time_anchor="po_date", lineage=("stg_fmcg_purchase_orders", "stg_fmcg_receipts"),
       implemented_today="diagnostics.supplier_page, insights.suppliers"),
    _m(metric_id="lead_time_p50", version=1, display_name=_t("Lead time (median)", "مدة التوريد (الوسيط)"), description=_t("Median days from order date to first receipt.", "وسيط الأيام من تاريخ الطلب إلى أول استلام."),
       business_definition="quantile 0.5 of date_diff(po_date, first receipt) over matched orders.", source_entities=("matched_purchase_order",), fact="matched_purchase_order", aggregation_rule="quantile",
       allowed_dimensions=_MATCHED_DIMS, required_fields=("po_date", "receipt_date"), coverage_rule=Coverage("matched orders in the group", thin_sample_below=THIN_SAMPLE),
       null_behavior={"no_matched_orders": "NO_DATA"}, unit="days", currency_behavior="none", grain="purchase_order", evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL",
       domain="Suppliers", numerator="quantile_cont(observed lead days, 0.5)", denominator="—", additive=False, parameters={"q": 0.5}, time_anchor="po_date",
       lineage=("stg_fmcg_purchase_orders", "stg_fmcg_receipts"), implemented_today="diagnostics.supplier_page, insights.suppliers"),
    _m(metric_id="lead_time_p90", version=1, display_name=_t("Lead time (p90)", "مدة التوريد (المئين 90)"), description=_t("Ninetieth-percentile days from order date to first receipt.", "المئين التسعون للأيام من تاريخ الطلب إلى أول استلام."),
       business_definition="quantile 0.9 of date_diff(po_date, first receipt) over matched orders.", source_entities=("matched_purchase_order",), fact="matched_purchase_order", aggregation_rule="quantile",
       allowed_dimensions=_MATCHED_DIMS, required_fields=("po_date", "receipt_date"), coverage_rule=Coverage("matched orders in the group", thin_sample_below=THIN_SAMPLE),
       null_behavior={"no_matched_orders": "NO_DATA"}, unit="days", currency_behavior="none", grain="purchase_order", evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL",
       domain="Suppliers", numerator="quantile_cont(observed lead days, 0.9)", denominator="—", additive=False, parameters={"q": 0.9}, time_anchor="po_date",
       lineage=("stg_fmcg_purchase_orders", "stg_fmcg_receipts"), implemented_today="diagnostics.supplier_page, insights.suppliers"),
    _m(metric_id="lead_time", version=1, display_name=_t("Lead time (mean)", "مدة التوريد (المتوسط)"), description=_t("Mean days from order date to first receipt.", "متوسط الأيام من تاريخ الطلب إلى أول استلام."),
       business_definition="mean of date_diff(po_date, first receipt) over matched orders.", source_entities=("matched_purchase_order",), fact="matched_purchase_order", aggregation_rule="mean",
       allowed_dimensions=_MATCHED_DIMS, required_fields=("po_date", "receipt_date"), coverage_rule=Coverage("matched orders in the group", thin_sample_below=THIN_SAMPLE),
       null_behavior={"no_matched_orders": "NO_DATA"}, unit="days", currency_behavior="none", grain="purchase_order", evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL",
       domain="Suppliers", numerator="avg(observed lead days)", denominator="—", additive=False, time_anchor="po_date", lineage=("stg_fmcg_purchase_orders", "stg_fmcg_receipts"),
       implemented_today="diagnostics.supplier_page (mean_lead_days)"),
    _m(metric_id="lead_time_variability", version=1, display_name=_t("Lead-time variability", "تذبذب مدة التوريد"), description=_t("Spread of lead time: p90 minus p50, in days.", "مدى مدة التوريد: المئين 90 ناقص الوسيط، بالأيام."),
       business_definition="quantile 0.9 − quantile 0.5 of observed lead days over matched orders in the group.", source_entities=("matched_purchase_order",), fact="matched_purchase_order",
       aggregation_rule="quantile", allowed_dimensions=_MATCHED_DIMS, required_fields=("po_date", "receipt_date"), coverage_rule=Coverage("matched orders in the group", thin_sample_below=THIN_SAMPLE),
       null_behavior={"no_matched_orders": "NO_DATA"}, unit="days", currency_behavior="none", grain="purchase_order", evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL",
       domain="Suppliers", numerator="p90 − p50 of observed lead days", denominator="—", additive=False, parameters={"spread": "p90-p50"}, time_anchor="po_date",
       lineage=("stg_fmcg_purchase_orders", "stg_fmcg_receipts"), status="DERIVABLE"),
    _m(metric_id="mean_late_days", version=1, display_name=_t("Days late (when late)", "أيام التأخير (عند التأخر)"), description=_t("Mean days after the promised date, over late orders only.", "متوسط الأيام بعد التاريخ الموعود، على الأوامر المتأخرة فقط."),
       business_definition="avg(late_days) over matched orders with late_days > 0.", source_entities=("matched_purchase_order",), fact="matched_purchase_order", aggregation_rule="mean",
       allowed_dimensions=_MATCHED_DIMS, required_fields=("expected_delivery_date", "receipt_date"), coverage_rule=Coverage("late orders in the group", thin_sample_below=THIN_SAMPLE),
       null_behavior={"no_late_orders": "NOT_APPLICABLE", "no_promised_dates": "BLOCKED_BY_DATA"}, unit="days", currency_behavior="none", grain="purchase_order", evidence_class="OBSERVED_FACT",
       security_classification="OPERATIONAL", domain="Suppliers", numerator="avg(days after the promised date) where late", denominator="—", additive=False, time_anchor="po_date",
       lineage=("stg_fmcg_purchase_orders", "stg_fmcg_receipts"), implemented_today="diagnostics.supplier_page, insights.suppliers"),
    # ── Decisions (plan snapshot) ──
    _m(metric_id="decision_count", version=1, display_name=_t("Decisions", "القرارات"), description=_t("Decisions in the latest completed plan (verdicts on open orders, purchases, transfers).", "القرارات في آخر خطة مكتملة (أحكام على الأوامر المفتوحة، مشتريات، تحويلات)."),
       business_definition="Count of decisions the latest DONE workspace plan carries, read verbatim from the stored report.", source_entities=("decision", "plan"), fact="decision",
       aggregation_rule="count", allowed_dimensions=("decision_verb", "sku", "supplier"), required_fields=("report",), coverage_rule=Coverage("every decision of the latest plan"),
       null_behavior={"no_completed_plan": "NOT_IN_PLAN"}, unit="count", currency_behavior="none", grain="decision", evidence_class="PLAN_SNAPSHOT", security_classification="OPERATIONAL",
       domain="Decisions", numerator="count(decisions)", denominator="—", lineage=("job store",), implemented_today="insights.decisions"),
    _m(metric_id="recommendation_count", version=1, display_name=_t("Recommended changes", "التغييرات الموصى بها"), description=_t("Decisions whose verb is a change (everything but KEEP).", "القرارات التي فعلها تغيير (كل شيء عدا الإبقاء)."),
       business_definition="Count of decisions in the latest plan whose verb is not KEEP.", source_entities=("decision", "plan"), fact="decision", aggregation_rule="count",
       allowed_dimensions=("decision_verb", "sku", "supplier"), required_fields=("report",), coverage_rule=Coverage("every decision of the latest plan"),
       null_behavior={"no_completed_plan": "NOT_IN_PLAN"}, unit="count", currency_behavior="none", grain="decision", evidence_class="PLAN_SNAPSHOT", security_classification="OPERATIONAL",
       domain="Decisions", numerator="count(decisions with verb ≠ KEEP)", denominator="—", lineage=("job store",), implemented_today="insights.decisions"),
    _m(metric_id="decision_response_count", version=1, display_name=_t("Decision responses", "الردود على القرارات"), description=_t("What people did with decisions: reviewed, accepted, overridden, rejected.", "ما فعله الأشخاص بالقرارات: مراجعة، قبول، تجاوز، رفض."),
       business_definition="Count of rows in zaad_decision_responses.", source_entities=("decision_response",), fact="decision_response", aggregation_rule="count", allowed_dimensions=("decision_status", "date"),
       required_fields=("status",), coverage_rule=Coverage("every response"), null_behavior={"no_responses": "NO_DATA"}, unit="count", currency_behavior="none", grain="decision_response",
       evidence_class="OBSERVED_FACT", security_classification="GOVERNANCE", domain="Decisions", numerator="count(responses)", denominator="—", time_anchor="created_at",
       lineage=("zaad_decision_responses",), implemented_today="insights.decisions"),
    _m(metric_id="override_rate", version=1, display_name=_t("Override rate", "نسبة التجاوز"), description=_t("Responses overridden ÷ responses.", "الردود المتجاوَزة ÷ الردود."),
       business_definition="count(status = OVERRIDDEN) / count(responses).", source_entities=("decision_response",), fact="decision_response", aggregation_rule="ratio_of_counts",
       allowed_dimensions=("date",), required_fields=("status",), coverage_rule=Coverage("every response", thin_sample_below=THIN_SAMPLE), null_behavior={"no_responses": "NO_DATA"},
       unit="ratio", currency_behavior="none", grain="decision_response", evidence_class="OBSERVED_FACT", security_classification="GOVERNANCE", domain="Decisions",
       numerator="count(overridden)", denominator="count(responses)", additive=False, time_anchor="created_at", lineage=("zaad_decision_responses",), status="DERIVABLE"),
    _m(metric_id="proposal_count", version=1, display_name=_t("Proposals", "المقترحات"), description=_t("Proposed orders by state.", "أوامر مقترحة حسب الحالة."),
       business_definition="Count of rows in zaad_draft_orders.", source_entities=("proposal",), fact="proposal", aggregation_rule="count", allowed_dimensions=("proposal_state", "supplier", "date"),
       required_fields=("state",), coverage_rule=Coverage("every proposal"), null_behavior={"no_proposals": "NO_DATA"}, unit="count", currency_behavior="none", grain="proposal",
       evidence_class="OBSERVED_FACT", security_classification="GOVERNANCE", domain="Decisions", numerator="count(proposals)", denominator="—", time_anchor="updated_at",
       lineage=("zaad_draft_orders",), implemented_today="insights.decisions"),
    # ── Value (five registers, never combined) ──
    _m(metric_id="modeled_difference", version=1, display_name=_t("Modelled difference", "الفرق المنمذج"), description=_t("The plan's ledger: incumbent total minus selected total. A modelled difference, not a saving.", "دفتر الخطة: إجمالي السياسة الحالية ناقص إجمالي المختار. فرق منمذج وليس توفيراً."),
       business_definition="From the latest plan's economics block: incumbent_costs.TOTAL − selected_costs.TOTAL, read verbatim.", source_entities=("plan",), fact="plan_value",
       aggregation_rule="snapshot", allowed_dimensions=("value_register",), required_fields=("economics",), coverage_rule=Coverage("the latest completed plan"),
       null_behavior={"no_completed_plan": "NOT_IN_PLAN", "plan_without_economics": "NOT_IN_PLAN"}, unit="money", currency_behavior="workspace_currency", grain="plan",
       evidence_class="MODELED", security_classification="ECONOMIC", domain="Value", numerator="incumbent total", denominator="selected total (as a difference)", additive=False,
       register="MODELED_DIFFERENCE", lineage=("job store",), implemented_today="insights.value"),
    _m(metric_id="backtested_opportunity", version=1, display_name=_t("Backtested opportunity", "الفرصة المختبَرة رجعياً"), description=_t("Held-out replay difference on the operator's own history. Not wired.", "فرق إعادة التشغيل على سجل المشغّل. غير موصول."),
       business_definition="Not measured: no held-out replay of customer history is wired into the product.", source_entities=("plan",), fact="plan_value", aggregation_rule="snapshot",
       allowed_dimensions=("value_register",), required_fields=(), coverage_rule=Coverage("—"), null_behavior={"always": "NOT_MEASURED"}, unit="money", currency_behavior="workspace_currency",
       grain="plan", evidence_class="MODELED", security_classification="ECONOMIC", domain="Value", numerator="—", denominator="—", additive=False, register="BACKTESTED_OPPORTUNITY", status="FUTURE"),
    _m(metric_id="approved_expected_difference", version=1, display_name=_t("Approved expected difference", "الفرق المتوقع المعتمد"), description=_t("An approved proposal's evaluation difference at approval time. Expected, not observed.", "فرق تقييم مقترح معتمد وقت الاعتماد. متوقع وليس مرصوداً."),
       business_definition="For each approved proposal, its evaluation's TOTAL proposal_vs_current difference, read from the two stored runs.", source_entities=("proposal", "evaluation"), fact="plan_value",
       aggregation_rule="snapshot", allowed_dimensions=("value_register",), required_fields=("approved_evaluation_id",), coverage_rule=Coverage("approved proposals with an evaluation"),
       null_behavior={"no_approved_proposal": "NO_DATA"}, unit="money", currency_behavior="workspace_currency", grain="proposal", evidence_class="MODELED", security_classification="ECONOMIC",
       domain="Value", numerator="sum(evaluation differences)", denominator="—", additive=False, register="APPROVED_EXPECTED_DIFFERENCE", lineage=("zaad_draft_orders", "zaad_evaluations", "job store"),
       implemented_today="insights.value"),
    _m(metric_id="observed_after_action", version=1, display_name=_t("Observed after action", "المرصود بعد الإجراء"), description=_t("Outcome values recorded after an approved action was placed. Observed after action; not attributed to ZAAD.", "قيم النتائج المسجّلة بعد تنفيذ إجراء معتمد. مرصودة بعد الإجراء؛ غير منسوبة إلى زاد."),
       business_definition="Sum of value over zaad_outcomes rows, by outcome metric.", source_entities=("outcome",), fact="outcome", aggregation_rule="sum", allowed_dimensions=("outcome_metric", "value_register", "date"),
       required_fields=("value",), coverage_rule=Coverage("every recorded outcome"), null_behavior={"no_outcomes": "NO_DATA"}, unit="mixed", currency_behavior="none", grain="outcome",
       evidence_class="OBSERVED_FACT", security_classification="ECONOMIC", domain="Value", numerator="sum(value)", denominator="—", register="OBSERVED_AFTER_ACTION", time_anchor="observed_at",
       lineage=("zaad_outcomes",), implemented_today="insights.value"),
    _m(metric_id="realized_value", version=1, display_name=_t("Realized value", "القيمة المحققة"), description=_t("Comparator minus observed value on outcomes whose comparator basis is stated.", "قيمة المقارنة ناقص القيمة المرصودة على النتائج التي حُدّد أساس مقارنتها."),
       business_definition="Sum of (comparator_value − value) over outcomes with a comparator and its basis. Only these rows may be called realized.", source_entities=("outcome",), fact="outcome",
       aggregation_rule="sum", allowed_dimensions=("outcome_metric", "value_register", "date"), required_fields=("value", "comparator_value", "comparator_basis"),
       coverage_rule=Coverage("share of outcomes carrying a comparator with a stated basis", insufficient_below=0.5), null_behavior={"no_outcomes": "NO_DATA", "no_comparator": "NOT_MEASURED"},
       unit="mixed", currency_behavior="none", grain="outcome", evidence_class="OBSERVED_FACT", security_classification="ECONOMIC", domain="Value", numerator="sum(comparator_value − value)",
       denominator="—", register="REALIZED_VALUE", time_anchor="observed_at", lineage=("zaad_outcomes",), implemented_today="insights.value, zaad_history.realized_value"),
    # ── classified, not built ──
    _m(metric_id="otif", version=1, display_name=_t("On time in full", "في الوقت وبالكامل"), description=_t("Lines shipped in full by the requested date. Needs a ship date per line.", "السطور المشحونة بالكامل بحلول التاريخ المطلوب. يحتاج تاريخ شحن لكل سطر."),
       business_definition="Requires a shipment date per order line; the upload carries requested_delivery_date only.", source_entities=("customer_order_line",), fact="customer_order_line",
       aggregation_rule="ratio_of_counts", allowed_dimensions=_ORDER_DIMS, required_fields=("ship_date",), coverage_rule=Coverage("—"), null_behavior={"always": "BLOCKED_BY_DATA"}, unit="ratio",
       currency_behavior="none", grain="customer_order_line", evidence_class="OBSERVED_FACT", security_classification="OPERATIONAL", domain="Service", numerator="—", denominator="—",
       additive=False, status="REQUIRES_NEW_DATA"),
    _m(metric_id="forecast_accuracy", version=1, display_name=_t("Forecast accuracy", "دقة التنبؤ"), description=_t("Fitted versus observed. No calibrated forecast exists to score.", "المقدَّر مقابل المرصود. لا يوجد تنبؤ معاير لتقييمه."),
       business_definition="Depends on an unreleased engine phase (P6).", source_entities=("customer_order_line",), fact="customer_order_line", aggregation_rule="mean", allowed_dimensions=("date",),
       required_fields=(), coverage_rule=Coverage("—"), null_behavior={"always": "NOT_MEASURED"}, unit="ratio", currency_behavior="none", grain="product", evidence_class="MODELED",
       security_classification="OPERATIONAL", domain="Demand", numerator="—", denominator="—", additive=False, status="FUTURE"),
)}


# ── registry helpers ────────────────────────────────────────────────────────

def metric(ref: str) -> MetricContract:
    """Resolve `metric_id` or `metric_id@version`. Unknown ids and versions raise KeyError."""
    metric_id, _, version = ref.partition("@")
    contract = METRICS.get(metric_id)
    if contract is None:
        raise KeyError(metric_id)
    if version and int(version) != contract.version:
        raise KeyError(ref)
    return contract


def queryable_metrics() -> list[MetricContract]:
    return [m for m in METRICS.values() if m.status in ("EXISTS", "DERIVABLE")]


def dimension(dimension_id: str) -> Dimension:
    d = DIMENSIONS.get(dimension_id)
    if d is None:
        raise KeyError(dimension_id)
    return d


def join_path(fact_id: str, dimension_id: str) -> str | None:
    """How a fact reaches a dimension, or None when there is no legal path."""
    fact = FACTS.get(fact_id)
    if fact is None:
        return None
    return fact.dimensions.get(dimension_id)


def model_document(locale: str = "en") -> dict[str, Any]:
    """The whole semantic model, machine-readable, for the model panel and Ask ZAAD's context."""
    return {
        "semantic_model_version": MODEL_VERSION,
        "domains": list(DOMAINS),
        "time_grains": list(TIME_GRAINS),
        "null_reasons": list(NULL_REASONS),
        "value_registers": list(VALUE_REGISTERS),
        "entities": [{"id": e.id, "label": e.label, "description": e.description, "source": e.source, "key": list(e.key), "status": e.status} for e in ENTITIES.values()],
        "dimensions": [{"id": d.id, "label": d.label, "entity": d.entity, "description": d.description, "kind": d.kind, "parent": d.parent,
                        "members": list(d.members) if d.members else None, "status": d.status, "classification": d.classification,
                        "drill_through": d.drill_through, "queryable": d.status in ("EXISTS", "DERIVABLE")} for d in DIMENSIONS.values()],
        "metrics": [m.as_dict() for m in METRICS.values()],
        "relationships": [{"from": r.from_entity, "to": r.to_entity, "on": r.on, "cardinality": r.cardinality} for r in RELATIONSHIPS],
        "facts": [{"id": f.id, "entity": f.entity, "dimensions": dict(f.dimensions), "time_anchor": f.time_anchor, "time_anchors": list(f.time_anchors), "source": f.source} for f in FACTS.values()],
        "drill_paths": dict(DRILL_PATHS),
        "parameters": {"thin_sample": THIN_SAMPLE, "short_fill_tolerance": SHORT_FILL_TOLERANCE, "cover_weeks": COVER_WEEKS},
    }

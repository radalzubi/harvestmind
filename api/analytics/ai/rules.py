"""The deterministic planner: a question becomes a governed query from the registry alone.

This is Ask ZAAD's floor. It runs when no model is configured, when the model's candidate is
refused twice, and for the curated questions the product knows well ("which suppliers are getting
less reliable"). It matches words against metric and dimension vocabularies, resolves members
against the bounded value lists, reads time phrases, and applies follow-ups to the previous spec.
It never guesses a metric: an unmatched question returns a clarification, not an invented number.
"""
from __future__ import annotations

import re
from typing import Any

from api.analytics import semantic
from api.analytics.ai.provider import PlanCandidate

#: words that point at a metric, beyond its display name
METRIC_WORDS: dict[str, tuple[str, ...]] = {
    "ordered_units": ("demand", "orders", "ordered", "units ordered", "sales", "volume", "customer orders", "الطلب", "الطلبات", "المطلوب"),
    "ordered_lines": ("order lines", "lines"),
    "customers_ordering": ("how many customers", "customers ordering", "active customers"),
    "shipped_units": ("shipped", "fulfilled units", "المشحون"),
    "unfulfilled_units": ("unfulfilled", "shortfall", "short shipped", "unmet", "غير الملبى"),
    "fill_rate": ("service level", "customer fill", "fill rate", "service", "fulfilment rate", "fulfillment rate", "نسبة التلبية", "مستوى الخدمة"),
    "inventory_units": ("stock", "on hand", "inventory", "units on hand", "المخزون"),
    "inventory_value": ("stock value", "inventory value", "value of stock", "قيمة المخزون"),
    "in_transit_units": ("in transit",),
    "weeks_of_cover": ("cover", "weeks of cover", "weeks of stock", "days of stock", "run out", "running out", "excess", "overstock", "التغطية"),
    "open_po_units": ("open po", "open purchase", "on order", "inbound", "outstanding orders", "open orders", "أوامر مفتوحة"),
    "open_po_value": ("open po value", "committed spend", "value on order"),
    "open_po_count": ("how many open", "open purchase orders count", "number of open"),
    "po_ordered_units": ("purchased", "bought", "po units"),
    "received_units": ("received", "receipts", "arrived units", "المستلم"),
    "matched_orders": ("deliveries", "measured orders"),
    "supplier_fill_rate": ("supplier fill", "quantity arrived", "delivered quantity", "reliable", "reliability", "unreliable", "performance", "getting worse", "deteriorat", "الموردون", "المورد"),
    "short_fill_rate": ("short fill", "short deliveries", "short-fill", "arrived short"),
    "short_fill_units": ("short units", "units short"),
    "supplier_late_rate": ("late", "lateness", "on time", "delays", "delayed", "reliable", "reliability", "unreliable", "getting worse", "deteriorat", "worse", "متأخر", "التأخير"),
    "lead_time_p50": ("lead time", "lead-time", "how long", "delivery time", "مدة التوريد"),
    "lead_time_p90": ("slow lead", "p90", "worst lead"),
    "lead_time_variability": ("variability", "variable lead", "lead time variability", "consistency", "inconsistent", "تذبذب"),
    "mean_late_days": ("days late", "how late"),
    "decision_count": ("decisions", "verdicts", "what zaad decided", "القرارات"),
    "recommendation_count": ("recommendations", "recommended changes", "changes recommended"),
    "decision_response_count": ("responses", "accepted", "overridden", "rejected decisions"),
    "override_rate": ("override rate", "overrides"),
    "proposal_count": ("proposals", "drafts", "المقترحات"),
    "modeled_difference": ("modelled difference", "modeled difference", "ledger", "plan value", "الفرق المنمذج"),
    "observed_after_action": ("observed after action", "outcomes", "النتائج"),
    "realized_value": ("realized value", "realised value", "القيمة المحققة"),
}
DIMENSION_WORDS: dict[str, tuple[str, ...]] = {
    "supplier": ("supplier", "suppliers", "vendor", "vendors", "المورد", "الموردين", "الموردون"),
    "category": ("category", "categories", "الفئة", "الفئات"),
    "sub_category": ("sub-category", "subcategory", "sub category"),
    "brand": ("brand", "brands", "العلامة"),
    "sku": ("sku", "skus", "product code", "products", "product", "items", "المنتج", "المنتجات"),
    "customer": ("customer", "customers", "accounts", "العميل", "العملاء"),
    "location": ("site", "sites", "warehouse", "warehouses", "branch", "branches", "location", "locations", "الموقع", "المواقع", "الفرع"),
    "destination": ("destination",),
    "channel": ("channel", "channels", "القناة"),
    "route": ("route", "routes", "corridor", "lane", "المسار"),
    "origin": ("origin", "country", "countries", "المنشأ"),
    "abc_class": ("abc", "class a", "class b", "class c"),
    "po_status": ("po status", "status of orders"),
    "decision_verb": ("verb", "by decision", "by verdict", "keep", "defer", "expedite"),
    "decision_status": ("by response", "response status"),
    "proposal_state": ("by state", "proposal state"),
    "outcome_metric": ("by outcome metric", "outcome metric"),
}
GRAIN_WORDS = {"day": ("daily", "by day", "per day", "يومي"), "week": ("weekly", "by week", "per week", "أسبوعي"), "month": ("monthly", "by month", "per month", "over time", "trend", "شهري", "مع الوقت"),
               "quarter": ("quarterly", "by quarter", "per quarter"), "year": ("yearly", "by year", "annual", "per year")}
RANK_WORDS = ("which", "top", "worst", "best", "highest", "lowest", "most", "least", "rank", "biggest", "largest", "smallest", "أي", "أكثر", "أقل", "أعلى")
TREND_WORDS = ("over time", "trend", "getting", "changing", "improving", "worse", "better", "deteriorat", "monthly", "weekly", "each month", "مع الوقت", "تتغير")
COMPOSITION_WORDS = ("share", "breakdown", "split", "mix", "composition", "by category", "حصة")
DETERIORATION = ("getting worse", "less reliable", "deteriorat", "worse", "declining reliability", "slipping", "worsening", "تتراجع", "أسوأ", "أقل موثوقية")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _match_any(text: str, words: tuple[str, ...]) -> bool:
    return any(w in text for w in words)


def find_metrics(text: str, fact: str | None = None) -> list[str]:
    """Metric ids the question names, longest match first, one fact only."""
    scored: list[tuple[int, str]] = []
    for metric_id, words in METRIC_WORDS.items():
        contract = semantic.METRICS[metric_id]
        if contract.status not in ("EXISTS", "DERIVABLE"):
            continue
        best = max((len(w) for w in words if w in text), default=0)
        name = contract.display_name["en"].lower()
        if name in text:
            best = max(best, len(name))
        if best:
            scored.append((best, metric_id))
    scored.sort(reverse=True)
    out: list[str] = []
    chosen_fact = fact
    for _, metric_id in scored:
        f = semantic.METRICS[metric_id].fact
        if chosen_fact is None:
            chosen_fact = f
        if f == chosen_fact and metric_id not in out:
            out.append(metric_id)
    return out[:4]


def find_dimensions(text: str, allowed: list[str]) -> list[str]:
    scored: list[tuple[int, str]] = []
    for dimension_id, words in DIMENSION_WORDS.items():
        if dimension_id not in allowed:
            continue
        best = max((len(w) for w in words if re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", text)), default=0)
        if best:
            scored.append((best, dimension_id))
    scored.sort(reverse=True)
    return [d for _, d in scored][:2]


def find_grain(text: str) -> str | None:
    for grain, words in GRAIN_WORDS.items():
        if _match_any(text, words):
            return grain
    return None


def find_range(text: str) -> dict[str, Any] | None:
    m = re.search(r"last (\d{1,3}) (day|week|month|quarter|year)s?", text)
    if m:
        return {"last": int(m.group(1)), "unit": m.group(2)}
    if "this year" in text or "year to date" in text or "ytd" in text:
        return {"last": 1, "unit": "year"}
    if "last year" in text:
        return {"last": 12, "unit": "month"}
    if "last quarter" in text:
        return {"last": 1, "unit": "quarter"}
    if "this month" in text or "last month" in text:
        return {"last": 1, "unit": "month"}
    if "last week" in text or "this week" in text:
        return {"last": 1, "unit": "week"}
    return None


def find_top_n(text: str) -> int | None:
    m = re.search(r"\b(top|worst|best|bottom|first)\s+(\d{1,2})\b", text)
    if m:
        return int(m.group(2))
    m = re.search(r"\b(\d{1,2})\s+(worst|best|top|biggest|largest|most)\b", text)
    if m:
        return int(m.group(1))
    return None


def find_members(text: str, members: dict[str, list[str]], allowed: list[str]) -> list[dict[str, Any]]:
    """Members the question names, resolved against bounded value lists (case-insensitive, whole word)."""
    out: list[dict[str, Any]] = []
    for dimension_id, values in members.items():
        if dimension_id not in allowed:
            continue
        hits = [v for v in values if len(v) >= 3 and re.search(r"(?<!\w)" + re.escape(v.lower()) + r"(?!\w)", text)]
        if hits:
            out.append({"dimension_id": dimension_id, "op": "in", "values": hits[:20]})
    return out


def plan(question: str, context: dict[str, Any], previous: dict[str, Any] | None, locale: str = "en") -> PlanCandidate:
    text = _norm(question)
    members = context.get("members") or {}
    follow_up = previous is not None and (len(text.split()) <= 8 or text.startswith(("only", "just", "add", "by ", "break", "and ", "now ", "same ", "what about", "فقط", "أضف")))

    if follow_up and previous:
        return _follow_up(text, previous, members, locale)

    if _match_any(text, DETERIORATION) and ("supplier" in text or "vendor" in text or "مورد" in text or "reliab" in text):
        # the curated question: reliability over time per supplier, ranked by the deterioration signal
        curated: dict[str, Any] = {"measures": [{"metric_id": "supplier_late_rate"}, {"metric_id": "supplier_fill_rate"}, {"metric_id": "matched_orders"}],
                                   "dimensions": [{"dimension_id": "supplier"}], "time": {"grain": "month", "range": find_range(text) or {"last": 12, "unit": "month"}},
                                   "purpose": "ask", "filters": find_members(text, members, ["category", "brand", "route", "origin", "sector"])}
        return PlanCandidate(intent="trend", query_spec=curated, visual_type="line",
                             explanation_plan=["rank suppliers by the change in late rate between the earlier and the recent half of the window",
                                               "state fill rate alongside, with the sample size", "name suppliers whose lateness cannot be measured (no promised dates)"],
                             source="rules", reasons=["deterioration question → supplier reliability over time"])

    metrics = find_metrics(text)
    if not metrics:
        return PlanCandidate(intent="unknown", query_spec={}, clarification=_clarify(locale), source="rules", reasons=["no governed metric named"])
    contracts = [semantic.METRICS[m] for m in metrics]
    allowed = [d for d in semantic.DIMENSIONS if all(d in c.allowed_dimensions for c in contracts)]
    dims = find_dimensions(text, allowed)
    grain = find_grain(text)
    filters = find_members(text, members, allowed)
    # a member the question names is a filter, not a breakdown, unless the breakdown was asked for too
    for f in filters:
        if f["dimension_id"] in dims and not re.search(r"\b(by|per|each|every)\s+" + "|".join(DIMENSION_WORDS[f["dimension_id"]]), text):
            dims = [d for d in dims if d != f["dimension_id"]]
    top_n = find_top_n(text)
    rank = _match_any(text, RANK_WORDS)
    trend = _match_any(text, TREND_WORDS) or grain is not None
    if rank and not dims and "supplier" in allowed and ("supplier" in text or "مورد" in text):
        dims = ["supplier"]
    if trend and "date" in allowed and grain is None:
        grain = "month"
    spec: dict[str, Any] = {"measures": [{"metric_id": m} for m in metrics], "dimensions": [{"dimension_id": d} for d in dims], "filters": filters, "purpose": "ask"}
    if grain and "date" in allowed and not any(c.aggregation_rule == "snapshot" for c in contracts):
        spec["time"] = {"grain": grain, "range": find_range(text) or ({"last": 12, "unit": "month"} if grain == "month" else {"last": 12, "unit": "week"} if grain == "week" else None)}
        if spec["time"]["range"] is None:
            spec["time"].pop("range")
    elif find_range(text) and "date" in allowed:
        spec["time"] = {"range": find_range(text)}
    if dims and (rank or top_n):
        spec["top_n"] = {"dimension_id": dims[0], "n": top_n or 10, "others": False, "by": metrics[0]}
    if _match_any(text, ("compared to", "versus", "vs ", "change", "growth", "period over period", "مقارنة")) and grain:
        spec["comparison"] = {"kind": "period_over_period", "lag": 1}
    intent = "trend" if grain else "ranking" if (rank and dims) else "composition" if (_match_any(text, COMPOSITION_WORDS) and dims) else "kpi" if not dims else "detail"
    return PlanCandidate(intent=intent, query_spec=spec, visual_type=None, source="rules",
                         reasons=[f"metrics: {', '.join(metrics)}", f"dimensions: {', '.join(dims) or 'none'}", f"grain: {grain or 'none'}"])


def _follow_up(text: str, previous: dict[str, Any], members: dict[str, list[str]], locale: str) -> PlanCandidate:
    spec: dict[str, Any] = {k: v for k, v in previous.items() if k in ("measures", "dimensions", "time", "filters", "top_n", "comparison", "sort", "limit")}
    spec.setdefault("filters", [])
    spec["purpose"] = "ask"
    reasons: list[str] = []
    contracts = [semantic.METRICS[m["metric_id"]] for m in spec.get("measures", []) if m.get("metric_id") in semantic.METRICS]
    fact = contracts[0].fact if contracts else None
    allowed = [d for d in semantic.DIMENSIONS if all(d in c.allowed_dimensions for c in contracts)] if contracts else []
    grain = find_grain(text)
    if grain and "date" in allowed:
        spec["time"] = {**(spec.get("time") or {}), "grain": grain}
        reasons.append(f"grain → {grain}")
    rng = find_range(text)
    if rng and "date" in allowed:
        spec["time"] = {**(spec.get("time") or {}), "range": rng}
        reasons.append("range changed")
    new_filters = find_members(text, members, allowed)
    if text.startswith(("only", "just", "فقط")) or new_filters:
        for f in new_filters:
            spec["filters"] = [x for x in spec["filters"] if x.get("dimension_id") != f["dimension_id"]] + [f]
        if new_filters:
            reasons.append("filter added: " + ", ".join(f["dimension_id"] for f in new_filters))
        elif text.startswith(("only", "just")):
            return PlanCandidate(intent="unknown", query_spec={}, clarification=("I could not find that member in your data. Name a category, brand, supplier, customer or site as it appears in the workspace." if locale == "en"
                                                                                   else "لم أجد هذه القيمة في بياناتك. اذكر فئة أو علامة أو مورداً أو عميلاً أو موقعاً كما يظهر في المساحة."), source="rules")
    if text.startswith(("add", "and ", "أضف", "include")) or "add " in text:
        extra = [m for m in find_metrics(text, fact) if m not in {x["metric_id"] for x in spec["measures"]}]
        if extra:
            spec["measures"] = spec["measures"] + [{"metric_id": m} for m in extra][: max(0, 6 - len(spec["measures"]))]
            reasons.append("measures added: " + ", ".join(extra))
        elif find_metrics(text):
            return PlanCandidate(intent="unknown", query_spec={}, clarification=("That measure is defined on different records and cannot be added to this query; ask for it on its own." if locale == "en"
                                                                                   else "هذا المقياس معرّف على سجلات مختلفة ولا يمكن إضافته إلى هذا الاستعلام؛ اطلبه وحده."), source="rules")
    dims = find_dimensions(text, allowed)
    if dims and (text.startswith(("by ", "break", "split")) or " by " in text):
        current = [d["dimension_id"] for d in spec.get("dimensions", [])]
        for d in dims:
            if d not in current and len(current) < 2:
                current.append(d)
        spec["dimensions"] = [{"dimension_id": d} for d in current]
        reasons.append("dimension added: " + ", ".join(dims))
    top = find_top_n(text)
    if top and spec.get("dimensions"):
        spec["top_n"] = {"dimension_id": spec["dimensions"][0]["dimension_id"], "n": top, "others": False, "by": spec["measures"][0]["metric_id"]}
        reasons.append(f"top {top}")
    if "remove" in text or "without" in text or "clear" in text:
        spec["filters"] = []
        reasons.append("filters cleared")
    intent = "trend" if (spec.get("time") or {}).get("grain") else "ranking" if spec.get("top_n") else "detail"
    return PlanCandidate(intent=intent, query_spec=spec, source="rules", reasons=reasons or ["follow-up kept the previous query"])


def _clarify(locale: str) -> str:
    if locale == "ar":
        return "لم أتعرف على مقياس محكوم في سؤالك. جرّب: الطلب حسب الفئة شهرياً، نسبة تلبية الموردين، أسابيع التغطية حسب المنتج، الأوامر المفتوحة حسب المورد."
    return ("I could not match a governed measure to that question. Try: demand by category each month, supplier fill rate over time, "
            "weeks of cover by product, open purchase orders by supplier, service level by customer.")

"""Ask ZAAD, end to end:

    question → context (schema, bounded members, warnings) → candidate plan (model or rules)
    → deterministic validation (one repair round) → the same query engine every surface uses
    → ResultSet → grounded interpretation → recommended VisualSpec

The model never runs anything. Its candidate is an `AnalyticsQuerySpec` that goes through the same
validator a human-built one does; a refused candidate is sent back once with the refusal, and a
second refusal falls back to the rules planner. The answer always carries the validated spec, the
result's provenance, the reasons present, and which planner produced the plan.
"""
from __future__ import annotations

import time
from typing import Any

from api.analytics import query
from api.analytics.ai import context as context_module
from api.analytics.ai import interpret as interpret_module
from api.analytics.ai import recommend, rules
from api.analytics.ai.provider import AnalysisProvider, PlanCandidate, default_provider
from api.analytics.contracts import AnalyticsQuerySpec, AnalyticsRefused, AskIn
from api.analytics.validate import validate
from api.product.governance import Actor

MAX_REPAIRS = 1


def _to_spec(candidate: PlanCandidate) -> AnalyticsQuerySpec:
    raw = dict(candidate.query_spec or {})
    raw.setdefault("purpose", "ask")
    raw.pop("semantic_model_version", None)
    # the model may name a version; the spec pins the current one
    try:
        return AnalyticsQuerySpec.model_validate(raw)
    except Exception as exc:  # noqa: BLE001 - pydantic's message names the field
        raise AnalyticsRefused("spec_invalid", f"The proposed query is malformed: {str(exc)[:300]}") from exc


def ask(conn: Any, operator: str, actor: Actor | None, body: AskIn, *, provider: AnalysisProvider | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    ctx = context_module.build(conn, operator, actor, body.question)
    previous = body.previous.canonical() if body.previous else None
    provider = provider if provider is not None else default_provider()
    attempts: list[dict[str, Any]] = []
    candidate: PlanCandidate | None = None
    validated = None

    def try_candidate(c: PlanCandidate) -> bool:
        nonlocal candidate, validated
        if c.clarification and not c.query_spec:
            attempts.append({"source": c.source, "outcome": "clarification"})
            return False
        try:
            spec = _to_spec(c)
            validated = validate(spec, actor)
            candidate = c
            attempts.append({"source": c.source, "outcome": "accepted"})
            return True
        except AnalyticsRefused as exc:
            attempts.append({"source": c.source, "outcome": "refused", "code": exc.code, "message": str(exc)})
            c.reasons.append(f"refused: {exc.code}")
            return False

    if provider is not None and provider.available():
        first = provider.plan(body.question, ctx, previous, body.locale)
        if first is not None and not try_candidate(first):
            last = attempts[-1]
            if last.get("outcome") == "refused":
                repaired = provider.plan(body.question, ctx, previous, body.locale, repair=f"{last['code']}: {last['message']}")
                if repaired is not None:
                    try_candidate(repaired)
    if candidate is None:
        fallback = rules.plan(body.question, ctx, previous, body.locale)
        if not try_candidate(fallback):
            return {"answered": False, "clarification": fallback.clarification or attempts[-1].get("message") or rules._clarify(body.locale),
                    "attempts": attempts, "planner": "rules", "warnings": ctx["warnings"], "data_cutoff": ctx["data_cutoff"], "timing_ms": round((time.perf_counter() - started) * 1000, 1)}
    assert candidate is not None and validated is not None

    result = query.run(conn, operator, actor, validated.spec)
    visual_type, why = recommend.recommend(validated, candidate.visual_type or (body.previous_visual_type if body.previous else None))
    title = _title(validated, body.locale)
    visual = recommend.visual_for(validated, visual_type, {"en": title["en"], "ar": title["ar"]}, {"en": title["description_en"], "ar": title["description_ar"]})
    deterministic = interpret_module.interpret(result, body.locale)
    narrative = None
    if provider is not None and provider.available():
        try:
            raw = provider.interpret(result, candidate, ctx, body.locale)
            narrative = interpret_module.grounded(raw, result) if raw else None
        except Exception:  # noqa: BLE001 - the deterministic claims stand on their own
            narrative = None
    claims = [{"kind": c.kind, "text": c.text, "source": "model"} for c in (narrative.claims if narrative else [])] + \
             [{"kind": c.kind, "text": c.text, "source": "rules"} for c in deterministic.claims]
    return {
        "answered": True, "question": body.question, "intent": candidate.intent, "planner": candidate.source, "attempts": attempts,
        "spec": validated.spec.canonical(), "visual": visual.model_dump(mode="json"), "visual_reason": why, "result": result,
        "claims": claims, "explanation_plan": candidate.explanation_plan, "clarification": candidate.clarification,
        "reasons_present": sorted({c.get("reason") for row in result["rows"] for c in row if isinstance(c, dict) and c.get("reason")}),
        "warnings": ctx["warnings"], "data_cutoff": ctx["data_cutoff"], "dataset_version": result["dataset_version"],
        "handoff": _handoff_hint(validated, result), "timing_ms": round((time.perf_counter() - started) * 1000, 1),
    }


def _title(validated, locale: str) -> dict[str, str]:
    metrics_en = ", ".join(m.display_name["en"] for m in validated.metrics)
    metrics_ar = "، ".join(m.display_name["ar"] for m in validated.metrics)
    dims_en = " × ".join(d.dimension.label["en"] if d.dimension.kind != "time" else (d.level or "week") for d in validated.dimensions)
    dims_ar = " × ".join(d.dimension.label["ar"] for d in validated.dimensions)
    title_en = f"{metrics_en}" + (f" by {dims_en}" if dims_en else "")
    title_ar = f"{metrics_ar}" + (f" حسب {dims_ar}" if dims_ar else "")
    definition = "; ".join(f"{m.display_name['en']}: {m.description['en']}" for m in validated.metrics)
    definition_ar = "؛ ".join(f"{m.display_name['ar']}: {m.description['ar']}" for m in validated.metrics)
    filters = ", ".join(f"{f.dimension.label['en']} {f.op} {', '.join(f.values)}" for f in validated.filters)
    return {"en": title_en[:160], "ar": title_ar[:160], "description_en": (definition + (f" Filters: {filters}." if filters else ""))[:600], "description_ar": definition_ar[:600]}


def _handoff_hint(validated, result: dict[str, Any]) -> dict[str, Any]:
    """Identifiers a hand-off to the optimizer could carry, from the result's own members."""
    dims = [c["id"] for c in result["columns"] if c["kind"] == "dimension"]
    skus: list[str] = []
    suppliers: list[str] = []
    for row in result["rows"]:
        for i, d in enumerate(dims):
            v = row[i]
            if isinstance(v, dict) or v is None:
                continue
            if d == "sku" and len(skus) < 50:
                skus.append(str(v))
            if d == "supplier" and len(suppliers) < 20:
                suppliers.append(str(v))
    for f in validated.filters:
        if f.dimension.id == "sku":
            skus.extend(x for x in f.values if x not in skus)
        if f.dimension.id == "supplier":
            suppliers.extend(x for x in f.values if x not in suppliers)
    return {"possible": bool(skus or suppliers), "skus": skus[:50], "suppliers": suppliers[:20]}

"""The workspace assistant: a plain-language reading of the operator's state
and the latest diagnostic, and answers to questions about them.

The assistant only ever sees what the workspace already computed: the
state estimate, the latest diagnostic summary and the table counts. It is
told to use only those figures. With ANTHROPIC_API_KEY set it talks to
Claude; without it, it returns the deterministic explanation from
adaptive/plain_language.py so the feature degrades to a still-useful text.

  GET  /assistant/summary?lang=en|ar   plain-language summary of the workspace
  POST /assistant/ask                  {question, history?, lang?} -> {answer}
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from adaptive.plain_language import explain_state, state_summary_text
from api.dependencies import capability, get_conn, rate_limiter, require_operator

router = APIRouter(prefix="/assistant", tags=["assistant"])
log = logging.getLogger("harvestmind.assistant")

MODEL = os.environ.get("HARVESTMIND_ASSISTANT_MODEL", "claude-opus-5")

SYSTEM = """You are the assistant inside Zaad Supply, a purchasing diagnostic for distributors that import what they sell.
You explain the workspace's numbers to a buyer or owner in plain language.

Rules:
- Use only the figures in the CONTEXT. If something is not in it, say it is not available in this workspace rather than guessing.
- Never promise or estimate savings. The product reports backtests on the operator's own history, not forecasts.
- "Incumbent" means the operator's current ordering policy as read from their history; call it "your current policy".
- Be concrete and short: a few sentences or a short list. No headings. No em dashes.
- If asked in Arabic, or if lang is "ar", answer in Arabic using trade wording (أوامر الشراء، سندات الاستلام، الجرد، مدة التوريد، الموردون، خطوط الشحن).
- Keep the operator's identifiers as given; do not invent SKU names or supplier names."""


def _context(conn, authed: str | None) -> dict[str, Any]:
    from api.routers.fmcg import _replan_triggers, _state_for, build_inputs, latest_gate_decision
    from api.routers.intake import STAGING_TABLES
    counts = {}
    for t in STAGING_TABLES:
        try:
            row = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()  # noqa: S608  # nosec B608 - allowlisted names
            counts[t] = int(row[0]) if row else 0
        except Exception:  # noqa: BLE001
            counts[t] = 0
    ctx: dict[str, Any] = {"tables": {k: v for k, v in counts.items() if v}}
    try:
        fi, report = build_inputs(conn, horizon=12, train_weeks=52, service_level=0.97, holding_rate_per_week=None,
                                  currency="USD", incumbent_cover_weeks=None)
        est, src = _state_for(fi)
        state = {**est.as_dict(), "mode": est.posture.mode, "replan_triggers": _replan_triggers(est)}
        state.pop("sku", None)
        state.pop("supplier", None)
        state.pop("signals", None)
        ctx["state"] = state
        ctx["plain"] = explain_state(state)
        ctx["incumbent"] = report.get("incumbent")
        ctx["warnings"] = list(report.get("warnings", []))[:8]
        ctx["diagnostic"] = latest_gate_decision(authed, n_products=len(fi.products),
                                                 history_periods=min(len(v) for v in fi.train_demand.values()) if fi.train_demand else 0)
    except HTTPException as exc:
        ctx["state_unavailable"] = str(exc.detail)
    except Exception as exc:  # noqa: BLE001
        ctx["state_unavailable"] = f"{type(exc).__name__}: {exc}"[:200]
    return ctx


def _model_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _ask_model(ctx: dict, question: str, history: list[dict], lang: str) -> str:
    import anthropic
    client = anthropic.Anthropic()
    context_text = json.dumps(ctx, default=str, sort_keys=True)[:60000]
    messages: list[dict] = []
    for turn in history[-8:]:
        role = "user" if turn.get("role") == "user" else "assistant"
        text = str(turn.get("content", ""))[:4000]
        if text:
            messages.append({"role": role, "content": text})
    messages.append({"role": "user", "content": f"(lang={lang}) {question}"})
    try:
        response = client.messages.create(  # type: ignore[call-overload]  # dict literals; shapes per SDK docs
            model=MODEL,
            max_tokens=2000,
            thinking={"type": "adaptive"},
            output_config={"effort": "low"},
            system=[
                {"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": "CONTEXT (this workspace, computed by the engine):\n" + context_text},
            ],
            messages=messages,
        )
    except anthropic.RateLimitError:
        raise HTTPException(429, "The assistant is busy; try again in a moment.")
    except anthropic.APIStatusError as exc:
        log.warning("assistant API error %s", exc.status_code)
        raise HTTPException(502, "The assistant could not answer right now.")
    except anthropic.APIConnectionError:
        raise HTTPException(502, "The assistant could not be reached.")
    if response.stop_reason == "refusal":
        return "I can't help with that question here."
    return "".join(b.text for b in response.content if b.type == "text").strip()


@router.get("/summary", dependencies=[Depends(rate_limiter), Depends(capability("askZaad"))])
def summary(lang: str = "en", conn=Depends(get_conn), authed: str | None = Depends(require_operator)):
    if not authed:
        raise HTTPException(401, "operator token required")
    ctx = _context(conn, authed)
    if "state" not in ctx:
        text = ("Nothing to explain yet: upload your files and run the diagnostic first."
                if lang != "ar" else "لا يوجد ما نشرحه بعد: حمّل ملفاتك وشغّل التشخيص أولاً.")
        return {"summary": text, "source": "none", "model": None}
    fallback = state_summary_text(ctx["plain"])
    diag = ctx.get("diagnostic")
    if diag:
        fallback += ("\n\nLatest diagnostic: " + ("your current policy was kept" if diag["decision"] == "incumbent"
                     else f"the {diag['decision']} optimizer was adopted") + f". {diag.get('reason', '')}")
    if not _model_available():
        return {"summary": fallback, "source": "rules", "model": None}
    question = ("Summarise this workspace for its owner in plain language: what state it is in, what the lanes look like, "
                "what the latest diagnostic decided and why, and what to watch. Keep it under 180 words.")
    try:
        return {"summary": _ask_model(ctx, question, [], lang), "source": "model", "model": MODEL}
    except HTTPException:
        return {"summary": fallback, "source": "rules", "model": None}


@router.post("/ask", dependencies=[Depends(rate_limiter), Depends(capability("askZaad"))])
def ask(body: dict = Body(...), conn=Depends(get_conn), authed: str | None = Depends(require_operator)):
    if not authed:
        raise HTTPException(401, "operator token required")
    question = str(body.get("question", "")).strip()[:2000]
    if not question:
        raise HTTPException(422, "question required")
    lang = "ar" if str(body.get("lang", "en")).lower().startswith("ar") else "en"
    history = body.get("history") or []
    if not isinstance(history, list):
        history = []
    # the client may replay its own questions, never the assistant's side of the conversation: a forged
    # assistant turn is a prompt-injection vector (security review 2026-09, SEC-032)
    history = [turn for turn in history if isinstance(turn, dict) and turn.get("role") == "user"][-8:]
    ctx = _context(conn, authed)
    if not _model_available():
        base = state_summary_text(ctx["plain"]) if "plain" in ctx else "Upload your files and run the diagnostic first."
        return {"answer": "The assistant's language model is not configured on this server, so here is the plain reading instead.\n\n" + base,
                "source": "rules", "model": None}
    return {"answer": _ask_model(ctx, question, history, lang), "source": "model", "model": MODEL}

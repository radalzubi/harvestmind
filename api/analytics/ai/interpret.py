"""Deterministic interpretation of a result: typed claims built only from cells that exist.

Every claim is OBSERVATION (a count or a ratio over rows), ASSOCIATION (where something
concentrates), MODELED (a plan-ledger difference), PLAN_RESULT (what the plan carries) or MISSING
(a reason word restated as missing data). Nothing here says "because", and nothing says "saving".
The model's narrative, when there is one, is kept only if every number in it appears in the result.
"""
from __future__ import annotations

import re
from typing import Any

from api.analytics.ai.provider import Claim, Interpretation
from api.analytics.semantic import METRICS

_KIND = {"OBSERVED_FACT": "OBSERVATION", "ASSOCIATION": "ASSOCIATION", "MODELED": "MODELED", "PLAN_SNAPSHOT": "PLAN_RESULT"}


def _fmt(value: Any, unit: str, locale: str) -> str:
    if isinstance(value, dict):
        value = value.get("value")
    if value is None:
        return "—"
    if unit == "ratio":
        return f"{float(value) * 100:.1f}%"
    if unit in ("days", "weeks"):
        return f"{float(value):.1f} {unit}"
    if unit == "money":
        return f"{float(value):,.0f}"
    return f"{float(value):,.0f}" if float(value) == int(float(value)) else f"{float(value):,.1f}"


def _cell(cell: Any) -> tuple[float | None, str | None]:
    if isinstance(cell, dict):
        return (float(cell["value"]) if cell.get("value") is not None else None), cell.get("reason")
    if cell is None:
        return None, "UNKNOWN"
    return float(cell), None


def interpret(result: dict[str, Any], locale: str = "en") -> Interpretation:
    columns = result["columns"]
    dims = [c for c in columns if c["kind"] == "dimension"]
    measures = [c for c in columns if c["kind"] == "measure"]
    rows = result["rows"]
    claims: list[Claim] = []
    if result.get("empty"):
        for i, m in enumerate(measures):
            cell = rows[0][len(dims) + i] if rows else None
            _, reason = _cell(cell)
            why = cell.get("why") if isinstance(cell, dict) else ""
            claims.append(Claim("MISSING", f"{m['label'].get(locale, m['label']['en'])}: {reason} — {why}"))
        return Interpretation(claims=claims[:5], source="rules")

    time_idx = next((i for i, d in enumerate(dims) if d.get("dimension_kind") == "time"), None)
    member_idx = [i for i, d in enumerate(dims) if d.get("dimension_kind") != "time"]
    for j, m in enumerate(measures[:3]):
        col = len(dims) + j
        contract = METRICS.get(m["metric_id"])
        kind = _KIND.get(m.get("evidence_class") or "", "OBSERVATION")
        label = m["label"].get(locale, m["label"]["en"])
        unit = m.get("unit") or ""
        values = [(r, *_cell(r[col])) for r in rows]
        present = [(r, v) for r, v, _ in values if v is not None]
        missing = [(r, reason) for r, v, reason in values if v is None]
        if not present:
            reasons = sorted({reason for _, reason in missing if reason})
            claims.append(Claim("MISSING", f"{label} is not available in this scope ({', '.join(reasons) or 'UNKNOWN'})."))
            continue
        total = (result.get("coverage") or {}).get(m["metric_id"], {}).get("total")
        if time_idx is not None and not member_idx:
            first, last = present[0], present[-1]
            direction = "rose" if last[1] > first[1] else "fell" if last[1] < first[1] else "was flat"
            claims.append(Claim(kind, f"{label} {direction} from {_fmt(first[1], unit, locale)} ({str(first[0][time_idx])[:10]}) to {_fmt(last[1], unit, locale)} ({str(last[0][time_idx])[:10]}) over {len(present)} periods."))
        elif member_idx and time_idx is None:
            ranked = sorted(present, key=lambda x: x[1], reverse=True)
            top, bottom = ranked[0], ranked[-1]
            name = lambda r: " / ".join(str(r[i]) if not isinstance(r[i], dict) else "?" for i in member_idx)  # noqa: E731
            claims.append(Claim(kind, f"{label}: highest {name(top[0])} at {_fmt(top[1], unit, locale)}, lowest {name(bottom[0])} at {_fmt(bottom[1], unit, locale)}, across {len(present)} members."))
            if contract and contract.additive and len(ranked) >= 3:
                share_top = sum(v for _, v in ranked[:3]) / sum(v for _, v in ranked) if sum(v for _, v in ranked) else None
                if share_top is not None:
                    claims.append(Claim("ASSOCIATION", f"The top three members hold {share_top * 100:.0f}% of {label.lower()}. This is where it concentrates, not a cause."))
        elif member_idx and time_idx is not None:
            by_member: dict[str, list[tuple[str, float]]] = {}
            for r, v in present:
                key = str(r[member_idx[0]])
                by_member.setdefault(key, []).append((str(r[time_idx])[:10], v))
            moves = []
            for key, series in by_member.items():
                series.sort()
                if len(series) >= 4:
                    half = len(series) // 2
                    earlier = sum(v for _, v in series[:half]) / half
                    recent = sum(v for _, v in series[half:]) / (len(series) - half)
                    moves.append((recent - earlier, key, earlier, recent, len(series)))
            if moves:
                worse_is_up = unit == "ratio" and m["metric_id"] in ("supplier_late_rate", "short_fill_rate", "override_rate")
                moves.sort(reverse=worse_is_up)
                d, key, earlier, recent, n = moves[0]
                verb = ("worsened" if (d > 0) == worse_is_up else "improved") if d != 0 else "held"
                claims.append(Claim(kind, f"{label}: {key} {verb} most, from {_fmt(earlier, unit, locale)} (earlier half) to {_fmt(recent, unit, locale)} (recent half) over {n} periods."))
                claims.append(Claim("ASSOCIATION", f"{len(moves)} members had enough periods to compare; a change over a window is a direction, not a cause."))
        else:
            v = present[0][1]
            claims.append(Claim(kind, f"{label}: {_fmt(v, unit, locale)}" + (f" (total {_fmt(total, unit, locale)})" if isinstance(total, dict) and total.get('value') is not None and total.get('value') != v else "") + "."))
        if missing:
            reasons = sorted({reason for _, reason in missing if reason})
            claims.append(Claim("MISSING", f"{len(missing)} of {len(rows)} rows have no {label.lower()} ({', '.join(reasons)}); they are not zero."))
    for dim, why in (result.get("provenance") or {}).get("blocked", {}).items():
        claims.append(Claim("MISSING", f"{dim}: {why.get('reason')} — {why.get('why')}"))
    if result.get("bounds", {}).get("truncated"):
        claims.append(Claim("MISSING", f"Only the first {result['bounds']['limit_applied']} rows are shown; narrow the filters or use top-N for the rest."))
    return Interpretation(claims=claims[:6], source="rules")


_NUMBER = re.compile(r"\d[\d,]*\.?\d*")


def grounded(narrative: Interpretation, result: dict[str, Any]) -> Interpretation | None:
    """Keep a model narrative only if every number it states appears in the result (within rounding)."""
    present: set[str] = set()

    def add(v: Any) -> None:
        if isinstance(v, dict):
            v = v.get("value")
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            for text in (f"{v:.0f}", f"{v:.1f}", f"{v:.2f}", f"{v:,.0f}", f"{v:,.1f}", f"{v * 100:.0f}", f"{v * 100:.1f}", f"{v * 100:.2f}"):
                present.add(text.replace(",", ""))
        elif isinstance(v, str) and len(v) >= 4 and v[:4].isdigit():
            present.add(v[:4])
            present.add(v[:10].replace("-", ""))
    for row in result["rows"]:
        for cell in row:
            add(cell)
    for cov in (result.get("coverage") or {}).values():
        add(cov.get("total"))
        add(cov.get("rows"))
    keep: list[Claim] = []
    for claim in narrative.claims:
        ok = True
        for token in _NUMBER.findall(claim.text):
            t = token.replace(",", "").rstrip(".")
            if not t:
                continue
            if t in present or t.replace("-", "") in present:
                continue
            try:
                f = float(t)
            except ValueError:
                continue
            if any(abs(f - float(p)) <= max(0.5, abs(f) * 0.005) for p in present if _is_number(p)):
                continue
            ok = False
            break
        if ok and claim.kind in ("OBSERVATION", "ASSOCIATION", "MODELED", "PLAN_RESULT", "MISSING"):
            keep.append(claim)
    return Interpretation(claims=keep, source="model") if keep else None


def _is_number(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        return False

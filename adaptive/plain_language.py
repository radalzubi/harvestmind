"""Plain-language reading of the state estimate.

Everything the State page shows has a number behind it; this turns those
numbers into sentences a buyer can read without knowing the vocabulary.
Deterministic, no model involved, so it is also the fallback the assistant
uses when no language model is configured. Nothing here invents a figure:
every sentence carries the value it was built from.
"""
from __future__ import annotations

import re

REGIME_WORDS = {
    "NORMAL": "normal", "CALM": "calm", "WATCH": "worth watching",
    "PORT_DISRUPTION": "a port disruption", "ROUTE_DISRUPTION": "a shipping-route disruption",
    "SUPPLIER_DEGRADED": "a supplier slipping", "SUPPLIER_FAILURE": "a supplier failing",
    "DEMAND_VOLATILE": "unusually swingy demand", "DEMAND_SHIFT": "a lasting change in demand",
    "RECOVERY": "recovering after a disruption", "CAPACITY_CONSTRAINED": "a capacity squeeze",
}
CANDIDATE_WORDS = {
    "order_up_to": "a simple order-up-to rule", "deterministic_sp": "the plain optimizer",
    "stochastic_sp": "the optimizer that plans across many demand scenarios",
    "anchored_sp": "the optimizer kept close to your current orders",
    "adaptive_sp": "the state-aware optimizer", "incumbent": "your current policy",
}
LANE_WORDS = {"aqaba": "Aqaba (sea)", "red_sea": "the Red Sea route", "hormuz": "the Strait of Hormuz route",
              "suez": "the Suez route", "road_saudi": "the road lane through Saudi Arabia",
              "road_syria": "the road lane through Syria", "road_iraq": "the road lane through Iraq", "air": "air freight"}
MODE_WORDS = {
    "EFFICIENCY": "Conditions look calm. The optimizer is free to chase ordinary cost savings, and the evidence gate still has to prove any change on your own history before it is adopted.",
    "BALANCED": "Something is moving. The optimizer stays within a band around your current orders and weighs bad outcomes more heavily.",
    "PROTECTION": "Conditions are disrupted. The optimizer stays very close to your current orders, weighs bad outcomes heavily, and commits only one week at a time.",
}


def regime_word(name: str) -> str:
    return REGIME_WORDS.get(name, name.replace("_", " ").lower())


def lane_word(route: str) -> str:
    return LANE_WORDS.get(route, route.replace("_", " "))


def _level(x: float, low: float, high: float, words=("low", "moderate", "high")) -> str:
    return words[0] if x < low else words[1] if x < high else words[2]


def plain_reason(text: str) -> str:
    """Rewrite one machine reason into a sentence, keeping its numbers."""
    m = re.match(r"^(?P<sku>[\w-]+): demand CV (?P<cv>[\d.]+), zero-share (?P<z>\d+)%$", text)
    if m:
        cv = float(m["cv"])
        z = int(m["z"])
        swing = "swings a lot" if cv >= 1.0 else "swings noticeably" if cv >= 0.6 else "is fairly steady"
        return f"{m['sku']}: weekly demand {swing} (variation {cv:.2f}) and {z}% of weeks had no sales at all."
    m = re.match(r"^(?P<name>.+?) transits at (?P<pct>\d+)% of their trailing norm$", text)
    if m:
        return f"Ships passing the {m['name']} are at {m['pct']}% of their usual number."
    m = re.match(r"^gscpi elevated \((?P<v>[\d.]+)\)$", text)
    if m:
        return f"The global supply-chain pressure index is elevated ({m['v']}, where 0 is normal)."
    m = re.match(r"^fuel_index elevated \((?P<v>[\d.]+)\)$", text)
    if m:
        return f"Fuel prices are {round((float(m['v']) - 1) * 100)}% above their trailing norm."
    m = re.match(r"^(?P<k>[a-z_]+) elevated \((?P<v>[\d.]+)\)$", text)
    if m:
        return f"The {m['k'].replace('_', ' ')} indicator is elevated ({m['v']})."
    m = re.match(r"^(?P<k>[a-z_]+) (?P<state>unavailable|stale)", text)
    if m:
        return f"The {m['k'].replace('_', ' ')} feed is {m['state']}, so it adds no evidence."
    return text


def plain_trigger(text: str) -> str:
    table = [
        (r"portfolio p\(disruptive\) crosses ([\d.]+) \(enter\)", lambda m: f"The chance that your suppliers or lanes are disrupted rises above {int(float(m[1]) * 100)}%."),
        (r"portfolio p\(disruptive\) drops below ([\d.]+)", lambda m: f"The chance of disruption falls back below {int(float(m[1]) * 100)}%."),
        (r"change-point alarm on any supplier", lambda m: "A supplier starts delivering later or shorter than its own history."),
        (r"demand level shift beyond (\d+) sd on any SKU", lambda m: f"Demand for any SKU moves more than {m[1]} standard deviations from its usual level and stays there."),
        (r"port throughput index below ([\d.]+)", lambda m: f"Traffic through a port you use drops below {int(float(m[1]) * 100)}% of normal, or the feed goes stale."),
        (r"inventory discrepancy above (\d+)%", lambda m: f"A stock count differs from the book figure by more than {m[1]}%."),
        (r"promotion calendar change", lambda m: "A promotion is added or moved inside the planning horizon."),
    ]
    for pat, fn in table:
        m = re.search(pat, text)
        if m:
            return fn(m)
    return text


def explain_state(state: dict) -> dict:
    """Sentences for each block of the State page plus a two-line headline."""
    port = state.get("portfolio", {})
    post = state.get("posture", {})
    probs = port.get("probabilities", {}) or {}
    dominant = port.get("dominant", "NORMAL")
    p_dom = probs.get(dominant, 0.0)
    stress = float(port.get("stress", 0.0))
    quality = float(port.get("data_quality", 0.0))
    p_disruptive = sum(v for k, v in probs.items() if k not in ("NORMAL", "CALM", "WATCH"))
    mode = state.get("mode", post.get("mode", "EFFICIENCY"))

    regime = (
        f"The most likely picture of your operation right now is {regime_word(dominant)} "
        f"({int(round(p_dom * 100))}% likely). Disruption of some kind sits at about {int(round(p_disruptive * 100))}%. "
        f"Stress on the business from uncertainty is {_level(stress, 0.3, 0.6)} ({stress:.2f} on a 0 to 1 scale), "
        f"and the data behind this reading is {_level(quality, 0.6, 0.85, ('thin', 'fair', 'good'))} ({quality:.2f})."
    )
    regime_reasons = [plain_reason(r) for r in port.get("reasons", [])[:5]]

    cw = int(post.get("commit_window", 0) or 0)
    lam = float(post.get("cvar_lambda", 0.0) or 0.0)
    width = float(post.get("scenario_width", 1.0) or 1.0)
    auto = float(post.get("autonomy", 0.0) or 0.0)
    cands = [CANDIDATE_WORDS.get(c, c) for c in post.get("candidates", [])]
    posture = [
        f"Orders for the next {cw} week{'s' if cw != 1 else ''} are firm; later weeks are advisory and get re-planned at the next review.",
        f"Caution is {_level(lam, 0.35, 0.65)} ({lam:.2f}): that is how much the plan pays to avoid bad weeks rather than chase the average.",
        f"It plans against a {_level(width, 0.9, 1.1, ('narrow', 'normal', 'wide'))} range of possible futures ({width:.2f}, where 1 is normal).",
        f"On its own it may change your orders {_level(auto, 0.3, 0.6, ('very little', 'moderately', 'freely'))} ({auto:.2f} on a 0 to 1 scale); anything beyond that needs the evidence gate.",
        ("Optimizers allowed to compete against your current policy: " + ", ".join(cands) + ".") if cands else "No optimizer is allowed to compete with your current policy in this state.",
    ]

    lanes = []
    for route, o in (state.get("outlooks") or {}).items():
        risk = float(o.get("risk", 0.0))
        q = float(o.get("quality", 0.0))
        lanes.append({
            "lane": lane_word(route),
            "sentence": f"{lane_word(route)}: risk is {_level(risk, 0.3, 0.55, ('low', 'moderate', 'elevated'))} ({int(round(risk * 100))}%), "
                        f"on {_level(q, 0.5, 0.8, ('thin', 'fair', 'strong'))} evidence ({q:.2f}).",
            "reasons": [plain_reason(r) for r in o.get("reasons", [])],
            "missing": list(o.get("missing", [])),
        })

    triggers = [plain_trigger(t) for t in state.get("replan_triggers", [])]

    headline = MODE_WORDS.get(mode, f"Mode {mode}.")
    if lanes:
        risks = {lane_word(r): float(o.get("risk", 0.0)) for r, o in state["outlooks"].items()}
        worst = max(lanes, key=lambda item: risks.get(item["lane"], 0.0))
        headline += " " + worst["sentence"]

    return {"headline": headline, "regime": regime, "regime_reasons": regime_reasons, "posture": posture,
            "lanes": lanes, "triggers": triggers,
            "glossary": {
                "Your current policy": "How you order today, read from your own history: reorder points, order quantities and cadence per SKU. Every optimizer has to beat it on your past before it may change anything.",
                "Evidence gate": "The check that only adopts an optimizer if its conservative lower bound beat your current policy on held-out weeks of your history.",
                "Regime": "The state your suppliers, lanes and demand appear to be in, as a set of probabilities rather than a single label.",
                "Lane risk": "The chance of a delay or shortfall on a shipping lane over the coming weeks, from public port, chokepoint and freight data.",
            }}


def state_summary_text(plain: dict) -> str:
    """One readable block, used when no language model is configured."""
    parts = [plain["headline"], "", plain["regime"]]
    if plain["regime_reasons"]:
        parts += ["Why: " + " ".join(plain["regime_reasons"])]
    parts += ["", "What the optimizer is allowed to do: " + " ".join(plain["posture"])]
    if plain["lanes"]:
        parts += ["", "Supply lanes:"] + [f"- {ln['sentence']} {' '.join(ln['reasons'])}" for ln in plain["lanes"]]
    if plain["triggers"]:
        parts += ["", "The plan is redone early if: " + " ".join(plain["triggers"])]
    return "\n".join(parts)

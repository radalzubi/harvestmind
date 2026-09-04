"""State -> optimization posture. The engine changes HOW it optimizes, not
just which solver runs.

A ``Posture`` carries every state-dependent knob the pipeline reads:
scenario width and persistence, the CVaR weight and level on baseline-
relative regret, the regret budget, the per-SKU anchoring scale and trust
region, the plan-stability cost, the commit window, the selection
thresholds, and which candidates are admitted. The mapping is monotone
in the disruption probability and the stress score, and the autonomy
score summarises how much freedom the optimizer is being given and why.
All constants below are configuration, developed on the calibration
archetypes and never tuned against the frozen evaluation seeds.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from adaptive.state_estimator import EntityState


@dataclass
class PostureConfig:
    # Mode thresholds on severity t (with the trackers' hysteresis upstream):
    # EFFICIENCY below efficiency_max, PROTECTION above protection_min.
    efficiency_max: float = 0.25
    protection_min: float = 0.55
    # scenario generation
    width_calm: float = 0.85          # scale on demand spread when calm
    width_disrupted: float = 1.35
    persistence_calm: int = 2         # block length in periods
    persistence_disrupted: int = 5
    # risk aversion on baseline-relative regret
    lambda_calm: float = 0.10
    lambda_disrupted: float = 1.00
    alpha_calm: float = 0.80
    alpha_disrupted: float = 0.95
    # anchoring / trust region (fraction of incumbent quantity per SKU)
    # EFFICIENCY mode: the optimizer optimises ordinary expected cost with
    # the region OFF and a light anchor; the safe gate (evidence on the
    # operator's own history) is what still protects the incumbent.
    rho_scale_efficiency: float = 0.25
    rho_scale_calm: float = 0.75
    rho_scale_disrupted: float = 0.25
    trust_off: float = 1.0            # >= 1 disables the region in the MILP
    trust_low: float = 0.05
    trust_medium: float = 0.15
    trust_high: float = 0.40
    trust_severe: float = 0.80
    # plan stability (fraction of unit cost per unit changed vs previous plan)
    change_cost_calm: float = 0.02
    change_cost_disrupted: float = 0.005
    # selection gate: a normal bar in EFFICIENCY mode (beat the incumbent on
    # the operator's own history), a stricter one as protection tightens
    min_rel_improvement_efficiency: float = 0.02
    min_rel_improvement_calm: float = 0.03
    min_rel_improvement_disrupted: float = 0.02
    confidence_efficiency: float = 0.80
    confidence_calm: float = 0.85
    confidence_disrupted: float = 0.75
    # demand channel: how much demand severity opens the trust region upside
    demand_trust_open: float = 0.60
    # commitment
    commit_calm: int = 4
    commit_disrupted: int = 1
    # robust candidate admission
    robust_min_p_disruptive: float = 0.5
    robust_max_data_quality: float = 0.6


@dataclass
class Posture:
    p_disruptive: float
    stress: float
    mode: str = "BALANCED"            # EFFICIENCY | BALANCED | PROTECTION
    demand_severity: float = 0.0
    outlook_risk: float = 0.0
    autonomy: float = 0.0
    dominant: str = "NORMAL"
    scenario_width: float = 1.0
    persistence: int = 2
    cvar_lambda: float = 0.1
    cvar_alpha: float = 0.8
    regret_budget_share: float | None = None
    rho_scale: float = 1.0
    trust_region: dict = field(default_factory=dict)      # sku -> fraction (>= 1 = off)
    change_cost_rate: float = 0.02
    commit_window: int = 4
    min_rel_improvement: float = 0.03
    confidence: float = 0.85
    candidates: tuple = ()
    reasons: list = field(default_factory=list)
    config: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = dict(self.__dict__)
        d["candidates"] = list(self.candidates)
        return d


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))


def autonomy_score(portfolio: EntityState, evidence_strength: float, calibration_confidence: float,
                   economics_quality: float) -> tuple[float, list]:
    """How much freedom the optimizer gets, in [0, 1], with the reasons.

    Freedom rises with the economic importance of uncertainty (stress) and
    with the strength of evidence that a candidate beats the incumbent; it
    falls with poor data quality, poor calibration confidence and unknown
    economics. Less evidence = less autonomy, always."""
    reasons = []
    base = 0.15 + 0.45 * portfolio.stress + 0.40 * evidence_strength
    reasons.append(f"stress {portfolio.stress:.2f} and evidence {evidence_strength:.2f} set a base of {base:.2f}")
    caps = []
    if portfolio.data_quality < 0.6:
        caps.append(("data quality", 0.35 + 0.5 * portfolio.data_quality))
    if calibration_confidence < 0.5:
        caps.append(("scenario calibration confidence", 0.45 + 0.5 * calibration_confidence))
    if economics_quality < 0.7:
        caps.append(("economics provenance", 0.3 + 0.6 * economics_quality))
    a = base
    for name, cap in caps:
        if a > cap:
            reasons.append(f"capped at {cap:.2f} by {name}")
            a = cap
    return float(max(0.0, min(1.0, a))), reasons


def posture_from_state(portfolio: EntityState, sku_states: dict, *, evidence_strength: float = 0.0,
                       calibration_confidence: float = 0.5, economics_quality: float = 1.0,
                       tracker_disrupted: bool | None = None, sku_flags: dict | None = None,
                       cfg: PostureConfig | None = None) -> Posture:
    cfg = cfg or PostureConfig()
    p_dis = portfolio.p_disruptive()
    share = float(portfolio.features.get("value_share_disrupted", 0.0))
    if tracker_disrupted is not None:
        # hysteresis: the tracker's posture flag dominates a transient dip
        p_eff = max(p_dis, 0.6) if tracker_disrupted else p_dis
    else:
        p_eff = p_dis
    outlook_risk = float(max([float(s.features.get("outlook_risk", 0.0)) for s in sku_states.values()] + [0.0]))
    t = max(p_eff, portfolio.stress, share)                # supply severity in [0, 1]
    d_sev = float(portfolio.features.get("demand_severity", 0.0))
    sku_flags = sku_flags or {}
    auton, why = autonomy_score(portfolio, evidence_strength, calibration_confidence, economics_quality)
    mode = "EFFICIENCY" if t < cfg.efficiency_max else ("PROTECTION" if t >= cfg.protection_min else "BALANCED")
    trust: dict = {}
    for j, s in sku_states.items():
        sev = max(s.p_disruptive(), s.stress, 0.6 if sku_flags.get(j) else 0.0)
        if mode == "EFFICIENCY":
            frac = cfg.trust_off                       # optimise freely; the gate protects
        elif s.probabilities.get("SEVERE_DISRUPTION", 0.0) > 0.4 or sev > 0.8:
            frac = cfg.trust_severe
        elif sev > 0.5:
            frac = cfg.trust_high
        elif sev > 0.25:
            frac = cfg.trust_medium
        else:
            frac = cfg.trust_low
        if frac < 1.0:
            # autonomy scales the region: low autonomy keeps every SKU tight;
            # demand severity opens it (a surge needs room to order more)
            frac = frac * (0.5 + 0.5 * auton) + cfg.demand_trust_open * float(s.features.get("demand_severity", 0.0))
        trust[j] = round(min(frac, 1.0), 4)
    dominant = portfolio.dominant
    if mode == "EFFICIENCY":
        candidates: list = ["order_up_to", "deterministic_sp", "stochastic_sp", "anchored_sp", "adaptive_sp"]
    else:
        candidates = ["order_up_to", "deterministic_sp", "anchored_sp", "adaptive_sp"]
        if t > 0.45 or d_sev > 0.4:
            candidates += ["stochastic_sp"]
    if p_dis > cfg.robust_min_p_disruptive and (portfolio.data_quality < cfg.robust_max_data_quality
                                                or calibration_confidence < 0.5):
        candidates += ["dro"]
    width_t = max(t, d_sev)
    reasons = [f"{mode}: portfolio {dominant} ({portfolio.probabilities[dominant]:.0%}), p(disruptive) {p_dis:.0%}, "
               f"value share in disrupted SKUs {share:.0%}, stress {portfolio.stress:.2f}, "
               f"demand severity {d_sev:.2f}, leading-indicator risk {outlook_risk:.0%}"]
    if tracker_disrupted:
        reasons.append("hysteresis holds the disrupted posture until the exit threshold persists")
    reasons += why
    if mode == "EFFICIENCY":
        gate_min, gate_conf = cfg.min_rel_improvement_efficiency, cfg.confidence_efficiency
        rho = cfg.rho_scale_efficiency * (1.5 - auton)
    else:
        gate_min = _lerp(cfg.min_rel_improvement_calm, cfg.min_rel_improvement_disrupted, t)
        gate_conf = _lerp(cfg.confidence_calm, cfg.confidence_disrupted, t)
        rho = _lerp(cfg.rho_scale_calm, cfg.rho_scale_disrupted, t) * (1.5 - auton)
    return Posture(
        p_disruptive=p_dis, stress=portfolio.stress, mode=mode, demand_severity=d_sev, outlook_risk=outlook_risk,
        autonomy=auton, dominant=dominant,
        scenario_width=_lerp(cfg.width_calm, cfg.width_disrupted, width_t),
        persistence=int(round(_lerp(cfg.persistence_calm, cfg.persistence_disrupted, t))),
        cvar_lambda=_lerp(cfg.lambda_calm, cfg.lambda_disrupted, t),
        cvar_alpha=_lerp(cfg.alpha_calm, cfg.alpha_disrupted, t),
        regret_budget_share=None if t < 0.3 else 0.15 + 0.35 * (1 - t),
        rho_scale=rho,
        trust_region=trust,
        change_cost_rate=_lerp(cfg.change_cost_calm, cfg.change_cost_disrupted, t),
        commit_window=int(round(_lerp(cfg.commit_calm, cfg.commit_disrupted, max(t, 0.5 * d_sev)))),
        min_rel_improvement=gate_min,
        confidence=gate_conf,
        candidates=tuple(candidates), reasons=reasons, config=cfg.__dict__.copy())


def explain_posture(portfolio: EntityState, posture: Posture, info_value: dict | None, incumbent_label: str,
                    mode_run: str, gate_reason: str, improvement: dict | None, commit_window: int,
                    horizon: int) -> str:
    top = sorted(portfolio.probabilities.items(), key=lambda kv: -kv[1])[:3]
    lines = [f"Mode: {posture.mode}", "Current regime:", "  " + ", ".join(f"{k} {v:.0%}" for k, v in top),
             f"Operational stress: {portfolio.stress:.2f}  (autonomy {posture.autonomy:.2f}, "
             f"demand severity {posture.demand_severity:.2f}, leading-indicator risk {posture.outlook_risk:.0%})",
             "Primary signals:"]
    lines += [f"  - {r}" for r in portfolio.reasons[:5]] or ["  - none material"]
    if info_value:
        lines += ["Value of stochastic information:",
                  f"  {info_value.get('classification')} (VSS {info_value.get('vss_rel', 0):.0%}, EVPI {info_value.get('evpi_rel', 0):.0%} of RP)"]
    lines += [f"Incumbent policy: {incumbent_label}", f"Selected policy: {mode_run}", f"Reason: {gate_reason}"]
    if improvement:
        lines += ["Expected improvement vs baseline: " + (f"{improvement.get('mean', 0):+.1%}" if improvement.get('mean') is not None else "n/a"),
                  "Conservative estimate: " + (f"{improvement.get('lower_bound', 0):+.1%}" if improvement.get('lower_bound') is not None else "n/a"),
                  f"Downside regret: {improvement.get('downside_regret', 0):.1%} (budget {posture.regret_budget_share if posture.regret_budget_share is not None else 'none'})"]
    lines += ["Trust region: off (efficiency mode; the evidence gate protects the incumbent)" if posture.mode == "EFFICIENCY"
              else f"Trust region: {min(posture.trust_region.values()) if posture.trust_region else 0:.0%}-"
                   f"{max(posture.trust_region.values()) if posture.trust_region else 0:.0%} of incumbent quantities by SKU",
              f"Executable recommendation: next {commit_window} week(s)",
              f"Weeks {commit_window + 1}-{horizon}: advisory only"]
    if mode_run == "incumbent":
        lines.append("Action: no material ordering-policy change.")
    return "\n".join(lines)

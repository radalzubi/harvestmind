"""Named supply-disruption scenarios applied as an overlay to the engine.

WHAT THIS IS. A set of operator-selectable parameter overrides that shift
the supply distribution and recourse economics, then re-solve. It reuses the
optimizer, the settlement path and the validation unchanged. No new
mathematics.

WHAT IT IS NOT. A prediction. We hold no history pairing disruption events
to realized supplier fills, so the event-to-impact mapping is not learnable
today. Every number in every preset is a STATED ASSUMPTION, carries a
source, and is meant to be shown to the operator and edited by them.
`assumed` is True on every preset and there is deliberately no way to set it
False.

STRUCTURAL LIMITATION, stated here because it decides whether the output is
usable. The optimizer indexes suppliers x products x scenarios; its
variables are x[i,j], s[j,w], w[j,w], u[j,w]. There is NO time index. A
chokepoint closure or a congested berth is primarily a TIMING shock, and
this overlay can only approximate it as a quantity shock: cargo that arrives
three weeks late did not arrive, as far as the commitment week is concerned.

That approximation captures the commit decision. It cannot represent the
late shipment arriving later and creating a glut, shelf life lost in
transit, inventory carried to bridge a known delay, or rescheduling rather
than requantifying. Rescheduling is the natural response to a lead-time
shock and this model cannot recommend it. Say so to the operator.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DisruptionScenario:
    """Parameter overlay describing a named supply disruption."""

    name: str
    description: str
    # Supply side
    fill_multiplier: float = 1.0
    fill_variance_inflation: float = 1.0
    # Recourse side
    recourse_cost_multiplier: float = 1.30
    recourse_capacity_factor: float = 0.30
    # Cost of the units that do arrive (freight, insurance, rerouting)
    landed_cost_multiplier: float = 1.0
    # Which suppliers this reaches. Empty means all of them; a Jordanian
    # distributor sourcing partly locally and partly through Aqaba is NOT
    # uniformly exposed, and a blanket haircut would overstate the shock
    # enough to give advice worse than doing nothing.
    affected_routes: tuple[str, ...] = ()
    source: str = ""
    assumed: bool = field(default=True, init=False)

    def __post_init__(self) -> None:
        if not 0.0 < self.fill_multiplier <= 1.0:
            raise ValueError(
                f"fill_multiplier must be in (0, 1], got {self.fill_multiplier}")
        if self.fill_variance_inflation < 1.0:
            raise ValueError(
                "fill_variance_inflation must be >= 1.0 (a disruption cannot "
                f"make supply more predictable), got {self.fill_variance_inflation}")
        if self.recourse_cost_multiplier < 1.0:
            raise ValueError(
                "recourse_cost_multiplier must be >= 1.0; emergency supply is "
                f"never cheaper than contracted, got {self.recourse_cost_multiplier}")
        if not 0.0 <= self.recourse_capacity_factor <= 1.0:
            raise ValueError("recourse_capacity_factor must be in [0, 1]")
        if self.landed_cost_multiplier < 1.0:
            raise ValueError("landed_cost_multiplier must be >= 1.0")

    def applies_to(self, route: str | None) -> bool:
        """Whether a supplier on ``route`` is exposed to this scenario."""
        if not self.affected_routes:
            return True
        return str(route) in self.affected_routes

    def adjusted_fill(self, base_fill: float, route: str | None = None) -> float:
        if not self.applies_to(route):
            return float(base_fill)
        return max(0.0, min(1.0, float(base_fill) * self.fill_multiplier))

    def describe(self) -> str:
        return (
            f"{self.name}: {self.description} "
            f"[ASSUMED, not measured. fill x{self.fill_multiplier}, "
            f"variance x{self.fill_variance_inflation}, recourse cost "
            f"x{self.recourse_cost_multiplier} capped at "
            f"{self.recourse_capacity_factor:.0%} of demand, landed cost "
            f"x{self.landed_cost_multiplier}. Source: {self.source or 'none'}]"
        )


# ── Presets ────────────────────────────────────────────────────────────────
# WHAT MEASUREMENT HAS SETTLED, as of the PortWatch validation in
# scripts/validate_disruption_presets.py (data 2019-01 to 2026-08):
#
#   red_sea_houthi            was 0.85, measured 0.743 -> REVISED to 0.75
#   aqaba_congestion          0.80 vs measured 0.743   -> consistent
#   northern_land_disruption  0.65 vs measured 0.736   -> consistent
#   saudi_land_disruption     UNTESTED: no Saudi land closure occurred
#   all_land_disruption       UNTESTED: never occurred
#   regional_escalation       UNTESTED: never occurred
#
# The three untested presets are neither confirmed nor refuted. They
# describe tails that did not happen in the measured window, and an
# operator should read them as priced hypotheticals, not forecasts.
#
# `assumed` remains True on every one of them. PortWatch measures tonnage
# ARRIVED; a fill rate is tonnage arrived over tonnage ORDERED, and no
# public source publishes the denominator. Measurement narrowed the range;
# it did not turn an assumption into an observation.
# Calibrated for JORDAN, whose exposure differs from the GCC. Jordan imports
# through Aqaba on the Red Sea, not through Hormuz. Its wheat and barley
# arrive from Romania and Montenegro via Suez. Hormuz matters to Jordan
# indirectly and mostly as an OPPORTUNITY: Iraq has diverted imports from
# Basra to Aqaba, trucking roughly 760 km east, and Aqaba transit volumes
# rose 155.1% in the first half of 2026. That surge is itself a risk to a
# Jordanian food importer, because it competes for berths, yard space and
# trucking capacity.

BASELINE = DisruptionScenario(
    name="baseline",
    description="normal operating conditions",
    source="no disruption applied",
)

RED_SEA_HOUTHI = DisruptionScenario(
    name="red_sea_houthi",
    description=(
        "Threat to Red Sea and Suez transits serving Aqaba. Jordan's grain "
        "and much containerised food arrive this way; importers have "
        "rerouted in response to attacks on shipping. Aqaba sits INSIDE "
        "Bab el-Mandeb, so the Cape of Good Hope reroute that protects "
        "Europe-bound cargo is not available for the final leg into "
        "Jordan: a ship calling at Aqaba must pass the strait either way. "
        "That asymmetry is why Jordan's exposure here is worse than a "
        "European importer's, not better."),
    # REVISED DOWNWARD after measurement. The original 0.85 was a stated
    # guess. IMF PortWatch AIS then measured Aqaba arrivals at 0.743 of
    # their trailing norm through Dec 2023 - Dec 2024, and Aqaba container
    # port calls at 0.53 of the pre-crisis mean, while Bab el-Mandeb
    # transits fell to 0.66 and stayed there for over two years. 0.85 was
    # optimistic against every one of those. 0.75 is set at the measured
    # arrival ratio, which is the most defensible of the three because it
    # is tonnage landed rather than ships counted.
    fill_multiplier=0.75,
    fill_variance_inflation=1.8,
    recourse_cost_multiplier=1.80,
    recourse_capacity_factor=0.15,
    landed_cost_multiplier=1.15,
    affected_routes=("red_sea", "suez", "aqaba"),
    source=(
        "IMF PortWatch AIS: Aqaba import tonnage 0.743 of trailing norm "
        "Dec 2023-Dec 2024 and container calls 0.53 of pre-crisis; Bab "
        "el-Mandeb transits 0.66 of 2019 baseline and still 0.64 through "
        "mid-2026; Cape of Good Hope transits 1.75-1.87x, the measured "
        "reroute. Still ASSUMED: arrivals are not fills."),
)

AQABA_CONGESTION = DisruptionScenario(
    name="aqaba_congestion",
    description=(
        "Aqaba congested by transit cargo bound for Iraq after Hormuz "
        "closed Basra. Not a conflict shock: berths, yard space and trucks "
        "are taken by someone else's freight, so local deliveries slip."),
    fill_multiplier=0.80,
    fill_variance_inflation=2.0,
    recourse_cost_multiplier=1.60,
    recourse_capacity_factor=0.20,
    landed_cost_multiplier=1.10,
    affected_routes=("red_sea", "suez", "aqaba"),
    source=(
        "Aqaba transit volumes +155.1% H1 2026; 573,680 TEU over seven "
        "months, +3% year on year; Iraq trucking ~760 km from Aqaba"),
)

SAUDI_LAND_DISRUPTION = DisruptionScenario(
    name="saudi_land_disruption",
    description=(
        "Road freight from or through Saudi Arabia interrupted: border "
        "closure, crossing congestion, trucking capacity or fuel. A large "
        "share of Jordan's imports arrive by truck this way, including "
        "goods landed at Saudi ports and driven north, so this is not a "
        "minor channel."),
    fill_multiplier=0.60,
    fill_variance_inflation=2.5,
    recourse_cost_multiplier=2.00,
    recourse_capacity_factor=0.12,
    landed_cost_multiplier=1.30,
    affected_routes=("saudi_land",),
    source="operator-reported: substantial Jordanian import volume moves "
           "by road from and through Saudi Arabia",
)

NORTHERN_LAND_DISRUPTION = DisruptionScenario(
    name="northern_land_disruption",
    description=(
        "Overland routes through Syria or Iraq interrupted. Historically "
        "the most politically volatile of Jordan's land channels."),
    fill_multiplier=0.65,
    fill_variance_inflation=2.5,
    recourse_cost_multiplier=2.20,
    recourse_capacity_factor=0.10,
    landed_cost_multiplier=1.25,
    affected_routes=("syria_land", "iraq_land"),
    source="Iraq expanding overland links through Syria and Turkiye",
)

ALL_LAND_DISRUPTION = DisruptionScenario(
    name="all_land_disruption",
    description=(
        "Every land crossing degraded at once. Sea arrivals at Aqaba are "
        "untouched, so this is the scenario where route SUBSTITUTION "
        "matters most: an operator who can shift volume to Aqaba is far "
        "less exposed than one who cannot."),
    fill_multiplier=0.50,
    fill_variance_inflation=2.8,
    recourse_cost_multiplier=2.60,
    recourse_capacity_factor=0.08,
    landed_cost_multiplier=1.35,
    affected_routes=("saudi_land", "syria_land", "iraq_land"),
    source="composite of the individual land-route scenarios",
)

REGIONAL_ESCALATION = DisruptionScenario(
    name="regional_escalation",
    description=(
        "Severe regional escalation: sea and land routes degraded together "
        "and air freight is the only recourse."),
    fill_multiplier=0.45,
    fill_variance_inflation=3.0,
    recourse_cost_multiplier=3.50,
    recourse_capacity_factor=0.05,
    landed_cost_multiplier=1.55,
    source=(
        "Sustained air-freight substitution reported in regional markets; "
        "UN describes the largest supply disruption since COVID with costs "
        "up roughly 20%"),
)

PRESETS: dict[str, DisruptionScenario] = {
    s.name: s for s in (
        BASELINE, RED_SEA_HOUTHI, AQABA_CONGESTION,
        SAUDI_LAND_DISRUPTION, NORTHERN_LAND_DISRUPTION,
        ALL_LAND_DISRUPTION, REGIONAL_ESCALATION,
    )
}

# Jordan's import channels, for tagging suppliers. Naming them explicitly
# matters because they are SUBSTITUTES, not independent risks: goods landed
# at a Saudi port and trucked north are an alternative to Aqaba, and an
# operator who can switch between them is far less exposed than one who
# cannot. A scenario that hits one channel should leave the others alone,
# which is what `affected_routes` is for.
ROUTES: tuple[str, ...] = (
    "aqaba",        # sea, Red Sea, Jordan's own port
    "red_sea",      # transits reaching Aqaba
    "suez",         # European and Black Sea origin via Suez
    "saudi_land",   # road freight from or through Saudi Arabia
    "syria_land",   # road freight via Syria
    "iraq_land",    # road freight via Iraq
    "air",          # air freight, the recourse of last resort
    "local",        # domestic Jordanian production, unexposed
)


def get_scenario(name: str) -> DisruptionScenario:
    if name not in PRESETS:
        raise ValueError(
            f"unknown disruption scenario {name!r}; available: "
            f"{sorted(PRESETS)}")
    return PRESETS[name]


def benchmark_overrides(scenario: DisruptionScenario) -> dict[str, float]:
    """Scenario as keyword arguments for ``run_benchmark``."""
    return {
        "spot_cost_multiplier": scenario.recourse_cost_multiplier,
        "spot_capacity_factor": scenario.recourse_capacity_factor,
    }

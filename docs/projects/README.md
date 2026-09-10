# Two projects, one engine

These are **separate projects** with separate markets, separate prospects
and separate outreach. They share the mathematical core and nothing else.
Do not mix their materials, their prospect lists, or their claims.

**September 2026 Project B audit:** [commercial remodel](../remodel/README.md).
It corrects pipeline/evidence-gate defects and separates vendor market evidence
from synthetic results. It does not establish customer savings for either project.

---

## Project A — Agriculture (US, primary)

**Market.** Midstream perishable operators in the US Midwest: produce
distributors, aggregators, food hubs.

**The decision.** How much to commit to growers and buyers before harvest
and delivery resolve.

**Uncertainty source.** Weather-driven yield. Correlated across growers who
share a region, which is why the copula layer exists.

**Status.** Engine built and gate-tested on synthetic data. No real operator
records have touched it. No customers.

**Outreach lives in `docs/outreach/`** and is AGRICULTURE ONLY:
Purdue contacts (Ballard, Psomas, Seetharaman, Simsek, Ellison, Torres,
Downey, Gray), the Indiana and Illinois prospect lists, the cold-call
script, and the discovery interview script. **None of this is for
Project B.**

**Gating question (Q0 on the discovery script).** Do operators ever reduce
a customer commitment because supply is uncertain, or do they promise and
scramble? If they always promise, there is no decision to optimize.

---

## Project B — Commercial / regional distribution (Jordan first)

**Market.** Commercial food and FMCG distributors, starting in Jordan.
First real data is expected here, not from the GCC.

**The decision.** The same commitment decision, but the binding uncertainty
is different.

**Uncertainty source.** Route and transit disruption, not weather. Jordan's
channels are Aqaba by sea via the Red Sea and Suez, road freight from and
through Saudi Arabia, and overland via Syria and Iraq. Aqaba delays are
frequent and worsen during political events. Aqaba is also congested by
Iraq-bound transit cargo after Hormuz closed Basra, with transit volumes up
155.1% in H1 2026.

**Critically, these routes are SUBSTITUTES.** Goods landed at a Saudi port
and trucked north are an alternative to Aqaba. An operator who can switch
channels is far less exposed than one who cannot, and the model represents
that through `affected_routes`.

**What Project B needs that Project A does not.**
- Route tagging per supplier (`risk/disruption_scenarios.ROUTES`)
- Disruption scenarios (`risk/disruption_scenarios.py`)
- The time dimension, because a transit shock is a TIMING shock
  (`optimization/multi_period_sp.py`)

**Status.** Scenario overlay and multi-period model built. Every scenario
number is a stated assumption, not a measurement. No operator data.

**Gating question.** When Aqaba backs up, do you change HOW MUCH you order
or WHEN you order? The answer is reportedly both, which is why the
multi-period model exists.

---

## What they genuinely share

The engine, and only the engine:

- two-stage stochastic programming with recourse, and the multi-period form
- probabilistic supplier reliability (empirical-Bayes Beta-Binomial)
- conformal calibration of demand intervals
- copula-based dependence between suppliers
- the settlement path, the benchmark ladder, and VSS validation
- the diagnostic layer

See `docs/MATH_SPEC.md`.

## Rules to keep them distinct

1. **Do not send Project A outreach to Project B contacts, or the reverse.**
   A Purdue extension educator is not a lead for a Jordanian distributor.
2. **Do not quote Project A validation results in Project B materials.**
   The Indiana synthetic results say nothing about transit disruption.
3. **Weather correlation is Project A. Route correlation is Project B.**
   They are different covariance structures and should not be conflated.
4. **Keep the prospect lists in separate files.** `docs/outreach/` is
   agriculture. Project B prospects belong in their own file when they exist.

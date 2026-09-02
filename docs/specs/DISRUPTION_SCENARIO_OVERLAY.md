# Spec: Disruption Scenario Overlay

_2026-09-01. For testing with Middle East commercial distributors while the
Strait of Hormuz is closed. Built so it needs no training data, because we
have none._

## The situation this addresses

As of 30 July 2026 the Strait of Hormuz is effectively closed to routine
commercial shipping; the June US-Iran agreement broke down in early July
after attacks on vessels. The Red Sea route to Europe was already at 49% of
pre-crisis capacity. GCC states import up to 85% of their food and have
spent months air-freighting goods that normally move by sea. The UN calls
it the largest supply disruption since COVID, with costs up roughly 20%.

Our own benchmarking found the optimizer is worth most when recourse is
expensive or unavailable. A closed chokepoint is that condition exactly.

## What this is, and what it deliberately is not

**It is** a named, operator-selectable set of parameter overrides that shift
the supply distribution and recourse economics, then re-solves.

**It is not** a prediction. We do not have historical data pairing
disruption events to realized supplier fills, so the event-to-impact
mapping is not learnable today. Every number in a preset is a STATED
ASSUMPTION, shown to the operator, and editable by them.

Presenting it as a forecast would be the same class of dishonesty as
claiming validation on synthetic data.

## Data model

```
DisruptionScenario
  name                    "hormuz_closure"
  description             one line the operator sees
  fill_multiplier         scales each supplier's mean fill        (0.6)
  fill_variance_inflation scales fill variance                    (2.0)
  affected_suppliers      which suppliers are exposed             (by region/route)
  recourse_cost_multiplier  spot/air-freight premium               (3.5)
  recourse_capacity_factor  how much can be covered at all         (0.05)
  landed_cost_multiplier  freight and insurance on committed units (1.4)
  source                  citation for every number above
  assumed                 True, always, and displayed as such
```

`affected_suppliers` matters: a Gulf distributor sourcing partly locally and
partly through Hormuz is not uniformly exposed. Applying a blanket haircut
would overstate the shock and produce advice worse than doing nothing.

## What it changes and what it does not

Reuses the engine unchanged. `SupplyRiskPolicy` already parameterises supply
behaviour; a scenario is a preset over it plus the recourse coefficients the
benchmark already accepts (`spot_cost_multiplier`, `spot_capacity_factor`).

**No new mathematics.** The optimizer, settlement, and validation are
untouched.

## The honest limitation: this cannot represent timing

The optimizer indexes suppliers x products x scenarios. Its variables are
`x[i,j]`, `s[j,w]`, `w[j,w]`, `u[j,w]`. **There is no time index.** It is a
single-period model: commit, one realization, done.

A chokepoint closure is primarily a TIMING shock. Goods are not destroyed,
they arrive three weeks late.

The overlay approximates this as a quantity shock: from the commit week's
point of view, cargo that arrives three weeks late did not arrive, so the
fill rate for that order is zero. That captures the part that matters for
the commit decision, which is whether stock is there when demand is.

**What the approximation cannot represent:**
- the late shipment arriving later and creating a glut
- perishable product arriving with less remaining shelf life
- inventory carried between periods to bridge a known delay
- rescheduling: ordering earlier rather than ordering more

That last one is the real strategic response to a lead-time shock, and this
model cannot recommend it. Say so to any operator rather than let them
assume otherwise.

## Doing it properly requires a multi-period reformulation

To model timing rather than approximate it:

```
x[i,j,t]        commit to supplier i, product j, arriving period t
L[i,w]          random lead time per supplier per scenario
inventory[j,t]  balance constraint linking periods
```

Inventory balance across periods is the structural addition, and
perishability interacts with it: stock held to bridge a delay decays.
This is a multi-period stochastic inventory problem, materially larger
than the current single-period model. Weeks of work, not days.

## Suggested presets, every number an assumption

| preset | fill x | variance x | recourse cost x | recourse cap | landed cost x |
|---|---:|---:|---:|---:|---:|
| `baseline` | 1.00 | 1.0 | 1.30 | 0.30 | 1.00 |
| `red_sea_rerouting` | 0.85 | 1.5 | 1.80 | 0.15 | 1.15 |
| `hormuz_closure` | 0.60 | 2.5 | 3.50 | 0.05 | 1.40 |
| `regional_conflict_severe` | 0.40 | 3.0 | 5.00 | 0.02 | 1.60 |

Anchors: Red Sea at 49% of pre-crisis capacity; Hormuz closed to routine
commercial traffic since 30 July 2026; reported cost increases around 20%;
sustained air-freight substitution in GCC markets. The multipliers are our
interpretation of those conditions, not measured values.

## Output the operator should see

Never a single recommended number. Always the comparison:

```
                      baseline    hormuz_closure
commit to Supplier A     820            1,340
expected unmet            4%              19%
expected landed cost   $18,400         $34,900
recourse exposure      $2,100          $11,600
```

Plus, in plain words: what changed, which assumption drove it, and what
happens if that assumption is wrong by half.

## Build phases

1. **Scenario presets and re-solve.** Days. No new mathematics, no training
   data, testable with a Gulf distributor immediately.
2. **Supplier route exposure tagging.** Which suppliers ship through which
   chokepoint. Requires operator input, one conversation.
3. **Live signal ingestion.** Chokepoint status and port congestion before
   news sentiment: structured, less noisy, maps directly to the parameters
   above. Buyable (SupplyMaven, WorldMonitor, GoComet, Portcast) rather
   than built.
4. **Multi-period reformulation.** Only if operators say rescheduling, not
   requantifying, is the decision they actually make. Ask before building.

## The question to ask a Gulf distributor first

Before any of this: **"When Hormuz closed, did you change how much you
committed to customers, or did you change when you ordered?"**

If the answer is timing, phases 1 to 3 solve the wrong problem and phase 4
is the product. That is one conversation and it should precede the code.

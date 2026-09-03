# Project B first result: multi-period SP under route disruption

_2026-09-01. Synthetic Jordanian distributor. First time the commercial
branch has been tested at all._

## Setup

`synthetic/commercial/jordan_distributor_sim.py`: 14 suppliers tagged to
Aqaba, Saudi road, Syria, Iraq, local and air; shelf-stable product mix with
a few semi-perishables; Ramadan uplift instead of harvest seasonality;
**episodic regime-switching disruption** where Syria and Iraq fail together
as a northern political group while Aqaba is its own group.

Generated behaviour, 160 weeks: ~17% of supplier-weeks disrupted, fill
**0.915 to 0.597** and lead time **1.38 to 3.25 weeks** when a route is hit.

Baselines match the Project A ladder so the comparison is like for like.

| policy | what it knows |
|---|---|
| `mean_lead` | average lead time, average fill |
| `buffer_lead` | 90th-percentile lead time |
| `multi_period` | the full joint distribution over lead time and fill |

## Result (3 seeds, 24 scored folds)

| comparison | median edge | folds won | range |
|---|---:|---:|---|
| vs deterministic (mean lead + fill) | **+2.66%** | **13/24** | -34.8 to +50.6 |
| vs cautious (p90 lead) | +17.96% | 16/24 | -69.4 to +50.7 |

## Reading this honestly

**+2.66% on 13 of 24 folds is not an edge.** Fifty-four percent of folds is
a coin flip. The range from -34.8% to +50.6% says the result is unstable,
not that the median is small but reliable.

The +17.96% against the p90 planner is the less interesting number: it
beats a policy that deliberately over-buffers, which is easy.

**This does not establish commercial viability of the multi-period
optimizer.** A planner using average lead times does about as well.

## Caveats that could move it either way

This harness is new and unvalidated. Every headline in this repository has
moved when a harness defect was found, four times, so treat this as
preliminary rather than settled.

Specific weaknesses:
- Only 10 scenarios per solve. Thin for a distribution over lead time AND
  fill jointly.
- Scoring collapses realized lead time to a per-supplier MEAN over the
  evaluation window, which flattens exactly the timing variation the model
  exists to exploit.
- Supplier capacity is set by an arbitrary formula, the same class of
  defect that made the Project A benchmark degenerate.
- Disruption episodes are rare enough that a fold may contain none, which
  would explain part of the variance.

## What to do before believing either sign

1. Raise the scenario count and re-run; if the edge moves, it was noise.
2. Score against realized per-WEEK lead times, not a per-supplier mean.
3. Split folds into disrupted and calm; the model should earn its keep in
   the disrupted ones and roughly tie in the calm ones. If it does not
   separate on that split, it is not modelling what we think it is.
4. Fix capacity on an evidence basis, as was done for Project A.

## Standing comparison

Project A, after four harness corrections, reached +3.0 to +5.9% against a
fill-aware deterministic optimizer on 25-28 of 52 folds. Project B currently
sits at +2.66% on 13 of 24. Neither is a strong moat, and both say the same
thing: the distribution adds a few points over a competent deterministic
planner, and most of the apparent advantage in earlier numbers came from
comparing against planners that ignored something obvious.

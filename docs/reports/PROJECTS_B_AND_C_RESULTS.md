# Projects B and C: thorough tests

_2026-09-01. Supersedes `COMMERCIAL_BENCHMARK_FIRST_RESULT.md`, whose
+2.66% figure came from a defective harness._

---

# Project B — commercial distribution (Jordan)

## The harness was wrong, and the ablation proves which part

The first run reported **+2.66%, winning 13 of 24 folds** — a coin flip.
Three defects were fixed together, so an ablation was run to attribute the
change rather than assume it.

| configuration | median edge | folds won | range |
|---|---:|---:|---|
| original (per-supplier mean lead, arbitrary capacity, 10 scen) | +2.66% | 13/24 | -34.8 to +50.6 |
| fixed scoring, **10** scenarios | **+15.44%** | 16/24 | -66.6 to +49.3 |
| fixed scoring, **40** scenarios | +13.14% | 20/24 | -21.2 to +47.9 |

**Scenario count was not the driver.** Going from 10 to 40 barely moved the
median and slightly lowered it. What it did was cut the variance (range
narrowed from 116 points to 69) and raise the win rate.

The driver was the **scoring fix**. The original collapsed realized lead
time to a per-supplier MEAN over the evaluation window, which flattened
exactly the timing variation the multi-period model exists to exploit. That
is the same class of defect as scoring committed quantity as delivered
quantity: the benchmark deleted the mechanism under test and then reported
that the mechanism added nothing.

## Full result (5 seeds, 14 folds, 40 scenarios, 70 folds scored)

| comparison | median | folds won | range |
|---|---:|---:|---|
| vs deterministic (mean lead + fill) | **+18.93%** | **60/70** | -25.1 to +62.9 |
| vs cautious (p90 lead) | +25.06% | 64/70 | -18.1 to +61.5 |

## The split that validates the mechanism

| fold condition | n | median edge | won |
|---|---:|---:|---:|
| route disrupted | 21 | **+23.02%** | 19/21 |
| calm | 49 | +16.51% | 41/49 |
| **separation** | | **+6.51 points** | |

This is the result that matters most. The model does better precisely when
routes are disrupted, which is the mechanism it claims to model. Had it
performed equally in calm and disrupted folds, the edge would have been
coming from something else and the story would be wrong.

## Honest limits

- Synthetic throughout. Route profiles, disruption probabilities and
  transit distributions are assumptions.
- 60/70 is strong but the range still spans -25% to +63%: single folds vary
  enormously.
- The generator produces disruption from a regime-switching process the
  model is well suited to; a real disruption process may be less tidy.

---

# Project C — vertically integrated producer

## Why this is a distinct structure

Not a variant of A or B. The producer GROWS most of what it sells: one
lumpy harvest per year, committed to buyers roughly twenty weeks before it
resolves, with no supplier diversification to soften a bad draw.

Integration does not remove supply uncertainty; it concentrates it. And
integrated shippers buy externally anyway — reported practice has
California grape shippers importing from Mexico and Chile for year-round
supply — so the real decision is **make versus buy under uncertainty**,
with external purchase as the recourse channel at a premium and limited
availability.

Generated yield ratios across six years: 0.63, 0.78, 0.93, 1.03, 1.12,
1.32. One draw decides the whole book.

## Result (5 seeds, 12 years, 50 seasons scored)

| policy | mean profit | vs expected-yield |
|---|---:|---:|
| p25 rule | -2,543 | -105.8% |
| p40 rule | 1,954 | -38.0% |
| expected_yield | 4,351 | baseline |
| p60 rule | 6,646 | +37.5% |
| **stochastic** | **12,297** | **+67.2%** |

Against the best percentile rule (p60), the stochastic policy earns roughly
**85% more mean profit**. Against p40 the median percentage edge is
+168.76% but it wins only 30 of 50 seasons.

## Read this more sceptically than Project B

**The percentage figures are unstable.** p40's mean profit is close to
zero, so ratios against it explode. Compare mean profit, not percentage
edge.

**Winning 30 of 50 is only 60%.** Large mean gains with a modest win rate
means a few seasons carry the result, which is what one would expect when a
single annual draw dominates, and is also what makes it fragile.

**The comparison is favourable by construction.** The stochastic policy
selects the commitment maximising expected profit under the SAME profit
function used to score it, drawing from a correctly specified
distribution. Real planning suffers model misspecification, which this
setup excludes. Treat the number as an upper bound.

**The commitment level matters more than the method.** p25 loses money and
p60 makes it. Most of the available value is in committing at the right
level at all, and a grower who happens to pick a sensible percentile
captures much of it without any optimizer.

## What would make Project C credible

1. Score under a MISSPECIFIED belief: fit a normal, generate from something
   skewed, and see whether the edge survives.
2. Report absolute profit distributions, not percentage edges off a
   near-zero baseline.
3. Test whether the value is in the commitment LEVEL or the channel
   ALLOCATION by fixing one and varying the other. If it is all level, a
   percentile rule plus good judgement is the product.

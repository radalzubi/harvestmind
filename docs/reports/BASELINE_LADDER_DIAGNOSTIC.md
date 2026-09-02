# Baseline Ladder: is the stochastic layer the advantage?

_2026-09-01. Answers a question the previous benchmarks could not: does the
SP beat a competent DETERMINISTIC planner, as opposed to beating a
fill-blind one?_

## Why the old headline was not a fair test

Every prior result compared the SP against `deterministic_lp`, which
commits mean demand and **ignores supplier fill entirely**. It therefore
gets short-delivered by construction. Any policy that grosses up for fill
beats it. The +13.46% median and 25/30 gate may measure fill-awareness
versus fill-blindness, not stochastic versus deterministic planning.

## The ladder

Each rung adds exactly one thing over the last, so a win can be attributed.

| Policy | Adds |
|---|---|
| `naive_runrate` | trailing average |
| `deterministic_lp` | cost optimization (fill-blind) |
| `deterministic_atp` | fill awareness (mean fill, capacity-capped) |
| `safety_buffer_atp` | conservatism (10th-percentile fill) |
| **`mean_value_sp`** | **the real yardstick, see below** |
| `two_sided_sp` | the full distribution |

`mean_value_sp` is a fill-aware DETERMINISTIC optimizer: identical solver,
capacity constraints, recourse economics, training information and
settlement path as the SP, differing only in seeing a point estimate of
supplier fill instead of a distribution. It is the mean-value problem of
the SP, so SP-versus-it is a true value of the stochastic solution.

## Result (seed 11, fill 0.85, rationed spot 1.60x/15%)

| capacity headroom | SP vs LP | **SP vs mean-value** | SP vs buffered ATP | SP wins |
|---:|---:|---:|---:|---:|
| 1.00 | +21.67% | 0.0% | 0.0% | 0/8 |
| 1.25 | +37.03% | **-26.57%** | -41.78% | 1/8 |
| 1.50 | +37.08% | **-26.47%** | -41.31% | 1/8 |
| 2.00 | +36.94% | **-26.69%** | -41.19% | 1/8 |
| 3.00 | +38.79% | **-20.72%** | -39.65% | 1/8 |

## Two defects this exposed in the benchmark itself

**1. At headroom 1.0 the benchmark measures nothing.** SP, mean-value
optimizer and both ATP rules produce byte-identical allocations (53,465 kg,
max per-key difference 0.0). Capacity binds for every fill-aware policy, so
there is no decision left for a distribution to inform.

The cause: capacity is defined as the MEAN OF WHAT WAS HISTORICALLY
ORDERED. That is what someone chose to buy, not what a supplier could
supply. As a hard ceiling it is artificial. `capacity_headroom` now scales
it; 1.0 reproduces the old behaviour exactly.

**2. The cost structure may be degenerate.** Decomposing one fold at
headroom 1.5:

| policy | ordered | delivered | waste $ | spot $ | unmet $ | total |
|---|---:|---:|---:|---:|---:|---:|
| two_sided_sp | 56,432 | 47,359 | **0** | 6,535 | 3,861 | 10,396 |
| deterministic_lp | 50,172 | 42,293 | **0** | 7,536 | 8,142 | 15,679 |
| deterministic_atp | 59,069 | 49,678 | 34 | 5,589 | 2,366 | 7,989 |
| mean_value_sp | 59,075 | 49,751 | 37 | 5,605 | 2,317 | 7,959 |
| safety_buffer_atp | 61,605 | 51,813 | 486 | 4,695 | 1,498 | **6,679** |

Cost falls monotonically as ordering rises, and **the SP records zero
waste in every fold**. Shortfall costs dominate waste costs by roughly an
order of magnitude, so "order more" always wins and there is no interior
newsvendor optimum to find. A benchmark whose optimal policy is "order as
much as capacity allows" cannot distinguish planning methods.

## What this does and does not establish

**Does not establish** that stochastic optimization fails. The benchmark is
not yet capable of settling that, for the two reasons above.

**Does establish** that the previous headline was measured against a weak
baseline, and that the SP systematically under-orders relative to what
these economics reward.

**Commercial viability of the stochastic layer is therefore UNPROVEN, not
disproven.** It should not be sold, and no product should be built on the
assumption that it works.

## What would settle it

1. Define capacity from something other than historical order volume.
2. Rebalance waste against shortfall so an interior optimum exists, then
   confirm the critical fractile is not pinned near 1.
3. Re-run the ladder. If the SP still loses to `mean_value_sp` on a
   benchmark with a genuine interior optimum, the distribution is not the
   value and the product case rests on the diagnostic, the forecasting
   layer, and workflow instead.

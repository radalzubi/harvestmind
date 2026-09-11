# Project B v2: calibrated distributor, and the condition that decides value

_2026-09-01. Supersedes the v1 commercial results. The model's value turns
out to depend on ONE operator characteristic, and it is measurable in a
single question._

## Calibration

The generator is built to published benchmarks, not guesses.

| source | figure used |
|---|---|
| Sysco FY2025 | $81.4B revenue, 18.4% gross, 2.25% net |
| US Foods FY2025 | 17.4% gross, 14.4% opex, 5.4% adj EBITDA |
| Performance Food Group FY2025 | 11.72% gross, 0.54% net, **13.63 inventory turns** |
| MENA FMCG distribution | import distribution **12-22% gross**; a leading MENA distributor at **0.5% net** |
| distribution operations | **21 days inventory**, 20 DSO, 15 DPO, carrying **1.5-2.5%/month** |
| Jordan retail | traditional trade **85% of outlets, 90% of sales**; modern trade = Carrefour, Cozmo, C-Town, Safeway |

Generated and verified: 120 SKUs on an ABC curve (24 A-items carrying 80%
of volume; 60 C-items with 45% zero-demand weeks), 22 suppliers tagged to
routes by realistic share, gross margin 17.2% (12.1-22.0%), carrying cost
0.46%/week, 8.8% of supplier-weeks disrupted.

## The harness was wrong twice before it was right

A cost comparison looked plausible both times. A PHYSICAL quantity exposed
both.

**First run:** +6.76%, winning 30/30. But service was **55%** and shortage
was 94.9% of cost. Two failing policies were being compared. Cause: an
18-week Aqaba lead tail against a 6-week horizon, and a start with zero
stock and nothing in transit, which no distributor has.

**Second run:** −24.70%, winning 0/24. Service now realistic at 99.6%, but
holding became 98.5% of cost. The regime had simply flipped.

## The sweep that resolves it

Same model, same data, varying only how well-stocked the operator already
is at the start.

| opening cover | SP vs deterministic | folds won | deterministic service | SP service |
|---:|---:|---:|---:|---:|
| 0 weeks | **+4.29%** | 8/12 | 93.6% | 96.5% |
| 1 week | -12.69% | 3/12 | 96.6% | 98.5% |
| 2 weeks | -18.94% | 0/12 | 98.5% | 99.5% |
| 3.4 weeks (calibrated 24 days) | -22.90% | 0/12 | 99.7% | 99.9% |
| 5 weeks | -20.67% | 0/12 | 100.0% | 100.0% |

**The crossover sits below one week of cover.**

## What the model actually does, consistently

At every level it buys **1 to 3 points of extra service** (96.5 vs 93.6,
98.5 vs 96.6, 99.5 vs 98.5, 99.9 vs 99.7). That is the mechanism, and it is
stable.

Whether that is worth paying for is entirely a function of where the
operator starts. Below roughly 95% service, the recovered gross margin
exceeds the extra holding cost. Above it, it does not, and the model is
selling insurance to somebody who is already safe.

## The honest commercial reading

**The value is conditional, and the condition is measurable.**

Do not lead with a headline percentage. Lead with the question:

> **"What service level do you run, and how many days of stock do you
> carry?"**

At 99% on 24 days, this model has nothing to offer and we should say so.
At 93% with regular stockouts, it recovers real margin.

One caveat against our own case: an operator at 93.6% service has a problem
that "carry more inventory" also solves, and they do not need an optimizer
to be told that. The defensible claim is narrower than it first appears —
the model carries more stock **in the right places**, reaching 96.5% where
the deterministic policy reaches 93.6% at comparable cost. That is an
allocation result, not a stocking result.

## Withdrawn

The +175% net-profit translation from the first v2 run. The arithmetic is
right — at 0.5% net margin a 0.877% COGS saving is genuinely that large —
but it was computed on a run where both policies sat at 55% fill. The −96%
from the second run is untrustworthy for the mirror reason. Neither input
deserves the multiplier until the operating regime is realistic.

## A guard the harness should carry permanently

Five harness defects were found in this session. Every time, the cost
number looked plausible and a physical quantity gave it away: fill rate,
service level, or waste being exactly zero.

The benchmark should REFUSE to report an edge when service falls outside
90-100%, or when any single cost component exceeds ~90% of total cost.
Both conditions mean the comparison is being run in a degenerate regime,
and a number produced there is worse than no number.

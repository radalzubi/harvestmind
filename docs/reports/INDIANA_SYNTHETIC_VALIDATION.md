# Indiana Synthetic Validation

Run date: 2026-08-31  
Verdict: **the diagnostic pipeline is credible enough for a real-data pilot;
the stochastic policy did not pass its commercialization gate.**

> SYNTHETIC ONLY. No Indiana operator supplied records. These results test
> software behavior under modeled conditions; they are not market performance,
> customer proof, a savings claim, or a forecast of an Indiana business.

## Test design

- Five independent seeds: 11, 23, 42, 67, 101.
- 80 weekly observations per seed; the rolling benchmark used a 52-week train
  window and 12 held-out origins.
- Six spot-market regimes: 15% or 30% capacity at 1.15x, 1.30x, or 1.60x normal
  procurement cost.
- 30 completed head-to-head runs in total.
- Each simulated operator: approximately $6.0M annual revenue, 16 products, 18
  suppliers, 10 buyer archetypes, 12,800 order lines, 3,840 delivery lines, and
  a modeled 6.5% waste rate.
- Product basket and harvest windows follow USDA NASS Indiana crop reporting
  and Purdue Extension's Indiana fresh-produce seasonal chart. Supplier,
  margin, fill-rate, spot, and waste parameters are modeled assumptions.

Reproduce:

```bash
python3 scripts/validate_indiana_market.py \
  --seeds 11,23,42,67,101 \
  --weeks 80 \
  --folds 12 \
  --output /tmp/harvestmind_indiana_validation.json
```

## Results

| Measure | Result |
|---|---:|
| Completed runs | 30 / 30 |
| Commercial gate passes | **0 / 30** |
| Median SP edge vs deterministic LP | **-29.21%** |
| Range vs deterministic LP | **-41.70% to -5.83%** |
| Median SP edge vs four-week run rate | **-21.52%** |
| Range vs order-up-to heuristic | **+21.09% to +57.89%** |
| SP service level | 99.3% to 100.0% |
| Deterministic service level | 98.5% to 100.0% |

The stochastic program consistently beat the safety-stock-like order-up-to
heuristic, but it lost to both the deterministic LP and the simple run-rate
policy in the costs used by the current benchmark. Its modest service lift did
not pay for its additional commitments. That is a real negative result, not a
reason to retune the simulation until the model wins.

The API now blocks stochastic commitments by default unless the same
rolling-origin gate passes on the connected operator's own history. Users may
disable the gate only to inspect a diagnostic plan.

## All 30 runs

Edges are `(baseline cost − SP cost) / baseline cost`; positive favors SP.

| Seed | Spot x | Cap | vs LP | vs run rate | vs order-up-to | SP svc | LP svc |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 11 | 1.15 | 0.15 | -38.34% | -46.49% | +36.25% | 99.7% | 98.9% |
| 11 | 1.15 | 0.30 | -34.83% | -41.83% | +44.44% | 100.0% | 100.0% |
| 11 | 1.30 | 0.15 | -29.21% | -36.19% | +32.58% | 99.7% | 98.9% |
| 11 | 1.30 | 0.30 | -34.88% | -41.42% | +34.53% | 100.0% | 100.0% |
| 11 | 1.60 | 0.15 | -15.95% | -21.44% | +26.03% | 99.7% | 98.9% |
| 11 | 1.60 | 0.30 | -17.85% | -23.06% | +26.38% | 100.0% | 100.0% |
| 23 | 1.15 | 0.15 | -33.84% | -39.99% | +31.50% | 99.3% | 98.5% |
| 23 | 1.15 | 0.30 | -30.14% | -31.22% | +42.61% | 100.0% | 100.0% |
| 23 | 1.30 | 0.15 | -23.56% | -30.44% | +27.92% | 99.4% | 98.5% |
| 23 | 1.30 | 0.30 | -31.82% | -36.13% | +29.98% | 100.0% | 100.0% |
| 23 | 1.60 | 0.15 | -10.11% | -17.69% | +21.09% | 99.4% | 98.5% |
| 23 | 1.60 | 0.30 | -11.98% | -19.01% | +21.78% | 100.0% | 100.0% |
| 42 | 1.15 | 0.15 | -41.10% | -30.24% | +40.84% | 99.7% | 99.0% |
| 42 | 1.15 | 0.30 | -37.73% | -24.59% | +48.87% | 100.0% | 100.0% |
| 42 | 1.30 | 0.15 | -29.60% | -21.52% | +37.86% | 99.7% | 99.0% |
| 42 | 1.30 | 0.30 | -35.97% | -26.00% | +39.69% | 100.0% | 100.0% |
| 42 | 1.60 | 0.15 | -14.11% | -9.35% | +32.16% | 99.7% | 99.0% |
| 42 | 1.60 | 0.30 | -16.05% | -10.83% | +32.52% | 100.0% | 100.0% |
| 67 | 1.15 | 0.15 | -41.70% | -26.84% | +44.37% | 99.7% | 99.0% |
| 67 | 1.15 | 0.30 | -40.35% | -25.03% | +50.21% | 100.0% | 100.0% |
| 67 | 1.30 | 0.15 | -30.85% | -19.69% | +41.27% | 99.7% | 99.0% |
| 67 | 1.30 | 0.30 | -36.90% | -24.94% | +42.49% | 100.0% | 100.0% |
| 67 | 1.60 | 0.15 | -15.73% | -9.10% | +35.43% | 99.7% | 99.0% |
| 67 | 1.60 | 0.30 | -17.51% | -10.65% | +35.75% | 100.0% | 100.0% |
| 101 | 1.15 | 0.15 | -30.41% | -11.82% | +51.16% | 99.6% | 98.9% |
| 101 | 1.15 | 0.30 | -28.70% | -5.82% | +57.89% | 100.0% | 100.0% |
| 101 | 1.30 | 0.15 | -19.84% | -7.57% | +47.45% | 99.6% | 98.9% |
| 101 | 1.30 | 0.30 | -26.75% | -11.24% | +48.88% | 100.0% | 100.0% |
| 101 | 1.60 | 0.15 | -5.83% | -1.10% | +40.49% | 99.6% | 98.9% |
| 101 | 1.60 | 0.30 | -7.54% | -2.29% | +40.81% | 100.0% | 100.0% |

## What the test does and does not prove

It does prove that the ingestion, staging schema, diagnostics, supplier-risk
fit, optimizer, and rolling-origin comparison can operate repeatedly at a
plausible pilot scale and honestly reject the flagship model.

It does not prove economic value. The benchmark scores product-level
commitments and does not replay realized supplier fills into every policy's
settlement, so it may understate the value of a policy that deliberately
over-commits against yield risk. The simulation also omits labor, warehouse
capacity, case packs, order cutoffs, substitutions across products, contract
minimums, truck routes, and actual Indiana operator behavior. Those gaps are
reasons to run a paid diagnostic on real exports, not reasons to claim a win.


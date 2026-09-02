# Full Synthetic Simulation Sweep

> Synthetic mechanism test only — not operator validation, a realized-savings claim, or a market forecast.

## Headline: fill-rate decay at fixed 1.30x / 30% spot

| Mean fill | Median SP vs LP | Range | Failures |
|---:|---:|---:|---:|
| 0.99 | +4.36% | -1.04% to +7.45% | 1/5 |
| 0.95 | -4.08% | -8.76% to -1.82% | 5/5 |
| 0.85 | +10.91% | +9.77% to +13.68% | 0/5 |
| 0.70 | +18.92% | +18.15% to +20.09% | 0/5 |

## Segment signal across all six spot regimes

| Mean fill | Median SP vs LP | Range | Commercial gate failures |
|---:|---:|---:|---:|
| 0.99 | -2.33% | -6.87% to +27.53% | 19/30 |
| 0.95 | -2.09% | -9.77% to +9.10% | 24/30 |
| 0.85 | +19.24% | +0.94% to +25.61% | 4/30 |
| 0.70 | +18.25% | +13.83% to +25.97% | 15/30 |

## Decision findings

- The fill-rate hypothesis is directionally supported but not monotonic: the fixed-spot median falls from the 0.70 cell to the 0.99 cell, while the 0.95 cell is a negative trough. Treat 0.95 as a model-regime transition to investigate, not a smooth decay curve.
- The forced-perfect-delivery control has a median SP-vs-LP edge of +7.84% and cannot open the gate by construction.
- Correlated-shortfall value is not demonstrated merely by wiring the copula. Use the B.1 per-level table below; the realized tau tracks the targets, but a higher tau must improve the edge consistently before it supports a commercial claim.
- The large intermittent-demand cost edge is partly purchased with lower service. The commercial gate now requires the configured 90% SP service floor; 50%-zero cells fail it and must not be sold as savings.
- Scale is an arithmetic invariance check, not evidence of larger percentage savings. Absolute dollar opportunity scales; the modeled percentage edge should remain stable.

## Grid B one-factor summaries

| Factor | Level | Median SP vs LP | Range | Failures |
|---|---|---:|---:|---:|
| correlated_shortfall | tau=0.0 | +10.91% | +9.77% to +13.68% | 0/5 |
| correlated_shortfall | tau=0.3 | +11.39% | +7.81% to +13.90% | 0/5 |
| correlated_shortfall | tau=0.6 | +10.76% | +6.96% to +13.66% | 0/5 |
| demand_intermittency | zero_rate=0.0 | +10.91% | +9.77% to +13.68% | 0/5 |
| demand_intermittency | zero_rate=0.2 | +33.12% | +22.71% to +34.92% | 2/5 |
| demand_intermittency | zero_rate=0.5 | +33.63% | +26.40% to +40.39% | 5/5 |
| cost_asymmetry | underage:overage=1.0:1 | +11.80% | +10.93% to +15.20% | 0/5 |
| cost_asymmetry | underage:overage=3.0:1 | +20.98% | +19.25% to +24.92% | 0/5 |
| cost_asymmetry | underage:overage=9.0:1 | +38.74% | +33.12% to +40.46% | 0/5 |
| operator_scale | annual_revenue=6000000.0 | +10.91% | +9.77% to +13.68% | 0/5 |
| operator_scale | annual_revenue=15000000.0 | +10.91% | +9.77% to +13.68% | 0/5 |
| operator_scale | annual_revenue=50000000.0 | +10.91% | +9.77% to +13.68% | 0/5 |
| train_window | train_weeks=26 | +17.17% | +17.04% to +18.47% | 2/5 |
| train_window | train_weeks=52 | +10.91% | +9.77% to +13.68% | 0/5 |
| train_window | train_weeks=78 | +14.79% | +9.09% to +17.59% | 0/5 |

## Summary

- Grid A: `{'runs': 120, 'completed': 120, 'gate_passes': 58, 'median_sp_vs_lp_edge_pct': 9.43, 'min_sp_vs_lp_edge_pct': -9.77, 'max_sp_vs_lp_edge_pct': 27.53}`
- Grid B: `{'runs': 75, 'completed': 75, 'gate_passes': 66, 'median_sp_vs_lp_edge_pct': 13.45, 'min_sp_vs_lp_edge_pct': 6.96, 'max_sp_vs_lp_edge_pct': 40.46}`
- Controls: `{'runs': 5, 'completed': 5, 'gate_passes': 0, 'median_sp_vs_lp_edge_pct': 7.84, 'min_sp_vs_lp_edge_pct': 2.57, 'max_sp_vs_lp_edge_pct': 11.28}`

The SP differs from the deterministic LP in demand uncertainty as well as supply uncertainty. The forced-unit-fill controls therefore quantify the residual demand-planning edge; a 0.99-fill result should converge toward that control, not necessarily mathematical zero.

Supplier-blind policies are allocated pro rata by training-window delivered volume. Missing held-out fills use the supplier's training-window mean. All policies use one settlement path.

## Commercial market-gap excerpt

The synthetic evidence supports a narrow initial segment hypothesis: operators with materially unreliable but still recoverable supply, roughly the 0.85-fill cell in this design, are the strongest target. That cell clears the commercial gate in 26/30 spot regimes. Near-perfect 0.99 supply clears only 11/30, so high-reliability procurement is a weak target. Catastrophic 0.70 supply clears only 15/30 despite positive cost edges because limited recourse often cannot maintain 90% service. HarvestMind therefore looks most useful as a planning layer for produce distributors, food hubs, and similar perishable networks where shortfalls are frequent enough to matter but operational alternatives still exist. This is a pilot-selection rule from synthetic evidence, not a TAM estimate or market validation.

## Every run

| Grid | Factor | Level | Seed | Obs fill | Obs tau | Obs zero | SP vs LP | vs naive | vs routed | Service | Gate | Croston routes |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|---:|
| A | full_factorial | fill=0.99\|spot=1.15\|cap=0.15 | 11 | 0.9900 | -0.003 | 0.000 | -3.58% | 4.99% | 4.99% | 96.3% | no | 0 |
| A | full_factorial | fill=0.99\|spot=1.15\|cap=0.15 | 23 | 0.9900 | 0.006 | 0.000 | 3.71% | 9.46% | 9.46% | 96.6% | yes | 0 |
| A | full_factorial | fill=0.99\|spot=1.15\|cap=0.15 | 42 | 0.9901 | 0.002 | 0.000 | -6.87% | -0.78% | -0.78% | 96.5% | no | 0 |
| A | full_factorial | fill=0.99\|spot=1.15\|cap=0.15 | 67 | 0.9901 | -0.005 | 0.000 | 0.23% | -0.74% | -0.74% | 97.0% | no | 0 |
| A | full_factorial | fill=0.99\|spot=1.15\|cap=0.15 | 101 | 0.9899 | -0.001 | 0.000 | 1.43% | 0.09% | 0.09% | 96.4% | yes | 0 |
| A | full_factorial | fill=0.99\|spot=1.15\|cap=0.30 | 11 | 0.9900 | -0.003 | 0.000 | 23.00% | 33.68% | 33.68% | 99.5% | yes | 0 |
| A | full_factorial | fill=0.99\|spot=1.15\|cap=0.30 | 23 | 0.9900 | 0.006 | 0.000 | 22.99% | 33.37% | 33.37% | 99.4% | yes | 0 |
| A | full_factorial | fill=0.99\|spot=1.15\|cap=0.30 | 42 | 0.9901 | 0.002 | 0.000 | 17.01% | 25.73% | 25.73% | 99.6% | yes | 0 |
| A | full_factorial | fill=0.99\|spot=1.15\|cap=0.30 | 67 | 0.9901 | -0.005 | 0.000 | 27.53% | 26.92% | 26.92% | 99.8% | yes | 0 |
| A | full_factorial | fill=0.99\|spot=1.15\|cap=0.30 | 101 | 0.9899 | -0.001 | 0.000 | 27.14% | 27.48% | 27.48% | 99.4% | yes | 0 |
| A | full_factorial | fill=0.99\|spot=1.30\|cap=0.15 | 11 | 0.9900 | -0.003 | 0.000 | -5.91% | 0.01% | 0.01% | 96.7% | no | 0 |
| A | full_factorial | fill=0.99\|spot=1.30\|cap=0.15 | 23 | 0.9900 | 0.006 | 0.000 | -1.37% | 3.21% | 3.21% | 97.1% | no | 0 |
| A | full_factorial | fill=0.99\|spot=1.30\|cap=0.15 | 42 | 0.9901 | 0.002 | 0.000 | -6.59% | -5.25% | -5.25% | 97.1% | no | 0 |
| A | full_factorial | fill=0.99\|spot=1.30\|cap=0.15 | 67 | 0.9901 | -0.005 | 0.000 | -2.42% | -5.14% | -5.14% | 97.5% | no | 0 |
| A | full_factorial | fill=0.99\|spot=1.30\|cap=0.15 | 101 | 0.9899 | -0.001 | 0.000 | -2.24% | -4.36% | -4.36% | 97.0% | no | 0 |
| A | full_factorial | fill=0.99\|spot=1.30\|cap=0.30 | 11 | 0.9900 | -0.003 | 0.000 | 4.36% | 12.83% | 12.83% | 99.8% | yes | 0 |
| A | full_factorial | fill=0.99\|spot=1.30\|cap=0.30 | 23 | 0.9900 | 0.006 | 0.000 | 2.11% | 11.18% | 11.18% | 99.7% | yes | 0 |
| A | full_factorial | fill=0.99\|spot=1.30\|cap=0.30 | 42 | 0.9901 | 0.002 | 0.000 | -1.04% | 2.88% | 2.88% | 99.9% | no | 0 |
| A | full_factorial | fill=0.99\|spot=1.30\|cap=0.30 | 67 | 0.9901 | -0.005 | 0.000 | 5.46% | 2.87% | 2.87% | 99.9% | yes | 0 |
| A | full_factorial | fill=0.99\|spot=1.30\|cap=0.30 | 101 | 0.9899 | -0.001 | 0.000 | 7.45% | 6.59% | 6.59% | 99.7% | yes | 0 |
| A | full_factorial | fill=0.99\|spot=1.60\|cap=0.15 | 11 | 0.9900 | -0.003 | 0.000 | -4.87% | -2.82% | -2.82% | 97.6% | no | 0 |
| A | full_factorial | fill=0.99\|spot=1.60\|cap=0.15 | 23 | 0.9900 | 0.006 | 0.000 | -3.39% | -0.73% | -0.73% | 97.8% | no | 0 |
| A | full_factorial | fill=0.99\|spot=1.60\|cap=0.15 | 42 | 0.9901 | 0.002 | 0.000 | -4.58% | -9.38% | -9.38% | 97.9% | no | 0 |
| A | full_factorial | fill=0.99\|spot=1.60\|cap=0.15 | 67 | 0.9901 | -0.005 | 0.000 | -4.51% | -9.58% | -9.58% | 98.2% | no | 0 |
| A | full_factorial | fill=0.99\|spot=1.60\|cap=0.15 | 101 | 0.9899 | -0.001 | 0.000 | -3.99% | -7.13% | -7.13% | 97.9% | no | 0 |
| A | full_factorial | fill=0.99\|spot=1.60\|cap=0.30 | 11 | 0.9900 | -0.003 | 0.000 | -5.51% | -2.66% | -2.66% | 100.0% | no | 0 |
| A | full_factorial | fill=0.99\|spot=1.60\|cap=0.30 | 23 | 0.9900 | 0.006 | 0.000 | -3.43% | 0.79% | 0.79% | 99.9% | no | 0 |
| A | full_factorial | fill=0.99\|spot=1.60\|cap=0.30 | 42 | 0.9901 | 0.002 | 0.000 | -5.22% | -9.30% | -9.30% | 100.0% | no | 0 |
| A | full_factorial | fill=0.99\|spot=1.60\|cap=0.30 | 67 | 0.9901 | -0.005 | 0.000 | -4.48% | -9.66% | -9.66% | 100.0% | no | 0 |
| A | full_factorial | fill=0.99\|spot=1.60\|cap=0.30 | 101 | 0.9899 | -0.001 | 0.000 | -4.25% | -6.92% | -6.92% | 99.9% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.15\|cap=0.15 | 11 | 0.9499 | -0.003 | 0.000 | -6.13% | -4.25% | -4.25% | 96.2% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.15\|cap=0.15 | 23 | 0.9500 | 0.006 | 0.000 | -4.60% | -0.76% | -0.76% | 96.6% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.15\|cap=0.15 | 42 | 0.9503 | 0.002 | 0.000 | -9.77% | -14.19% | -14.19% | 96.4% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.15\|cap=0.15 | 67 | 0.9503 | -0.005 | 0.000 | -6.59% | -12.01% | -12.01% | 97.0% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.15\|cap=0.15 | 101 | 0.9498 | -0.001 | 0.000 | -6.31% | -11.08% | -11.08% | 96.3% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.15\|cap=0.30 | 11 | 0.9499 | -0.003 | 0.000 | 8.23% | 17.55% | 17.55% | 99.4% | yes | 0 |
| A | full_factorial | fill=0.95\|spot=1.15\|cap=0.30 | 23 | 0.9500 | 0.006 | 0.000 | 3.10% | 17.59% | 17.59% | 99.4% | yes | 0 |
| A | full_factorial | fill=0.95\|spot=1.15\|cap=0.30 | 42 | 0.9503 | 0.002 | 0.000 | -2.26% | 1.05% | 1.05% | 99.6% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.15\|cap=0.30 | 67 | 0.9503 | -0.005 | 0.000 | 9.10% | 5.55% | 5.55% | 99.7% | yes | 0 |
| A | full_factorial | fill=0.95\|spot=1.15\|cap=0.30 | 101 | 0.9498 | -0.001 | 0.000 | 8.57% | 7.13% | 7.13% | 99.5% | yes | 0 |
| A | full_factorial | fill=0.95\|spot=1.30\|cap=0.15 | 11 | 0.9499 | -0.003 | 0.000 | -4.62% | -4.68% | -4.68% | 96.7% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.30\|cap=0.15 | 23 | 0.9500 | 0.006 | 0.000 | -3.78% | -1.10% | -1.10% | 97.1% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.30\|cap=0.15 | 42 | 0.9503 | 0.002 | 0.000 | -4.23% | -11.65% | -11.65% | 97.0% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.30\|cap=0.15 | 67 | 0.9503 | -0.005 | 0.000 | -4.32% | -10.27% | -10.27% | 97.4% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.30\|cap=0.15 | 101 | 0.9498 | -0.001 | 0.000 | -5.59% | -10.29% | -10.29% | 96.9% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.30\|cap=0.30 | 11 | 0.9499 | -0.003 | 0.000 | -2.41% | 2.01% | 2.01% | 99.7% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.30\|cap=0.30 | 23 | 0.9500 | 0.006 | 0.000 | -7.16% | 2.39% | 2.39% | 99.7% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.30\|cap=0.30 | 42 | 0.9503 | 0.002 | 0.000 | -8.76% | -12.75% | -12.75% | 99.9% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.30\|cap=0.30 | 67 | 0.9503 | -0.005 | 0.000 | -4.08% | -9.50% | -9.50% | 99.9% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.30\|cap=0.30 | 101 | 0.9498 | -0.001 | 0.000 | -1.82% | -4.59% | -4.59% | 99.7% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.60\|cap=0.15 | 11 | 0.9499 | -0.003 | 0.000 | 0.43% | -1.83% | -1.83% | 97.5% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.60\|cap=0.15 | 23 | 0.9500 | 0.006 | 0.000 | 1.73% | 3.02% | 3.02% | 97.8% | yes | 0 |
| A | full_factorial | fill=0.95\|spot=1.60\|cap=0.15 | 42 | 0.9503 | 0.002 | 0.000 | 2.07% | -8.39% | -8.39% | 97.9% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.60\|cap=0.15 | 67 | 0.9503 | -0.005 | 0.000 | -0.59% | -7.03% | -7.03% | 98.1% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.60\|cap=0.15 | 101 | 0.9498 | -0.001 | 0.000 | -0.25% | -4.67% | -4.67% | 97.8% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.60\|cap=0.30 | 11 | 0.9499 | -0.003 | 0.000 | -1.13% | -2.61% | -2.61% | 100.0% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.60\|cap=0.30 | 23 | 0.9500 | 0.006 | 0.000 | 0.41% | 3.44% | 3.44% | 100.0% | yes | 0 |
| A | full_factorial | fill=0.95\|spot=1.60\|cap=0.30 | 42 | 0.9503 | 0.002 | 0.000 | -0.56% | -10.42% | -10.42% | 100.0% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.60\|cap=0.30 | 67 | 0.9503 | -0.005 | 0.000 | -1.92% | -8.42% | -8.42% | 100.0% | no | 0 |
| A | full_factorial | fill=0.95\|spot=1.60\|cap=0.30 | 101 | 0.9498 | -0.001 | 0.000 | -1.88% | -5.71% | -5.71% | 99.9% | no | 0 |
| A | full_factorial | fill=0.85\|spot=1.15\|cap=0.15 | 11 | 0.8499 | -0.003 | 0.000 | 20.00% | 13.37% | 13.37% | 95.7% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.15\|cap=0.15 | 23 | 0.8501 | 0.006 | 0.000 | 24.76% | 21.74% | 21.74% | 96.3% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.15\|cap=0.15 | 42 | 0.8504 | 0.002 | 0.000 | 25.61% | 12.63% | 12.63% | 95.7% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.15\|cap=0.15 | 67 | 0.8504 | -0.005 | 0.000 | 23.38% | 16.73% | 16.73% | 96.5% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.15\|cap=0.15 | 101 | 0.8496 | -0.001 | 0.000 | 21.63% | 17.17% | 17.17% | 95.9% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.15\|cap=0.30 | 11 | 0.8499 | -0.003 | 0.000 | 0.94% | -5.67% | -5.67% | 99.4% | no | 0 |
| A | full_factorial | fill=0.85\|spot=1.15\|cap=0.30 | 23 | 0.8501 | 0.006 | 0.000 | 2.58% | 5.43% | 5.43% | 99.4% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.15\|cap=0.30 | 42 | 0.8504 | 0.002 | 0.000 | 4.01% | -4.20% | -4.20% | 99.5% | no | 0 |
| A | full_factorial | fill=0.85\|spot=1.15\|cap=0.30 | 67 | 0.8504 | -0.005 | 0.000 | 2.95% | -0.65% | -0.65% | 99.7% | no | 0 |
| A | full_factorial | fill=0.85\|spot=1.15\|cap=0.30 | 101 | 0.8496 | -0.001 | 0.000 | 1.79% | -1.08% | -1.08% | 99.4% | no | 0 |
| A | full_factorial | fill=0.85\|spot=1.30\|cap=0.15 | 11 | 0.8499 | -0.003 | 0.000 | 18.95% | 12.59% | 12.59% | 95.8% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.30\|cap=0.15 | 23 | 0.8501 | 0.006 | 0.000 | 23.74% | 20.94% | 20.94% | 96.3% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.30\|cap=0.15 | 42 | 0.8504 | 0.002 | 0.000 | 23.78% | 12.45% | 12.45% | 95.8% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.30\|cap=0.15 | 67 | 0.8504 | -0.005 | 0.000 | 22.36% | 16.91% | 16.91% | 96.6% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.30\|cap=0.15 | 101 | 0.8496 | -0.001 | 0.000 | 20.84% | 17.22% | 17.22% | 96.0% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.30\|cap=0.30 | 11 | 0.8499 | -0.003 | 0.000 | 9.77% | 3.26% | 3.26% | 99.7% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.30\|cap=0.30 | 23 | 0.8501 | 0.006 | 0.000 | 12.17% | 11.92% | 11.92% | 99.7% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.30\|cap=0.30 | 42 | 0.8504 | 0.002 | 0.000 | 13.68% | 5.14% | 5.14% | 99.8% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.30\|cap=0.30 | 67 | 0.8504 | -0.005 | 0.000 | 10.91% | 7.23% | 7.23% | 99.9% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.30\|cap=0.30 | 101 | 0.8496 | -0.001 | 0.000 | 10.00% | 7.56% | 7.56% | 99.7% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.60\|cap=0.15 | 11 | 0.8499 | -0.003 | 0.000 | 17.48% | 11.44% | 11.44% | 95.8% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.60\|cap=0.15 | 23 | 0.8501 | 0.006 | 0.000 | 22.28% | 19.73% | 19.73% | 96.3% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.60\|cap=0.15 | 42 | 0.8504 | 0.002 | 0.000 | 21.13% | 11.64% | 11.64% | 95.8% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.60\|cap=0.15 | 67 | 0.8504 | -0.005 | 0.000 | 20.94% | 16.82% | 16.82% | 96.6% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.60\|cap=0.15 | 101 | 0.8496 | -0.001 | 0.000 | 19.54% | 16.89% | 16.89% | 96.0% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.60\|cap=0.30 | 11 | 0.8499 | -0.003 | 0.000 | 15.70% | 9.33% | 9.33% | 99.8% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.60\|cap=0.30 | 23 | 0.8501 | 0.006 | 0.000 | 20.94% | 19.10% | 19.10% | 99.8% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.60\|cap=0.30 | 42 | 0.8504 | 0.002 | 0.000 | 19.62% | 11.02% | 11.02% | 99.9% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.60\|cap=0.30 | 67 | 0.8504 | -0.005 | 0.000 | 18.90% | 15.35% | 15.35% | 99.9% | yes | 0 |
| A | full_factorial | fill=0.85\|spot=1.60\|cap=0.30 | 101 | 0.8496 | -0.001 | 0.000 | 18.11% | 16.00% | 16.00% | 99.8% | yes | 0 |
| A | full_factorial | fill=0.70\|spot=1.15\|cap=0.15 | 11 | 0.6999 | -0.003 | 0.000 | 18.19% | 12.73% | 12.73% | 85.5% | no | 0 |
| A | full_factorial | fill=0.70\|spot=1.15\|cap=0.15 | 23 | 0.7001 | 0.006 | 0.000 | 20.86% | 16.84% | 16.84% | 86.4% | no | 0 |
| A | full_factorial | fill=0.70\|spot=1.15\|cap=0.15 | 42 | 0.7005 | 0.002 | 0.000 | 18.97% | 12.27% | 12.27% | 85.0% | no | 0 |
| A | full_factorial | fill=0.70\|spot=1.15\|cap=0.15 | 67 | 0.7005 | -0.005 | 0.000 | 20.44% | 17.80% | 17.80% | 86.4% | no | 0 |
| A | full_factorial | fill=0.70\|spot=1.15\|cap=0.15 | 101 | 0.6995 | -0.001 | 0.000 | 19.12% | 17.15% | 17.15% | 85.8% | no | 0 |
| A | full_factorial | fill=0.70\|spot=1.15\|cap=0.30 | 11 | 0.6999 | -0.003 | 0.000 | 23.32% | 17.18% | 17.18% | 96.4% | yes | 0 |
| A | full_factorial | fill=0.70\|spot=1.15\|cap=0.30 | 23 | 0.7001 | 0.006 | 0.000 | 25.42% | 19.92% | 19.92% | 97.0% | yes | 0 |
| A | full_factorial | fill=0.70\|spot=1.15\|cap=0.30 | 42 | 0.7005 | 0.002 | 0.000 | 24.57% | 15.50% | 15.50% | 96.5% | yes | 0 |
| A | full_factorial | fill=0.70\|spot=1.15\|cap=0.30 | 67 | 0.7005 | -0.005 | 0.000 | 25.97% | 21.91% | 21.91% | 97.1% | yes | 0 |
| A | full_factorial | fill=0.70\|spot=1.15\|cap=0.30 | 101 | 0.6995 | -0.001 | 0.000 | 23.54% | 20.19% | 20.19% | 96.6% | yes | 0 |
| A | full_factorial | fill=0.70\|spot=1.30\|cap=0.15 | 11 | 0.6999 | -0.003 | 0.000 | 16.39% | 11.49% | 11.49% | 85.5% | no | 0 |
| A | full_factorial | fill=0.70\|spot=1.30\|cap=0.15 | 23 | 0.7001 | 0.006 | 0.000 | 18.57% | 14.78% | 14.78% | 86.4% | no | 0 |
| A | full_factorial | fill=0.70\|spot=1.30\|cap=0.15 | 42 | 0.7005 | 0.002 | 0.000 | 16.98% | 10.96% | 10.96% | 85.0% | no | 0 |
| A | full_factorial | fill=0.70\|spot=1.30\|cap=0.15 | 67 | 0.7005 | -0.005 | 0.000 | 18.31% | 15.95% | 15.95% | 86.4% | no | 0 |
| A | full_factorial | fill=0.70\|spot=1.30\|cap=0.15 | 101 | 0.6995 | -0.001 | 0.000 | 17.12% | 15.36% | 15.36% | 85.8% | no | 0 |
| A | full_factorial | fill=0.70\|spot=1.30\|cap=0.30 | 11 | 0.6999 | -0.003 | 0.000 | 18.15% | 13.08% | 13.08% | 96.4% | yes | 0 |
| A | full_factorial | fill=0.70\|spot=1.30\|cap=0.30 | 23 | 0.7001 | 0.006 | 0.000 | 19.76% | 15.34% | 15.34% | 97.0% | yes | 0 |
| A | full_factorial | fill=0.70\|spot=1.30\|cap=0.30 | 42 | 0.7005 | 0.002 | 0.000 | 18.92% | 11.94% | 11.94% | 96.5% | yes | 0 |
| A | full_factorial | fill=0.70\|spot=1.30\|cap=0.30 | 67 | 0.7005 | -0.005 | 0.000 | 20.09% | 17.13% | 17.13% | 97.1% | yes | 0 |
| A | full_factorial | fill=0.70\|spot=1.30\|cap=0.30 | 101 | 0.6995 | -0.001 | 0.000 | 18.46% | 16.09% | 16.09% | 96.6% | yes | 0 |
| A | full_factorial | fill=0.70\|spot=1.60\|cap=0.15 | 11 | 0.6999 | -0.003 | 0.000 | 13.83% | 9.76% | 9.76% | 85.5% | no | 0 |
| A | full_factorial | fill=0.70\|spot=1.60\|cap=0.15 | 23 | 0.7001 | 0.006 | 0.000 | 15.36% | 11.92% | 11.92% | 86.4% | no | 0 |
| A | full_factorial | fill=0.70\|spot=1.60\|cap=0.15 | 42 | 0.7005 | 0.002 | 0.000 | 14.14% | 9.12% | 9.12% | 85.0% | no | 0 |
| A | full_factorial | fill=0.70\|spot=1.60\|cap=0.15 | 67 | 0.7005 | -0.005 | 0.000 | 15.28% | 13.35% | 13.35% | 86.4% | no | 0 |
| A | full_factorial | fill=0.70\|spot=1.60\|cap=0.15 | 101 | 0.6995 | -0.001 | 0.000 | 14.28% | 12.84% | 12.84% | 85.8% | no | 0 |
| A | full_factorial | fill=0.70\|spot=1.60\|cap=0.30 | 11 | 0.6999 | -0.003 | 0.000 | 13.88% | 9.79% | 9.79% | 96.4% | yes | 0 |
| A | full_factorial | fill=0.70\|spot=1.60\|cap=0.30 | 23 | 0.7001 | 0.006 | 0.000 | 15.34% | 11.87% | 11.87% | 97.0% | yes | 0 |
| A | full_factorial | fill=0.70\|spot=1.60\|cap=0.30 | 42 | 0.7005 | 0.002 | 0.000 | 14.24% | 9.15% | 9.15% | 96.5% | yes | 0 |
| A | full_factorial | fill=0.70\|spot=1.60\|cap=0.30 | 67 | 0.7005 | -0.005 | 0.000 | 15.37% | 13.41% | 13.41% | 97.1% | yes | 0 |
| A | full_factorial | fill=0.70\|spot=1.60\|cap=0.30 | 101 | 0.6995 | -0.001 | 0.000 | 14.30% | 12.82% | 12.82% | 96.6% | yes | 0 |
| B | correlated_shortfall | tau=0.0 | 11 | 0.8499 | -0.003 | 0.000 | 9.77% | 3.26% | 3.26% | 99.7% | yes | 0 |
| B | correlated_shortfall | tau=0.0 | 23 | 0.8501 | 0.006 | 0.000 | 12.17% | 11.92% | 11.92% | 99.7% | yes | 0 |
| B | correlated_shortfall | tau=0.0 | 42 | 0.8504 | 0.002 | 0.000 | 13.68% | 5.14% | 5.14% | 99.8% | yes | 0 |
| B | correlated_shortfall | tau=0.0 | 67 | 0.8504 | -0.005 | 0.000 | 10.91% | 7.23% | 7.23% | 99.9% | yes | 0 |
| B | correlated_shortfall | tau=0.0 | 101 | 0.8496 | -0.001 | 0.000 | 10.00% | 7.56% | 7.56% | 99.7% | yes | 0 |
| B | correlated_shortfall | tau=0.3 | 11 | 0.8495 | 0.284 | 0.000 | 10.29% | 3.62% | 3.62% | 99.7% | yes | 0 |
| B | correlated_shortfall | tau=0.3 | 23 | 0.8503 | 0.307 | 0.000 | 13.90% | 13.81% | 13.81% | 99.8% | yes | 0 |
| B | correlated_shortfall | tau=0.3 | 42 | 0.8504 | 0.354 | 0.000 | 13.31% | 4.34% | 4.34% | 99.8% | yes | 0 |
| B | correlated_shortfall | tau=0.3 | 67 | 0.8501 | 0.298 | 0.000 | 11.39% | 8.25% | 8.25% | 99.8% | yes | 0 |
| B | correlated_shortfall | tau=0.3 | 101 | 0.8495 | 0.247 | 0.000 | 7.81% | 4.66% | 4.66% | 99.6% | yes | 0 |
| B | correlated_shortfall | tau=0.6 | 11 | 0.8493 | 0.597 | 0.000 | 10.15% | 3.55% | 3.55% | 99.6% | yes | 0 |
| B | correlated_shortfall | tau=0.6 | 23 | 0.8503 | 0.607 | 0.000 | 13.66% | 13.07% | 13.07% | 99.8% | yes | 0 |
| B | correlated_shortfall | tau=0.6 | 42 | 0.8505 | 0.632 | 0.000 | 13.18% | 4.03% | 4.03% | 99.7% | yes | 0 |
| B | correlated_shortfall | tau=0.6 | 67 | 0.8496 | 0.634 | 0.000 | 10.76% | 7.85% | 7.85% | 99.8% | yes | 0 |
| B | correlated_shortfall | tau=0.6 | 101 | 0.8498 | 0.549 | 0.000 | 6.96% | 2.92% | 2.92% | 99.6% | yes | 0 |
| B | demand_intermittency | zero_rate=0.0 | 11 | 0.8499 | -0.003 | 0.000 | 9.77% | 3.26% | 3.26% | 99.7% | yes | 0 |
| B | demand_intermittency | zero_rate=0.0 | 23 | 0.8501 | 0.006 | 0.000 | 12.17% | 11.92% | 11.92% | 99.7% | yes | 0 |
| B | demand_intermittency | zero_rate=0.0 | 42 | 0.8504 | 0.002 | 0.000 | 13.68% | 5.14% | 5.14% | 99.8% | yes | 0 |
| B | demand_intermittency | zero_rate=0.0 | 67 | 0.8504 | -0.005 | 0.000 | 10.91% | 7.23% | 7.23% | 99.9% | yes | 0 |
| B | demand_intermittency | zero_rate=0.0 | 101 | 0.8496 | -0.001 | 0.000 | 10.00% | 7.56% | 7.56% | 99.7% | yes | 0 |
| B | demand_intermittency | zero_rate=0.2 | 11 | 0.8500 | 0.001 | 0.213 | 22.71% | 23.52% | 21.10% | 88.6% | no | 60 |
| B | demand_intermittency | zero_rate=0.2 | 23 | 0.8500 | 0.006 | 0.221 | 33.12% | 39.47% | 33.97% | 91.4% | yes | 60 |
| B | demand_intermittency | zero_rate=0.2 | 42 | 0.8501 | 0.004 | 0.214 | 31.61% | 33.48% | 26.20% | 89.7% | no | 46 |
| B | demand_intermittency | zero_rate=0.2 | 67 | 0.8507 | -0.006 | 0.231 | 33.94% | 33.61% | 34.96% | 92.2% | yes | 58 |
| B | demand_intermittency | zero_rate=0.2 | 101 | 0.8499 | -0.001 | 0.222 | 34.92% | 44.72% | 33.73% | 91.5% | yes | 60 |
| B | demand_intermittency | zero_rate=0.5 | 11 | 0.8503 | -0.002 | 0.492 | 26.40% | 29.24% | 24.50% | 67.2% | no | 120 |
| B | demand_intermittency | zero_rate=0.5 | 23 | 0.8501 | 0.013 | 0.518 | 33.71% | 39.72% | 34.87% | 71.1% | no | 132 |
| B | demand_intermittency | zero_rate=0.5 | 42 | 0.8500 | 0.004 | 0.487 | 33.63% | 36.38% | 32.70% | 69.1% | no | 89 |
| B | demand_intermittency | zero_rate=0.5 | 67 | 0.8514 | 0.001 | 0.510 | 40.39% | 41.87% | 40.76% | 75.0% | no | 130 |
| B | demand_intermittency | zero_rate=0.5 | 101 | 0.8500 | -0.000 | 0.505 | 33.16% | 45.19% | 33.86% | 69.6% | no | 132 |
| B | cost_asymmetry | underage:overage=1.0:1 | 11 | 0.8499 | -0.003 | 0.000 | 10.93% | 3.97% | 3.97% | 99.7% | yes | 0 |
| B | cost_asymmetry | underage:overage=1.0:1 | 23 | 0.8501 | 0.006 | 0.000 | 13.45% | 12.95% | 12.95% | 99.7% | yes | 0 |
| B | cost_asymmetry | underage:overage=1.0:1 | 42 | 0.8504 | 0.002 | 0.000 | 15.20% | 7.26% | 7.26% | 99.8% | yes | 0 |
| B | cost_asymmetry | underage:overage=1.0:1 | 67 | 0.8504 | -0.005 | 0.000 | 11.80% | 8.45% | 8.45% | 99.9% | yes | 0 |
| B | cost_asymmetry | underage:overage=1.0:1 | 101 | 0.8496 | -0.001 | 0.000 | 11.26% | 8.88% | 8.88% | 99.7% | yes | 0 |
| B | cost_asymmetry | underage:overage=3.0:1 | 11 | 0.8499 | -0.003 | 0.000 | 19.46% | 8.67% | 8.67% | 99.7% | yes | 0 |
| B | cost_asymmetry | underage:overage=3.0:1 | 23 | 0.8501 | 0.006 | 0.000 | 23.87% | 20.04% | 20.04% | 99.7% | yes | 0 |
| B | cost_asymmetry | underage:overage=3.0:1 | 42 | 0.8504 | 0.002 | 0.000 | 24.92% | 19.45% | 19.45% | 99.9% | yes | 0 |
| B | cost_asymmetry | underage:overage=3.0:1 | 67 | 0.8504 | -0.005 | 0.000 | 19.25% | 17.78% | 17.78% | 99.9% | yes | 0 |
| B | cost_asymmetry | underage:overage=3.0:1 | 101 | 0.8496 | -0.001 | 0.000 | 20.98% | 17.51% | 17.51% | 99.8% | yes | 0 |
| B | cost_asymmetry | underage:overage=9.0:1 | 11 | 0.8499 | -0.003 | 0.000 | 34.58% | 18.90% | 18.90% | 99.8% | yes | 0 |
| B | cost_asymmetry | underage:overage=9.0:1 | 23 | 0.8501 | 0.006 | 0.000 | 40.46% | 32.22% | 32.22% | 99.8% | yes | 0 |
| B | cost_asymmetry | underage:overage=9.0:1 | 42 | 0.8504 | 0.002 | 0.000 | 39.89% | 37.59% | 37.59% | 99.9% | yes | 0 |
| B | cost_asymmetry | underage:overage=9.0:1 | 67 | 0.8504 | -0.005 | 0.000 | 33.12% | 34.44% | 34.44% | 99.9% | yes | 0 |
| B | cost_asymmetry | underage:overage=9.0:1 | 101 | 0.8496 | -0.001 | 0.000 | 38.74% | 34.15% | 34.15% | 99.8% | yes | 0 |
| B | operator_scale | annual_revenue=6000000.0 | 11 | 0.8499 | -0.003 | 0.000 | 9.77% | 3.26% | 3.26% | 99.7% | yes | 0 |
| B | operator_scale | annual_revenue=6000000.0 | 23 | 0.8501 | 0.006 | 0.000 | 12.17% | 11.92% | 11.92% | 99.7% | yes | 0 |
| B | operator_scale | annual_revenue=6000000.0 | 42 | 0.8504 | 0.002 | 0.000 | 13.68% | 5.14% | 5.14% | 99.8% | yes | 0 |
| B | operator_scale | annual_revenue=6000000.0 | 67 | 0.8504 | -0.005 | 0.000 | 10.91% | 7.23% | 7.23% | 99.9% | yes | 0 |
| B | operator_scale | annual_revenue=6000000.0 | 101 | 0.8496 | -0.001 | 0.000 | 10.00% | 7.56% | 7.56% | 99.7% | yes | 0 |
| B | operator_scale | annual_revenue=15000000.0 | 11 | 0.8499 | -0.003 | 0.000 | 9.77% | 3.26% | 3.26% | 99.7% | yes | 0 |
| B | operator_scale | annual_revenue=15000000.0 | 23 | 0.8501 | 0.006 | 0.000 | 12.17% | 11.92% | 11.92% | 99.7% | yes | 0 |
| B | operator_scale | annual_revenue=15000000.0 | 42 | 0.8504 | 0.002 | 0.000 | 13.68% | 5.14% | 5.14% | 99.8% | yes | 0 |
| B | operator_scale | annual_revenue=15000000.0 | 67 | 0.8504 | -0.005 | 0.000 | 10.91% | 7.23% | 7.23% | 99.9% | yes | 0 |
| B | operator_scale | annual_revenue=15000000.0 | 101 | 0.8496 | -0.001 | 0.000 | 10.00% | 7.56% | 7.56% | 99.7% | yes | 0 |
| B | operator_scale | annual_revenue=50000000.0 | 11 | 0.8499 | -0.003 | 0.000 | 9.77% | 3.26% | 3.26% | 99.7% | yes | 0 |
| B | operator_scale | annual_revenue=50000000.0 | 23 | 0.8501 | 0.006 | 0.000 | 12.17% | 11.92% | 11.92% | 99.7% | yes | 0 |
| B | operator_scale | annual_revenue=50000000.0 | 42 | 0.8504 | 0.002 | 0.000 | 13.68% | 5.14% | 5.14% | 99.8% | yes | 0 |
| B | operator_scale | annual_revenue=50000000.0 | 67 | 0.8504 | -0.005 | 0.000 | 10.91% | 7.23% | 7.23% | 99.9% | yes | 0 |
| B | operator_scale | annual_revenue=50000000.0 | 101 | 0.8496 | -0.001 | 0.000 | 10.00% | 7.56% | 7.56% | 99.7% | yes | 0 |
| B | train_window | train_weeks=26 | 11 | 0.8499 | -0.003 | 0.000 | 17.08% | -1.65% | -1.65% | 99.5% | no | 0 |
| B | train_window | train_weeks=26 | 23 | 0.8501 | 0.006 | 0.000 | 18.43% | 4.66% | 4.66% | 99.5% | yes | 0 |
| B | train_window | train_weeks=26 | 42 | 0.8504 | 0.002 | 0.000 | 17.04% | -5.68% | -5.68% | 99.6% | no | 0 |
| B | train_window | train_weeks=26 | 67 | 0.8504 | -0.005 | 0.000 | 18.47% | 4.00% | 4.00% | 99.8% | yes | 0 |
| B | train_window | train_weeks=26 | 101 | 0.8496 | -0.001 | 0.000 | 17.17% | 0.12% | 0.12% | 99.6% | yes | 0 |
| B | train_window | train_weeks=52 | 11 | 0.8499 | -0.003 | 0.000 | 9.77% | 3.26% | 3.26% | 99.7% | yes | 0 |
| B | train_window | train_weeks=52 | 23 | 0.8501 | 0.006 | 0.000 | 12.17% | 11.92% | 11.92% | 99.7% | yes | 0 |
| B | train_window | train_weeks=52 | 42 | 0.8504 | 0.002 | 0.000 | 13.68% | 5.14% | 5.14% | 99.8% | yes | 0 |
| B | train_window | train_weeks=52 | 67 | 0.8504 | -0.005 | 0.000 | 10.91% | 7.23% | 7.23% | 99.9% | yes | 0 |
| B | train_window | train_weeks=52 | 101 | 0.8496 | -0.001 | 0.000 | 10.00% | 7.56% | 7.56% | 99.7% | yes | 0 |
| B | train_window | train_weeks=78 | 11 | 0.8499 | -0.003 | 0.000 | 14.79% | 4.30% | 4.30% | 99.5% | yes | 0 |
| B | train_window | train_weeks=78 | 23 | 0.8502 | 0.004 | 0.000 | 9.09% | 7.58% | 7.58% | 99.4% | yes | 0 |
| B | train_window | train_weeks=78 | 42 | 0.8504 | 0.001 | 0.000 | 12.74% | 9.76% | 9.76% | 99.7% | yes | 0 |
| B | train_window | train_weeks=78 | 67 | 0.8503 | -0.006 | 0.000 | 17.59% | 7.59% | 7.59% | 99.8% | yes | 0 |
| B | train_window | train_weeks=78 | 101 | 0.8497 | -0.002 | 0.000 | 15.30% | 10.43% | 10.43% | 99.4% | yes | 0 |
| CONTROL | forced_unit_fills | fill=1.0 | 11 | 0.9996 | 0.002 | 0.000 | 7.84% | 16.73% | 16.73% | 99.8% | no | 0 |
| CONTROL | forced_unit_fills | fill=1.0 | 23 | 0.9994 | 0.001 | 0.000 | 6.22% | 14.01% | 14.01% | 99.7% | no | 0 |
| CONTROL | forced_unit_fills | fill=1.0 | 42 | 0.9995 | -0.004 | 0.000 | 2.57% | 7.53% | 7.53% | 99.9% | no | 0 |
| CONTROL | forced_unit_fills | fill=1.0 | 67 | 0.9995 | -0.018 | 0.000 | 9.80% | 7.23% | 7.23% | 99.9% | no | 0 |
| CONTROL | forced_unit_fills | fill=1.0 | 101 | 0.9995 | -0.000 | 0.000 | 11.28% | 12.45% | 12.45% | 99.7% | no | 0 |

# ZAAD frozen synthetic benchmark results

**Verdict: NEEDS FURTHER ENGINEERING.** Runnable decision prototype; not deployment-ready, not real-operator validation, not Oracle parity.

75 cells × 5 untouched future seeds × 8 baseline/controller rows = **3,000 individual runs**. 375 distinct operator/future-path cases—not 3,000 independent operators. The normal core is an 8-target × 5-stock factorial; additional factors are one-at-a-time, not an exhaustive cross-product.

Frozen source SHA-256: `365cac6fe33a40c372daf829d640b1c131ce22a6315832722a922e41917bccb7`. No policy or threshold retuning after this holdout.

[Every run CSV](evidence/holdout_runs.csv) · [JSONL](evidence/holdout_runs.jsonl) · [Preregistration](evidence/preregistered_manifest.json) · [Aggregates](evidence/holdout_summary.json)

## Gated controller, including retained incumbent and abstentions

Savings are percent of this 12-period modeled economic-cost ledger, **not percent of revenue or annual spend**. An abstention is replayed as the incumbent for policy evaluation and explicitly marked; it is not a candidate win. A service breach means at least one SKU misses its requested realized unit-fill target.

| Family | Cases | Median saving | Range | Cost losses | Service breaches | Changes / abstentions |
|---|---:|---:|---:|---:|---:|---:|
| control | 5 | 0.00% | 0.00% to 0.00% | 0 | 0 | 0 / 5 |
| disruption | 60 | 3.08% | 0.00% to 11.39% | 0 | 35 | 55 / 0 |
| normal | 200 | 0.35% | 0.00% to 1.46% | 0 | 33 | 164 / 30 |
| normal_ofat | 75 | 0.34% | -8.79% to 7.57% | 14 | 19 | 58 / 5 |
| signal_ablation | 35 | 4.64% | -3.13% to 6.12% | 10 | 35 | 35 / 0 |

## Stronger baseline comparisons

All methods see the same histories, known pipeline and route constraints. 'Expected/CVaR search' is a finite closed-loop policy family, not the legacy Pyomo stochastic program or a globally optimal stochastic solution. The deterministic baseline searches that same family on mean paths.

| Family | Baseline | Median vs incumbent | Range | Losses | Service breaches |
|---|---|---:|---:|---:|---:|
| disruption | incumbent | 0.00% | 0.00% to 0.00% | 0/60 | 38/60 |
| disruption | base_stock | -3.38% | -8.85% to 0.61% | 46/60 | 45/60 |
| disruption | service_target | 0.00% | -3.22% to 0.00% | 16/60 | 40/60 |
| disruption | deterministic_constrained | 0.00% | -3.22% to 0.00% | 15/60 | 40/60 |
| disruption | expected_search | 0.00% | 0.00% to 0.53% | 0/60 | 38/60 |
| disruption | cvar_search | 4.03% | 0.00% to 12.15% | 0/60 | 33/60 |
| disruption | route_aware | 3.08% | 0.00% to 11.39% | 0/60 | 35/60 |
| disruption | zaad_gated | 3.08% | 0.00% to 11.39% | 0/60 | 35/60 |
| normal | incumbent | 0.00% | 0.00% to 0.00% | 0/200 | 33/200 |
| normal | base_stock | 0.48% | -0.91% to 1.61% | 24/200 | 42/200 |
| normal | service_target | 0.00% | -3.22% to 1.48% | 93/200 | 45/200 |
| normal | deterministic_constrained | -0.31% | -3.22% to 0.97% | 140/200 | 92/200 |
| normal | expected_search | 0.35% | 0.00% to 1.46% | 0/200 | 33/200 |
| normal | cvar_search | 0.29% | -13.18% to 1.33% | 5/200 | 33/200 |
| normal | route_aware | 0.35% | -13.18% to 1.46% | 5/200 | 33/200 |
| normal | zaad_gated | 0.35% | 0.00% to 1.46% | 0/200 | 33/200 |

### Controller versus competent rules, paired on identical realized paths

| Comparator | Median saving | Range | Losses |
|---|---:|---:|---:|
| base_stock | -0.04% | -1.63% to 15.12% | 192/370 |
| service_target | 0.83% | -1.04% to 11.39% | 46/370 |
| expected_search | 0.00% | -2.58% to 11.39% | 5/370 |
| cvar_search | 0.00% | -4.45% to 11.65% | 82/370 |

## Disruption, recovery and signal cells individually

| Cell / variant | Median saving | Range | Service breaches | Changes / abstentions |
|---|---:|---:|---:|---:|
| C055 / no_disruption | 0.46% | 0.30% to 0.53% | 0/5 | 5 / 0 |
| C056 / early_warning | 3.07% | 2.73% to 3.87% | 5/5 | 5 / 0 |
| C057 / mild | 1.93% | 1.26% to 3.92% | 0/5 | 5 / 0 |
| C058 / moderate | 4.69% | 3.24% to 6.12% | 5/5 | 5 / 0 |
| C059 / severe | 10.56% | 10.43% to 11.39% | 5/5 | 5 / 0 |
| C060 / recovery | 0.26% | 0.24% to 0.29% | 0/5 | 5 / 0 |
| C061 / false_alarm | 0.46% | 0.30% to 0.53% | 0/5 | 5 / 0 |
| C062 / late_news | 4.69% | 3.24% to 6.12% | 5/5 | 5 / 0 |
| C063 / already_protected | 2.90% | 2.11% to 3.66% | 3/5 | 5 / 0 |
| C064 / shared_route | 4.90% | 4.64% to 6.09% | 5/5 | 5 / 0 |
| C065 / closed_port | 0.00% | 0.00% to 0.00% | 2/5 | 0 / 0 |
| C066 / no_alternative | 5.55% | 4.37% to 6.71% | 5/5 | 5 / 0 |
| C067 / history_only | -2.48% | -3.13% to -2.46% | 5/5 | 5 / 0 |
| C068 / port | 4.69% | 3.24% to 6.12% | 5/5 | 5 / 0 |
| C069 / ais | 4.69% | 3.24% to 6.12% | 5/5 | 5 / 0 |
| C070 / news | -2.48% | -3.13% to -2.46% | 5/5 | 5 / 0 |
| C071 / freight | 4.69% | 3.24% to 6.12% | 5/5 | 5 / 0 |
| C072 / weather | 4.69% | 3.24% to 6.12% | 5/5 | 5 / 0 |
| C073 / combined | 4.69% | 3.24% to 6.12% | 5/5 | 5 / 0 |
| C074 / force_unit_fills | 0.00% | 0.00% to 0.00% | 0/5 | 0 / 5 |

## Interpretation guardrails

- False-news alarms do not change physical-risk inputs or actions relative to the matching no-signal input. A nonzero saving in that cell is normal inventory optimization, not a news benefit.
- Port/AIS/freight/weather/combined cells currently inject the same synthetic physical-severity contract. Equal results are wiring controls, not independent provider-value measurements. News-only has no physical effect. No paid AIS or freight data was evaluated.
- The late-news fixture makes physical evidence available first. News has no modeled incremental decision role, so it cannot establish news warning lead or value.
- Model stress and final truth differ deliberately: stress predicts +ceil(3s) lead and 30%×s fill loss; realized disruption uses +ceil(4s) lead and 35%×s fill loss, ending at review7. These are assumptions, not fitted causal effects.
- Gate failures in final service are real evidence of model misspecification. Independent Monte Carlo confirmation samples the same assumed model; it does not protect against that misspecification.
- No 100% service guarantee, real-data ROI, measured TAM, production readiness, calibrated event probability or commercial no-harm claim follows.
- No legacy report is overwritten. Prior service failure mechanism is reproduced separately in CURRENT_STATE_AUDIT.md.

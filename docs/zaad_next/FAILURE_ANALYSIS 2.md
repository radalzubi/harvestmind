# ZAAD final failure analysis — no retuning

## Decision

**NEEDS FURTHER ENGINEERING.** Across375 final controller cases,24 cost losses and122 SKU-service breaches were retained. There are zero observed physical-capacity breaches across all3,000 rows. Passing physical tests does not imply adequate customer service or incremental commercial value.

`evidence/loss_diagnostics.csv` enumerates all646 cost-losing baseline rows, identifying each seed/cell/policy and the exact consumed-goods, freight, holding, disposal and lost-sales delta. The dominant accounting term is not mislabeled a proven causal mechanism. All original run metadata remains in CSV/JSONL.

## Gated cost-loss families

| Variant | Losing controller cases | Observed range of affected family | Mechanism assessment |
|---|---:|---|---|
| Intermittent20% | 1/5 | −0.72% to +7.57% | Forecast selection/variance and finite policy family; not isolated causal proof |
| Intermittent50% | 3/5 | −1.65% to +1.84% | Small-sample demand/stock tradeoff; Croston/TSB routing does not ensure decision superiority |
| Unannounced promotion | 5/5 | −3.69% to −2.17% | Known injected demand increase is absent from training/inputs; leaner policy loses protective stock |
| Structural demand shift | 5/5 | −8.79% to −7.27% | Forecast held fixed through replay; no real-time break adaptation; worst controller cost family |
| No external warning during disruption | 5/5 | −3.13% to −2.46% | True future deterioration absent from supplied risk state; normal lean candidate underprotects |
| News-only during disruption | 5/5 | same as no warning | News has no physical-risk decision effect; this is not a failed learned news model |

Exact per-seed observations are in BENCHMARK_RESULTS.md / raw rows. No favourable overall median can remove these failures.

## Service feasibility

Normal factorial33/200 service misses:30 begin with0.1week stock at targets93–99.5%; the controller abstains, and the incumbent also fails because existing supply cannot serve the first period. Two changed plans and one retained incumbent miss high targets with one week's opening stock. This separates initial infeasibility from candidate-caused cost loss, without excusing missed service.

Disruption35/60 misses: early warning, moderate, severe, late-news, shared-route and no-alternative variants each5/5; already-protected3/5; closed-port2/5. The modeled+ceil(3s) delay and30%s fill loss understate final+ceil(4s) delay and35%s fill loss. This is intentionally misspecified synthetic truth. These results demonstrate that the simulation confirmation gate is **not decision-grade safety against model error**.

All35 feed-ablation cases miss service. Some cost improvements are genuine within the ledger, but 'cheaper while failing service' is not an approved commercial recommendation. The UI labels all proposals experimental and human-review only; do not connect them to write-back.

## Other defects caught before freeze

- Legacy target-only LP could withhold37.5773 available units at review0, producing exactly that later replay shortfall on the same scenarios. New settlement is work-conserving.
- Candidate confirmation figures were initially compared with selection incumbent figures; fixed to paired same-world economics.
- Reserved/damaged inventory initially did not consume physical storage; corrected.
- Due-now POs initially differed between emitted and simulated first action; normalized and regression-tested.
- JSON signals initially conflicted with strict tuple/datetime parsing; validated at the canonical request boundary.
- Route quote validity initially applied only at origin; enforced at every projected review.
- Missing risk evidence initially could imply recovery; explicit fresh recovery now required.

Those are development fixes, not post-holdout tuning. Frozen final outputs reflect the corrected versions.

## Remaining engineering by failure class

Forecast error: promotion/structural adaptation, intermittent calibration, richer history before high service promises. False positive/negative: actual prospective warning labels and non-events; current news-only negative control passes but does not test every physical false alarm. Horizon/pipeline: uncertain pending ETA and censoring, beyond-horizon expiry/salvage, dynamic re-estimation. Service formulation: work-conserving replay is fixed; out-of-model service robustness remains unproved. Cost/capacity: accepted-payment assumptions and conservative storage require operator reconciliation; alternate quotes/volume bounds are explicit. Infeasibility: identify unavoidable initial shortfall separately and do not promise missing supply. Instability: churn measured, no switching-penalty optimizer yet. Stale/thin data: validated abstention exists, but persistent risk-state quality and aging supplier estimates remain gaps.

Next work should be these mechanisms on new development evidence—not further market valuation or relabeling the present sweep as validation.

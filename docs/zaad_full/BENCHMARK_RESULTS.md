# ZAAD v2 synthetic benchmark results

**Verdict: NEEDS FURTHER ENGINEERING.** These are synthetic engineering measurements, not customer validation, market ROI, or an autonomous-deployment approval.

Frozen engine commit: `488ab4c`; source fingerprint `394b8d304ebaab052d21b7501941770e5dd984ddb5427274a4ada77922d7a420`. Seeds: 22001, 22002, 22003, 22004, 22005. 85 coverage cells × 5 seeds × 7 methods = 2,975 rows.

[Every JSONL run](evidence/final_v2/final.jsonl) and [flat CSV](evidence/final_v2/runs.csv) retain parameters, seeds, failures, service, and costs. 425 matched path cases are not 2,975 independent operators. The 7,560-cell normal Cartesian experiment was not executed.

## Against competent projected base-stock

Savings use modeled economic cost, not operator turnover. A completed run can still breach its requested service floor. Incomplete pairs are excluded only from percentages, never erased from attempted/failure counts. This is not an intention-to-treat claim of guaranteed savings.

| Method | Complete / attempted | Service breaches among complete | Paired complete | Median saving [range] | Cost losses |
|---|---:|---:|---:|---:|---:|
|base_stock|415/425|284/415|415|+0.00% [+0.00, +0.00]|0|
|order_up_to|415/425|365/415|415|-3.49% [-22.57, +14.76]|347|
|deterministic|414/425|370/414|414|-2.99% [-24.25, +28.52]|293|
|stochastic|416/425|297/416|414|+2.13% [-43.62, +27.77]|108|
|robust|402/425|176/402|401|+5.50% [-28.55, +36.91]|67|
|frozen_forecast|415/425|309/415|415|+0.53% [-45.97, +28.45]|195|
|gated|415/425|279/415|415|+1.58% [-7.62, +14.48]|13|

## Status audit

| Method | Status | Count |
|---|---|---:|
|base_stock|COMPLETE|415|
|base_stock|INFEASIBLE|10|
|deterministic|COMPLETE|414|
|deterministic|INFEASIBLE|11|
|frozen_forecast|COMPLETE|415|
|frozen_forecast|INFEASIBLE|10|
|gated|ABSTAIN|10|
|gated|COMPLETE|415|
|order_up_to|COMPLETE|415|
|order_up_to|INFEASIBLE|10|
|robust|COMPLETE|402|
|robust|INFEASIBLE|9|
|robust|PHYSICAL_FAILURE|1|
|robust|TIME_LIMIT|13|
|stochastic|COMPLETE|416|
|stochastic|INFEASIBLE|9|

## Normal family

| Method | Complete / attempted | Service breaches among complete | Paired complete | Median saving [range] | Cost losses |
|---|---:|---:|---:|---:|---:|
|base_stock|295/295|183/295|295|+0.00% [+0.00, +0.00]|0|
|order_up_to|295/295|255/295|295|-3.52% [-22.57, +14.76]|241|
|deterministic|294/295|255/294|294|-1.91% [-24.25, +28.52]|207|
|stochastic|294/295|192/294|294|+2.23% [-43.62, +27.77]|54|
|robust|283/295|94/283|283|+3.47% [-28.55, +27.92]|59|
|frozen_forecast|295/295|203/295|295|+1.72% [-45.97, +28.45]|114|
|gated|295/295|180/295|295|+1.71% [-7.62, +14.18]|11|

## Disruption family

| Method | Complete / attempted | Service breaches among complete | Paired complete | Median saving [range] | Cost losses |
|---|---:|---:|---:|---:|---:|
|base_stock|80/85|74/80|80|+0.00% [+0.00, +0.00]|0|
|order_up_to|80/85|80/80|80|-2.87% [-5.91, +0.98]|77|
|deterministic|80/85|80/80|80|-5.24% [-11.63, +6.25]|62|
|stochastic|81/85|75/81|80|+0.21% [-8.40, +9.79]|39|
|robust|80/85|65/80|80|+12.27% [-1.82, +27.99]|5|
|frozen_forecast|80/85|76/80|80|-5.01% [-10.59, +9.12]|57|
|gated|80/85|74/80|80|+1.41% [+0.00, +3.59]|0|

## Misspecification family

| Method | Complete / attempted | Service breaches among complete | Paired complete | Median saving [range] | Cost losses |
|---|---:|---:|---:|---:|---:|
|base_stock|25/25|25/25|25|+0.00% [+0.00, +0.00]|0|
|order_up_to|25/25|25/25|25|-2.52% [-5.81, +0.74]|22|
|deterministic|25/25|25/25|25|-8.23% [-19.08, +2.13]|23|
|stochastic|25/25|25/25|25|-1.47% [-14.77, +19.61]|14|
|robust|25/25|15/25|25|+26.00% [+16.14, +36.91]|0|
|frozen_forecast|25/25|25/25|25|-8.82% [-21.48, +3.13]|23|
|gated|25/25|25/25|25|+1.09% [-0.13, +11.93]|1|

## Action family

| Method | Complete / attempted | Service breaches among complete | Paired complete | Median saving [range] | Cost losses |
|---|---:|---:|---:|---:|---:|
|base_stock|15/20|2/15|15|+0.00% [+0.00, +0.00]|0|
|order_up_to|15/20|5/15|15|+0.72% [-5.40, +4.20]|7|
|deterministic|15/20|10/15|15|+5.96% [-0.65, +13.66]|1|
|stochastic|16/20|5/16|15|+8.86% [-0.65, +15.45]|1|
|robust|14/20|2/14|13|+12.45% [-4.16, +15.23]|3|
|frozen_forecast|15/20|5/15|15|+7.57% [-0.65, +17.71]|1|
|gated|15/20|0/15|15|+5.72% [-0.21, +14.48]|1|

## Recovery PO fixture

| Method | Complete / attempted | Service breaches among complete | Paired complete | Median saving [range] | Cost losses |
|---|---:|---:|---:|---:|---:|
|base_stock|5/5|0/5|5|+0.00% [+0.00, +0.00]|0|
|stochastic|5/5|0/5|5|+2.11% [-0.65, +3.69]|1|
|robust|5/5|0/5|5|-0.26% [-4.16, +1.72]|3|
|gated|5/5|0/5|5|+2.07% [-0.21, +2.42]|1|

## Direct comparator checks

| Comparison | Paired complete | Median saving [range] | Cost losses |
|---|---:|---:|---:|
|gated vs deterministic (all)|414|+3.84% [-32.98, +26.58]|100|
|stochastic vs deterministic (all)|413|+3.15% [-71.82, +29.34]|92|
|robust vs stochastic (misspecification)|25|+28.37% [+16.96, +39.07]|0|
|stochastic vs frozen_forecast (increase)|20|+13.85% [+3.02, +27.44]|0|
|stochastic vs frozen_forecast (decrease)|20|+0.23% [-30.96, +9.73]|9|

## Service-qualified economic pairs

Both policies must complete and meet their requested aggregate fill target. These selected pairs do not rescue the failures outside the subset.

| Method vs base-stock | Both meet service | Median saving [range] | Losses |
|---|---:|---:|---:|
|order_up_to|50|+1.22% [-5.44, +14.76]|21|
|deterministic|41|+3.90% [-4.98, +28.52]|14|
|stochastic|100|+2.26% [-43.62, +16.42]|6|
|robust|118|+1.69% [-28.55, +21.33]|42|
|frozen_forecast|79|+2.89% [-7.09, +28.45]|9|
|gated|130|+2.06% [-2.33, +13.40]|6|

## Interpretation limits

- Requested aggregate service is measured separately from cost. A breach is not automatically an optimizer bug or unavoidable: this experiment does not contain an ex-post joint feasibility certificate for every path.
- Several named disruption cells share the same physical mapping; they do not establish independent news timing, AIS, port, or learned causal effects.
- The base-stock policy is a disclosed fill-aware target projected through common physical and cash constraints. It is stronger than an unconstrained strawman but is not a real operator's observed incumbent.
- `recovery_solves` in raw rows actually counts reviews with any warning, including gate reasons. Do not interpret that field as a count of lexicographic recovery solves.
- The shrinking finite financial horizon, sparse scenario counts and assumed stress envelopes limit extrapolation. Post-horizon invoices remain obligations, not a later-date liquidity guarantee.
- Earlier validation and first final attempt remain available. The first final uncovered unreceived overdue POs funding immediate transfers. A separate corrected preflight was stopped for type-check cleanup without analyzing its outcome metrics. This result uses fresh seeds after both corrections.

See [failure analysis](FAILURE_ANALYSIS.md), [feature probes](ABLATIONS.md), [commercial answers](COMMERCIAL_ANSWERS.md), and [verification](VERIFICATION.md).

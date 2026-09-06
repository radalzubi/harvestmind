# False protection: state-dependent decay in the reliability profile

Branch `claude/zaad-false-protection`, stacked on PR 30 (`claude/zaad-service-reliability`).
Nothing is merged. The PR 30 reliability profile is preserved exactly as
`Request.protection_decay = False` (benchmark method `gated_pr30`); the frozen PR 23/24
engine remains `engine_profile: "pr24"`. New seeds only: `development3` (26001) and
`validation3` (27001, 27002). `holdout3` is untouched.

PR 30 result to beat: breaches 69 vs 74, avoidable 15 vs 20, median service .904 vs .872,
inventory **1.93 vs 1.37** periods of demand, benign-cell inventory .89 vs .48.

## 1. What caused the false protection

The decomposition (`scripts/diagnose_zaad_false_protection.py`, evidence under
`docs/zaad_full/evidence/false_protection/diag_*.json`) replayed single cells with one
component switched off at a time. Findings, in order of size:

1. **Symmetric, unbounded young-regime widening.** After a detected level change the level
   standard error was inflated by the size of the shift itself, in both directions, for
   eight observations. After a *decrease* this fabricated demand worlds above the old
   level, so the quantile constraint bought stock for demand that could not exist. Decrease
   cells carried 2.0 periods against 1.1 frozen; the widening was the whole difference.
2. **Root-mean-square residual spread.** One abnormal week entered the twelve-observation
   residual window as a squared term, widened the effective spread and the level error for
   the whole window, and repopulated the scenario bootstrap with the spike. Spike and
   temporary-spike cells carried 1.4 to 1.6 periods against 1.0 to 1.3 frozen.
3. **Calibration counted twice.** A calibration ratio above one already widens the sampled
   deviations; in PR 30 it also raised the protection profile and, through the shared
   spread, the proxy incumbent. Under the benchmark's history (normal, sd 2) against its
   truth (Poisson, sd 4.5) every stable cell reads as under-covered from the first review
   and never returns inside the band, so "calm" cells were treated as active for the whole
   horizon.
4. **Stress hedge floor with no evidence.** The declared severe stress kept a tenth of its
   weight on every source, including sources whose receipts were clean; on 90% and 95%
   quiet cells that changed which candidate the selector picked without improving service.
5. **Supply state saturated by normal fill.** The partial-delivery probability was measured
   against a 95% threshold, so a supplier that delivers 95% on average scored a 50% partial
   probability and a fully active supply driver. Every declared source therefore looked
   risky.
6. **Quantile protection not conditioned on state.** The CVaR level was a constant .5
   whatever the SKU's replenishment speed, alternatives or evidence.

Not found: double counting between lead-time and fill spread (they enter as independent
variances divided by the effective number of independent sources), or between the profile
and the optimizer (the profile drives only the proxy incumbent and the report). The
high-target quiet cells (97%, 99%) were not false protection: the frozen proxy breaches a
99% target at .968 service, and the reliability profile's extra stock there buys the
service the customer asked for.

## 2. What changed (`protection_decay = True`)

| Component | PR 30 | Decay |
|---|---|---|
| Residual scale | root-mean-square of the last 12 residuals | 80th percentile of absolute residuals / 1.28 (one outlier does not move it); outliers counted and aged |
| Calibration ratio | applied as measured, up to 4x | dead band to 1.25, cap 2x; widens the scenario spread only, never the activity |
| Young regime | level error += shift x (1 - age/8), both directions | **downward**: bounded mixture, a fading share of worlds keeps the old (higher) level; **upward**: PR 30 widening kept (the shortage side is the expensive one) |
| Spike in bootstrap | sizes resampled as observed | under decay, sampled sizes capped at mean + 3 robust sd while an outlier is in the window |
| Supply state | late + partial(<95%) + signal | 2 x late + fill shortfall below 90% + fill spread above .05 + signal; normal fill scores 0 |
| Stress hedge floor | always a tenth of the weight | a tenth only while some approved source has no observed record; clean observed records mean no floor |
| Quantile (CVaR) level | .5 for every service | .5 x activity per SKU/location; activity = max(demand event score, supply score) x (1 - resilience/2); zero (expected floor only) when activity <= .05 |
| Activity: demand | n/a | level change younger than 8 observations, or two or more outliers in the last 6 residuals; persistent widening is not an event |
| Resilience | n/a | 1 if replenishment <= 2 periods and (>= 1.5 independent sources or substitute stock covers the window); .5 for one of the two; 0 otherwise |

The optimizer is not redesigned: the same candidates, gates, recovery and settlement run;
only the uncertainty inputs and the per-service quantile level change with state.

## 3. Diagnostics in every report (`report["false_protection"]`)

Per SKU and location: `protection_units`, `lean_baseline_units` (protection with every
active driver removed: fitted demand spread and the declared lead and fill spread only),
`incremental_protection_units`, `active_drivers` (demand, supply, inbound ETA with scores
and reasons), `risk_active`, `decaying` (active but nothing abnormal in the last two
observations and supply below half-active), `periods_to_lean` (reviews until the young
regime matures or the outlier cluster leaves the window, or six clean receipts for a supply
driver), `false_protection_flag` (calm state yet protection above the lean baseline), the
per-service quantile levels, and the explanation sentence, for example "Risk state:
decaying (demand, activity 0.25); expected return to lean in 3 period(s) if nothing new
happens."

<!-- EVIDENCE -->
EVIDENCE_PLACEHOLDER

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
## 4. Evidence (new seeds; every row retained under `docs/zaad_full/evidence/false_protection/`)

Paired replays of the gated planner under the frozen PR 24 profile, the PR 30 profile
(`protection_decay=False`) and the decay profile, plus the competent base-stock baseline.

| | Development3 (56 cells) | | | Validation3 (112 replays) | | |
|---|---|---|---|---|---|---|
| | PR 24 | PR 30 | **decay** | PR 24 | PR 30 | **decay** |
| Service breaches | 38 | 37 | 37 | 74 | 69 | 71 |
| Avoidable breaches | 3 | 2 | 2 | 8 | 3 | 5 |
| Median service | .872 | .925 | .919 | .872 | .904 | .895 |
| Inventory, median periods | 1.26 | 1.76 | 1.75 | 1.37 | 1.90 | 1.82 |
| Quiet-cell inventory | .57 | .68 | .49 | .48 | .91 | .78 |
| Decrease cells inventory | .91 | 1.71 | 1.32 | 1.49 | 2.76 | 2.20 |
| Partial-delivery cells inventory | .71 | 1.39 | .98 | 1.30 | 2.64 | 2.20 |
| Saving vs base stock (median) | +1.95% | +1.15% | +0.50% | +2.04% | +1.69% | +2.24% |

Paired, decay versus PR 30 on the same cell and seed: development inventory lower in 33 of
49, service wins 11 / losses 29; validation inventory lower in 80 of 100, cost wins 42 /
losses 58, service wins 18 / losses 57. Decay versus frozen PR 24 on validation: service
wins 56 / losses 32, inventory higher in 79 of 104.

### Reading, honestly

- **Quiet cells are leaner**: 28% (development) and 14% (validation) less inventory than
  PR 30 on stable-demand, stable-supply cells; post-decrease cells 23% and 20% leaner;
  partial-delivery cells 30% and 17% leaner. These are the cells the diagnosis named.
- **Overall inventory did not fall materially**: 1.82 against 1.90 periods on validation,
  4%. The bulk of PR 30's extra stock sits in variable-fill, late-supplier and severe cells
  where the supply driver is genuinely active and the profile keeps protecting, and in the
  persistent calibration widening that the benchmark's normal history against Poisson truth
  triggers on every cell.
- **Service slipped slightly**: two more breaches and two more avoidable breaches than
  PR 30 on validation, median service .895 against .904, and PR 30 wins the paired service
  comparison three to one. The decay profile still beats the frozen PR 24 planner on
  service (56 / 32) with fewer breaches (71 against 74).
- **High-risk cells stayed protected**: late-supplier cells 3.12 periods and .828 service
  (PR 24: 2.61 and .737); severe cells .667 against .598.
- **Recovery**: median time from first stockout to full service is 2 periods for every
  profile; the benchmark horizon is too short to show a full decay back to lean after a
  disruption, which the `periods_to_lean` diagnostic reports but the replay cannot verify.

### Verdict for this cycle

**NEEDS FURTHER FALSE-PROTECTION ENGINEERING.** The causes were identified and the fixes
work where they were aimed, but the overall reduction is 4%, not material, and it costs a
small amount of service. No parameter was changed after the validation result. The next
cycle, if opened, should target the calibration widening under history/truth spread mismatch
and the supply-driver protection sizing on variable-fill cells, with a fresh untouched
holdout.


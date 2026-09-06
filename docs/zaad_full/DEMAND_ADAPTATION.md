# Dynamic demand adaptation

Every replay review observes actual current receipts, updates its visible state,
fits demand, optimizes, executes one review, settles demand, then appends observed
demand to the next training window. Future realized demand/receipts never reach
the current choice. Completed supply outcomes update fill estimates only on arrival.

Two-sided clipped CUSUM uses a trailing baseline, .5 drift allowance,4.5 threshold,
and a minimum baseline window. One isolated spike cannot trigger a reset; two
large persistent observations can. These are engineering defaults, not calibrated
business alarm rates. A detected regime reselects/refits on the recent segment.

Candidates: moving average, EWMA, Croston-SBA, TSB, recent level, and eligible
seasonal-naive. Selection uses chronological shortage/holding decision loss,
not MAE alone. Occurrence and positive size are sampled separately to retain
actual zero-demand probability; scaling preserves estimated unconditional mean.

Known-future promotions/events carry known-at, start/end and multiplier. They
are admitted only if known at the origin. Unannounced promotions cannot be
known early by this model; adaptation begins after observations arrive.

Compared methods: Croston/SBA and TSB fit the existing data and dependencies;
ADIDA and fitted zero-inflated/hierarchical models remain alternatives, not newly
implemented capabilities. [Forecasting: Principles and Practice](https://otexts.com/fpp3/counts.html)
explains Croston's occurrence/size decomposition;
[River's Page–Hinkley documentation](https://riverml.xyz/0.10.0/api/drift/PageHinkley/)
describes the alternative online detector. Synthetic change tests show mechanism,
not a universal detection-delay or savings guarantee.

## Alternative downward-shift rules (PR 24 follow-up study)

`Request.demand_adaptation` selects the changepoint rule: `symmetric`
(default, the frozen PR 23 rule), `asymmetric` (downward threshold 6.5 with a
two-observation confirmation), `soft` (blended pre/post fit) and `ensemble`
(decision-loss weighted blend). They were compared on new seeds only
(development2 23001, validation2 24001 and 24002) with paired cost and
service comparison against `symmetric`.

Result: none improves the decrease cells. On development2 all three lose the
majority of paired decrease comparisons for the `gated` and `stochastic`
methods (worst single losses +15% soft, +18% ensemble). On validation2 the
asymmetric rule is neutral in median on decrease cells, raises `gated`
service breaches from 1 to 3 there, and only helps stable cells by
suppressing false alarms. `symmetric` stays the default; the other modes are
retained opt-in with their adverse evidence in
`docs/zaad_full/evidence/adaptation/`. The traced cause of the original
downshift harm is the gated planner's proxy candidate behaviour under stress
rejection, described in [PR24_FOLLOWUP.md](PR24_FOLLOWUP.md).

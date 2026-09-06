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

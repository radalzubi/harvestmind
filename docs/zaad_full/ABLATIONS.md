# Paired feature probes

All dollars below are modeled **six-period synthetic-fixture economic cost**,
disabled minus enabled, not customer savings or annual revenue. Five seeds
18001–18005 use identical evaluation paths within each pair. These probes were
rerun on frozen engine `488ab4c`; raw results are in
[`evidence/final_v2/ablations.json`](evidence/final_v2/ablations.json).

| Feature | Median benefit | Range | Cost losses / pairs |
|---|---:|---:|---:|
|Continuous quantities vs artificial 10-unit restriction|$7.66|−$36.64 to +$15.48|1/5|
|Transfers and network placement|$245.10|$137.17 to $306.21|0/5|
|Approved substitution|$185.46|$147.14 to $208.79|0/5|
|Contractual cancellation|$114.50|$114.50 to $114.50|0/5|
|Contractual de-expediting|$130.03|$123.28 to $134.76|0/5|

Transfers and placement are **one mechanism in this experiment**; their benefits
cannot be added together as separate MEIO and transfer wins. There is no standard
guaranteed-service MEIO comparator here. The de-expediting fixture explicitly
makes cancellation expensive and keeping the old shipment more costly. Its
result establishes conditional option value, not prevalence of such contracts.

All five stress-envelope probes were physically usable. They improved service
in three pairs and tied in two; even the best resulting unit fill was only50%.
No amount of optimization made this deliberately understocked network meet95%.
The five forced-unit-fill controls **all kept the approval gate closed**.

Continuous quantities lost money on one held-out draw despite enlarging the
training feasible set. An in-sample optimization dominance theorem does not
guarantee held-out economic dominance; this loss is retained.

## What is not established

The full eleven-feature ablation request is **not complete**. Separate measured
incremental value remains missing for standalone MEIO vs a credible MEIO
incumbent, supplier allocation, cash constraints, customer segmentation, and
censored ETA. Their constraints/mechanics have unit tests, but a unit test is
not a commercial value estimate. Robustness and adaptive-vs-frozen forecasting
also have direct comparisons in the final rolling benchmark; those comparisons
remain conditional on the coverage matrix and should not be extrapolated to
unseen customers.

These probes draw held-out paths from the fitted family. The broader rolling
benchmark uses a separate truth generator and misspecified stress severity.
Neither experiment uses real operator records.

Substitution is a **cost win, not a measured service-protection win** in these
fixtures: enabled and disabled both reach100% in three seeds; enabled reaches
99.17% and99.68% in the other two while disabled remains100%. This prevents a
cheaper policy being incorrectly advertised as better service.

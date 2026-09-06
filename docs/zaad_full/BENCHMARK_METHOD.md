# Evidence protocol

PR21's seeds and results remain historical. New work has development seeds14001,
pre-freeze validation15001–15002, and a separately registered final seed set.
The exact final manifest is in `evidence/preregistered.json`; the executable
checks its source hash and refuses both changed code and output overwrite.

The executed coverage matrix has85 cells:35 service-target×opening-cover cells,
24 demand/supply combinations with rotated topology/dependence,17 disruption
labels,5 explicit misspecification settings and4 action fixtures. Five final seeds
and seven methods yield2,975 policy rows, representing425 operator/path cases,
**not2,975 independent operators**. A full Cartesian normal matrix is available
with `--matrix full`, but is not the executed experiment.

Methods: projected fill-aware base-stock; projected order-up-to; deterministic
network; stochastic network; stress-envelope network; frozen-demand baseline;
gated incumbent-first controller. Every method uses common physical settlement,
source resources, costs and financial constraints. The baseline projection is
explicit; there is no phantom unconstrained supplier capacity.

Truth is generated separately from the fitted bootstrap: Poisson/occurrence
demand, independently drawn fill/lead and explicitly mismatched disruption
severity/recovery. The replay observes current arrivals before choosing actions;
future realizations stay private. It refits demand every review and updates fill
only after observed arrival. Known promotions are origin-visible; structural
increases/decreases are not. Supplied planning horizons shrink during this finite
replay instead of inventing future financial/capacity records.

Some disruption labels currently share the same physical generator mapping. They
test wiring, not distinct learned news/port/AIS effects; early versus late news
lead advantage is not established. Final stress cases are assumptions, not measured
Jordanian logistics statistics. No annualization or percentage-of-revenue claim.

All rows carry cell/seed/method/parameters, status, failed review count, service,
ledger, forecast method/change origin, cash/debt and runtime. Percent savings use
absolute base-stock modeled economic cost as denominator. Reports use
`statistics.median`, ranges, loss counts and failed-run counts. Incomplete failures
are never treated as zero cost; paired summaries disclose the completed subset.

Separate paired action probes and five force-unit-fill gate controls are retained
in `ablations.json`. The scale probe is a sparse deterministic4-period workload,
not the full stochastic fleet. Pending receipts, censored tails, timeouts and
physically impossible states must remain visible in failure analysis.

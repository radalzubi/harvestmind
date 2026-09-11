# Zaad news and physical-signal model

Implementation reference: `zaad/signals.py`, `zaad/engine.py::prepare`, `route_parameters`, `draw_paths`. These are explicit descriptive stress mappings, **not calibrated event probabilities, fitted causal effects, or validated savings predictions**.

## Observation to decision

1. A frozen `Signal` carries source identity, entity IDs, observation/publication/ingestion times, effective/expiry times, direction, magnitude, confidence, rights status and adapter version. No article body, executable instruction or arbitrary tool action is accepted.
2. Evidence is available only when observation, publication and ingestion are all no later than `as_of`; effective time must also have begun. Unapproved rights and reconstructed historical vintages are excluded. Ingestion today cannot create a signal supposedly available in 2024.
3. Matching uses exact route, supplier, edge, graph-node and shared-failure-domain identifiers. Geographic mapping is explicit. A text mention of a region is not enough. The NWS adapter emits UGC weather-zone identifiers; a commercial graph must deliberately map them to exposures before a weather alert can affect a route.
4. Newer versions in the same event/syndication family supersede older ones. Syndicated articles do not become multiple independent confirmations. One publisher does not count repeatedly merely by publishing many distinct pieces. An expired cancellation cannot resurrect an older warning.
5. Freshness weight is `2 ** (-age_hours / half_life_hours)`, with assumed half-lives: physical 6 hours, news 12 hours, official 24 hours. Weight below 0.01 is excluded. These constants are configurable-design candidates to calibrate later, not learned provider reliability.
6. Physical and official deterioration scores are the maximum bounded weighted magnitude across eligible observations, not a sum that grows with duplicated coverage. Returned evidence separately reports news count, IDs, recovery IDs and missing-evidence reason.
7. The engine uses `max(physical_severity, official_severity)` as route severity. News count is displayed as corroborating context **but does not change lead time, fill, ordering or route availability** in this implementation. The first test of news value therefore remains open; the implementation intentionally makes no such claim.

## Exact current stress transformation

For an aware planning policy and severity `s`, route mean accepted fill is multiplied by `1 - 0.30*s`; planned lead time increases by `ceil(3*s)` periods. The physical scenario generator applies the same severity-based shift to sampled supplier history. Descriptive score is capped at one. The constants and step rounding are assumptions. A tiny positive severity can add one whole period, so sensitivity near zero must be reported; this is not a smooth calibrated dose-response model.

Every policy is evaluated against the same sampled physical world, including incumbent/base-stock policies that ignore the signal when deciding. That is fair for a **conditional stress experiment**, but it does not establish that real signals forecast actual disruptions: the scenario generator is explicitly instructed that the signal has an effect. A claimed real-signal advantage would be circular unless a separate out-of-time outcome dataset independently measures the event/lead-time realization. A negative-control generator must also include false alarms, missed events, delayed warnings and incorrect direction, rather than assuming all warnings are correct.

Current signals stress newly modeled route draws. Known PO expected quantities and dates are held fixed in the model; no claim is made that it updates each in-transit shipment ETA from live AIS. A confirmed legal/physical closure should be represented as an unavailable edge or blocked/unreviewed route input, not inferred from this magnitude score. No automatic legal clearance is generated.

## Shared exposure, not an estimated copula

`draw_paths` draws one rank stream per shared failure domain and combines it with each route's independent rank. A marginal CDF correction avoids automatically depressing every marginal merely because a route has more domains. Routes sharing a port/domain have positively associated supply draws; merely changing supplier names cannot erase that common exposure. Routes with no shared domain have independent rank streams in this generator.

This is structural coupling, **not** an estimated copula, fitted Kendall tau, calibrated tail dependence or evidence of diversification value. Historical fill/lead pairs are sampled together, preserving that empirical pairing; cross-route joint history is not fitted. Correlation, service and policy-value claims must be reported separately.

## Recovery and missing evidence

An eligible recovery observation supersedes deterioration in the same event family and is returned explicitly. It does not erase an independent contradictory warning. Missing, expired, unlicensed, irrelevant and reconstructed observations all mean absent evidence, not proof of normal conditions. Mode transitions should require explicit recovery or operator-cleared state; stale feeds alone must never trigger an automatic unwind. Prior protective mode without a usable retained risk-state magnitude is insufficient to reconstruct a new exposure distribution.

## Historical fixture boundary

`data/zaad/baltimore_official_metadata.json` records a genuine official June 10, 2024 reopening notice. Its exact publication hour and original captured response are not available. The next-local-day upper bound is documented separately; `published_at` is null and `historical_eligible` is false. It cannot be promoted into the strict signal contract without fabricating evidence. The fixture demonstrates exclusion and date-precision reporting, not historical warning accuracy. See [data-source audit](DATA_SOURCE_AUDIT.md) for the official URLs.

## Regression evidence and remaining empirical work

`tests/unit/test_zaad_signals.py` tests records, temporal gates, immutable replay, freshness, cancellation/syndication, licensing and network failures. `tests/unit/test_zaad_risk_integration.py` exercises the signal-to-route-to-scenario/action path with deliberately synthetic controls: future/stale/irrelevant/licensing-rejected/reconstructed/news-only signals do not shift the physical model; relevant physical signals do; domain coupling appears in actual arrays; blocked alternatives never get orders.

Those tests verify implementation behavior, not that the assumed transformation is correct for an operator. Before offering calibrated disruption probabilities, collect permissioned prospective vintages, operational delays and non-events, fit on training-only data, measure warning lead time/precision/recall and calibration, and compare policy value against strong baselines on independently observed outcomes. No traffic index, news count or vendor confidence should be relabeled as an empirical probability in the meantime.

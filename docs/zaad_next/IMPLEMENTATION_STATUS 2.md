# ZAAD implementation status and scope closure

Updated after the frozen final sweep. **NEEDS FURTHER ENGINEERING**: a coherent runnable prototype is delivered; the full enterprise specification is not complete. The evidence contains 3,000 runs, 24 gated cost losses and 122 service breaches. No real operator validation or automatic PO write-back exists.

Status: **I** implemented/tested bounded capability; **P** partial or unproved acceptance; **D** documented research/design; **X** deliberately deferred. I does not mean production validated.

## All 53 phases

| Phase | Status | Delivered / remaining |
|---:|---|---|
| 1 | I/P | CURRENT_STATE_AUDIT + exact same-scenario legacy withholding reproduction; legacy production adapter defects isolated, not broadly repaired |
| 2 | I/D | COMPETITIVE_BASELINE: sourced useful Oracle/vendor subset, strategic vs execution separated; no parity claim |
| 3 | I/P | Source audit + external_data_sources.yaml; actual NOAA fetch; paid vendors/uncertain rights remain disabled |
| 4 | I/P | Directed nodes/edges/itineraries, volume capacity, shared failure domains; supplied shortlist, not global route enumeration |
| 5 | I/P | Strict dated SKU/location/lot/history/PO snapshot and CSV round-trip; full movements, revisions reconciliation and payment ledger deferred |
| 6 | I/P | Chronological moving average/EWMA/Croston-SBA/TSB/seasonal-naive scoring; existing boosting retained, hierarchy/ETS not newly benchmarked |
| 7 | P | Ordered→confirmed→received→accepted, empirical joint fill/lead, thin-data refusal; censored open-PO survival and calibrated ETA absent |
| 8 | I/P | Common work-conserving inventory/cost simulation and service-filtered finite-policy search; not global inventory optimization |
| 9 | I/P | Strict structured signal/event contract + provenance/dedup; no LLM extraction or article ingestion deployed |
| 10 | I/P | Actual NOAA official alerts and generic physical records; no live AIS/dwell/FBX integration |
| 11 | D/P | Method comparison; no learned/calibrated route-risk posterior; explicit stress assumptions only |
| 12 | I/P | Exact route/entity relevance and causal freshness fusion; statistical cross-feed calibration not established |
| 13 | P | Quantity, buffer, approved-source split/spill; transfers/substitution/cancellation/de-expediting deferred |
| 14 | I/P | Quote/capacity/itinerary/compliance hard gates, route cards; actual carrier bookings/manual review still required |
| 15 | I/P | Expected/CVaR/mean-path finite-policy comparison, rolling stock/pipeline decisions; no continuous global SP/DRO/RL or per-week method refit |
| 16 | I/P | Costs and sampled tail/worst-regret controls; real economic risk calibration unproved |
| 17 | I/P | Per-SKU targets, priority, margin/criticality, segment; channel/customer-service integration absent |
| 18 | P | Standalone contractual-minimum/priority/pro-rata-tie helper tested; not integrated order-line OTIF allocation |
| 19 | I/P | Fresh recovery required, pipeline retained, inventory run-down controls +480 trace rows; no cancel/rebook or validated glidepath |
| 20 | I/P | Snapshot→frontier→confirmation→review/abstain; human approval required, persistent operational state/approvals not built |
| 21 | I | Eight baseline/controller rows per cell, all on one settlement; finite-search methods labeled honestly |
| 22 | I/P | Paired simulated confirmation, hard bounds and force-unit control; final service failures prove no real no-harm guarantee |
| 23 | I/P | 40 target×stock factorial +15 OFAT cases; not exhaustive all-SKU/all-factor operator-scale validation |
| 24 | I/P | Twelve disruption/control cells, five seeds; topology limited, some full requested disruption types remain unmodeled |
| 25 | I/P | News-only false alarm equals matching no-signal outcome; physical-feed false-positive predictive value not measured |
| 26 | I/P | Future-news exclusion and late-news-after-physical case; no incremental news decision effect or measured lead advantage |
| 27 | P | Seven synthetic signal-contract ablations; port/AIS/freight/weather labels share a mapping, NOT provider-specific evaluation |
| 28 | P | Genuine Baltimore official metadata, rejected for unverified historical vintage; no causal historical-event backtest completed |
| 29 | I/P | Actual193 NWS records replayed against synthetic network; unmatched routes unchanged; not historical shipment/ROI validation |
| 30 | I/P | Observed/published/ingested/effective/expiry, source IDs, adapter and input fingerprint; source-unit mapping remains operator responsibility |
| 31 | I/P | Real report carries reasons, alternatives, costs/service/capital evidence, limits; concise narrative explanations can improve |
| 32 | I/P | Route cost/path/lead/fill/capacity/exposure/rights/expiry/rejection evidence; no calibrated on-time probability |
| 33 | I/P | Separate inventory release, recurring carry, temporary buffer and modeled tail benefit; real CFO/AP reconciliation pending |
| 34 | I/P | Seven-view Next.js /zaad page, JSON import and what-ifs, actual API browser smoke; narrow-layout polish remains |
| 35 | I/P | Swappable validated signal boundary + bounded NWS adapter; paid provider interfaces documented but not complete SDK adapters |
| 36 | P | Immutable normalized SignalStore + non-overwriting demo artifacts; full raw append-only production lake/rebuild scheduler absent |
| 37 | I/P | Expiry/freshness/syndication regression controls; half-lives assumed, operational calibration absent |
| 38 | I/P | Allowlisted no-redirect bounded fetch;2MiB API cap, tenant match, mandatory rate/compute caps; distributed quotas/TLS deployment pending |
| 39 | I | Instruction/tool fields rejected; external text has no execution pathway; no LLM extraction introduced |
| 40 | I/P | Source-by-source license audit and runtime rights eligibility; operator clearance not automated legal certification |
| 41 | P | Overstock/understock/recovery order behavior tested; final normal improvements modest, stress acceptance fails in some cases |
| 42 | P | False alarm/recovery mechanisms tested; severe disruption service failures prevent full resilience acceptance |
| 43 | I/P | Competent fill-aware incumbent/base-stock, shared constraints; no vendor proprietary benchmark |
| 44 | I/P | Forecast chronological scores and policy mean/tail comparisons; broad model superiority not established |
| 45 | I | Frozen source/config, every row retained, true median, no hidden fallback wins |
| 46 | I | Five untouched final seeds generated after selection, frozen source hash retained; no post-holdout policy retuning |
| 47 | I/P | All646 baseline cost-loss rows decomposed;24 gated losses grouped; causal attribution beyond accounting still requires controlled experiments |
| 48 | I/P | 1,473 Python tests passed,1 skipped;80 new tests; changed-code Ruff, CI-equivalent mypy103files, TS/build + actual browser/API smoke; nine imported legacy typing errors corrected without algorithm changes |
| 49 | I/D | Competitive baseline and pilot docs tie pain→decision→method/data→value |
| 50 | D/P | Stock-owning distributor ICP hypothesis and explicit disqualifiers; no customer proof or assumed MENA shortcut |
| 51 | D/P | Read-only→replay→shadow→limited-approved plan; no customer agreement/enrollment/live actions |
| 52 | P/X | Reviewable timestamped artifacts; no persistent prospective override/outcome/approval workflow |
| 53 | I/P | Required documentation, results, failures and reproducible branch; draft PR handoff, no merge or deploy |

## Definition of done A–Q

| Letter | Bounded closure / gap |
|---|---|
| A | Canonical JSON and CSV intake tested, no training DB writes |
| B | Normal recommendations run; real-value/service acceptance not established |
| C | Actual public NWS fetch193 records with provenance; historical Baltimore metadata cannot be used as causal vintage |
| D | Exact entity/domain→route mapping tested |
| E | Only relevant eligible evidence changes route stress; assumptions uncalibrated |
| F | Hard approved-source/path/capacity/expiry feasibility tested |
| G | Paired cost/protection comparison implemented; no real savings claim |
| H | News-only negative control identical to normal; broader physical false-positive acceptance partial |
| I | Risk-aware decisions can lower synthetic cost; severe service acceptance fails |
| J | Explicit recovery and no-duplicate pipeline tested, exact trace replay; cancellation absent |
| K | Fill-aware competent incumbent and tuned simple baselines share physics |
| L | Thin data, impossible modeled service, unavailable recovery evidence and unit-fill control abstain |
| M | Actual UI/API report includes provenance and limitations |
| N |80 new tests, full Python suite1473pass/1skip; JS/API checks |
| O | Every run and646 losing-row decompositions retained |
| P | Frozen source/config hash, exact commands, original dirty checkout untouched |
| Q | Separate branch/draft PR, no main merge; final PR URL in task handoff |

## Mandatory regression mapping

| Control | Concrete evidence |
|---|---|
|1 Pipeline prevents duplication | test_pipeline_expected_acceptance_is_not_haircut_twice; test_emitted_first_action_equals_simulated_first_action_with_due_now_po |
|2–3 Future port/news | test_unusable_or_news_only_evidence_cannot_shift_supply_or_orders; signal-store clock controls |
|4 Syndication | test_syndication_does_not_multiply_news_confirmation_or_hazard |
|5 Staleness | signal expiry/decay and stale integration control |
|6 Irrelevant port | irrelevant integration control |
|7–8 Overstock/understock | test_overstock_does_not_order_while_understock_orders_more; final matrix with failures |
|9 Balanced retain incumbent | KEEP_INCUMBENT paths observed and paired-gate tests; not every balanced case must retain an inefficient incumbent |
|10–11 Disruption/recovery | test_disruption_changes_feasible_protection_rule_and_recovery_unwinds; missing evidence abstains |
|12 False alarm | test_news_alone_never_creates_panic_inventory; no-signal matching frozen results |
|13 Shared exposure | test_shared_failure_domain_couples_actual_draws_not_just_route_labels |
|14 Alternative capacity | route/edge/budget/pack tests; item volume conversion test |
|15–16 Illegal/unavailable | test_blocked_unapproved_expired_and_unavailable_routes_never_ordered |
|17 Relaxation | test_no_relaxed_constraint_field_can_enter_request; no relaxation pathway in finite search |
|18 Thin data | actual-engine API abstention test; contract/history checks |
|19 Prompt injection | test_news_instruction_payload_is_rejected_at_api_contract_boundary |
|20 Provider/API failure | immutable batch, timeout/429/malformed tests; no optimizer state writes |
|21 Timestamps | strict aware clocks/provenance tests and actual captured NWS records |
|22 Reproduction | deterministic path/settlement test; frozen hash and exact trace-cost matches |

## Release decision and priorities

Do not deploy procurement recommendations. Next: strengthen nonstationary demand and pending-PO ETA, test an out-of-model service gate, reconcile real unit/cash/quote semantics, and implement a durable shadow ledger. Use new preregistered seeds/data afterward; the current holdout is consumed. Paid keys and archival vintages are explicit external dependencies, not permission to fabricate data.

# HARDENING V1, H2: opening inventory as a proven physical state

Branch `hardening/h2-inventory-state-contract` on main `56c3535` (H0, H1a, H1c, H1b merged). One purpose:
opening inventory is a reconstructable, explicitly proven physical state, never "the last row we happen
to have". Nothing below is operator validation: every vault is the SYNTHETIC sample or a crafted row.

## Defects reproduced on main before the change (sample `A_stable` seed 7, planning at 2026-09-07)

| case | rows | main planned from | after H2 |
|---|---|---|---|
| A asynchronous cells | SKU-0001 = 100 on 09-06, SKU-0002 = 200 on 09-05 | `{SKU-0001: 100}` only: one global latest day dropped SKU-0002 | per-cell: SKU-0002 is `NOT_READY_INCOMPLETE_MOVEMENTS`, the request is blocked and says so |
| B two locations, one date | DC = 100, BRANCH = 40 | `{SKU-0001@main: 40}`: one arbitrary row | `NOT_READY_LOCATION_AMBIGUITY`; with the explicit `inventory_single_site_aggregation = SUM` declaration: 140 |
| C repeated rows for one cohort | 100 and 70, or 100 and 100, same cell / instant / expiry | 70 in one physical order, 100 in the other (fingerprints differ) | `NOT_READY_AMBIGUOUS` in either order, equal quantities included: without a `lot_id` one record repeated and two real lots cannot be told apart; distinct `lot_id`s are two lots, a repeated `lot_id` blocks |
| D no row for the planned SKU | none | stock `{}` with a warning: unknown became zero | `NOT_READY_NO_SNAPSHOT`, blocked |
| E 30-day-old count, 300 received since | 500 on 08-08 | 500 unchanged, a warning only | `NOT_READY_INCOMPLETE_MOVEMENTS`: no adjustments / returns / shrink / cycle-count feed, roll-forward not provable |
| explicit zero | 0 on 09-06 | indistinguishable from "no row" | `READY_DIRECT`, quantity 0, no Stock row, counted in `zero_cells` |
| date-only, no basis | 100 on 09-06 | planned as if a known instant | `NOT_READY_AMBIGUOUS_TIMING` until a row or workspace basis is declared |
| expiry cohorts | 60 exp 09-20, 40 exp 10-11 | one row survived `drop_duplicates` | two Stock rows `open_SKU-0001#2026-09-20` / `#2026-10-11` |
| late-known count | `source_known_at` 09-08 09:00 | used | excluded (`rows_excluded_not_known` = 1), `NOT_READY_NO_SNAPSHOT` |
| no knowledge time | row without `source_known_at`, no declared rule | planned | `NOT_READY_KNOWLEDGE_TIME_UNAVAILABLE`; `imported_at` changes nothing |
| boundary | `source_known_at` = T − 1 s / T / T + 1 s | all used | available / unavailable / unavailable (strict `<`) |
| partial state knowledge | cohorts 60 (known 08:00) + 40 (known at T) of one snapshot | 60 planned | `NOT_READY_INCOMPLETE_STATE_KNOWLEDGE`: 2 rows define the state, 1 knowable; no request from the subset |
| late-known location | DC known, BRANCH known at T, same snapshot | planned as single-site DC | `NOT_READY_LOCATION_AMBIGUITY` (BRANCH does not vanish); under SUM, BRANCH blocks |
| repeated `lot_id` | L1 twice: same / different expiry, quantity, knowledge time, null expiry | n/a | `NOT_READY_AMBIGUOUS` in every case and either order; L1 + L2 with equal expiry and quantity are two lots |
| `in_transit` 999 | on the snapshot | ignored silently | reported as `in_transit_declared`; stock, pipeline and fingerprint unchanged |

## The contract (`zaad/full/inventory_state.py`, migration 030)

- Cell = `(sku, location)`; cohorts = rows of one instant with distinct `expiry_date`.
- `effective_at`: `snapshot_at` (POINT_IN_TIME) > date + `snapshot_basis` END_OF_DAY (date + 1 day 00:00)
  or START_OF_DAY (date 00:00) > workspace `inventory_snapshot_basis` > AMBIGUOUS (never guessed).
- Knowledge (H1b, unchanged for inventory): `source_known_at < decision_at`, strict. A row without a
  knowledge time is not available (`NOT_READY_KNOWLEDGE_TIME_UNAVAILABLE`): not its effective instant, not
  its date, never import time or "decision minus a second". The only other admissible knowledge time is the
  explicit workspace declaration `inventory_source_known_rule = CLOSE_OF_SNAPSHOT_DAY` (known at the
  snapshot day's last second), recorded per cell as `knowledge_basis = DECLARED_RULE:…`. The physical basis
  (START_OF_DAY / END_OF_DAY / snapshot_at) never stands in for knowledge.
- Cohorts carry their own `source_known_at`; each `Stock.known_at` is its cohort's. A declared SUM of
  locations is known when all components are (max). Every fact-derived Stock satisfies `known_at < as_of`.
- State completeness: the physical state is selected first (the cell's latest instant at or before T,
  knowledge aside); it is READY only if every row defining it is known before T. A knowable subset is
  `NOT_READY_INCOMPLETE_STATE_KNOWLEDGE` and its quantities never reach the Request; the report's
  `state_knowledge` gives rows defining the state / known before the decision / excluded by the causal
  cutoff / without a knowledge time. State strictly after T is not history and creates no requirement.
- Single-site location discovery uses physical relevance (state at or before T), not causal availability,
  so a location whose count was not knowable blocks instead of disappearing.
- Lots: rows for one `(sku, location, effective_at, expiry_date)` without a `lot_id` block as ambiguous
  whatever their quantities (never chosen, deduplicated, summed, or told apart by rowid / upload metadata);
  optional `lot_id` (migration 030) is an identity: within one cell and physical state it names exactly one
  row, validated before cohorts are built; a repeated `lot_id` blocks whatever else differs.
- READY_DIRECT only when `effective_at == decision_at` (PERIOD_BOUNDARY, H1b). An earlier count is
  NOT_READY_INCOMPLETE_MOVEMENTS: the data contract has no adjustments / returns / shrink / cycle-count
  feed and no completeness declaration, so roll-forward is not performed (`roll_forward_performed: false`).
- Single-site build: one real location (or none) maps to `main`; several block unless
  `inventory_single_site_aggregation = SUM` is declared, and then every location must be READY.
- A NOT READY planned cell raises `WorkspaceError` naming the SKU, location, status and reason.
- Build report section `inventory_state`: per-cell `snapshot_effective_at`, `source_known_at`, `basis`,
  `quantity_at_snapshot`, `quantity_at_origin`, `roll_forward`, `age_days`, `in_transit_declared`;
  `movement_coverage`; the 14-day rule is `age_note` metadata, not a decision.

## Synthetic semantics, proven and declared

`synthetic/fmcg/distributor_sim.py` appends each week's `on_hand` after that week's arrivals,
fulfilment and replenishment and labels it with the week start (sample SKU-0001: row labelled 2025-12-22
holds 2965 while 1969 units were received on 2025-12-22). `closing_inventory_rows` now writes
`snapshot_date` = week start + 6 days, `snapshot_basis` = END_OF_DAY, `snapshot_at` = next Monday 00:00,
and `source_known_at` = Sunday 23:59:59 (SYNTHETIC convention `SYNTHETIC_COUNT_KNOWN_AT_CLOSE_OF_WEEK`: the
simulator's week is a discrete state machine whose state is final once the replenishment decision is
recorded, and the count is posted at the last second of the closing day, strictly before the Monday
decision). The loader also declares `inventory_snapshot_basis = END_OF_DAY` and
`inventory_source_known_rule = CLOSE_OF_SNAPSHOT_DAY` (provenance SYNTHETIC) for vaults without migration
030. `demo_company` (Sunday counts, 3 sites) writes the same per-row knowledge time and declares END_OF_DAY,
the rule and SUM; the network smoke split carries the sample's timing columns and declares SUM because its
three sites are shares of one count. None of this is a fallback for operator data.

## Known origin 2025-09-01 (`E_mixed_portfolio` seed 7)

| cell | status | effective_at | source_known_at | knowledge basis | physical basis | quantity |
|---|---|---|---|---|---|---|
| SKU-0009@main | READY_DIRECT | 2025-09-01T00:00 | 2025-08-31T23:59:59 | EXPLICIT_SOURCE_KNOWN | POINT_IN_TIME | 5454 |
| SKU-0030@main | READY_DIRECT | 2025-09-01T00:00 | 2025-08-31T23:59:59 | EXPLICIT_SOURCE_KNOWN | POINT_IN_TIME | 2208 |
| SKU-0143@main | READY_DIRECT | 2025-09-01T00:00 | 2025-08-31T23:59:59 | EXPLICIT_SOURCE_KNOWN | POINT_IN_TIME | 204 |

The quantities are unchanged because the synthetic knowledge time is declared explicitly one second before
the decision, not because the inequality was relaxed; every `Stock.known_at < Request.as_of`.

Open inbound unchanged from H1a: 3000 / 3888 / 72 (`test_workspace_known_origin_2025_09_01` passes).

## Not done, by design

- No roll-forward, no adjustments ledger, no partial-receipt or same-day-tie contract (deferred items stand).
- `api/product/readiness.py` INVENTORY_VALUE still measures `on_hand` column coverage for the valuation
  diagnostic; planning readiness is the build report's `inventory_state` section.
- The historical replay builds one request (review 0) from the vault; later reviews open on the settled
  state of the previous review, so the attestation is that review-0 section plus a completed replay.

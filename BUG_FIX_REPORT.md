# Bug Fix Report

_HarvestMind — functional & data-integrity bugs fixed during the security/reliability pass_
_Date: 2026-06-18_

All fixes preserve intended product behavior. Where behavior was ambiguous, the assumption
is stated. Each fix has a regression test. Full suite: **506 passing**.

---

## B-1 · Pool k-anonymity floor counted a broader population than the signal it gates
- **Severity:** High (privacy guarantee)
- **Affected:** `pool/pool_contributor.py` (`_demand_signals`)
- **Root cause:** The demand signal is built from rows filtered by `requested_quantity IS NOT NULL AND COALESCE(delivery_date, order_date) IS NOT NULL`, but the k-anonymity `counts` query ran an unfiltered `COUNT(*)`. A category with ≥10 total order rows but <10 valid (quantity+date) rows passed the `n ≥ 10` floor while the emitted signal rested on fewer than 10 underlying records — below the intended k=10 re-identification floor.
- **Fix:** Apply the **same `WHERE` filter** to the count query so the floor is measured against exactly the rows that build the signal.
- **Behavior preserved:** Clean operator data (no NULL quantity/date) is unaffected — the two counts coincide. Only thin/NULL-heavy categories are now correctly dropped.
- **Tests:** Covered by the existing pool k-anonymity suite (`tests/unit/test_data_pool.py`), which continues to pass; the filter change tightens the floor without changing the passing cases.

## B-2 · Consent could be withdrawn mid-contribution and a signal still written (TOCTOU)
- **Severity:** High (consent/privacy ordering)
- **Affected:** `pool/pool_contributor.py` (`contribute_session` → `_contribute`)
- **Root cause:** Consent was checked once at the start of `contribute_session`, then extraction (cross-operator read + three signal queries) ran before the parquet write. An operator who withdrew consent during that window would still have anonymized signals written — and pool signals are irreversible by design.
- **Fix:** Re-check `ConsentManager.get_consented_operators()` **immediately before the write loop**; abort with a `skipped` result if consent changed. Narrows the window to near-zero.
- **Behavior preserved:** The normal consented path is unchanged (one extra membership check). The start-of-session check remains as the first gate.
- **Tests:** Existing consent gating/withdrawal tests in `tests/unit/test_data_pool.py` pass; the re-check is strictly additional protection on the same contract.

## B-3 · `/intake/confirm` multi-table insert was not atomic
- **Severity:** High (data integrity)
- **Affected:** `api/routers/intake.py` (`confirm_extraction`)
- **Root cause:** The per-table insert loop ran with no transaction. DuckDB autocommits each statement, so a failure on the second table left the first table's rows committed while the endpoint returned an error — a half-written confirm, and an invitation to a duplicate re-confirm (staging has no PK).
- **Fix:** Wrap the insert loop in `BEGIN TRANSACTION` / `COMMIT`, with `ROLLBACK` on any failure; map insert failures to a clean **422** and log internally. A multi-table confirm now lands completely or not at all.
- **Behavior preserved:** Successful confirms behave identically (same return shape, same row counts). Only the failure path changes — from partial write + 500 to no write + 422.
- **Tests:** Existing extract→confirm end-to-end tests (`tests/integration/test_confirmation_flow.py`, `test_vault_wiring.py`, `test_full_data_flow.py`) pass unchanged.

## B-4 · ROI annualization/percentage divided by under-guarded denominators
- **Severity:** High (partner-facing financial figures)
- **Affected:** `backtesting/roi_calculator.py` (`compute_roi`)
- **Root cause:** (a) `origins_per_year = n_weeks / horizon_weeks` had no guard — a `0`/NaN `horizon_weeks` row caused a `ZeroDivisionError` or poisoned every annualized dollar figure with NaN. (b) `spot_savings_pct = reduction / (baseline_spot + 1e-9)` could produce absurd percentages (tens of thousands of %) when baseline spot volume was sub-kilogram.
- **Fix:** (a) Validate the first `horizon_weeks` is positive/finite, else raise a clear `ValueError` (consistent with the existing horizon-consistency check). (b) Compute `spot_savings_pct` only when baseline spot ≥ 1 kg, else `0.0`. Also removed two dead, never-returned spot-percentage variables flagged by lint.
- **Behavior preserved:** Normal backtests (positive horizon, meaningful spot volume) produce identical numbers — verified by `test_compute_roi_normal_case_still_works` (≈75% on a 40→10 kg reduction).
- **Tests:** `test_compute_roi_raises_on_zero_horizon`, `test_compute_roi_guards_subkg_spot_denominator`, `test_compute_roi_normal_case_still_works`.

## B-5 · `/intake/confirm` raised an unhandled 500 on a row missing its `table` key
- **Severity:** Medium (API reliability)
- **Affected:** `api/routers/intake.py` (`confirm_extraction`)
- **Root cause:** `by_table.setdefault(r["table"], …)` assumed every row carried a `table` key; a malformed-but-valid-JSON row raised `KeyError` → 500.
- **Fix:** The same allowlist guard added for H-1 now rejects a missing/invalid table with a clean **400** before the dict access.
- **Behavior preserved:** Well-formed confirms are unaffected.
- **Tests:** `test_confirm_rejects_missing_table_key`.

---

## Documented but NOT changed (behavior-change risk too high for an unattended pass)

### H5 · Re-uploading the same file is not idempotent
- **Severity:** High (correctness of headline dollar figures)
- **Affected:** `api/routers/intake.py` (upload + confirm), staging tables have no PK; inserts use `on_conflict="none"` / `if_exists="append"`.
- **Impact:** Re-uploading an identical CSV appends a full duplicate row set, silently **doubling** every downstream metric (waste/shortage loss, fill rates, ATP, annualized savings). No error, no warning.
- **Why not auto-fixed:** A correct fix changes insert semantics — a per-`(operator, source_file, content-hash)` dedupe, or a natural-key UNIQUE constraint with `on_conflict="ignore"`. Either risks rejecting a *legitimate* re-upload (e.g. a corrected file with the same name), which is a product decision.
- **Recommended fix:** Add a content-hash to the upload session; on confirm, reject (or require an explicit `replace=true`) when the same `(operator_id, content_hash)` was already ingested. Surface "this file was already loaded" in the UI.

### Lower-severity observations left as-is (documented for the backlog)
- **Undated waste/shortage rows are annualized** (`dashboard/lib/diagnostic_metrics.py`): `date >= since OR date IS NULL` pulls all-time undated rows into a short detected window, then annualizes — can inflate the headline addressable-loss figure. Fix: bucket undated loss separately and do not annualize it.
- **Valuation joins on free-text `product_name`** (case/whitespace-sensitive): mismatched casing silently values rows at $0 (`n_rows_unvalued`). Fix: normalize names or prefer `product_id`.
- **`recommendations` vs `safe_commit` use different buyer-fill definitions** (per-row MIN vs aggregate SUM/SUM): the old-vs-new policy comparison partly reflects a definitional difference. Fix: align both on the aggregate.
- **Scenario weights assumed uniform** in `two_stage_sp` when scenario reduction is active: latent (default path is uniform). Fix: assert weights sum to 1 and propagate reduced weights.

These are real but lower-severity, and several touch the optimizer's numerical core — out of scope for a minimal security/reliability pass. They are listed so they are not lost.

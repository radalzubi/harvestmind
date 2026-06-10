# Data Infrastructure

_The complete reference for HarvestMind's three-layer data architecture._
_Code: `infrastructure/`, `pool/`, `training/`. Everything under
`data/operators/`, `data/registry/`, `pool/`, and the model checkpoint
directories is gitignored — operator data never reaches the repo._

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│ COMPANY VAULTS (private, isolated)        data/operators/<op_id>/    │
│   harvestmind.db   their staging + results (all migrations applied)  │
│   uploads/         raw originals, WRITE-ONCE (audit ground truth)    │
│   sessions/        confirmed LLM-extraction snapshots                │
│   exports/         reports, confirmed CSVs                           │
│   consent.json     their pool consent record, with full history      │
│                       data/registry/operators.json  (metadata)       │
└───────────────┬─────────────────────────────────────────────────────┘
                │  ONE sanctioned crossing: DBManager.get_cross_operator
                │  _connection — read-only, purpose-logged, used only by
                ▼  the pool contributor. Consent checked first.
┌─────────────────────────────────────────────────────────────────────┐
│ DATA POOL (anonymized, aggregate)                          pool/     │
│   signals/demand_patterns/      category CV + trend, volume = 1.0    │
│   signals/yield_distributions/  category+region fill-rate ratios     │
│   signals/waste_profiles/       category waste rates, bucketed why   │
│   contributions/contribution_log.jsonl  (ids + counts, never content)│
│   K-ANONYMITY FLOOR: signals on <10 underlying rows are dropped      │
└───────────────┬─────────────────────────────────────────────────────┘
                │  PoolReader → population-level priors only
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ MODEL TRAINING (validation-gated)                       training/    │
│   demand: pool trend/CV bootstraps thin-history operators            │
│   yield:  pool Beta prior = 3rd level of the hierarchy               │
│   extraction: gold-label corpus, fine-tune gated at 50 sessions      │
│   retraining_scheduler: thresholds + gates + retraining_log.jsonl    │
│   forecaster_checkpoints/, extraction_checkpoints/ (versioned,       │
│   rollback one call away)                                            │
└─────────────────────────────────────────────────────────────────────┘
```

## The three layers

**Vaults.** Every operator's data lives in their own directory with
their own DuckDB. No shared tables, no tenant column filtering — the
isolation is physical. All access goes through
`infrastructure/db_manager.py`; nothing else opens a vault file. The
only multi-operator path is `get_cross_operator_connection`, which is
read-only, requires explicitly named operators and a stated purpose,
logs every call, and exists solely for pool contribution. The
diagnostic and the optimizer never touch it. The legacy root database
remains as the single-operator dev mode (no `operator_id` on a request).

**Pool.** After each confirmed session of a *consenting* operator, the
contributor extracts category-level statistical signals — never rows —
and appends them as parquet (one file per contribution; a partial write
cannot corrupt history). Anonymization happens at extraction, before
anything leaves the vault path. The k-anonymity floor (n ≥ 10 underlying
rows per signal) exists because small samples identify businesses: "the
one operator with three saffron deliveries" is not anonymous no matter
how the fields are scrubbed.

**Training.** Pool priors make models smarter exactly where individual
operators are weakest: a new operator's demand forecast leans on the
cross-operator trend consensus until their own history accumulates
(weight shifts automatically); their supplier-yield population shrinks
toward the pooled Beta prior instead of being estimated from a
population of one. Every retrain — scheduled or manual — passes a
validation gate: the refit deploys only if it beats the incumbent on
held-out data. Every attempt is logged.

## How to create an operator

```python
from infrastructure.operator_registry import OperatorRegistry

registry = OperatorRegistry()
op = registry.create_operator(
    "Hoosier Harvest Market",
    pool_consent=True,          # only after they've read POOL_PRIVACY.md
    region="midwest",
)
# op.operator_id → "op_3fa9c2d1"; vault + migrated DB + consent.json exist
```

Uploads then carry the id: `POST /intake/upload/stg_buyer_orders?operator_id=op_3fa9c2d1`
(or the smart-upload path: `POST /intake/extract?operator_id=...`).

## Lineage: tracing a number to its source

Every row inserted on the operator path carries four columns:
`_operator_id`, `_upload_session_id`, `_source_file`, `_uploaded_at` —
rows without them are rejected (`infrastructure/lineage.py`). To trace:

```python
from infrastructure.lineage import trace_row
trace_row(conn, "stg_buyer_orders", "product_name = 'Roma Tomatoes'")
# → [{_operator_id, _upload_session_id, _source_file, _uploaded_at, n_rows}]
```

`_source_file` names the immutable copy in `uploads/`;
`_upload_session_id` keys the extraction session in `sessions/` and the
audit log — so any diagnostic figure walks back to the exact bytes the
operator uploaded and the exact confirmation they gave.

## Consent, withdrawal, deletion

- Consent is recorded in two synchronized stores (vault `consent.json`
  with full event history + the registry); `ConsentManager` is the only
  writer of either.
- Contribution checks consent at run time — a non-consenting operator is
  skipped and the skip is logged.
- Withdrawal stops future contributions immediately. Signals already in
  the pool are not reversible to the operator and remain — operators are
  told this **before** consenting (POOL_PRIVACY.md), not after.
- Deletion marks the operator deleted, kills consent, and keeps vault
  files (retention is an explicit operational decision, never a silent
  code path).

## What enters the pool / what never does

| In | Never |
|---|---|
| product **category** | product, supplier, buyer, company names |
| demand CV, trend direction | actual volumes (means normalized to 1.0) |
| fill-rate mean/std (ratios) | prices or costs |
| waste **rate** + bucketed reason | free-text reasons |
| operator-level region | anything below region level |
| `operator_id` (audit only, never exposed by the reader) | |

The anonymization test (`tests/unit/test_data_pool.py`) scans the actual
parquet payloads for every name present in the source data; a leak fails
the build.

# Data handling: what the engine keeps, and how the data bank stays anonymous

**Principle.** The optimizer needs quantities, dates, prices and *joins*. It never needs to know which supplier is "Acme" or which customer is "Alice". So identities are hashed before storage and names are never stored at all.

## What happens to an upload

1. **Anonymisation** (`ingestion/anonymize.py`). Every identifier column (`sku`, `supplier_id`, `customer_id`, `po_id`, `order_id`, `lot_id`, anything ending in `_id`) is replaced by a keyed hash: HMAC-SHA256 with a per-operator secret, truncated to 16 hex characters. The same secret gives the same hash in every table, so a PO still joins to its receipts. Name columns that act as keys (`product_name`, `supplier_name`, `customer_name`, `buyer_name`) are hashed like ids, so a join on them still works and the name itself is never stored. Free-text columns (`description`, `contact`, `email`, `phone`, `address`, `notes`, and so on) are dropped, not hashed. Quantities, prices, dates and pack sizes are untouched.
   - Server side: `POST /intake/upload/{table}?anonymize=true` (the default for operator-scoped uploads) applies this before the file reaches the vault. The secret lives in the operator registry (`data/operators/registry.json`, git-ignored, file permissions 600), never in DuckDB and never in a response.
   - Client side, recommended for pilots: `python scripts/anonymize_export.py --secret "<passphrase>" *.csv` on the operator's own machine. Real codes never leave their building; they keep the passphrase and can resolve hashed ids in our reports locally. `looks_anonymized()` lets the server refuse a raw file when anonymisation is required.
2. **Vault.** The (anonymised) original is written once, content-hashed (`upload_hashes/`), and cannot be overwritten; duplicates are refused unless `force=true`.
3. **Isolation.** One DuckDB per operator (`infrastructure/db_manager.py`); tokens are stored as SHA-256 hashes; auth fails closed outside development; the API refuses to bind a non-loopback address without an admin key.
4. **Audit trail.** `optimization/audit_trail.py` records input *hashes*, configuration and results, never raw rows. Run sidecars under `data/runs/` are git-ignored.
5. **Pooling.** Cross-operator pooling (`api/routers/pool.py`) uses only consented, anonymised operators; consent is a per-operator flag in the registry.

## What is never committed to the repository

`data/operators/`, `data/raw/`, `data/processed/`, `data/partner/`, `data/runs/`, model artifacts, extraction logs and training corpora are all in `.gitignore`. Public series under `data/external/` are the only data committed, and each is classified in `data/external/README.md`.

## What an operator can ask for

- The list of columns hashed and dropped (returned with every upload as `anonymization`).
- Deletion: `POST /intake/clear/{table}` per table, or removal of the operator's vault directory and registry record on request.
- Their secret is theirs; we cannot reverse a hash without it and do not store it anywhere but the registry file for server-side mode (client-side mode: we never see it).

## Known limits, stated plainly

- Hashing is pseudonymisation, not full anonymisation: a party holding both the secret and the hashes can re-identify. That party is the operator.
- Quantities and dates are a fingerprint of a business even without names. The vault, per-operator isolation and no-pooling-without-consent are the controls for that; there is no technical control that makes a full purchase history unrecognisable to someone who already knows it.
- Free-text columns are matched by name; an unusual column name carrying a name or address would pass through. The upload response lists every untouched column so this is visible.

-- 023: the operating product (draft purchase orders, proposal evaluations, export profiles).
--
-- Additive, nullable, idempotent. Nothing here touches the optimizer or any staging table's
-- existing columns: an existing vault keeps every row it has and plans exactly as before.
--
-- Three rules this schema exists to keep:
--
--   1. Imported source data is evidence. A change to an imported purchase order is stored here as a
--      *proposal against* it (`source_po_id` + `amendment_action`), never as an edit of
--      `stg_fmcg_purchase_orders`. The original row is never rewritten or deleted by the product.
--   2. Every object is owned by one operator. These tables live inside the operator's own vault,
--      and `operator_id` is carried and filtered on anyway so a mis-mounted connection cannot leak.
--   3. Nothing here executes. A draft order is a document ZAAD can evaluate, a person can approve,
--      and the workspace can export. It is never transmitted to a supplier or an ERP.

-- One proposed order. Four provenances produce the same object (§16 of the product brief):
-- ZAAD_RECOMMENDATION, CURRENT_POLICY, MANUAL, UPLOADED_PROPOSAL — plus IMPORTED_AMENDMENT, which
-- is a proposal against an order that already exists in the vault.
CREATE TABLE IF NOT EXISTS zaad_draft_orders (
    draft_id                VARCHAR NOT NULL,
    operator_id             VARCHAR NOT NULL,
    origin                  VARCHAR NOT NULL,   -- ZAAD_RECOMMENDATION | CURRENT_POLICY | MANUAL | UPLOADED_PROPOSAL | IMPORTED_AMENDMENT
    state                   VARCHAR NOT NULL,   -- DRAFT | READY_FOR_REVIEW | APPROVED | REJECTED | EXPORTED | SUPERSEDED
    revision                INTEGER NOT NULL DEFAULT 1,
    reference               VARCHAR,            -- the operator's own PO number when they have one
    supplier_id             VARCHAR,
    destination_id          VARCHAR,
    currency                VARCHAR,
    requested_order_date    DATE,
    requested_receipt_date  DATE,
    notes                   VARCHAR,
    source_decision_id      VARCHAR,            -- the decision this was created from
    source_po_id            VARCHAR,            -- the imported open order this amends
    amendment_action        VARCHAR,            -- KEEP | DEFER | EXPEDITE | REDUCE | CANCEL | SPLIT (amendments only)
    evaluation_id           VARCHAR,            -- the most recent evaluation of this revision
    created_by              VARCHAR,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_by             VARCHAR,
    approved_at             TIMESTAMP,
    decision_reason         VARCHAR,            -- why it was approved or rejected
    superseded_by           VARCHAR,
    supersedes              VARCHAR             -- the approved or exported revision this one replaces
);
COMMENT ON TABLE zaad_draft_orders IS 'Proposed purchase orders and proposed amendments. Never transmitted; approval and export are the last mile.';

CREATE TABLE IF NOT EXISTS zaad_draft_lines (
    draft_id                VARCHAR NOT NULL,
    operator_id             VARCHAR NOT NULL,
    line_no                 INTEGER NOT NULL,
    sku                     VARCHAR NOT NULL,
    quantity                DOUBLE  NOT NULL,
    unit_price              DOUBLE,             -- NULL = not declared; never inferred into the export
    units_per_case          DOUBLE,
    requested_receipt_date  DATE,               -- NULL = the order's date
    notes                   VARCHAR
);

-- The audit trail. One row per thing that happened to a draft, in order.
CREATE TABLE IF NOT EXISTS zaad_draft_events (
    draft_id                VARCHAR NOT NULL,
    operator_id             VARCHAR NOT NULL,
    happened_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actor                   VARCHAR,
    event                   VARCHAR NOT NULL,   -- created | edited | submitted | evaluated | approved | rejected | exported | reopened | superseded
    revision                INTEGER,
    detail                  VARCHAR
);

-- A company's own import format. Mapping is a JSON object of {output column -> draft field}; the
-- field vocabulary is fixed in api/product/exporting.py and validated on save, so an export can
-- never name a column the product cannot fill.
CREATE TABLE IF NOT EXISTS zaad_export_profiles (
    profile_id              VARCHAR NOT NULL,
    operator_id             VARCHAR NOT NULL,
    name                    VARCHAR NOT NULL,
    format                  VARCHAR NOT NULL,   -- csv | xlsx | print
    sheet_name              VARCHAR,
    delimiter               VARCHAR,
    date_format             VARCHAR,            -- iso | dmy | mdy | compact
    number_format           VARCHAR,            -- plain | grouped
    filename_template       VARCHAR,
    supplier_id             VARCHAR,            -- NULL = every supplier; else a supplier-specific profile
    columns                 VARCHAR NOT NULL,   -- JSON: [{"header": "...", "field": "...", "constant": "..."}]
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE zaad_export_profiles IS 'Operator-defined output formats for approved orders. Deterministic column mapping; no file content is interpreted by a model.';

CREATE TABLE IF NOT EXISTS zaad_export_log (
    export_id               VARCHAR NOT NULL,
    operator_id             VARCHAR NOT NULL,
    draft_id                VARCHAR NOT NULL,
    revision                INTEGER,
    profile_id              VARCHAR,
    profile_name            VARCHAR,
    format                  VARCHAR,
    filename                VARCHAR,
    actor                   VARCHAR,
    happened_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- One proposal evaluation: two runs of the released engine over the same information set, one with
-- the proposal overlaid on the workspace and one without. No economics are computed here; the
-- result is the two reports' own ledger lines.
CREATE TABLE IF NOT EXISTS zaad_evaluations (
    evaluation_id           VARCHAR NOT NULL,
    operator_id             VARCHAR NOT NULL,
    draft_id                VARCHAR NOT NULL,
    revision                INTEGER,
    baseline_job_id         VARCHAR,
    proposal_job_id         VARCHAR,
    as_of                   VARCHAR,
    scope_skus              VARCHAR,            -- JSON list: the products the two runs covered
    status                  VARCHAR NOT NULL,   -- QUEUED | RUNNING | DONE | FAILED | TIMEOUT | CANCELLED
    note                    VARCHAR,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at             TIMESTAMP
);

-- Commercial structure the SKU master may declare (§63). Nullable: a workspace that does not
-- declare them shows neither, and nothing is inferred from the description text.
ALTER TABLE stg_fmcg_skus ADD COLUMN IF NOT EXISTS brand VARCHAR;
ALTER TABLE stg_fmcg_skus ADD COLUMN IF NOT EXISTS sub_category VARCHAR;

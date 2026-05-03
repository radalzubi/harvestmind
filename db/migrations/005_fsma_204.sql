-- Migration 005: FSMA Section 204 traceability tables
-- Implements Key Data Elements (KDEs) and Critical Tracking Events (CTEs)
-- as required by 21 CFR Part 1, Subpart S (Food Safety Modernization Act, Section 204).
-- Compliance date: July 20, 2028 (extended Nov 2025). Major buyers require data now.
-- Electronic sortable spreadsheet must be producible within 24 hours of FDA request.

CREATE TABLE IF NOT EXISTS fact_lots (
    lot_id                          VARCHAR PRIMARY KEY,
    traceability_lot_code           VARCHAR NOT NULL UNIQUE,    -- TLC: core FSMA-204 identifier
    tlc_source_reference            VARCHAR NOT NULL,           -- farm name + GLN per FTL requirements
    product_id                      VARCHAR NOT NULL REFERENCES dim_products(product_id),
    quantity_kg                     DOUBLE NOT NULL CHECK (quantity_kg > 0),
    unit_of_measure                 VARCHAR NOT NULL DEFAULT 'kg',
    harvest_date                    DATE,
    pack_date                       DATE,
    best_by_date                    DATE,
    supplier_id                     VARCHAR REFERENCES dim_suppliers(supplier_id),
    origin_location_id              VARCHAR REFERENCES dim_locations(location_id),
    gtin_14                         VARCHAR(14),
    sscc                            VARCHAR(18),                -- GS1 Serial Shipping Container Code
    parent_lot_id                   VARCHAR,                    -- for transformation chains
    lot_status                      VARCHAR DEFAULT 'active',   -- 'active','consumed','disposed','recalled'
    created_at                      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_lot_status CHECK (lot_status IN ('active','consumed','disposed','recalled','donated'))
);

COMMENT ON TABLE fact_lots IS 'FSMA-204 lot master. traceability_lot_code is the PTI-aligned identifier on the case label.';

-- Append-only: no UPDATE statements allowed. Use INSERT only.
-- Enforce via application layer (leakage_guard.py) and trigger if DB supports it.
CREATE TABLE IF NOT EXISTS fact_cte_events (
    cte_id                          VARCHAR PRIMARY KEY,
    lot_id                          VARCHAR NOT NULL REFERENCES fact_lots(lot_id),
    traceability_lot_code           VARCHAR NOT NULL,
    cte_type                        VARCHAR NOT NULL,
    event_timestamp                 TIMESTAMP NOT NULL,
    location_id                     VARCHAR REFERENCES dim_locations(location_id),
    location_description            VARCHAR NOT NULL,           -- KDE: human-readable location
    business_name                   VARCHAR NOT NULL,           -- KDE: trading partner name
    point_of_contact                VARCHAR,                    -- KDE: name or role
    phone_or_email                  VARCHAR,                    -- KDE: contact info
    quantity_kg                     DOUBLE,
    referenced_tlc_codes            VARCHAR[],                  -- for transformation: input TLCs
    new_tlc_code                    VARCHAR,                    -- for transformation: output TLC
    additional_kdes                 VARCHAR,                    -- JSON blob for CTE-specific KDEs
    recorded_by                     VARCHAR,
    created_at                      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- immutable record time

    CONSTRAINT chk_cte_type CHECK (cte_type IN (
        'harvesting','cooling','initial_packing','shipping','receiving','transformation'
    ))
);

COMMENT ON TABLE fact_cte_events IS 'Append-only FSMA-204 CTE event log. Never UPDATE — only INSERT. FDA requires 24-hr retrieval by TLC.';

-- View for FDA 24-hour sortable spreadsheet export
CREATE OR REPLACE VIEW v_fsma_204_report AS
SELECT
    c.cte_id,
    c.traceability_lot_code,
    c.cte_type                      AS "Critical Tracking Event",
    c.event_timestamp               AS "Date/Time of Event",
    c.location_description          AS "Location",
    c.business_name                 AS "Business Name",
    c.point_of_contact              AS "Point of Contact",
    c.phone_or_email                AS "Phone or Email",
    p.crop_name                     AS "Product Description",
    c.quantity_kg                   AS "Quantity (kg)",
    l.harvest_date                  AS "Harvest Date",
    l.tlc_source_reference          AS "TLC Source Reference",
    c.referenced_tlc_codes          AS "Referenced TLC Codes",
    c.created_at                    AS "Record Created"
FROM fact_cte_events c
JOIN fact_lots l ON c.lot_id = l.lot_id
JOIN dim_products p ON l.product_id = p.product_id
ORDER BY c.traceability_lot_code, c.event_timestamp;

COMMENT ON VIEW v_fsma_204_report IS 'FDA-ready 24-hour sortable spreadsheet. Filter by TLC to respond to traceback request.';

-- Indexes for fast TLC lookup (critical for 24-hr FDA response)
CREATE INDEX IF NOT EXISTS idx_lots_tlc ON fact_lots(traceability_lot_code);
CREATE INDEX IF NOT EXISTS idx_lots_supplier ON fact_lots(supplier_id);
CREATE INDEX IF NOT EXISTS idx_cte_lot ON fact_cte_events(lot_id);
CREATE INDEX IF NOT EXISTS idx_cte_tlc ON fact_cte_events(traceability_lot_code);
CREATE INDEX IF NOT EXISTS idx_cte_type ON fact_cte_events(cte_type);
CREATE INDEX IF NOT EXISTS idx_cte_timestamp ON fact_cte_events(event_timestamp);

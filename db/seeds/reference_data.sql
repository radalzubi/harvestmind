-- Reference seed data: Indiana/Midwest pilot market
-- Realistic archetypes — not real businesses. Safe for demo.

-- Products (10 core SKUs, mix of FTL and non-FTL)
INSERT OR IGNORE INTO dim_products (product_id, crop_name, crop_category, variety, shelf_life_days, cold_chain_required, is_ftl_item, grade_levels) VALUES
    ('PRD-001', 'Romaine Lettuce',   'leafy_green', 'Green Romaine',  7,  TRUE,  TRUE,  ARRAY['A','B']),
    ('PRD-002', 'Baby Spinach',      'leafy_green', 'Savoy',          5,  TRUE,  TRUE,  ARRAY['A','B']),
    ('PRD-003', 'Cherry Tomatoes',   'tomato',      'Campari',        10, TRUE,  TRUE,  ARRAY['A','B','C']),
    ('PRD-004', 'Bell Pepper Mix',   'pepper',      'Red/Yellow/Orange', 14, TRUE, FALSE, ARRAY['A','B']),
    ('PRD-005', 'Cucumber',          'other',       'English',        10, TRUE,  FALSE, ARRAY['A','B']),
    ('PRD-006', 'Zucchini',          'squash',      'Green',          7,  FALSE, FALSE, ARRAY['A','B']),
    ('PRD-007', 'Kale Bunched',      'leafy_green', 'Curly Kale',     7,  TRUE,  TRUE,  ARRAY['A','B']),
    ('PRD-008', 'Sweet Corn',        'other',       'Bi-Color',       4,  FALSE, FALSE, ARRAY['A','B']),
    ('PRD-009', 'Strawberry',        'berry',       'Albion',         5,  TRUE,  TRUE,  ARRAY['A','B']),
    ('PRD-010', 'Yellow Onion',      'allium',      'Storage',        60, FALSE, FALSE, ARRAY['A','B','C']);

-- Suppliers (6 Indiana-region farms/aggregators)
INSERT OR IGNORE INTO dim_suppliers (supplier_id, supplier_name, supplier_type, lat, lon, region, state, county_fips, gap_certified, primary_crops, total_ha, avg_reliability) VALUES
    ('SUP-001', 'Sunrise Fields Farm',    'farm',        39.78, -86.23, 'Central Indiana',  'IN', '18057', TRUE,  ARRAY['leafy_green','tomato'],       48.0,  0.92),
    ('SUP-002', 'Heartland Acres',        'farm',        40.15, -85.40, 'East Central IN',  'IN', '18035', TRUE,  ARRAY['pepper','cucumber','squash'],  62.0,  0.87),
    ('SUP-003', 'Crossroads Organics',    'farm',        39.50, -87.10, 'West Central IN',  'IN', '18167', TRUE,  ARRAY['leafy_green','kale'],          30.0,  0.90),
    ('SUP-004', 'Green River Aggregator', 'aggregator',  37.98, -87.56, 'Southern Indiana', 'IN', '18019', FALSE, ARRAY['tomato','pepper','corn'],      NULL,  0.85),
    ('SUP-005', 'Prairie Berry Growers',  'farm',        40.47, -86.13, 'North Central IN', 'IN', '18007', TRUE,  ARRAY['strawberry'],                  18.0,  0.88),
    ('SUP-006', 'Indiana Root Co',        'farm',        40.25, -85.72, 'East Indiana',     'IN', '18095', FALSE, ARRAY['allium','root_veg'],            80.0,  0.94);

-- Locations (1 hub, 1 DC, 3 buyers, 6 farm locations)
INSERT OR IGNORE INTO dim_locations (location_id, location_name, location_type, city, state, lat, lon, cold_storage_m3) VALUES
    ('LOC-HUB-01', 'Hoosier Harvest Hub',       'hub',          'Greenfield',   'IN', 39.79, -85.77, 1200.0),
    ('LOC-DC-01',  'Central Indiana DC',         'dc',           'Indianapolis', 'IN', 39.77, -86.16,  800.0),
    ('LOC-BUY-01', 'IU Health Campus Kitchen',   'buyer',        'Indianapolis', 'IN', 39.77, -86.18,  NULL),
    ('LOC-BUY-02', 'Market Wagon Fulfillment',   'buyer',        'Westfield',    'IN', 40.04, -86.12,  NULL),
    ('LOC-BUY-03', 'Piazza Fresh Distribution',  'buyer',        'Indianapolis', 'IN', 39.80, -86.30,  NULL),
    ('LOC-FAR-01', 'Sunrise Fields - Main',      'farm',         'Greenfield',   'IN', 39.78, -86.23,  NULL),
    ('LOC-FAR-02', 'Heartland Acres - Main',     'farm',         'Muncie',       'IN', 40.15, -85.40,  NULL),
    ('LOC-FAR-03', 'Crossroads Organics',        'farm',         'Terre Haute',  'IN', 39.50, -87.10,  NULL),
    ('LOC-FAR-04', 'Green River Aggregator',     'farm',         'Evansville',   'IN', 37.98, -87.56,  NULL),
    ('LOC-FAR-05', 'Prairie Berry',              'farm',         'Kokomo',       'IN', 40.47, -86.13,  NULL),
    ('LOC-FAR-06', 'Indiana Root Co',            'farm',         'Anderson',     'IN', 40.25, -85.72,  NULL);

-- Buyers (5 accounts: 2 anchor/tier-1, 3 standard/tier-2)
INSERT OR IGNORE INTO dim_buyers (buyer_id, buyer_name, buyer_type, location_id, city, state, tier, avg_weekly_spend, preferred_crops) VALUES
    ('BUY-001', 'IU Health System',         'institution', 'LOC-BUY-01', 'Indianapolis', 'IN', 1, 18000.0, ARRAY['leafy_green','tomato','pepper']),
    ('BUY-002', 'Market Wagon',             'distributor', 'LOC-BUY-02', 'Westfield',    'IN', 1, 12000.0, ARRAY['leafy_green','berry','squash']),
    ('BUY-003', 'Piazza Produce / IF&P',    'wholesale',   'LOC-BUY-03', 'Indianapolis', 'IN', 2,  8500.0, ARRAY['tomato','pepper','cucumber']),
    ('BUY-004', 'Traders Point Creamery Café','restaurant', NULL,         'Indianapolis', 'IN', 2,  3200.0, ARRAY['leafy_green','herb','tomato']),
    ('BUY-005', 'Gleaners Food Bank',       'foodbank',    NULL,         'Indianapolis', 'IN', 2,  1500.0, ARRAY['allium','squash','corn']);

-- Logistics lanes (hub ↔ buyer routes)
INSERT OR IGNORE INTO dim_logistics_lanes (lane_id, origin_node, destination_node, transit_hrs, cold_chain_flag, cost_per_kg, capacity_kg_per_trip, days_operational) VALUES
    ('LANE-001', 'LOC-HUB-01', 'LOC-BUY-01', 0.5, TRUE,  0.08, 2000.0, ARRAY['mon','tue','wed','thu','fri']),
    ('LANE-002', 'LOC-HUB-01', 'LOC-BUY-02', 0.7, TRUE,  0.10, 1500.0, ARRAY['mon','wed','fri']),
    ('LANE-003', 'LOC-HUB-01', 'LOC-BUY-03', 0.4, TRUE,  0.07, 2500.0, ARRAY['mon','tue','wed','thu','fri']),
    ('LANE-004', 'LOC-HUB-01', 'LOC-BUY-04', 0.6, FALSE, 0.09, 800.0,  ARRAY['mon','wed','fri']),
    ('LANE-005', 'LOC-HUB-01', 'LOC-BUY-05', 0.5, FALSE, 0.06, 3000.0, ARRAY['tue','thu']),
    -- Farm to hub
    ('LANE-006', 'LOC-FAR-01', 'LOC-HUB-01', 0.3, TRUE,  0.05, 3000.0, ARRAY['mon','tue','wed','thu','fri']),
    ('LANE-007', 'LOC-FAR-02', 'LOC-HUB-01', 1.0, TRUE,  0.09, 2000.0, ARRAY['mon','wed','fri']),
    ('LANE-008', 'LOC-FAR-03', 'LOC-HUB-01', 1.5, TRUE,  0.12, 2000.0, ARRAY['tue','thu']),
    ('LANE-009', 'LOC-FAR-04', 'LOC-HUB-01', 2.0, TRUE,  0.15, 2500.0, ARRAY['mon','thu']),
    ('LANE-010', 'LOC-FAR-05', 'LOC-HUB-01', 0.8, TRUE,  0.08, 1500.0, ARRAY['mon','wed','fri']),
    ('LANE-011', 'LOC-FAR-06', 'LOC-HUB-01', 0.9, FALSE, 0.07, 3000.0, ARRAY['mon','wed','fri']);

# ZAAD route and shared-risk contract

`Node`: supplier, port, border, chokepoint, hub or DC, country, known_at. `Edge`: directed origin/destination, mode, available flag, per-review volume capacity, known_at and named failure domains. `Route`: one approved item-supplier itinerary of edge IDs, all-in landed quote, base-unit capacity, validity, operator compliance clearance, quote reference and known_at. Item IDs identify a location and carry base-unit-to-volume conversion.

Validation checks references, continuity and actual supplier→item location endpoints. This prevents the same alternate port being treated as feasible from every origin. Route feasibility is an intersection of approval, legal clearance, edge availability, unexpired quote and at least12 observed deliveries. The prototype does not estimate capacity from historic delivered volume; capacity is an explicit operator-known constraint, avoiding double penalization of low fills.

The path shortlist is supplied and approved, not invented by a route-finding LLM. A route card shows path, supplier, item, landed cost, capacity, lead median/P90, accepted fill, history size, common failure domains, evidence IDs, expiry and rejection reason. Quantiles are descriptive sample quantiles, not confidence bounds. Alternative cost includes the whole landed quote; the UI +40% experiment says landed quote, not falsely freight-only.

Edge capacity uses the same declared volume unit as item.volume; item quantity consumes quantity×volume on every path edge. Route capacity uses item base units. Warehouse uses the same volume unit. Mixed units require explicit conversion before ingestion; no implicit currency conversion is allowed. One run has one currency, and all fees/quotes must already be converted with operator-approved as-of rates.

Shared domains may identify PORT, CARRIER, LANE, CHOKEPOINT, BORDER, COUNTRY, HUB or MODE. Scenario ranks share a random stream for each common domain plus a route-specific stream, followed by marginal CDF correction. This is structural dependence, not fitted Kendall tau or supplier diversification proof. Exposure counts alone cannot certify independence.

MENA and US examples are structural only. China→Jebel Ali ordinarily implicates Hormuz; China→Jeddah ordinarily implicates Bab el-Mandeb, not automatically the same chokepoint. Exact carrier/transshipment paths can add common failures. Current carrier/cargo/direction/quote approval is mandatory; dated advertised landbridges are not evergreen capacity. See COMPETITIVE_BASELINE.md for official contemporary references and explicit uncertainty.

Compliance is a hard operator-supplied gate. The provider registry audits OFAC/UN/EU/UK sources but no name-screening or legal-clearance service is shipped. `cleared` is not ZAAD's legal certification. No route planning supports evasion of restrictions.

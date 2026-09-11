# Zaad logistics data-source and access audit

Research date: 2026-09-05. Scope: civilian commercial inventory and lawful supply resilience only. This is a source/engineering assessment, not legal clearance, navigation advice, or certification that a transaction is permitted. Sources and contracts change; production onboarding must recheck them. `UNKNOWN` means not established from the primary material inspected, not that a capability does not exist. No paid access, subscriptions, supplier contact, or purchases were made.

## Decision

Build the availability/provenance contract first. Enable a bounded **NWS CAP-alert adapter** for US weather-exposed lanes and a reviewed **official commercial port-notice metadata adapter**. Use operator POs, confirmed ETAs and receipts as the primary planning evidence. Add ECMWF open forecasts for global weather exposures once geographic mapping and issued-forecast retention are implemented. GDELT metadata can support event discovery, never establish that a port is closed. PortWatch is useful aggregate context, but its commercial reuse needs review and its current historical observations are not verified historical vintages.

No source reviewed supplies a free, complete, commercially cleared, global, live, historical-as-known, shipment-level resilience feed. A public website is not a permission to scrape, redistribute, train models on, or sell its contents. A vessel position is not an operator PO arrival, port volume is not supplier fill, a rate index is not an executable freight quote, and weather severity is not calibrated lead-time delay.

## Existing-path findings

Inspected `adaptive/signals.py`, `adaptive/indicators.py`, `scripts/fetch_real_data.py`, `scripts/fetch_indicators.py`, `ingestion/noaa_weather_fetcher.py`, `scripts/ingest_real_data.py`, and project instructions. Findings refer to the inherited code before this work:

- `SignalStore.series(as_of=...)` filters observation time, not first availability. The comment claiming leakage freedom is therefore too strong. `refreshed_at` does not participate in selection.
- The PortWatch monthly adapter timestamps completed-month totals on day 28. This can include days 29–31 before they happened; even a month-end stamp would not establish release availability. File modification time measures the local copy, not provider publication. Excluding only the last month cannot repair this.
- The ArcGIS fetcher requests current rows and rewrites a CSV; it does not retain historical response versions, first-seen dates or hashes. A current `lastEditDate` is a layer-edit timestamp, not each record's first publication time.
- GDELT and other indicator sidecars preserve one download date, but do not prove when each historical datum became available. The GDELT script's `24m` setting and five-second-limit comment are implementation assumptions unless reverified against the endpoint; old official documentation has changed its history window several times.
- NOAA CDO ingestion catches every exception and returns an empty frame. A resilience path must distinguish credentials absent, transport failure, malformed data, no observations and stale data; none means normal conditions.
- CSV/operator ingestion and external intelligence must stay separate. This audit does not authorize writing public/synthetic information into any production training database.

## Source capabilities and rights

### 1. IMF PortWatch — aggregate ports/chokepoints

**Observed technical interface.** The public [Daily Ports layer metadata](https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Ports_Data/FeatureServer/0?f=pjson) exposes query-only ArcGIS REST, JSON/GeoJSON/PBF, `maxRecordCount=1000`, `ObjectId`, UTC date-only `date`, port identifiers, port-call and import/export estimates; layer `copyrightText` was empty. The existing daily chokepoint service is the sibling `Daily_Chokepoints_Data/FeatureServer/0`. The [catalog API](https://portwatch.imf.org/api/search/definition/) discovers records; it is not the row-level observation API.

The [IMF methodology](https://www.elibrary.imf.org/abstract/journals/001/2025/093/article-A001-en.xml) describes daily port-call/shipment estimates beginning 2019-01-01, derived from AIS. Geographic coverage in that publication is a dated description, not a guaranteed current complete list. The [separate trade-nowcast page](https://data-download.imf.org/ClimateData/portwatch-monitor.html) states monthly estimates lag seven working days and undergo weekly revisions. Do not transfer that lag to every daily port row or call the estimates customs-confirmed trade.

**Access/latency.** No key was required to inspect layer metadata. Endpoint quota and production SLA: UNKNOWN. Data frequency is daily, not proof of same-day publication. Row-level published/ingested timestamps, version endpoint and unrevised as-known archive: NOT VERIFIED. Pagination must inspect errors and transfer-limit flags, verify record counts, and use stable ordering. Cache HTTP responses with request and retrieval timestamps; do not treat `cacheMaxAge` as a business freshness guarantee.

**Rights.** [IMF current copyright/data terms](https://www.imf.org/en/about/copyright-and-terms) distinguish statistical data and other content and explicitly direct potential commercial reusers to request permission. Item-specific permission overriding that requirement was not verified. Commercial feature use, redistributing raw/derived data, long-term retention and ML training: **LEGAL REVIEW / NOT APPROVED**. Public access and a blank copyright field grant none of those rights. Retain only the minimum research metadata until the relevant license is confirmed. Production-commercial provider status should be `LEGAL_REVIEW`, not `READY`.

**Planning use.** Route-context feature after a tested geographic join; never directly set a supplier's fill to the port throughput index. Port calls/cargo estimates can reflect demand, transshipment, mix, coverage gaps and measurement revision as well as congestion. Compare published forecasts with subsequent observations, not retrospectively revised observations presented as advance intelligence.

### 2. Kpler / MarineTraffic — commercial AIS and events

[MarineTraffic Data Services](https://www.kpler.com/product/maritime/data-services) offers AIS APIs/streams, port events and historical data, advertising an archive since 2010. That is a product-family claim; a particular endpoint's field set/history depends on entitlement. [Kpler's 2026 API update](https://www.kpler.com/blog/maritime-product-updates-smarter-risk%2Dsignals-stronger-apis-faster-mobile-experience) discusses the enhanced historical AIS endpoint. Do not implement a discontinued endpoint from an old Spire tutorial.

API credentials, exact end-to-end latency, rate/concurrency limits, archive availability, quotation and SLA: **CONTRACT REQUIRED / UNKNOWN**. Do not translate an advertising phrase such as real-time into a measured maximum delay. AIS may be absent, spoofed, inconsistent or stale. Use only civil cargo records relevant to the user's lawful supply chain; exclude military/intelligence use cases.

[Kpler terms](https://www.kpler.com/company/terms-of-use) describe product-specific and contract-specific restrictions, information-quality limitations, and restrictions on historical-data copying, distribution and derivative works absent written agreement. Zaad SaaS display, derived alerts, model fitting, embeddings, caching, tenant sharing, retention after termination and redistribution need explicit written rights. No purchase or trial is authorized by this audit. Status: `CONTRACT_REQUIRED`; default disabled.

**Supplier concentration matters:** [Kpler completed Spire Maritime acquisition in April 2025](https://www.kpler.com/blog/kpler-completes-acquisition-of-spire-maritime-strengthening-maritime-intelligence-capabilities). Treating MarineTraffic and Spire Maritime as independent vendor redundancy would be misleading. Validate upstream and corporate independence before claiming multi-source resilience.

### 3. AIS alternatives

**VesselFinder.** [API documentation](https://api.vesselfinder.com/docs/) describes AIS, voyage, vessel particulars and port-call datasets, API keys and credit/subscription models. Posted example: 10,000 credits cost EUR330 excluding VAT; it is a usage unit, not a Zaad monthly quote. [FAQ](https://api.vesselfinder.com/docs/faq.html) says subscription polling depends on agreement and observation updates depend on transmissions. Coverage and arrival prediction require testing.

Its [2026 terms](https://www.vesselfinder.com/terms) are materially restrictive: customer-facing redistribution, caching beyond agreed retention and ML training/evaluation/benchmarking are disallowed without written authorization; internal derived data has conditions. It is expressly not a compliance or safety-of-life decision service. Accordingly, low advertised API cost does not clear this product's use. Status: `CONTRACT_REQUIRED`; ML/benchmark use `DENIED_UNLESS_WRITTEN`; retention, display and tenant redistribution separately negotiated.

**NOAA MarineCadastre / AccessAIS.** [Official catalog](https://coast.noaa.gov/digitalcoast/data/vesseltraffic.html) provides historical US-related vessel traffic (catalog inspected: 2009–2025), including CSV and geospatial services. [AccessAIS](https://coast.noaa.gov/digitalcoast/tools/ais.html) adds data quarterly. The [FAQ](https://coast.noaa.gov/data/marinecadastre/ais/faq.pdf) explicitly says it has no live feed or satellite AIS and describes geographic gaps and third-party restrictions. This is a plausible historical outcome/context dataset, not global live coverage or a historical as-known feed. Its [dictionary](https://coast.noaa.gov/data/marinecadastre/ais/data-dictionary.pdf) distinguishes UTC position time, MMSI, coordinates and speed. Audit the selected dataset's metadata/use constraints before publishing derived commercial products; no blanket clearance for all NOAA-hosted third-party data. No key needed for public catalog; clip/download limits and source publication delay apply. Rights/retention for a specific file: `DATASET_REVIEW`.

### 4. Freightos Baltic Index (FBX)

[Official API reference](https://apidocs.freightos.com/reference/get_fbx-data) identifies the FBX data endpoint. [Current Freightos data terms](https://www.freightos.com/freightos-data-terms-conditions/) make subscribed lanes, history, frequency, delivery channel and scope purchase-order specific; non-public data is confidential. Public reproduction has attribution/link requirements. API auth, numeric quotas, commercial quote, precise release timing, revision/vintage archive, storage duration and training rights were not verified. Status: `CONTRACT_REQUIRED`; do not cache or redistribute a paid API because a public chart is visible.

Planning role is a broad freight-cost prior, not a bookable quote. The terms themselves warn indexes need not represent the physical price paid. Calibrate against operator quotations, currency, container type, lane, surcharges and quote validity. Index movements cannot justify automatically purchasing an alternative route.

### 5. GDELT Project — discovery, not ground truth

[GDELT's own terms](https://gdeltproject.org/about.html#termsofuse) permit commercial use and redistribution of its released datasets with citation and link. This does not grant rights over the linked publisher articles/photos. Store identifiers, URLs, structured metadata and timestamps; do not bulk republish article bodies or feed them to model training without separate rights. Training on GDELT's released structured dataset is compatible with its broad stated grant; training on underlying linked content is **UNKNOWN / PUBLISHER REVIEW**.

[DOC 2.0 documentation](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/) provides JSON search/timeline modes. Its [2018 history update](https://blog.gdeltproject.org/doc-2-0-updates-1-5-year-searching-and-updated-mobile-interface/) shows why a hardcoded historical window should not be treated as timeless. The current available lookback, effective query rate, completeness and latency SLA were not independently measured. No key for the public DOC interface; client should bound requests, honor throttling and retain errors. GDELT Cloud is a separate commercial offering with different terms; do not mix its subscription rights with GDELT Project dataset rights.

An article event date, GDELT first-seen/ingestion time and Zaad retrieval time are different. Timeline share is news attention, not event probability; deduplicate syndication, test language/geography bias, corroborate through official notices, and include false-positive/late-warning controls. Source-discovery-only status is appropriate before predictive calibration.

### 6. NOAA NWS CAP alerts — viable minimum live adapter

[NWS API documentation](https://www.weather.gov/documentation/services-web-api) states the API is free, open for any purpose and cache-friendly; it requires an identifying User-Agent, not a paid key. Exact abuse rate limits are unpublished. Honor cache headers and retry/backoff; do not promise an SLA. API forecasts, observations and alerts have different freshness semantics. Current alerts are not a guaranteed complete long-term issue-time archive. Snapshot from first deployment onward and explicitly retain `sent`, `effective`, `onset`, `expires`, alert identifier, update/cancel references, areas/geocodes, status and retrieval time when supplied. Preserve absent timestamps as absent.

Use US weather exposure only. A warning is not a confirmed port closure and an expired or cancelled alert must not keep a lane closed. Raw government alert data commercial/derived/caching use is supported by the stated grant; third-party embedded content and official branding are separate. Proposed retention: immutable permitted alert versions for audit, with organization policy and privacy review; that is Zaad's design, not a provider-mandated retention term. NWS is not a substitute for ECMWF/global or local meteorological services.

**Existing CDO is different.** [NOAA CDO API](https://www.ncei.noaa.gov/cdo-web/webservices/v2) concerns historical observations and uses a token. It must not be relabeled a live maritime warning source. Verify its quota before new deployment; historical observation dates do not establish real-time availability.

### 7. ECMWF open forecasts — global hazard candidate

[ECMWF Open Data](https://www.ecmwf.int/en/forecasts/datasets/open-data) explicitly permits commercial use and redistribution under CC BY 4.0 plus ECMWF terms. The inspected product page describes global IFS/AIFS forecast fields in GRIB2, public/cloud access, four daily cycles, a portal limit of 500 simultaneous connections and a rolling 12-run archive (about 2–3 days). This is a provider-wide ceiling, not permission for Zaad to run 500 clients. Use one modest shared fetcher. IFS release follows its dissemination schedule; model initialization time is not publication time. Reanalysis is not an issued forecast.

The public rolling endpoint cannot alone backtest years of issued forecasts. Historical archives and higher-resolution products have separate access arrangements. Retain licensed runs prospectively, with issue/retrieval/valid times, model version, attribution and checksums. Record any derived lane-risk transformation. Numeric delay/closure effects require operational calibration; global weather resolution does not imply port-operating-threshold accuracy. Commercial redistribution is permitted for this open-data subset under attribution; current license details, third-party products and model-training pipeline still require normal compliance review. Do not generalize this license to every ECMWF/CDS dataset.

### 8. Official port, canal, customs and operator notices

Highest-authority source for a declared commercial closure/reopening, but not a uniform API or guaranteed throughput restoration. Each authority needs an allowlisted URL/feed, local timezone, publication precision, document revision and stated applicability. Auth, rate limits, history, content license and automated reuse are authority-specific **UNKNOWN until registered**. HTML/PDF availability does not establish RSS/API support. Cache modest metadata plus permitted audit evidence; preserve original language, source URL, extraction confidence and human review. Do not turn an inferred closure probability into a legal prohibition or a navigation instruction.

For Jordan/GCC, onboard only operator-relevant commercial Aqaba/ASEZA, Saudi port/customs and carrier notices after verifying their official channels and scope. This audit does not verify a comprehensive live MENA port-notice API. An official notice in another country is not evidence of Jordan-specific predictive performance.

## Legitimate dated historical fixture: Baltimore reopening

Source: [USACE Baltimore commercial-channel restoration notice, published June 10, 2024](https://www.nab.usace.army.mil/Media/News-Releases/Article/3802402/us-army-corps-of-engineers-announces-full-restoration-of-baltimores-fort-mchenr/). Fact suitable for a minimal fixture: the Fort McHenry Federal Channel was restored to its operational dimensions for commercial transit. This civil port-status notice does not authorize military vessel tracking. Retain a paraphrased event type, dimensions if needed, URL and provenance—not photos or the full article.

Verified publication precision is **DATE ONLY**, not an exact intraday timestamp. Source HTML metadata could not be independently inspected with the shell fetch (HTTP403); web-rendered official text provided the date. Do not invent an hour. For daily causal replay, a defensible conservative boundary is `2024-06-11T04:00:00Z` (start of the next day in America/New_York), explicitly named `available_after_upper_bound`, **not** `published_at`. Use only from that boundary in a date-granular research replay, and label that same-day timing is unavailable. A strictly exact-issue-time benchmark must exclude it until exact publication evidence is obtained.

For comparison, [April 4, 2024 tentative reopening timeline](https://www.nab.usace.army.mil/Media/News-Releases/Article/3731790/us-army-corps-of-engineers-develops-tentative-timeline-to-reopen-fort-mchenry-c/) and [May 24 channel-expansion update](https://www.nab.usace.army.mil/Media/News-Releases/Article/3787297/us-army-corps-of-engineers-expands-port-of-baltimore-limited-access-channel/) are distinct dated forecasts/updates. Never place June's actual reopening date into the April planning features. Current publication pages can themselves have later edits: this is **dated official-event metadata replay**, not proof that current full page text is an immutable 2024 vintage.

## Restrictions and sanctions: constraints, not optimization opportunities

Sanctions data must be handled as compliance inputs with human/legal ownership. A route cannot be marked legal merely because no name matched. Applicable jurisdiction, goods, beneficial ownership/control, counterparties, vessel, insurer, payment channel, licenses and effective dates matter. Empty/stale/unavailable screening means `UNKNOWN` and blocks automated promotion of the route. Never optimize circumvention.

| Authority | Verified source/access | Temporal and rights boundary |
|---|---|---|
| OFAC (US) | [Sanctions List Service](https://ofac.treasury.gov/sanctions-list-service) supplies SDN and separate non-SDN downloads and published delta archives. [Hash documentation](https://ofac.treasury.gov/specially-designated-nationals-list-sdn-list/hash-values-for-ofac-sanctions-list-files) supports integrity checks. | Public downloads; exact quota/SLA and archive completeness not verified. Persist version and effective/publication/retrieval dates. Name screening alone is insufficient. Review personal-data retention and downstream dataset licensing separately; no automatic model training on personal records. |
| UN | [Security Council consolidated list](https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list) offers XML/HTML/PDF and explains measures depend on the relevant committee/regime. | Current list is not a historical snapshot. API SLA, full revision archive and commercial redistribution/training rights: UNKNOWN/LEGAL REVIEW. Consult implementing jurisdictions; a consolidated membership list is not a uniform embargo. |
| EU | [Commission sanctions resources](https://finance.ec.europa.eu/eu-and-world/sanctions-restrictive-measures/overview-sanctions-and-related-resources_en) links the financial list and EUR-Lex legal acts. | The legally authoritative acts and effective dates govern. Machine file access/auth/schema and reuse rights must be rechecked at onboarding; old XML manuals do not establish a current keyless endpoint. Do not substitute a current consolidated list for historical applicable law. |
| UK | [Current UK Sanctions List](https://www.gov.uk/government/publications/the-uk-sanctions-list) and [official closure notice](https://www.gov.uk/government/publications/financial-sanctions-consolidated-list-of-targets/consolidated-list-of-targets). | **The OFSI consolidated list closed on 2026-01-28.** Using it as the live source now would silently miss new designations. GOV.UK publication carries OGL v3 except exclusions. Preserve update notices and rights attribution; resolve exact machine-download and privacy retention separately. |

Zaad should not claim legally complete global screening from these four lists, particularly for transactions governed by additional local laws. Treat sanctions-list access, legal interpretation and user transaction authorization as separate checks.

## Proposed provider registry and runtime contract

The registry is a typed configuration, not merely a list of URLs. Each entry should contain:

- Identity: `provider_id`, dataset/product, official documentation/terms URLs, legal entity, coverage, commercial-cargo scope, owner, review date, review expiry and license/contract reference.
- Access: allowlisted hosts, endpoint version/schema, auth method and secret reference (never a stored secret), configured request timeout, payload/page bound, pagination method, polling budget, cache policy and retry/circuit-breaker settings.
- Timing: observation time semantics, provider issued/published time, first-seen time, retrieved time, validity interval, revision/supersedes identifier, timezone and precision; `historical_vintages_verified` must be false absent evidence.
- Rights independently enumerated: research use, commercial internal use, customer display, raw redistribution, derived redistribution, caching, maximum contractual retention, training/evaluation and post-termination retention; values `ALLOWED`, `DENIED`, `UNKNOWN`, `CONTRACT_REQUIRED`, with evidence URL/date. Do not use one boolean `free`.
- Operational status: `READY`, `DISABLED`, `NO_CREDENTIALS`, `LEGAL_REVIEW`, `RATE_LIMITED`, `UNAVAILABLE`, `STALE`, `SCHEMA_ERROR`. Missing evidence never becomes a zero-risk observation.
- Provenance: immutable payload/metadata checksum where retention permitted, parser version, event ID, source URL, available-as-of boundary, transform version, quality flags, geography matching basis and classification `REAL_PUBLIC`, `REAL_OPERATOR`, `INFERRED` or `ASSUMED`.

**Recommended initial statuses:** NWS public alerts `READY_FOR_BOUNDED_ADAPTER`; official-notice metadata `MANUAL_REVIEW`; ECMWF open-data subset `ADAPTER_PENDING`; GDELT released metadata `DISCOVERY_ONLY`; PortWatch `LEGAL_REVIEW`; MarineTraffic/Kpler and VesselFinder `CONTRACT_REQUIRED`; FBX `CONTRACT_REQUIRED`; sanctions providers `COMPLIANCE_REVIEW`. A report recommendation is not evidence that an adapter has already been implemented or a contract cleared.

### Implemented foundation in this change

`zaad/signals.py` now supplies frozen strict records, atomic immutable replay, three-clock/effective-time/licensing filtering, age decay, syndicated-news deduplication and descriptive route evidence. Its bounded NWS fetcher has a fixed HTTPS destination, redirects disabled, connect/read and overall elapsed-time bounds, response-size/record limits and explicit failure results. It makes no implicit planner network call. The static `config/external_data_sources.yaml` is a rights/access registry **description**, not a network scheduler, credential manager or legal entitlement verifier. `license_status` must come from trusted onboarding, never from untrusted provider text or a customer checkbox presented as legal proof.

The implementation's NWS categorical-severity mapping and freshness half-lives are explicit assumptions, not calibrated probabilities. It does not yet perform automatic polling, durable snapshot persistence, a historical NWS archive, sanctions screening, ECMWF/FBX/AIS integration or automatic MENA port discovery. Callers must persist permitted returned records and preserve previous stores when a fetch raises `ProviderError`. The checked-in Baltimore file contains only factual/date-precision metadata and deliberately cannot pass the strict historical-evidence gate.

Availability at a historical decision requires both the observation's permitted valid-time relationship and a verified issue/first-availability boundary no later than the decision. Forecasts may describe future valid times if issued already. Later revisions must not replace the visible old version. Real-time operation may conservatively use Zaad first-seen time; backtesting must not invent a historical first-seen time. If a provider only supplies today's revised history, label `RETROSPECTIVE_CONTEXT_ONLY` and exclude it from claims of historical warning value.

## Minimal operational checks before live recommendations

1. Fetch only allowed public endpoints and disabled-by-default licensed endpoints; never send operator POs or personal data to a provider merely to test connectivity.
2. Test timeout, rate limit, expired credential, empty but valid response, malformed response, missing/naive/future timestamps, duplicate/revised/cancelled event, source change and geographic mismatch.
3. First store a snapshot in an isolated evidence store, then normalize. No broad exception turns failure into an apparently normal condition.
4. Show source age, issue time, retrieval time, status, geography and transformation next to an alert. Treat freshness thresholds as policy assumptions, not guaranteed vendor latency.
5. Compare signal-on/off forecasts on the same held-out outcomes with publication-time gating; report false alerts, warning lead time, misses and confidence calibration before claiming value. A dated Baltimore fixture tests temporal plumbing; it does not validate demand, route switching, customer savings or MENA performance.
6. Maintain attribution and contract retention deletion rules. Paid entitlements, training rights and raw-data redistribution remain off until explicit approval. No paid services were acquired in this task.

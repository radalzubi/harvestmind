# External data

Public, redistributable series used to validate the commercial branch.
Committed so results are reproducible without re-hitting the source APIs.
Re-fetch with `python3 scripts/fetch_real_data.py`.

## fred/  — US Census, via FRED CSV (no key required)

| series | meaning | span |
|---|---|---|
| `S4244SM144NCEN` | Merchant wholesalers sales, grocery and related products (NAICS 4244), **not** seasonally adjusted | 1992-01 .. 2026-06 |
| `S4244SM144SCEN` | the same, seasonally adjusted | 1992-01 .. 2026-06 |
| `MRTSSM445USN` | Retail sales, food and beverage stores | 1992-01 .. 2026-06 |
| `MRTSSM4451USN` | Retail sales, grocery stores | 1992-01 .. 2026-06 |
| `WHLSLRIRSA`, `WHLSLRIRNSA` | Merchant wholesalers inventory/sales ratio | 1992-01 .. 2026-06 |
| `WHLSLRIMSA`, `WHLSLRSMSA` | Wholesale inventories, wholesale sales | 1992-01 .. 2026-06 |
| `RETAILIRSA`, `TOTBUSIRNSA` | Retail and total-business inventory/sales ratios | 1992-01 .. 2026-06 |
| `CUSR0000SAF11` | CPI, food at home | 1952-01 .. 2026-07 |
| `WPU02` | PPI, processed foods and feeds | 1947-01 .. 2026-07 |

The demand spine is `S4244SM144NCEN`. NSA is deliberate: seasonality is the
signal being forecast, and an adjusted series has had it filtered out.

## portwatch/ — IMF PortWatch, satellite AIS

Joint IMF and Oxford Environmental Change Institute platform, derived from
AIS signals. Public ArcGIS FeatureServer, no key required.

| file | rows | contents |
|---|---|---|
| `chokepoint_daily.csv` | 78,372 | daily transit calls and cargo capacity for 28 chokepoints, 2019-01-01 .. 2026-08-30 |
| `regional_ports_daily.csv` | 22,376 | daily port calls plus import and export tonnage for Aqaba, Jeddah, Umm Qasr, Latakia, Ashdod, Djibouti, Jebel Ali, King Abdullah Port |

The window spans COVID, the Ever Given grounding, the Red Sea crisis from
December 2023, and the 2026 Hormuz disruption, so a disruption scenario can
be checked against a period in which it actually happened.

PortWatch records **Aqaba as carrying 100% of Jordan's maritime imports**.
Jordan's single-seaport exposure is therefore measured, not assumed.

## indicators/ — leading indicators (keyless public feeds, `scripts/fetch_indicators.py`)

| file | source | cadence |
|---|---|---|
| `freight_index.csv` | FRED TSIFRGHT, Freight Transportation Services Index | monthly |
| `brent_usd.csv`, `diesel_usd.csv` | FRED DCOILBRENTEU, GASDESW | daily, weekly |
| `consumer_sentiment.csv`, `retail_sales_usd_m.csv` | FRED UMCSENT, RSXFS | monthly |
| `gscpi.csv` | NY Fed Global Supply Chain Pressure Index | monthly |
| `gdelt_*.csv` | GDELT DOC 2.0 timeline volume (coverage share) per shipping lane / Jordan economy | daily, trailing 24 months |

Each has a `.meta.json` sidecar with `fetched_at`, so freshness is honest. All REAL PUBLIC.

## priors/ — public priors for what an operator has not measured (`scripts/fetch_public_priors.py`)

| file | source | used for |
|---|---|---|
| `lpi.csv` | World Bank Logistics Performance Index, latest year per country | lead-time variability prior by supplier origin country (`domain/priors.lead_time_cv_prior`), until 8+ receipts exist |
| `ers_lafa_loss.csv` | USDA ERS Loss-Adjusted Food Availability, per-commodity loss shares at each stage | perishability prior by commodity (`domain/priors.decay_rate_prior`), until write-offs are measured |

The mappings from index to parameter are ASSUMED and documented in `domain/priors.py`; every prior carries a provenance and is reported wherever it is in use. Both REAL PUBLIC.

## What these data cannot do

They are aggregate. No public source publishes SKU-level or supplier-level
order and fill records for any distributor, so the cross-section of any
simulated operator stays synthetic, and an arrival shortfall is a **proxy**
for a fill rate, never a measurement of one: tonnage landed is observable,
tonnage ordered is not.

## Classification of every dataset and artifact in this repository

| artifact | class |
|---|---|
| `data/external/fred/*.csv` | REAL PUBLIC (US Census via FRED, public domain) |
| `data/external/portwatch/*.csv` | REAL PUBLIC (IMF PortWatch, open data) |
| `data/external/indicators/*.csv` | REAL PUBLIC (FRED, NY Fed, GDELT) |
| `data/external/priors/*.csv` | REAL PUBLIC (World Bank, USDA ERS); parameter mappings ASSUMED |
| `validation/commercial/real_data.py` route shock panel | DERIVED FROM REAL PUBLIC (arrival-shortfall proxy; not a fill rate) |
| `docs/reports/evidence/real_validation/*` | DERIVED FROM REAL PUBLIC (backtest outputs on the real demand path; cross-section synthetic) |
| `synthetic/fmcg/distributor_sim.py` output, `artifacts/fmcg_*.json` | SYNTHETIC CALIBRATED (public benchmarks shape the parameters) |
| `synthetic/generator.py`, `synthetic/realistic_operator_sim.py` output | SYNTHETIC CALIBRATED (USDA ERS, Wallace Center, Indiana hub volumes) |
| `synthetic/commercial/*` (Project B v1/v2, Project C) | SYNTHETIC CALIBRATED |
| `data/samples/*` | SYNTHETIC ILLUSTRATIVE |
| `db/seeds/*` | SYNTHETIC ILLUSTRATIVE (dimension seeds) |

No artifact in this repository is a real operator's records.

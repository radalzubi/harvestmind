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
| `validation/commercial/real_data.py` route shock panel | DERIVED FROM REAL PUBLIC (arrival-shortfall proxy; not a fill rate) |
| `docs/reports/evidence/real_validation/*` | DERIVED FROM REAL PUBLIC (backtest outputs on the real demand path; cross-section synthetic) |
| `synthetic/fmcg/distributor_sim.py` output, `artifacts/fmcg_*.json` | SYNTHETIC CALIBRATED (public benchmarks shape the parameters) |
| `synthetic/generator.py`, `synthetic/realistic_operator_sim.py` output | SYNTHETIC CALIBRATED (USDA ERS, Wallace Center, Indiana hub volumes) |
| `synthetic/commercial/*` (Project B v1/v2, Project C) | SYNTHETIC CALIBRATED |
| `data/samples/*` | SYNTHETIC ILLUSTRATIVE |
| `db/seeds/*` | SYNTHETIC ILLUSTRATIVE (dimension seeds) |

No artifact in this repository is a real operator's records.

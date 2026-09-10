"""Fetch and cache the public leading indicators the adaptive engine reads.

Every source is keyless and public. Cached CSVs are committed so results are
reproducible without re-hitting the APIs; re-run this script to refresh.
Each cache carries a `fetched_at` sidecar so freshness is honest.

  FRED (St. Louis Fed CSV endpoint, no key)
    TSIFRGHT      Freight Transportation Services Index (monthly)
    DCOILBRENTEU  Brent crude, USD/bbl (daily)
    GASDESW       US diesel retail price, USD/gal (weekly)
    UMCSENT       Consumer sentiment (monthly)
    RSXFS         Retail sales ex food services, USD m (monthly)
  NY Fed  GSCPI  Global Supply Chain Pressure Index (monthly, xlsx)
  GDELT   DOC 2.0 timelinevol: share of global news coverage matching a query
          (daily). Rate limit one request per five seconds.
  IMF PortWatch chokepoints and ports: scripts/fetch_real_data.py (already cached)
"""
from __future__ import annotations

import csv
import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "external" / "indicators"
FRED = {"TSIFRGHT": "freight_index", "DCOILBRENTEU": "brent_usd", "GASDESW": "diesel_usd",
        "UMCSENT": "consumer_sentiment", "RSXFS": "retail_sales_usd_m"}
GSCPI_URL = "https://www.newyorkfed.org/medialibrary/research/interactives/gscpi/downloads/gscpi_data.xlsx"
GDELT_QUERIES = {
    "red_sea_shipping": '(Houthi OR "Red Sea" OR "Bab el-Mandeb") shipping',
    "hormuz_shipping": '("Strait of Hormuz" OR Hormuz) shipping',
    "suez_shipping": '("Suez Canal") shipping',
    "jordan_economy": 'Jordan (economy OR inflation OR fuel OR strike)',
}


def _stamp(name: str, source: str, url: str, rows: int) -> None:
    (OUT / f"{name}.meta.json").write_text(json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(), "source": source, "url": url, "rows": rows,
        "provenance": "REAL_PUBLIC"}, indent=1))


def fetch_fred(sid: str, name: str) -> int:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    rows = [(d, v) for d, v in csv.reader(io.StringIO(r.text)) if d != "observation_date" and v not in ("", ".")]
    with (OUT / f"{name}.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "value"])
        w.writerows(rows)
    _stamp(name, f"FRED {sid}", url, len(rows))
    return len(rows)


def fetch_gscpi() -> int:
    import pandas as pd
    r = requests.get(GSCPI_URL, timeout=60)
    r.raise_for_status()
    # The file is served as .xlsx but is a legacy .xls; let pandas sniff, fall back to xlrd.
    try:
        xl = pd.read_excel(io.BytesIO(r.content), sheet_name=None, header=None)
    except ValueError:
        xl = pd.read_excel(io.BytesIO(r.content), sheet_name=None, header=None, engine="xlrd")
    rows: list = []
    for _sheet, df in xl.items():                      # the data sheet has "Date, GSCPI" rows like 31-Jan-1998
        for _, row in df.iterrows():
            vals = row.tolist()
            if len(vals) < 2 or vals[1] != vals[1]:
                continue
            d = pd.to_datetime(vals[0], errors="coerce")
            if d is pd.NaT or d != d:
                continue
            try:
                rows.append((pd.Timestamp(d).strftime("%Y-%m-%d"), float(vals[1])))
            except (TypeError, ValueError):
                continue
        if rows:
            break
    rows = sorted(set(rows))
    with (OUT / "gscpi.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "value"])
        w.writerows(rows)
    _stamp("gscpi", "NY Fed GSCPI", GSCPI_URL, len(rows))
    return len(rows)


def fetch_gdelt(name: str, query: str, timespan: str = "24m") -> int:
    url = ("https://api.gdeltproject.org/api/v2/doc/doc?query=" + requests.utils.quote(query)
           + f"&mode=timelinevol&timespan={timespan}&format=json")
    data: dict[str, Any] = {}
    for _attempt in range(5):
        time.sleep(6)                                   # GDELT: one request per five seconds, hard limit
        r = requests.get(url, timeout=60)
        if r.status_code == 429:
            continue
        r.raise_for_status()
        try:
            data = r.json()
            break
        except ValueError:                              # rate-limit text with a 200 status
            continue
    else:
        raise RuntimeError("GDELT rate limit persisted")
    series = data.get("timeline", [{}])[0].get("data", [])
    rows = [(x["date"][:8], float(x["value"])) for x in series]
    rows = [(f"{d[:4]}-{d[4:6]}-{d[6:8]}", v) for d, v in rows]
    with (OUT / f"gdelt_{name}.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "value"])
        w.writerows(rows)
    _stamp(f"gdelt_{name}", "GDELT DOC 2.0 timelinevol", url, len(rows))
    time.sleep(6)
    return len(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    status: dict = {}
    for sid, name in FRED.items():
        try:
            status[name] = fetch_fred(sid, name)
        except Exception as exc:  # noqa: BLE001
            status[name] = f"FAILED {type(exc).__name__}: {exc}"
    try:
        status["gscpi"] = fetch_gscpi()
    except Exception as exc:  # noqa: BLE001
        status["gscpi"] = f"FAILED {type(exc).__name__}: {exc}"
    for name, q in GDELT_QUERIES.items():
        try:
            status[f"gdelt_{name}"] = fetch_gdelt(name, q)
        except Exception as exc:  # noqa: BLE001
            status[f"gdelt_{name}"] = f"FAILED {type(exc).__name__}: {exc}"
    for k, v in status.items():
        print(f"{k:28s} {v}")
    return 0 if all(isinstance(v, int) for v in status.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

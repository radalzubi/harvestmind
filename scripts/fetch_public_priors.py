"""Fetch public statistics that serve as PRIORS when an operator's own
history is thin. Everything here is keyless and public, cached with a
fetch stamp, and every derived prior carries provenance PUBLIC_BENCHMARK
with the mapping documented as ASSUMED. Measured operator data always
overrides a prior.

  World Bank Logistics Performance Index (LP.LPI.OVRL.XQ, 1..5 by country)
    -> lead-time variability prior by origin country
  USDA ERS Loss-Adjusted Food Availability (per-commodity loss shares)
    -> perishability / shrink prior by commodity
"""
from __future__ import annotations

import csv
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "external" / "priors"
LPI_URL = "https://api.worldbank.org/v2/country/all/indicator/LP.LPI.OVRL.XQ?format=json&per_page=2000&date=2018:2023"


def _stamp(name: str, source: str, url: str, rows: int) -> None:
    (OUT / f"{name}.meta.json").write_text(json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(), "source": source, "url": url, "rows": rows,
        "provenance": "REAL_PUBLIC"}, indent=1))


def fetch_lpi() -> int:
    r = requests.get(LPI_URL, timeout=60)
    r.raise_for_status()
    data = r.json()[1]
    latest: dict = {}
    for row in data:
        if row["value"] is None or not row["countryiso3code"]:
            continue
        iso, year, val = row["countryiso3code"], int(row["date"]), float(row["value"])
        if iso not in latest or year > latest[iso][1]:
            latest[iso] = (row["country"]["value"], year, val)
    with (OUT / "lpi.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["iso3", "country", "year", "lpi"])
        for iso, (name, year, val) in sorted(latest.items()):
            w.writerow([iso, name, year, val])
    _stamp("lpi", "World Bank LPI overall score", LPI_URL, len(latest))
    return len(latest)


def fetch_ers_lafa(urls: dict) -> int:
    """urls: name -> xlsx URL of an ERS loss-adjusted availability workbook.
    Extracts, per commodity sheet, the loss shares at each stage from the
    header block (primary->retail, retail->consumer, consumer level)."""
    import pandas as pd
    rows = []
    for group, url in urls.items():
        r = requests.get(url, timeout=90, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        try:
            xl = pd.read_excel(io.BytesIO(r.content), sheet_name=None, header=None)
        except ValueError:
            xl = pd.read_excel(io.BytesIO(r.content), sheet_name=None, header=None, engine="xlrd")
        for sheet, df in xl.items():
            text = df.astype(str).apply(lambda s: " ".join(s.tolist()), axis=1).str.cat(sep=" ")
            if "loss" not in text.lower():
                continue
            found: dict = {}
            for i in range(min(len(df), 12)):
                for j in range(min(df.shape[1], 30)):
                    cell = str(df.iat[i, j]).lower()
                    if "loss from primary" in cell or "primary to retail" in cell:
                        found["primary_to_retail"] = (i, j)
                    if "loss from retail" in cell or "retail/institutional to consumer" in cell:
                        found["retail_to_consumer"] = (i, j)
                    if "consumer level" in cell and "loss" in cell:
                        found["consumer"] = (i, j)
            if not found:
                continue
            # the percentage sits in the first numeric row below the header block
            vals: dict = {}
            for key, (i, j) in found.items():
                for k in range(i + 1, min(len(df), i + 8)):
                    try:
                        v = float(str(df.iat[k, j]).replace("%", ""))
                    except ValueError:
                        continue
                    if 0 <= v <= 100:
                        vals[key] = v / 100.0 if v > 1.0 else v
                        break
            if vals:
                rows.append({"group": group, "commodity": sheet, **vals})
    with (OUT / "ers_lafa_loss.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["group", "commodity", "primary_to_retail", "retail_to_consumer", "consumer"])
        w.writeheader()
        w.writerows(rows)
    _stamp("ers_lafa_loss", "USDA ERS Loss-Adjusted Food Availability", "; ".join(urls.values()), len(rows))
    return len(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print("lpi", fetch_lpi())
    urls = {a.split("=", 1)[0]: a.split("=", 1)[1] for a in sys.argv[1:] if "=" in a}
    if urls:
        print("ers_lafa_loss", fetch_ers_lafa(urls))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

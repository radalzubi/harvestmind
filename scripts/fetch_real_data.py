"""Re-fetch the public series under data/external/.

Both sources are open and unauthenticated. Network calls go through curl
rather than urllib because the bundled Python on macOS ships without a
usable CA bundle and fails certificate verification against both hosts.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRED = ROOT / "data" / "external" / "fred"
PORT = ROOT / "data" / "external" / "portwatch"

FRED_SERIES = [
    "S4244SM144NCEN", "S4244SM144SCEN", "MRTSSM445USN", "MRTSSM4451USN",
    "RETAILIRSA", "WHLSLRIRSA", "WHLSLRIRNSA", "WHLSLRIMSA", "WHLSLRSMSA",
    "TOTBUSIRNSA", "CUSR0000SAF11", "WPU02",
]
ARC = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services"
CHOKE = f"{ARC}/Daily_Chokepoints_Data/FeatureServer/0/query"
PORTS = f"{ARC}/Daily_Ports_Data/FeatureServer/0/query"
PORT_IDS = {
    "port19": "Aqaba", "port518": "Jeddah", "port1341": "Umm Qasr",
    "port26": "Latakia", "port73": "Ashdod", "port294": "Djibouti",
    "port744": "Jebel Ali", "port2031": "King Abdullah Port",
}
CHOKE_FIELDS = [
    "date", "year", "month", "day", "portid", "portname", "n_container",
    "n_dry_bulk", "n_general_cargo", "n_roro", "n_tanker", "n_cargo",
    "n_total", "capacity_container", "capacity_dry_bulk",
    "capacity_general_cargo", "capacity_roro", "capacity_tanker",
    "capacity_cargo", "capacity",
]
PORT_FIELDS = [
    "date", "portid", "portname", "country", "portcalls_container",
    "portcalls_dry_bulk", "portcalls_general_cargo", "portcalls_tanker",
    "portcalls_cargo", "portcalls", "import_container", "import_dry_bulk",
    "import_general_cargo", "import_cargo", "import", "export",
]


def _curl(url: str, timeout: int = 120) -> str:
    p = subprocess.run(["curl", "-sL", "--max-time", str(timeout), url],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"curl failed ({p.returncode}) for {url[:110]}")
    return p.stdout


def _page(base: str, where: str, fields: list[str]) -> list[dict]:
    """Page an ArcGIS layer. It caps pages at 1000 whatever we ask for."""
    rows, offset = [], 0
    while True:
        url = (f"{base}?where={where}&outFields={','.join(fields)}"
               f"&returnGeometry=false&orderByFields=ObjectId"
               f"&resultOffset={offset}&resultRecordCount=1000&f=json")
        data = json.loads(_curl(url))
        feats = data.get("features", [])
        if not feats:
            return rows
        rows.extend(f["attributes"] for f in feats)
        offset += len(feats)


def _write(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {len(rows):>7,} rows -> {path.relative_to(ROOT)}")


def main() -> int:
    FRED.mkdir(parents=True, exist_ok=True)
    print("FRED")
    for sid in FRED_SERIES:
        body = _curl(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}",
                     timeout=40)
        if not body.startswith("observation_date"):
            print(f"  SKIP {sid}: unexpected response")
            continue
        (FRED / f"{sid}.csv").write_text(body)
        print(f"  {sid:<16} {len(body.splitlines()) - 1:>5} observations")

    print("PortWatch chokepoints")
    _write(PORT / "chokepoint_daily.csv", CHOKE_FIELDS,
           _page(CHOKE, "1%3D1", CHOKE_FIELDS))

    print("PortWatch regional ports")
    rows: list[dict] = []
    for pid, name in PORT_IDS.items():
        got = _page(PORTS, f"portid%3D%27{pid}%27", PORT_FIELDS)
        print(f"  {name:<22} {len(got):>6} daily rows")
        rows.extend(got)
    _write(PORT / "regional_ports_daily.csv", PORT_FIELDS, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())

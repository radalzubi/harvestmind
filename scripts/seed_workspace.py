"""Create or refresh an invited workspace with a short key and a logo.

    python scripts/seed_workspace.py --name NTDCO --sector commercial --code 839285 --logo /logos/ntdco.svg

Equivalent to one entry of HARVESTMIND_SEED_WORKSPACES, which the API also
applies at startup. The code is stored as a hash; the logo path is served
by the web app from web/public.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from infrastructure.operator_registry import OperatorRegistry  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--sector", default="commercial", choices=("commercial", "produce"))
    ap.add_argument("--code", required=True, help="at least 6 characters")
    ap.add_argument("--logo", default=None)
    a = ap.parse_args()
    reg = OperatorRegistry()
    rec = reg.find_by_name(a.name) or reg.create_operator(a.name, sector=a.sector)
    reg.set_access_code(rec.operator_id, a.code)
    reg.set_profile(rec.operator_id, display_name=a.name, logo_url=a.logo)
    print(f"{a.name}: workspace {rec.operator_id}, sector {a.sector}, key set, logo {a.logo or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

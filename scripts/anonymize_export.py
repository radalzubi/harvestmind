"""Anonymise ERP exports on the operator's own machine before sending them.

    python scripts/anonymize_export.py --secret "<your secret>" purchase_orders.csv receipts.csv ...

Writes ``<name>.anon.csv`` next to each file and prints what was hashed and
dropped. Keep the secret: it is the only way to map hashed ids back to
your real codes, and HarvestMind never sees it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion.anonymize import anonymize_csv_bytes  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--secret", required=True, help="a passphrase you keep; same one for every file")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    if len(a.secret) < 12:
        print("secret must be at least 12 characters", file=sys.stderr)
        return 2
    for f in a.files:
        p = Path(f)
        out, rep = anonymize_csv_bytes(p.read_bytes(), a.secret)
        dst = p.with_suffix(".anon.csv")
        dst.write_bytes(out)
        print(f"{p.name} -> {dst.name}: {rep.rows} rows; hashed {rep.hashed_columns}; dropped {rep.dropped_columns}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

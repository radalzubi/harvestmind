#!/usr/bin/env python3
"""Rotate a seeded workspace's access code on Fly without the value touching a shell command line, git or the terminal.

The startup seed (`infrastructure/seed_workspaces.py`) re-applies `HARVESTMIND_SEED_WORKSPACES` on every start, so the
secret is the controlling copy of a seeded workspace's access code: rotating anywhere else is overwritten at the next
boot. This script builds the new secret value (same name, sector and logo; a fresh random code of 24 URL-safe
characters), writes the code to a 0600 file for the owner to hand to the customer through the agreed channel, and
feeds the secret to `fly secrets import` on stdin. It prints neither value.

    python scripts/rotate_access_code.py --app zaad-api --name "<workspace name>" --sector commercial \
        --logo /logos/customer.jpg --out ~/.zaad-secrets/customer_access_code.txt

Then verify (the values never appear in the commands; the old code is read from wherever the owner keeps it):

    curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $(cat OLD_CODE_FILE)" https://<api>/me   # 401
    curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $(cat NEW_CODE_FILE)" https://<api>/me   # 200

Every seeded workspace must appear in the same secret: pass `--entry` once per additional workspace in the seed
format `name|sector|code|logo` (read from a file with `--entries-file`, never typed on the command line with a code).
"""
from __future__ import annotations

import argparse
import os
import secrets
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--app", required=True)
    ap.add_argument("--name", required=True, help="the workspace's registry name (exact)")
    ap.add_argument("--sector", default="commercial")
    ap.add_argument("--logo", default="")
    ap.add_argument("--out", required=True, help="0600 file that receives the new code")
    ap.add_argument("--entries-file", default=None, help="other seed entries to keep, one `name|sector|code|logo` per line")
    ap.add_argument("--length", type=int, default=18, help="random bytes; 18 → 24 characters")
    ap.add_argument("--dry-run", action="store_true", help="write the code file and print the fly command, do not run it")
    args = ap.parse_args(argv)

    for field in (args.name, args.sector, args.logo):
        if "|" in field or ";" in field:
            print("refused: '|' and ';' are the seed's delimiters", file=sys.stderr)
            return 3
    code = secrets.token_urlsafe(args.length)
    if len(code) < 12:
        print("refused: the code must be at least 12 characters", file=sys.stderr)
        return 3
    out = Path(args.out).expanduser()
    out.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(code + "\n")
    entries = [f"{args.name}|{args.sector}|{code}|{args.logo}"]
    if args.entries_file:
        for line in Path(args.entries_file).expanduser().read_text().splitlines():
            if line.strip():
                entries.append(line.strip())
    payload = "HARVESTMIND_SEED_WORKSPACES=" + ";".join(entries) + "\n"
    if args.dry_run:
        print(f"new code written to {out} (0600). Would run: fly secrets import -a {args.app}  (value on stdin, {len(entries)} entr{'y' if len(entries) == 1 else 'ies'})")
        return 0
    proc = subprocess.run(["fly", "secrets", "import", "-a", args.app], input=payload, text=True)
    if proc.returncode != 0:
        print("fly secrets import failed; the new code file is kept, the deployment is unchanged", file=sys.stderr)
        return proc.returncode
    print(f"seed secret replaced on {args.app}; the app restarts and applies the new code at start. New code: {out} (0600).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

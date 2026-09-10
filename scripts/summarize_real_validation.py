"""Collect every real-data validation run into one comparable table."""
from __future__ import annotations

import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "outputs" / "real_validation"
ROW = re.compile(
    r"SP vs (naive order-up-to|fill-aware determ\.|cautious p90)\s+"
    r"median\s+([+-][\d.]+)%\s+(?:IQR \[([^\]]*)\]\s+)?wins (\d+)/(\d+)")
STRAT = re.compile(r"(binding|slack)\s+n=(\d+)\s+median\s+([+-][\d.]+)%\s+"
                   r"wins (\d+)/(\d+)")
FOLDS = re.compile(r"POOLED\s+\((\d+) admissible folds\)")


def parse(path: Path) -> dict | None:
    txt = path.read_text()
    if "POOLED" not in txt:
        return None
    pooled = txt[txt.index("POOLED"):]
    out: dict = {"folds": None, "edges": {}, "strata": {}}
    m = FOLDS.search(pooled)
    if m:
        out["folds"] = int(m.group(1))
    for lab, med, iqr, w, n in ROW.findall(pooled):
        out["edges"][lab] = (float(med), int(w), int(n), iqr or "")
    for k, n, med, w, tot in STRAT.findall(pooled):
        out["strata"][k] = (float(med), int(w), int(tot))
    m = re.search(r"service:\s+(.*)", pooled)
    if m:
        out["service"] = m.group(1).strip()
    return out


def main() -> int:
    files = sorted(OUT.glob("*.txt"))
    if not files:
        print("no results in outputs/real_validation/")
        return 1
    print("\n" + "=" * 92)
    print("REAL-DATA VALIDATION SUMMARY — every run, one table")
    print("=" * 92)
    print(f"{'run':<22}{'folds':>7}{'vs naive':>11}{'vs det':>10}"
          f"{'vs p90':>10}{'binding':>11}{'slack':>10}{'det wins':>11}")
    for f in files:
        r = parse(f)
        if not r:
            continue
        e = r["edges"]

        def g(k):
            return f"{e[k][0]:+.2f}%" if k in e else "-"
        det = e.get("fill-aware determ.")
        wins = f"{det[1]}/{det[2]}" if det else "-"
        b = r["strata"].get("binding")
        s = r["strata"].get("slack")
        print(f"{f.stem:<22}{r['folds'] or 0:>7}"
              f"{g('naive order-up-to'):>11}{g('fill-aware determ.'):>10}"
              f"{g('cautious p90'):>10}"
              f"{(f'{b[0]:+.2f}%' if b else '-'):>11}"
              f"{(f'{s[0]:+.2f}%' if s else '-'):>10}{wins:>11}")
    print("=" * 92)
    print("binding = shortage above 20% of the baseline's cost; slack = an easy")
    print("month where holding dominates. Stratum is set by the BASELINE's cost")
    print("split, never by the stochastic policy's own outcome.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Final P1 closure: compare a rolling-benchmark record produced under the cycle continuation with the
authoritative pass-L record (`horizon52_tAonly`). ZAAD rows come from the new tag; comparator rows from
the new tag when present, else from the base record (the rule policies do not depend on the planner's
terminal basis). Per fixture: delta at 52 on the declared landed-cost continuation valuation (new / base), stability 40..52,
service, average and terminal inventory, first material lot, order count and cadence per seed, statuses,
ownership counts, wall-clock p50 / p95 / max per review.

usage: PYTHONPATH=. python3 -m scripts.p1_cycle_compare <new_tag> [base_tag] [fixture,...]"""
from __future__ import annotations

import sys
from statistics import mean, median

from scripts.p1_fixtures import FIXTURES
from scripts.p1_horizon_benchmark import POLICIES, SEEDS, W_MAX
from scripts.p1_horizon_tables import EVID, load


def _percentile(xs: list[float], q: float) -> float:
    if not xs:
        return float("nan")
    xs = sorted(xs)
    k = min(len(xs) - 1, int(round(q * (len(xs) - 1))))
    return xs[k]


def _merged(new_by: dict, base_by: dict) -> dict:
    out = dict(base_by)
    out.update(new_by)
    return out


def _delta(by: dict, name: str, w: int, key: str = "continuation_landed") -> tuple[float, str]:
    base = {}
    for p in POLICIES:
        if p == "gated":
            continue
        if all((name, p, s) in by and by[name, p, s]["reviews_completed"] >= w for s in SEEDS):
            base[p] = mean(by[name, p, s]["curve"][w - 1][key] for s in SEEDS)
    if not base or not all((name, "gated", s) in by and by[name, "gated", s]["reviews_completed"] >= w for s in SEEDS):
        return float("nan"), "-"
    bp = min(base, key=base.get)
    z = mean(by[name, "gated", s]["curve"][w - 1][key] for s in SEEDS)
    return 100. * (z - base[bp]) / base[bp], bp


def _material(cell: dict) -> tuple[float | None, int, list[int]]:
    """First material lot (>= one period of mean demand), count of material orders, order periods."""
    mu = mean(sum(r["forecast_mean"].values()) for r in cell["per_review"]) if cell.get("per_review") else 0.
    lots = [(r["review"], sum(q for _, q in r["purchases"])) for r in cell.get("per_review", [])]
    material = [(t, q) for t, q in lots if q >= .5 * mu]
    return (material[0][1] if material else None), len(material), [t for t, _ in material]


def report(new_tag: str, base_tag: str, names: list[str]) -> None:
    _, new_by = load(EVID / "closure" / f"{new_tag}.jsonl")
    _, base_by = load(EVID / "closure" / f"{base_tag}.jsonl")
    by = _merged(new_by, base_by)
    print(f"new record {new_tag}; comparators from {base_tag} where absent; tolerance = fixture expectation")
    print(f"{'fixture':32s} {'d52 new':>8s} {'d52 base':>9s} {'stable':>6s} {'svc':>5s} {'avg inv':>8s} {'term':>6s} {'first lots':>22s} {'orders':>8s} {'p50':>5s} {'p95':>5s} {'max':>5s} statuses / owners")
    for name in names:
        if not all((name, "gated", s) in new_by for s in SEEDS):
            print(f"{name:32s} (incomplete)")
            continue
        tol = 100. * FIXTURES[name]["expect"]["zaad_not_worse"]
        d_new, bp = _delta(by, name, W_MAX)
        d_base, _ = _delta(base_by, name, W_MAX)
        ws = [w for w in range(40, W_MAX + 1)]
        ds = [_delta(by, name, w)[0] for w in ws]
        stable = all(abs(d - d_new) <= 1. and ((d <= tol) == (d_new <= tol)) for d in ds if d == d)
        cells = [new_by[name, "gated", s] for s in SEEDS]
        svc = mean(c["curve"][-1]["service"] for c in cells)
        inv = mean(c["curve"][-1]["avg_inventory_units"] for c in cells)
        term = mean(c["curve"][-1]["terminal_on_hand"] for c in cells)
        firsts, counts, cadences = [], [], []
        for c in cells:
            f, n, ts = _material(c)
            firsts.append(f)
            counts.append(n)
            cadences.append(round(mean(b - a for a, b in zip(ts, ts[1:])), 1) if len(ts) > 1 else None)
        walls = [r["wall_seconds"] for c in cells for r in c["per_review"]]
        statuses: dict[str, int] = {}
        owners: dict[str, int] = {}
        for c in cells:
            for r in c["per_review"]:
                statuses[str(r["status"])[:18]] = statuses.get(str(r["status"])[:18], 0) + 1
                owners[str(r["owner"])[:4]] = owners.get(str(r["owner"])[:4], 0) + 1
        verdict = "PASS" if d_new <= tol + 1e-9 else "FAIL"
        print(f"{name:32s} {d_new:+8.2f} {d_base:+9.2f} {str(stable):>6s} {svc:5.3f} {inv:8.0f} {term:6.0f} {str([round(f) if f else None for f in firsts]):>22s} {str(counts):>8s} {median(walls):5.1f} {_percentile(walls, .95):5.1f} {max(walls):5.1f} {verdict} vs {bp}; cadence {cadences}; {statuses}; {owners}")
        if all((name, "gated", s) in base_by for s in SEEDS):
            bcells = [base_by[name, "gated", s] for s in SEEDS]
            bfirst, bcount = [], []
            for c in bcells:
                f, n, _ = _material(c)
                bfirst.append(f)
                bcount.append(n)
            bwalls = [r["wall_seconds"] for c in bcells for r in c["per_review"]]
            print(f"{'  base ' + base_tag:32s} {'':8s} {'':9s} {'':6s} {mean(c['curve'][-1]['service'] for c in bcells):5.3f} {mean(c['curve'][-1]['avg_inventory_units'] for c in bcells):8.0f} {mean(c['curve'][-1]['terminal_on_hand'] for c in bcells):6.0f} {str([round(f) if f else None for f in bfirst]):>22s} {str(bcount):>8s} {median(bwalls):5.1f} {_percentile(bwalls, .95):5.1f} {max(bwalls):5.1f}")


if __name__ == "__main__":
    new_tag = sys.argv[1]
    base_tag = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else "horizon52_tAonly"
    names = [n for n in (sys.argv[3].split(",") if len(sys.argv) > 3 else []) if n] or list(FIXTURES)
    report(new_tag, base_tag, names)

"""Materialise the exact planning snapshot of a benchmark review (fixture, seed, review) by replaying
ZAAD on the fixture up to that review with `keep_requests`, and cache it as JSON so profiling and
equivalence experiments plan the identical request without replaying again.

usage: PYTHONPATH=. python3 -m scripts.p2_snapshots FIXTURE SEED REVIEW [...]   (e.g. M 41002 7 O 41001 6)
Snapshots: docs/zaad_full/evidence/p2/perf/snapshots/<fixture>_<seed>_r<review>.json"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from scripts.p2_fixtures import FIXTURES, build

SNAP = Path("docs/zaad_full/evidence/p2/perf/snapshots")


def snapshot_path(fixture: str, seed: int, review: int) -> Path:
    return SNAP / f"{fixture}_{seed}_r{review}.json"


def make_snapshot(fixture: str, seed: int, review: int) -> Path:
    from zaad.full.evaluation import long_truth
    from zaad.full.replay import replay
    from zaad.meio.baselines import register_replay_methods
    register_replay_methods()
    name = next(n for n in FIXTURES if n.split("_")[0] == fixture or n == fixture)
    initial = build(name, seed)
    H = initial.horizon
    reviews = review + 1
    segments = -(-(reviews - 1 + H) // H)
    truth = long_truth(initial, seed + 10000, segments * H)
    kept: list = []
    started = time.time()
    out = replay(initial, truth, reviews, "gated", keep_requests=kept, rolling=True)
    SNAP.mkdir(parents=True, exist_ok=True)
    for k in range(review + 1):
        # every earlier review of the same replay is a free, equally exact snapshot
        snapshot_path(fixture, seed, k).write_text(kept[k].model_dump_json())
    path = snapshot_path(fixture, seed, review)
    meta = {"fixture": name, "seed": seed, "review": review, "status": out["status"], "seconds_to_materialise": round(time.time() - started, 1),
            "review_wall_seconds": out["reviews"][review].get("wall_seconds") if out.get("reviews") and len(out["reviews"]) > review else None,
            "state": (out["reviews"][review].get("orchestration") or {}).get("state") if out.get("reviews") and len(out["reviews"]) > review else None}
    path.with_suffix(".meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta))
    return path


def main() -> int:
    args = sys.argv[1:]
    for i in range(0, len(args), 3):
        make_snapshot(args[i], int(args[i + 1]), int(args[i + 2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Summarise an M5 stage with the FreshRetailNet summarizer's tables and series-level paired statistics.

    python -m scripts.m5_summarize --stage fifty_corrected [--out docs/remodel/evidence/m5]

M5 has one demand track (observed sales), so the `track` column is constant; everything else (continuation and
realized cost, service, inventory, provenance, completion, paired bootstrap, strata, failures) is shared code.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import frn_summarize as S

RESULTS_ROOT = Path("data/public/m5/results")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--out", default="docs/remodel/evidence/m5")
    args = ap.parse_args()
    S.RESULTS_ROOT = RESULTS_ROOT
    rows = S.load_rows(args.stage)
    for r in rows:                                   # the FRN summarizer keys series by (store_id, product_id); M5 series ids are strings
        r.setdefault("track", "observed")
        r.setdefault("store_id", (r.get("series_id") or "").rsplit("_", 3)[-3] if r.get("series_id") else None)
        r.setdefault("item_id", r.get("series_id"))
        r.setdefault("product_id", r.get("item_id"))
        r.setdefault("stockout_class", r.get("volatility_class"))
        r.setdefault("regularity_class", r.get("intermittency_class"))
        r.setdefault("promo_class", r.get("cat_id"))
    manifest = json.loads((RESULTS_ROOT / args.stage / "run_manifest.json").read_text())
    table, pairs, strat, fails = S.policy_table(rows), S.paired(rows), S.strata(rows), S.failures(rows)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"RESULTS_{args.stage}.json").write_text(json.dumps({"run_manifest": manifest, "policy_table": table, "paired": pairs, "strata": strat, "failures": fails},
                                                                indent=1, default=str) + "\n")
    md = S.markdown(args.stage, table, pairs, fails, manifest).replace("# FreshRetailNet pilot results", "# Walmart M5 (Experiment A) results", 1)
    md = md.replace("Every figure is a modelled index under declared SYNTHETIC supply and normalized-unit economics",
                    "Every figure is a modelled dollar-of-shelf-price index under declared SYNTHETIC supply and economics (the classes volume / volatility / intermittency / category stand in the strata columns)")
    (out / f"RESULTS_{args.stage}.md").write_text(md)
    print(f"wrote {out / f'RESULTS_{args.stage}.md'}: {len(rows)} rows, {sum(1 for r in rows if r.get('status') == 'COMPLETE')} complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Insert measured closed-loop results into the validation report.

Reads artifacts/fmcg_counterfactuals_rolling.json and replaces the
<!-- ROLLING_TABLE --> marker (or a previously inserted table) in
docs/validation/COMMERCIAL_MODEL_VALIDATION.md. The report never carries a
number that was typed in.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "validation" / "COMMERCIAL_MODEL_VALIDATION.md"
JSON = ROOT / "artifacts" / "fmcg_counterfactuals_rolling.json"
BEGIN, END = "<!-- ROLLING_TABLE_BEGIN -->", "<!-- ROLLING_TABLE_END -->"


def build() -> str:
    d = json.load(open(JSON))
    cfg = d["config"]
    lines = [BEGIN,
             f"Configuration: seeds {cfg['seeds']}, run {cfg['run_periods']} periods, re-plan every "
             f"{cfg['review']}, horizon {cfg['horizon']}, train {cfg['train']}, scenarios {cfg['scenarios']}, "
             f"opening cover {cfg['cover_weeks']:.1f} wk, warehouse cap {cfg['warehouse_cap_weeks']} wk, "
             f"SLA target {cfg['sla_target']}. Elapsed {d['elapsed_s']} s.", "",
             "| archetype | SP vs deterministic | win | SP vs order-up-to | SP vs min/max | SP vs naive | **SELECTED vs deterministic** | service SP / det / OUT | selections | solver failures |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for name, r in d["archetypes"].items():
        e = r["edge_vs"]
        sv = r["service"]
        se = r["selected_edge_vs_deterministic"]

        def g(k):
            return f"{e[k].get('median', float('nan')):+.2f}%"
        lines.append(f"| {name} | {g('deterministic_sp')} | {e['deterministic_sp'].get('win_rate', 0):.0%} | "
                     f"{g('order_up_to')} | {g('min_max')} | {g('naive_forecast')} | "
                     f"**{se.get('median', float('nan')):+.2f}%** (win {se.get('win_rate', 0):.0%}) | "
                     f"{sv['stochastic_sp']:.1%} / {sv['deterministic_sp']:.1%} / {sv['order_up_to']:.1%} | "
                     f"{r['selections']} | {r['solver_failures']} |")
    lines += ["", "Edges are median percentage cost reductions over 3 seeded 40-week runs; win is the share "
                  "of runs where the stochastic optimizer's cost was lower. Costs are holding + lost margin + "
                  "disposal + SLA penalty in the domain's economics.", END]
    return "\n".join(lines)


def main() -> int:
    if not JSON.exists():
        print("no rolling results yet")
        return 1
    doc = DOC.read_text()
    table = build()
    if BEGIN in doc and END in doc:
        doc = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), table, doc, flags=re.S)
    elif "<!-- ROLLING_TABLE -->" in doc:
        doc = doc.replace("<!-- ROLLING_TABLE -->", table)
    else:
        print("marker not found")
        return 1
    DOC.write_text(doc)
    print("validation report updated with", len(json.load(open(JSON))["archetypes"]), "archetypes")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Read-only analysis of frozen policy evidence; no policy or threshold changes."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import median
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_zaad_benchmark import build_case, holdout_paths, source_hash  # noqa: E402
from zaad.engine import POLICIES, prepare, settle  # noqa: E402

EVIDENCE = ROOT / "docs/zaad_next/evidence"


def main():
    frozen = json.loads((EVIDENCE / "preregistered_manifest.json").read_text())
    if frozen["source_sha256"] != source_hash():
        raise SystemExit("Policy source differs from frozen evidence")
    rows = [json.loads(line) for line in (EVIDENCE / "holdout_runs.jsonl").read_text().splitlines()]
    aggregate = json.loads((EVIDENCE / "holdout_summary.json").read_text())
    expected = len(frozen["cells"]) * len(frozen["holdout_seeds"]) * len(frozen["baselines"])
    assert len(rows) == expected == 3000
    assert len({(r["cell"], r["seed"], r["baseline"]) for r in rows}) == len(rows)
    bykey = {(r["cell"], r["seed"], r["baseline"]): r for r in rows}
    gated = [r for r in rows if r["baseline"] == "zaad_gated"]
    lines = [
        "# ZAAD frozen synthetic benchmark results",
        "",
        "**Verdict: NEEDS FURTHER ENGINEERING.** Runnable decision prototype; not deployment-ready, not real-operator validation, not Oracle parity.",
        "",
        "75 cells × 5 untouched future seeds × 8 baseline/controller rows = **3,000 individual runs**. "
        "375 distinct operator/future-path cases—not 3,000 independent operators. The normal core is an 8-target × 5-stock factorial; additional factors are one-at-a-time, not an exhaustive cross-product.",
        "",
        f"Frozen source SHA-256: `{source_hash()}`. No policy or threshold retuning after this holdout.",
        "",
        "[Every run CSV](evidence/holdout_runs.csv) · [JSONL](evidence/holdout_runs.jsonl) · "
        "[Preregistration](evidence/preregistered_manifest.json) · [Aggregates](evidence/holdout_summary.json)",
        "",
        "## Gated controller, including retained incumbent and abstentions",
        "",
        "Savings are percent of this 12-period modeled economic-cost ledger, **not percent of revenue or annual spend**. "
        "An abstention is replayed as the incumbent for policy evaluation and explicitly marked; it is not a candidate win. "
        "A service breach means at least one SKU misses its requested realized unit-fill target.",
        "",
        "| Family | Cases | Median saving | Range | Cost losses | Service breaches | Changes / abstentions |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for a in aggregate["aggregates"]:
        if a["baseline"] == "zaad_gated":
            lines.append(
                f"| {a['family']} | {a['n']} | {a['median_pct']:.2f}% | {a['range_pct'][0]:.2f}% to {a['range_pct'][1]:.2f}% | {a['losses']} | {a['service_breaches']} | {a['changes']} / {a['abstentions']} |"
            )
    lines += [
        "",
        "## Stronger baseline comparisons",
        "",
        "All methods see the same histories, known pipeline and route constraints. 'Expected/CVaR search' is a finite closed-loop policy family, "
        "not the legacy Pyomo stochastic program or a globally optimal stochastic solution. The deterministic baseline searches that same family on mean paths.",
        "",
        "| Family | Baseline | Median vs incumbent | Range | Losses | Service breaches |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for a in aggregate["aggregates"]:
        if a["family"] in ("normal", "disruption"):
            lines.append(
                f"| {a['family']} | {a['baseline']} | {a['median_pct']:.2f}% | {a['range_pct'][0]:.2f}% to {a['range_pct'][1]:.2f}% | {a['losses']}/{a['n']} | {a['service_breaches']}/{a['n']} |"
            )
    lines += [
        "",
        "### Controller versus competent rules, paired on identical realized paths",
        "",
        "| Comparator | Median saving | Range | Losses |",
        "|---|---:|---:|---:|",
    ]
    for baseline in ("base_stock", "service_target", "expected_search", "cvar_search"):
        values = []
        for r in gated:
            if r["family"] == "control":
                continue
            b = bykey[(r["cell"], r["seed"], baseline)]
            values.append(100 * (b["total_cost"] - r["total_cost"]) / b["total_cost"])
        lines.append(
            f"| {baseline} | {median(values):.2f}% | {min(values):.2f}% to {max(values):.2f}% | {sum(v < -1e-8 for v in values)}/{len(values)} |"
        )
    lines += [
        "",
        "## Disruption, recovery and signal cells individually",
        "",
        "| Cell / variant | Median saving | Range | Service breaches | Changes / abstentions |",
        "|---|---:|---:|---:|---:|",
    ]
    for cell in frozen["cells"]:
        if cell["family"] not in ("disruption", "signal_ablation", "control"):
            continue
        rr = [r for r in gated if r["cell"] == cell["cell"]]
        ss = [r["savings_vs_incumbent_pct"] for r in rr]
        lines.append(
            f"| {cell['cell']} / {cell['variant']} | {median(ss):.2f}% | {min(ss):.2f}% to {max(ss):.2f}% | {sum(r['service_breach'] for r in rr)}/5 | {sum(r['status'] == 'RECOMMEND_FOR_REVIEW' for r in rr)} / {sum(r['status'] == 'ABSTAIN' for r in rr)} |"
        )
    lines += [
        "",
        "## Interpretation guardrails",
        "",
        "- False-news alarms do not change physical-risk inputs or actions relative to the matching no-signal input. A nonzero saving in that cell is normal inventory optimization, not a news benefit.",
        "- Port/AIS/freight/weather/combined cells currently inject the same synthetic physical-severity contract. Equal results are wiring controls, not independent provider-value measurements. News-only has no physical effect. No paid AIS or freight data was evaluated.",
        "- The late-news fixture makes physical evidence available first. News has no modeled incremental decision role, so it cannot establish news warning lead or value.",
        "- Model stress and final truth differ deliberately: stress predicts +ceil(3s) lead and 30%×s fill loss; realized disruption uses +ceil(4s) lead and 35%×s fill loss, ending at review7. These are assumptions, not fitted causal effects.",
        "- Gate failures in final service are real evidence of model misspecification. Independent Monte Carlo confirmation samples the same assumed model; it does not protect against that misspecification.",
        "- No 100% service guarantee, real-data ROI, measured TAM, production readiness, calibrated event probability or commercial no-harm claim follows.",
        "- No legacy report is overwritten. Prior service failure mechanism is reproduced separately in CURRENT_STATE_AUDIT.md.",
    ]
    (ROOT / "docs/zaad_next/BENCHMARK_RESULTS.md").write_text("\n".join(lines) + "\n")
    components = ("consumed_cost", "freight_premium", "holding", "disposal", "lost_sales_revenue")
    losses = []
    for r in rows:
        if r["savings_vs_incumbent_pct"] >= -1e-8:
            continue
        b = bykey[(r["cell"], r["seed"], "incumbent")]
        delta = {k: r[k] - b[k] for k in components}
        losses.append(
            {
                "cell": r["cell"],
                "variant": r["variant"],
                "family": r["family"],
                "seed": r["seed"],
                "baseline": r["baseline"],
                "selected_policy": r["selected_policy"],
                "saving_pct": r["savings_vs_incumbent_pct"],
                "cost_increase": r["total_cost"] - b["total_cost"],
                "dominant_accounting_component": max(delta, key=delta.get),
                "service_breach": r["service_breach"],
                **{k + "_delta": v for k, v in delta.items()},
                "causal_attribution": "not isolated; accounting decomposition only",
            }
        )
    with (EVIDENCE / "loss_diagnostics.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(losses[0]))
        writer.writeheader()
        writer.writerows(losses)
    traces = []
    for cell in frozen["cells"]:
        if cell["variant"] not in ("recovery", "moderate", "false_alarm", "already_protected"):
            continue
        for seed in frozen["holdout_seeds"]:
            req = build_case(cell, seed)
            f, c, _ = prepare(req)
            paths = holdout_paths(req, f, c, cell, seed)
            for name in ("incumbent", "zaad_gated"):
                saved = bykey[(cell["cell"], seed, name)]
                policy = next(p for p in POLICIES if p.name == saved["selected_policy"])
                replay = settle(req, f, c, policy, paths, 0)
                assert abs(replay["total_cost"] - saved["total_cost"]) < 1e-8
                traces.extend(
                    {
                        "cell": cell["cell"],
                        "variant": cell["variant"],
                        "seed": seed,
                        "baseline": name,
                        **t,
                    }
                    for t in replay["trace"]
                )
    with (EVIDENCE / "recovery_traces.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(traces[0]))
        writer.writeheader()
        writer.writerows(traces)
    print(
        json.dumps(
            {
                "runs": len(rows),
                "loss_rows": len(losses),
                "gated_losses": sum(r["savings_vs_incumbent_pct"] < -1e-8 for r in gated),
                "gated_service_breaches": sum(r["service_breach"] for r in gated),
                "trace_rows": len(traces),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

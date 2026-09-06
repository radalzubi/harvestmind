"""Preregistered synthetic holdout. No retuning or dropping failures after freeze.

Run --freeze after development checks, then --stage holdout. A source change
invalidates the frozen manifest. Output is every individual run, not a median-only claim.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from datetime import timedelta
import hashlib
import json
from pathlib import Path
from statistics import median
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from zaad.contracts import PlanningRequest  # noqa: E402
from zaad.demo import demo_request  # noqa: E402
from zaad.engine import (POLICIES, Policy, draw_paths, evaluate, plan, prepare, summary)  # noqa: E402
from zaad.signals import Signal  # noqa: E402

OUTPUT = ROOT / "docs/zaad_next/evidence"
TARGETS = [.85,.90,.93,.95,.97,.98,.99,.995]
COVERS = [.1,1.,2.,4.,7.]
HOLDOUT_SEEDS = [9101,9102,9103,9104,9105]
DEV_SEEDS = [8101]
BASELINES = ["incumbent", "base_stock", "service_target", "deterministic_constrained",
             "expected_search", "cvar_search", "route_aware", "zaad_gated"]


def cells() -> list[dict]:
    output = [{"family":"normal", "target":t, "cover":c, "variant":"stable"}
              for t in TARGETS for c in COVERS]
    for variant in ("seasonal", "intermittent20", "intermittent50", "promotion", "structural_shift",
                    "variable_supply", "long_lead", "short_fill", "high_margin", "low_margin",
                    "critical", "perishable", "misallocated", "small_scale", "large_scale"):
        output.append({"family":"normal_ofat", "target":.95,"cover":2.,"variant":variant})
    for variant in ("no_disruption", "early_warning", "mild", "moderate", "severe",
                    "recovery", "false_alarm", "late_news", "already_protected", "shared_route",
                    "closed_port", "no_alternative"):
        output.append({"family":"disruption", "target":.95,"cover":2.,"variant":variant})
    for feed in ("history_only", "port", "ais", "news", "freight", "weather", "combined"):
        output.append({"family":"signal_ablation", "target":.95,"cover":2.,"variant":feed})
    output.append({"family":"control", "target":.95,"cover":2.,"variant":"force_unit_fills"})
    return [{"cell":f"C{k:03d}", **c} for k,c in enumerate(output)]


def source_hash() -> str:
    paths = sorted((ROOT/"zaad").glob("*.py"))+[Path(__file__).resolve()]
    return hashlib.sha256(b"".join(p.name.encode()+p.read_bytes() for p in paths)).hexdigest()


def manifest() -> dict:
    return {"version":"zaad-benchmark-v1", "classification":"SYNTHETIC THROUGHOUT",
            "source_sha256":source_hash(), "cells":cells(), "holdout_seeds":HOLDOUT_SEEDS,
            "development_seeds":DEV_SEEDS, "baselines":BASELINES,
            "policies":[asdict(p) for p in POLICIES], "horizon":12,"selection_scenarios":24,
            "economics":"opening assets + accepted purchase - closing assets + premiums + hold + disposal + lost selling revenue",
            "holdout":"Independent future demand/supply generator, not selection scenarios. Five paths/cell.",
            "signal_warning":"Synthetic feed ablations are mechanistic tests; no real predictive feed value established.",
            "matrix_scope":"40 target-stock factorial cells plus one-factor stress cases; NOT all-factor cross-product",
            "rules":["all runs retained", "statistics.median", "same first-stage information and physical settlement",
                     "no retuning after final holdout", "fallback to incumbent recorded not counted as candidate win"]}


def build_case(cell: dict, seed: int) -> PlanningRequest:
    raw = demo_request(seed=seed+20000).model_dump(mode="json")
    rng = np.random.default_rng(seed+30000)
    variant = cell["variant"]
    means = {"A":100.,"B":40.}
    scale = .4 if variant == "small_scale" else 3. if variant == "large_scale" else 1.
    for item in raw["items"]:
        item["service_target"] = cell["target"]
        if variant == "high_margin":
            item["selling_price"] = item["base_cost"]*3
        if variant == "low_margin":
            item["selling_price"] = item["base_cost"]*1.1
        if variant == "critical" and item["id"] == "A":
            item["criticality"] = 10
            item["service_target"] = .99
        if variant == "perishable":
            item["shelf_life"] = 4
            item["disposal_per_unit"] = .1
    for lot in raw["inventory"]:
        cover = cell["cover"]
        if variant in ("recovery", "already_protected"):
            cover = 6
        if variant == "misallocated":
            cover = .2 if lot["item"] == "A" else 8
        lot["quantity"] = means[lot["item"]]*cover*scale
        if variant == "perishable":
            lot["expires_in"] = 3
    for row in raw["demand"]:
        mu = means[row["item"]]
        t = row["period"]
        if variant == "seasonal":
            row["quantity"] = max(0.,rng.normal(mu*(1+.35*np.sin(2*np.pi*t/52)),mu*.12))
        if variant in ("intermittent20","intermittent50"):
            probability = .2 if variant.endswith("20") else .5
            if rng.random() < probability:
                row["quantity"] = 0.
        row["quantity"] *= scale
    for delivery in raw["deliveries"]:
        delivery["ordered"] *= scale
        delivery["confirmed"] *= scale
        fill = (.8 if variant == "short_fill" else .97)
        sigma = .12 if variant == "variable_supply" else .015
        ratio = float(np.clip(rng.normal(fill,sigma),.1,1.))
        delivery["received"] = delivery["accepted"] = delivery["ordered"]*ratio
        if variant == "long_lead" and delivery["route"].endswith("main"):
            delivery["lead_periods"] = 4
        elif variant == "variable_supply":
            delivery["lead_periods"] = int(rng.choice([1,2,3,4]))
    for po in raw["pipeline"]:
        po["ordered"] *= scale
        po["expected_accepted"] *= scale
    for route in raw["routes"]:
        route["capacity"] *= scale
        if variant == "no_alternative" and route["id"].endswith("alt"):
            route["approved"] = False
    for edge in raw["edges"]:
        edge["capacity"] *= scale
        if variant == "shared_route":
            edge["failure_domains"] = ["PORT:EXAMPLE"]
        if variant == "closed_port" and edge["id"] == "ocean":
            edge["available"] = False
    raw["warehouse_capacity"] *= scale
    raw["review_budget"] *= scale
    raw["seed"] = seed+40000
    severity = {"early_warning":.25,"mild":.25,"moderate":.6,"severe":.9,
                "already_protected":.6,"shared_route":.6,"no_alternative":.6,
                "closed_port":.9,"false_alarm":.9,"late_news":.6}.get(variant,0.)
    if cell["family"] == "signal_ablation":
        severity = 0. if variant == "history_only" else .6
    raw["signals"] = []
    if severity or variant == "recovery":
        req = PlanningRequest.model_validate(raw)
        kind = "news" if variant in ("false_alarm","news") else "physical"
        if variant == "recovery":
            raw["prior_mode"] = "PROTECT"
        signal = Signal(id=f"synthetic-{variant}", provider=f"synthetic-{variant}",
                        entity_ids=("PORT:EXAMPLE",),kind=kind,
                        observed_at=req.as_of,published_at=req.as_of,ingested_at=req.as_of,
                        effective_at=req.as_of,valid_until=req.as_of+timedelta(days=7),
                        magnitude=severity,confidence=1.,direction="recovery" if variant == "recovery" else "deterioration",
                        source_url="https://example.com/explicitly-synthetic-feed",
                        syndication_key=f"synthetic-{variant}",adapter_version="synthetic.v1",
                        license_status="open_verified",availability_basis="synthetic_fixture")
        raw["signals"] = [signal.model_dump(mode="json")]
        if variant == "late_news":
            late = signal.model_copy(update={"id":"late-news", "kind":"news", "provider":"synthetic-news",
                "observed_at":req.as_of+timedelta(days=14),"published_at":req.as_of+timedelta(days=14),
                "ingested_at":req.as_of+timedelta(days=14),"effective_at":req.as_of+timedelta(days=14),
                "valid_until":req.as_of+timedelta(days=15),"syndication_key":"late-news"})
            raw["signals"].append(late.model_dump(mode="json"))
    raw["force_unit_fills"] = variant == "force_unit_fills"
    return PlanningRequest.model_validate(raw)


def holdout_paths(req: PlanningRequest, forecasts: dict, cards: list[dict], cell: dict, seed: int) -> dict:
    """Independent outcome generator; model assumptions do not serve as realized truth."""
    rng = np.random.default_rng(seed)
    v = cell["variant"]
    paths = {"demand":{}, "supply":{}, "card_timeline":{}}
    scale = .4 if v == "small_scale" else 3. if v == "large_scale" else 1.
    for sku,mu in (("A",100.),("B",40.)):
        values = np.maximum(0.,rng.normal(mu,mu*.12,size=(1,req.horizon)))
        if v == "seasonal":
            values *= 1+.35*np.sin(2*np.pi*np.arange(req.horizon)/52)
        if v in ("intermittent20","intermittent50"):
            values *= rng.random(values.shape) >= (.2 if v.endswith("20") else .5)
        if v in ("promotion","structural_shift"):
            values[:,3:6 if v=="promotion" else req.horizon] *= 1.5
        paths["demand"][sku] = values*scale
    intensity = {"early_warning":.5,"mild":.25,"moderate":.6,"severe":.9,
                 "already_protected":.6,"shared_route":.6,"no_alternative":.6,
                 "closed_port":.9,"late_news":.6}.get(v,0.)
    if cell["family"] == "signal_ablation":
        intensity = .6
    for card in cards:
        shape = (1,req.horizon)
        fill = np.clip(rng.normal(.8 if v=="short_fill" else .97,
                                 .12 if v=="variable_supply" else .015,size=shape),.1,1.)
        lead = np.full(shape,4 if v=="long_lead" and card["route"].endswith("main") else
                       2 if card["route"].endswith("main") else 1,dtype=int)
        if v == "variable_supply":
            lead = rng.integers(1,5,size=shape)
        exposed = card["route"].endswith("main") or v=="shared_route"
        if exposed and intensity:
            start = 2 if v=="early_warning" else 0
            fill[:,start:7] *= 1-.35*intensity
            lead[:,start:7] += int(np.ceil(4*intensity))
        paths["supply"][card["route"]] = {"fills":np.ones(shape) if req.force_unit_fills else fill,"leads":lead}
    # Information changes at recovery are visible only from that review onward.
    # Quantities/ETAs for unreceived booked POs remain private in settlement.
    for t in range(7,req.horizon):
        paths["card_timeline"][t] = [{**c,"severity":0.} for c in cards]
    return paths


def choose(request, forecasts, cards, paths, *, objective="mean_cost", risk=False):
    candidates = [Policy(p.name,p.buffer,p.alternative_share,risk) for p in POLICIES]
    if not risk:
        candidates = [p for p in candidates if p.alternative_share==0]
    scores = [(p,summary(request,evaluate(request,forecasts,cards,p,paths),p.name)) for p in candidates]
    feasible = [(p,s) for p,s in scores if s["service_feasible"] and s["physical_feasible"]]
    if not feasible:
        return POLICIES[0], "NO_FEASIBLE_CANDIDATE_KEEP_INCUMBENT"
    selected = min(feasible,key=lambda ps:ps[1][objective])[0]
    return selected,"MODEL_SELECTED"


def run_cell(cell: dict, seed: int) -> list[dict]:
    req = build_case(cell,seed)
    f,c,w = prepare(req)
    if w:
        raise RuntimeError(f"Invalid preregistered input: {cell}: {w}")
    training = draw_paths(req,f,c,req.seed)
    deterministic = draw_paths(req,f,c,req.seed,deterministic=True)
    selected = {"incumbent":(POLICIES[0],"INCUMBENT"), "base_stock":(POLICIES[1],"RULE")}
    selected["service_target"] = choose(req,f,c,training,objective="average_inventory_value")
    selected["deterministic_constrained"] = choose(req,f,c,deterministic)
    selected["expected_search"] = choose(req,f,c,training)
    selected["cvar_search"] = choose(req,f,c,training,objective="cvar90_cost",risk=True)
    selected["route_aware"] = choose(req,f,c,training,risk=True)
    report = plan(req)
    policy = next((p for p in POLICIES if p.name==report.selected_policy),POLICIES[0])
    selected["zaad_gated"] = (policy,report.status)
    # Truth is generated ONLY AFTER selection and confirmation finish.
    truth = holdout_paths(req,f,c,cell,seed)
    results = {}
    for name,(policy,status) in selected.items():
        r = evaluate(req,f,c,policy,truth)[0]
        r.pop("trace")
        r.update({**cell,"seed":seed,"baseline":name,"selected_policy":policy.name,
                  "status":status,"forecast_methods":{k:v["method"] for k,v in f.items()},
                  "input_fingerprint":report.input_fingerprint,"mode":report.mode})
        results[name]=r
    incumbent = results["incumbent"]
    for r in results.values():
        r["savings_vs_incumbent_pct"] = 100*(incumbent["total_cost"]-r["total_cost"])/incumbent["total_cost"]
        r["inventory_release_not_profit"] = incumbent["average_inventory_value"]-r["average_inventory_value"]
        r["service_breach"] = any(r["item_fill"][i.id]+1e-9<i.service_target for i in req.items)
        loss = r["total_cost"]>incumbent["total_cost"]+1e-7
        r["loss_classification"] = ("none" if not loss else "candidate_cost_service_tradeoff_or_forecast_misspecification")
        if loss and cell["family"] in ("disruption","signal_ablation"):
            r["loss_classification"] = "stress_mapping_horizon_or_alternative_cost"
        r["classification_status"] = "candidate mechanism, not isolated causal proof" if loss else "not a losing run"
        r["fallback_not_candidate_win"] = r["status"] in ("ABSTAIN","KEEP_INCUMBENT","NO_FEASIBLE_CANDIDATE_KEEP_INCUMBENT")
    return list(results.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze",action="store_true")
    parser.add_argument("--stage",choices=["development","holdout"],default="development")
    parser.add_argument("--limit",type=int)
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True,exist_ok=True)
    freeze = OUTPUT/"preregistered_manifest.json"
    if args.freeze:
        if freeze.exists():
            raise SystemExit("Manifest already frozen; do not overwrite a preregistration")
        freeze.write_text(json.dumps(manifest(),indent=2)+"\n")
        print(f"FROZEN {source_hash()}")
        return
    if args.stage=="holdout":
        frozen=json.loads(freeze.read_text())
        if frozen!=manifest() or args.limit:
            raise SystemExit("Holdout requires exact frozen source/config and complete grid")
    seeds=HOLDOUT_SEEDS if args.stage=="holdout" else DEV_SEEDS
    output=OUTPUT/f"{args.stage}_runs.jsonl"
    if output.exists():
        raise SystemExit("Evidence already exists; will not overwrite previous runs")
    all_rows=[]
    with output.open("x") as stream:
        for cell in cells()[:args.limit]:
            for seed in seeds:
                rows=run_cell(cell,seed)
                for row in rows:
                    stream.write(json.dumps(row,allow_nan=False)+"\n")
                stream.flush()
                all_rows.extend(rows)
            print(f"{cell['cell']} {cell['variant']}: {len(all_rows)} individual runs",flush=True)
    flat=OUTPUT/f"{args.stage}_runs.csv"
    with flat.open("x",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(all_rows[0]))
        writer.writeheader()
        for row in all_rows:
            writer.writerow({k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in row.items()})
    aggregates=[]
    for family in sorted({r["family"] for r in all_rows}):
        for baseline in BASELINES:
            rows=[r for r in all_rows if r["family"]==family and r["baseline"]==baseline]
            savings=[r["savings_vs_incumbent_pct"] for r in rows]
            aggregates.append({"family":family,"baseline":baseline,"n":len(rows),
                "median_pct":median(savings),"range_pct":[min(savings),max(savings)],
                "losses":sum(x < -1e-8 for x in savings),"service_breaches":sum(r["service_breach"] for r in rows),
                "abstentions":sum(r["status"]=="ABSTAIN" for r in rows),
                "changes":sum(r["status"]=="RECOMMEND_FOR_REVIEW" for r in rows)})
    (OUTPUT/f"{args.stage}_summary.json").write_text(json.dumps({"source_sha256":source_hash(),
                "total_runs":len(all_rows),"aggregates":aggregates},indent=2)+"\n")
    print(json.dumps(aggregates,indent=2))


if __name__=="__main__":
    main()

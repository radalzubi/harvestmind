# ZAAD — inventory and resilience decision prototype

**Engineering verdict: NEEDS FURTHER ENGINEERING.** This branch implements a runnable, isolated prototype, not the entire enterprise specification. No real operator has validated it, no automatic PO is possible, and final synthetic service failures prevent a deployment claim. Company: **ZAAD**, [zaadsupply.com](https://zaadsupply.com); repository name remains `radalzubi/harvestmind`.

## What works

Canonical JSON or CSV bundle → strict as-of snapshot → demand-candidate comparison → explicit route exposure → feasible closed-loop policy search → independent simulated confirmation → recommend for human review, retain incumbent, or abstain. The Next.js `/zaad` workspace displays the same API result across seven views; it does not substitute mock metrics for a failed solve.

The architecture skill led to an isolated modular-monolith boundary instead of replacing the legacy planning stack. The API-security skill influenced strict schemas, tenant matching, request/compute bounds, provider allowlists and fail-closed data handling.

```text
Operator snapshot ──> forecast candidates ──> common physical replay ──> service/cost frontier
Licensed signals ──> as-of/freshness filter ──> route-specific stress ──────────┘
Approved graph/quotes ──> hard feasible action set ────────────────────────────┘
                     selection + separate simulation confirmation
                         └─> human-review recommendation / abstention
```

## Run

From the repository root, with the existing Python environment installed:

```bash
python3 scripts/run_zaad_demo.py --case balanced --output /tmp/zaad-review.json
python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000
cd web
npm ci
npm run dev
```

Open `http://localhost:3000/zaad`. API: `GET /api/zaad/demo`, `GET /api/zaad/schema`, `POST /api/zaad/plan`. The CSV adapter is `zaad.intake.load_csv_bundle`; new operator data remains in the request, not any training database. Use `HARVESTMIND_ENV=pilot` and existing operator credentials before any non-local deployment. New recommendations are experimental, not the legacy `/fmcg` executable-plan path.

Explicit public-source example:

```bash
python3 scripts/run_zaad_demo.py --fetch-noaa --output /tmp/zaad-noaa-review.json
```

The saved run in `evidence/live_noaa_demo.json` fetched **193 actual NWS records**. It is **REAL-SIGNAL / SYNTHETIC-OPERATOR**, not a real shipment replay. The synthetic network has no asserted NWS-zone exposure; unmatched alerts correctly leave its routes unchanged. NOAA data is intended to be open and free for any purpose, subject to rate limits; official guidance requires an identifying User-Agent. [NWS API documentation](https://www.weather.gov/documentation/services-web-api).

## Evidence, not a headline-only median

- [Benchmark results](BENCHMARK_RESULTS.md): 3,000 individual rows, 375 operator/path cases, 75 cells, five held-out seeds, eight policies.
- [Failure analysis](FAILURE_ANALYSIS.md): 24 gated cost losses and 122 realized service breaches, including abstention/incumbent cases; no failures deleted.
- [Method and reproduction](BENCHMARK_METHOD.md): frozen source/config and independent final outcomes; no retuning.
- [Current-state audit](CURRENT_STATE_AUDIT.md): old service model deliberately withholds usable stock, plus production adapter chronology/gate issues.
- [Implementation status](IMPLEMENTATION_STATUS.md): all 53 phases, A–Q, and explicit enterprise/deployment gaps.

Normal core median saving is **0.35%** of modeled economic cost (range **0 to 1.46%**, 0/200 cost losses), with **33/200 service breaches**. Thirty are low-opening-stock cases where the controller abstains and the incumbent also misses the target. Normal stress/OFAT cases include losses down to **−8.79%**. Disruption median is **3.08%** (0 to 11.39%), but **35/60** service breaches. Against the competent base-stock rule across non-control cases, the gated controller's median is **−0.04%**, with 192/370 cost losses. This is not evidence of broad commercial superiority.

## Research and design

[Competitive baseline](COMPETITIVE_BASELINE.md) · [Sources and rights](DATA_SOURCE_AUDIT.md) · [Normal engine](NORMAL_ENGINE.md) · [Resilience engine](RESILIENCE_ENGINE.md) · [Route model](ROUTE_MODEL.md) · [News/signals](NEWS_SIGNAL_MODEL.md) · [Math](MATHEMATICAL_SPEC.md) · [Security](SECURITY_AND_DATA_GOVERNANCE.md) · [Pilot plan](PILOT_PLAN.md)

The commercial next step is a **read-only data/decision audit**, not performance-based production deployment. Investigate whether ordinary fill-aware inventory rules capture most normal value, then test whether route decisions add incremental value under actual constrained recourse. Broad MEIO, calibrated shipment ETA/censored lead models, persistent shadow workflow, transfers/substitution/cancellation and licensed AIS/FBX integration remain unimplemented or partial.

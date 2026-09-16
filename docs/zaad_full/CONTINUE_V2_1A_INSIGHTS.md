# CONTINUE HERE — V2.1A Insights, paused mid-release (2026-09-15, ~19:10 UTC)

> **Superseded 2026-09-16:** the release completed — PR #84 merged as `13dde49`, Fly v28 `canonical-13dde49`, tag `zaad-operating-product-v2.1a-runtime`. Kept as the record of the pause; read `CURRENT_SYSTEM.md` and the ledger's current-state table instead.

The laptop was shut down with V2.1A built, tested locally, pushed, and its PR open with CI running.
Nothing is merged, deployed or tagged yet. Resume from this file; do not rebuild what is here.

## Where things are

| item | value |
|---|---|
| branch | `feat/zaad-insights-canonical-connectivity`, head **`9c2cfc0`** (= `b882e0a` + this Markdown file; Markdown-only pushes do not run CI, so the exact-head run to cite is the one on `b882e0a` — if you want a run on the literal PR head, `gh workflow run ci.yml -R radalzubi/harvestmind --ref feat/zaad-insights-canonical-connectivity` before merging), pushed; base `main` `3a25b52` (production `d2a3cb5` + docs) |
| PR | **#84** (draft): https://github.com/radalzubi/harvestmind/pull/84 |
| CI on `b882e0a` | run `35011538354`, **in progress** at pause time (1/13 done, 0 failed). The previous run on `e2796f7` failed only ruff (one F541) and bandit (four B608 on `api/product/insights.py`); both are fixed in `b882e0a` |
| working tree | clean at `b882e0a` (the Desktop clone is healthy; no scratch clone needed) |
| production | unchanged: Fly `zaad-api` v27 `canonical-d2a3cb5`; Vercel from `main`; V2 planner still BLOCKED at the default scope (owner decisions in `HANDOFF_PLANNER_RECOVERY_2026-09-15.md`) — the V2.1A brief says build regardless |
| records written | `OPERATING_PRODUCT_V2_1_INSIGHTS.md` (architecture, complete), `FABLE_V2_1_RELEASE_AUDIT.md` (§1–6 filled; §7 CI/merge, §8 production, §9 decision still to fill) |

## What is built and verified (do not redo)

* Backend `api/product/insights.py` + `api/routers/zaad_insights.py` (`/api/zaad/insights/{summary,plan,demand,demand/period,inventory,supply,suppliers,service,decisions,value,connectivity}`), registered in `api/main.py`; `POST /intake/load-demo-company`; telemetry events `insights_opened`, `insights_period_opened`.
* Demo company `synthetic/fmcg/demo_company.py` (DEMO / SYNTHETIC; 42,280 rows), `scripts/zaad_demo_workspace.py` (API-driven loop), `scripts/insights_scale_qa.py` (10k / 50k: all queries < 800 ms median; 437 ms worst at 50k).
* Web: `/insights` page, `web/src/lib/zaad/insights.ts`, `components/insights/ChartCard.tsx`, `MultiLine` / `StackedBars` in `components/charts.tsx`, nav + en/ar copy, Home "At a glance", decision-detail reverse links, CSS in `globals.css`.
* Tests green locally: `tests/integration/test_zaad_insights.py` (16), `tests/integration/test_demo_company.py` (7), web `insights.test.ts` (10; 150 web tests total), tsc / eslint clean, ruff / bandit / mypy (CI scope) clean.
* Browser QA done on the local dev server (recorded in the audit §6): all six tabs, the spike drill-down, filters, Arabic, mobile, plan-backed Decisions & value with all five registers, connectivity matrix, decision → insights links, Home glance. Two demo loops ran end to end through the API; the second (`op_96acea06`, plan `job_f2d1b4dc…`, draft `draft_da5f08e8b5b1451d`) completed every step with exit 0.

## Local environment after a reboot (it will be gone)

`/private/tmp/claude-501/…/scratchpad/` held the version-matched venv, the local job store and the
demo logs; a reboot clears it. `.claude/launch.json` entry `api-demo` points at that venv, so recreate
it before starting the API (or edit the entry):

```bash
uv venv --python 3.12 /tmp/venv312 && uv pip install --python /tmp/venv312/bin/python -e . highspy==1.15.1 scipy==1.18.1 numpy==2.5.3 duckdb==1.5.5 pydantic==2.13.5 pytest
```

Then either fix the venv and job-store paths in `.claude/launch.json` (`api-demo`) or run the API with:
`HARVESTMIND_AUTH_REQUIRED=true ZAAD_JOB_STORE=/tmp/demo_jobs.sqlite ZAAD_ATP_ENABLED=1 ZAAD_LEGACY_PLANNERS=0 HARVESTMIND_RATE_LIMIT_PER_MIN=0 /tmp/venv312/bin/python -m uvicorn api.main:app --port 8001`
(use the desktop app's preview for servers, not Bash). `web/.env.local` already points the web at
`http://localhost:8001`. The local operator vaults under `./data` survive, but their plans lived in the
lost job store: run `python3 scripts/zaad_demo_workspace.py --api http://127.0.0.1:8001 --products 5 --as-of 2026-09-15`
again for a plan-backed workspace (about 10 minutes on this laptop; it prints the token at the end;
open the web with `/access?token=…`). The API imports the demo module lazily: restart it after editing
`synthetic/fmcg/demo_company.py`.

## Exact remaining steps (the brief §43, in order)

1. `gh run view 35011538354` — CI must be 13/13 on `b882e0a`. If anything fails, fix, commit, push, and wait for the new run; every commit changes the head.
2. Optional but planned: the final acceptance walk (brief §45) once more in one sitting on a plan-backed demo workspace: Demand → click the spike week → products / customers → Inventory → open POs → supplier → related decision → decision detail → proposal → approve → export → external status → outcome / History / value. Every piece has been verified; the connected walk is what §45 asks to demonstrate. Record it in the audit §6.
3. Fill the audit §7: `gh pr ready 84`, verify `main` is still `3a25b52` (`gh api repos/radalzubi/harvestmind/git/ref/heads/main`), merge with the convention
   `gh pr merge 84 --merge --subject "Merge PR #84: feat(zaad): V2.1A Insights — visual insights, canonical connectivity, customer demand intelligence" --body "Exact tested head b882e0a (CI 35011538354, 13/13). …"`, record the merge SHA and that its tree equals the tested head's.
4. Backend changed → deploy the exact merge: `gh workflow run deploy-api.yml -R radalzubi/harvestmind -f sha=<merge sha> -f app=zaad-api`; confirm `fly image show -a zaad-api` reads `canonical-<sha7>` (expect v28).
5. Vercel: `gh api "repos/radalzubi/harvestmind/deployments?per_page=4"` must show a Production deployment for the merge SHA; `vercel ls zaad --prod --scope rad-al-zubi-s-projects` Ready.
6. Production smoke: `SSL_CERT_FILE=$(python3 -m certifi) python3 scripts/operating_product_release_smoke.py --api https://zaad-api.fly.dev --self-serve` — now 24 checks (five Insights checks added). Then the demo on production: `python3 scripts/zaad_demo_workspace.py --api https://zaad-api.fly.dev --products 5` (the plan takes 2–3 min on a rested machine; it burns burst balance — run it once). Walk `https://zaadsupply.com/insights` on that workspace; check the browser console and `fly logs -a zaad-api --no-tail`.
7. Tag: `git tag -a zaad-operating-product-v2.1a-runtime <merge sha> -m "…"`; `git push origin zaad-operating-product-v2.1a-runtime` (convention: `<name>-runtime` on the deployed merge; note in the ledger that the V2 planner tag is still withheld).
8. Records (docs-only commit on `main`, as before): `CURRENT_SYSTEM.md` status line + released table row for V2.1A; `ZAAD_RELEASE_LEDGER.md` current-state table (runtime, tags), a V2.1A entry, "Exact next action"; audit §7–9 with the verdict; `HANDOFF_PLANNER_RECOVERY_2026-09-15.md` §1 line "V2.1 not started" → started/released.
9. Final report ending with exactly `ZAAD OPERATING PRODUCT V2.1A — RELEASE PASS` or `— BLOCKED`.

## Things learned today that will bite again

* bandit's `# nosec B608` must sit on the statement's **closing** line for a multi-line SQL string; inside the string it becomes SQL and breaks the query.
* `stg_atp_customer_orders` for the workspace path must name the contract's aggregate customer `customers`, `incumbent_policy` one of `FIFO_PROMISE | FCFS_ORDER_DATE | TIER_PRIORITY | PROPORTIONAL | CONTRACTUAL_THEN_PRIORITY | DECLARED_MANUAL`, `inbound_confidence = 1`, unique `line_id`s across orders.
* Decision-response `reason_code` values are lowercase (`supplier_relationship`, `customer_commitment`, …).
* Export answers a CSV file, not JSON.
* DuckDB positional `?` binds follow the SQL text order, including placeholders inside SELECT before the WHERE.
* The Data explorer's filterable columns: `products` (category, brand, supplier_id), `inventory` (location_id), `customer_orders` (customer_id) — the Insights filter bar reads its options from those.
* The plan report has no `network` key; P2 presence is `network_service` or transfer actions.

# ZAAD Diagnostic run experience + consulting-grade diagnostic report — implementation tracker

**Status: DONE — RELEASED (2026-09-17).** Branch `feat/diagnostic-report-consulting` from `main` `ed2d15c` → PR #89 (tested head `eceed3f`, CI 35236930051 13 / 13) merged as `e88c660`; wording follow-ups from production QA in PR #90 (tested head `b2ff8c8`, CI 35239397661 13 / 13) merged as `e512a62`. Fly `zaad-api` **v32** `canonical-e512a62` (digest `sha256:9c7c6ab1abc87bcf549291e4c4fd5d2a0fbf0d97d4cb8f297d7e7ad18f5390cd`, deploy-api run 35240675975; v31 `canonical-e88c660` in between, deploy-api run 35238653172); Vercel production from `e512a62`; machine `0804e0dfd1e948` unchanged; tag `zaad-diagnostic-report-v2-runtime` = `e512a62`.

## 0. What is being fixed

Two production problems in the free diagnostic (`/start` → `POST /jobs/diagnostic` → `GET /jobs/{id}/report.pdf`):

1. **The run looks stuck.** `web/src/app/start/page.tsx` shows one spinner and the raw backend `progress`
   string, polls every 3 s, forgets the job on refresh (no reconnect), has no timeout / cancel / reference id,
   and the button can be pressed repeatedly while a request is in flight. The backend job has no real stage,
   no queued state, no hard timeout for in-process runs, and only persists finished jobs.
2. **The report is optimizer output pasted into a PDF.** `api/routers/jobs.py::render_report_pdf` prints the
   readiness enum (`READY_WITH_CAVEATS`), the decision string (`incumbent`), the candidate table
   (`order_up_to +15.4% / +13.9% / cleared the gate: yes`) next to "incumbent retained" with no explanation
   of held-out validation, raw regime reasons (`demand CV 2.04, zero-share 77%`), lane rows (`aqaba 64% /
   quality 0.42`) with no meaning or exposure, and the assumption list in the body.

## 1. Current-state review (read before coding)

| Area | File(s) | What was found |
|---|---|---|
| Frontend flow | `web/src/app/start/page.tsx`, `web/src/lib/api.ts` (`Job`, `startDiagnostic`, `getJob`, `downloadReport`) | single spinner, 3 s poll, no reconnect, no terminal states beyond done/failed |
| Job API | `api/routers/jobs.py` | statuses `running/done/failed`; machine or thread runner; stale check only for machine jobs; `_persist` only on done and machine-failed; no cancel; no timeout for thread jobs; one-at-a-time per operator (POST returns the running job) |
| Worker | `api/worker.py` | ephemeral Fly machine; posts `progress` text only |
| Diagnostic core | `_run_commercial`: `ingestion.pilot_readiness.assess` → `api.routers.fmcg.build_inputs` (infers incumbent, provenance, priors) → `_state_for` (regimes, lane outlooks) → `backtesting.safe_selector.safe_select` (inner folds, gates, nested held-out re-check) | untouched by this task |
| Selection semantics | `backtesting/safe_selector.py` | a candidate `passed` = all inner gates; the winner is then re-checked on held-out folds; failure there returns the incumbent with reason "won the selection folds but did not beat the incumbent on N held-out fold(s)". The summary sent to the report did not carry the held-out stats or gates, which is why the PDF looked contradictory |
| Lane risk | `adaptive/leading.py::disruption_outlook` | `risk` = logistic of ASSUMED weights over public indicators (chokepoint transits, port throughput, conflict news, GSCPI, fuel, freight); `quality` = share of feeds present, reduced for stale ones; `missing` lists absent feeds |
| Readiness | `ingestion/pilot_readiness.py` | verdict enum, score, preferred-missing fields, `weakened_conclusions` (already customer-readable sentences), `history_weeks` |
| Incumbent | `backtesting/incumbent.py` | per-SKU cover weeks and review cadence inferred from PO history; note when inventory position at PO date is unknown |
| Tenant / export | `api/dependencies.require_operator`; job JSON under the operator's vault `reports/`; job lookups 404 for another operator | preserved |
| NTDCO output | production vault (`fly ssh`) | **not read**: production reads are refused in this session. The NTDCO-shaped fixture is built from the owner's quoted report (`READY_WITH_CAVEATS`, `order_up_to +15.4% / lower bound +13.9% / cleared gate yes` with the incumbent retained, `SKU-0137 CV 2.04 zero-share 77%`, `aqaba 64%`) in the exact summary shape the old job produced |

## 2. Design

### 2.1 Job lifecycle (backend)
- Statuses: `queued` → `running` → `done` | `failed` | `timed_out` | `cancelled`. `stage` ∈
  `preparing`, `reconstructing`, `lanes`, `testing`, `reporting` (real boundaries in `_run_commercial`; the
  worker forwards them). No percentage anywhere.
- `queued`: in-process runs wait for a diagnostics-only FIFO solver slot (`HARVESTMIND_DIAG_WORKERS`, default 1)
  in submission order and report `queue_position`; machine runs are `queued` while the dedicated machine boots
  (`queue_position` null).
- Hard timeout `HARVESTMIND_JOB_MAX_S` (default 3600 s) → `timed_out` with a message and retry path; the stale
  rule (`HARVESTMIND_JOB_STALE_S`) is kept for machine jobs. `POST /jobs/{id}/cancel` → `cancelled`
  (cooperative for threads at the next stage boundary; the machine is destroyed).
- Every terminal state is persisted; `GET /jobs/latest` returns the operator's newest job so a refreshed
  browser reconnects instead of starting a second run. `POST /jobs/diagnostic` keeps returning the active job.
- `GET /jobs/{id}` carries `report` (the structured findings) once done. `GET /jobs/{id}/report.json` too.

### 2.2 Summary enrichment (additive, in `reports/diagnostic_summary.py`)
Readiness detail, incumbent detail (cover / review per SKU), SKU profile (demand mean, variability, zero share,
cover, value share, regime reasons), supplier profile (receipts, fill, lead mean / spread, value share, SKUs),
candidate evidence (fold deltas, gates, held-out stats and gates, service diff), gate configuration, lane
exposure (suppliers, SKUs, value share, PO lines without a receipt), history range, versions. Nothing invented:
a value that cannot be computed is absent, never zero.

### 2.3 Analysis layer (`reports/diagnostic_findings.py`)
Deterministic `build_report(summary, job, company) -> dict` producing the structured report: conclusion,
readiness (label + level from explicit criteria), ordering today, policy comparison (with the held-out
explanation), ranked findings (`DiagnosticFinding`), supplier analysis, lane risk (external condition +
exposure + response), actions NOW / NEXT / MONITOR, appendix (assumptions, methodology, provenance, run id).
No model API involved. Old summaries (pre-enrichment) still render: held-out facts fall back to parsing the
selector's reason string.

### 2.4 Renderers
- PDF: `reports/diagnostic_pdf.py` (reportlab) consumes the structured report. 3–6 pages, executive summary
  first, finding cards, one fold chart when fold deltas exist, appendix last.
- In-app: `web/src/app/start/page.tsx` renders the same structured report (`DiagnosticReport` component) with
  links to Inventory (SKU), Supplier, Purchase orders, Decisions.
- Run view: `web/src/lib/diagnostic/lifecycle.ts` (pure state machine + poller, tested with node:test) and
  `web/src/components/diagnostic/DiagnosticRun.tsx` (indeterminate animated bar, stages, elapsed time,
  queue position, terminal states, cancel, retry).

## 3. Progress

- [x] Branch, review, tracker
- [x] Backend lifecycle (`api/routers/jobs.py`: real stages, queued with a FIFO solver slot and position, hard
      timeout and stale reaping → `timed_out`, cancel, every terminal state persisted, `GET /jobs/latest`,
      `GET /jobs/{id}/report.json`; `api/worker.py` forwards stages and stops when told)
- [x] Summary enrichment (`reports/diagnostic_summary.py`, additive, `summary_version` 2026.09.2)
- [x] Findings builder (`reports/diagnostic_findings.py`, `report_version` 2026.09.2)
- [x] PDF renderer (`reports/diagnostic_pdf.py`)
- [x] Frontend lifecycle lib + run component (`web/src/lib/diagnostic/lifecycle.ts`,
      `web/src/components/diagnostic/DiagnosticRun.tsx`)
- [x] Frontend report view (`web/src/components/diagnostic/DiagnosticReport.tsx`, `/start` wired)
- [x] Tests: 12 lifecycle (integration), 21 report (unit), 20 frontend lifecycle (node:test); the real
      end-to-end diagnostic test still passes with the enriched summary
- [x] Manual QA on a local demo workspace (below)
- [x] Performance measurement (below)
- [x] PR, CI on exact head, merge, deploy, production QA, tag, docs (§7)

## 4. Manual QA (local, synthetic demo company, 2026-09-17)

Workspace: self-serve `QA Demo Distributor` with `POST /intake/load-demo-company` (36 SKUs, 6 suppliers,
104 weeks, 5 declared lanes). API in-process runner (`HARVESTMIND_WORKER_MACHINES=false`).

| Check | Result |
|---|---|
| Run → live state | indeterminate bar animating (`diag-slide`, 1.6 s), title "Running your diagnostic", backend progress text, elapsed clock, five stages with the current one marked, Cancel, reference id; no `%` anywhere in the run view |
| Repeated press / second tab | the same job id is returned; one active job in the process |
| Refresh while running | the page reconnects through `GET /jobs/latest`; the finished run's result is shown without a second start |
| Cancel | terminal "Diagnostic cancelled" with retry; the worker stops at its next stage; a new run can start |
| Done | result view renders the structured report; PDF downloads (`zaad-diagnostic-<id>.pdf`) |
| Phone (375 px) | run view and report readable; wide tables scroll inside their own container; no page overflow |
| Arabic / RTL | layout mirrors correctly; report copy is English (not localised, see limits) |
| Enum leakage | none in the run view or the report body (tested); internal terms only in the appendix |

Failed and timed-out states are exercised by the lifecycle tests (`tests/integration/test_diagnostic_lifecycle.py`)
rather than provoked in the browser.

## 5. Performance (local, Apple Silicon, one solver thread)

| Step | Demo company (36 SKUs, 104 weeks) | Synthetic 20 SKUs, 80 weeks |
|---|---|---|
| Create job (`POST /jobs/diagnostic`) | < 50 ms | < 50 ms |
| Queue wait | 0 s (one slot, nothing queued) | 0 s |
| Diagnostic execution (`timing.run_s`) | 16.2 s | 6.7 s |
| Report build (`timing.report_build_s`) | 0.03 s | 0.002 s |
| PDF generation | 0.14 s | 0.12 s |
| `GET /jobs/{id}` payload | 76 KB (report 37 KB, summary 25 KB) | 63 KB |
| PDF | 25 KB, 8 pages (6 body + 2 appendix; 5 lanes, 8 finding cards) | 24 KB, 7 pages |

The diagnostic itself was not changed: scenario count, folds, gates and candidates are as before. Production
runs on a dedicated 4-CPU machine; a customer-scale run is measured in production QA.

## 7. Release and production QA (2026-09-17)

| step | value |
|---|---|
| PR #89 | `feat/diagnostic-report-consulting`, tested head `eceed3f`, CI run 35236930051 13 / 13 (the `unit-zaad-4` shard failed once on a pre-existing timing race in `tests/unit/test_zaad_solver_lease.py`'s fake — a module this change does not touch — and passed on re-run of the same head); merge `e88c660c47e0d79a9d5c7c5c6bd698ae93d8eafa` |
| Fly v31 | `canonical-e88c660`, digest `sha256:a82b870be64364aa875b8858cf2fde555bc4e49971e8ceb1f659b8db80b84dc7`, deploy-api run 35238653172 |
| production QA on v31 | demo workspace `op_428f8767` only: `POST /jobs/diagnostic` 5.6 s (synchronous machine launch, pre-existing) → `queued` "starting a dedicated solver machine" 36 s → `running` with machine-forwarded stages (`lanes`, `testing`) → `done` in 41 s; second press returned the same job; `report.json` 37 KB; PDF 25 KB, 8 pages, 0.86 s; other-tenant 404 and anonymous 401 on job, report.json, report.pdf, cancel, latest, start. Browser (zaadsupply.com): reconnect to the running job, animated bar (`diag-slide`), queued → running → result. Found: "anchored to the your current policy" and a truncated executive line for an adopted candidate |
| PR #90 | `fix/diagnostic-report-wording`, tested head `b2ff8c8`, CI run 35239397661 13 / 13; merge `e512a62a4ab5299d9e6efc64e02a82b88da39166` |
| Fly v32 | `canonical-e512a62`, digest `sha256:9c7c6ab1abc87bcf549291e4c4fd5d2a0fbf0d97d4cb8f297d7e7ad18f5390cd`, deploy-api run 35240675975; machine `0804e0dfd1e948` `shared-cpu-2x` / 2 GB unchanged |
| Vercel | production alias `zaadsupply.com` → deployment `zaad-9zl99eg5h` built from `e512a62` |
| production QA on v32 | same walk: `done` in 42 s (queue wait 37 s for the machine), report.json 37 KB, PDF 25 KB 8 pages, isolation 404 / 401 on every route, wording clean ("anchored to your current policy"; the executive line for the adopted candidate complete); the production page reconnects to the finished run and renders the report |
| tag | `zaad-diagnostic-report-v2-runtime` = `e512a62` (annotated; old tags untouched) |
| NTDCO | not opened (no customer key held); its production output was not read. The report renders its old-shape summary through the tested fallbacks |

## 6. Decisions and limits (kept current)

- Optimizer, gates, fold construction, scenario counts: untouched. The enrichment reads the objects the
  selector already returns.
- NTDCO production output was not read (no production reads in this session; the customer key is not held).
- `/start` was never localised; the run view and report view are English. RTL layout is verified, copy is not
  translated (recorded as a limit).
- In-process diagnostics take a diagnostics-only FIFO slot (`HARVESTMIND_DIAG_WORKERS`, default 1); they do not
  share the ZAAD planner's solver lease. Production runs on dedicated machines, where the slot is not involved.
- A cancel or timeout stops an in-process run at its next stage boundary; a solve already in flight finishes
  silently and its result is discarded. A machine run is destroyed.
- Inventory, working-capital and waste comparisons are reported as "Not available from current data": the
  backtest keeps cost and service per period only. Open-order value appears only when a currency is declared.
- Old persisted jobs (pre-enrichment) render through fallbacks: held-out facts from the selector's reason
  string, SKU and supplier facts from the estimator's top reasons, margin count from the warnings.

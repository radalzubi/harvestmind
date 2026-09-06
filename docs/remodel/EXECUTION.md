# Commercial engine and market audit — execution record

Requested: both attached prompts, parts 1–37. Started 2026-09-05.
Base: `2820a69`, `origin/adaptive/decision-engine`, fetched from GitHub.
Branch: `codex/commercial-engine-evidence-audit`.
The original checkout and its uncommitted Indiana sweep are preserved.

## Decision and sequencing

1. Audit the actual commercial implementation and predecessor reports.
2. Verify current vendor, scientific, geographic and savings evidence.
3. Select architecture from those findings, then implement and test.
4. Benchmark every run and ablation, retaining adverse outcomes.
5. Write the market verdict, pilot and mathematical specification.
6. Run repository checks, commit and push the review branch.

The newer base already implements most proposed architecture: incumbent,
service floors, rolling execution, adaptive state, anchoring and a selector.
Reimplementing those would duplicate work. This audit will repair verified
defects and add the missing stock/service decision experiment.

## Findings before changes

- Optimizer candidates receive opening stock but **not pipeline receipts**;
  settlement and incumbent heuristics do receive them.
- Nested selector confirmation checks mean cost only, not the service,
  downside, completeness or solver-relaxation gates used during selection.
- The live winner is checked only for a non-null schedule.
- Inner-fold supplier fallback can use later observations; lead estimates
  and opening-cover reconstruction can depend on data after the inner origin.
- A demand-shift branch bypasses historical evidence altogether.
- Existing saved SAFE results include a -27.6% worst run; they do not
  establish a guarantee against future harm.
- Competitor right-sizing, service frontiers, probabilistic planning and
  export/ERP-based deployment are already documented category capabilities.

## Completion tracking

| Prompt parts | Deliverable | State |
|---|---|---|
| 1–2 | Root cause and marginal service economics | ROOT_CAUSE, BENCHMARK_RESULTS, marginal_service.csv |
| 3–6, 13 | Vendor/method evidence, architecture decision | COMPETITORS_AND_SAVINGS, METHODS_AND_ARCHITECTURE |
| 7–8, 12, 17–18 | Implementation, tests, policy gates | Pipeline and gates repaired; two experimental service candidates; MATH_SPEC §28 |
| 9–11, 20–35 | Country, competitors, sizing, ROI, positioning | MARKETS_AND_POSITIONING, ECONOMICS_AND_PILOT, 867 vendor-feature cells; country counts explicitly unknown |
| 14–15, 36–37 | Regime experiment, ablations, recommendation evidence | 4,005 causal main runs +300 ablation runs; adverse outcomes retained; autonomous commercial acceptance fails |
| 16, 19 | Pilot, executive report, GitHub handoff | README, pilot/CFO card, review branch; no merge or deployment |

## Verification

- `python3 -m pytest -q`: **1393 passed, 1 skipped**, four existing FastAPI
  deprecation warnings. 27 new regression cases in `test_commercial_remodel.py`.
- Ruff0.15.12 on every changed Python file: pass. Repo-wide: **142 existing
  issues**, outside the changed files; no unrelated mass rewrite performed.
- CI-equivalent decision-core mypy: pass,102 source files. Untyped-body notes
  are retained; this is not a claim all function bodies are strictly typed.
- Frontend `tsc --noEmit`: pass. Production `npm run build`: pass. The first
  sandboxed build could not resolve Google Fonts; rerun with approved network
  access succeeded. No frontend source changes required.
- `git diff --check`: pass. Repeated main/ablation controls have zero maximum
  cost difference. Physical information separation and pipeline accounting
  have dedicated regression tests.
- Research uses public primary vendor/government/research sources. Vendor
  outcome selection bias and unknown market counts are stated, not replaced
  by invented estimates.

## Deliberate limits, not completed commercial validation

The final acceptance test **does not pass** for autonomous savings optimization.
The selector has two realized losses and almost always retains the incumbent;
both service-target candidates fail badly. No real customer, paid conversion,
retention, qualified country TAM count or company valuation has been established.
Those cannot be manufactured by more synthetic seeds.

MEIO, route-source substitution, cash/FX constraints, terminal cash valuation,
OTIF, perishable settlement parity and separately identified copula/DRO/route
value are not shipped or claimed. They are ranked and deferred with customer
data prerequisites, as the prompts instruct rather than adding every feature.
The main grid is target×cover plus OFAT, not all high-dimensional interactions.

One intermediate replay was rejected after finding future-pipeline and supplier
availability leakage. Its last results are retained in `evidence/rejected/`;
all final summaries use `evidence/causal/`. The per-period service experiment
was developed after inspecting aggregate-service failure. Evaluation remains
developmental, not a pristine blind holdout.

Git SSH fetch works. GitHub CLI API inspection returned HTTP401; a separate
GitHub connector is available for the review handoff. No production deployment,
branch merge, prospect contact or customer-data ingestion is authorized by this
audit and none was performed. The original dirty working directory is preserved.

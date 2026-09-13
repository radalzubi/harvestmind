# ZAAD repository cleanup audit (post-P4B, 2026-09-13)

Every tracked file classified before any deletion. Classification is by evidence (references, imports, API
registration, CI / Docker / Fly / Makefile / packaging references, evidence-record citations), never by filename.
ONLY `DEAD` is deleted. Starting `main` `3b079c4`; production runtime `1851f40` (`p4b-v1-release-runtime`, Fly v23).

## Counts

| classification | files |
|---|---|
| HISTORICAL EVIDENCE | 835 |
| REGRESSION ORACLE | 479 |
| ACTIVE | 409 |
| COMPATIBILITY | 267 |
| DEAD | 51 |
| MIGRATION DEPENDENCY | 22 |
| **total audited** | **2063** |

## By area

| area | ACTIVE | COMPATIBILITY | REGRESSION ORACLE | HISTORICAL EVIDENCE | MIGRATION DEPENDENCY | DEAD | classification basis |
|---|---|---|---|---|---|---|---|
| `docs/zaad_full` | 1 | 0 | 435 | 529 | 0 | 27 | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `tests` | 161 | 0 | 0 | 0 | 0 | 0 | test suite (P0-P5 / P4B regression coverage, legacy platform coverage) |
| `scripts` | 0 | 22 | 42 | 64 | 0 | 0 | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `web` | 113 | 0 | 0 | 0 | 0 | 0 | released optimizer stack / API / frontend (canonical engine zaad/full + phase packages) |
| `zaad` | 82 | 7 | 0 | 0 | 0 | 0 | released optimizer stack / API / frontend (canonical engine zaad/full + phase packages) |
| `data` | 0 | 50 | 0 | 0 | 0 | 0 | committed public series and samples the legacy validation and adaptive indicators read (data/external README: reproducible without re-hitting APIs) |
| `docs/zaad_next` | 0 | 0 | 2 | 27 | 0 | 17 | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/outreach` | 0 | 0 | 0 | 39 | 0 | 0 | phase / product / pilot / research documentation of record; stale intermediate statements are historical, not current |
| `docs/reports` | 0 | 0 | 0 | 34 | 0 | 1 | phase / product / pilot / research documentation of record; stale intermediate statements are historical, not current |
| `docs/remodel` | 0 | 0 | 0 | 33 | 0 | 0 | phase / product / pilot / research documentation of record; stale intermediate statements are historical, not current |
| `artifacts` | 0 | 0 | 0 | 32 | 0 | 0 | committed outputs of the pre-commercial readiness audit and legacy validation (cited by COMMERCIAL_READINESS.md, docs/audits, docs/validation, readiness scripts) |
| `api` | 26 | 0 | 0 | 0 | 0 | 0 | released optimizer stack / API / frontend (canonical engine zaad/full + phase packages) |
| `dashboard` | 0 | 26 | 0 | 0 | 0 | 0 | legacy HarvestMind platform package: mounted by the API (legacy routers), imported by runtime / scripts / tests, or gated behind ZAAD_LEGACY_PLANNERS; removal would change the API surface |
| `db` | 1 | 0 | 0 | 0 | 22 | 0 | schema lineage; setup_db applies every migration in order (idempotent) |
| `docs/workspace` | 0 | 0 | 0 | 22 | 0 | 1 | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `ingestion` | 0 | 20 | 0 | 0 | 0 | 0 | legacy HarvestMind platform package: mounted by the API (legacy routers), imported by runtime / scripts / tests, or gated behind ZAAD_LEGACY_PLANNERS; removal would change the API surface |
| `(root)` | 14 | 0 | 0 | 5 | 0 | 0 | repository configuration / metadata (build, deploy, lint, security, packaging, README) |
| `optimization` | 0 | 18 | 0 | 0 | 0 | 0 | legacy HarvestMind platform package: mounted by the API (legacy routers), imported by runtime / scripts / tests, or gated behind ZAAD_LEGACY_PLANNERS; removal would change the API surface |
| `forecasting` | 0 | 17 | 0 | 0 | 0 | 0 | legacy HarvestMind platform package: mounted by the API (legacy routers), imported by runtime / scripts / tests, or gated behind ZAAD_LEGACY_PLANNERS; removal would change the API surface |
| `docs/(top)` | 2 | 0 | 0 | 13 | 0 | 0 | phase / product / pilot / research documentation of record; stale intermediate statements are historical, not current |
| `backtesting` | 0 | 13 | 0 | 0 | 0 | 0 | legacy HarvestMind platform package: mounted by the API (legacy routers), imported by runtime / scripts / tests, or gated behind ZAAD_LEGACY_PLANNERS; removal would change the API surface |
| `synthetic` | 0 | 13 | 0 | 0 | 0 | 0 | legacy HarvestMind platform package: mounted by the API (legacy routers), imported by runtime / scripts / tests, or gated behind ZAAD_LEGACY_PLANNERS; removal would change the API surface |
| `docs/validation` | 0 | 0 | 0 | 12 | 0 | 0 | phase / product / pilot / research documentation of record; stale intermediate statements are historical, not current |
| `risk` | 0 | 11 | 0 | 0 | 0 | 0 | legacy HarvestMind platform package: mounted by the API (legacy routers), imported by runtime / scripts / tests, or gated behind ZAAD_LEGACY_PLANNERS; removal would change the API surface |
| `adaptive` | 0 | 10 | 0 | 0 | 0 | 0 | legacy HarvestMind platform package: mounted by the API (legacy routers), imported by runtime / scripts / tests, or gated behind ZAAD_LEGACY_PLANNERS; removal would change the API surface |
| `infrastructure` | 0 | 9 | 0 | 0 | 0 | 0 | legacy HarvestMind platform package: mounted by the API (legacy routers), imported by runtime / scripts / tests, or gated behind ZAAD_LEGACY_PLANNERS; removal would change the API surface |
| `reports` | 0 | 9 | 0 | 0 | 0 | 0 | legacy HarvestMind platform package: mounted by the API (legacy routers), imported by runtime / scripts / tests, or gated behind ZAAD_LEGACY_PLANNERS; removal would change the API surface |
| `data_contracts` | 0 | 8 | 0 | 0 | 0 | 0 | legacy HarvestMind platform package: mounted by the API (legacy routers), imported by runtime / scripts / tests, or gated behind ZAAD_LEGACY_PLANNERS; removal would change the API surface |
| `training` | 0 | 8 | 0 | 0 | 0 | 0 | legacy HarvestMind platform package: mounted by the API (legacy routers), imported by runtime / scripts / tests, or gated behind ZAAD_LEGACY_PLANNERS; removal would change the API surface |
| `domain` | 0 | 7 | 0 | 0 | 0 | 0 | legacy HarvestMind platform package: mounted by the API (legacy routers), imported by runtime / scripts / tests, or gated behind ZAAD_LEGACY_PLANNERS; removal would change the API surface |
| `agronomy` | 0 | 6 | 0 | 0 | 0 | 0 | legacy HarvestMind platform package: mounted by the API (legacy routers), imported by runtime / scripts / tests, or gated behind ZAAD_LEGACY_PLANNERS; removal would change the API surface |
| `docs/cofounder` | 6 | 0 | 0 | 0 | 0 | 0 | current source of truth (entry point, ledger, roadmap, checklist) |
| `docs/research` | 0 | 0 | 0 | 4 | 0 | 0 | phase / product / pilot / research documentation of record; stale intermediate statements are historical, not current |
| `docs/security` | 0 | 0 | 0 | 2 | 0 | 2 | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `retraining` | 0 | 4 | 0 | 0 | 0 | 0 | legacy HarvestMind platform package: mounted by the API (legacy routers), imported by runtime / scripts / tests, or gated behind ZAAD_LEGACY_PLANNERS; removal would change the API surface |
| `.github` | 2 | 0 | 0 | 0 | 0 | 1 | the one CI workflow and Dependabot config |
| `config` | 0 | 3 | 0 | 0 | 0 | 0 | legacy HarvestMind platform package: mounted by the API (legacy routers), imported by runtime / scripts / tests, or gated behind ZAAD_LEGACY_PLANNERS; removal would change the API surface |
| `docs/commercial-pilot-readiness` | 0 | 0 | 0 | 3 | 0 | 0 | phase / product / pilot / research documentation of record; stale intermediate statements are historical, not current |
| `docs/customer_intake` | 0 | 0 | 0 | 3 | 0 | 0 | phase / product / pilot / research documentation of record; stale intermediate statements are historical, not current |
| `docs/full-simulation-sweep` | 0 | 0 | 0 | 3 | 0 | 0 | phase / product / pilot / research documentation of record; stale intermediate statements are historical, not current |
| `pool` | 0 | 3 | 0 | 0 | 0 | 0 | legacy HarvestMind platform package: mounted by the API (legacy routers), imported by runtime / scripts / tests, or gated behind ZAAD_LEGACY_PLANNERS; removal would change the API surface |
| `docs/audits` | 0 | 0 | 0 | 1 | 0 | 1 | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/optimization` | 0 | 0 | 0 | 2 | 0 | 0 | phase / product / pilot / research documentation of record; stale intermediate statements are historical, not current |
| `docs/pilot` | 0 | 0 | 0 | 2 | 0 | 0 | phase / product / pilot / research documentation of record; stale intermediate statements are historical, not current |
| `docs/seo` | 0 | 0 | 0 | 1 | 0 | 1 | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/specs` | 0 | 0 | 0 | 2 | 0 | 0 | phase / product / pilot / research documentation of record; stale intermediate statements are historical, not current |
| `validation` | 0 | 2 | 0 | 0 | 0 | 0 | legacy HarvestMind platform package: mounted by the API (legacy routers), imported by runtime / scripts / tests, or gated behind ZAAD_LEGACY_PLANNERS; removal would change the API surface |
| `.claude` | 1 | 0 | 0 | 0 | 0 | 0 | dev tooling (launch config) |
| `.streamlit` | 0 | 1 | 0 | 0 | 0 | 0 | legacy HarvestMind platform package: mounted by the API (legacy routers), imported by runtime / scripts / tests, or gated behind ZAAD_LEGACY_PLANNERS; removal would change the API surface |
| `docs/deploy` | 0 | 0 | 0 | 1 | 0 | 0 | phase / product / pilot / research documentation of record; stale intermediate statements are historical, not current |
| `docs/projects` | 0 | 0 | 0 | 1 | 0 | 0 | phase / product / pilot / research documentation of record; stale intermediate statements are historical, not current |

## Deleted (DEAD only)

| path | reason |
|---|---|
| `.github/workflows/codeql.yml` | permanently failing CodeQL workflow: code scanning is unavailable on this plan (repository-level 403), security stays with bandit / pip-audit / gitleaks |
| `docs/audits/pre_commercial_baseline 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/reports/PROJECT_B_V2_CALIBRATED 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/security/DATA_HANDLING 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/security/SECURITY_HARDENING_REPORT 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/seo/ZAAD_SEARCH_STRATEGY 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/workspace/README 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/ABLATIONS 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/ARCHITECTURE 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/BENCHMARK_METHOD 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/BENCHMARK_RESULTS 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/CALIBRATED_PROTECTION_V4 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/CAPITAL_RECOVERY_V7 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/CASH_FLOW_MODEL 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/COMMERCIAL_ANSWERS 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/DEMAND_ADAPTATION 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/ETA_SURVIVAL_MODEL 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/FAILURE_ANALYSIS 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/FALSE_PROTECTION 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/IMPLEMENTATION_STATUS 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/INDUSTRY_STANDARD_V8 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/MATHEMATICAL_MODEL 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/MEIO 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/MEIO_RECOVERY_V6 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/NETWORK_RECOVERY_V5 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/PR24_FOLLOWUP 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/README 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/ROBUST_RESILIENCE 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/SCALABILITY 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/SERVICE_AND_ALLOCATION 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/SERVICE_RELIABILITY 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/SHADOW_PILOT 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/UNTOUCHED_HOLDOUT 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_full/VERIFICATION 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_next/BENCHMARK_METHOD 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_next/BENCHMARK_RESULTS 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_next/COMPETITIVE_BASELINE 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_next/CURRENT_STATE_AUDIT 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_next/DATA_SOURCE_AUDIT 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_next/FAILURE_ANALYSIS 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_next/IMPLEMENTATION_STATUS 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_next/MATHEMATICAL_SPEC 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_next/NEWS_SIGNAL_MODEL 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_next/NORMAL_ENGINE 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_next/PILOT_PLAN 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_next/README 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_next/RESILIENCE_ENGINE 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_next/ROUTE_MODEL 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_next/SECURITY_AND_DATA_GOVERNANCE 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_next/VERIFICATION 2.md` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |
| `docs/zaad_next/reproduce_legacy_service_mismatch 2.py` | byte-identical macOS Finder duplicate of the sibling file (verified with cmp); no reference |

Also removed from `pyproject.toml` (no import, no string use, no build / deploy / test / script use anywhere outside the
dependency list itself; verified with `git grep -P` over every non-docs file): `mlforecast`, `polars`, `sqlalchemy`,
`pydantic-settings`, `tenacity`, `python-dotenv`. Retained although unimported directly: `pyarrow` (pandas parquet in
the pool / worker), `python-multipart` (FastAPI `UploadFile`), `httpx` (the FastAPI test client), `click` / `Pillow` /
`urllib3` / `idna` / `tinycss2` / `gitpython` / `tornado` (transitive security pins recorded next to their CVEs),
`pandera` (data_contracts schemas), `reportlab` / `pdfplumber` / `jinja2` / `loguru` / `lightgbm` /
`hierarchicalforecast` / `pyomo` (imported by runtime packages).

## Scripts (every file under `scripts/`)

| script | classification | reason |
|---|---|---|
| `scripts/__init__.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/analyze_paired_folds.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/anonymize_export.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/benchmark_performance.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/build_dashboard_summary.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/build_readiness_json.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/calibrate_zaad_uncertainty.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/commercial_validate.sh` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/decompose_zaad_network_breaches.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/demo_run.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/diagnose_zaad_false_protection.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/fetch_indicators.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/fetch_public_priors.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/fetch_real_data.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/fill_adaptive_validation_doc.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/fill_safe_validation_doc.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/fill_validation_tables.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/generate_pilot_summary.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/generate_roi_report.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/health_check.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/ingest_market_prices.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/ingest_real_data.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/master_plan.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/p1_c_economics.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p1_cell90_diff.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p1_cell90_trace.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p1_closure_tables.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p1_common_valuation_diag.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p1_common_valuation_p0.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p1_cop_trace.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p1_cycle_compare.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p1_dual_terminal_table.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p1_final_table.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p1_fixtures.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p1_flag_trace.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p1_gate_trace.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p1_horizon_benchmark.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p1_horizon_extension_diag.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p1_horizon_tables.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p1_i_forensics.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p1_invariants.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p1_ownership_compare.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p1_p0_arms.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p1_p_counterfactuals.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p1_p_forensics.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p1_sampler_validation.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p1_t_decomposition.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p1_targeted.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p2_adversarial.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p2_benchmark.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p2_decision_compare.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p2_final_table.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p2_fixtures.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p2_frozen_cell_variability.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p2_h_diagnostic.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p2_invariants.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p2_perf_tie_check.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p2_profile_compare.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p2_profile_review.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p2_scalability.py` | HISTORICAL EVIDENCE | P1 / P2 closure diagnostic cited from the evidence records (docs/zaad_full/evidence) |
| `scripts/p2_snapshots.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p3_adversarial.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p3_benchmark.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p3_invariants.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p3_profile.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p4_adversarial.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p4_benchmark.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p4_invariants.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p4_perf_profile.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p4_profile.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p4b_adversarial.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p4b_benchmark.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p4b_profile.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p4b_release_audit.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p5_adversarial.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p5_benchmark.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p5_integration.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p5_profile.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/p5_release_audit.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/profile_zaad_network.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/report_zaad_full_evidence.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/retrain.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/run_adaptive_transition_validation.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/run_backtest.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/run_commercial_benchmark.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/run_commercial_benchmark_v2.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/run_commercial_remodel_audit.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/run_disruption_overlay.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/run_fmcg_counterfactuals.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/run_fmcg_stress_matrix.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/run_full_simulation_sweep.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/run_integrated_benchmark.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/run_p1_fixtures.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/run_paired_scenario_test.sh` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/run_real_validation_suite.sh` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/run_safe_policy_validation.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/run_scenario_generator_control.sh` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/run_supply_shock_control.sh` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/run_zaad_benchmark.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/run_zaad_demo.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/run_zaad_full_ablations.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/run_zaad_full_benchmark.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/sector_benchmark.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/sector_invariants.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/sector_profile.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/seed_workspace.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/setup_db.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/stress_test_backtest.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/study_zaad_recovery.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/study_zaad_surge.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/summarize_commercial_remodel.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/summarize_real_validation.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/summarize_zaad_adaptation.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/summarize_zaad_benchmark.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/summarize_zaad_holdout.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/summarize_zaad_reliability.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/sweep_commercial_sensitivity.sh` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/validate_against_benchmarks.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/validate_commercial_real_data.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/validate_demand_scenarios_real.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/validate_disruption_presets.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/validate_indiana_market.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/validate_leading_indicators.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/validate_real_data.py` | HISTORICAL EVIDENCE | producer of a committed validation / study record (docs/validation, docs/reports, artifacts/, evidence v1-v8); unreferenced by code, retained because its output is |
| `scripts/zaad_canonical_regression.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/zaad_network.py` | COMPATIBILITY | operational / legacy HarvestMind pipeline script (Makefile, packaging entry point, readiness pipeline, data fetch) |
| `scripts/zaad_network_workspace_smoke.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |
| `scripts/zaad_workspace_smoke.py` | REGRESSION ORACLE | reproduces or compares a frozen phase record (benchmark / invariants / adversarial / profile / compare / regression) |

## Retained despite appearing old (explicit)

* `docs/zaad_next/` (46 files): the pre-P0 resilience prototype's plan and evidence; README still points at it as history.
* `docs/remodel/`, `docs/reports/`, `docs/validation/`, `docs/full-simulation-sweep/`, `docs/commercial-pilot-readiness/`,
  `docs/outreach/`, `docs/research/`, `docs/pilot/`, `docs/projects/`, `docs/specs/`, `docs/audits/`, `docs/customer_intake/`,
  `docs/workspace/`: legacy HarvestMind-era product, pilot and validation records; historical, trustworthy, not current.
* `artifacts/` (32 files): outputs of the pre-commercial readiness audit cited by `COMMERCIAL_READINESS.md` and
  `docs/audits/pre_commercial_baseline.md`; six uncited baseline files (`artifacts/baseline/mypy_by_code.txt`, `pip_audit.*`,
  `pytest.txt`, `ruff.txt`) are the raw outputs that audit names as a directory and stay with it.
* `data/` (50 files, 10.9 MB): committed public series (portwatch, FRED, indicators, priors) the legacy validation and the
  adaptive indicators read; committed on purpose for reproducibility (`data/external/README.md`).
* Root `BUG_FIX_REPORT.md`, `CHANGELOG_SECURITY_PASS.md`, `SECURITY_CHECKLIST.md`, `SECURITY_HARDENING_REPORT.md`
  (July 2026 security pass; referenced by `SECURITY.md`, `tests/unit/test_auth.py` and each other; the docs/security
  copy of the hardening report differs by 209 lines and is a later revision, both kept).
* Legacy packages `adaptive agronomy backtesting config dashboard data_contracts domain forecasting infrastructure ingestion
  optimization pool reports retraining risk synthetic training validation`: the HarvestMind platform the API still mounts
  (routers planning / fmcg / backtest / data / fsma / reports / diagnostics / intake / forecasts / training / pool / admin /
  assistant / access / jobs). The web client calls `/access`, `/fmcg`, `/assistant`, `/admin` and `/api/zaad/*`; the other
  routers have no frontend caller but are part of the served API surface, so removing them would change API semantics
  (rule 21). `data_contracts` has no importer at all (its pandera schema module is unreferenced; the CSV templates are the
  partner data contract named in `STRUCTURE.md`): kept as COMPATIBILITY, listed as cleanup debt.
* `scripts/p1_*` diagnostics (25 files): cited from the P1 closure evidence; ruff-excluded by design (provenance).
* Unreferenced legacy study scripts (`analyze_paired_folds`, `run_commercial_benchmark*`, `run_integrated_benchmark`,
  `run_disruption_overlay`, `run_*_control.sh`, `sweep_commercial_sensitivity.sh`, `study_zaad_recovery`,
  `summarize_zaad_*`, `run_zaad_full_ablations`, `profile_zaad_network`, `report_zaad_full_evidence`,
  `calibrate_zaad_uncertainty`, `p2_scalability`): each produced a committed record (PROJECT B / C reports, the v1-v8
  zaad_full evidence, SCALABILITY.md, docs/validation); deleting them would leave those records irreproducible (rule 9).

## Legacy HarvestMind findings

* Repository name, package name (`harvestmind` in `pyproject.toml`), Docker user / paths (`/var/lib/harvestmind`), Fly env
  names (`HARVESTMIND_*`), migrations 001-013 and the frozen evidence all carry the name: embedded in contracts, left (rule 7).
* Legacy planners (`/planning`, `/fmcg/plan` legacy modes, `/api/zaad` prototype engine `zaad/{engine,allocation,forecast,
  signals,intake,contracts,demo}.py`) are gated by `ZAAD_LEGACY_PLANNERS` (production `0`: 410 Gone); the canonical engine is
  `zaad/full` with the phase packages `zaad/{meio,sectors,sourcing,recourse,atp,commitments}`. One canonical optimizer; the
  gated prototype is COMPATIBILITY (the public web demo still calls it in dev), consolidation is out of scope.
* `dashboard/` (Streamlit, `make dashboard`, optional `[dashboard]` extra) and `STRUCTURE.md` describe the legacy platform;
  kept, pointed at the current entry point.
* Environment variables read by the runtime and not set on Fly (`ZAAD_JOB_*`, `HARVESTMIND_WORKER_*`, `HARVESTMIND_SELF_SERVE`,
  `RESEND_API_KEY`, `ANTHROPIC_API_KEY`, `HARVESTMIND_DEMO_*`, ...) have code defaults; none removed (each is a behaviour switch).

## Feature flags

| flag | class | evidence |
|---|---|---|
| `ZAAD_LEGACY_PLANNERS` | ACTIVE | Fly secret = 0; gates every legacy planner path (410 when off); default outside dev is off |
| `ZAAD_ATP_ENABLED` | ACTIVE | fly.toml env = 1 since the P5 release; `atp_gate` refuses declared ATP blocks when unset |
| `HARVESTMIND_GATE_*`, `HARVESTMIND_WORKER_*`, `HARVESTMIND_SOLVER_THREADS` | ACTIVE | Fly env; job runner sizing |
| `HARVESTMIND_AUTH_REQUIRED`, `HARVESTMIND_RATE_LIMIT_PER_MIN`, `HARVESTMIND_ADMIN_KEY`, `HARVESTMIND_SEED_WORKSPACES`, `HARVESTMIND_SELF_SERVE` | ACTIVE | auth / rate limit / self-serve workspaces |
| `ZAAD_JOB_STORE`, `ZAAD_SHADOW_LEDGER`, `ZAAD_JOB_*` | ACTIVE | asynchronous jobs and the shadow ledger |
| `.env.example` legacy keys (`DATABASE_BACKEND`, `POSTGRES_URL`, `GUROBI_AVAILABLE`, `HIGHS_FALLBACK`, `QBO_*`, `USDA_NASS_API_KEY`, `NOAA_CDO_TOKEN`, `LOCAL_LINE_API_KEY`, `SYNTHETIC_*`, `USE_REAL_LLM`, `EXTRACTION_MODEL`) | COMPATIBILITY | read by legacy packages / connectors (mocked in tests); documented example, not runtime-bearing |

## Migrations

All 22 files under `db/migrations/` are MIGRATION DEPENDENCY: `setup_db` applies them in order and every one is
idempotent; older vault files upgrade through the full sequence. Not squashed, renumbered or rewritten.

## Tests

161 test files, all ACTIVE. No duplicate or obsolete test found for deleted content (the deleted files are
documentation duplicates and a workflow). Skips are runtime-conditional (`requires_solver`, `needs_data`, git absent,
fixture shape) and one documented `xfail` convention; none is removed or altered. Assertions untouched.

## GitHub branches

See the cleanup PR body: merged branches with no unique history deleted; the squash-merged branches
`ci-pytest-ruff` (#4), `docs/migrate-agri-ai-workspace` (#15), `codex/frontend-pages-no-hero` (#26),
`codex/revert-frontend-pages-no-hero` (#27), `codex/zaad-production-source` (#28) deleted; the superseded P3 closeout
drafts (#61 / #62 closed, content contained in the merged v3 up to one or two lines) deleted; retained: `docs/brief-al-burger`
(unique unmerged work, no PR), `claude/zaad-network-twin-v1` (PR #39 open, deferred), every `dependabot/*` branch (open PRs).

## GitHub protection and CodeQL

Branch protection and rulesets: the API answers `Upgrade to GitHub Pro or make this
repository public to enable this feature` (private repository, free personal plan). Not faked. Minimal manual action:
upgrade the owner to GitHub Pro (or make the repository public), then set on `main`: require a pull request, require the
`CI` workflow's jobs, block force pushes and deletions, no reviewer count. Code scanning: `Code scanning is not enabled for
this repository` (default setup 403) and cannot be enabled on this plan, so the CodeQL workflow (which never produced a
green status) is removed; bandit, pip-audit and gitleaks remain the security gates.

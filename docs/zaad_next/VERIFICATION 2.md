# ZAAD verification record

Local verification completed on the isolated `codex/zaad-resilience-engine` branch, based on PR #20 commit `6939523a7fe888bd9808ef55563314a485d88929`. Original checkout remains on `71ad5ab` with its nine existing dirty Indiana-sweep files untouched.

| Check | Result |
|---|---|
| `python3 -m pytest -q` | **1,473 passed,1 skipped**,4 existing FastAPI on_event deprecation warnings,105.60s |
| New ZAAD unit/integration tests | **80 passed** |
| Forecast + ZAAD retest after annotation-only corrections | **193 passed**,3.34s |
| Changed Python files Ruff0.15.12 | Passed |
| CI command `python3 -m mypy optimization risk backtesting api ingestion domain adaptive --ignore-missing-imports` | Passed,**103 files**; untyped-function informational notes remain |
| `mypy zaad api/routers/zaad.py --ignore-missing-imports --follow-imports=silent` | Passed,9 explicit new files |
| `npx tsc --noEmit` | Passed |
| `npm run build` | Passed, Next16.3.4 production output includes `/zaad` |
| `git diff --check` | Passed |
| Staged-file secret tripwire |3 passed; a public Kpler URL triggered the coarse key regex and was equivalently URL-encoded, not allowlisted |
| Frozen source/config check | Exact SHA-256365cac6fe33a40c372daf829d640b1c131ce22a6315832722a922e41917bccb7 |
| Final sweep completeness |75cells×5seeds×8methods=3,000 unique rows |
| Exact selected-trace cost replay |480 period rows reproduced; every replay matched saved cost within1e−8 |
| Physical capacity breaches |0/3,000 observed rows; not a proof for all inputs |
| Actual NWS adapter |193 normalized public records fetched; source-count and timestamps saved in `evidence/live_noaa_demo.json` |
| Browser/API smoke | Local `/zaad` loads; real demo request shows LEAN / RECOMMEND_FOR_REVIEW, selected policy and same economic report as Python; route cards display quote, path, approval and expiry |

## Post-freeze changes

No `zaad/` policy, forecast, threshold or benchmark-generator source changed after freeze. Reporting/docs and UI verification continued. The CI-equivalent mypy command exposed nine existing errors in imported forecast helpers; three annotation-only corrections were made: mixed-string numeric score dictionary return type, duplicate local annotation removal, and predictor Protocol instead of object. No formula or numeric code changed. The193-test retest and exact frozen trace check passed afterward.

Generated CSV line endings were normalized from CRLF to LF for Git's whitespace check; no values or rows changed. JSONL retains the primary exact numeric record.

## Environment and browser notes

Network calls and loopback binding initially failed under sandbox restrictions; the exact public fetch/build/local servers succeeded with scoped approval. A pre-existing agent-started Next dev instance was found at port3026 and used for smoke testing with API8026. An attempted3101 instance was refused because the same worktree already had a dev server; no unrelated server was stopped. The in-app browser's narrow viewport exposes inherited sidebar width constraints; responsive polish is not claimed complete. A later select-locator smoke action was unavailable; false-alarm correctness is covered by Python integration tests and the frozen matched control, not claimed from that UI action.

Local coverage was not recomputed; do not carry historical coverage percentages forward. Remote GitHub checks are separate from these observed local results. No merge, public deployment, supplier contact, live order, payment or customer-data upload was performed.

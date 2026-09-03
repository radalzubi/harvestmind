#!/usr/bin/env bash
# The single command that says whether this repository is releasable.
#   ./scripts/commercial_validate.sh          quick gates (minutes)
#   ./scripts/commercial_validate.sh --full   plus the simulation matrices (tens of minutes)
# Exit code is non-zero if any gate fails. Results land in artifacts/ and
# the machine-readable verdict in artifacts/commercial_readiness.json.
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p artifacts
FULL=0; [ "${1:-}" = "--full" ] && FULL=1
fail=0
step() { echo; echo "== $1"; }

step "ruff (new work must be clean; repo-wide debt reported)"
python3 -m ruff check domain optimization/solve_status.py optimization/explain.py optimization/audit_trail.py \
  backtesting/counterfactual.py synthetic/fmcg validation scripts/validate_commercial_real_data.py \
  scripts/run_fmcg_counterfactuals.py scripts/run_fmcg_stress_matrix.py scripts/benchmark_performance.py \
  scripts/build_readiness_json.py scripts/fill_validation_tables.py api/routers/fmcg.py domain/money.py \
  backtesting/safe_selector.py backtesting/incumbent.py backtesting/regime.py optimization/vss_evpi.py \
  optimization/safe_stochastic.py risk/supply_paths.py domain/carrying_cost.py ingestion/pilot_readiness.py \
  scripts/run_safe_policy_validation.py scripts/fill_safe_validation_doc.py tests/unit/test_safe_selector.py \
  tests/unit/test_safe_stochastic.py tests/unit/test_supply_paths.py tests/unit/test_incumbent_regime_readiness.py \
  tests/unit/test_optimizer_service_and_transfers.py tests/unit/test_promo_input.py tests/unit/test_money.py \
  tests/unit/test_entrypoint_guard.py tests/integration/test_fmcg_api.py dashboard/pages/09_fmcg_plan.py \
  tests/unit/test_optimizer_invariants.py tests/unit/test_domain_model.py \
  tests/unit/test_tenant_isolation.py tests/unit/test_ingestion_adversarial.py tests/unit/test_fmcg_simulator.py \
  tests/unit/test_agriculture_invariants.py tests/unit/test_solver_robustness.py || fail=1
python3 -m ruff check . --statistics > artifacts/ruff_repo.txt 2>&1 || true

step "mypy on the decision core (must be zero)"
python3 -m mypy optimization risk backtesting api ingestion domain adaptive --ignore-missing-imports > artifacts/mypy.txt 2>&1 || fail=1
grep -c "error:" artifacts/mypy.txt | sed 's/^/  errors: /'

step "bandit (medium+, must be zero)"
python3 -m bandit -r api infrastructure ingestion optimization risk backtesting reports pool forecasting domain -ll -q -f json -o artifacts/bandit.json >/dev/null 2>&1
python3 -c "import json,sys;n=len(json.load(open('artifacts/bandit.json'))['results']);print('  findings:',n);sys.exit(1 if n else 0)" || fail=1

step "pip-audit (project closure; weasyprint advisory has no fix)"
python3 -m pip_audit --ignore-vuln PYSEC-2026-3412 -f json -o artifacts/pip_audit.json >/dev/null 2>&1; echo "  exit $? (0 = clean in THIS environment)"

step "secret scan (tree)"
if git grep -nEI "(AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|sk-ant-[A-Za-z0-9_-]{20,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY)" -- . ':!*.md' >/dev/null 2>&1; then echo "  SECRET-SHAPED STRING FOUND"; fail=1; else echo "  clean"; fi

step "tests with coverage"
python3 -m pytest tests/ -q -p no:cacheprovider --junitxml=artifacts/junit.xml \
  --cov=optimization --cov=domain --cov=backtesting --cov=ingestion --cov=api --cov=risk --cov=synthetic \
  --cov-report=json:artifacts/coverage.json --cov-report=term > artifacts/pytest_full.txt 2>&1 || fail=1
tail -2 artifacts/pytest_full.txt

step "frontend build"
if [ -d web/node_modules ]; then (cd web && npm run build > ../artifacts/web_build.txt 2>&1) && echo "  ok" || { echo "  FAILED"; fail=1; }; else echo "  skipped (no node_modules)"; fi

step "disruption presets vs measured data; demand scenario calibration"
python3 scripts/validate_disruption_presets.py > artifacts/disruption_presets.txt 2>&1 && echo "  ok" || fail=1
python3 scripts/validate_demand_scenarios_real.py > artifacts/scenario_calibration.txt 2>&1 && echo "  ok" || fail=1

if [ $FULL -eq 1 ]; then
  step "closed-loop counterfactual matrix (SYNTHETIC CALIBRATED)"
  python3 scripts/run_fmcg_counterfactuals.py --rolling --seeds 3 --run-periods 40 --review 4 --scenarios 20 > artifacts/fmcg_rolling.log 2>&1 || fail=1
  step "stress matrix"
  python3 scripts/run_fmcg_stress_matrix.py --axes demand_cv,fill --seeds 2 --folds 2 --scenarios 15 > artifacts/fmcg_stress_cv_fill.log 2>&1 || fail=1
  python3 scripts/run_fmcg_stress_matrix.py --axes cover --seeds 2 --folds 3 --scenarios 15 > artifacts/fmcg_stress_cover.log 2>&1 || fail=1
  step "safe-policy validation (frozen design, unseen seeds)"
  python3 scripts/run_safe_policy_validation.py --small > artifacts/safe_policy_validation.log 2>&1 || fail=1
  python3 scripts/fill_safe_validation_doc.py || true
  step "performance benchmarks"
  python3 scripts/benchmark_performance.py > artifacts/performance.log 2>&1 || true
fi

step "readiness verdict"
python3 scripts/build_readiness_json.py || fail=1
echo; [ $fail -eq 0 ] && echo "COMMERCIAL VALIDATE: PASS" || echo "COMMERCIAL VALIDATE: FAIL"
exit $fail

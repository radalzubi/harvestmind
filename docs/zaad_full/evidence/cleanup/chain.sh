#!/bin/zsh
# Post-P4B cleanup: full validation on the cleanup tree. Suite in the fresh dependency closure first, then the frozen
# chain (same invocations as the P4B release audit, tags *_under_cleanup) and the P4 / P5 / P4B matrices.
set -o pipefail
export PYTHONPATH=. PYTHONHASHSEED=0
V=/private/tmp/claude-501/-Users-radalzubi-Desktop-harvestmind/ff795fbd-41f4-4af5-afd4-b87ad517d896/scratchpad/venv/bin/python
G=docs/zaad_full/evidence/cleanup/gates; E=docs/zaad_full/evidence
step() { echo "=== $1 $(date -u +%H:%M:%S)"; }
step "full pytest suite (fresh closure venv)"
$V -m pytest tests -q -p no:cacheprovider > $G/full_suite.log 2>&1; echo "suite_exit $?"
step "P3 shared-MOV snapshot identity"
python3 docs/zaad_full/evidence/cleanup/p3_snapshot_gate.py > $G/p3_snapshot.log 2>&1; echo "p3_snapshot_exit $?"
step "P1 canonical regression + invariants"
python3 -m scripts.zaad_canonical_regression > $G/p1_canonical.log 2>&1; echo "p1_canonical_exit $?"
python3 -m scripts.p1_invariants > $G/p1_invariants.log 2>&1; echo "p1_invariants_exit $?"
step "P2"
python3 -m scripts.p2_benchmark --tag p2_under_cleanup --workers 6 > $G/p2_benchmark.log 2>&1; echo "p2_benchmark_exit $?"
python3 -m scripts.p2_invariants --benchmark p2_under_cleanup > $G/p2_invariants.log 2>&1; echo "p2_invariants_exit $?"
python3 -m scripts.p2_decision_compare $E/p2/p2_perf_closure.jsonl $E/p2/p2_under_cleanup.jsonl --out p2_under_cleanup_compare > $G/p2_compare.log 2>&1; echo "p2_compare_exit $?"
step "sector"
python3 -m scripts.sector_benchmark --tag sector_under_cleanup --workers 6 > $G/sector_benchmark.log 2>&1; echo "sector_benchmark_exit $?"
python3 -m scripts.sector_invariants --benchmark sector_under_cleanup > $G/sector_invariants.log 2>&1; echo "sector_invariants_exit $?"
python3 -m scripts.p2_decision_compare $E/sectors/sector_perf_closure.jsonl $E/sectors/sector_under_cleanup.jsonl --policy gated --out sector_under_cleanup_compare > $G/sector_compare.log 2>&1; echo "sector_compare_exit $?"
step "P3"
python3 -m scripts.p3_benchmark --tag p3_under_cleanup --workers 6 > $G/p3_benchmark.log 2>&1; echo "p3_benchmark_exit $?"
python3 -m scripts.p3_invariants --benchmark p3_under_cleanup > $G/p3_invariants.log 2>&1; echo "p3_invariants_exit $?"
python3 -m scripts.p3_adversarial > $G/p3_adversarial.log 2>&1; echo "p3_adversarial_exit $?"
python3 -m scripts.p2_decision_compare $E/p3/p3_perf_closure.jsonl $E/p3/p3_under_cleanup.jsonl --out p3_under_cleanup_compare > $G/p3_compare.log 2>&1; echo "p3_compare_exit $?"
step "P4 matrices"
python3 -m scripts.p4_benchmark --tag p4_under_cleanup > $G/p4_benchmark.log 2>&1; echo "p4_benchmark_exit $?"
python3 -m scripts.p4_invariants --benchmark p4_under_cleanup > $G/p4_invariants.log 2>&1; echo "p4_invariants_exit $?"
python3 -m scripts.p4_adversarial > $G/p4_adversarial.log 2>&1; echo "p4_adversarial_exit $?"
step "P5 matrices"
python3 -m scripts.p5_benchmark --tag p5_under_cleanup > $G/p5_benchmark.log 2>&1; echo "p5_benchmark_exit $?"
python3 -m scripts.p5_integration --tag p5_integration_under_cleanup > $G/p5_integration.log 2>&1; echo "p5_integration_exit $?"
python3 -m scripts.p5_adversarial > $G/p5_adversarial.log 2>&1; echo "p5_adversarial_exit $?"
step "P4B matrices (identity against the production runtime checkout 1851f40)"
python3 -m scripts.p4b_benchmark --tag p4b_under_cleanup --pre-p4b-worktree /Users/radalzubi/Desktop/harvestmind-deploy > $G/p4b_benchmark.log 2>&1; echo "p4b_benchmark_exit $?"
python3 -m scripts.p4b_adversarial > $G/p4b_adversarial.log 2>&1; echo "p4b_adversarial_exit $?"
python3 -m scripts.p4b_release_audit > $G/p4b_release_audit.log 2>&1; echo "p4b_release_audit_exit $?"
step "P0 six-cell arm p4b_release (unchanged arm definition) vs router_cycle"
python3 -m scripts.p1_p0_arms p4b_release > $G/p0_arm.log 2>&1; echo "p0_arm_exit $?"
python3 -m scripts.p1_ownership_compare router_cycle p4b_release > $G/p0_compare.log 2>&1; echo "p0_compare_exit $?"
step "CHAIN_DONE"

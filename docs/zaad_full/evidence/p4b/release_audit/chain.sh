#!/bin/zsh
# P4B V1 release audit: frozen P0-P5 regression chain on the audit tree (same chain as the P4 / P5 closures).
# usage: zsh docs/zaad_full/evidence/p4b/release_audit/chain.sh   (from the audit worktree)
set -o pipefail
export PYTHONPATH=. PYTHONHASHSEED=0
G=docs/zaad_full/evidence/p4b/release_audit/gates; mkdir -p $G
E=docs/zaad_full/evidence
step() { echo "=== $1 $(date -u +%H:%M:%S)"; }
step "P3 shared-MOV production snapshot identity (no option declared)"
python3 $G/../p3_snapshot_gate.py > $G/p3_snapshot.log 2>&1; echo "p3_snapshot_exit $?"
step "P1 canonical regression"
python3 -m scripts.zaad_canonical_regression > $G/p1_canonical.log 2>&1; echo "p1_canonical_exit $?"
step "P1 invariants"
python3 -m scripts.p1_invariants > $G/p1_invariants.log 2>&1; echo "p1_invariants_exit $?"
step "P2 benchmark"
python3 -m scripts.p2_benchmark --tag p2_under_p4brel --workers 6 > $G/p2_benchmark.log 2>&1; echo "p2_benchmark_exit $?"
python3 -m scripts.p2_invariants --benchmark p2_under_p4brel > $G/p2_invariants.log 2>&1; echo "p2_invariants_exit $?"
python3 -m scripts.p2_decision_compare $E/p2/p2_perf_closure.jsonl $E/p2/p2_under_p4brel.jsonl --out p2_under_p4brel_compare > $G/p2_compare.log 2>&1; echo "p2_compare_exit $?"
step "sector physics benchmark"
python3 -m scripts.sector_benchmark --tag sector_under_p4brel --workers 6 > $G/sector_benchmark.log 2>&1; echo "sector_benchmark_exit $?"
python3 -m scripts.sector_invariants --benchmark sector_under_p4brel > $G/sector_invariants.log 2>&1; echo "sector_invariants_exit $?"
python3 -m scripts.p2_decision_compare $E/sectors/sector_perf_closure.jsonl $E/sectors/sector_under_p4brel.jsonl --policy gated --out sector_under_p4brel_compare > $G/sector_compare.log 2>&1; echo "sector_compare_exit $?"
step "P3 benchmark"
python3 -m scripts.p3_benchmark --tag p3_under_p4brel --workers 6 > $G/p3_benchmark.log 2>&1; echo "p3_benchmark_exit $?"
python3 -m scripts.p3_invariants --benchmark p3_under_p4brel > $G/p3_invariants.log 2>&1; echo "p3_invariants_exit $?"
python3 -m scripts.p3_adversarial > $G/p3_adversarial.log 2>&1; echo "p3_adversarial_exit $?"
python3 -m scripts.p2_decision_compare $E/p3/p3_perf_closure.jsonl $E/p3/p3_under_p4brel.jsonl --out p3_under_p4brel_compare > $G/p3_compare.log 2>&1; echo "p3_compare_exit $?"
step "P0 six-cell arm p4b_release"
python3 -m scripts.p1_p0_arms p4b_release > $G/p0_arm.log 2>&1; echo "p0_arm_exit $?"
python3 -m scripts.p1_ownership_compare router_cycle p4b_release > $G/p0_compare.log 2>&1; echo "p0_compare_exit $?"
step "CHAIN_DONE"

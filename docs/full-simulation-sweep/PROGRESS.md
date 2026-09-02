# Full Synthetic Simulation Sweep — Progress

- [x] Isolated branch from the fill-replay correction.
- [x] Audited benchmark, Indiana generator, Croston routing and copula layer.
- [x] Documented methodology, assumptions and primary references.
- [x] Correct zero-demand settlement and median calculation.
- [x] Add controlled generator inputs.
- [x] Wire leakage-safe correlated training scenarios.
- [x] Build Grid A and Grid B runner with per-run output.
- [x] Add focused tests and forced-fill control.
- [x] Run 120 Grid A, 75 Grid B and 5 control cells; publish every run.
- [x] Harden the commercial gate with the configured 90% service floor.
- [x] Run full regression suite: 1,062 passed after the service-gate hardening.
- [x] Ruff-clean every touched file. A repository-wide scan still reports 165
  pre-existing findings outside this branch; they were not mechanically
  rewritten as part of the simulation scope.

## Result snapshot

- Fixed 1.30x/30% fill curve: +4.36% (0.99), -4.08% (0.95),
  +10.91% (0.85), +18.92% (0.70), conventional medians over five seeds.
- The decay hypothesis is directional, not monotonic. The 0.95 trough is a
  regime transition requiring real-history investigation.
- Correlation targets are realized, but SP edge is not monotonic in tau;
  correlated-shortfall value is not demonstrated.
- Scale leaves percentage edge unchanged, as expected.
- Sparse-demand cost improvements trade away service; the hardened gate rejects
  sub-90% service rather than presenting it as commercial savings.

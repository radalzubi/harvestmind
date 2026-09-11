# Three-sector physics: authoritative results

Run `sector_authoritative` (`sector_authoritative.jsonl` / `.summary.json` / `.tables.md`, console
`sector_authoritative.log`) at code `8b7aadc` (runtime code `43d769f`): the pre-registered fixture
matrix (`SECTOR_PHYSICS_FIXTURE_SPEC.md`, unchanged after the specification date), seeds 41001 /
41002, five policies, eight rolling reviews, the P2 rules and scoring, four workers. Synthetic
throughout: **ENGINEERING VALIDATED, not real-data validated.**

## Gates

**26 / 26 fixtures PASS** the economic gate (ZAAD within the pre-registered tolerance of the best
valid baseline), the service gate (no branch worse than min(target, incumbent) - .01; unavoidable
shortage only where the incumbent starves too), the structural gates (conservation residual
<= 1e-9, no reverse pairs, no physical failure, no required-candidate starvation) and the fixture's
own principle. Solve statuses over every ZAAD candidate: 1,829 OPTIMAL, 198 INFEASIBLE (service
floors provably unattainable on a candidate class), 0 time-limited.

| fixture | best baseline | ZAAD gap | tol | ZAAD min branch service | incumbent | abstained / 8 | wall p50 / max s | principle |
|---|---|---|---|---|---|---|---|---|
| C1 case-pack rounding | independent | +1.07% | 2% | .983 | .983 | 6.5 | 9.5 / 59.5 | every purchase a multiple of 12 (PASS) |
| C2 pallet / load threshold | independent | -0.07% | 2% | .988 | .978 | 5 | 3.5 / 11.4 | no order above 8 pallets or 2,200 weight (PASS) |
| C3 MOQ / MOV | independent | -0.53% | 2% | 1.000 | .992 | 0.5 | 3.8 / 8.2 | no order between 0 and MOQ, every order >= MOV (PASS) |
| C4 long import lead | network_rop | +0.02% | 2% | .980 | .975 | 3.5 | 0.5 / 1.0 | not worse (PASS) |
| C5 variable supplier arrival | independent | +2.11% | 3% | .773 | .773 | 8 | 0.7 / 1.8 | not worse, no avoidable starvation (PASS; frozen-engine property, dev log entry 5) |
| C6 storage capacity | independent | +0.38% | 2% | .978 | .978 | 7.5 | 0.3 / 0.8 | no capacity breach (PASS) |
| C7 no material improvement | echelon_base_stock | +0.11% | 2% | .985 | .984 | 7.5 | 0.3 / 0.6 | abstains >= 6 (PASS) |
| P1 fresh, no unnecessary purchase | independent | +0.88% | 2% | .981 | .977 | 6 | 1.7 / 4.3 | no purchase on the first two reviews (PASS) |
| P2 near-expiry inventory | independent | +0.67% | 3% | .981 | .924 | 5.5 | 2.9 / 8.1 | acts at review 0, north service 1.00 against the incumbent's .90 (PASS) |
| P3 age at receipt | independent | +1.67% | 3% | .977 | .992 | 0 | 2.3 / 20.9 | buys from the fresh local source; expired 21 / 6 units against the incumbent's 200 / 200 (PASS) |
| P4 transfer becomes useless | independent | -0.19% | 3% | .983 | .795 | 0.5 | 3.0 / 19.2 | south moved no more than the incumbent, north served (PASS) |
| P5 spoilage against service | independent | +1.27% | 3% | .962 | .963 | 5.5 | 0.7 / 1.3 | not worse (PASS) |
| P6 uncertain usable yield | echelon_base_stock | +0.02% | 3% | .944 | .945 | 3.5 | 8.2 / 16.5 | service kept under the yield uncertainty (PASS) |
| P7 FEFO settlement | network_rop | +0.00% | 3% | .978 | .978 | 7.5 | 2.2 / 3.3 | FEFO and sellable-life consumption (invariants 05, 03, 15) (PASS) |
| P8 no material improvement | echelon_base_stock | +0.09% | 2% | .986 | .983 | 7.5 | 2.1 / 5.4 | abstains >= 5 (PASS) |
| M1 chilled shelf life | independent | +0.22% | 3% | .961 | .875 | 3 | 0.7 / 0.9 | not worse; expired 166 / 117 against the incumbent's 215 / 129 (PASS) |
| M2 frozen shelf life | independent | +0.98% | 2% | .978 | .978 | 6.5 | 0.3 / 0.6 | not worse (PASS) |
| M3 storage-state infeasibility | network_rop | +0.00% | 3% | .000 | .000 | 8 | 0.3 / 0.5 | never held at or shipped to south; south's frozen demand is unavoidable (PASS) |
| M4 cold-chain lane | network_rop | -0.01% | 3% | .978 | .978 | 7.5 | 1.7 / 3.6 | ambient lane never used (PASS) |
| M5 aging against service | independent | +2.51% | 3% | .962 | .975 | 4 | 0.8 / 1.6 | not worse (PASS) |
| M6 transfer of a usable lot | independent | +1.32% | 3% | .882 | .864 | 7 | 1.3 / 2.5 | lot moved to north at review 0 (PASS) |
| M7 transfer rejected by expiry | independent | -0.41% | 3% | .775 | .711 | 5.5 | 1.2 / 2.7 | expiring lot not moved; explanation states the remaining life (PASS) |
| M8 no material improvement | echelon_base_stock | +0.11% | 2% | .985 | .984 | 7.5 | 0.3 / 0.6 | abstains >= 6 (PASS) |
| X1 commercial + produce | independent | -0.05% | 3% | .978 | .970 | 7 | 1.4 / 3.0 | A unaffected by B's expiry, capacity respected (PASS) |
| X2 produce + frozen seafood | echelon_base_stock | +0.04% | 3% | .956 | .956 | 8 | 1.3 / 3.1 | shared capacity respected, frozen never expires (PASS) |
| X3 three sectors | independent | +0.38% | 3% | .000 | .000 | 8 | 2.1 / 3.5 | frozen SKU never at south, others unaffected (PASS) |

Both minimum-service zeros (M3, X3) are the frozen SKU's service at the chilled-only south branch,
which no policy can serve; every other branch of those fixtures is served at target.

## What the physics did (settled on the truth, both seeds)

* Produce near-expiry (P2): the incumbent counts 150 physical units per branch that have one
  sellable period left and does nothing; ZAAD buys and transfers at review 0 and holds north at
  1.00 against the incumbent's .90.
* Age at receipt (P3): imports arrive with three of six periods; ZAAD buys the fresher local source
  for part of the demand and expires 21 and 6 units over eight reviews where the incumbent expires 200.
* Useless transfers (P4): a three-period lane leaves one sellable period at south; ZAAD moves no
  more than the incumbent over that lane and serves north .983 against the incumbent's .795.
* Cold chain (M3, M4): no frozen unit at a chilled-only branch, no chilled unit on an ambient lane;
  the reefer lane carries everything to south at three times the cost.
* Expiring lot (M7): the 300-unit central lot with two periods left is not moved (it would arrive at
  the threshold); the plan buys instead and the explanation says so in operator terms.
* Commercial: every purchase a whole case (C1), no shipment above eight pallets or the weight cap
  (C2), no order below the MOQ or the MOV (C3), capacity never breached (C6); on calm fixtures ZAAD
  abstains on 6-8 of 8 reviews (C7, M8, P8).

## Frozen behaviour under the sector code

* P2 authoritative matrix re-run unchanged under the sector code (`p2_under_sectors`,
  `p2_final_under_sectors.*`): 20 / 20 fixtures, 18 / 18 principles, runtime p50 0.5 s / p95 6.5 s /
  max 14.5 s, and **344 / 344 ZAAD reviews decision-identical** to the P2 release record
  (`p2_under_sectors_compare.json`).
* Canonical regression (B / T / Q / A twelve-review identity, P0 cell 15) PASS at every step.
* P0 six-cell arm and P1 invariants: `gates/` (closeout).

## Not claimed

No commercial validation, no real-world savings, no calibration to operator data. The fixtures
are synthetic and the tolerances are engineering gates.

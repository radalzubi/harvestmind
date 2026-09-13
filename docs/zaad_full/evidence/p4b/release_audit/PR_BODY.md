## P4B V1 open PO / commitment intervention — release (audited)

Authoritative release PR: the P4B V1 implementation (PR #75, product `a6483ab`, tested head `7311d00`) plus the release-audit corrections and evidence. Supersedes PR #75, which is not merged independently.

| item | value |
|---|---|
| starting `main` | `5dc87b4` |
| implementation product / tested CI head | `a6483ab` / `7311d00` (CI run 34759841637 green) |
| audit-corrected product | `28c1fa7` (tag `p4b-v1-frozen-product`) |
| audit evidence | tag `p4b-v1-frozen` (tag `p4b-v1-frozen`) |
| record | `docs/zaad_full/evidence/p4b/release_audit/P4B_RELEASE_AUDIT.md` |

### Corrections (smallest scope, no model / P4 / P3 / probability / tolerance change)
R1 adapter normalisation boundary with `commitments:` refusals; R2 option-set bounds (12 per order, 200 non-keep; 413 interactive, x4 batch); R3 split floor as a sum of clipped cancel caps + guarded settlement floor check; R4 credit on cancel options only; R5 block 1.1 (`commitment_action`, `commitment_verdict`, `commitment_value_vs_keep`, `overall_plan_status`, `plan_changes_outside_commitments`, `reading`); R6 pre-existing production defect (numpy bool in `service_reliability`, `/plan` 500 on `2fc7b50`) cast to `bool`.

### Validation counts
Release-audit cases 35 / 35; fixtures 21 / 21 (F00 identical to `2fc7b50`); adversarial 16 / 16; invariants all; profile structurally identical (850 / 300 / 122 nodes); suite 1,979 passed, 2 skipped; ruff / mypy / bandit clean; frozen chain: P3 snapshot identical (18 HiGHS calls), P1 canonical PASS + invariants 0 failures, P2 1,720 / 1,720 (15 load-time-limit reviews rerun quiet: 280 / 280), sector 416 / 416, P3 2,304 / 2,304, P0 arm 120 / 120.

### Known limitations
Here-and-now, scenario-invariant; no V2 node-indexed amendments, no REROUTE, no supplier execution (approval-only, `executable_amendment` false); declaration-dependent; plan-level value attribution; cancel caps sum inside the floor under split; cancel-only credits; engineering-validated, not real-data validated.

### Deployment plan
After required CI (all twelve ZAAD jobs; CodeQL is a repository-level condition, not a gate): merge with a merge commit, deploy `zaad-api` from a clean detached checkout of the merge SHA (`fly deploy --image-label canonical-<sha> --strategy rolling`), production smoke (`docs/zaad_full/evidence/p4b/release/smoke_p4b.py`), log inspection, then tag `p4b-v1-release-runtime`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

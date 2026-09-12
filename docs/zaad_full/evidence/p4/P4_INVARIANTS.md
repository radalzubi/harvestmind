# P4 invariants

Benchmark: `p4_perf_closure`. **27 / 27 PASS**

| invariant | statement | result | evidence |
|---|---|---|---|
| 01_no_anticipation | Before the first epoch every world's plan equals the here-and-now plan; after it, worlds of one set share the plan (structural check on solved values). | PASS | "structural check passed on 4 fixtures" |
| 02_same_information_same_decision | Two worlds with identical observable histories map to the same information set at every epoch (N3, W2). | PASS | {"N3_zero_information": {"3": 1}, "W2_no_benefit": {"3": 1}} |
| 03_set_probabilities_sum | Information-set probabilities equal the sums of member weights and sum to one per epoch. | PASS | "sums exact on 2 fixtures" |
| 04_world_probabilities_preserved | The tree worlds' weights sum to one and every branch keeps its history weight split evenly over its continuations. | PASS | {"total": 1.0, "worlds": 6} |
| 05_static_feasible | The static comparator is a feasible static plan under the frozen rows (usable) wherever a static plan exists. | PASS | {"A1_demand_visible_at_epoch": "OPTIMAL", "I1_p1_fixed_cost_lots": "OPTIMAL", "I4_p3_shares_hold": "OPTIMAL"} |
| 06_adaptive_feasible_every_world | Every represented world settles under its own policy plan (no physical violation, no guidance truncation). | PASS | "125 world settlements clean" |
| 07_committed_stays_committed | Purchases before the first epoch are identical in every world's plan and equal the here-and-now plan (no cancellation, no retroactive change). | PASS | {"committed_periods": [0, 1, 2], "worlds": 4} |
| 08_no_negative_inventory | Settlement of every world plan reports no negative stock (settlement raises on any physical violation). | PASS | "125 world settlements clean" |
| 09_network_conservation | On the P2 recourse fixture the settled conservation residual is zero in every world. | PASS | {"worst_residual": 9.521272659185342e-13} |
| 10_no_double_allocation | Period-0 transfers of the adaptive plan never exceed opening stock at the origin (settlement strict at period zero, every world). | PASS | {"worst_residual": 9.521272659185342e-13} |
| 11_source_capacity | No branch buys above a source's capacity or maximum (I3, I6). | PASS | "clean" |
| 12_shared_supplier_capacity | Shared resources hold in every branch (I6). | PASS | "clean" |
| 13_moq |  | PASS | "clean" |
| 14_mov | Every branch's supplier order meets the MOV or is absent (shared supplier orders counted once per node). | PASS | {"status": "OPTIMAL", "worlds": 4} |
| 15_packs |  | PASS | "whole packs in every branch" |
| 16_share_constraints |  | PASS | "shares hold in every branch" |
| 17_transfer_lead_time | A recourse transfer decided at epoch e cannot arrive before e + lane lead (columns exist only for t >= e; arrival = t + lead). | PASS | "every recourse transfer departs at or after its epoch" |
| 18_sector_physics | Sector fixtures settle in every world (physics enforced by the same rows and settlement). | PASS | "clean" |
| 19_shelf_life_fefo | Produce fixture: no world plan settles with expired sales (settlement's FEFO and life rules). | PASS | "clean" |
| 20_cold_chain | Meat / seafood fixture: every world plan settles under the cold-chain and receipt-life rules. | PASS | {"status": "OPTIMAL", "worlds": 4} |
| 21_approval_required |  | PASS | "NO MATERIAL ADAPTIVE BENEFIT" |
| 22_no_executable_po |  | PASS | "NO MATERIAL ADAPTIVE BENEFIT" |
| 23_perfect_le_adaptive | PI <= adaptive on every fixture whose perfect-information solve is CERTIFIED (status OPTIMAL); a
feasible time-limited PI incumbent is not a bound and is listed, not compared (release audit blocker A). | PASS | "PI <= adaptive on 25 certified PI solves; non-certified (not compared): ['S1_commercial_packs']" |
| 24_adaptive_le_static |  | PASS | "adaptive <= static wherever a static plan exists" |
| 25_disabled_is_frozen |  | PASS | "reports identical up to timings and the request hash" |
| 26_signature_order_independent | Reversing the world order changes no information-set membership signature and no probability. | PASS | "signatures, probabilities and memberships invariant under world reordering" |
| 27_signature_uses_no_future | Changing any world's demand at or after the epoch never changes its signature at that epoch. | PASS | "epoch 3: future demand doubled, signature unchanged" |

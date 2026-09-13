# P4B V1 release-audit cases

35 / 35 PASS

| case | result | evidence |
|---|---|---|
| B1 refundable fraction 1, partial cancel | PASS | {"amendments": {"keep": 40.0, "cancel": 60.0}, "commitment_credit": -120.0, "opening_assets": 550.0, "action": "REDUCE"} |
| B2 refundable fraction between 0 and 1 | PASS | {"credit_1_accepted": true, "credit_1.5": "1 validation error for Request\npipeline.0\n  Value error, commitments: option cancel credits 1.5 per unit above the  |
| B3 split with mixed keep / cancel | PASS | {"amendments": {"keep": 40.0, "cancel": 60.0}, "commitment_credit": -60.0, "cancel_fee": 15.0, "action": "REDUCE"} |
| B4 credit exactly at the bound | PASS | {"bound": 0.5, "credit": 0.5} |
| B5 credit epsilon above the bound | PASS | {"plus_1e-6": "1 validation error for Request\npipeline.0\n  Value error, commitments: option cancel credits 0.500001 per unit above the refundable deposit 0.5  |
| B6 cancel fee above the refund | PASS | {"amendments": {"cancel": 100.0}, "cancel_fee": 300.0, "commitment_credit": -200.0, "action": "CANCEL"} |
| B7 refund above the fee never manufactures value | PASS | {"cancelled": 100.0, "net_cash_per_unit": -1.75, "invoice_avoided": 530.0, "opening_assets_equal": true} |
| B8 no deposit + positive refund | PASS | "1 validation error for Request\npipeline.0\n  Value error, commitments: option cancel credits 1.0 per unit above the refundable deposit 0.0 (prepaid 0.0 x refu |
| B9 deposit with no refund right | PASS | {"credit_refused": "1 validation error for Request\npipeline.0\n  Value error, commitments: option cancel credits 1.0 per unit above the refundable deposit 0.0  |
| B10 several credit options, one selectable | PASS | {"amendments": {"c1": 100.0}, "commitment_credit": -200.0, "action": "CANCEL"} |
| B11 credit on a non-cancel option | PASS | {"defer": "1 validation error for Request\npipeline.0.options.1\n  Value error, commitments: option defer (de_expedite) carries a credit; a refund is declared o |
| C1 vault stage case normalised, unknown refused | PASS | {"normalised": "in_transit", "unknown": "commitments: order po1 declares stage 'teleported' outside the vocabulary ['placed', 'ordered', 'confirmed', 'in_produc |
| C2 every released writer inside the vocabulary | PASS | {"writers": {"workspace": ["ordered", "received"], "replay": ["placed"], "demo": ["confirmed"], "atp_integration_fixtures": ["ordered"], "p2_perf_snapshots": [" |
| D1 F14: KEEP with PENDING_REVIEW | PASS | {"overall_plan_status": "PENDING_REVIEW", "commitment_action": "KEEP", "commitment_value_vs_keep": 0.0, "plan_level_value": 332.586, "outside": [{"kind": "purch |
| D2 mixed-phase defer next to an alternate purchase | PASS | {"overall_plan_status": "PENDING_REVIEW", "commitment_action": "KEEP", "verdict": "NO MATERIAL COMMITMENT IMPROVEMENT AVAILABLE", "outside": [{"kind": "purchase |
| D3 recommended reading names the order | PASS | {"reading": "Commitment verdict: COMMITMENT CHANGE RECOMMENDED - CANCEL po1 (100.0 units); the value is the whole plan's against the KEEP incumbent. Approval re |
| E1a material on inventory, not on cost (released standard) | PASS | {"status": "PENDING_REVIEW", "value": 0.267, "cost_delta_fraction": -0.0003751077277930979, "inventory_delta_fraction": -0.13513513513513511, "better_on": ["inv |
| E1b below materiality on every dimension | PASS | {"status": "RETAIN_INCUMBENT", "value": 0.0, "cost_delta_fraction": -0.004064977910852583, "inventory_delta_fraction": -0.004379562043795521, "material": false, |
| E2 incumbent keeps, candidates free | PASS | {"incumbent": {"keep": 100.0}, "selected": {"cancel": 100.0}, "incumbent_label": null} |
| E3 economically neutral tie -> KEEP | PASS | {"status": "RETAIN_INCUMBENT", "value": 0.0, "amendments": {"keep": 100.0}} |
| E4 two identical amendments, deterministic | PASS | {"identical_runs": 3, "distinct_blocks": 1, "amendments": {"c2": 100.0}} |
| E5 feasible option alone is no recommendation | PASS | {"eligible_options": ["cancel", "defer", "expedite"], "action": "KEEP"} |
| F1 cross-tenant identifier collision | PASS | {"tenant_b_sees": "nothing (KEEP-only)", "tenant_a_without_the_order": "commitments: declared options for open orders the workspace does not carry: ['po1']"} |
| F2 duplicate declaration rows | PASS | "commitments: order po1 declares the same option id more than once" |
| F3 oversized declaration set | PASS | {"adapter": "commitments: order po1 declares 12 amendment options, over the limit 11", "api_interactive": "an order declares 13 options, over the limit 12"} |
| F4 invalid provenance / impossible date | PASS | {"provenance": "commitments: option c of order po1 declares provenance 'guess' outside ['CONTRACT', 'OPERATOR_DECLARED', 'CONFIGURED_ASSUMPTION']", "past_deadli |
| F5 NaN / inf / negative / huge | PASS | {"nan_fee": "1 validation error for Request\npipeline.0.options.1.fee_per_unit\n  Input should be a finite number", "inf_fee": "1 validation error for Request\n |
| F6 no execution path | PASS | {"routes": ["/api/zaad/network/schema", "/api/zaad/network/fixture", "/api/zaad/network/plan", "/api/zaad/network/request/from-workspace", "/api/zaad/network/pl |
| G1 full cancel only when the floor is zero | PASS | {"floor_1": "1 validation error for Request\npipeline.0\n  Value error, commitments: cancel option cancel may cancel 100.0 but the order may not fall below 1.0  |
| G2 boundary around tolerance | PASS | {"minimum_40+1e-6": "1 validation error for Request\npipeline.0\n  Value error, commitments: cancel option cancel may cancel 60.0 but the order may not fall bel |
| G3 sum of caps under split | PASS | {"split": "1 validation error for Request\npipeline.0\n  Value error, commitments: PO po1 allows split amendments and its cancel options together may cancel 80. |
| G4 settlement floor (contract bypassed) | PASS | "PO reduced below its declared minimum remaining quantity" |
| H1 fee / credit / procurement charged once | PASS | {"cancel_fee": 0.0, "commitment_credit": -200.0, "procurement": 0.0, "po_invoice": 0.0, "purchases": 0, "opening_assets": 1200.0} |
| H2 economics reconciles the block | PASS | {"value": 122.404, "ordering_delta": 10.0, "de_expedite_fee": {"selected": 10.0, "incumbent": 0.0}} |
| H3 model objective vs settlement | PASS | {"model_cancel": 100.0, "settlement_cancel_fee": 25.0, "settlement_total": 744.0} |

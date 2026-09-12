# P3 adversarial inputs

23 / 23 fail safely

Every case is built on a valid two-source request and mutated; REFUSED_AT_CONTRACT is a pydantic / validator ValueError (HTTP 422 on the API before any model is built); HANDLED means the frozen model or contract bounds the case by construction.

| case | outcome | result | detail |
|---|---|---|---|
| duplicate source ids | REFUSED_AT_CONTRACT | PASS | ["1 validation error for Request", "Value error, duplicate entity ID / unresolved PO revisions [type=value_error, input_value={'schema_version': 'zaad....D'}]}, 'recourse': None}, input_type=dict]"] |
| two options with the same id and conflicting terms | REFUSED_AT_CONTRACT | PASS | ["1 validation error for Request", "Value error, duplicate entity ID / unresolved PO revisions [type=value_error, input_value={'schema_version': 'zaad....D'}]}, 'recourse': None}, input_type=dict]"] |
| negative capacity | REFUSED_AT_CONTRACT | PASS | ["1 validation error for Request", "Value error, invalid source capacity [type=value_error, input_value={'known_at': '2026-09-06T...sive_quote_group': None}, input_type=dict]"] |
| negative unit cost | REFUSED_AT_CONTRACT | PASS | ["1 validation error for Request"] |
| negative pack size | REFUSED_AT_CONTRACT | PASS | ["1 validation error for Request"] |
| zero pack size | HANDLED_BY_CONTRACT | PASS | "a zero pack size is the declared continuous pack (frozen contract); it creates no integer column" |
| minimum share above maximum share | REFUSED_AT_CONTRACT | PASS | ["1 validation error for Request", "Value error, share constraint src_B: minimum share above maximum share [type=value_error, input_value={'sku': 'A', 'destination...e': 'OPERATOR_DECLARED'}, input_type=dict]"] |
| minimum shares summing above 100 % | REFUSED_AT_CONTRACT | PASS | ["1 validation error for Request", "Value error, sourcing: minimum shares for A at central sum above 100 % [type=value_error, input_value={'schema_version': 'zaad....D'}]}, 'recourse': None}, input_type=dict]"] |
| source not qualified for the SKU carrying a minimum share | REFUSED_AT_CONTRACT | PASS | ["1 validation error for Request", "Value error, sourcing: source src_B is not qualified (approved and cleared) and cannot carry a minimum share or committed units [type=value_error, input_value={'schema_version': 'zaad....D'}]}, 'recourse': None}, input_type=dict]"] |
| unknown supplier in a risk group | REFUSED_AT_CONTRACT | PASS | ["1 validation error for Request", "Value error, sourcing: risk group g names unknown source 'src_ghost' [type=value_error, input_value={'schema_version': 'zaad....D'}]}, 'recourse': None}, input_type=dict]"] |
| unknown SKU in a share constraint | REFUSED_AT_CONTRACT | PASS | ["1 validation error for Request", "Value error, sourcing: share constraint for src_B names ZZZ at central, but the source supplies A to central [type=value_error, input_value={'schema_version': 'zaad....D'}]}, 'recourse': None}, input_type=dict]"] |
| risk group without provenance | REFUSED_AT_CONTRACT | PASS | ["1 validation error for Request", "Value error, risk group g: a declared dependency needs a provenance other than UNKNOWN [type=value_error, input_value={'id': 'g', 'kind': 'PLAN...'provenance': 'UNKNOWN'}, input_type=dict]"] |
| contradictory cold-chain state (frozen SKU, chilled-only locations) | REFUSED_AT_CONTRACT | PASS | ["1 validation error for Request", "Value error, sku physics A: no location can hold storage state FROZEN [type=value_error, input_value={'schema_version': 'zaad....D'}]}, 'recourse': None}, input_type=dict]"] |
| impossible MOV / capacity combination | HANDLED_BY_MODEL | PASS | "supplier_b (capacity 100 units, MOV 6000) receives 0 units: the order binary cannot open" |
| total group correlation above one (non-PSD equivalent) | REFUSED_AT_CONTRACT | PASS | ["1 validation error for Request", "Value error, sourcing: source src_A has a total group correlation of 1.200 above 1; the shock cannot keep its marginal [type=value_error, input_value={'schema_version': 'zaad....D'}]}, 'recourse': None}, input_type=dict]"] |
| duplicated risk groups | REFUSED_AT_CONTRACT | PASS | ["1 validation error for Request", "Value error, sourcing: risk group h duplicates another group's members [type=value_error, input_value={'schema_version': 'zaad....D'}]}, 'recourse': None}, input_type=dict]"] |
| single-member risk group | REFUSED_AT_CONTRACT | PASS | ["1 validation error for Request"] |
| infinite unit price | REFUSED_AT_CONTRACT | PASS | ["1 validation error for Request", "Input should be a finite number [type=finite_number, input_value=inf, input_type=float]"] |
| NaN freight | REFUSED_AT_CONTRACT | PASS | ["1 validation error for Request", "Input should be a finite number [type=finite_number, input_value=nan, input_type=float]"] |
| infinite capacity | REFUSED_AT_CONTRACT | PASS | ["12 validation errors for Request", "Input should be a finite number [type=finite_number, input_value=inf, input_type=float]"] |
| extreme source count (66 for one pair) | REFUSED_AT_CONTRACT | PASS | ["1 validation error for Request", "Value error, sourcing: 66 sources for A at central; at most 64 [type=value_error, input_value={'schema_version': 'zaad....D'}]}, 'recourse': None}, input_type=dict]"] |
| switching cost on an unknown source | REFUSED_AT_CONTRACT | PASS | ["1 validation error for Request", "Value error, sourcing: switching cost for unknown source 'src_ghost' [type=value_error, input_value={'schema_version': 'zaad....D'}]}, 'recourse': None}, input_type=dict]"] |
| committed units above the source's capacity | REFUSED_AT_CONTRACT | PASS | ["1 validation error for Request", "Value error, sourcing: committed units 1000 for src_B exceed its capacity over the horizon (120) [type=value_error, input_value={'schema_version': 'zaad....D'}]}, 'recourse': None}, input_type=dict]"] |

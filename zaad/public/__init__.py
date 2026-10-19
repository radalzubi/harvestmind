"""Public-dataset evaluation harnesses for the frozen ZAAD planning core.

Nothing under this package touches an operator vault, the `stg_fmcg_*` staging tables, the workspace adapter or
the optimizer. Each dataset gets its own loader (into a dedicated DuckDB file), a declared-assumption manifest, a
request builder onto `zaad.full.contracts.Request`, truth construction for `zaad.full.replay.replay`, and a
benchmark script that keeps every instance's result, including failures. Evidence classes used throughout:

    OBSERVED     a value present in the source files
    DERIVED      a documented transformation of observed values
    SYNTHETIC    an explicit modelling assumption (every supply-side and economic input of a public dataset)
    UNAVAILABLE  information the dataset cannot provide

No result produced here is a realized saving, a customer outcome or operator validation.
"""

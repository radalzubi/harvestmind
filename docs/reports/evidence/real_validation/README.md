# Raw evidence for REAL_DATA_VALIDATION_PROJECT_B.md

Committed because the report quotes these numbers and `outputs/` is
gitignored. Regenerate everything with:

```
python3 scripts/fetch_real_data.py
./scripts/run_real_validation_suite.sh
./scripts/run_paired_scenario_test.sh
python3 scripts/validate_disruption_presets.py
python3 scripts/validate_demand_scenarios_real.py
python3 scripts/summarize_real_validation.py
```

| file | what it is |
|---|---|
| `A_full_history.txt` | 1,028 folds, 1994-2026, real demand path |
| `B_real_supply.txt` | 2019-2026, real demand and real route supply shocks |
| `C_cover_*.txt` | opening-stock sensitivity, the parameter that decides the answer |
| `D_cap_*.txt` | warehouse-capacity sensitivity |
| `E_idio0.txt` | synthetic SKU noise removed, real signal alone |
| `F_shocks_on/off.txt` | controlled experiment: measured supply shocks toggled |
| `G_seasonal_scen/iid_scen.txt` | controlled experiment: scenario generator swapped |
| `H_disruption_presets.txt` | presets confronted with satellite data |
| `I_scenario_calibration.txt` | WIS, PIT coverage and interval scores on 4,404 real origin-horizon pairs |
| `folds_*.csv` | one row per fold, so runs can be compared PAIRED rather than by two medians over two different fold sets |
| `SUMMARY_TABLE.txt` | every run in one table |

`G_iid_scen.txt` reproduces `F_shocks_on.txt` exactly, which is the
harness's own reproducibility check: identical settings, identical result.

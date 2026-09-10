#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.."
OUT=outputs/real_validation
V=scripts/validate_commercial_real_data.py
C="--seeds 7,19,33,41,53,61,73 --start 2019-01 --train-months 30 \
--scenarios 30 --skus 40 --suppliers 14 --stride 1 --opening-cover 1.0 \
--real-supply-only"
python3 $V $C --csv "$OUT/folds_seasonal.csv" > "$OUT/G_seasonal_scen.txt" 2>&1
echo "  seasonal done"
python3 $V $C --iid-scenarios --csv "$OUT/folds_iid.csv" > "$OUT/G_iid_scen.txt" 2>&1
echo "  iid done"
python3 $V $C --flat-supply --csv "$OUT/folds_flat.csv" > "$OUT/F_shocks_off.txt" 2>&1
echo "  flat-supply done"

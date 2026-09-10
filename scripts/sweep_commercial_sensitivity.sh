#!/usr/bin/env bash
# Sensitivity of the real-data commercial backtest to the two parameters
# that decide the answer: how much stock the operator starts with, and how
# much the warehouse can hold. Both are reported rather than chosen.
set -u
cd "$(dirname "$0")/.."
OUT=outputs/real_validation
mkdir -p "$OUT"
for cover in 0.0 0.5 1.0 1.5 2.0; do
  python3 scripts/validate_commercial_real_data.py \
    --seeds 7,19,33 --start 1994-01 --train-months 36 --scenarios 20 \
    --skus 30 --suppliers 12 --stride 4 --opening-cover "$cover" \
    > "$OUT/C_cover_${cover}.txt" 2>&1
  echo "cover $cover done"
done
for cap in 1.0 1.5 2.0 3.0; do
  python3 scripts/validate_commercial_real_data.py \
    --seeds 7,19,33 --start 1994-01 --train-months 36 --scenarios 20 \
    --skus 30 --suppliers 12 --stride 4 --opening-cover 1.0 \
    --inv-cap-months "$cap" > "$OUT/D_cap_${cap}.txt" 2>&1
  echo "cap $cap done"
done
python3 scripts/validate_commercial_real_data.py \
  --seeds 7,19,33 --start 1994-01 --train-months 36 --scenarios 20 \
  --skus 30 --suppliers 12 --stride 4 --opening-cover 1.0 --idio-cv 0.0 \
  > "$OUT/E_idio0.txt" 2>&1
echo "idio 0 done"

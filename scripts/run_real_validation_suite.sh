#!/usr/bin/env bash
# Full real-data validation suite for the commercial branch.
# Sequential on purpose: parallel runs contend for CPU and the HiGHS solve
# time dominates, so this finishes sooner and reports cleaner timings.
set -u
cd "$(dirname "$0")/.."
OUT=outputs/real_validation
mkdir -p "$OUT"
V=scripts/validate_commercial_real_data.py

echo "[1/5] full history 1994-2026, real demand path"
python3 $V --seeds 7,19,33 --start 1994-01 --train-months 36 --scenarios 30 \
  --skus 40 --suppliers 14 --stride 1 --opening-cover 1.0 \
  > "$OUT/A_full_history.txt" 2>&1

echo "[2/5] 2019-2026 only, real demand AND real route supply shocks"
python3 $V --seeds 7,19,33,41,53 --start 2019-01 --train-months 30 \
  --scenarios 30 --skus 40 --suppliers 14 --stride 1 --opening-cover 1.0 \
  --real-supply-only > "$OUT/B_real_supply.txt" 2>&1

echo "[3/5] opening-cover sensitivity"
for c in 0.0 0.5 1.0 1.5 2.0; do
  python3 $V --seeds 7,19,33 --start 1994-01 --train-months 36 --scenarios 20 \
    --skus 30 --suppliers 12 --stride 4 --opening-cover "$c" \
    > "$OUT/C_cover_${c}.txt" 2>&1
  echo "      cover $c"
done

echo "[4/5] warehouse-cap sensitivity"
for k in 1.0 1.5 2.0 3.0; do
  python3 $V --seeds 7,19,33 --start 1994-01 --train-months 36 --scenarios 20 \
    --skus 30 --suppliers 12 --stride 4 --opening-cover 1.0 \
    --inv-cap-months "$k" > "$OUT/D_cap_${k}.txt" 2>&1
  echo "      cap $k"
done

echo "[5/5] no synthetic SKU noise: the real signal alone"
python3 $V --seeds 7,19,33 --start 1994-01 --train-months 36 --scenarios 20 \
  --skus 30 --suppliers 12 --stride 4 --opening-cover 1.0 --idio-cv 0.0 \
  > "$OUT/E_idio0.txt" 2>&1
echo "done"

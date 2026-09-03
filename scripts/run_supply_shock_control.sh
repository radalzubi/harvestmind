#!/usr/bin/env bash
# The decisive experiment. Identical window, seeds, training length and
# operator draws; the ONLY difference is whether the measured PortWatch
# route shocks are applied. Any gap between the two arms is attributable
# to supply uncertainty and not to the period or the sampling.
set -u
cd "$(dirname "$0")/.."
OUT=outputs/real_validation
V=scripts/validate_commercial_real_data.py
COMMON="--seeds 7,19,33,41,53,61,73 --start 2019-01 --train-months 30 \
--scenarios 30 --skus 40 --suppliers 14 --stride 1 --opening-cover 1.0 \
--real-supply-only"
python3 $V $COMMON              > "$OUT/F_shocks_on.txt"  2>&1
echo "  arm 1 (real shocks) done"
python3 $V $COMMON --flat-supply > "$OUT/F_shocks_off.txt" 2>&1
echo "  arm 2 (control) done"

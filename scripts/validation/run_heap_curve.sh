#!/bin/bash
# Heap test (C06-3, C06-4): the 17 heaps behind the mu_r table of
# docs/scientific_rationale/06_rolling_resistance.md, then the refit.
# Each heap takes ~25 min on 4 threads; JOBS heaps run at once (default 4).
# Writes $OUT/heap_<mu>_s<seed>.json (OUT defaults to data/raw/validation/results/heap) and prints the curve.
set -e
cd "$(dirname "$0")/../.."
OUT=${OUT:-data/raw/validation/results/heap}
JOBS=${JOBS:-4}
SCENARIO=configs/simulation/sag_slice_lifters.json
mkdir -p "$OUT"
# mu_r:seed pairs as run on 2026-11-04/05 (mu_r = 0 is excluded: in the original
# run eta = 0 meant an uncapped rolling spring; the code now switches the moment off).
RUNS="0.05:0 0.10:0 0.10:1 0.10:2 0.15:0 0.15:1 0.15:2 0.20:0 0.20:1 0.20:2
      0.25:0 0.25:1 0.25:2 0.30:0 0.30:1 0.30:2 0.40:1"
printf '%s\n' $RUNS | xargs -P "$JOBS" -I{} bash -c '
    MU=${1%%:*}; SEED=${1##*:}
    yadedaily -n -x -j 4 pm_dem_sm/simulation/yade_dem/heap.py --scenario '"$SCENARIO"' \
        --mu-r $MU --seeds $SEED --out '"$OUT"'/heap_${MU}_s${SEED}.json \
        > '"$OUT"'/heap_${MU}_s${SEED}.log 2>&1
' _ {}
python scripts/validation/heap_refit.py --results-dir "$OUT" --out "$OUT/refit_cell_top.json"

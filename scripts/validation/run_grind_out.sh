#!/bin/bash
# Grind-out / crash-stop particle counts (C12-2, C12-3, V16) at full scale (SAG_A, mu_r = 0.13).
# Many hours on 16 threads (a ball cycle ~20 min, a mixed cycle ~2.5 h).
# Starts from scenarios/grind_out_start.json: 3437 balls (the ball-stage result of a first,
# mu_r = 0.25 attempt) and the provisional 14650 rocks.
# Full run directories (with checkpoints) go to OUT; copy grind_out.json and the per-cycle
# fill_level.json / manifest.json into scripts/validation/results/grind_out/ afterwards.
set -e
cd "$(dirname "$0")/../.."
OUT=${OUT:-data/raw/grind_out}
mkdir -p "$OUT"
export PYTHONUNBUFFERED=1
yadedaily -n -x -j "${THREADS:-16}" pm_dem_sm/simulation/yade_dem/grind_out.py \
    --scenario scripts/validation/scenarios/grind_out_start.json \
    --out-dir "$OUT" --seeds 0 1 2 --revolutions 2 > "$OUT/grind_out.log" 2>&1
grep -a "\[grind-out\]" "$OUT/grind_out.log"

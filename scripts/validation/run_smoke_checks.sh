#!/bin/bash
# Per-run checks (V2, V3, V4, V5, V13, V14, V18) on the smoke test, with and without
# rolling resistance, and the grind-out procedure at smoke scale. A few minutes each.
# Each run directory has manifest.json (stage "checks") and mill_log.csv.
set -e
cd "$(dirname "$0")/../.."
OUT=${OUT:-data/raw/validation_smoke}
mkdir -p "$OUT"
RUN=pm_dem_sm/simulation/yade_dem/run_simulation.py
yadedaily -n -x -j 8 $RUN --scenario configs/simulation/smoke_test.json \
    --run-dir "$OUT/smoke" > "$OUT/smoke.log" 2>&1
yadedaily -n -x -j 4 $RUN --scenario scripts/validation/scenarios/smoke_no_rolling.json \
    --run-dir "$OUT/smoke_no_rolling" --to-stage settle > "$OUT/smoke_no_rolling.log" 2>&1
yadedaily -n -x -j 6 pm_dem_sm/simulation/yade_dem/grind_out.py \
    --scenario configs/simulation/smoke_test.json --out-dir "$OUT/grind_out_smoke" \
    --seeds 0 --revolutions 0.5 --jb 0.08 --jc 0.16 --max-iterations 2 \
    > "$OUT/grind_out_smoke.log" 2>&1
python scripts/validation/summarize_manifest.py "$OUT"/smoke/manifest.json \
    "$OUT"/smoke_no_rolling/manifest.json

#!/bin/bash
# Per-run checks on the smoke test, through the CLI (each successful run is post-processed:
# float32 parquet frames, validation.json with V2-V8, V13, V14, V16, V18, V19):
#   1. calibrate run (smoke_test.json): toe / shoulder in analysis/charge_shape.json;
#   2. settle without rolling resistance (scenarios/smoke_no_rolling.json);
#   3. make_ic -> dataset chain, seed 0 (smoke_make_ic.json, smoke_dataset.json; the dataset
#      loads data/raw/yade_runs/smoke_make_ic_s0): segregation profiles and Lacey;
#   4. the grind-out procedure at smoke scale.
# A few minutes each. Needs the project environment (python -m pm_dem_sm) and yadedaily.
set -e
cd "$(dirname "$0")/../.."
OUT=${OUT:-data/raw/validation_smoke}
mkdir -p "$OUT"
python -m pm_dem_sm dem-sim --scenario configs/simulation/smoke_test.json \
    --run-dir "$OUT/smoke" --threads 8 > "$OUT/smoke.log" 2>&1
python -m pm_dem_sm dem-sim --scenario scripts/validation/scenarios/smoke_no_rolling.json \
    --run-dir "$OUT/smoke_no_rolling" --threads 4 --to-stage settle \
    > "$OUT/smoke_no_rolling.log" 2>&1
python -m pm_dem_sm dem-sim --scenario configs/simulation/smoke_make_ic.json --seed 0 \
    --threads 8 > "$OUT/smoke_make_ic.log" 2>&1
python -m pm_dem_sm dem-sim --scenario configs/simulation/smoke_dataset.json --seed 0 \
    --threads 8 > "$OUT/smoke_dataset.log" 2>&1
yadedaily -n -x -j 6 pm_dem_sm/simulation/yade_dem/grind_out.py \
    --scenario configs/simulation/smoke_test.json --out-dir "$OUT/grind_out_smoke" \
    --seeds 0 --revolutions 0.5 --jb 0.08 --jc 0.16 --max-iterations 2 \
    > "$OUT/grind_out_smoke.log" 2>&1
python scripts/validation/summarize_manifest.py "$OUT"/smoke/manifest.json \
    "$OUT"/smoke_no_rolling/manifest.json data/raw/yade_runs/smoke_make_ic_s0/manifest.json \
    data/raw/yade_runs/smoke_dataset_s0/manifest.json

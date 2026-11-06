#!/bin/bash
# Run the friction-calibration grid (docs/scientific_rationale/05_friction.md), PARALLEL grid
# points at a time with THREADS threads each. Each point is a calibrate run from the shared IC,
# through `python -m pm_dem_sm dem-sim` (post-processed when it succeeds), in
# data/raw/yade_runs/<name>/.
#
#   source .venv/bin/activate
#   scripts/calibration/run_grid.sh                       # all of configs/simulation/calibration/
#   PARALLEL=2 THREADS=10 scripts/calibration/run_grid.sh configs/simulation/calibration/cal_mup0p5_*.json
#
# Needs the shared IC: data/raw/yade_runs/sag_a_make_ic_rmic_s0 (the pilot's make_ic run).
# A point whose run directory already has validation.json is skipped, so the script can be
# rerun after an interruption. Logs: data/raw/calibration/logs/<name>.log.
set -e
cd "$(dirname "$0")/../.."
PARALLEL=${PARALLEL:-2}
THREADS=${THREADS:-10}
LOGS=data/raw/calibration/logs
mkdir -p "$LOGS"
if [ "$#" -gt 0 ]; then
    SCENARIOS=("$@")
else
    SCENARIOS=(configs/simulation/calibration/cal_*.json)
fi

run_one() {
    name=$(basename "$1" .json)
    if [ -f "data/raw/yade_runs/$name/validation.json" ]; then
        echo "[grid] $name: done before, skipped"
        return 0
    fi
    echo "[grid] $name: started $(date +%H:%M)"
    if python -m pm_dem_sm dem-sim --scenario "$1" --threads "$THREADS" > "$LOGS/$name.log" 2>&1; then
        echo "[grid] $name: finished $(date +%H:%M)"
    else
        echo "[grid] $name: FAILED $(date +%H:%M), see $LOGS/$name.log"
    fi
}
export -f run_one
export THREADS LOGS

printf '%s\n' "${SCENARIOS[@]}" | xargs -P "$PARALLEL" -I{} bash -c 'run_one "$@"' _ {}
python scripts/calibration/grid_summary.py

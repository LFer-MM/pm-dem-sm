#!/bin/bash
# Crash-stop check (pilot): stop the turning charge at the end of a dataset run's record stage,
# settle and measure J; compare with the grind-out (C12-3) and the plant target. ~20-30 min on
# 16 threads at full scale. Result: data/raw/validation/results/crash_stop/<run>_record.json.
set -e
cd "$(dirname "$0")/../.."
RUN=${1:-data/raw/yade_runs/sag_a_dataset_rmic_s0}
mkdir -p data/raw/validation/results/crash_stop
yadedaily -n -x -j "${THREADS:-16}" scripts/validation/crash_stop_check.py "$RUN" \
    > "data/raw/validation/results/crash_stop/$(basename "$RUN").log" 2>&1
grep -a "\[crash-stop\]" "data/raw/validation/results/crash_stop/$(basename "$RUN").log"

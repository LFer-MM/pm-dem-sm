#!/bin/bash
# V1 restitution recovery (C01-4) on the SAG_A scenario, plus the onset-phase side study.
# Produces $OUT/v1_sag_a.json and $OUT/onset_phase_sweep_rock_rock.json (OUT defaults to data/raw/validation/results/v1).
# Run from anywhere; takes a few minutes.
set -e
cd "$(dirname "$0")/../.."
OUT=${OUT:-data/raw/validation/results/v1}
mkdir -p "$OUT"
yadedaily -n -x pm_dem_sm/simulation/yade_dem/collision_check.py \
    --scenario configs/simulation/sag_slice_lifters.json --out "$OUT/v1_sag_a.json" || true
yadedaily -n -x scripts/validation/v1_onset_phase_sweep.py \
    --scenario configs/simulation/sag_slice_lifters.json --pair rock rock \
    --speeds 5 14.5 --phases 6 --out "$OUT/onset_phase_sweep_rock_rock.json"

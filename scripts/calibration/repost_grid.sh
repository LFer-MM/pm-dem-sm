#!/bin/bash
# Post-process the finished grid points again (e.g. after a change of the toe / shoulder
# rule): `pm-dem-sm dem-post` on every data/raw/yade_runs/cal_* run directory that has
# validation.json (i.e. finished), then the grid table. Frames are not touched; analysis/,
# validation.json and the manifest's validation entry are rewritten. Minutes per point.
#
#   source .venv/bin/activate
#   scripts/calibration/repost_grid.sh
set -e
cd "$(dirname "$0")/../.."
for d in data/raw/yade_runs/cal_*; do
    if [ -f "$d/validation.json" ]; then
        echo "[repost] $(basename "$d")"
        python -m pm_dem_sm dem-post "$d" > /dev/null
    fi
done
python scripts/calibration/grid_summary.py

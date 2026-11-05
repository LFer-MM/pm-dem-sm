"""Refit saved heap results and build the mu_r -> repose-angle curve (C06-3; plain Python).

Reads every ``heap*.json`` written by ``pm_dem_sm/simulation/yade_dem/heap.py``
that contains final positions, refits each heap with
:func:`pm_dem_sm.simulation.checks.repose_angle` (cell-top surface) and
:func:`~pm_dem_sm.simulation.checks.repose_angle_sectors`, prints the mean
and seed spread per mu_r, and interpolates mu_r for 33 / 37 / 41 deg with
linear and quadratic fits over 0.05-0.30. This produced the table in
docs/scientific_rationale/06_rolling_resistance.md ("Heap test results").

Run from the repository root (project venv)::

    python scripts/validation/heap_refit.py --results-dir data/raw/validation/results/heap
"""

import argparse
import glob
import json
import math
from pathlib import Path
import statistics
import sys

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from pm_dem_sm.simulation import checks

# Heap geometry of heap.py: rock radius, base layer of fixed spheres
# (centres at z = r, top at 2 r) out to BASE_RADIUS_D rock diameters.
ROCK_R = 0.034925
BASE_TOP = 2 * ROCK_R
BASE_RADIUS = 17 * 2 * ROCK_R
TARGETS = (33.0, 37.0, 41.0)

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("--results-dir", default="data/raw/validation/results/heap")
p.add_argument("--out", default=None, help="JSON with the per-heap refits.")
p.add_argument("--fit-max-mu", type=float, default=0.30)
args = p.parse_args()

rows = []
for path in sorted(glob.glob(str(Path(args.results_dir) / "heap*.json"))):
    with open(path) as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "results" not in data:
        continue
    for r in data["results"]:
        if r.get("mu_r", 0) <= 0 or "spheres" not in r:
            continue
        s = [
            x
            for x in r["spheres"]
            if math.hypot(x[0], x[1]) <= BASE_RADIUS and x[2] > BASE_TOP - ROCK_R
        ]
        fit = checks.repose_angle(s, base_z=BASE_TOP)
        sec = checks.repose_angle_sectors(s, 8, base_z=BASE_TOP)
        rows.append(
            {
                "file": Path(path).name,
                "mu_r": r["mu_r"],
                "seed": r["seed"],
                "angle": fit["angle_deg"],
                "r2": fit["r2"],
                "radius": fit["radius_m"],
                "cells": fit["n_bins_fitted"],
                "sec_mean": sec["mean_deg"],
                "sec_sd": sec["sd_deg"],
                "final_speed": r["final_mean_speed_m_s"],
            }
        )

by_mu = {}
for r in rows:
    by_mu.setdefault(round(r["mu_r"], 4), []).append(r)
print(f"{'mu_r':>5} n  mean   sd | per seed: angle [sector mean +- sd] R2 radius cells")
for mu in sorted(by_mu):
    rs = sorted(by_mu[mu], key=lambda r: r["seed"])
    a = [r["angle"] for r in rs]
    sd = statistics.stdev(a) if len(a) > 1 else float("nan")
    print(
        f"{mu:5.2f} {len(a)} {statistics.fmean(a):5.2f} {sd:4.2f} | "
        + "; ".join(
            f"s{r['seed']} {r['angle']:.1f} [{r['sec_mean']:.1f}+-{r['sec_sd']:.1f}] "
            f"{r['r2']:.2f} {r['radius']:.2f} {r['cells']}"
            for r in rs
        )
    )

x = np.array([r["mu_r"] for r in rows if r["mu_r"] <= args.fit_max_mu])
y = np.array([r["angle"] for r in rows if r["mu_r"] <= args.fit_max_mu])
grid = np.linspace(x.min(), x.max(), 2501)
for deg in (1, 2):
    coef = np.polyfit(x, y, deg)
    sd = (y - np.polyval(coef, x)).std(ddof=deg + 1)
    f = np.polyval(coef, grid)
    hits = {
        t: [round(float(grid[i]), 3) for i in np.where(np.diff(np.sign(f - t)))[0]]
        for t in TARGETS
    }
    print(
        f"fit degree {deg} on mu_r <= {args.fit_max_mu} (n = {x.size}): residual sd "
        f"{sd:.2f} deg; mu_r at targets {hits}"
    )
if args.out:
    Path(args.out).write_text(json.dumps(rows, indent=1), encoding="utf-8")

# Friction calibration grid

The friction calibration of
[`docs/scientific_rationale/05_friction.md`](../../docs/scientific_rationale/05_friction.md):
particle-particle friction mu_p x particle-liner friction mu_w, scored on the
bulk toe / shoulder against SAG_A
([15](../../docs/scientific_rationale/15_calibration_targets.md)). Every grid
point is a `calibrate_ic` run: it loads one shared settled initial condition
(the pilot's RMIC IC, `data/raw/yade_runs/sag_a_make_ic_rmic_s0`), spins up
to steady state and records 2 revolutions. Run from the repository root with
the project environment active (`source .venv/bin/activate`).

| Script | What |
|---|---|
| `make_grid_scenarios.py` | Writes `configs/simulation/calibration/cal_mup<mu_p>_muw<mu_w>.json` from the IC's own `make_ic` scenario, changing only the run type, the friction and the record length. Default grid {0.3, 0.5, 0.7} x {0.3, 0.5, 0.7}; `--mu-p` / `--mu-w` for a refinement, `--record-revolutions` for the record length |
| `run_grid.sh` | Runs the grid points `PARALLEL` at a time with `THREADS` threads each (default 2 x 10), through `python -m pm_dem_sm dem-sim` (post-processed when a run succeeds). Points whose run directory already has `validation.json` are skipped, so it can be rerun after an interruption. Logs in `data/raw/calibration/logs/` |
| `grid_summary.py` | Ranks the finished (and running) points by the distance of the bulk toe / shoulder from the middle of the target ranges; also the liner-force toe / shoulder, spin-up revolutions, mean power and failed checks. Writes `data/raw/calibration/grid_summary.csv` |

```bash
source .venv/bin/activate
PARALLEL=2 THREADS=10 scripts/calibration/run_grid.sh        # the whole grid
scripts/calibration/run_grid.sh configs/simulation/calibration/cal_mup0p5_muw0p5.json   # one point
python scripts/calibration/grid_summary.py                    # the table, any time
pm-dem-sm dem-view data/raw/yade_runs/cal_mup0p5_muw0p5       # watch a point
```

Threads: the machine has 12 physical cores (24 hardware threads). Two
points at 10 threads each leave some room for the system; they share the 12
physical cores, so each point runs slower than alone, but the pair finishes
sooner than two points one after the other. Check the timings of the first
pair before committing to a split.

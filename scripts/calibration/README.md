# Friction calibration grid

The friction calibration of
[`docs/scientific_rationale/05_friction.md`](../../docs/scientific_rationale/05_friction.md):
particle-particle friction mu_p x particle-liner friction mu_w, scored on the
bulk toe / shoulder against SAG_A
([15](../../docs/scientific_rationale/15_calibration_targets.md)). Every grid
point is a `calibrate` run with `run.ic_dir` set: it loads one shared settled
initial condition
(the pilot's RMIC IC, `data/raw/yade_runs/sag_a_make_ic_rmic_s0`), spins up
to steady state and records 2 revolutions. Run from the repository root with
the project environment active (`source .venv/bin/activate`).

| Script | What |
|---|---|
| `make_grid_scenarios.py` | Writes `configs/simulation/calibration/cal_mup<mu_p>_muw<mu_w>.json` from the IC's own `make_ic` scenario, changing only the run type, the friction and the record length. Default grid {0.3, 0.5, 0.7} x {0.3, 0.5, 0.7}; `--mu-p` / `--mu-w` for a refinement, `--record-revolutions` for the record length |
| `run_grid.sh` | Runs the grid points `PARALLEL` at a time with `THREADS` threads each (default 2 x 10), through `python -m pm_dem_sm dem-sim` (post-processed when a run succeeds). Points whose run directory already has `validation.json` are skipped, so it can be rerun after an interruption. Logs in `data/raw/calibration/logs/` |
| `repost_grid.sh` | Runs `pm-dem-sm dem-post` again on every finished point and prints the table: after a change of the toe / shoulder rule (the 50 % cut of 2026-11-06), points finished before it are measured again from their saved frames |
| `make_probe_scenarios.py` | The two probes after the grid (2026-11-07): mu_p 0.1 on the shared IC, mu_r 0.08 on its own bed (rolling resistance is part of an IC's material-set id) |
| `make_final_scenario.py --mu-r X` | The calibrated point (option 1, 2026-11-08): mu_p 0.3, mu_w 0.5 and the re-fitted mu_r (0.16), a `calibrate` run on its own bed; run with `--seed` 0, 1, 2 for the replicates |
| `final_point_summary.py <run-dirs>` | V12 (toe / shoulder / power mean +- sd over the seeds) and V15 (full-mill power vs the plant's, c_cone 0.05 and 0.13); writes `data/raw/calibration/final_point.json` |
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

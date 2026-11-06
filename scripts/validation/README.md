# Validation code and results

Where every validation result in `docs/scientific_rationale/` comes from:
the code that implements it, the command that produced it, the commit and
date, the stored result files, and the document that reports it. All runs
were made on 2026-11-04/05 with YADE `yadedaily` 20260115-8983~7c8d01e
(`scripts/validation/yade_api_probe.py` prints the build) on a 24-core
machine, through the implementation phases of
[`docs/implementation_plan.md`](../../docs/implementation_plan.md).

Run everything from the repository root. YADE scripts run with `yadedaily -n -x`;
plain-Python scripts with the project environment (`python`).

**Code in git, results not.** This folder (code, launchers, scenarios, this
index) is in git. The results are written to `data/raw/validation/results/`,
which is git-ignored like the rest of `data/` and stays on the machine that
ran them; the launchers write there by default. The results of 2026-11-04/05
are on the author's machine at that path (2.4 MB; they were briefly committed
in `34334ed`, so that commit also holds a copy).

## Two kinds of checks

1. **Per-run checks**: built into every simulation run
   (`pm_dem_sm/simulation/yade_dem/run_simulation.py`). Their results are
   written to the run's `manifest.json`, under each stage's `checks`, and to
   `mill_log.csv`. `summarize_manifest.py` prints them.
2. **Standalone studies**: scripts run once (or when the material set or dt
   changes) whose results are written into the topic files.

The decision logic of both is in `pm_dem_sm/simulation/checks.py` (plain
Python + numpy, unit-tested in `tests/simulation/test_checks.py`).

## Index

| Item | What | Code | How to rerun | Result files (local, not in git) | Reported in |
|---|---|---|---|---|---|
| V1 / C01-4 | Restitution recovered in binary collisions per material pair at the run's dt, averaged over 8 contact-onset phases | `pm_dem_sm/simulation/yade_dem/collision_check.py` | `run_v1.sh` | `data/raw/validation/results/v1/v1_sag_a.json` | [01](../../docs/scientific_rationale/01_contact_model.md) Open items |
| V1 side study | e versus contact-onset phase (why V1 averages) | `v1_onset_phase_sweep.py` | `run_v1.sh` | `data/raw/validation/results/v1/onset_phase_sweep_rock_rock.json` | 01 Open items |
| V2 / C02-2, C02-3 | Steps per collision: worst-case check per scenario; P99 normal impact speed of the run | `scenario.steps_per_collision`, `monitor.contact_samples`, `run_simulation._stage_checks` | any run; `run_smoke_checks.sh` | `data/raw/validation/results/smoke/*/manifest.json`, `mill_log.csv` | [02](../../docs/scientific_rationale/02_time_step.md) |
| V3 / C03-2 | Overlaps relative to the smaller diameter, per pair type | `monitor.contact_samples`, `checks.overlap_stats`, `diagnostics.check_overlaps` | any run | same | [03](../../docs/scientific_rationale/03_stiffness_young_modulus.md) |
| V4 / C04-3 | Energy balance, drive work vs. dissipation (incl. a sampled estimate of the untracked rolling dissipation) | `monitor.energy_terms`, `monitor.rolling_dissipation_rate`, `checks.energy_balance` | any run; `run_smoke_checks.sh` | `data/raw/validation/results/smoke/phase4_*` | [04](../../docs/scientific_rationale/04_numerical_damping.md) Open items |
| V4 side study | Which energy terms YADE tracks for the Mindlin law | `energy_probe.py` | `yadedaily -n -x scripts/validation/energy_probe.py` | (prints) | 04 Open items |
| V5 / C04-2 | Damping exactly 0 at the start of every stage | `engines.assert_no_damping`, `run_simulation.run` | any run | manifests (`checks.damping`) | 04 |
| V13 / C04-4 | No overlaps before each fill batch (aborts) | `diagnostics.check_new_batch`, `checks.new_sphere_overlaps`, `checks.sphere_wall_overlaps` | any run | manifests (`v13_initial_overlaps`) | 04 |
| V14 / C04-4 | No particle outside the mill after each stage (aborts) | `diagnostics.count_escapes`, `checks.escaped_spheres` | any run | manifests (`checks.escaped`) | 04 |
| V18 / C04-5 | Geometric settle stop rule; stop reason recorded | `checks.settle_stop`, `monitor.run_until_settled`, `state.settle_and_save` | any run | manifests (`settle`) | [13](../../docs/scientific_rationale/13_initial_conditions.md) |
| C06-3 | Heap (angle of repose) -> mu_r for 37 / 33 / 41 deg | `pm_dem_sm/simulation/yade_dem/heap.py`, `checks.repose_angle`, `checks.repose_angle_sectors` | `run_heap_curve.sh` (runs) and `heap_refit.py` (table) | `data/raw/validation/results/heap/heap*.json` (with final positions), `data/raw/validation/results/heap/refit_cell_top.json` | [06](../../docs/scientific_rationale/06_rolling_resistance.md) "Heap test results" |
| C06-4 | Heap and charge come to rest with rolling resistance and damping 0 | `heap.py` (final mean speed), settle stage | as above | `data/raw/validation/results/heap/*`, `data/raw/validation/results/smoke/*` | 06, 13 |
| V16 / C12-2, C12-3 | Particle counts and phi from the grind-out / crash-stop procedure, J from the stopped bed | `checks.fill_level`, `pm_dem_sm/simulation/yade_dem/grind_out.py` | `run_grind_out.sh` (full scale); `run_smoke_checks.sh` (smoke) | `data/raw/validation/results/grind_out/`, `data/raw/validation/results/smoke/phase4_grind_out_smoke/` | [12](../../docs/scientific_rationale/12_charge_fill_and_particles.md) |
| V16 pilot | Crash stop of a turning charge: a poured starting packing (J at rest below Jc) gives the plant's J once it has turned and is stopped like the plant | `crash_stop_check.py`, `grind_out.crash_stop` | `run_crash_stop_check.sh [run-dir]` (after the dataset run; default `sag_a_dataset_rmic_s0`) | `data/raw/validation/results/crash_stop/<run>_record.json` | [13](../../docs/scientific_rationale/13_initial_conditions.md), [12](../../docs/scientific_rationale/12_charge_fill_and_particles.md) |
| C07-3 | YADE version floor (>= 2023.02) | `pm_dem_sm/simulation/yade_dem/version.py` | every run; `tests/simulation/yade_dem/test_version.py` | -- | [07](../../docs/scientific_rationale/07_restitution.md) |
| V6 / C16-1 | Same counts in every frame, no particle outside the mill | `checks.frame_inventory`, `simulation/postprocess.py` | post-processing of any run (`pm-dem-sm dem-post <run-dir>`; `dem-sim` does it automatically) | `<run-dir>/validation.json` | [16](../../docs/scientific_rationale/16_validation_checks.md) |
| V7 / C16-1 | Quasi-steady kinetic energy / power / charge angle before the training window; Lacey plateau (dataset runs); spin-up steady (calibrate runs) | `checks.quasi_steady_time`, `checks.plateau`, `postprocess.lacey_series` | as above | `validation.json`, `analysis/lacey.csv` | [14](../../docs/scientific_rationale/14_dataset_runs_and_recording.md) |
| V8 / C15-1 | Bulk toe / shoulder from the time-averaged position density; liner-force cross-check | `checks.toe_shoulder`, `checks.liner_force_arc`, `postprocess.charge_shape`, `monitor.liner_force_histogram` | post-processing of a calibrate run | `analysis/charge_shape.json` | [15](../../docs/scientific_rationale/15_calibration_targets.md) |
| V19 / C14-3 | Radial large-particle fraction per frame: slice, centre and near-wall layers | `postprocess.segregation_profiles` | post-processing of a dataset run | `analysis/radial_fraction.parquet`, `validation.json` | 14 |
| C16-1 | All per-run checks in one table (value, criterion, pass / fail / reported) | `postprocess.validation_summary` | any run | manifest `validation`, `validation.json` | 16 |
| C14-1 | Run types: make_ic -> dataset chain with the material-set id check | `run_simulation.py` (`_stage_save_ic`, `_stage_load_ic`), `scenario.material_set_id` | `run_smoke_checks.sh` (smoke chain) | `data/raw/yade_runs/smoke_make_ic_s0`, `smoke_dataset_s0` | [13](../../docs/scientific_rationale/13_initial_conditions.md), 14 |
| C10-4 | Mill liner geometry (radii, widths, angles, areas) | `pm_dem_sm/simulation/mill_geometry.py` | `tests/simulation/test_mill_geometry.py`; any run writes `mill_geometry` + mesh hash to the manifest | `data/raw/validation/results/build/phase3_sag_a_build_manifest.json` | [10](../../docs/scientific_rationale/10_mill_geometry.md) |
| -- | What a saved scene actually contains (functors, per-pair friction / restitution, overlaps, escapes, speeds) | `inspect_checkpoint.py` | `yadedaily -n -x scripts/validation/inspect_checkpoint.py <checkpoint> --shell-radius R --depth L` | (prints) | 05, 06, 07 (Phase 2 check) |
| -- | YADE API facts relied on (defaults, MatchMaker by id, energy attributes) | `yade_api_probe.py` | `yadedaily -n -x scripts/validation/yade_api_probe.py` | (prints) | 01, 04, 05, 06 |

Not implemented yet: V9-V12, V15, V17 (one-off studies; their scenario files are in
`configs/simulation/sensitivity/`, C03-3).

## Provenance of the stored results

| Result | Code (commit) | Notes |
|---|---|---|
| `data/raw/validation/results/smoke/phase1_smoke_main_baseline` | `508c09a` (`main` before Phase 1) | Baseline for the Phase 1 comparison; damping 0.2, old dt |
| `data/raw/validation/results/smoke/phase1_smoke` | `5c194ab` + `4ecf399` | Phase 1 acceptance: undamped, dt 2.5e-5 s; old unbalanced-force settle |
| `data/raw/validation/results/smoke/phase2_smoke` | `4bb17e4` | Liner material, per-pair friction, rolling resistance (mu_r 0.25 placeholder) |
| `data/raw/validation/results/smoke/phase3_smoke` | `d73d750` | Generated SAG_A-type liner (smoke size) |
| `data/raw/validation/results/build/phase3_sag_a_build_manifest.json` | `d73d750` | Full SAG_A liner: 796 facets, geometry summary and mesh hash |
| `data/raw/validation/results/smoke/phase4_smoke_checks` | `494c1f3` (before the rolling estimate) | V2-V5, V13, V14, V18 |
| `data/raw/validation/results/smoke/phase4_smoke_rolling_estimate` | `494c1f3` | With the sampled rolling-dissipation estimate (V4); mu_r 0.25 |
| `data/raw/validation/results/smoke/phase4_smoke_eta0_uncapped` | `494c1f3` | mu_r = 0 **before** the eta = 0 fix: the rolling spring was uncapped (unlimited rolling resistance). Kept because it is how the YADE behaviour was found (see 06) |
| `data/raw/validation/results/smoke/phase4_smoke_no_rolling` | `9959f69` | Moment law switched off (`scenarios/smoke_no_rolling.json`) |
| `data/raw/validation/results/smoke/phase4_grind_out_smoke` | `494c1f3` | Grind-out procedure at smoke scale (2 iterations per stage) |
| `data/raw/validation/results/v1/v1_sag_a.json` | `494c1f3` | 8 onset phases; rock-rock -2.1 % / -2.6 % at 5 / 14.5 m/s |
| `data/raw/validation/results/v1/onset_phase_sweep_rock_rock.json` | `9959f69` | Rerun of the side study for this folder |
| `data/raw/validation/results/heap/heap2_*`, `heap3_*` | `9959f69` (`heap.py` as committed there) | Fit redone with the cell-top method by `heap_refit.py`; `heap2_0.0` is the uncapped eta = 0 run (excluded from the fit) |
| `data/raw/validation/results/heap/batch1_ring_fit/` | `494c1f3` | First 5 heaps, fitted with the superseded ring-max statistic, no positions saved; not used for the mu_r table |
| `data/raw/validation/results/grind_out/attempt_mur025/` | `494c1f3` | First grind-out attempt with mu_r = 0.25, stopped when the heap fixed mu_r = 0.13 (ball stage: 3437 balls -> J 0.1897) |
| `data/raw/validation/results/grind_out/final_mur013/` | `9959f69` (run), counts written in `4ac94bb` | mu_r = 0.13, 3 seeds, 2026-11-05 01:35-12:50: 3437 balls + 16082 rocks, J 0.1883 / 0.2766, phi 0.515 / 0.548 |

## Files

- `README.md`: this index.
- `run_v1.sh`, `run_heap_curve.sh`, `run_grind_out.sh`, `run_smoke_checks.sh`:
  launchers that reproduce the runs (environment variables `OUT`, `JOBS`,
  `THREADS` override the defaults).
- `v1_onset_phase_sweep.py`, `energy_probe.py`, `inspect_checkpoint.py`,
  `yade_api_probe.py`: YADE side studies and probes.
- `heap_refit.py`, `summarize_manifest.py`: plain-Python analysis.
- `scenarios/`: the scenario files these runs used and that are not in
  `configs/simulation/`.
- Results: `data/raw/validation/results/` (not in git): manifests, mill-state
  logs, result JSONs; no checkpoints or frames.

# Implementation plan for the pending code changes (C items)

Planned 2026-11-04, after the full re-review of
[`scientific_rationale/`](scientific_rationale/README.md).

Every decision and its justification lives in the topic files of
`docs/scientific_rationale/`; **they are the source of truth**. This plan only
orders the work. Each C item (`Cnn-k` = code change k of topic nn) is
specified in the "Pending code changes" table of its topic file; read that
row and the topic's Decision before implementing it.

## Status of the 43 items

| Status | Items |
|---|---|
| Done | C15-2 (plant-data analysis, kept outside the repository) |
| Merged into other items | C01-1 -> C05-2; C01-2 -> C06-1 |
| Phase 1 -- defaults and clean-up (15) | C01-3, C02-1, C02-2, C03-1, C04-1, C05-1, C07-2, C07-3, C08-1, C10-1, C10-2, C10-3, C11-1, C12-1, C14-2 |
| Phase 2 -- contact physics (5) | C05-3, C07-1, C05-2, C06-1, C06-2 |
| Phase 3 -- mill geometry (1) | C10-4 |
| Phase 4 -- simulation tools and stage checks (11) | C04-2, C04-4, C04-5, C03-2, C02-3, C04-3, C01-4, C06-3, C06-4, C12-2, C12-3 |
| Phase 5 -- run types and outputs (6) | C14-1, C14-4, C14-3, C15-1, C16-1, C03-3 |
| After the first runs (2) | C14-5 (needs the pilot run), C15-3 (needs the calibrated point) |

Dependencies between phases:

```
Phase 1 ──> Phase 2 ──┐
        └─> Phase 3 ──┴──> Phase 4 ──> Phase 5 ──> pilot run ──> C14-5
                                                    calibration ──> C15-3
```

Phases 2 and 3 are independent of each other and can run in parallel.

## Rules for every phase

- **One branch and one pull request per phase**, from an up-to-date `main`;
  never push to `main`. The phase is done when its PR is merged.
- **Docs follow the code in the same PR.** For each item implemented:
  change its "Current code" cell to `Done (<commit>)`, update the topic's
  "Current state" section, and update the README index of pending code
  changes. If implementation shows a decision cannot be applied as
  written, stop and ask instead of improvising; the decision is changed
  in the topic file first.
- **Tests.** Pure-Python logic gets unit tests that run in CI
  (`python -m pytest tests -q`). YADE-dependent code gets tests guarded by
  `pytest.importorskip("yade")` (as in `tests/simulation/yade_dem/`) and is
  exercised locally with `yadedaily` on `configs/simulation/smoke_test.json`.
  Lint with `make lint` (ruff).
- **Diagrams.** If a change alters what `docs/diagrams/` shows, update the
  spec in the same PR (see `AGENTS.md`).
- **Plant data never enters the repository.** Operating-point and target
  values are used only as the published numbers in the topic files.
- **Configuration values carry their provenance**: physical values stored
  as physical values (e.g. moduli in Pa, then `young_scale`), with a comment
  pointing to the topic file.

## Phase 1 -- defaults and clean-up

Goal: every default in `config.py`, `scenario.py` and
`configs/simulation/*.json` matches the decisions. No new features.

| Item | Change | Main files |
|---|---|---|
| C02-1 | Default `solver.dt_s = 2.5e-5` | `scenario.py`, JSONs |
| C02-2 | Replace the `dt / dt_R > 0.5` warning by the steps-per-collision check (Johnson Eq. 11.24 at sqrt(2 g D), >= 20 steps per pair) | `scenario.py` |
| C03-1 | Physical moduli 207e9 / 55e9 Pa in `MATERIALS`; `young_scale = 1/26` | `config.py`, `scenario.py`, JSONs |
| C04-1 | Damping 0 in every stage (fill / settle defaults to 0 or fields removed) | `scenario.py`, `run_simulation.py`, JSONs |
| C05-1 | One `mu_p` config value for steel and rock | `config.py` |
| C08-1 | Rock density 2850 | `config.py` |
| C10-1 | `MILL_DIAMETER_M = 10.7128` | `config.py` |
| C10-2 | Default `end_walls = "frictionless"` | `scenario.py` |
| C10-3 | Default `depth_m = 0.6` | `scenario.py` |
| C11-1 | Default `speed_rpm = 9.5` | `scenario.py`, JSONs |
| C12-1 | Remove `ROCK_COUNT` / `BALL_COUNT`; counts are scenario inputs (provisional SAG_A estimate ~3,750 balls / ~14,650 rocks for the 0.6 m slice, [12](scientific_rationale/12_charge_fill_and_particles.md)) | `config.py`, `scenario.py`, JSONs |
| C14-2 | `MetricsOptions.cell_size = 0.3` | `config.py`, `configs/pipeline_example.json` |
| C07-2 | Delete `build_yade_material_interactions()` and its BlazeDEM placeholder | `config.py` |
| C01-3 | Remove the `cundall_strack` option | `engines.py`, `scenario.py` |
| C07-3 | Record the YADE version; refuse releases older than 2023.02 | `run_simulation.py` (version parsing unit-tested) |

Tests: defaults asserted in `tests/simulation/test_scenario.py`; the
steps-per-collision check reproduces the [02](scientific_rationale/02_time_step.md)
table (rock-rock 20.9 steps at 14.5 m/s, f = 26, 2850 kg/m^3) and flags
dt = 1e-4 s; version parsing accepts `2023.02`, `20260115` daily builds,
rejects `2022.01`. Acceptance: smoke test fills and settles with damping 0
and no escapes.

## Phase 2 -- contact physics

Needs phase 1.

| Item | Change |
|---|---|
| C05-3 + C07-1 | `"liner"` material (steel density / modulus / Poisson, friction `mu_w`); `mill.liner_material = "liner"`; liner-steel 0.8 and liner-rock 0.5 restitution; end walls derived from it (frictionless) |
| C05-2 | `frictAngle` `MatchMaker` from material labels: particle pairs `mu_p` (or the Owen set as a scenario option), particle-liner pairs `mu_w`, end walls 0 |
| C06-1 | `Ig2_*_ScGeom6D`, `Law2_ScGeom_MindlinPhys_Mindlin(includeMoment=True)`, `Ip2_FrictMat_FrictMat_MindlinPhys(eta=mu_r, krot, ktwist=0)` |
| C06-2 | `krot` helper: T_r >= 20 dt for the smallest rock sphere and theta_y ~ 0.01 rad at a typical contact force; asserted at build |

`mu_r` has no sourced value until the heap test (C06-3, phase 4) fixes it:
it is a required scenario input, and runs record it as provisional in the
manifest. Calibration baselines: `mu_p = 0.5`, `mu_w = 0.5`.

Tests: MatchMaker tables built from labels (all pairs, symmetric); krot
helper against hand-computed values; YADE smoke run with rolling
resistance on. Acceptance: the smoke charge settles (C06-4 proper comes in
phase 4).

## Phase 3 -- mill geometry

Independent of phase 2.

| Item | Change |
|---|---|
| C10-4 | Parametric generator per the plan in [10](scientific_rationale/10_mill_geometry.md) ("Mill generator"): inside-shell diameter, lifter count, base width at the shell, height from the shell, face angle, plate thickness, slice depth -> YADE facets (optional STL for viewing); parameters and a mesh hash in the manifest. SAG_A: 36 ft, 36 lifters, 523 mm base, 395 mm, 35 deg, 130 mm plates. Extend `initialize_parametric_mill` (`stl.py`) or replace it |

Tests (CI, pure numpy): lifter count; radii of the plate surface
(R_shell - 0.130) and lifter tops (R_shell - 0.395); top width 152 mm; face
angle; closed profile; net cross-section = circle inside liners minus the
36 exposed lifter sections (0.0894 m^2 each). Retire the old STL path
(`SAGMILL_STL_PATH`) as the default.

## Phase 4 -- simulation tools and stage checks

Needs phases 1-3.

| Item | Change |
|---|---|
| C04-2 | V5: assert damping == 0 at the start of every stage |
| C04-4 | V13 zero-overlap check before each fill batch; V14 escape check after each stage |
| C04-5 | Geometric settle stop rule ([13](scientific_rationale/13_initial_conditions.md)), replacing `run_until_forces_balanced` in `run_simulation.py` and `state.py`; stop condition recorded |
| C03-2 | Overlap statistics relative to the smaller diameter, per pair type (mean, P99, max) |
| C02-3 | P99 normal impact velocity in the monitor |
| C04-3 | Energy tracking and the V4 balance |
| C01-4 | V1 binary-collision script per material pair at the run's dt |
| C06-3 | Heap (angle-of-repose) script; then fix `mu_r` for 37 deg (and 33 / 41 deg for V11e) and record it in [06](scientific_rationale/06_rolling_resistance.md) |
| C06-4 | Settling test with rolling resistance and damping 0 (heap and charge reach rest) |
| C12-2 | J measured from the settled surface profile (Morrell convention) |
| C12-3 | Grind-out / crash-stop script: ball stage to Jb, mixed stage to Jc (+-0.5 points), 3 seeds; writes counts and phi |

Tests: stop-rule and J-from-profile logic on synthetic data (CI); V1
restitution within ~2 % per pair (local YADE). Outputs of C06-3 and C12-3
(mu_r, counts, phi) are written into the topic files as results.

## Phase 5 -- run types and outputs

Needs phase 4.

| Item | Change |
|---|---|
| C14-1 | Run types `make_ic`, `calibrate` (spin-up, then record), `dataset` (load IC, start from rest, record from t = 0 for 20 s RMIC / 35 s SIC) |
| C14-4 | Frames as float32 parquet at the end of each run |
| C14-3 | Radial large-particle fraction (result) and axial near-wall vs centre layers (V19) |
| C15-1 | Bulk toe / shoulder from the time-averaged position-density contour (0 deg at 3 o'clock, CCW); liner-force cross-check |
| C16-1 | Per-run validation (V2-V7, V13, V14, V16, V18, V19) written to the manifest |
| C03-3 | Sensitivity scenarios: V10 (`young_scale` 1/52 and 1/13); with them, the V9, V11, V11b-e scenario files of [16](scientific_rationale/16_validation_checks.md) |

Tests: toe / shoulder extraction on a synthetic charge with known angles;
radial-fraction and parquet round-trip tests (CI).

## After the first runs

- **Pilot run** (with phase 5 merged): measure the quasi-steady time ->
  **C14-5** (`start_frame` / `dt0`); confirm the stop-rule thresholds, run
  cost and particle counts; update [14](scientific_rationale/14_dataset_runs_and_recording.md).
- **Calibration** (mu_p x mu_w grid, [05](scientific_rationale/05_friction.md))
  -> **C15-3** (V15 power comparison) and the one-off studies of
  [16](scientific_rationale/16_validation_checks.md).
- **Datasets**: 5 replicates per IC type.

## Starting a phase

In a new session in the repository:

> Implement phase N of `docs/implementation_plan.md`.

The session reads this plan, the topic files of its items and the code,
works on its own branch, and opens a PR.

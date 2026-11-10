# Data provenance: what is in `data/raw/`, when it was made, and why

`data/` is not in git; everything below lives on the machine that ran it
(`/home/pher/MCD/pm-dem-sm/data/raw/`). This file says, for every folder of
simulation and validation output, which parameters made it, when (relative
to the key moments of the calibration), what it was for, and whether it is
still current. Times are local (2026-11). Code: the commit noted, or the
`main` of that day. Reasons and results are in `docs/scientific_rationale/`.

## Parameter sets

| Set | mu_p | mu_w | mu_r | Rocks + balls | Status |
|---|---|---|---|---|---|
| **P0** pre-calibration | 0.5 | 0.5 | 0.13 (heap, 37 deg at mu_p 0.5) | 16,082 + 3,437 (grind-out at P0) | superseded |
| **G** grid / probes | 0.1-0.7 | 0.3-0.7 | 0.13 (probe B 0.08) | 16,082 + 3,437 | calibration record |
| **C16** calibrated, old count | 0.3 | 0.5 | 0.16 (heap, 37 deg at mu_p 0.3) | 16,082 + 3,437 | calibration record |
| **C** calibrated (**production**) | 0.3 | 0.5 | 0.16 | **17,270** + 3,437 (grind-out at C) | current defaults |

Smoke runs use their own 2 m mill (300 rocks + 60 balls) with the
contact values of their day.

## Key moments

| # | When | What happened | Consequence |
|---|---|---|---|
| K1 | 11-05 | Heap curve at mu_p 0.5 -> mu_r 0.13; grind-out -> 16,082 + 3,437 | set P0 (phase 4) |
| K2 | 11-06 morning | Pilot (`make_ic` + 20 s dataset) at P0; crash-stop check (J 0.277) | C14-5: training window 6-7 s |
| K3 | 11-06 15:52 | First grid point: the 10 % density cut read the shoulder at 65 deg (lifter streams) | bulk toe / shoulder rule changed to **50 %** (commit `2bea06b`); grid re-measured |
| K4 | 11-07 04:23 | **3 x 3 grid done: no friction reaches toe 214 / shoulder 27 deg**; mu_w has no effect | probes planned |
| K5 | 11-07 13:16 | Probes: only mu_p 0.1 moves the angles much, with a 23 deg ore; mu_r 0.08 moves them ~2 deg | toe / shoulder targets judged unreachable with admissible parameters |
| K6 | 11-08 | **Decision: option 1, a constrained calibration**; mu_r re-fitted to 0.16 at mu_p 0.3; calibrated point run (C16) | V12, V15 (C15-3); defaults changed to mu_p 0.3 / mu_r 0.16 (`ec44a58`) |
| K7 | 11-09 | Grind-out at the calibrated friction: 16,082 rocks too few (J 0.268) -> **17,270** (confirmed J 0.2756) | set C; calibrated point rerun at C (`a80637c`, `7ff6c9c`) |
| K8 | 11-10 00:24 | Production starts (Phase B packings at C) | mixed replicates use seeds **1-5** because the pilot keeps `_s0` (option A) |

## Folders

### Before the calibration (P0)

| Folder | Made | By | Purpose | Status |
|---|---|---|---|---|
| `grind_out_mur025/` | 11-04 23:00 - 11-05 01:27 | `grind_out.py` at mu_r 0.25 | first count attempt | superseded (mu_r placeholder) |
| `grind_out/` | 11-05 01:28 - 12:52 | `scripts/validation/run_grind_out.sh` | counts 3,437 + 16,082, 3 seeds (C12-3) | record of P0 counts |
| `heap/` | 11-05 01:28 (copied) | heap test | working copy of the mu_r curve at mu_p 0.5 | duplicate of `validation/results/heap/` |
| `validation/results/{v1,heap,smoke,build,grind_out}` | 11-05 09:20 - 12:53 (stored) | `scripts/validation/` | phases 1-4 validations (V1-V5, V13, V14, V18, C06-3, C10-4, C12-3) | record |
| `yade_runs/smoke_make_ic_s2`, `smoke_dataset_s2` | 11-05 15:36 | smoke chain (phase 5) | run types make_ic -> dataset | test |
| `yade_runs/sag_a_make_ic_rmic_s0` | 11-05 21:16 - 11-06 07:56 | pilot `make_ic` (P0) | starting packing at rest (J 0.2588); **the shared IC of the grid and probe A** | calibration record; keeps `_s0` |
| `yade_runs/sag_a_dataset_rmic_s0` | 11-06 07:58 - 09:34 | pilot dataset (P0) | quasi-steady time -> C14-5 | calibration record |
| `validation/results/crash_stop/` | 11-06 10:04 | `scripts/validation/crash_stop_check.py` | J after turning: 0.2770 | record (K2) |

### Code tests of 11-06 (smoke mill)

| Folder | Made | Purpose | Status |
|---|---|---|---|
| `yade_runs/smoke_make_ic_s3` | 11-06 11:35 | IC for the shared-IC tests | test |
| `yade_runs/smoke_calibrate_ic_s3` | 11-06 11:49 | test of the run type `calibrate_ic` | **obsolete**: that run type was folded into `calibrate` + `run.ic_dir` the same day; its manifest no longer loads |
| `yade_runs/smoke_calibrate_from_ic_s3` | 11-06 12:14 | test of `calibrate` + `run.ic_dir` | test |

### Calibration record (G, C16)

| Folder | Made | Purpose | Status |
|---|---|---|---|
| `yade_runs/cal_mup*_muw*` (9) | 11-06 12:26 - 11-07 04:23, 2 at a time | the 3 x 3 friction grid from the pilot IC | record. Post-processed first with the 10 % cut, **re-measured with the 50 % rule** (K3; first four on 11-06 ~20:50, all nine on 11-07 04:23) |
| `calibration/grid_summary.csv` | updated with each summary | grid table | record |
| `yade_runs/probe_mup0p1_muw0p5` | 11-07 07:37 - 12:43 | probe A, shared pilot IC | record (K5) |
| `yade_runs/probe_mup0p3_muw0p5_mur0p08` | 11-07 07:37 - 13:16 | probe B, own bed (mu_r is part of the IC id) | record (K5) |
| `validation/results/heap_probes/` | 11-07 07:37 - 10:41 | repose at the best grid point (34.0 deg) and the probes (23.3 / 29.8 deg) | record |
| `validation/results/heap_mup0p3/` | 11-08 09:33 - 10:17 | mu_r curve at mu_p 0.3 -> 0.16 | record (K6) |
| `yade_runs/cal_final_mup0p3_muw0p5_mur0p16_s0..s2` | 11-08 10:18 - 17:15 | calibrated point, C16 (16,082 rocks) | record; superseded as reported values by the rerun below |
| `calibration/final_point.json` | 11-08 ~17:30 | V12 / V15 of the C16 runs | record |
| `grind_out_calibrated/` | 11-08 21:26 - 11-09 03:46 | count recheck at C: 16,082 -> J 0.268; 17,700 -> 0.279 | record (K7) |
| `validation/results/heap_v11e_mup0p3/`, `heap_mup0p3_all/` | 11-08 21:42 - 11-09 09:44 | V11e band at mu_p 0.3: 33 deg at mu_r 0.105, 41 deg unreachable (~40 deg plateau); combined 24-heap fit (37 deg at 0.163) | current |
| `yade_runs/sens_v10_stiffness_f13`, `_f52` | 11-09 03:46 - 09:44 | V10 stiffness x2 / x0.5 at C16 (16,082 rocks, compared with the C16 point) | record; V10 passed (f52 fails V3, expected) |
| `grind_out_calibrated_confirm/` | 11-09 10:11 - 13:26 | 17,270 rocks -> J 0.2756 | record (K7) |
| `yade_runs/cal_final_mup0p3_muw0p5_mur0p16_r17270_s0..s2` | 11-09 14:49 - 22:33 | **calibrated point at C (reported values)**: toe 240.1, shoulder 37.2 deg, power -7.9 to -0.8 % | current |
| `calibration/final_point_r17270.json` | 11-09 ~22:40 | V12 / V15 of the C runs | current |

### Production (C)

| Folder | Made | Purpose | Status |
|---|---|---|---|
| `yade_runs/sag_a_make_ic_sic_s0..s4` | 11-10 00:24 - 02:52 (Phase B, 2 x 10 threads) | segregated starting packings: J 0.285-0.286, phi 0.541-0.543 (layers do not fill each other's gaps, so above Jc at rest) | production |
| `yade_runs/sag_a_make_ic_rmic_s1..s5` | 11-10 02:03 - 06:35 (Phase B) | mixed starting packings (seeds 1-5: `_s0` is the pilot): J 0.260, phi 0.597 (dense random 2:1 packing, below Jc at rest) | production |

All ten carry material-set id `7a4fe8952ab5` (set C), settled by the
geometric rule after 1.2-1.3 s and passed every check.

`calibration/logs/` holds the stdout of every grid, probe, final and
production run, named after the run.

## Rules this file keeps

- A folder made with an older parameter set is never overwritten; launchers
  skip existing run directories.
- Scenario files of the calibration record keep the values they ran with;
  `make_grid_scenarios.py` reproduces the grid with `--rolling-resistance
  0.13 --rock-count 16082`.
- New phases are added here as they run (Phase C datasets, Phase D
  sensitivity set).

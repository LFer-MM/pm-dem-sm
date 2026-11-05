# 14 -- Dataset runs, durations and recording

## Decision

| Item | Value |
|---|---|
| Start | Load a saved IC; damping 0; mill starts from rest at t = 0 and turns at 9.5 rpm ([11](11_mill_speed.md)) |
| Recording | From t = 0, one frame every **0.05 s** (columns `id,x,y,z,r,m,vx,vy,vz`) plus an exact frame-time index and a mill log (charge angle, power, kinetic energy, overlaps) |
| RMIC duration | **20 s** (3.2 revolutions at 9.5 rpm; Kishida: 2.5) -- decided 2026-11-02 |
| SIC duration | **35 s** (5.5 revolutions; Kishida: 5) -- decided 2026-11-02 |
| Training window | 20 frames (1 s) starting **after the measured quasi-steady state** of kinetic energy / power -- not a fixed 3-4 s |
| Replicates | **5 per IC type, each with its own seed** (decided 2026-11-02): different random initial packings of the same charge, everything else identical; they show that the metrics do not depend on the microscopic arrangement. More if the spread is large compared with the segregation effect. Seed and thread count go into each manifest |
| Frame storage | Binary float32 (parquet), not per-frame CSV kept long term |

**Metrics** (decided 2026-11-02):

| Metric | Definition |
|---|---|
| Lacey's mixing index | Large particles (balls) as tracers; **cubic cells of 0.3 m** (2 cells across the 0.6 m slice; 0.028 D), cells with >= 15 particles |
| Granular temperature | Same 0.3 m cells |
| **Segregation result** | **Radial** fraction of large particles vs distance from the mill axis |
| Axial profile | Only as the **end-wall artefact check** ([10](10_mill_geometry.md)): near-wall layers (one ball diameter from each frictionless end wall) vs the centre layer; reported, not used as a result |

No spin-up stage before recording: spinning up first would destroy the IC.

## Evidence

| Source | What it says | Where | Verified |
|---|---|---|---|
| Kishida 2025 | "The DEM simulations ... were performed for 10 s starting from (a) the RM-IC and for 20 s starting from (b) the S-IC" | §3, PDF p6 | Yes |
| Kishida 2025 | "time step used in RNN (Delta t_RNN) was set to 0.05 s ... The raw DEM simulation data were extracted every 0.05 s between 3.0 and 4.0 s (20 frames), in which the quasi-steady state of particle kinetic energy was ensured. Subsequently, the time-series data for 15 frames were input into the RNN." | §3, PDF p6 | Yes |
| Kishida 2025 SM | "the particle kinetic energy reached quasi-steady state after 2.0 second" (Fig. S1, RM-IC) | Supplementary, PDF p1 | Yes |
| Kishida 2025 | Drum speed 15 rpm | Fig. 2(a), PDF p4 | Yes |
| Kishida 2025 | Each case uses **one** DEM run: the surrogate is built from 1 s of it and predicts the rest; no replicate runs | §3-4, PDF p6-10 | Yes |
| Kishida 2025 | Lacey: "the drum mixer was divided into cubic cells, and large particles were used as tracers ... the length of the cubic cell was set to 0.04D"; sensitivity analysis (Fig. S3): "the change in Lacey's mixing index was almost negligible at cell lengths smaller than 0.04D"; granular temperature on the same cells | §4.1, PDF p7-8 | Yes |
| Kishida 2025 | Reports radial and axial large-particle fractions; axial segregation towards its (real) end walls | Fig. 8b-c, PDF p7-8 | Yes |
| Owen & Cleary 2015 | Four centre-point repeats for error estimation | §3, Table 2, PDF p3 / j.21 | Yes |
| Boemer & Ponthot 2017 | "the system reaches the quasi-steady state after 2.5 s according to the position of the global center of gravity; 2.5 additional seconds are necessary to obtain sufficiently representative averages"; recording period 0.01 s | §3.1, PDF p8 / j.60 | Yes |
| Govender 2015 | Los Bronces SAG: "The computed power seems to stabilizes after six revolutions" | §3, PDF p14 / j.165 | Yes |
| Owen & Cleary 2015 | Charge features measured on the **steady** charge distribution | §4.1, PDF p4 / j.22 | Yes |

## PPT

| Slide | Content |
|---|---|
| 19 | "Simulaciones para Generacion de Datasets": dt = 1e-4, gravity_damping = 0.2, duracion_simulacion_sic = 20 s, duracion_simulacion_rmic = 10 s, save_particle_frames_dt = 0.05 s; F2_SIC_0..F2_SIC_400, F2_RMIC_0..F2_RMIC_200 |
| 21 | Lacey index per frame, cell 0.4732 m, min 15 particles per cell |
| 22 | RNN input (N, 15, [x, y, z, d]) |
| 30 | SIC 20 s (400 frames x 30 runs), RMIC 10 s (200 frames x 30 runs) |

## Current state

| Where | What |
|---|---|
| `config.py:188, 193, 194` | `start_frame = 66`, `dt0 = 4.05`, `dt_step = 0.05` (prediction seeded at ~3.3-4.05 s, from the old dataset) |
| `config.py:236-237`, `configs/pipeline_example.json` | `MetricsOptions.cell_size = 0.3` (C14-2, commit `5c194ab`), `min_particles_per_cell = 15` |
| `scenario.py:32`, `run_simulation.py:282-294` | Stages `build, fill, settle, spinup, record`: recording only **after** spin-up -- right for calibration runs, wrong for SIC / RMIC datasets (record from rest) |
| `capture.py:71, 129` | One CSV per frame; `data_processing` converts to parquet afterwards |
| Existing dataset | Charge centre-of-mass angle: 0 deg (t = 0), 22 deg (2 s), 38 deg (4 s), 54 deg (10 s), 60 deg (20 s) -- still rising at 3-4 s |

## Analysis

Compare in revolutions, not seconds:

| | Kishida (15 rpm) | SAG (9.5 rpm) with the PPT durations | SAG with matched revolutions |
|---|---|---|---|
| RM-IC run | 10 s = 2.5 rev | 10 s = 1.6 rev | 15.8 s |
| S-IC run | 20 s = 5 rev | 20 s = 3.2 rev | 31.6 s |
| Training window | 3-4 s = 0.75-1.0 rev | 3-4 s = 0.48-0.63 rev | 4.7-6.3 s (if quasi-steady) |
| Quasi-steady KE | 2.0 s = 0.5 rev | ? (measure) | -- |

- Copying Kishida's seconds gives the SAG run only 63 % of the revolutions.
- Kishida chose 3-4 s *because* kinetic energy was quasi-steady there. The
  criterion transfers, the numbers do not: the old SAG dataset's charge angle
  was still rising at 3-4 s. The training window must be placed after the
  measured quasi-steady time of the new runs (kinetic energy and power from
  the mill log).
- 0.05 s frames at 9.5 rpm are 0.0079 rev per frame (Kishida: 0.0125 rev), i.e.
  finer sampling per revolution; keeping 0.05 s is conservative and keeps the
  RNN Delta t identical.
- Govender's ~6 revolutions for power concerns long-term operation; mixing
  datasets do not need a stationary power, but the training window does need
  quasi-steady flow.
- **Replicates.** Kishida uses one run per case. Replicates here serve to
  show that the metrics do not depend much on the run; 5 per IC type give a
  usable mean and spread (Owen & Cleary estimated error from 4 repeats) at
  ~12 h of compute and ~4 GB of float32 frames for SAG_A's ~18,400
  particles, against ~70 h and ~22 GB for 30 + 30 (rough estimates, to be
  replaced by the pilot's timings).
- **Why different seeds, not the same run repeated.** On 1 thread YADE is
  bit-for-bit deterministic: repeating the same input gives identical runs
  and zero spread. On several threads (needed for speed) the order in which
  contact forces are summed varies, round-off differs and the chaotic
  granular flow amplifies it (test 2026-11-02: 3,000 spheres, 20,000 steps,
  4 threads, two runs: median 0.6 mm apart, 1.6 % of particles more than a
  radius apart) -- spread from uncontrolled noise. Different seeds instead
  sample, reproducibly, the arbitrary microscopic arrangement of a fixed
  macroscopic charge, give independent samples for means and confidence
  intervals, and allow run-wise train / test splits without leakage. V17
  checks determinism once on 1 thread.
- **Cell size.** 0.04 D is 0.43 m for SAG_A, which does not tile the 0.6 m
  slice. Kishida found Lacey's index insensitive to the cell size below
  0.04 D, so 0.3 m cubes (two across the slice, ~35 particles per cell on
  average) keep their method and fit the geometry.
- **Radial, not axial.** In the real mill's belly there is no end wall, so
  axial segregation in the slice is an artefact; radial segregation is the
  result, and the axial profile only checks the artefact.

## Verdict and how to defend it

"Dataset runs start from the static IC and are recorded from t = 0 every
0.05 s, as in Kishida et al. (2025, §3). Durations are scaled by revolutions
(20 s and 35 s, i.e. 3.2 and 5.5 revolutions, against 2.5 and 5 in the
reference at 15 rpm), five replicates per initial condition show the
run-to-run spread, mixing is measured with Lacey's index on 0.3 m cubic
cells (Kishida et al. found it insensitive below 0.04 D) and segregation by
the radial fraction of large particles, and the 20-frame training window is placed after the measured quasi-steady
state of kinetic energy, the criterion used by Kishida et al. (§3, Fig. S1)."

## Open items / validation

- **End-wall artefact in segregation metrics** ([10](10_mill_geometry.md)):
  report the near-wall layers (~1-2 ball diameters from each frictionless
  end wall) separately from the slice centre, or show they agree;
  segregation next to the end walls has no counterpart in the real mill's
  belly.

- Pilot RMIC run: measure the time to quasi-steady kinetic energy / power /
  charge angle; set `start_frame` / `dt0` from it.
- Check the Lacey index curves reach their plateau within the run length
  (SIC 5 rev); extend if not.
- Separate run types in the code: `calibrate` (spin-up, steady state),
  `make_ic`, `dataset` (record from rest).

## Pending code changes

| ID | Change | Current code | When |
|---|---|---|---|
| C14-1 | Run types: `dataset` (load IC, start from rest, record from t = 0 for 20 / 35 s), `calibrate` (spin-up, then record), `make_ic` | One pipeline with spin-up before recording | Before datasets |
| C14-2 | `MetricsOptions.cell_size = 0.3` | Done (`5c194ab`) | With C14-3 |
| C14-3 | Radial large-particle fraction (result) and axial profile with near-wall vs centre layers (artefact check) | Not computed | Before datasets |
| C14-4 | Frames to parquet float32 at the end of each run; drop the per-frame CSVs | CSV per frame, converted later | Any time |
| C14-5 | `start_frame` / `dt0` from the pilot's quasi-steady time | 66 / 4.05 (old dataset) | After the pilot |


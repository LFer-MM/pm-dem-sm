# 16 -- Validation checks (acceptance criteria per run)

Every calibration and dataset run must pass these checks; the results are
written to the run manifest so each dataset can be defended individually.

| # | Check | Criterion | Basis |
|---|---|---|---|
| V1 | Restitution recovery | Binary collision test per pair at the run's dt: measured e within ~2 % of input | Cleary 2001 §2, PDF p5 / j.83 ("If the integration is accurate then the coefficient of restitution ... should be recovered") |
| V2 | Steps per collision | >= ~20 for the 99th-percentile impact velocity of the run | Cleary 2001 §2, PDF p5 (15-25); Boemer & Ponthot §2.2.3, PDF p5 / j.57 (20-70); see [02](02_time_step.md) |
| V3 | Overlap | Mean <= ~0.5 %, P99 <= ~2 %, max < 10 % of the smaller **diameter** | Boemer §3.1.2, PDF p8 / j.60 (0.1-1 %); §4, PDF p13 (max ~10 %); Owen & Cleary §3, PDF p3 (~0.8 %) |
| V4 | Energy balance | Energy supplied (integral of torque x omega) vs. energy dissipated in contacts: within a few % over the steady part | Cleary & Morrison §2, PDF p3 / j.77 |
| V5 | No artificial damping | `NewtonIntegrator.damping == 0`, set explicitly, in **every** stage (fill, settle, packing measurement, calibration, dataset) | [04](04_numerical_damping.md) |
| V6 | Inventory | Same particle counts per species in every frame; no particle outside the shell | Integrity check of `data_processing` |
| V7 | Quasi-steady time | Kinetic energy / power / charge angle quasi-steady before the training window; Lacey index reaches its plateau within the SIC run (else extend the run) | Kishida 2025 §3, PDF p6; SM Fig. S1; [14](14_dataset_runs_and_recording.md) |
| V8 | Charge shape (calibration runs) | Bulk toe and shoulder within SAG_A's interquartile range, widened to the replicate scatter of V12 if that is larger | [15](15_calibration_targets.md) |
| V9 | dt sensitivity (once) | dt vs dt/2: toe, shoulder, power within run-to-run scatter | [02](02_time_step.md) |
| V10 | Stiffness sensitivity (once; kept 2026-10-19) | Both moduli x 0.5 (f = 52) and x 2 (f = 13), same dt = 2.5e-5 s, 3 revolutions each: toe, shoulder, power and charge angle within the replicate scatter (V12). Tests in this mixed steel-rock charge the insensitivity Boemer found for steel balls only | Boemer abstract and §4 (PDF p13); [03](03_stiffness_young_modulus.md) |
| V11 | End-wall sensitivity (once) | Frictionless (baseline) vs liner-friction end walls, 3 revolutions each: toe, shoulder, power and segregation within the replicate scatter | [10](10_mill_geometry.md) |
| V11b | Ore-density sensitivity (once) | 2850 (baseline) vs 2650 kg/m^3, same moduli: toe, shoulder, power **and steel / rock segregation** within the replicate scatter | [08](08_density.md) |
| V11c | Friction pair structure (once) | Owen & Cleary set (steel-steel / steel-rock / rock-rock 0.4 / 0.5 / 0.8) vs the calibrated uniform mu_p: toe, shoulder and steel / rock segregation within the replicate scatter | [05](05_friction.md) |
| V11d | Restitution (once) | All e -0.1 and all e +0.1 (steel-steel capped at 0.9): toe, shoulder and segregation within the replicate scatter | [07](07_restitution.md) |
| V11e | Rolling resistance band (once) | mu_r that reproduces 33 deg and 41 deg in the heap test vs the 37 deg baseline: toe, shoulder and segregation | [06](06_rolling_resistance.md) |
| V12 | Replicate scatter | Replicates = **different seeds** (different random initial packings, everything else identical); spread of toe / shoulder / Lacey / radial-fraction curves over the seeds reported | Owen & Cleary §3 and Table 2, PDF p3 / j.21 (four centre-point repeats for error estimation) |
| V13 | No initial overlaps | Zero sphere-sphere and sphere-facet overlaps before the first step of every fill batch; abort otherwise. Spawning inside a facet ejects particles through it | [04](04_numerical_damping.md), [13](13_initial_conditions.md) |
| V14 | No escapes | Zero particles outside the shell radius or slice depth at the end of every stage | [04](04_numerical_damping.md) (instability test) |
| V15 | Plant power (once, after calibration) | P_mill = P_slice x (L / 0.6 m) x 1.05 (cone allowance, Doll 2013) vs P_charge,plant = eta_d x (P_motor - P_NL) in the same operating window; report the % deviation (not a pass / fail target; ~+-20 % consistent with the comparison uncertainty) | [15](15_calibration_targets.md); Govender 2015 §3 (6.8 vs 7.1 MW) |
| V16 | Fill level | Settled J (Morrell convention, from the stopped surface profile) within +-0.5 points of Jb (ball stage) and Jc (full charge) | [12](12_charge_fill_and_particles.md) |
| V17 | Determinism (once) | Rerun one short case with the same seed on 1 thread: bit-identical result. Confirms that the spread in V12 comes from the initial packing, not from the software (multithreaded runs are not bit-reproducible: test 2026-11-02, 3,000 spheres, 4 threads, median 0.6 mm divergence after 20,000 steps) | [14](14_dataset_runs_and_recording.md) |
| V18 | IC settle stop | Every IC settle stage ends by the geometric stop rule (charge geometry stationary, mean speed < 1 cm/s), not by the time cap; the stop condition is recorded | [13](13_initial_conditions.md); C06-4 |
| V19 | End-wall layers (dataset runs) | Radial large-particle fraction in the near-wall layers (one ball diameter from each end wall) vs the centre layer, reported with every segregation result | [10](10_mill_geometry.md), [14](14_dataset_runs_and_recording.md) |

## Notes

- V4 uses YADE's energy tracker (`O.trackEnergy = True`) for contact
  dissipation and the mill torque logged by `monitor.py` for the input.
- V1 and V2 are cheap and should run automatically before any long run with a
  new material set or dt.
- How the per-run checks are judged (C16-1, `postprocess.validation_summary`):
  - V3 is judged over the settle, spin-up and record stages; the pouring
    transient of the fill stage stays recorded in the manifest. The mean is
    the time average of the logged per-row means.
  - V4 passes at |residual| <= 5 % over the record stage. On the 360-particle
    smoke mill with a 1 s record the residual scatters run to run by about
    +-20 % (four repeats: +19 %, +20 %, +8 %, -11 %; the rolling dissipation is
    a sampled estimate), so a smoke-test V4 failure says nothing; at full
    scale the pilot's 20 s record gave -0.2 %.
  - V7 is the spin-up's steady-state verdict for `calibrate` runs. For
    `dataset` runs it needs the quasi-steady time of kinetic energy, power
    and charge angle to leave the 1 s training window before the end,
    plus a Lacey plateau.
  - V8, V16 and V19 are reported, with no pass / fail yet.
- One-off studies: V9 (dt), V10 (stiffness), V11 (end walls), V11b (ore
  density), V11c (friction pair structure), V11d (restitution), V11e
  (rolling resistance), V15 (plant power), V17 (determinism). Their results
  go in the thesis as evidence that the modelling choices do not drive the
  conclusions.
- Replicate scatter (V12) is the yardstick for "within the scatter" in
  V8-V11e.
- **Results at the calibrated point (2026-11-08,
  [15](15_calibration_targets.md) "Calibration outcome"):** V12 over seeds
  0-2 with the rechecked count (17,270 rocks): toe 240.1 +- 0.2 deg, shoulder
  37.2 +- 0.2 deg, slice power 1,108 +- 5 kW (16,082 rocks: 240.8 / 36.6 /
  1,111). V15: -7.9 % (c_cone 0.05) to -0.8 % (0.13) against the plant's power
  reaching the charge. V8 not met: the toe / shoulder residual (26 / 10 deg)
  is far outside the replicate scatter and is attributed to the reference
  angles (Maleki-Moghaddam's correlation), as argued in topic 15.

### Sensitivity results (Phase D, 2026-11-12/13)

One run per check at the calibrated point (mu_p 0.3, mu_w 0.5, mu_r 0.16;
3,437 + 17,270 particles), each pouring its own bed, spinning up to steady
state and recording 3 revolutions (V9: 2), compared with `sens_baseline`
(the same, unchanged). V10 ran earlier against the calibrated point at
16,082 rocks. Every run passed its per-run checks. Segregation (V11,
V11b-e) was computed afterwards from the saved frames with the dataset
functions (`postprocess.segregation_profiles`, `lacey_series`;
`data/raw/calibration/sensitivity_segregation.json`).

**Yardstick (V12, the calibrated point's 3 seeds):** toe +-0.2 deg,
shoulder +-0.2 deg, power +-5 kW; Lacey 0.992 +- 0.0002; large-particle
fraction in the outer (liner-side) half of the radius 0.177 +- 0.0005, in
the inner half 0.121 +- 0.003; near-wall minus centre -0.133 +- 0.002. The
baseline itself (one seed, 3 recorded revolutions) differs from the seeds'
mean by -0.3 deg (toe) and -0.004 (Lacey): record length alone moves the
time averages by about that much.

| Check | Change | Toe | Shoulder | Power | Lacey | Large fraction outer / inner | Literal verdict (within +-2 sd) | Interpretation |
|---|---|---|---|---|---|---|---|---|
| baseline | -- | 239.8 | 37.3 | 1,114 kW | 0.988 | 0.179 / 0.117 | -- | -- |
| V9 | dt / 2 (2.5e-5 -> 1.25e-5 s) | +1.0 | -0.9 | +0.8 % | -- | -- | not within | small; dt converged at the 1 deg / 1 % level |
| V10 | E x 0.5 / x 2 | +0.0 / +0.1 | +0.0 / +0.6 | -0.3 / +0.8 % | -- | -- | within / shoulder just outside | stiffness reduction does not drive the results (f = 52 fails V3, expected) |
| V11 | liner-friction end walls | **+6.8** | **+28.6** | +1.6 % | **0.964** | **0.196 / 0.172** | not within | **real effect**: in a 0.6 m slice the walls hold back the whole charge (2.4x more particles carried to 45-70 deg across the whole width, spin-up 4.25 rev); confirms frictionless end walls |
| V11b | rock density 2,650 | -0.1 | +0.4 | -0.9 % | 0.988 | 0.179 / 0.118 | shoulder at the edge, rest within | no effect |
| V11c | Owen pair set 0.4 / 0.5 / 0.8 | +1.9 | +2.0 | -0.6 % | 0.989 | 0.178 / 0.134 | not within | small; uniform mu_p justified (05) |
| V11d | e -0.1 / +0.1 | +0.9 / -1.0 | -0.6 / +0.3 | +0.2 / +0.1 % | 0.990 / 0.987 | 0.178 / 0.120 ; 0.179 / 0.115 | not within | small |
| V11e | mu_r 0.11 (33 deg) / 0.30 (~40 deg) | -1.4 / +2.3 | -1.6 / +1.9 | -0.8 / +1.5 % | 0.991 / 0.986 | 0.177 / 0.109 ; 0.180 / 0.131 | not within | small; the repose band moves the angles by ~2 deg |

**Firmer yardstick and combined best case (2026-11-19).** Two more seeds of
the baseline (`sens_baseline_s1`, `_s2`) give the replicate scatter
**recorded like the sensitivity runs** (3 revolutions, 3 seeds): toe 240.0
+- 0.19 deg, shoulder 37.4 +- 0.37 deg, power 1,111 +- 7.5 kW (0.7 %),
Lacey 0.988 +- 0.0013, large fraction outer / inner 0.179 +- 0.0005 /
0.118 +- 0.003 (`data/raw/calibration/replicates_3rev_and_best_case.json`).
The 2-revolution yardstick above was too narrow for the shoulder (x 2) and
Lacey (x 6). Against +-2 sd of this one: **V10 and V11b are within on
everything** (V11b including segregation); **V11d** is within on shoulder,
power, Lacey and the radial fractions, outside only on the toe (+-1 deg);
V9, V11c, V11e (by design: the band's ends) and V11 stay outside.

A **combined best case** (`sens_best_case_combined`, commit `5766625`): every
lever that moved the toe towards the target within plausible values, at
once -- mu_r 0.11 (33 deg ore) and restitution +0.1 (mu_p is already at the
bottom of its range, mu_w 0.5 was the grid's best, the Owen set and the end
walls move the wrong way, density does nothing). Measured against the
3-seed mean: **toe -2.8 deg (237.2), shoulder -0.7 deg (36.7)**, power
-0.7 %, segregation unchanged (Lacey 0.992); the sum of the single effects
predicted -2.4 / -1.3 deg. The plausible levers together move the toe by
~3 deg, leaving 23 deg to the 214 deg target.

**Literally** (against the 2-revolution yardstick), only V11b (and V10) stay within the replicate scatter: the
yardstick from three seeds is very narrow (0.2 deg, 0.0002 in Lacey), and
record length alone shifts the averages by about that much. **In
substance**, every modelling choice except the end walls moves the toe and
shoulder by at most ~2 deg, the power by < 2 % and the segregation state
barely (Lacey 0.986-0.991, outer fraction +-0.003, inner fraction within
0.02), an order of magnitude below the 26 deg toe residual of the
calibration ([15](15_calibration_targets.md)). The end-wall choice is the
one that matters, and the frictionless walls are what the setup uses.
The first V9 run failed in the pour (`fill.settle_steps` counts steps, so
half dt halved the settling time; V13 abort); fixed in commit `5d5577b`
(40,000 steps = the baseline's 0.5 s) and rerun.

## Implementation

The code, rerun commands, stored results and provenance (commit, date) of
every check run so far are indexed in
[`scripts/validation/README.md`](../../scripts/validation/README.md).

| Check | Code item |
|---|---|
| V1 | C01-4 (binary-collision script) |
| V2 | C02-2 / C02-3 ([02](02_time_step.md)) |
| V3 | C03-2 (overlap statistics) |
| V10 | C03-3 |
| V4 | C04-3 (energy tracking) |
| V5 | C04-2 |
| V13, V14 | C04-4 |
| V16 | C12-3 (grind-out / crash-stop script) |
| V18 | C04-5 (geometric stop rule) |
| V8 | C15-1 (toe / shoulder extraction) |
| V15 | C15-3 |
| V19 | C14-3 (radial / axial profiles) |
| V6, V7, all per-run checks together | C16-1 (`postprocess.validation_summary`: value, criterion and pass / fail / reported per check) |
| V9, V10, V11, V11b-e scenario files | C03-3 (`configs/simulation/sensitivity/`) |

## Pending code changes

| ID | Change | Current code | When |
|---|---|---|---|
| C16-1 | Validation step: run the per-run checks (V2-V7, V13, V14, V16, V18, V19) and write their results to the run manifest | Done (`69e6ea0`): `simulation/postprocess.validation_summary`, run by `pm-dem-sm dem-sim` after every successful run and by `dem-post`; manifest `validation` and `validation.json` (also V8 reported for calibrate runs) | Before calibration |


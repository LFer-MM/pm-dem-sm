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
| V7 | Quasi-steady time | Kinetic energy / power / charge angle quasi-steady before the training window | Kishida 2025 §3, PDF p6; SM Fig. S1 |
| V8 | Charge shape (calibration runs) | Bulk toe and shoulder within the interquartile range of SAG_A (the reference mill) | [15](15_calibration_targets.md) |
| V9 | dt sensitivity (once) | dt vs dt/2: toe, shoulder, power within run-to-run scatter | [02](02_time_step.md) |
| V10 | Stiffness sensitivity (once; kept 2026-10-19) | Both moduli x 0.5 (f = 52) and x 2 (f = 13), same dt = 2.5e-5 s, 3 revolutions each: toe, shoulder, power and charge angle within the replicate scatter (V12). Tests in this mixed steel-rock charge the insensitivity Boemer found for steel balls only | Boemer abstract and §4 (PDF p13); [03](03_stiffness_young_modulus.md) |
| V11 | End-wall sensitivity (once) | Frictionless (baseline) vs liner-friction end walls, 3 revolutions each: toe, shoulder, power and segregation within the replicate scatter | [10](10_mill_geometry.md) |
| V11b | Ore-density sensitivity (once) | 2850 (baseline) vs 2650 kg/m^3, same moduli: toe, shoulder, power **and steel / rock segregation** within the replicate scatter | [08](08_density.md) |
| V12 | Replicate scatter | Spread of toe / shoulder / Lacey curves over seeds reported | Owen & Cleary Table 5 / §4.1 (4 centre-point replicates, PDF p4) |
| V13 | No initial overlaps | Zero sphere-sphere and sphere-facet overlaps before the first step of every fill batch; abort otherwise. Spawning inside a facet ejects particles through it | [04](04_numerical_damping.md), [13](13_initial_conditions.md) |
| V14 | No escapes | Zero particles outside the shell radius or slice depth at the end of every stage | [04](04_numerical_damping.md) (instability test) |
| V15 | Plant power (once, after calibration) | P_mill = P_slice x (L / 0.6 m) x 1.05 (cone allowance, Doll 2013) vs P_charge,plant = eta_d x (P_motor - P_NL) in the same operating window; report the % deviation (not a pass / fail target; ~+-20 % consistent with the comparison uncertainty) | [15](15_calibration_targets.md); Govender 2015 §3 (6.8 vs 7.1 MW) |
| V16 | Fill level | Settled J (Morrell convention, from the stopped surface profile) within +-0.5 points of Jb (ball stage) and Jc (full charge) | [12](12_charge_fill_and_particles.md) |

## Notes

- V4 uses YADE's energy tracker (`O.trackEnergy = True`) for contact
  dissipation and the mill torque logged by `monitor.py` for the input.
- V1 and V2 are cheap and should run automatically before any long run with a
  new material set or dt.
- V9-V11 are one-off studies; their results go in the thesis as evidence that
  the numerical choices do not drive the conclusions.

# 01 -- Contact model

## Decision

Use the **Hertz-Mindlin** model in YADE
(`Ip2_FrictMat_FrictMat_MindlinPhys` + `Law2_ScGeom_MindlinPhys_Mindlin`) with:

- pair-wise normal restitution through a `MatchMaker` on `en` (see [07](07_restitution.md));
- pair-wise friction through a `MatchMaker` on `frictAngle` (see [05](05_friction.md));
  without it YADE uses the **minimum** of the two materials' friction angles;
- rolling resistance through `includeMoment=True`, `krot`, `eta` (one value for all
  contacts: not per-pair in base YADE, see [06](06_rolling_resistance.md)), which needs the
  6-DOF geometry functors `Ig2_Sphere_Sphere_ScGeom6D` / `Ig2_Facet_Sphere_ScGeom6D`
  (see [06](06_rolling_resistance.md)).

Documented alternative: YADE's linear spring-dashpot `ViscElMat` +
`Ip2_ViscElMat_ViscElMat_ViscElPhys` + `Law2_ScGeom_ViscElPhys_Basic`
(supports `en`, `et`, `frictAngle` MatchMakers), which is the model family used
by the mill papers.

## Evidence

| Source | What it says | Where | Verified |
|---|---|---|---|
| Kishida 2025 | All DEM simulations of the reference RNNSR study use the **Hertz-Mindlin** contact model with a rolling-friction torque; stiffness and damping from Young's modulus, Poisson's ratio and restitution (Table A-1) | Appendix A, Eqs. (A-1)-(A-6) and Table A-1, PDF p11-12; software "EDEM 2023" in §2.2.1, PDF p4 | Yes |
| Cleary & Morrison 2016 | "The collision model used in this work is a linear spring-dashpot model"; tangential stiffness half the normal one | §4 text before Table 2, PDF p7 / j.81; §2, PDF p3 / j.77 | Yes |
| Owen & Cleary 2015 | Linear spring-dashpot; normal stiffness 20e6 N/m; shear stiffness half of normal | §2, PDF p2 / j.20; §3, PDF p3 / j.21 | Yes |
| Boemer & Ponthot 2017 | Linear spring-slider-damper, **run in YADE** ("The time integration scheme implemented in YADE ...", §2.2.3); kt = kn, ct = cn | §2.2.3, PDF p5 / j.57; §3.1.1, PDF p8 / j.60; Table 2, PDF p7 / j.59 | Yes |
| Boemer & Ponthot 2017 | "the charge motion and the power draw are relatively insensitive to the stiffness and the damping coefficient of the linear spring-slider-damper contact law, the coefficient of friction has a strong influence" | Abstract, PDF p1 / j.53 | Yes |
| Govender 2015 | Linear spring dash-pot for normal and tangential forces | §1.5 "Force model", Eqs. (7)-(8), PDF p6 / j.157 | Yes |
| Cleary 2001 (2D) | Linear spring with kn = 8e6 N/m; 15-25 steps per collision | §2, PDF p4-5 / j.82-83 | Yes |
| YADE (this build, `yadedaily` 20260115) | `FrictPhys` (used by `Law2_ScGeom_FrictPhys_CundallStrack`) has only `kn`, `ks`, `tangensOfFrictionAngle` -- **no dashpot, no restitution**. `Ip2_FrictMat_FrictMat_MindlinPhys` has `en`, `es`, `frictAngle`, `krot`, `ktwist`, `eta`. `ViscElMat` has `en`, `et`, `kn`, `ks`, `tc`. | Introspection of the installed classes (attribute lists) | Yes (run on this machine) |

## PPT

| Slide | Content |
|---|---|
| 8 | "En YADE DEM el modelo para contactos de Cundall-Strack no admite pares de coeficientes de restitucion, por lo que se optara por el modelo de Hertz-Mindlin. Dando prioridad a volver configurables friccion y restitucion, y permitiendo al modelo calcular la rigidez de manera automatica en cada iteracion." |
| 8 | "En Cleary & Owen (2016) utilizan el modelo de contacto de Cundall-Strack ... admite coeficientes de friccion, restitucion y rigidez. [1]" -- [1] is Cleary & **Morrison** 2016, and their model is a linear spring-**dashpot** (with restitution), not YADE's Cundall-Strack law, which has no dashpot. |

## Current state

| Where | What |
|---|---|
| `simulation/yade_dem/engines.py:76-83` | Hertz-Mindlin (`Ip2_FrictMat_FrictMat_MindlinPhys` with `en` = restitution MatchMaker, `Law2_ScGeom_MindlinPhys_Mindlin`), `Ig2_*_ScGeom` (not `ScGeom6D`): no `frictAngle` MatchMaker (min rule), no rolling moment |
| `engines.py:64-68` | Optional `Law2_ScGeom_FrictPhys_CundallStrack` -- no collisional damping at all (C01-3) |
| `simulation/yade_dem/materials.py:39` | Restitution MatchMaker built from material labels (used); the old id-based `config.restitution_matchmaker()` (`config.py:482-499`) is unused (C07-2) |

## Analysis

1. The PPT's reason for leaving Cundall-Strack is correct and is in fact
   stronger than stated: in YADE that law has **no dashpot**, so the only
   dissipation left is friction plus the integrator's artificial damping
   (see [04](04_numerical_damping.md)).
2. The mill literature uses linear spring-dashpot models (Cleary & Morrison,
   Owen & Cleary, Boemer & Ponthot, Govender). Kishida -- the method this
   project reproduces -- uses Hertz-Mindlin. Boemer & Ponthot show the
   macroscopic charge motion and power are insensitive to stiffness and
   damping formulation, so the choice linear vs. Hertz does not limit fidelity;
   friction (and particle shape, see [06](06_rolling_resistance.md)) does.
3. Hertz-Mindlin derives stiffness from E and nu, so the stiffness reduction in
   [03](03_stiffness_young_modulus.md) stays expressed in physical units.

## Verdict and how to defend it

Hertz-Mindlin is kept because (a) it is the model of the reference surrogate
study (Kishida 2025, App. A), (b) it supports pair-wise restitution and
friction and a rolling-resistance torque in YADE, and (c) Boemer & Ponthot --
a YADE study validated against a 1:5 lab mill -- show that charge motion and
power are insensitive to the stiffness/damping formulation, so the deviation
from the linear models used in the mill papers is not a fidelity concern.

## Open items / validation

- Check that YADE recovers the input restitution in binary collisions at the
  chosen dt (see [16](16_validation_checks.md)); Cleary 2001 (§2, PDF p5)
  uses exactly this as the accuracy criterion of the integration.
- If calibration cannot reach the plant toe / shoulder, the `ViscElMat` linear
  model is the fallback that matches the mill papers one-to-one.

## Pending code changes

| ID | Change | Current code | When |
|---|---|---|---|
| C01-1 | **Merged into C05-2** ([05](05_friction.md)): `frictAngle` `MatchMaker` built from material labels | Not set: YADE uses the minimum of the two materials' friction angles | See C05-2 |
| C01-2 | 6-DOF geometry (`Ig2_Sphere_Sphere_ScGeom6D`, `Ig2_Facet_Sphere_ScGeom6D`) and `Law2_ScGeom_MindlinPhys_Mindlin(includeMoment=True)` with `krot`, `ktwist`, `eta` | `ScGeom`, no moment law (`engines.py`) | Implemented as C06-1 with values from [06](06_rolling_resistance.md) (uniform eta, ktwist = 0); also needed to investigate the residual-spin floor ([13](13_initial_conditions.md)) |
| C01-3 | Remove the `cundall_strack` contact option (no collisional dissipation in YADE), optionally replacing it with the `ViscElMat` linear fallback | Still offered (`engines.py`, `scenario.CONTACT_MODELS`) | Any time |
| C01-4 | V1 restitution-recovery script: one binary collision per material pair at the run's dt, measured vs input e | None | With the run-type split ([14](14_dataset_runs_and_recording.md)) |

# 06 -- Rolling resistance

## Decision

Decided 2026-10-21.

- **One rolling-resistance coefficient mu_r for all contacts** (rock, steel,
  liner): YADE `Ip2_FrictMat_FrictMat_MindlinPhys.eta`. Per-pair or
  per-material rolling resistance is not available for the Hertz-Mindlin
  model in base YADE (verified in the source and the documentation, see
  Evidence), and a uniform value adds no contrast between species, in line
  with the uniform mu_p of [05](05_friction.md).
- **mu_r is not calibrated against the mill.** The two mill targets (toe,
  shoulder) are used for mu_p and mu_w ([05](05_friction.md)). mu_r is
  fixed by a **third, independent target: the angle of repose of the ore**,
  reproduced with a rock-only heap simulation. The heap does not involve
  mu_w, so the three targets (toe, shoulder, repose) identify the three
  parameters (mu_p, mu_w, mu_r).
- **Repose target: 37 deg**, sensitivity band 33-41 deg (sources and their
  weight in Analysis). No plant measurement is available.
- **Result of the heap test (C06-3, 2026-11-05): mu_r = 0.13** for 37 deg
  at the baseline mu_p = 0.5, and 0.08 / 0.19 for 33 / 41 deg (V11e),
  each about +-0.02 from the seed scatter (Analysis, "Heap test results").
  To be re-checked once the mill calibration fixes mu_p (step 3 below).
- **Re-checked at the calibrated mu_p = 0.3 (2026-11-08): mu_r = 0.16.**
  At mu_p 0.3 the heap with mu_r 0.13 stands at 34.0 deg, 3 deg below the
  target (more than the 2 deg of step 3), so mu_r was re-fitted with the
  same quadratic cell-top fit (12 heaps, residual 1.9 deg; the linear fit
  gives 0.168):

  | mu_r | 0.13 | 0.15 | 0.18 | 0.21 |
  |---|---|---|---|---|
  | Repose (3 seeds) | 34.0 +- 1.1 | 35.8 +- 2.3 | 39.0 +- 2.0 | 39.0 +- 2.1 |

  37 deg at mu_r = 0.157, taken as **0.16**. The calibrated point (mu_p 0.3,
  mu_w 0.5, mu_r 0.16) was then run with 3 seeds
  ([15](15_calibration_targets.md), "Calibration outcome"). Data:
  `data/raw/validation/results/heap_mup0p3/`.
- **Settings:** `ktwist = 0`; `krot` chosen from the time step and a
  yield-rotation criterion (Analysis); 6-DOF geometry functors.

YADE implementation: `Ig2_Sphere_Sphere_ScGeom6D`, `Ig2_Facet_Sphere_ScGeom6D`,
`Ip2_FrictMat_FrictMat_MindlinPhys(eta=mu_r, krot=..., ktwist=0)`,
`Law2_ScGeom_MindlinPhys_Mindlin(includeMoment=True)`.

## Evidence

| Source | What it says | Where | Verified |
|---|---|---|---|
| YADE source (`7c8d01e`, the installed `yadedaily` build) | Plastic limit of the rolling moment: `maxBendPl = eta * Rmean`, Rmean = (R1 + R2) / 2 (for a facet the sphere radius is used); `MomentMax = maxBendPl * |F_n|`; the bending moment is scaled back to MomentMax when exceeded. So **M_max = eta R_mean |F_n|**, the form of Kishida's Eq. (A-6) with eta = mu_rf | `pkg/dem/HertzMindlin.cpp:142-143, 154, 170, 688-694` | Yes (source read) |
| YADE source | `eta`, `krot`, `ktwist` are plain `Real` attributes of the Ip2 functor (one value for the whole simulation); the only `MatchMaker` attributes are `en`, `es`, `betan`, `betas`, `vn`, `frictAngle` | `pkg/dem/HertzMindlin.hpp:101-113` | Yes |
| YADE source | Only the **bending** moment is capped; the twisting moment `momentTwist` grows elastically with `ktwist` without any plastic limit | `pkg/dem/HertzMindlin.cpp:640-697` | Yes |
| YADE source | `kr = krot` is a constant per contact (not scaled with radius or normal force); no rolling dashpot in this law | `pkg/dem/HertzMindlin.cpp:168, 645-647` | Yes |
| YADE source | Per-material rolling resistance exists only in other contact models: `ViscElMat.mR` (pair value = harmonic mean, `ViscoelasticPM.cpp:301-305`) and `CohFrictMat.etaRoll` (pair value = min(etaRoll_i R_i), `CohesiveFrictionalContactLaw.cpp:472`) | `ViscoelasticPM.hpp:40`, `CohesiveFrictionalContactLaw.hpp:32` | Yes |
| YADE docs 2021 | `Ip2_FrictMat_FrictMat_MindlinPhys`: "The en, βn, es, βs, vn are MatchMaker objects"; `eta` "Coefficient to determine the plastic bending moment"; `krot` "Rotational stiffness for moment contact law" | printed p. 562 (PDF p569) | Yes |
| YADE (installed build) | Attributes of `Ip2_FrictMat_FrictMat_MindlinPhys`: betan, betas, en, es, eta, frictAngle, gamma, krot, ktwist, vn | `dir()` on this machine | Yes |
| Kishida 2025 | Rotational equation includes "torque due to the rolling resistance" M_rf; M_rf = -mu_rf r |F_cn| omega / |omega| | Appendix A, Eqs. (A-2) and (A-6), PDF p11-12 | Yes |
| Kishida 2025 | Rolling friction coefficient 0.01 (fine powders) | Fig. 2(b), PDF p4 | Yes |
| Thakur 2016 | Particle rolling friction 0.001 (uniaxial-test simulations) | Parameter table, PDF p5 / j.134 | Yes |
| Li et al. 2005 | Spheres with sliding friction only ("rolling friction is ignored"): repose angles of glass and steel ball piles ~24-27 deg (Q2D), 3-3.5 deg lower for conical piles | §1 PDF p2 / j.220; Table 4 PDF p7 / j.225; §5 PDF p7-8 | Yes |
| Cleary 2001 (2D) | "Increasing the angularity or aspect ratios of the rock ... strengthens the charge and makes slope failure more difficult. For sub-critical speeds, this leads to higher dynamic angles of repose ..., to higher shoulder positions and to higher power consumption." | §11 Conclusion, PDF p34 / j.112 | Yes |
| Cleary 2001 (2D) | Non-circular particles: charge "significantly dilated"; for N <= 75 % critical "there is no change in the mill power draw" | §10, PDF p28-29 / j.106-107 | Yes |
| Cleary & Morrison 2016 | Particles are **super-quadrics**, so their mu = 0.5 already includes shape interlocking | §3.2, PDF p3 / j.77 | Yes |
| Wei et al. 2022 | Irregular lump materials (pellet, sinter, coke; 6-15 mm) as spheres: measured repose 24.7-27.4 deg on the same material, reproduced with rolling friction 0.2-0.3 (EDEM, Hertz-Mindlin with "RVD" rolling model) | Tables 4-5, §3.2 | Yes (online, open access) |
| Engineering Toolbox | Angle of repose: "Ore, damp or fresh mined" 37 deg; "Ore, dry" 30 deg; "Stone, crushed" 30; "Gravel" 40 | "Angles of Repose" table | Yes (online; the table cites no primary source) |
| PDHonline M344 (Primo, CEMA-based) | Flowability classes by angle of repose: 35-39 deg "General everyday material as for example bituminous coal and the majority of minerals" | p. "Belt Angle of Repose" table | Yes (online; course notes, secondary) |
| Marin Perez et al. 2024 (Particuology 92) | Calibration tests "are quite ambiguous and may not always lead to a single set of parameters on their own"; the draw down test with three aperture sizes and multi-sphere particles "can converge to a small feasible region in which a single combination of the friction coefficients can be selected" | §1, PDF p2; abstract, PDF p1 | Yes (2026-11-04) |
| Wensrich & Katterfeld 2012 | "Shape is a computationally expensive property to model in DEM, and so rolling friction is often employed in order to simulate its effects"; in repose tests spheres with rolling friction vs clumped particles: "Some similarities were observed, however, quantitatively, there was a significant discrepancy" | Abstract, PDF p1 / j.409 | Yes (2026-11-04) |
| Wensrich & Katterfeld 2012 | "a single angle of repose can be achieved from a wide range of parameters ... One bulk parameter from one type of test is entirely insufficient"; "Repeat simulations under the same conditions are extremely valuable" | §4.4, PDF p8 / j.416 | Yes |
| Wensrich & Katterfeld 2012 | Rolling stiffness: "there is a desire to set the rolling stiffness as high as possible within the bounds of numerical stability"; with natural frequencies of the same order as the contact's "the calculation of the critical time step is unaffected"; "With higher levels of rolling stiffness, the shear damping is mobilised and additional rolling damping is not required" | §2, PDF p3 / j.411 | Yes |
| Ai et al. 2011 | Four classes of rolling-resistance models: "a) directional constant torque models; b) viscous models; c) elastic-plastic spring-dashpot models; and d) contact-independent models" (YADE's Hertz-Mindlin moment law = class c without the dashpot) | §5, PDF p5 / j.273 | Yes (2026-11-04) |
| Ai et al. 2011 | Class c without rolling damping: "If the damping coefficient is zero, the disk oscillates permanently at the final position" (single disk); larger rolling stiffness gives faster oscillation | §6, PDF p7-8 / j.275-276, Fig. 8 | Yes |
| Ai et al. 2011 | Rolling stiffness rules: k_r = k_s R_r^2 (Iwashita & Oda, Eq. 7a); k_r = 3 k_n mu_r^2 R_r^2 (Eq. 7b); or via a mobilisation angle theta_r^m = mu_r / (2 J_n) (Eqs. 7c, 15); sandpile example with theta_r^m = 0.05 rad | §4.3, PDF p4-6 / j.272-274; §7, PDF p12 | Yes |

## PPT

No slide mentions rolling resistance. Slide 42 (structure map) lists
"Materials -> Mechanical Properties / Physical Interactions" without it.

## Current state

| Where | What |
|---|---|
| `engines.py:60-82` | `Ig2_Sphere_Sphere_ScGeom6D`, `Ig2_Facet_Sphere_ScGeom6D`, `Ip2_FrictMat_FrictMat_MindlinPhys(eta=mu_r, krot=..., ktwist=0)`, `Law2_ScGeom_MindlinPhys_Mindlin(includeMoment=True)` (C06-1, commit `4bb17e4`) |
| `config.ROLLING_RESISTANCE`, `scenario.py` (`ContactOptions.rolling_resistance`) | mu_r = **0.16** by default and in the production, smoke and sensitivity scenarios: the heap test's value for 37 deg at the calibrated mu_p = 0.3 (re-check 2026-11-08, Decision). It was 0.13 (37 deg at mu_p = 0.5; C06-3, commit `9959f69`; Analysis "Heap test results"); the calibration record (grid, probes) keeps the values it ran with. Before C06-3 it was a required input, with a 0.25 placeholder in the JSONs. It stays listed under `provisional_parameters` in every manifest until the heap is re-checked with the calibrated mu_p. mu_r = 0 switches the moment law off (`engines.initialize_engines`): in YADE, eta = 0 would leave the rolling spring uncapped |
| `scenario.py` (`rolling_stiffness()`, `check_rolling_stiffness()`) | C06-2, commit `4bb17e4`. `krot` is set so that the smallest sphere's rolling period is exactly 20 time steps, the stiffest the step resolves: with the defaults (r = 0.034925 m, 2850 kg/m^3, dt = 2.5e-5 s) krot = 39,183 N m/rad. At build, `run_simulation` checks T_r >= 20 dt and theta_y <= 0.01 rad at the typical contact force, and stops otherwise. The typical force (`typical_contact_force_n()`) is an order-of-magnitude, high-end estimate: the weight of a column of bulk charge (solid fraction 0.6) as deep as a flat bed holding the fill, standing on one small-particle cross-section (2 r)^2, ~560 N with the defaults. That gives theta_y = 1.3e-4 rad at mu_r = 0.25, far inside the 0.01 rad criterion, so the estimate's precision does not matter. `checks()` and the manifest record krot, T_r, the force and theta_y |

## Analysis

### Why rolling resistance at all

- Rock in a SAG mill is angular; here it is a sphere. Spheres with sliding
  friction only roll freely and pile at ~24-27 deg (Li et al. 2005), well
  below ore (30-37 deg in the handbook values below). The charge then has
  less shear strength than the real one: lower shoulder at sub-critical
  speeds (Cleary 2001, §11). At 73 % CS shape changes the power little
  (Cleary 2001, §10), so the effect shows mainly in charge shape -- the
  calibration targets.
- The mill papers that reach good agreement either use real shapes (Cleary
  & Morrison: super-quadrics) or media that really are spheres (Boemer:
  steel balls). Spheres standing in for rock is the case where DEM adds
  rolling resistance as a shape surrogate (Wensrich & Katterfeld 2012: "rolling
  friction is often employed in order to simulate its effects"; Wei et al.
  2022 for lump materials). Wensrich & Katterfeld also show that the
  match is only qualitative -- spheres with rolling friction reproduced
  clumped-particle repose angles with "a significant discrepancy" -- so
  mu_r is an effective parameter fixed by a bulk test, not a shape
  measurement.

### Uniform mu_r: verified limitation of base YADE

YADE's Hertz-Mindlin Ip2 functor holds `eta` as a single number and builds
`maxBendPl = eta * Rmean` for every contact; per-pair values exist only for
`en`, `es`, `betan`, `betas`, `vn` and `frictAngle` (source and docs, see
Evidence). Per-material rolling resistance exists in base YADE only in
other contact models (`ViscElMat.mR`, `CohFrictMat.etaRoll`), i.e. it would
mean leaving the Hertz-Mindlin model chosen in [01](01_contact_model.md).
The remaining routes are setting `MindlinPhys.maxBendPl` per interaction from
Python on every new contact, or a modified YADE build; both were rejected
(fragile, slow, not base YADE).

Consequences of a uniform mu_r:
- Steel balls, which are true spheres, also get rolling resistance. Accepted
  as a limitation, consistent with the uniform mu_p reasoning (no species
  contrast the data cannot support).
- Liner contacts get it too (part of the particle-liner interaction
  calibrated through mu_w).
- **End walls** (frictionless, [10](10_mill_geometry.md)) also get a rolling
  moment. It resists rotation about axes parallel to the wall, not the
  in-plane tumbling (rotation about the mill axis is twist relative to the
  end wall, and `ktwist = 0`). To be checked (Open items).

### How mu_r is fixed: angle of repose

- A rock-only heap is cheap (minutes) and does not involve the liner, so it
  adds the third, independent target that the mill alone cannot provide.
  It does depend on mu_p, so the two are iterated: (1) with mu_p = 0.5 find
  the mu_r that gives the target repose; (2) run the mill grid
  ([05](05_friction.md)); (3) recompute the heap with the calibrated mu_p;
  if the angle moves by more than ~2 deg, readjust mu_r and re-run the best
  grid points.
- Repose alone does not identify mu_p and mu_r together: "a single angle of
  repose can be achieved from a wide range of parameters ... One bulk
  parameter from one type of test is entirely insufficient" (Wensrich &
  Katterfeld 2012, §4.4; also Marin Perez et al. 2024, §1). Here mu_p is set
  by the mill, so the heap only has to fix mu_r.

### The repose target and the weight of its sources

| Source | Value | Weight |
|---|---|---|
| Engineering Toolbox | ore, damp or fresh mined: 37 deg; ore, dry: 30 deg | Handbook table, no primary source |
| PDHonline M344 (CEMA-based) | 35-39 deg: "the majority of minerals" | Course notes, secondary |
| Li et al. 2005 | Spheres without rolling resistance: ~24-27 deg | Lower bound the model must exceed |

SAG feed is damp, freshly mined ore, so **37 deg** is the target and
**33-41 deg** the sensitivity band (the mill shape is re-run with the mu_r
that gives each end). No peer-reviewed measurement for coarse SAG-feed ore
was found; this is stated as a limitation, and the band covers the spread
of the handbook values.

### krot, ktwist and the absence of rolling damping

- `ktwist = 0`: the twisting moment has no plastic limit in this law, so any
  `ktwist > 0` stores unbounded elastic twist.
- `krot` is one constant for all contacts. YADE's moment law is Ai et al.'s
  class c (elastic-plastic spring) **without** the dashpot. Wensrich &
  Katterfeld's guidance (§2) fixes the approach: set the rolling stiffness
  **as high as numerical stability allows** -- rotational natural frequency
  of the same order as the contact's, so the critical time step is
  unaffected -- because "with higher levels of rolling stiffness, the shear
  damping is mobilised and additional rolling damping is not required".
  The shear damping is present here (es = en, [07](07_restitution.md)).
  Criteria: (a) the rolling oscillation period of the smallest rock sphere,
  T_r = 2 pi sqrt(I / krot) with I = (2/5) m r^2, stays >= ~20 dt
  ([02](02_time_step.md)), i.e. as short as the step resolves; (b) the
  rotation to reach the plastic limit, theta_y = eta R |F_n| / krot, stays
  small, ~0.01 rad, well below Ai et al.'s mobilisation angle of 0.05 rad
  (§7), at typical contact forces. For comparison, Ai et al.'s rules (§4.3): k_r = k_s R^2
  (Iwashita & Oda) or k_r = 3 k_n mu_r^2 R^2.
- There is no rolling dashpot, and numerical damping is 0
  ([04](04_numerical_damping.md)). Ai et al. (§6, Fig. 8) show that an
  undamped class-c rolling spring keeps a single particle oscillating at
  rest. The settling test (C06-4) checks that a heap and a settled charge
  come to rest with the stiff krot and shear damping
  ([13](13_initial_conditions.md)).
- **eta = 0 is not "no rolling resistance" in YADE.** The plastic cap is
  applied only `if (MomentMax > 0)` (`HertzMindlin.cpp:688-690`, build
  `7c8d01e`), so eta = 0 leaves the rolling spring elastic and uncapped,
  i.e. unlimited rolling resistance. A heap with eta = 0 stood at 54 deg,
  steeper than any capped value. The code therefore switches the moment
  law off when mu_r = 0.

### Heap test results (C06-3, C06-4; 2026-11-04/05)

`yade_dem/heap.py` follows the design under Open items.

**Setup:**
- 900 rock spheres (r = 0.034925 m, 2850 kg/m^3) poured into a
  frictionless cylinder 10 rock diameters wide, on a hexagonal layer of
  fixed rock spheres.
- Settled by the geometric rule, cylinder lifted at 0.05 m/s and removed,
  settled again.
- The run's dt, moduli and contact law: mu_p = 0.5, krot from the time
  step, damping 0.
- Seeds 0-2 per value. Heaps end ~1.2 m across (17-18 d).

**Fit (`checks.repose_angle`):** the surface is the top sphere in each
one-diameter horizontal cell, and `top = h0 - tan(angle) rho` is fitted
over 20-80 % of the heap radius (~140 cells, R^2 ~ 0.8).

| mu_r | Seeds | Mean angle | Seed SD |
|---|---|---|---|
| 0.05 | 1 | 30.3 deg | -- |
| 0.10 | 3 | 34.8 deg | 0.3 deg |
| 0.15 | 3 | 38.3 deg | 2.3 deg |
| 0.20 | 3 | 41.3 deg | 0.6 deg |
| 0.25 | 3 | 43.9 deg | 2.1 deg |
| 0.30 | 3 | 44.6 deg | 1.5 deg |

A quadratic fit through the 16 heaps (0.05-0.30, residual 1.4 deg) gives:

| Target | mu_r |
|---|---|
| **37 deg** | **0.13** |
| 33 deg | 0.08 |
| 41 deg | 0.19 |

A linear fit agrees within 0.02. The angle rises steadily with mu_r and
has not saturated by 0.30. The no-rolling-resistance limit (24-27 deg, Li
et al.) lies below 0.05.

Uncertainties:
- **Seed scatter:** ~1.5 deg, i.e. about +-0.02 in mu_r.
- **Fitting method:** an earlier version took the highest sphere of each
  radial ring. That is biased (outer rings hold more particles), and it
  read 1.5-3 deg lower; the cell-top method replaced it.
- **Within one heap:** the 8 azimuthal sector fits spread by 3-7 deg.

The pile is near the ~20 d minimum of the design. A wider pile would
lower the scatter if the 37 deg value needs to be tighter.

C06-4 (heap part): every heap came to rest with damping 0 and rolling
resistance on (final mean speed <= 5e-7 m/s), within 1-1.7 s of settling.
The charge part is in [13](13_initial_conditions.md): the smoke-test bed
settles by the geometric rule to 0.007 mm/s.

Data: `data/raw/heap/` (JSON per heap with final positions;
`heap_refit.py` reproduces the table), not in git.

## Verdict and how to defend it

"Rock particles are spheres, while the ore is angular; particle shape
controls the shear strength of the charge and hence the shoulder position
(Cleary 2001, §10-11), and smooth spheres without rolling resistance pile
at only ~24-27 deg (Li et al. 2005). We therefore include a constant
rolling-resistance torque, M_max = mu_r R |F_n|, of the form used in the
reference surrogate study (Kishida et al. 2025, Eq. A-6), which is YADE's
Hertz-Mindlin moment law (eta = mu_r). Base YADE applies one value to all
contacts in this model, which also avoids imposing an unsupported contrast
between species. mu_r is fixed independently of the mill targets, by
reproducing an ore angle of repose of 37 deg (handbook value for damp,
freshly mined ore) in a heap simulation, with 33-41 deg as a sensitivity
band."

## Open items / validation

- **V11e at the calibrated mu_p:** the sensitivity band 33 / 41 deg was
  mu_r 0.08 / 0.19 at mu_p 0.5; at mu_p 0.3 the heap curve gives 34.0 deg at
  0.13 and levels off near 39 deg at 0.18-0.21, so neither end is bracketed.
  Heaps at mu_r ~0.08-0.10 and ~0.25-0.30 (mu_p 0.3) are needed before the
  V11e scenarios (`sensitivity/sens_v11e_*`, still at 0.08 / 0.19) are run.
- Search further for a measured repose angle of coarse SAG-feed or ROM ore
  (peer-reviewed or official CEMA 550 table).
- Heap test design: rock-only spheres with the simulated rock size, rough
  base (fixed rock spheres), lifted-cylinder or poured cone, pile >= ~20
  particle diameters across, damping 0, same dt; slope from a fit of the
  surface particles.
- Check the end-wall rolling moment: log the rolling moments of end-wall
  contacts in the pilot run and compare them with those of particle
  contacts (eta cannot be switched off per pair in base YADE, and the
  periodic cell leaked particles, [10](10_mill_geometry.md)); the end-wall
  sensitivity V11 covers the effect on the charge.

## Pending code changes

| ID | Change | Current code | When |
|---|---|---|---|
| C06-1 | 6-DOF geometry functors and `Law2_ScGeom_MindlinPhys_Mindlin(includeMoment=True)`; `Ip2_FrictMat_FrictMat_MindlinPhys(eta=mu_r, krot=..., ktwist=0)` from config (this is C01-2 with values) | Done (`4bb17e4`) | Before calibration |
| C06-2 | `krot` helper: from the smallest rock sphere, dt and a typical contact force, return krot meeting the T_r >= 20 dt and theta_y ~ 0.01 rad (<< 0.05 rad, Ai et al.) criteria; assert at build | Done (`4bb17e4`): krot at exactly T_r = 20 dt; the typical force is the static-bed estimate in Current state | With C06-1 |
| C06-3 | Heap (angle-of-repose) script: rock-only pile, slope fit, returns the angle for given (mu_p, mu_r) | Done (`494c1f3`, refit `9959f69`): `yade_dem/heap.py`; mu_r = 0.13 (37 deg), 0.08 (33 deg), 0.19 (41 deg), see Analysis | Before calibration |
| C06-4 | Settling test with rolling resistance and damping 0: heap and charge reach rest (mean speed below the [13](13_initial_conditions.md) threshold) | Done: heaps at rest (<= 5e-7 m/s), smoke-test charge settles by the geometric rule to 0.007 mm/s; full-scale charge with the grind-out runs (C12-3) | With C06-1 and C04-5 |

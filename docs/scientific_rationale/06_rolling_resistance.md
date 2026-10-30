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
| Marin Perez et al. (Strathclyde, preprint 2024) | Bulk calibration tests "may not always lead to a single set of parameters on their own"; combining criteria narrows mu_s / mu_r to a feasible region | §1 | Yes (online preprint) |
| Wensrich & Katterfeld 2012 | *Rolling friction as a technique for modelling particle shape in DEM*, Powder Technol. 217, 409-417, doi 10.1016/j.powtec.2011.10.057 | -- | **No** (paywalled; to obtain) |
| Ai et al. 2011 | *Assessment of rolling resistance models in discrete element simulations*, Powder Technol. 206, 269-282, doi 10.1016/j.powtec.2010.09.030 (rolling stiffness and damping of elastic-plastic models) | -- | **No** (paywalled; to obtain) |

## PPT

No slide mentions rolling resistance. Slide 42 (structure map) lists
"Materials -> Mechanical Properties / Physical Interactions" without it.

## Current state

| Where | What |
|---|---|
| Branch `engines.py:64, 76-77` | `Ig2_Sphere_Sphere_ScGeom`, `Ig2_Facet_Sphere_ScGeom` (no 6-DOF); `includeMoment` not set: **no rolling resistance** |

## Analysis

### Why rolling resistance at all

- Rock in a SAG mill is angular; here it is a sphere. Spheres with sliding
  friction only roll freely and pile at ~24-27 deg (Li et al. 2005), well
  below ore (30-37 deg in the handbook values below). The charge then has
  less shear strength than the real one: lower shoulder at sub-critical
  speeds (Cleary 2001, §11). At 69 % CS shape changes the power little
  (Cleary 2001, §10), so the effect shows mainly in charge shape -- the
  calibration targets.
- The mill papers that reach good agreement either use real shapes (Cleary
  & Morrison: super-quadrics) or media that really are spheres (Boemer:
  steel balls). Spheres standing in for rock is the case where DEM adds
  rolling resistance as a shape surrogate (Wei et al. 2022 for lump
  materials; Wensrich & Katterfeld 2012, to be read).

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
- Repose alone does not identify mu_p and mu_r together (Marin Perez et al.,
  §1); here mu_p is set by the mill, so the heap only has to fix mu_r.

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
- `krot` is one constant for all contacts. Two criteria fix it: (a) the
  rolling oscillation period of the smallest rock sphere,
  T_r = 2 pi sqrt(I / krot) with I = (2/5) m r^2, stays >= ~20 dt so it does
  not limit the time step ([02](02_time_step.md)); (b) the rotation needed to
  reach the plastic limit, theta_y = eta R |F_n| / krot, stays small
  (~0.01 rad) at typical contact forces, so the moment is essentially
  rigid-plastic. Ai et al. 2011 give a stiffness rule to compare with once
  the paper is read.
- There is no rolling dashpot, and numerical damping is 0
  ([04](04_numerical_damping.md)). The elastic rolling stage can therefore
  oscillate without dissipation below the plastic limit. A settling test
  checks that a heap and a settled charge come to rest
  ([13](13_initial_conditions.md)).

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

- Obtain Wensrich & Katterfeld 2012 and Ai et al. 2011 (checklist in [README](README.md), "Pending Zotero additions"); compare the
  krot criterion with Ai's rule; quote Wensrich only after reading it.
- Search further for a measured repose angle of coarse SAG-feed or ROM ore
  (peer-reviewed or official CEMA 550 table).
- Heap test design: rock-only spheres with the simulated rock size, rough
  base (fixed rock spheres), lifted-cylinder or poured cone, pile >= ~20
  particle diameters across, damping 0, same dt; slope from a fit of the
  surface particles.
- Check the end-wall rolling moment: compare the charge shape with eta on and
  off at the end walls (e.g. one run with frictionless end walls replaced by
  periodic boundaries if available, or by measuring the end-wall moments).

## Pending code changes

| ID | Change | Current code | When |
|---|---|---|---|
| C06-1 | 6-DOF geometry functors and `Law2_ScGeom_MindlinPhys_Mindlin(includeMoment=True)`; `Ip2_FrictMat_FrictMat_MindlinPhys(eta=mu_r, krot=..., ktwist=0)` from config (this is C01-2 with values) | `ScGeom`, no moment law (`engines.py:64, 76-77`) | Before calibration |
| C06-2 | `krot` helper: from the smallest rock sphere, dt and a typical contact force, return krot meeting the T_r >= 20 dt and theta_y ~ 0.01 rad criteria; assert at build | None | With C06-1 |
| C06-3 | Heap (angle-of-repose) script: rock-only pile, slope fit, returns the angle for given (mu_p, mu_r) | None | Before calibration |
| C06-4 | Settling test with rolling resistance and damping 0: heap and charge reach rest (mean speed below the [13](13_initial_conditions.md) threshold) | None | With C06-1 and C04-5 |

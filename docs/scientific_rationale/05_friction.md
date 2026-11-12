# 05 -- Friction coefficient

## Decision

Friction is the **primary calibration variable**.

- **Particle-particle friction: one uniform mu_p for all three pairs**
  (steel-steel, steel-rock, rock-rock), as in Cleary & Morrison 2016
  (decided 2026-10-20). Baseline mu_p = 0.5; **calibrated mu_p = 0.3**
  (2026-11-08, "Outcome" below). The Owen & Cleary set
  0.4 / 0.5 / 0.8 is run **once as a sensitivity case**, not calibrated.
- Only two friction parameters are calibrated, because there are only two
  targets (plant toe / shoulder, [15](15_calibration_targets.md)): mu_p and a
  particle-liner friction mu_w. Rolling resistance is not a third calibrated
  knob ([06](06_rolling_resistance.md)).
- **Separate liner material** (decided 2026-10-20): shell and lifters get
  their own material "liner" (steel stiffness, density and Poisson ratio;
  its own friction), so mu_w is independent of steel-steel friction. Govender
  et al. 2015 (Table 8) treat lifter friction separately (0.70 vs 0.40 for
  particles) and use it to match the shoulder (§1.6.1).
- Implementation: friction angles in **radians** (mu = tan(angle)), assigned
  per pair with a `frictAngle` `MatchMaker`. Without it YADE takes the
  **minimum** of the two materials' angles, so mu_w could never exceed mu_p:
  the MatchMaker is **required** for the calibration, not only for the Owen
  run.
- **Calibration grid** (decided 2026-10-20): mu_p x mu_w in
  {0.3, 0.5, 0.7} x {0.3, 0.5, 0.7} (9 runs), then refined around the best
  point; mu_w extended to 0.8-0.9 if the shoulder / toe are not reached
  (the SAG_A toe is high for its fill, [15](15_calibration_targets.md)).
  All runs start from **one shared settled initial condition** and spin up
  to a steady charge shape (~6 revolutions = 38 s at 9.5 rpm, ~1.6 h per run
  at full scale with SAG_A's 0.6 m slice, [10](10_mill_geometry.md), ~15 h for
  the grid; rough, to be replaced by the pilot's timings). Score: simulated bulk toe / shoulder (position-density
  contour) vs. SAG_A.
- **Outcome (2026-11-08):** the grid ran (16 h, 2 points at a time); the
  toe stayed at 240-242 deg and the shoulder at 36-41 deg against 214 / 27
  deg. mu_w has practically no effect (the lifters carry the charge), so the
  two-parameter design does not identify two parameters; mu_p moves the
  angles weakly inside its literature range. **Calibrated (option 1, a
  constrained calibration): mu_p = 0.3, mu_w = 0.5**, with mu_r re-fitted to
  0.16 ([06](06_rolling_resistance.md)); the residual and why it is
  attributed to the reference angles are in [15](15_calibration_targets.md)
  ("Calibration outcome"). No refinement grid: inside the admissible range
  there is nothing left to refine.

## Evidence

| Source | What it says | Where | Verified |
|---|---|---|---|
| Cleary & Morrison 2016 | Friction 0.5 for rock-rock, rock-steel and steel-steel (super-quadric particles) | Table 2, PDF p7 / j.81; shape model §3.2, PDF p3 / j.77 | Yes |
| Owen & Cleary 2015 | Friction steel-steel 0.4, steel-rock 0.5, rock-rock 0.8: "smallest at 0.4 for the ball-ball collisions and highest for the rock-rock ones since the rocks are typically quite rough" | Table 4 and §3 text, PDF p3 / j.21 | Yes |
| Owen & Cleary 2015 | "DEM simulation of mill behaviour has been shown to be only weakly sensitive to the specific choices of these material parameters (Cleary, 2001a)" | §3, PDF p3 / j.21 | Yes |
| Boemer & Ponthot 2017 | "the coefficient of friction has a strong influence since it controls the sliding propensity of the charge" | Abstract, PDF p1 / j.53 | Yes |
| Boemer & Ponthot 2017 | Power draw 1311, 1382, 1391 W for mu = 0.25, 0.5, 0.75; default mu = 0.75 | §3.1.4 "Influence of the friction", PDF p10 / j.62; Table 2, PDF p7 / j.59 | Yes |
| Kishida 2025 | Friction coefficient 0.575 | Fig. 2(b), PDF p4 | Yes |
| Govender 2015 | Slice mill: mu particle 0.15 / shell 0.20 (GPU), 0.14 / 0.39 (CPU); Los Bronces SAG: mu particle 0.40, lifter 0.70; friction tuned to reproduce a reference shoulder position | Table 6, PDF p12 / j.163; Table 8, PDF p14 / j.165; §1.6.1, PDF p7 / j.158 | Yes |
| Cleary 2001 (2D) | "Changes in the material properties such as the friction coefficient and the coefficient of restitution have previously been shown to be relatively unimportant (Cleary, 1998a)" | §9, PDF p22 / j.100 | Yes |

The sources disagree on sensitivity: Cleary (2D, and Owen quoting it) finds
friction weakly important; Boemer & Ponthot (3D, experimentally validated
lab mill, run in YADE) and Govender (used friction as the tuning knob for the
shoulder) find it decisive. Since this project calibrates against plant charge
shape, friction is treated as the main calibration variable.

## PPT

| Slide | Content |
|---|---|
| 8, 9, 12 | "Angulo de Friccion = atan(coef. fric.) = atan(0.5) [1]" for steel and rock ([1] = Cleary & Morrison 2016, Table 2) |
| 8 | Claimed influence order "friccion, restitucion y rigidez" citing Cleary (2015), Boemer & Ponthot, Thakur. Only Boemer supports it (see the citation table in [README](README.md)) |
| 30 | "Busqueda manual para Angulos de Friccion y Densidades (respecto a Acomodo de Carga) <- AQUI ACTUALMENTE"; "Desarrollando GridSearch" |
| 31 | Simulation snapshot annotated 212 deg / 26.5 deg (toe / shoulder) |

## Current state

| Where | What |
|---|---|
| `config.py` | `PARTICLE_FRICTION = 0.3` (mu_p, C05-1, commit `5c194ab`; the calibrated value since 2026-11-08, was 0.5), `WALL_FRICTION = 0.5` (mu_w), `OWEN_PARTICLE_FRICTION` (0.4 / 0.5 / 0.8); `MATERIALS` has a `"liner"` entry (steel density, modulus and Poisson ratio) and no per-material friction (C05-3, commit `4bb17e4`) |
| `simulation/scenario.py` (`ContactOptions`, `contact_tables()`, `friction_for()`) | `contact.particle_friction` (mu_p), `contact.wall_friction` (mu_w) and `contact.particle_friction_set` (`"uniform"` or `"owen"`) give one friction value per material pair: particle pairs mu_p (or Owen), particle-liner mu_w, particle-end-wall 0. `mill.liner_material = "liner"` by default, and a liner that is also a particle material, or a material with its own `friction_angle`, is rejected (C05-2, C05-3, commit `4bb17e4`) |
| `simulation/yade_dem/engines.py:66-72`, `materials.py` (`pair_matchmaker`) | The pair table becomes a `frictAngle` `MatchMaker` (angles in radians, atan(mu)) keyed by the YADE ids of the material labels: no min rule. Each material's own `frictionAngle` is set to the same value (YADE's fallback for pairs not in the table, of which there are none). The table is written to the run manifest (`contact_tables`). Checked in the smoke run: every contact carries the friction of its pair |
| `simulation/scenario.py` (`RunOptions.ic_dir`, `CALIBRATE_FROM_IC_STAGES`, `material_set_id(ignore_friction)`), `run_simulation.py` (`_stage_load_ic`) | A `calibrate` run with `run.ic_dir` loads that IC instead of pouring its own (load_ic, spinup, record), so every grid point starts from **one shared settled IC**, checked to match in everything but friction (the material-set id without the friction table and friction angles); the IC's friction is recorded in the manifest, and the contacts are rebuilt with the point's friction (commits `8e1d4aa`, `ad8027f`) |
| `configs/simulation/calibration/`, `scripts/calibration/` | The 3 x 3 grid (`cal_mup<mu_p>_muw<mu_w>.json`) from the pilot's RMIC IC (`sag_a_make_ic_rmic_s0`, settled with mu_p = mu_w = 0.5), recording **2 revolutions** (12.63 s) after the spin-up's steady state, enough for the time-averaged toe / shoulder; `make_grid_scenarios.py` regenerates or refines it, `run_grid.sh` runs `PARALLEL` points with `THREADS` threads each (default 2 x 10 on the 12-core / 24-thread machine), `grid_summary.py` ranks the points by the distance of the bulk toe / shoulder from the SAG_A targets (commit `8e1d4aa`) |

Consequence: any run made with the old code (before commit `543208a`) -- including, if it used that code,
the 212 deg / 26.5 deg match of slide 31 -- had practically frictionless
particles and liner. The lifters (30 rows in the old 40 ft STL) can still lift such a charge,
which is why a plausible toe / shoulder may have been reached, but those
parameters are not valid once friction is correct. The manual friction and
density search of slide 30 must be repeated after the fix.

## Analysis

- Densities are not a calibration variable ([08](08_density.md)); friction
  (and rolling resistance, [06](06_rolling_resistance.md)) is what the
  literature tunes to match the shoulder.
- With spheres, friction alone cannot provide the interlocking of angular
  ore. Cleary & Morrison's mu = 0.5 was used with super-quadric shapes; with
  spheres the same mu gives a weaker charge, which rolling resistance
  compensates.
- **Why exactly two calibrated parameters, and why mu_p and mu_w.** There
  are two targets (bulk toe, shoulder), so at most two parameters can be
  identified; with more, many combinations fit equally well and the
  calibrated values are not unique. The two must act through different
  mechanisms:
  - mu_p (particle-particle) sets the shear strength of the bulk charge:
    cascading and the toe.
  - mu_w (particle-liner) sets how firmly lifters and shell hold the charge
    before release: the shoulder (Govender et al. 2015, §1.6.1, tune lifter
    friction separately for this).
  - Rock rolling resistance also acts on bulk shear strength, almost the
    same mechanism as mu_p; calibrating both would be ill-conditioned, so it
    is fixed separately ([06](06_rolling_resistance.md)) and checked as a
    sensitivity.
- Owen's pair-wise set needs a `frictAngle` MatchMaker in YADE; with
  per-material angles and the min rule, steel-rock would get 0.4, not 0.5.
- **Why uniform mu_p rather than Owen's ratios.** Owen's ordering
  (steel-steel < steel-rock < rock-rock) is the more physically plausible
  one: rock is rough, worn balls are smooth. Uniform mu_p is chosen anyway
  because:
  1. The targets cannot identify the ratio. Toe and shoulder are bulk
     responses; 1 : 1 : 1 and 0.4 : 0.5 : 0.8 (rescaled) fit them equally
     well, so the ratio is an assumption either way. Uniform adds no
     species contrast the data does not support.
  2. Neither set is measured. Owen's values are a modelling choice ("rocks
     are typically quite rough"), and the same group used 0.5 for every pair
     a year later (Cleary & Morrison 2016, Table 2).
  3. Rock roughness is already represented. With spheres, the angularity
     that makes rock-rock contacts strong is modelled by rock rolling
     resistance ([06](06_rolling_resistance.md)); a higher rock-rock mu on
     top would count it twice.
  4. Segregation is the surrogate's output. A friction contrast between
     species acts directly on steel / rock segregation; with uniform mu_p,
     segregation comes only from size and density, which are known.
  5. It needs no MatchMaker for particle pairs (all three equal).
- Cost of the choice: if rock roughness does drive segregation in the real
  mill, uniform mu_p understates it. The Owen sensitivity run checks this.

## Verdict and how to defend it

"Friction is calibrated because it controls the sliding of the charge and the
power draw (Boemer & Ponthot 2017, abstract and §3.1.4) and is the parameter
used to match the shoulder position (Govender et al. 2015, §1.6.1). The
search is bracketed by literature values: mu = 0.5 for all pairs (Cleary &
Morrison 2016, Table 2), 0.4 / 0.5 / 0.8 for steel-steel / steel-rock /
rock-rock (Owen & Cleary 2015, Table 4), 0.575 (Kishida et al. 2025) and
0.40 particle / 0.70 lifter for a SAG mill (Govender et al. 2015, Table 8).
Two parameters are calibrated, one per target mechanism: a uniform
particle-particle friction and a separate particle-liner friction, on a
3 x 3 grid from a shared settled initial condition; the remaining contact
parameters are fixed from the literature and tested one at a time."

On the pair structure: "Owen & Cleary's ordering (steel-steel 0.4,
steel-rock 0.5, rock-rock 0.8; Owen & Cleary 2015, Table 4) is physically
plausible, but the toe / shoulder targets cannot identify the ratios, rock
angularity is represented by rolling resistance, and segregation is the
output of interest. A uniform particle friction is therefore used, as in
Cleary & Morrison 2016 (Table 2), with Owen's set as a sensitivity case."

## Open items / validation

- **Owen sensitivity run** (decided 2026-10-20): after calibration, one run
  with steel-steel / steel-rock / rock-rock = 0.4 / 0.5 / 0.8 scaled so that
  the charge shape stays matched (or plain 0.4 / 0.5 / 0.8 with the
  calibrated mu_w), compared with the uniform case on toe / shoulder and on
  steel / rock segregation. Small change -> uniform mu_p justified; large
  change -> report as a limitation or revisit.
- Restitution for the liner pairs: steel values (liners are steel), decided
  in [07](07_restitution.md).
- Re-measure the packing fraction after calibration ([12](12_charge_fill_and_particles.md)):
  packing depends on friction.
- ~~**Run the grid** (`scripts/calibration/run_grid.sh`).~~ Done 2026-11-06/07
  (16 h at 2 x 10 threads, ~25 % faster than one point at a time); result
  in the Decision and in [15](15_calibration_targets.md).
- The grid's cost estimate held: a point took ~3.4 h at 10 threads with two
  side by side (one alone at 16 threads ~2.3 h). No refinement grid was run
  (Decision, "Outcome").
- The shared IC was settled with mu_p = mu_w = 0.5; with another friction a
  freshly poured bed would pack slightly differently. Sharing it is the
  decision (differences between points come from the friction during
  turning only); the spin-up to steady state removes the bed's memory of
  how it was poured.

## Pending code changes

| ID | Change | Current code | When |
|---|---|---|---|
| C05-1 | Uniform mu_p: steel and rock get the same `friction_angle` (radians, mu = tan(angle)) from one config value | Done (`5c194ab`): `config.PARTICLE_FRICTION` | Before calibration |
| C05-2 | `frictAngle` `MatchMaker` with per-pair friction: particle-liner pairs = mu_w (needed whenever mu_w > mu_p); particle pairs = mu_p, or the Owen set in the sensitivity run | Done (`4bb17e4`) | Before calibration |
| C05-3 | Add a `"liner"` entry to `MATERIALS` (steel density / young / poisson, friction mu_w) and set `mill.liner_material = "liner"`; add liner-steel / liner-rock restitution pairs; the frictionless `end_wall` material keeps deriving from it | Done (`4bb17e4`) | Before calibration |

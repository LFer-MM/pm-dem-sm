# 13 -- Initial conditions (SIC and RMIC)

## Decision

Two initial-condition (IC) types, generated with the same charge, materials
and geometry as the dataset runs:

| IC | Construction | Status |
|---|---|---|
| **RMIC** (randomly mixed) | Chord-box batches in which each sphere is randomly assigned rock or ball in the global proportion; masses and inertias recomputed after resizing | Fixed |
| **SIC** (segregated) | **Rock poured first (bottom layer), balls poured on top** -- the orientation of `ingress_segregated` and of the existing dataset | Fixed (decided 2026-10-18; deliberate deviation from Kishida's Fig. 6b, see analysis) |

Common protocol for both (revised 2026-10-19):

1. Check **zero overlaps** (sphere-sphere and sphere-facet) before the first
   step of every fill batch; abort otherwise (V13).
2. Pour in chord-box batches kept inside the inner radius minus lifter
   height minus one particle radius, each batch just above the current bed
   surface; mill not rotating; **damping = 0** ([04](04_numerical_damping.md));
   dt and moduli as for the dataset runs ([02](02_time_step.md),
   [03](03_stiffness_young_modulus.md)).
3. Settle by contact dissipation only until the **bed geometry is
   stationary**: over the last 1 s of simulated time, the charge
   centre-of-mass angle changes by < 0.5 deg and its height by < 1 % of the
   small-particle diameter, and the mean particle speed is < 1 cm/s. Cap at
   a maximum settling time and record which condition ended the stage.
   (Thresholds provisional: to be confirmed on the first full-scale IC.)
4. **Zero all velocities** ("all particles stationary", as in Kishida).
5. Save positions (CSV) **and** the YADE scene (`.yade.gz`), with the seed,
   counts, phi, material set, settling time and stop condition in a
   manifest.
6. **5 replicates per IC type** (decided 2026-11-02, [14](14_dataset_runs_and_recording.md); the PPT planned 30), differing only in the seed, which sets both the random placement (`makeCloud(seed=...)`) and the species assignment (`particles.py`).

**Particle counts** come from the simulated grind-out / crash-stop
procedure of [12](12_charge_fill_and_particles.md) (charge run, stopped and
settled with this same damping-free settling), which matches the plant's
definition of Jb and Jc. The ICs use those counts; a poured IC bed is not
re-tuned to J, but its settled J is recorded in the manifest for
information.

Why not the PPT's criteria: without artificial damping a settled bed keeps
a small residual motion (smoke test, 18 s of settling: mean speed 4-6 mm/s,
mostly particle spin; YADE's unbalanced-force ratio stays at 0.3-0.4) while
its geometry is fixed (charge centre-of-mass angle constant to 0.2-0.3 deg).
"Unbalanced force < 1e-3" (slides 17-18) and "mean speed < 1 mm/s" are
therefore never reached; a geometric criterion is.

## Evidence

| Source | What it says | Where | Verified |
|---|---|---|---|
| Kishida 2025 | "All particles were stationary under the initial conditions. Two types of initial particle positions of binary-sized particles, which were (a) randomly mixed initial condition (RM-IC) and (b) segregated initial condition (S-IC) along the Z-direction" | §3, PDF p6 | Yes |
| Kishida 2025 | Fig. 6(b): in the S-IC the **large particles (red) fill the bottom and the small particles (cyan) form the top layer**; Z is the vertical axis (Fig. 2a / 6 side and front views) | Fig. 6, PDF p6; Fig. 2(a), PDF p4 | Yes (figure read) |
| Kishida 2025 | Table 2: case 1 RM -> RM, case 2 RM -> S, case 3 S -> RM, case 4 S -> S (surrogate-modelling IC -> prediction IC) | Table 2, PDF p6 | Yes |
| Kishida 2025 | Training data from RM-IC generalised to S-IC; data from S-IC did not generalise: "the RNNSR constructed based on the data initiated from S-IC could not predict the mixing and segregation initiated from RM-IC ... attributed to the uniformity of the spatial arrangement" (in RM-IC data "both large and small particles were uniformly distributed") | §4.2, PDF p10 | Yes |
| Kishida 2025 | Single particle density for both sizes (2500 kg/m^3) | Fig. 2(b), PDF p4 | Yes |
| Kishida 2025 | Equal-density drum: "large particles were observed more in the peripheral region of the powder bed, while small particles were observed more in the central core ... This is a typical segregation pattern in a rotating drum"; attributed to percolation | §4.1, PDF p7; §2.2.2, PDF p5 | Yes |
| Govender 2015 | Los Bronces SAG (ore 2850, balls 7800 kg/m^3): "We also see radial segregation with the smallest particles moving to the mill shell as predicted by theory and experiment" | §3, PDF p14 / j.165 | Yes |

## PPT

| Slide | Content |
|---|---|
| 17 | "Simulacion de Generacion de Condicion Inicial en Segregacion (SIC)": dt = 1e-4, gravity_damping = 0.5, unbalanced_forces < 0.001, 26 % del slice; script `new_ingress_rmic.py`; output `sic.csv` |
| 18 | RMIC: same settings; output `rmic.csv` |
| 30 | Datasets: SIC 400 frames x 30 simulations, RMIC 200 frames x 30 simulations |

## Current state

| Where | What |
|---|---|
| `particles.py:196` | `ingress_segregated` pours **small first, then large** -> rock at the bottom, balls on top (matches the decision) |
| `particles.py:119, 182, 261-273` | `ingress_random`; mass and inertia recomputed from radius and density after resizing (the old steel-ball-mass bug is fixed) |
| `monitor.run_until_settled`, `run_simulation._stage_settle`, `state.settle_and_save` | Settle stage and the IC helper use the geometric stop rule above (`checks.settle_stop`: 1 s window, 0.5 deg, 1 % of d_small, 1 cm/s, time cap `settle.max_time_s` = 20 s) and record the stop reason; `settle_and_save` also zeroes all velocities before saving (C04-5, commit `494c1f3`) |
| Existing SIC dataset, frame 0 | ore_rock mean y = -4.42 m, ball_steel mean y = -2.10 m -> rock bottom, balls top (opposite of Kishida's S-IC) |

## Analysis

- **Why not copy Kishida's orientation.** Kishida's S-IC puts the large
  particles at the bottom (Fig. 6b). In a resting bed the bottom layer lies
  against the shell, i.e. on the *periphery* of the circulating charge -- and
  in Kishida's equal-density drum the large particles do migrate to the
  periphery (§4.1, PDF p7). In a SAG mill the large particles (balls) are also
  ~3x denser, and the observed segregation is the opposite: "the smallest
  particles moving to the mill shell" (Govender 2015, PDF p14), i.e. balls
  towards the core. The SAG analogue of Kishida's layering is therefore the
  species that migrates to the shell (rock) at the bottom and the balls on
  top. This is the orientation chosen.
- **Percolation at rest.** A 2:1 size ratio does **not** let rock fall
  through a resting ball bed by gravity alone. By plane geometry, the
  opening between three mutually touching spheres of diameter d passes a
  sphere of at most (2/sqrt(3) - 1) d = 0.155 d, and the opening between
  four touching spheres in a square passes at most (sqrt(2) - 1) d =
  0.414 d. A rock of 0.5 d is larger than both, so it cannot pass between
  touching balls; loose spots in a random bed are not continuous paths.
  So the "rock would go in between" argument applies to the **sheared**
  charge (kinetic sieving, the
  percolation mechanism Kishida cites, §2.2.2 PDF p5), in either orientation,
  not to the IC itself. With rock at the bottom the IC is static and well
  defined.
- **Consequence of balls on top.** Dense balls above light rock is
  gravitationally unstable once the charge is sheared: from t = 0 both density
  (balls sink) and size (balls rise) act, so the SIC exercises both
  mechanisms -- relevant for the SAG case, and a documented difference from
  Kishida's single-density system.
- **RMIC bug impact.** With the mass bug, every small rock created by
  resizing had the mass of a 0.1397 m steel ball (~24x too heavy). Any RMIC
  generated by the old `ingress_random` (before commit `543208a`) is
  invalid.
- **No damping during IC generation.** It would be harmless for the dynamics
  (velocities are zeroed afterwards) but it changes how the charge packs,
  and therefore phi; with a stable dt it is unnecessary (0 escapes without
  damping in the smoke test). See [04](04_numerical_damping.md).
- **Training IC.** Kishida's main finding for this design is that the
  surrogate must be trained on RM-IC data (uniform spatial coverage) to
  predict both ICs; SIC runs are mainly prediction / test cases.

- **J of a starting packing is below Jc, by design.** The ICs are poured and
  settled without turning, so they pack like a random 2:1 bed (pilot RMIC:
  J = 0.2588, phi = 0.5845) rather than like the plant's crash-stopped
  charge (J = 0.276). The plant's Jc is matched through the particle counts
  (grind-out, [12](12_charge_fill_and_particles.md)); the pilot's crash-stop
  check shows the same packing gives J = 0.2770 once it has turned 3.2
  revolutions and is stopped. Turning the charge before saving an IC would
  reach Jc at rest but destroy the defined mixing state (random or
  segregated) that the IC exists to provide.

## Verdict and how to defend it

"Both initial conditions are static packings (Kishida et al. 2025, §3): the
charge is poured with the mill at rest, settled by contact dissipation
alone (no artificial damping) until its geometry is stationary, and all
velocities are set to zero. The randomly mixed IC assigns
species at random in the global proportion. In the segregated IC the rock
forms the bottom layer and the balls the top layer. This differs from the
layering of Kishida et al. (large particles at the bottom, Fig. 6b) on
purpose: there, with equal densities, the large particles migrate to the
periphery (§4.1); in a SAG mill the denser balls migrate to the core and the
ore to the shell (Govender et al. 2015, §3), so placing the ore at the
bottom (against the shell) is the equivalent configuration. Five replicates
per IC differ only in the random seed."

## Open items

- Confirm the geometric stop-rule thresholds (0.5 deg, 1 % of d_small,
  1 cm/s, 1 s window) and the maximum settling time on the first full-scale
  IC; record the time it takes.
- Residual motion floor (open, not yet explained): with damping 0 the
  settled smoke-test bed keeps ~4-6 mm/s mean speed, ~85-90 % of its kinetic
  energy rotational, with frictionless **and** frictional end walls. Not an
  instability (no escapes, geometry fixed). Candidate causes to test:
  contacts switching between facets at shell / lifter edges; absence of
  rolling / twisting resistance (a first test that switched rolling
  resistance on in an already-settled bed was inconclusive because it had to
  reset all contacts). Rolling resistance is now part of the model
  ([06](06_rolling_resistance.md)), but YADE's rolling spring has no
  dashpot, and Ai et al. (2011, §6, Fig. 8) show that an undamped rolling
  spring keeps a particle oscillating at rest; Wensrich & Katterfeld
  (2012, §2) rely instead on a stiff rolling spring with shear damping.
  The settling test C06-4 checks whether the floor disappears with the
  stiff krot of [06](06_rolling_resistance.md).
  **Smoke test, 2026-11-04 (current code, geometric stop rule):** the 4-6
  mm/s floor is not seen. The settled bed stops by the rule after 1.15 s
  with mean speed 0.007 mm/s at mu_r = 0.25. With the rolling moment
  switched off it stops after 1.2 s at 0.5 mm/s: rolling resistance cuts
  the residual motion ~70-fold, but even without it the bed is well under
  the old floor. That floor may have come from the old shell / lifter
  facets (the liner is now generated, [10](10_mill_geometry.md)). To be
  confirmed at full scale. Note for such tests: in YADE, eta = 0 does
  **not** switch rolling resistance off. The plastic cap is applied only
  if eta R |F_n| > 0, so eta = 0 leaves the rolling spring uncapped,
  i.e. unlimited rolling resistance. The code therefore switches the moment
  law off when mu_r = 0 ([06](06_rolling_resistance.md)).
- ~~Store ICs under versioned names including the material-set id, so an IC is
  never reused with different materials.~~ Done (C14-1, commit `69e6ea0`): `make_ic`
  names the IC `<scenario>_<RMIC|SIC>_seed<N>_<material-set id>` and a `dataset` run
  refuses an IC whose id differs from its own (smoke chain tested 2026-11-05).
- Confirm in a calibrated run that balls do migrate towards the core (as in
  Govender) for this charge; if not, revisit the SIC orientation argument.

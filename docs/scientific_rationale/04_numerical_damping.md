# 04 -- Numerical ("gravity") damping

## Decision

**`NewtonIntegrator.damping = 0` everywhere, at all times** (decided
2026-10-19): filling, settling and packing measurements as well as
calibration and SIC / RMIC dataset runs. Initial conditions are settled by
the physical dissipation of the contact law alone, with a mean-speed stop
rule ([13](13_initial_conditions.md)); particle velocities are zeroed before
an IC is saved.

The value is **always set explicitly** in the code, never left to YADE's
default: the default differs between YADE versions (0.0 in the 3rd-edition
documentation, 0.2 in the `yadedaily` build installed here).

Damping was previously needed only because the integration was unstable
(see "Why damping appeared necessary" below); with the stable dt of
[02](02_time_step.md) it is not.

Energy is dissipated only by the contact law: normal / tangential dashpots set
from restitution ([07](07_restitution.md)), friction ([05](05_friction.md))
and rolling resistance ([06](06_rolling_resistance.md)).

## What YADE's numerical damping does

YADE docs 2021, §2.1 "DEM formulation", "Numerical damping", printed
pp. 70-71 (PDF pp. 77-78), Eq. (2.9): for each particle and each axis
w in {x, y, z}, the force is modified by

(Delta F)_w = -lambda_d sgn(F_w u_dot_w) F_w,

i.e. a force that would **increase** the particle's speed is reduced by the
fraction lambda_d, and a force that would **decrease** it is increased by
lambda_d. With `dampGravity = true` (the default, PDF p277) this applies to
gravity too. Consequences for a particle in free flight with lambda_d = 0.2:

| Phase | Physical acceleration | With damping 0.2 |
|---|---|---|
| Falling (cataracting stream, towards the toe) | g | **0.8 g** |
| Rising (thrown from the shoulder) | g | **1.2 g** |

A particle falling from the shoulder therefore reaches the toe with ~20 %
less kinetic energy than physics dictates, and its trajectory is distorted
-- a direct bias on the toe angle, the impact energies and the mixing that
the datasets are meant to capture.

## Why damping appeared necessary

**Observation (PPT setup):** without damping, particles poured into the mill
collided "explosively" and were shot out of the mill; damping 0.2-0.5 stopped
it.

**Test (2026-10-19, this machine).** The 2 m smoke-test mill
(`configs/simulation/smoke_test.json`, 300 rocks + 60 balls, 8 lifters) was
filled and settled with the branch code and **damping = 0 throughout**, at
five time steps expressed as a fraction of the Rayleigh step
dt_R = 6.13e-4 s of its material set. Escaped = particle centre outside the
shell radius or the slice depth after fill + settle:

| dt / dt_R | dt (s) | Escaped | Max speed | Mean speed at end |
|---|---|---|---|---|
| 0.3 | 1.84e-4 | **0 / 360** | 0.08 m/s | 0.004 m/s (settled) |
| 0.6 | 3.68e-4 | **0 / 360** | 0.21 m/s | 0.033 m/s (settles, but jittery: near the limit) |
| 1.0 | 6.13e-4 | **360 / 360** | 4,187 m/s | 1,687 m/s |
| 1.5 | 9.20e-4 | **360 / 360** | 11,156 m/s | 2,579 m/s |
| 3.0 | 1.84e-3 | **360 / 360** | 10,610 m/s | 5,030 m/s |

Above the stability limit the explicit integration **creates** energy at
every contact (particles leave a collision faster than they entered), and the
charge explodes. Damping "fixed" this only by draining the spurious energy as
fast as it was created -- it masked an unstable time step.

**Where the earlier setups sat** (dimensionless dt / dt_R is what transfers
between the smoke test and the full mill):

| Setup | dt / dt_R | Regime |
|---|---|---|
| `config.py` moduli (155.7 / 13.47 GPa) at dt = 1e-4 s | ~1.2 | explodes |
| PPT slide-12 moduli (33.16 / 2.868 GPa) at dt = 1e-4 s | ~0.55 | at the jittery edge |
| **Decided set (f = 26) at dt = 2.5e-5 s** | **0.11** (0.12 with rock at 2650) | stable with a wide margin |

**Contributing causes in the old code, fixed in commit `543208a`:**

- Fill boxes sized from the shell circle ignored the 30 lifters (old 40 ft STL), and boxes
  straddling the mill axis had corners outside the shell: spheres could be
  created overlapping a facet and be ejected through it (facets are thin,
  so a sphere whose centre crosses the facet plane is pushed to the other
  side). The code now keeps fill boxes inside the inner radius minus lifter
  height minus a particle radius, and bounds the box width by the farther
  chord.
- Resized rocks kept the mass of a steel ball (~24x too heavy), making their
  impacts far more energetic. Fixed (mass and inertia recomputed).

## Evidence

| Source | What it says | Where | Verified |
|---|---|---|---|
| YADE docs 2021 | "In simulations of **quasi-static** phenomena, it is desirable to dissipate kinetic energy of particles. Since most constitutive laws ... do not include velocity-based damping ..., it is possible to use artificial numerical damping." | §2.1, "Numerical damping", printed p. 70 (PDF p77) | Yes |
| YADE docs 2021 | "This is done by component, which makes the damping scheme **clearly non-physical**, as it is not invariant with respect to coordinate system rotation" | Same section, printed p. 71 (PDF p78), before Eq. (2.9) | Yes |
| YADE docs 2021 | `NewtonIntegrator.dampGravity(=true)`: "By default, numerical damping applies to ALL forces, even gravity"; `damping(=0.0)`: "damping coefficient for Cundall's non viscous damping" | `yade.wrapper.NewtonIntegrator` entry, printed p. 270 (PDF p277) | Yes |
| YADE (installed `yadedaily` 20260115) | `NewtonIntegrator.damping` docstring: "damping coefficient for Cundall's non viscous damping", default **0.2** | Attribute docstring of the installed class | Yes (run on this machine) |
| YADE (installed build) | `FrictPhys` (Cundall-Strack law) has only `kn`, `ks`, `tangensOfFrictionAngle`: no velocity-based (dashpot) damping, which is the case the YADE docs have in mind | Attribute list of the installed class | Yes |
| Cleary & Morrison 2016 | Power draw = torque x rotation speed; "For long duration mill simulations that have reached steady state operation, the energy dissipated and the energy supplied by the mill should be equal. In practice, balances within a few percent indicate an accurate DEM simulation." -- a non-physical energy sink makes this balance impossible to close | §2, PDF p3 / j.77 | Yes |
| Boemer & Ponthot 2017 | dt chosen "in order to limit the percentage of artificial numerical power with respect to the total power to 1 %" -- non-physical energy is treated as an error to be kept below 1 % | §3.1, PDF p7 / j.59 (criterion in §2.2.3, PDF p5) | Yes |
| Kishida 2025 | Equations of motion m dv/dt = F_cn + F_ct + m g and I dw/dt = M + M_rf: no global damping term; dissipation only through the contact dashpots and rolling friction | Appendix A, Eqs. (A-1)-(A-6), PDF p11-12 | Yes |
| Govender 2015 | Dissipation controlled through restitution: power could be matched "exactly by changing the coefficient of restitution" | §3, PDF p14 / j.165 | Yes |
| All mill papers (Kishida, Cleary & Morrison, Owen & Cleary, Boemer & Ponthot, Cleary 2001, Govender 2015) and Thakur 2016 | None mentions global, local, non-viscous, numerical or artificial damping (full-text search) | -- | Yes (negative result) |

## PPT

| Slide | Content |
|---|---|
| 10, 13 | "Gravity Damping Ingreso 0.2 -> Asentado 0.0" (overlap and packing tests) |
| 17, 18 | SIC / RMIC generation: `gravity_damping = 0.5`, `unbalanced_forces < 0.001`, dt = 1e-4 |
| 19 | Dataset runs: **`gravity_damping = 0.2`**, 20 s (SIC) / 10 s (RMIC) |

## Current state

| Where | What |
|---|---|
| `engines.py:80` | `NewtonIntegrator` created with `damping=0` |
| `scenario.py` (`FillOptions`, `SettleOptions`) | No damping fields any more: a scenario JSON with `fill.damping` or `settle.damping` is rejected (C04-1, commit `5c194ab`) |
| `run_simulation.py` (`run`, `_stage_checks`) | `NUMERICAL_DAMPING = 0.0` set explicitly at build and at the start of every stage, then **asserted** by `engines.assert_no_damping()` (V5, C04-2, commit `494c1f3`); each stage's `checks` in the manifest records the value. After every stage the V14 escape count (`diagnostics.count_escapes`: centre outside the shell radius or the slice depth) is recorded, and the run stops if it is not 0. Before the first step of every fill batch, `diagnostics.check_new_batch` checks the new spheres against each other, every other sphere, the liner triangles and the end walls (V13); the run stops on any overlap, and the counts go to the fill stage's `v13_initial_overlaps` (C04-4, commit `494c1f3`). The smoke test (`configs/simulation/smoke_test.json`) passes all of them: 11 batches, 360 spheres, 0 overlaps, 0 escapes |
| `monitor.py` (`run_until_settled`), `run_simulation._stage_settle`, `state.settle_and_save` | Settle stop = the geometric rule of [13](13_initial_conditions.md) (pure logic in `checks.settle_stop`, unit-tested); `run_until_forces_balanced` and the unbalanced-force fields are gone. The manifest records the stop reason (`stationary` or `time_cap`), the window's angle / height changes and the mean speed (C04-5, commit `494c1f3`). `state.settle_and_save` (IC helper) uses the same rule and zeroes all velocities before saving |
| `engines.initialize_engines`, `monitor.py`, `checks.energy_balance` | Energy tracking on (`O.trackEnergy`, Mindlin `calcEnergy`). The mill log carries the potential (`gravWork`), elastic and cumulative dissipated energy (dashpots + friction), plus a sampled estimate of the rolling-moment plastic dissipation, which YADE does not track: \|M\| x \|relative angular velocity normal to the contact\| over the contacts at the cap, integrated between log rows. Each stage records the V4 balance (C04-3, commit `494c1f3`; results in Analysis) |
| Existing `sic_dataset_20s_dt0p0001` | Generated with 0.2 according to slide 19 (old code) |

## Analysis

- **Purpose of the tool.** YADE's own documentation introduces numerical
  damping for quasi-static simulations with contact laws that lack
  velocity-based damping, and calls the scheme "clearly non-physical". A
  rotating mill is a dynamic, cataracting flow, and the Hertz-Mindlin law
  used here ([01](01_contact_model.md)) has velocity-based damping
  (restitution dashpots). Neither condition for using it holds in the
  rotating runs.
- **Effect on the physics.** With 0.2 the cataracting stream falls at 0.8 g
  and is thrown up at 1.2 g (table above); impacts at the toe lose ~20 % of
  their energy on top of the restitution losses. The charge throws less far,
  the toe moves, and the Cleary & Morrison energy balance (supplied =
  dissipated in contacts) cannot close because part of the energy disappears
  outside the contacts.
- **Effect on calibration.** Any friction / restitution values tuned with
  0.2 compensate for this artefact and are not transferable to undamped
  runs.
- **Why not even during IC settling.** Pouring and settling an IC is a
  quasi-static process -- YADE's intended use -- and its velocities are
  zeroed afterwards, so damping there would leave no trace in the dynamics.
  It is still not used, for two reasons: (1) with a stable dt the contact
  law alone settles the charge (test above: 0 escapes, mean speed 4 mm/s);
  (2) damping changes how the charge packs while it settles, and the
  packing fraction phi measured in that state sets the particle counts
  ([12](12_charge_fill_and_particles.md)). A single damping-free protocol
  for packing measurement, IC generation and dataset runs keeps all three
  consistent.
- **Historical reason.** With YADE's Cundall-Strack law (no dashpot), the
  integrator damping is the only way to dissipate normal-impact energy, which
  explains its use in earlier versions of the setup. With Hertz-Mindlin and
  pair-wise `en` it is not needed.

## Verdict and how to defend it

"No artificial (non-viscous) damping is used at any stage. YADE provides it
for quasi-static problems with contact laws lacking velocity-based damping
and describes it as 'clearly non-physical' (YADE documentation, 3rd ed.,
§2.1 'Numerical damping'); applied to gravity, a coefficient of 0.2 would
make particles fall at 0.8 g and rise at 1.2 g. Energy is dissipated
exclusively through the contact model (restitution, friction, rolling
resistance), as in all the mill DEM studies consulted, where the energy
dissipated in collisions must balance the energy supplied by the mill within
a few percent (Cleary & Morrison 2016, §2) and artificial numerical power is
kept below 1 % (Boemer & Ponthot 2017, §3.1). Damping had earlier appeared
necessary to stop particles being ejected during filling; a test at five
time steps showed this was an integration instability (all particles
ejected at dt >= dt_R, none at dt <= 0.6 dt_R, without damping), which the
chosen dt = 0.11 dt_R avoids. Initial conditions are therefore poured and
settled by contact dissipation alone, with the same protocol used to measure
the packing fraction."

## Open items / validation

- Energy balance per run (V4), implemented (C04-3). The terms:
  - **Input:** drive work, the integral of power (torque x omega).
  - **Tracked by YADE:** contact dissipation (normal and shear dashpots,
    friction), with the energy tracker and the Mindlin law's `calcEnergy`.
  - **Not tracked by YADE:** the plastic dissipation of the rolling moment.
    On the smoke test (mu_r = 0.25) leaving it out leaves 29-31 % of the
    dissipation unaccounted in fill and settle. With the moment law
    switched off the balance closes to -3.2 % (fill) and -1.7 % (settle),
    so the tracked terms are sound. The monitor therefore adds a sampled
    estimate of the rolling term (Current state).

  Smoke-test residuals with the estimate:

  | Stage | Residual |
  |---|---|
  | fill | -1.7 % |
  | spin-up | -10.5 % |
  | record | +11.6 % |
  | spin-up + record pooled | -6 % |
  | settle | 23 % of only 24 J |

  These are sampled every 0.05 s in a 360-particle mill whose power
  fluctuates strongly. Judge V4 ("within a few %") over the steady part
  of a full-scale run (pilot); if it does not close there, the next step is
  to integrate the drive work every step instead of sampling it.
  Two YADE details: friction dissipation can be slightly negative in this
  build, and the residual-free probe of two spheres on a facet closed to
  1.8 %.
- ~~V5: assert `NewtonIntegrator.damping == 0` in every stage (C04-2).~~
  Done (commit `494c1f3`).
- V13 (new): zero sphere-sphere and sphere-facet overlaps before the first
  step of every fill batch; abort otherwise. Implemented (C04-4, commit
  `494c1f3`). Seen in the phase-1 smoke run
  (2026-11-04): `fill.settle_steps` is a step count, so with dt = 2.5e-5 s
  the old 1,500 steps gave only 0.04 s of fall time per batch. Batches
  stacked up to the top of the mill, the chord box there had zero width,
  `stl.chord_box_3d` clamped it at y = R, and spheres were placed outside
  the shell, and the charge blew up. On `main` the old dt made the same
  1,500 steps 0.28 s, so it never happened there. Fixed in the smoke JSON
  by keeping the old simulated time (11,000 steps); the general guard
  belongs to V13 / V14 (C04-4).
- Confirm on the first full-scale IC that the charge settles without escapes
  and within an acceptable time (the smoke test covers the physics; the
  dimensionless dt / dt_R is what transfers).
- Fallback only if full-scale settling proves too slow: temporarily lower the
  restitution during IC generation (contact-level, does not distort gravity,
  erased when velocities are zeroed). Not expected to be needed.
- Re-generate the datasets and re-measure phi: those made with 0.2 do not
  represent undamped mill dynamics.

## Pending code changes

| ID | Change | Current code | When |
|---|---|---|---|
| C04-1 | **Damping = 0 in every stage**, set explicitly (drop the `fill.damping` / `settle.damping` fields or default them to 0) Done (`5c194ab`): fields removed | Before any production run |
| C04-2 | V5 assertion at the start of every stage | Done (`494c1f3`) | With C04-1 |
| C04-3 | Energy tracking (`O.trackEnergy = True`, `Law2...calcEnergy = True`) and the V4 energy balance (mill work vs contact dissipation) | Done (`494c1f3`), with a sampled estimate of the untracked rolling dissipation; V4 still to be judged on a full-scale run | With the run-type split |
| C04-4 | V13 overlap check before each fill batch; V14 escape check after each stage | Done (`494c1f3`) | With C04-1 |
| C04-5 | Settle stop rule -> geometric criterion of [13](13_initial_conditions.md) (charge COM angle / height stationary over 1 s, mean speed < 1 cm/s, time cap) | Done (`494c1f3`) | With C01-2 (rolling resistance may change the residual motion) |

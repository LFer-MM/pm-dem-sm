# 02 -- Time step (dt)

## Decision

**dt = 2.5e-5 s** (option A, decided 2026-10-18) with the moduli of
[03](03_stiffness_young_modulus.md): both physical moduli reduced by the same
factor **f = 26** (decided 2026-10-19), i.e. **E_steel = 7.96 GPa,
E_rock = 2.115 GPa**.

dt and f are chosen together: with f = 26 **every contact type gets >= 20
integration steps at the worst-case impact speed** sqrt(2 g D) = 14.5 m/s
(SAG_A, D inside liners 10.71 m, [10](10_mill_geometry.md)) with
dt = 2.5e-5 s for **both** rock densities used (2850 kg/m^3 baseline:
20.9-36.6 steps; 2650 sensitivity case: 20.3-36.6 steps;
[08](08_density.md)). f = 26 was fixed (2026-10-19) as the smallest
reduction meeting this at the earlier 40 ft geometry; for SAG_A the
threshold is f >= 25.0 (2650 case), so 26 keeps a margin of ~1 step.
That satisfies both accuracy criteria of the literature -- 15-25 steps
(Cleary 2001) and 20-70 steps (Boemer & Ponthot 2017) -- plus an energy
balance within a few percent (see [16](16_validation_checks.md)).

Options considered (contact time and peak overlap both scale as E^-0.4, so a
larger dt needs a larger reduction for the same number of steps):

| Option | dt | Uniform reduction f | E steel / rock | Max peak overlap at 14.5 m/s | Cost vs 1e-4 | Status |
|---|---|---|---|---|---|---|
| **A** | 2.5e-5 s | **26** | 7.96 / 2.115 GPa | 3.8 % | 4x | **chosen** |
| C | 5e-5 s | 147 | 1.41 / 0.374 GPa | 7.5 % | 2x | fallback if compute is short |
| B | 1e-4 s | 832 | 0.249 / 0.066 GPa | 15 % | 1x | rejected: exceeds Boemer's ~10 % limit |

The PPT's slide-12 set (33.16 / 2.868 GPa, i.e. steel / 6.2 and rock / 19.2)
was first adopted with dt = 2.5e-5 s and then replaced by the uniform
reduction; see [03](03_stiffness_young_modulus.md) for why.

## Evidence

The references are grouped by the argument they support. Every quote was
checked in the PDF.

### E1. Stability is necessary but not sufficient; accuracy sets dt

| Source | What it says | Where | Verified |
|---|---|---|---|
| Boemer & Ponthot 2017 | "To ensure the stability of the algorithm, it is necessary that the time step is smaller than the critical time step tc, e.g. tc = 2/omega_max for an undamped system ... Furthermore, this time step can also be determined in order to limit the creation of numerical energy, i.e. to recover the coefficient of restitution ... By limiting the creation of artificial energy in normal collisions to 1 % with respect to the total energy in the system, **this criterion is more restrictive than the stability requirement**." | §2.2.3 "Time integration", PDF p5 / j.57 | Yes |
| Cleary 2001 | "If the integration is accurate then the coefficient of restitution from which the damping coefficient was chosen should be recovered." | §2, PDF p5 / j.83 | Yes |
| Govender 2015 | Kn (and with it dt) "is chosen such that physical quantities of interest (such as energy) are conserved during integration for the typical range of velocities observed in tumbling mill simulations" | §1.5, PDF p6 / j.157 | Yes |

This is why the critical-step formula of PPT slide 9 (a stability bound)
cannot by itself justify dt: the papers size dt for accuracy, which is
stricter.

### E2. The accuracy criterion: steps per collision

| Source | What it says | Where | Verified |
|---|---|---|---|
| Cleary 2001 | "Between 15 and 25 timesteps are required to accurately integrate each collision." | §2, PDF p5 / j.83 | Yes |
| Boemer & Ponthot 2017 | The 1 % artificial-energy criterion "is equivalent to choosing 20-70 time steps per collision depending on the coefficient of restitution; more time steps per collision are usually required when the coefficient of restitution is important" | §2.2.3, PDF p5 / j.57 | Yes |

### E3. Typical magnitude of dt in mill DEM

| Source | What it says | Where | Verified |
|---|---|---|---|
| Cleary 2001 | The 15-25 steps "necessitates very small timesteps (typically 10^-4 to 10^-6 s depending on the controlling length and time scales of each problem)" -- the range is a consequence of the steps criterion, not a free choice | §2, PDF p5 / j.83 | Yes |
| Govender 2015 | dt = 2e-5 s for the slice mill, GPU and CPU codes | Table 6, PDF p12 / j.163 | Yes |
| Govender 2015 | dt = 2e-5 s for the Los Bronces SAG mill (10.12 m, 10 rpm) -- the closest industrial case to this project | Table 8, PDF p14 / j.165 | Yes |
| Boemer & Ponthot 2017 | dt = 1e-5, 2.5e-6, 1e-6 s for kn = 1e5, 1e6, 1e7 N/m (lab mill, 15 mm balls, run in YADE) | §3.1, PDF p7 / j.59 | Yes |
| Kishida 2025 | dt = 2.0 us (E = 1e7 Pa, 0.25-0.5 mm particles) | Fig. 2(b), PDF p4 | Yes (figure read) |
| Thakur 2016 | dt = 1e-5 s (uniaxial compression of 2-3.75 mm particles; not a mill) | Parameter table, PDF p5 / j.134 | Yes |

### E4. Worst-case impact speed

| Source | What it says | Where | Verified |
|---|---|---|---|
| Boemer & Ponthot 2017 | Maximum relative impact velocity "can be assumed to be equal to sqrt(2 x 9.81 x 0.8) ~ 4 m/s, which corresponds to the terminal velocity when a ball falls from the top of the mill (diameter of 0.8 m) to its lowest position starting from rest" | §3.1.2, PDF p8 / j.60 | Yes |
| Govender 2015 | Kn / dt chosen "for the typical range of velocities observed in tumbling mill simulations" | §1.5, PDF p6 / j.157 | Yes |

Applied here (SAG_A, D inside liners 10.7128 m): sqrt(2 x 9.81 x 10.7128) =
14.5 m/s.

### E5. Stiffness and dt are chosen together

| Source | What it says | Where | Verified |
|---|---|---|---|
| Cleary & Morrison 2016 | Stiffness "is used as a numerical rather than a physical parameter and is chosen ... so as to maximise the timestep and therefore minimise the simulation time ... as long as the numerical contact deformations remain small" | §2, PDF p3 / j.77 | Yes |
| Govender 2015 | "Typical DEM simulations use a spring stiffness and time-step that limits the maximum penetration depth to d_max ~ 0.05 r where r is the radius of the smallest particle (Cleary, 2001; ...)" | §1.5, PDF p6 / j.157 | Yes |

The overlap side of this trade-off is documented in
[03](03_stiffness_young_modulus.md).

### E6. Mill-specific bound: lifter motion per step

| Source | What it says | Where | Verified |
|---|---|---|---|
| Govender 2015 | Distance covered by a lifter in one step is R omega dt, so "the maximum time-step for a mill rotating at omega rpm having a maximum penetration distance of d_max is given by dt = d_max / (R omega)" (Eq. 11); with d_max = 0.025 r, dt_max = 1.65e-5 s for their mill | §1.6, Eq. (11), PDF p7 / j.158 | Yes |

### E7. The DEM dt is independent of the dataset frame interval

| Source | What it says | Where | Verified |
|---|---|---|---|
| Kishida 2025 | "The Delta t_RNN was significantly larger than the time step used in the DEM"; Delta t_RNN = 0.05 s | §2.1, PDF p3; §3, PDF p6 | Yes |

So reducing the DEM dt to 2.5e-5 s does not change the 0.05 s frame
interval of the datasets ([14](14_dataset_runs_and_recording.md)); it only
changes run time.

## PPT

| Slide | Content |
|---|---|
| 8 | "Se busca mantener en la simulacion DEM un dt = 0.0001 = 1e-4 [5]" -- [5] = Boemer & Ponthot. **Not supported by [5]**: Boemer uses 1e-5 to 1e-6 s. The closest support is Cleary 2001 (range 1e-4 to 1e-6 s *conditional on* 15-25 steps per collision). |
| 9 | dt_cr = R_min sqrt(rho / E_eff), E_eff = E / (1 - nu^2); with real E_rock = 55 GPa: dt_cr = 7.42e-6 s; E_reduced for dt_target = 1e-4: rock 3.0e8 Pa, steel 3.5e9 Pa |
| 10 | YADE `PWaveTimeStep()` = 1.36e-5 s with original moduli and 1.05e-4 s with 3.5e9 / 3e8 Pa; run used dt = 0.2 dt_crit |
| 11 | Table of E_reduced for dt_crit = 1.5e-5 ... 5e-5 s; aim "dt_crit entre 1.36e-5 y 1e-4" |
| 12 | Chosen moduli 33.16 GPa / 2.868 GPa, i.e. the dt_crit = 3.25e-5 s row of slide 11 |
| 17, 18, 19 | IC generation and dataset runs at **dt = 1e-4** |

## Current state

| Where | What |
|---|---|
| `main` `yade_dem/run_simulation.py:36` | `set_dt(new_dt=0.000015 * 0.2)` = 3e-6 s |
| `main` `config.py:89,96` | Moduli of the dt_crit = 1.5e-5 row (155.7 GPa / 13.47 GPa), not slide 12 |
| `data/raw/sic_dataset_20s_dt0p0001_csv.zip` | Generated at dt = 1e-4 s (folder name `sic_dataset_20s0.0001_`) |

## Analysis

### Formulas used and the status of their sources

The critical-step formulas are **not** the basis of the decision: they bound
*stability*, while the papers size dt by *accuracy*, which is stricter
(E1). They are reported only to show the stability bound is respected.

| Formula | Role here | Source | In Zotero? |
|---|---|---|---|
| t_c = 2 / omega_max (generic stability limit, undamped) | Stability bound | Boemer & Ponthot 2017 §2.2.3, PDF p5 (citing their ref. [30]) | **Yes** |
| P-wave step. **YADE's definition: dt = r / sqrt(E / rho)**, with E directly. PPT slides 9-11 use E_eff = E / (1 - nu^2), which gives a step 3-4 % smaller than YADE's | Stability bound | YADE docs 2021 (3rd ed., the latest official edition): §2.1 "DEM formulation", "Stability considerations -- Critical timestep", Eqs. (2.12)-(2.13), printed p. 72 (PDF p79); `yade.utils.SpherePWaveTimeStep` entry, printed p. 838 (PDF p845), whose example (r = 1e-3 m, rho = 2400, E = 30e9 -> 2.83e-7 s) confirms plain E | **Yes** (`4NJP35ET`) |
| Rayleigh step dt_R = (pi R / beta) sqrt(rho / G), beta = 0.8766 + 0.163 nu | Stability bound commonly used for Hertz-Mindlin | Li et al. 2005, end of §2, Eqs. (8)-(10), j.221 (PDF p3): beta from the exact Rayleigh-wave equation (9), approximated by Eq. (10) with **0.163** (later papers print 0.1631); R = average particle radius. Same formula in Nan et al. 2022, Eq. (71), manuscript p18, credited to Raji (1999) | **Yes** (`BN556RC8`, `M78ZRT88`) |
| Hertz impact duration t_c = 2.87 (m*^2 / (R* E*^2 v))^(1/5) = 2.94 delta_max / v | Steps per collision (the governing criterion) | Johnson 1985, §11.4 "Elastic impact", (a) "Collinear impact of spheres", **Eq. (11.24)**, book p. 353 (PDF p363) | **Yes** (`PDKNRX4P`) |
| Hertz maximum overlap delta_max = (15 m* v^2 / (16 E* R*^0.5))^(2/5) | Peak overlap ([03](03_stiffness_young_modulus.md)) | Johnson 1985, **Eq. (11.22)**, book p. 353 (PDF p363); force law P = (4/3) R^(1/2) E* delta^(3/2) and the definitions 1/R = 1/R1 + 1/R2, 1/E* = (1-nu1^2)/E1 + (1-nu2^2)/E2, 1/m = 1/m1 + 1/m2 in **Eq. (11.20)**, book p. 352 (PDF p362), from Eq. (4.23) of Ch. 4 | **Yes** (`PDKNRX4P`) |
| Linear-spring contact time / maximum overlap | Used by the mill papers (linear models) | Govender 2015 §1.5 Eq. (7), PDF p6; Boemer & Ponthot 2017 Eqs. (8)-(9), PDF p8 | Yes (but for the linear, not the Hertz, model) |

Internal check of the Hertz coefficients (independent of any source): with
F = (4/3) E* R*^(1/2) delta^(3/2), energy conservation gives
delta_max = (15 m* v^2 / (16 E* R*^(1/2)))^(2/5), and the contact lasts
t_c = 2.94 delta_max / v; substituting, 2.94 x (15/16)^(2/5) = 2.87. Other
coefficients seen in the literature (2.94, 3.21) are the same law written with
a different stiffness constant.

All formulas used in this file and in [03](03_stiffness_young_modulus.md)
are located in a source held in Zotero (verified 2026-10-19).


Nan et al. 2022 (manuscript p18) add that the Rayleigh step "only provides
the maximum limit of the time step" and recommend Delta t = 0.01-0.1
Delta T_R to resolve the details of their elasto-plastic adhesive contact
(e.g. the pull-off stage, their Fig. 1). That model has no adhesion here, so
the range is context rather than a criterion; dt = 2.5e-5 s is 0.11 Delta T_R
(rock), and the governing check remains the steps-per-collision criterion
(E2).

### Critical step (stability) with the chosen moduli

| Estimate | Steel (r = 0.06985 m) | Rock (r = 0.034925 m) |
|---|---|---|
| YADE P-wave step r / sqrt(E / rho) | 6.94e-5 s | 4.05e-5 s (3.91e-5 at 2650) |
| PPT slide-9 formula r sqrt(rho (1 - nu^2) / E) | 6.63e-5 s | 3.93e-5 s |
| Rayleigh step pi r sqrt(rho / G) / (0.8766 + 0.163 nu) (Li et al. 2005, Eq. 10), G = E / (2 (1 + nu)) | 3.79e-4 s | 2.20e-4 s (2.12e-4 at 2650) |

dt = 2.5e-5 s is 0.62x the smallest P-wave step (0.64x at 2650) and 0.11x the smallest
Rayleigh step: stability is respected with margin. The binding constraint is
the accuracy criterion below.

For the record: with the PPT's slide-12 set the PPT's own formula gives
3.25e-5 s, so the dt = 1e-4 s of slides 17-19 was 3.1x above the critical
step of the moduli it was used with.

### Steps per collision (the criterion the papers actually use)

Hertz elastic impact duration t_c = 2.87 (m*^2 / (R* E*^2 v))^(1/5)
(Johnson 1985, Eq. 11.24), f = 26 moduli, rock density 2850 kg/m^3 (steel-steel rows do
not depend on it):

| Pair | v (m/s) | t_c (s) | steps @ 1e-4 | steps @ 5e-5 | steps @ 2.5e-5 |
|---|---|---|---|---|---|
| steel-steel | 1 | 1.56e-3 | 15.6 | 31.2 | 62.4 |
| steel-steel | 8 | 1.03e-3 | 10.3 | 20.6 | 41.2 |
| steel-rock | 5 | 6.58e-4 | 6.6 | 13.2 | 26.3 |
| steel-rock | 8 | 5.99e-4 | 6.0 | 12.0 | 24.0 |
| steel-rock | 12 | 5.52e-4 | 5.5 | 11.0 | 22.1 |
| rock-rock | 8 | 5.89e-4 | 5.9 | 11.8 | 23.6 |
| steel-steel | **14.5** (worst case) | 9.14e-4 | 9.1 | 18.3 | **36.6** |
| steel-rock | **14.5** | 5.32e-4 | 5.3 | 10.6 | **21.3** (20.7 at 2650) |
| rock-rock | **14.5** | 5.23e-4 | 5.2 | 10.5 | **20.9** (20.3 at 2650) |

The worst case uses Boemer & Ponthot's choice of impact speed (§3.1.2,
PDF p8): free fall across the mill, sqrt(2 g D) = 14.5 m/s for SAG_A's
D = 10.71 m (inside liners). Real impacts are slower: the shell moves at
5.05 m/s at 9 rpm and the old (40 ft)
dataset's fastest particle moved at 12.6 m/s (frame 399). Even in the worst
case every contact gets >= 20 steps, meeting both Cleary's 15-25 and
Boemer's 20-70 (the rock contacts, with low restitution 0.3-0.5, need the
fewest steps: "more time steps per collision are usually required when the
coefficient of restitution is important", Boemer §2.2.3, PDF p5). At
dt = 1e-4 s the same collisions would get only ~5 steps.

### Govender's lifter-motion bound

dt_max = d_max / (R omega) with R = 5.36 m (SAG_A inside liners),
omega = 0.942 rad/s: 3.5e-4 s (d_max = 0.05 r_rock) or 1.7e-4 s
(0.025 r_rock). Not binding.

### Option B: keep dt = 1e-4 s

Getting the same >= 20 steps at 1e-4 s needs t_c x4, i.e. E / 32 relative to
option A (f = 832: E_steel ~ 0.25 GPa, E_rock ~ 0.07 GPa). Peak overlaps then
grow x4, to ~13-15 % of the smaller diameter at the 14.5 m/s worst case.
Boemer (§4, PDF p13) finds results insensitive "provided that the maximum
overlap percentage ... is smaller than about 10 %", so option B exceeds the
only measured sensitivity limit and is rejected. All overlap criteria in the
literature are compared in [03](03_stiffness_young_modulus.md).

### Cost

Throughput measured on this machine (24 cores, 16 threads) during the fill
of the full-scale lifter benchmark, with part of the charge loaded: ~400
steps/s (expect somewhat less with the full ~14k particles). A 33 s run at
2.5e-5 s is 1.33 M steps (~55 min); at 1e-4 s it would be ~14 min. The 4x
cost buys a collision resolution that the cited literature requires.

## Verdict and how to defend it

"The time step was set by integration accuracy rather than stability alone,
since recovering the coefficient of restitution is more restrictive than the
stability limit (Boemer & Ponthot 2017, §2.2.3; Cleary 2001, §2). Stiffness
being a numerical parameter chosen jointly with dt (Cleary & Morrison 2016,
§2; Govender et al. 2015, §1.5), both Young's moduli were reduced by the same
factor, 26, with which every collision is integrated with at least 20
steps at dt = 2.5e-5 s -- satisfying both the 15-25 steps of Cleary
(2001, §2) and the 20-70 of Boemer & Ponthot (2017, §2.2.3) -- at the
worst-case impact speed sqrt(2 g D) = 14.5 m/s (the free-fall estimate of
Boemer & Ponthot 2017, §3.1.2), using the Hertz impact duration of Johnson
(1985, Eq. 11.24). The P-wave and Rayleigh stability limits (YADE
documentation; Li et al. 2005) and the lifter-motion bound of Govender et al.
(2015, Eq. 11) are all respected with margin. The resulting dt is consistent
with the 1e-4 to 1e-6 s range of Cleary (2001) and close to the 2e-5 s used
by Govender et al. (2015, Table 8) for the Los Bronces SAG mill. The DEM time
step is independent of the 0.05 s interval at which frames are stored for the
surrogate model (Kishida et al. 2025, §2.1)."

## Open items / validation

- Measure the impact-velocity distribution in a pilot run (99th percentile of
  normal relative velocity at contact) and recompute the steps-per-collision
  table with it.
- dt-halving test (V9): run 2.5e-5 vs 1.25e-5 s for 2 revolutions; toe,
  shoulder and power must agree within the run-to-run scatter.
- Restitution recovery and energy balance (see [16](16_validation_checks.md)).
- Correct PPT slides 9-11: YADE's `PWaveTimeStep` uses E, not
  E / (1 - nu^2).
- ~~Add the formula sources to Zotero~~ -- done 2026-10-19; all formula
  locations verified (see the
  [README](README.md#references-added-on-2026-10-19-verified-in-the-pdfs)).

## Pending code changes

| ID | Change | Current code | When |
|---|---|---|---|
| C02-1 | **Default dt = 2.5e-5 s** (explicit `solver.dt_s` in the scenario defaults and JSONs) | Default is 0.3 x Rayleigh step: with the f = 26 moduli that is 6.4e-5 s, only ~8 steps per collision | Before any production run |
| C02-2 | Replace the scenario warning `dt / dt_R > 0.5` by the governing check: Hertz contact time (Johnson Eq. 11.24) at sqrt(2 g D) gives >= 20 steps for every pair | Only the Rayleigh-ratio warning (`scenario.warnings`) | With C02-1 |
| C02-3 | Log the impact-velocity distribution (P99 of normal relative velocity at contact) in the monitor | Not logged | With the run-type split |

# 03 -- Stiffness (Young's modulus)

## Decision

Both physical Young's moduli are reduced by the **same factor f = 26**
(decided 2026-10-19), preserving the physical steel / rock stiffness ratio:

| Material | Physical E | Source of the physical value | Simulation E = E / 26 |
|---|---|---|---|
| Steel (balls, lifters, shell) | 207 GPa | Shigley, 8th ed., inside-cover table "Constantes fisicas de materiales", carbon steel (PDF p3) | **7.96 GPa** |
| Rock (ore) | 55 GPa | Vergara et al. 2020, Table 1 "Mechanical parameters of intact rock of the CMET lithology", intact rock Young's modulus E_i (manuscript PDF p3) -- **representative value, not site-specific** (see "Ore modulus" below) | **2.115 GPa** |

Steel / rock ratio: 3.76 in both the physical and the simulated set.

**Rule behind f = 26:** every contact type (steel-steel, steel-rock,
rock-rock) is integrated with **>= 20 steps at the worst-case impact speed**
sqrt(2 g D) with dt = 2.5e-5 s ([02](02_time_step.md)), satisfying both the
15-25 steps of Cleary 2001 and the 20-70 of Boemer & Ponthot 2017. f = 26
was the smallest such reduction for the earlier 40 ft geometry (15.2 m/s);
for SAG_A (D inside liners 10.71 m, 14.5 m/s) the threshold is 25.0 for the
2650 sensitivity case and 23.3 at 2850, so 26 is kept with ~1 step of
margin. Softer sets only increase overlap.

Acceptance (all relative to the smaller particle **diameter**):

- **mean** overlap <= 0.5 % (the strictest average in the literature,
  Cleary & Morrison 2016);
- **maximum** overlap < 10 % (Boemer & Ponthot's sensitivity limit); the
  predicted worst case is 3.8 % (3.6 % with rock at 2650 kg/m^3);
- macroscopic results (toe, shoulder, power) unchanged when E is halved or
  doubled (validation check **V10**, [16](16_validation_checks.md)).

## Overlap criteria in the literature

| Source | Criterion | Kind | Relative to | Where |
|---|---|---|---|---|
| Cleary 2001 | "Typically, average overlaps of 0.1-1.0% are desirable" (hence kn = 8e6 N/m) | average, practice | not stated (diameter in the same group's later papers) | §2, PDF p4 / j.82 |
| Cleary & Morrison 2016 | "Typically, average overlaps of 0.1-0.5% are adequate to ensure a balance between computing speed and realistic predictions" | average, practice | not stated | §2, PDF p3 / j.77 |
| Owen & Cleary 2015 | kn chosen "to give an average overlap of the order of 0.8% of the average particle diameter" | average, used value | average diameter | §3, PDF p3 / j.21 |
| Boemer & Ponthot 2017 | Limit "the average overlap ... to a value between 0.1 and 1 % with respect to the diameter of the ball ... maybe 10 % would still lead to satisfying results" | average, practice | ball diameter | §3.1.2, PDF p8 / j.60 |
| Boemer & Ponthot 2017 | Results "relatively insensitive to the normal stiffness provided that the maximum overlap percentage ... is smaller than about 10 %" | **maximum, measured sensitivity** | diameter | §4, PDF p13 / j.65 |
| Boemer & Ponthot 2017 | Method: maximum overlap from the analytic collision (Eqs. 8-9) at the worst-case impact speed v_r = sqrt(2 g D) (free fall across the mill) | method | -- | §3.1.2, PDF p8 / j.60 |
| Govender 2015 | "Typical DEM simulations use a spring stiffness and time-step that limits the maximum penetration depth to d_max ~ 0.05 r where r is the radius of the smallest particle" (= 2.5 % of its diameter); lifter contacts accepted only for penetration < 5 % of the radius (Algorithm 1) | maximum, practice | smallest radius | §1.5, PDF p6 / j.157; Algorithm 1, PDF p5 / j.156 |
| Kishida 2025, Thakur 2016 | No overlap criterion stated | -- | -- | -- |

Two kinds of number appear: **average** overlaps (practice, 0.1-1 %, the
strictest being 0.1-0.5 %) and **maximum** overlaps (Govender's typical
practice 2.5 % of the diameter; Boemer's tested sensitivity limit ~10 %).
Only Boemer's 10 % is an actual sensitivity result; the others are
customary values.

## Evidence

| Source | What it says | Where | Verified |
|---|---|---|---|
| Shigley | Carbon steel ("Acero al carbono"): E = 207 GPa, G = 79.3 GPa, nu = 0.292 (table "Constantes fisicas de materiales"); also "el acero tiene un modulo de elasticidad de alrededor de 30 Mpsi (207 GPa) sin que importe el tratamiento termico, el contenido de carbono o la aleacion" | Inside-cover table, PDF p3; Ch. 2 text, PDF p59 | Yes |
| Vergara et al. 2020 | Table 1 "Mechanical parameters of intact rock of the CMET lithology": "Intact rock Young's modulus, E_i (GPa) 55"; "Intact rock Poisson's ratio 0.25" (repeated in the table on PDF p6) | Table 1, manuscript PDF p3 | Yes |
| Vergara et al. 2020 | Context: "Veined rock masses can be found in porphyry copper deposits like at the El Teniente mine in Chile"; tests "on veined rock andesite from the El Teniente mine" | Abstract, manuscript PDF p1 | Yes |
| Cleary & Morrison 2016 | "the stiffness is used as a numerical rather than a physical parameter ... This is generally possible as long as the numerical contact deformations remain small and the contact force networks are not altered by the moderate softening of the springs." (the sentence says "chosen to be larger than the real material stiffness so as to maximise the timestep", which given the rest of the sentence reads as a wording slip for softer) | §2, PDF p3 / j.77 | Yes |
| Cleary & Morrison 2016 | kn = 500,000 N/m, ks = 250,000 N/m for a 1.12 m pilot mill | Table 2, PDF p7 / j.81 | Yes |
| Owen & Cleary 2015 | kn = 20e6 N/m "chosen to give an average overlap of the order of 0.8 % of the average particle diameter. This is sufficient to give accurate mill simulations" | §3, PDF p3 / j.21 | Yes |
| Boemer & Ponthot 2017 | Charge motion and power "relatively insensitive to the normal stiffness provided that the maximum overlap percentage of two colliding spheres is smaller than about 10 %" (tested with steel balls only) | §4, PDF p13 / j.65 | Yes |
| Kishida 2025 | E = 1.0e7 Pa for 0.25-0.5 mm particles (strong reduction is standard practice even in the reference study) | Fig. 2(b), PDF p4 | Yes |
| Johnson 1985 | Hertz force law and maximum overlap used below: Eq. (11.20) p. 352, Eq. (11.22) p. 353 | §11.4(a), PDF pp. 362-363 | Yes |
| Thakur 2016 | Contact stiffness scales **linearly with particle size** for coarse-grained (scaled-up) particles | Abstract, PDF p1 / j.130; §2, PDF p3 / j.132 | Yes -- but **not** about reducing E for dt |

## PPT

| Slide | Content |
|---|---|
| 8 | Physical moduli: steel 207 GPa [Shigley], rock 55 GPa [Vergara]; "-> ? Pa [3]" (Thakur). Text: stiffness can be reduced "siempre y cuando se mantenga un bajo overlap de particulas (< 0.1 %)" citing [3][5][6] |
| 9 | E_reduced = rho (R_min / dt_target)^2 (1 - nu^2), computed **per material with its own radius**; for dt_target = 1e-4: rock 3.03e8 Pa, steel 3.50e9 Pa |
| 10 | YADE overlap check (994 rocks, 234 balls, settled): original moduli max overlap 0.039 %; 3.5e9 / 3e8 Pa max overlap **1.085 %**. Target stated: dt_crit between 1.36e-5 and 1e-4 with overlap between 0.1 % and 0.5 % |
| 11 | E_reduced table for dt_crit = 1.5e-5, 2e-5, 3e-5, 3.25e-5, 3.5e-5, 5e-5 s (the 3e-5 row's formula text shows 0.00002 but the value is computed with 3e-5) |
| 12 | Final: steel 33.16e9 Pa, rock 28.68e8 Pa (= 2.868e9 Pa) -- steel / 6.2, rock / 19.2 |

Note on slide 10: `diagnostics.check_overlaps()` divides the penetration by
`min(r1, r2)` (a **radius**), so 1.085 % of the radius is 0.54 % of the
diameter. The papers quote overlap relative to the **diameter**.

## Current state

| Where | What |
|---|---|
| `main` `config.py:89` | steel young = 155,709,722,558 Pa (slide 11, dt_crit = 1.5e-5 row) |
| `main` `config.py:96` | rock young = 13,468,135,026 Pa (same row) |
| -- | Neither slide 12 nor the f = 26 set is in the code yet. |

## Analysis

### Why a uniform reduction, not slide 12

Slides 9-11 derived each modulus from its own particle radius so that both
materials had the same P-wave critical step (3.25e-5 s for slide 12). That
softened steel by 6.2x and rock by 19.2x, making the simulated steel / rock
stiffness ratio **11.6 instead of the physical 3.8**. Once dt is set by the
steps-per-collision criterion ([02](02_time_step.md)) rather than by equal
critical steps, that construction has no remaining purpose. A uniform
reduction keeps the stiffness *ratio* physical, so the only approximation is
the overall softening -- which is exactly what Boemer & Ponthot's
insensitivity result covers. (That result was obtained with steel balls only,
so it does not by itself show that distorting the steel / rock ratio is
harmless in a mixed charge; the uniform reduction avoids having to argue it.)

### Why f = 26: the admissible range at dt = 2.5e-5 s

Rock density 2850 kg/m^3 ([08](08_density.md)); values for the 2650
sensitivity case in brackets where they change the conclusion.

SAG_A worst-case impact speed sqrt(2 g D) = 14.5 m/s (D inside liners
10.71 m, [10](10_mill_geometry.md)).

| f | E steel / rock | Fewest steps per collision (14.5 m/s) | Max peak overlap (14.5 m/s) | Status |
|---|---|---|---|---|
| <= 9.4 | >= 21.9 / 5.82 GPa | <= 14.0 | <= 2.5 % | meets Govender's customary 2.5 %, **fails** Cleary's 15 steps |
| 11.3 | 18.3 / 4.86 GPa | 15.0 | 2.7 % | Cleary's minimum, no margin |
| 23.3 | 8.90 / 2.37 GPa | 20.0 (19.4) | 3.6 % | meets Boemer's 20 at 2850 only, no margin |
| 25.0 | 8.28 / 2.20 GPa | 20.5 (20.0) | 3.7 % | meets both at both densities, no margin |
| **26** | **7.96 / 2.115 GPa** | **20.9 (20.3)** | **3.8 %** | **meets Cleary and Boemer for every contact at both rock densities, ~1 step margin** |
| <= 302 | -- | -- | < 10 % | Boemer's overlap limit |

f = 26 (fixed 2026-10-19 on the earlier 40 ft geometry) still meets both
step criteria for both rock densities used (2850 baseline, 2650 sensitivity
run) with a small margin; the same moduli serve both density runs, so only
density changes between them. Softening further gains
nothing but overlap. The range itself shows that no stiffer set
can meet both Cleary's/Boemer's step criteria and Govender's customary 2.5 %
at this dt: the customary 2.5 % would need dt ~ 1.7e-5 s.

### Peak overlaps with f = 26

delta_max = (15 m* v^2 / (16 E* R*^0.5))^(2/5) (Johnson 1985 Eq. 11.22,
p. 353, with E*, R*, m* as defined in Eq. 11.20, p. 352), relative to the
smaller diameter (rock density 2850 kg/m^3; steel-steel independent of it):

| Pair | 1 m/s | 5 m/s | 8 m/s | 12 m/s | **14.5 m/s (worst case)** |
|---|---|---|---|---|---|
| steel-steel | 0.38 % | 1.37 % | 2.00 % | 2.77 % | **3.22 %** |
| steel-rock | 0.44 % | 1.60 % | 2.33 % | 3.22 % | **3.75 %** |
| rock-rock | 0.43 % | 1.57 % | 2.29 % | 3.17 % | **3.68 %** |

The worst case follows Boemer's method: v_r = sqrt(2 g D) =
sqrt(2 x 9.81 x 10.7128) = 14.5 m/s for SAG_A, a particle falling from the
top of the mill to the bottom. Real impacts are slower (the old 40 ft
dataset's fastest particle moved at 12.6 m/s).

Against the criteria:

- **Maximum overlap.** Worst case 3.2-3.8 %: well below Boemer's ~10 %
  sensitivity limit. Govender's *customary* 2.5 % is exceeded only for
  impacts above ~9 m/s; meeting it would need a stiffer set and dt ~1.6e-5 s,
  which no sensitivity evidence requires.
- **Average overlap.** Average overlaps come from the enduring contacts of the
  bulk charge, loaded by gravity rather than impacts. Slide 10's settled-bed
  check gave a **maximum** of 0.54 % of the diameter for the much softer
  3.5e9 / 3e8 Pa set; static Hertz overlap scales as E^(-2/3), so the f = 26
  set (2.3x stiffer steel, 7x stiffer rock) should settle with maximum
  overlaps of roughly 0.15-0.3 %, and mean overlaps lower still -- inside the
  strictest 0.1-0.5 % average range (Cleary & Morrison). This must be
  measured, not assumed (see open items).

The slide-8 target "< 0.1 %" is below the lower end of every average range
in the library (0.1-0.5 % to 0.1-1 %); it should be replaced by these ranges.

### Ore modulus

The SAG_A/B/C mills grind ore from large Chilean copper operations
(e.g. Caserones, Minera Escondida, Minera Los Pelambres); no measured Young's
modulus of these ores is available. The value used, E_i = 55 GPa, is the
intact-rock modulus of El Teniente (CMET) andesite from Vergara et al. 2020,
Table 1 (manuscript PDF p3), a Chilean porphyry copper deposit ("Veined rock
masses can be found in porphyry copper deposits like at the El Teniente mine
in Chile", abstract). It is therefore a **representative value for hard
igneous rock of a Chilean porphyry copper deposit, not a measurement of the
SAG_A/B/C ores**. Its companion Poisson's ratio (0.25) lies within Gercek's
range for andesite ([09](09_poisson_ratio.md)).

The uncertainty matters little here: the modulus is reduced 26x for
numerical reasons, and V10 tests a factor-2 change in both moduli, which
brackets any plausible difference between this andesite value and the actual
ores.

## Verdict and how to defend it

"Young's moduli start from physical values -- 207 GPa for carbon steel
(Shigley) and 55 GPa for intact andesite of a Chilean porphyry copper deposit
(El Teniente, Vergara et al. 2020, Table 1), used as representative since
the ores of the reference mills were not characterised -- and are reduced by
a common factor of 26, preserving their physical ratio, to 7.96 and
2.115 GPa. In mill DEM the stiffness is a numerical parameter (Cleary &
Morrison 2016, §2); with this factor every collision is integrated with at
least 20 steps at dt = 2.5e-5 s for both ore densities considered (2850
and 2650 kg/m^3), satisfying the accuracy
criteria of Cleary (2001, §2) and Boemer & Ponthot (2017, §2.2.3). The
maximum overlap, estimated with Hertz theory (Johnson 1985, Eq. 11.22) at
Boemer & Ponthot's worst-case impact speed sqrt(2 g D) = 14.5 m/s, is 3.8 %,
well below the ~10 % up to which charge motion and power are insensitive to
stiffness (Boemer & Ponthot 2017, §4); average overlaps stay within the
0.1-0.5 % of Cleary & Morrison (2016, §2). A sensitivity study with both
moduli halved and doubled confirmed that charge shape and power do not depend
on the stiffness reduction (V10). Measured overlaps: mean X %, max Y %."

Replace the Thakur citation for this argument: Thakur 2016 concerns stiffness
scaling with particle size in coarse-grained DEM, not softening for dt.

## Open items / validation

- Measure mean / P99 / max overlap relative to the diameter, per contact
  pair type, in a steady-rotation run with the f = 26 set.
- **V10** (kept, 2026-10-19): runs at E x 0.5 (f = 52) and E x 2 (f = 13),
  both materials together, 3 revolutions each, same dt = 2.5e-5 s (E x 2
  still gets >= 15.3 steps per collision); toe, shoulder, power and charge
  angle must stay within the replicate scatter (V12).
- Update `config.MATERIALS` and `young_scale`: see C03-1 below.

## Pending code changes

| ID | Change | Current code | When |
|---|---|---|---|
| C03-1 | Store the **physical** moduli in `config.MATERIALS` (steel 207e9, rock 55e9 Pa) and set `solver.young_scale = 1/26` in the scenario, so the provenance stays visible | `config.py`: 155.7e9 / 13.47e9 Pa (PPT slide-11 row), `young_scale` default 1.0 | Before any production run |
| C03-2 | Overlap statistics relative to the smaller **diameter**, per pair type (mean, P99, max) in the monitor | `monitor.max_overlap()` divides by the smaller **radius** (2x the literature convention) and reports the max only; same in `diagnostics.check_overlaps()` | With C03-1 |
| C03-3 | V10 scenarios: `young_scale` = 1/52 and 1/13 | None | After C03-1 |

# 08 -- Particle density

## Decision

| Material | Density |
|---|---|
| Steel (balls; also the fixed liner facets, where density has no effect) | **7850 kg/m^3** |
| Rock (ore) | **2850 kg/m^3** (decided 2026-10-21; literature value for Chilean porphyry copper ore, no plant measurement) |

- These are the `density` values of the YADE `FrictMat` materials: the
  **solid (particle) density**, i.e. specific gravity x 1000, not the bulk
  density of a pile (which includes the voids).
- Densities are **physical inputs, not calibration variables**.
- The ore value is backed by a one-off **sensitivity run at 2650 kg/m^3**
  (the generic rock value of Cleary & Morrison 2016) comparing toe,
  shoulder, power **and steel / rock segregation** (V11b).
- Until 2026-10-21 the baseline was 2650; it was changed to 2850 for
  consistency with the rock modulus of [03](03_stiffness_young_modulus.md),
  which comes from the same Chilean porphyry-copper source.

## Evidence

| Source | What it says | Where | Verified |
|---|---|---|---|
| Vergara et al. 2020 | El Teniente veined andesite (Chilean porphyry copper deposit): "Intact rock density, (kN/m3) 28" = 2855 kg/m^3; same table as the E = 55 GPa, nu = 0.25 used in [03](03_stiffness_young_modulus.md) | Table 10, manuscript PDF p16 | Yes |
| Govender 2015 | Los Bronces SAG (Chilean porphyry copper): ore 2850 kg/m^3, balls 7800 kg/m^3 | Table 7, PDF p14 / j.165 | Yes |
| Cleary & Morrison 2016 | Density of rock 2650, of ball 7850 kg/m^3; rock "at an SG of 2.65", balls "at an SG of 7.85" | Table 2, PDF p7 / j.81; Table 1, PDF p7 / j.81 | Yes |
| Owen & Cleary 2015 | Ore 3000 kg/m^3, steel balls 7850 kg/m^3 | §3 text and Table 4, PDF p3 / j.21 | Yes |
| Shigley | Carbon steel unit weight 76.5 kN/m^3 (= 7800 kg/m^3) | Inside-cover table, PDF p3 | Yes |
| Cleary 2001 (2D) | "The ball density itself has almost no effect on the charge behaviour or on the specific power draw." | §11 Conclusion, PDF p34 / j.112 | Yes |
| Kishida 2025 | Single density 2500 kg/m^3 for both sizes (size-only segregation) | Fig. 2(b), PDF p4 | Yes |

## PPT

| Slide | Content |
|---|---|
| 8, 9, 12 | Steel 7850 kg/m^3 [1], rock 2650 kg/m^3 [1] ([1] = Cleary & Morrison 2016, Table 2 -- slide says "Page 81, Table 2", which is correct: PDF p7 = j.81). **Rock superseded by 2850** |
| 30 | "Busqueda manual para Angulos de Friccion y **Densidades** (respecto a Acomodo de Carga)" |

## Current state

`pm_dem_sm/config.py:90, 97`: 7850 / 2650 -- rock must change to 2850
(C08-1).

## Analysis

### Ore density: why 2850

- The SAG_A-C mills grind Chilean porphyry copper ore. The two sources that
  describe that ore type give the same value: El Teniente andesite,
  28 kN/m^3 = 2855 kg/m^3 (Vergara et al. 2020, Table 10), and the Los
  Bronces SAG ore, 2850 kg/m^3 (Govender et al. 2015, Table 7).
- Vergara et al. is also the source of the rock modulus and Poisson's ratio
  ([03](03_stiffness_young_modulus.md), [09](09_poisson_ratio.md)), so 2850
  keeps the rock properties from one consistent source.
- 2650 (Cleary & Morrison 2016) is a generic rock value (quartz-like SG
  2.65); 3000 (Owen & Cleary 2015) is another generic choice. The literature
  range for SAG ore is therefore 2650-3000 kg/m^3, and 2850 sits inside it.
- No plant measurement of the ore SG is available (confirmed 2026-10-18 and
  2026-10-21), so the literature value stands, backed by the sensitivity
  run.

### Steel density: why 7850 and not 7800

The sources split: 7850 in Cleary & Morrison 2016 (Table 2) and Owen &
Cleary 2015 (Table 4); 7800 in Govender 2015 (Table 7) and Shigley
(76.5 kN/m^3, generic carbon steel). 7850 is kept because:
- it is the value of the two mill DEM papers whose friction and restitution
  sets this project uses ([05](05_friction.md), [07](07_restitution.md));
- the difference is 0.6 %, and "the ball density itself has almost no
  effect on the charge behaviour or on the specific power draw" (Cleary
  2001, §11), so the choice cannot affect the results measurably;
- grinding balls are high-carbon / alloyed forged steel, for which
  7.80-7.85 g/cm^3 are both nominal values. Kept at 7850 (confirmed by the
  author 2026-10-21).

### Why density is not calibrated

- It is a measurable physical property; tuning it to the charge shape
  (PPT slide 30) would absorb errors from friction and particle shape.
- With two targets (toe, shoulder) already used for mu_p and mu_w
  ([05](05_friction.md)), it could not be identified anyway.
- For steel, Cleary 2001 (§11) shows ball density barely affects the
  charge. For ore no such source exists, which is why the ore value gets a
  sensitivity run.

### Density and segregation

The steel / rock density ratio drives segregation: 7850 / 2850 = 2.75
(2.96 with 2650). Unlike Kishida's single-density system, here the large
particles (balls) are also the dense ones, so size and density segregation
compete ([13](13_initial_conditions.md)). The sensitivity run therefore
compares segregation, not only charge shape and power.

### Effect of the change on other topics

Heavier rock lengthens rock collisions and raises the rock critical step, so
the time step stays valid (dt = 0.62 of the smallest P-wave step, >= 20.9
steps per collision at SAG_A's worst-case 14.5 m/s) and f = 26 is kept: it
satisfies the step criteria at **both** 2850 and 2650 (20.3 steps), so the
sensitivity run changes density only. Peak overlap 3.8 % at 2850 vs 3.6 %
at 2650 (limit 10 %). Recomputed numbers: [02](02_time_step.md),
[03](03_stiffness_young_modulus.md), [04](04_numerical_damping.md).

## Verdict and how to defend it

"Densities are physical: steel 7850 kg/m^3 (Cleary & Morrison 2016,
Table 2; Owen & Cleary 2015, Table 4) and ore 2850 kg/m^3, the value for
Chilean porphyry copper ore (El Teniente andesite, Vergara et al. 2020,
Table 10; Los Bronces SAG, Govender et al. 2015, Table 7), inside the
2650-3000 kg/m^3 range used in SAG DEM studies. They are not calibrated:
they are measurable, and calibration is carried by friction and rolling
resistance. Because the ore density also sets the steel / rock density
ratio that drives segregation, a run with 2650 kg/m^3 (Cleary & Morrison
2016) was compared for toe, shoulder, power and segregation."

## Open items

- **Sensitivity run (V11b):** rock density 2650 vs. 2850 kg/m^3 at the
  calibrated parameters, same moduli (f = 26), 3 revolutions; compare toe,
  shoulder, power **and steel / rock segregation** with the replicate
  scatter (V12). If they differ beyond it, ore density becomes a stated
  limitation.
- No plant ore SG will be available (confirmed by the author 2026-10-21):
  2850 kg/m^3 stays a literature value, and the V11b run is its support.

## Pending code changes

| ID | Change | Current code | When |
|---|---|---|---|
| C08-1 | Rock `density` 2650 -> **2850** in `MATERIALS` | `config.py:97` | Before calibration |

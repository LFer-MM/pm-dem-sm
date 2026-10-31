# 15 -- Calibration targets (charge shape and power)

## Decision

**Angle convention (fixed 2026-10-18):** 0 deg at the **3 o'clock** position
(right side, +X in YADE), angles increasing **counter-clockwise**, mill
rotating **counter-clockwise** seen from +Z (positive angular velocity about
Z in YADE). The charge rises on the right: shoulder in the first quadrant
(~25 deg), toe in the third quadrant (~215 deg). Liner designs are
symmetric, so this orientation is a free choice in simulation.

**Role of the reference mills** (SAG_A, SAG_B, SAG_C; SAG_D and SAG_E
may be added). **SAG_A is the reference**: its operating point sets the
simulation and its charge-shape angles are the targets the simulation is
compared to. **The other mills are evidence that the selected values are
typical**: their designs and dimensions differ, so they are not simulated
or used as validation cases, but they show that SAG_A's operating point and
angles sit inside the normal operating ranges of real SAG mills. The full
argument, joining plant data and literature, is in the Analysis
("Reference-mill argument").

**Calibration target (SAG_A, at SAG_A's operating point Jb 17 %, Jc 26 %,
9 rpm):**

| Target | SAG_A median | SAG_A interquartile range (box) | Range over the three mills (medians) |
|---|---|---|---|
| **Bulk** toe angle | **215 deg** | ~214.6-215.8 deg | 206-215 deg |
| Shoulder angle | **24.6 deg** | ~22-26.4 deg | 24.6-38.2 deg |

Friction and rolling resistance ([05](05_friction.md),
[06](06_rolling_resistance.md)) are tuned until the simulated steady-state
bulk toe and shoulder fall inside the SAG_A interquartile ranges.

**Measurement in simulation:** the plant reports the **bulk** toe, so the
simulated toe and shoulder are read from the boundary of the main charge
body: the time-averaged position-density contour (Boemer & Ponthot §2.3),
equivalent to Owen & Cleary's visual bulk toe / shoulder (§4.1). The liner
contact-force distribution (Owen & Cleary §4.3) is a cross-check, not the
primary measure, because it mainly detects the impact toe.

**Origin of the plant data** (stated by the author, 2026-10-20):
- **Jc and Jb** come from a plant model using load cells or bearing
  pressure together with a power model, calibrated against crash-stop and
  grind-out measurements made by the operation's personnel.
- **Toe and shoulder angles** are computed with the **Maleki-Moghaddam
  et al. (2013) charge-shape model** from the operating point (filling,
  speed) and the liner / lifter geometry. They are model outputs, not direct
  observations of the charge.

**Decision (2026-10-20):** the plant angles are taken as precise **bulk**
toe / shoulder angles (Maleki-Moghaddam's model is fitted to toe and
shoulder read from photographs of a model mill, i.e. bulk positions), and
the simulated angles are read with the bulk position-density contour.

**Power:** not a calibration target (decided 2026-10-18). Power is used
twice, neither time to choose parameters:
- the internal energy balance of every run ([16](16_validation_checks.md),
  V4);
- **one post-calibration check against the plant** (decided 2026-10-21,
  V15): the simulated power at the calibrated point, scaled from the slice
  to the full mill, is compared with SAG_A's plant power in the same
  operating window, and the **percentage deviation** is reported. No
  parameter is changed because of it. The analysis below records why plant
  power is not a calibration target and how the comparison is made.

## Evidence

| Source | What it says | Where | Verified |
|---|---|---|---|
| Owen & Cleary 2015 | Charge structure: head, shoulder, **bulk toe** and impact toe; bulk toe and shoulder estimated from standard particle visualisations, impact toe and head from streaks | §4.1, PDF p3-4 / j.21-22 | Yes |
| Owen & Cleary 2015 | Angles "given as an angle of anti-clockwise rotation from the 3 o'clock position"; Table 5 gives the four locations for 12 cases | §4.1 and Table 5, PDF p4 / j.22 | Yes |
| Owen & Cleary 2015 | Key positions can also be read from liner impact forces; correlation with the visual positions | §4.3, PDF p8 / j.26; §4.4, PDF p9 / j.27 | Yes |
| Boemer & Ponthot 2017 | "Position density limit": contour of the time-averaged position density separating the main charge from where particles are ~10x less likely; toe and shoulder read from it | §2.3, PDF p6 / j.58; Fig. 9, PDF p7 / j.59 | Yes |
| Boemer & Ponthot 2017 | Power 1311 / 1382 / 1391 W for mu = 0.25 / 0.5 / 0.75 (~6 % over a 3x change of friction); stiffness and restitution "only have a relatively small impact on the power draw"; power predicted within ~5 % | §3.1.4, PDF p10 / j.62; abstract, PDF p1 | Yes |
| Govender 2015 | Full-length Los Bronces SAG: 6.8 MW computed vs 7.1 MW reported; "we could match the power consumption exactly by changing the coefficient of restitution" | §3, PDF p14 / j.165 | Yes |
| Govender 2015 | Los Bronces SAG: 10.12 m x 4.7 m, 10 rpm, 31 % ore + 10 % balls by volume (41 % fill); "The charge shoulder is nearly at 2 o'clock and the toe is between 7 and 8 o'clock points on the mill circle" (Fig. 26); parameters "tuned ... to match the charge profile obtained by Rajamani et al. (2011)" | §3, PDF p12 / j.163; PDF p14 / j.165 | Yes |
| Morrell 1993 (via Toor et al. 2023) | Empirical toe angle theta_T = 2.5307 (1.2796 - J_t)(1 - exp(-19.42 (phi_c - phi))) + pi/2 (rad), phi_c = 0.35 (3.364 - J_t) away from centrifuging; coordinate system: 0 at 3 o'clock, counter-clockwise, toe in the third quadrant (= this convention); toe "only significantly affected by mill speeds" above 80 % CS or 40 % fill | Toor et al. 2023: Eq. (5)-(6), p9-10; Fig. 7 (coordinate system) and Fig. 8 (Morrell's lab data), p10 | Yes (secondary source; Morrell 1993 not in the library) |
| Pural & Boylu 2025 | Same toe equation (Morrell C model), Eq. (1) | §2.1, PDF p3 | Yes (their shoulder Eq. (3) is misprinted: it repeats Eq. (2)) |
| Maleki-Moghaddam et al. 2013 | Empirical relationships for toe, shoulder and impact point in industrial mills, correcting single-ball trajectory software (GMT); fitted to a 1 m transparent model mill with liners scaled from two industrial mills, 55 / 70 / 85 % CS, 10-30 % filling, angles read from photographs; checked against the Sarcheshmeh SAG mill liner (reported relative error 1.1 %) | Abstract (as indexed online) | **No** -- full text not yet read |
| Cleary & Morrison 2016 | Power = torque applied to the mill by all particle contacts x rotation speed; must balance collisional dissipation within a few % | §2, PDF p3 / j.77 | Yes |

## PPT

| Slide | Content |
|---|---|
| -- | **Naming:** the PPT labels the reference mill SAG_B and the other one SAG_A; swapped in these docs (reference = SAG_A), see [README](README.md) |
| 2 | Jb and Jc box plots for SAG_A/B/C (operating-range justification) |
| 3 | Toe and shoulder box plots for SAG_A/B/C; SAG_A toe 215 deg, shoulder 24.6 deg |
| 4 | Speed box plots; range 8.6-10 rpm; SAG_A 8.99 rpm |
| 31 | Simulation snapshot annotated 212 deg / 26.5 deg (read by eye; likely run with the friction bug, see [05](05_friction.md)) |

## Current state

No toe / shoulder measurement exists in code. The branch's `monitor.py` logs
the contact torque on the mill facets and the drive power P = -T_z * omega
every monitor interval.

## Analysis

### Plant values vs. Owen & Cleary in this convention

Owen's mill turns the other way (charge on the left), so their angles map to
this convention as theta' = 180 deg - theta:

| Feature | Owen Table 5, 12 cases (their convention) | In this convention | Owen 27.5 % fill, 175 mm lifters | SAG_A |
|---|---|---|---|---|
| Shoulder | 146-164 | **16-34** | 28-32 | **24.6** |
| Bulk toe | 306-324 | **216-234** | 226 | **215** |
| Impact toe | 306-338 | 202-234 | 208-210 | -- |

The SAG_A shoulder lies inside Owen's range. The SAG_A bulk toe (215 deg)
is just past the edge of Owen's bulk-toe range (216 deg, reached in Owen's
highest-fill case, 32.8 %), i.e. the plant charge extends ~10 deg further
round the mill than Owen's 27.5 % case. Plausible causes: different mill
(8.4 m, 56 lifters of 50-300 mm, 75 % critical, wide PSD vs. SAG_A's
10.71 m inside liners, 36 lifters of 395 mm, 69 %, binary charge). This is a quantitative check of the targets, not a
contradiction.

### Plant values vs. nominal SAG values

All angles in this convention (0 deg at 3 o'clock, counter-clockwise).
Morrell's toe is evaluated at SAG_A's operating point (J_t = 0.26,
phi = 0.692 -> phi_c = 1.086; the toe is practically speed-independent
below 80 % CS, so the 238 deg is unchanged from the earlier 40 ft estimate).

| Source | Mill / conditions | Shoulder (deg) | Bulk toe (deg) |
|---|---|---|---|
| **SAG_A (target)** | 36 ft x 19 ft (10.71 m inside liners), 36 lifters 395 mm / 35 deg, 9 rpm (69 % CS), Jc 26 % | **24.6** | **215** |
| SAG_B, SAG_C (plant, medians) | Similar SAG mills | up to 38.2 | 206-215 |
| Owen & Cleary 2015, Table 5 (DEM) | 8.4 m SAG, 75 % CS, 12 cases of fill and lifter height | 16-34 | 216-234 |
| Owen & Cleary 2015 (DEM) | Same, 27.5 % fill, 175 mm lifters | 28-32 | 226 |
| Govender 2015, Fig. 26 (DEM tuned to a measured profile) | Los Bronces SAG, 10.12 m, 10 rpm (~75 % CS), 41 % fill | ~30 ("nearly at 2 o'clock") | 210-240 ("between 7 and 8 o'clock") |
| Morrell 1993 correlation (lab mills) | J_t = 0.26, 69 % CS | -- | 238 |

**Shoulder:** 24.6 deg is inside Owen's DEM range (16-34 deg), a few degrees
below Owen's comparable case (28-32 deg) and Govender's Los Bronces
(~30 deg), and at the low end of the three plant mills. It is a nominal SAG
shoulder.

**Toe:** 215 deg lies inside the Los Bronces range (210-240 deg) and the
range of the three plant mills (206-215 deg), and at the edge of Owen's DEM
range (216 deg, reached at Owen's highest fill, 32.8 %). It is, however,
**higher than the correlations predict at 26 % fill**: Owen's comparable
case gives 226 deg and Morrell's correlation 238 deg. In Morrell's
correlation 215 deg corresponds to J_t ~ 0.42, i.e. SAG_A's toe looks like
that of a fuller mill (compare Govender's 41 % fill). That all three plant
mills report 206-215 deg suggests a systematic feature, not noise in one
mill: the plant angles come from Maleki-Moghaddam's model, which includes
the lifter / liner geometry, whereas Morrell's correlation depends on
filling and speed only; the difference is therefore partly model vs. model
and partly liner design. It is taken as given (Decision); the consequence for
calibration is that matching 215 deg at 26 % fill may require friction /
rolling resistance at the upper end of the literature range. If the
calibration cannot reach the toe within that range, this section is the
explanation to report.

### Reference-mill argument (plan, 2026-10-20)

The comparison above uses angles at different operating points, which a
reviewer can dismiss as coincidence. The argument is rebuilt as four
claims, each compared at matched conditions:

1. **SAG_A's operating point is typical.** Jc, Jb and % CS of SAG_A against
   SAG_A-E (box plots) and against usual SAG practice (total filling
   ~20-35 %, 70-80 % CS; "SAG mills typically operate at mill fillings below
   40 %", Toor et al. 2023, p10). Jc / Jb are trustworthy because they are
   measured (load cells / bearing pressure plus power model) and calibrated
   with crash stops / grind-outs.
2. **The target is SAG_A's angle at the simulated operating point**, not
   its all-time median: from the 10 s time series, keep steady periods with
   Jc, Jb and speed near the simulated values (e.g. Jc 26 +- 1.5 %,
   9 +- 0.2 rpm) and, since the simulated liners are new
   ([10](10_mill_geometry.md)), from the period just after a reline
   (reline dates needed). Target = median in that window; acceptance
   band = its interquartile range.
3. **The angle model is published and reproducible.** The angles come from
   Maleki-Moghaddam et al. (2013), an empirical model fitted to bulk toe /
   shoulder in a model mill and checked on an industrial SAG liner.
   Re-evaluating its equations with SAG_A's inputs and recovering the
   reported angles verifies the plant implementation.
   Note: regressing the plant toe on Jc / speed only reproduces the model's
   own sensitivities, so it is **not** used as physical evidence.
4. **Independent literature agrees at matched conditions.** One table in
   this convention with the fill, speed and liner of each entry: Morrell's
   correlation and lab data (trend and level), Owen & Cleary's DEM cases,
   Govender's Los Bronces, and published plant measurements if found.
   SAG_A is compared with entries at similar fill and speed; any remaining
   offset is quantified and explained (claim 3: liner geometry in Maleki,
   not in Morrell).

### Why the plant toe must be measured as a bulk toe in simulation

The bulk toe is where the main charge body meets the liner; the impact toe
is where the cataracting stream lands, usually further up. Comparing the
plant's bulk toe with a simulated impact toe would bias the calibration by
the 10-20 deg separating them in Owen's Table 5.

### How important is plant power?

Power is **not a determining support** for the material-parameter decisions,
for three reasons:

1. **Low sensitivity to the calibrated parameters.** In Boemer's validated
   mill a 3x change of friction (0.25 -> 0.75) moves power by ~6 %, and
   stiffness and restitution move it even less. Power mostly reflects charge
   mass and centre-of-mass position, which are fixed by Jc, Jb, density and
   speed, not by friction.
2. **Large comparison uncertainty.** A 0.6 m slice must be scaled to the
   full mill (P_mill ~ P_slice x L_eff / 0.6 m), and the plant figure
   includes motor / drive losses, conical ends, slurry and a real size
   distribution. These systematic differences (likely 10-20 %) exceed the
   ~6 % signal from friction, so power cannot discriminate between candidate
   parameter sets. Govender's full-length SAG model was 4 % off and could be
   "matched exactly" by changing restitution alone -- an example of power
   fitting a parameter it does not really constrain.
3. **Different designs.** With slightly different mills, cross-mill power
   ratios do not cancel the systematic factors either.

What power **is** used for: the **energy balance inside the simulation**
(V4) -- supplied energy (from the YADE contact torque) vs. collisional
dissipation. This needs no plant data and is a strong numerical-quality
check.

**Post-calibration plant power check (V15).** After calibration, and only
then:
- Simulated power: mean drive power P = -T_z omega of the slice over the
  steady window ([16](16_validation_checks.md), V7), scaled to the full mill
  as P_mill = P_slice x L_eff / L_slice, with L_slice = 0.6 m and L_eff
  SAG_A's length. Available: 19 ft = 5.79 m flange to flange (factor
  9.65), longer than Morrell's belly length inside liners, so it biases
  P_mill **high**; the vendor EGL replaces it if its definition is
  "inside liners". Cone ends: SAG_A has them, but the cone angle and
  trunnion diameter are not available, so P_mill is belly-only and biased
  **low** by the cone charge. The two biases partly offset by unknown
  amounts; V15 is therefore an order-of-magnitude check, reported with both
  caveats.
- Plant power: median SAG_A power in the same operating window used for the
  toe / shoulder target (claim 2: Jc, Jb, speed near the simulated point).
- Report the deviation (P_mill - P_plant) / P_plant in %, together with
  what the plant figure includes (motor / drive losses, slurry, real size
  distribution) so the sign of the expected bias is clear: the model has
  no drive losses, no slurry and a binary charge.
- Interpretation only: deviations within roughly +-20 % are consistent
  with the comparison uncertainty (Govender et al. 2015 obtained 6.8 vs
  7.1 MW, -4 %, for a full-length SAG model); a much larger deviation
  points to a gross error (fill, density, geometry) and is investigated,
  not tuned away.

## Verdict and how to defend it

"SAG_A is the reference mill: the operating point (9 rpm, Jb 17 %, Jc 26 %)
and the charge-shape targets were taken from it; the plant angles are
computed with the Maleki-Moghaddam et al. (2013) charge-shape model from the
measured operating point and liner geometry. SAG_B and SAG_C are evidence
that the selected values are typical: their operating data place SAG_A's
values within the normal ranges of SAG operation (speed 8.6-10 rpm, bulk toe
206-215 deg, shoulder 24.6-38.2 deg). Contact parameters were calibrated so the simulated
steady-state bulk toe and shoulder, read from the position-density contour
(Boemer & Ponthot 2017, §2.3), fall within the SAG_A interquartile ranges
(215 deg, 24.6 deg; counter-clockwise from 3 o'clock). The shoulder lies within the
ranges of DEM SAG studies (Owen & Cleary 2015, Table 5: 16-34 deg; Govender
et al. 2015: ~30 deg). The toe lies within the plant range of the three SAG
mills and of Govender's Los Bronces simulation (210-240 deg) and at the edge
of Owen & Cleary's range (216-234 deg); it is higher than Morrell's empirical
correlation predicts at 26 % fill (238 deg), a difference shared by all
three plant mills and attributed to the liner geometry included in the
Maleki-Moghaddam model. Power was not used as a calibration target, since it is
insensitive to the contact parameters (Boemer & Ponthot 2017, §3.1.4); it
was used to check the internal energy balance of the simulations and, after
calibration, compared with the reference mill's plant power as an
independent check (deviation reported in %)."

## Open items

To get (author, from plant data and reports):
- **Time series** (decided 2026-10-30: all five mills, at two levels of
  detail; period: the 2026 H1 campaign, which the design data describe,
  and in particular the weeks right after the reline, when the liners
  match the new-liner geometry):
  - **SAG_A** (targets and V15): 10 s resolution; toe, shoulder, Jc, Jb,
    speed, **power** (state motor input or shaft power), reline dates.
    At 10 s, 6 months is ~1.6 million rows.
  - **SAG_B-E** (typicality only): coarser is enough (1-5 min, or hourly
    medians); toe, shoulder, Jc, Jb, speed; power optional. Compared with
    SAG_A in dimensionless form (% of critical speed, J, angles), because
    SAG_D-E are 40 ft mills.
- **Mill design, SAG_A-E: received 2026-10-30** (`mill_dimensions.csv`,
  [10](10_mill_geometry.md); plates verified flat, LH from the inside
  shell; lengths flange to flange). Still open: SAG_A lifter top or base
  width; optionally SAG_A's EGL (V15); the plant's critical-speed
  definition. Cone geometry not available (V15 caveat).
- The Maleki-Moghaddam model inputs used at the plant (which liner geometry,
  updated with wear or not).

To do (Claude):
- Get Maleki-Moghaddam, Yahyaei & Banisi 2013 (Minerals Engineering 46-47,
  157-166, doi 10.1016/j.mineng.2013.04.013) into Zotero; verify its
  equations, validation errors and angle convention; implement it to
  reproduce SAG_A's angles (claim 3).
- Build the claim 1-4 analysis once the data arrive; search the literature
  for published plant toe / shoulder measurements (e.g. Burns et al. 2018,
  Lihir, cited by Toor et al. 2023) for claim 4.

- Zotero additions for this topic: see the checklist in [README](README.md) ("Pending Zotero additions"), plus Morrell
  1993 / 1996a if obtainable; verify Morrell's shoulder equation in a primary
  source before quoting a Morrell shoulder value.
- Implement bulk toe / shoulder extraction from the time-averaged position
  density (plus the liner-force cross-check).

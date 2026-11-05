# 15 -- Calibration targets (charge shape and power)

## Decision

**Angle convention (fixed 2026-10-18):** 0 deg at the **3 o'clock** position
(right side, +X in YADE), angles increasing **counter-clockwise**, mill
rotating **counter-clockwise** seen from +Z (positive angular velocity about
Z in YADE). The charge rises on the right: shoulder in the first quadrant
(~27 deg), toe in the third quadrant (~214 deg). Liner designs are
symmetric, so this orientation is a free choice in simulation.

**Role of the reference mills** (SAG_A-E). **SAG_A is the reference**: its operating point sets the
simulation and its charge-shape angles are the targets the simulation is
compared to. **The other mills are evidence that the selected values are
typical**: their designs and dimensions differ, so they are not simulated
or used as validation cases, but they show that SAG_A's operating point and
angles sit inside the normal operating ranges of real SAG mills. The full
argument, joining plant data and literature, is in the Analysis
("Reference-mill argument").

**Calibration target** (decided 2026-11-02, from the operational-data
analysis: SAG_A's first ~2 months after a reline, steady running data;
analysis and results in Zotero `bppm_dem_sm/data/operational_data`).
SAG_A's operating point = medians of its steady running data: **9.5 rpm
(73.0 % of critical), Jb 18.8 %, Jc 27.6 %**. Targets = toe / shoulder in
the window +-0.2 rpm, +-1.5 % Jc, +-0.5 % Jb around it (239 h):

| Target | SAG_A median | SAG_A interquartile range | P5-P95 | SAG_A-E medians (all usable data) |
|---|---|---|---|---|
| **Bulk** toe angle | **213.8 deg** | 213.4-214.5 deg | 212.9-215.4 deg | 208.6-215.4 deg |
| Shoulder angle | **26.6 deg** | 26.0-27.3 deg | 25.0-28.5 deg | 23.0-35.7 deg |

Cleaning (usable data): running (> 6 rpm, power > 0), power < 30,000 kW
(drops sensor error codes), model outputs present and not frozen (identical
for >= 30 min; 39 % of SAG_B's running time), >= 60 min after a start,
speed standard deviation <= 0.2 rpm over 30 min. Usable share of each
mill's ~2-month period (each 10 s sample counted once): SAG_A 67 %
(869 h), SAG_B 55 % (777 h), SAG_C 64 % (1,048 h), SAG_D 60 % (900 h),
SAG_E 29 % (417 h); the rest is mostly stopped time, start-up / unsteady
speed, and missing (SAG_D, SAG_E) or frozen (SAG_B) model outputs.

Friction and rolling resistance ([05](05_friction.md),
[06](06_rolling_resistance.md)) are tuned until the simulated steady-state
bulk toe and shoulder fall inside the acceptance band: **SAG_A's
interquartile range, widened to the simulation's own replicate scatter
(V12) if that is larger** (decided 2026-11-02). The toe IQR is only
1.1 deg wide -- finer than the 95 % confidence (+-1.8-2.5 deg) of the toe
measurements Maleki-Moghaddam et al. fitted their model to (§3.1.1), and
possibly finer than a DEM measurement resolves across seeds; the rule keeps
a correct model from failing on the plant model's smoothness without
changing the target values.

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
- **Liner geometry in those models** (author, 2026-11-01): the plant's
  models start each campaign with the **new-liner profiles** (the design
  data of [10](10_mill_geometry.md)) and update them for wear about three
  times per ~6-month campaign. The angles and the Jb / Jc of roughly the
  **first two months** after a reline are therefore computed with the same
  new-liner geometry that is simulated.

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
| Maleki-Moghaddam et al. 2013 | Empirical toe / shoulder / toe-departure / impact-point relationships correcting single-ball trajectory software (GMT); 1 m x 21.5 cm model mill with a transparent end, polyurethane liners scaled from industrial liners, 55 / 70 / 85 % CS, 10-30 % filling; angles from > 20 photographs per test | Abstract, PDF p1 / j.157; §2, PDF p3-4 | Yes (2026-11-04) |
| Maleki-Moghaddam et al. 2013 | Definitions: toe = "the highest point reached by the bulk of the charge in the toe region"; shoulder = "the point where the trajectories of the bulk particles near the lifters began to diverge from the mill shell"; angles "measured in degrees starting from the horizontal line passing the mill centre (i.e., 3 o'clock position) and moving counter clockwise" (= this convention); 95 % confidence of the measured toe +-2.5 / +-1.8 deg, shoulder +-4.0 / +-3.6 deg (two liners) | §3.1.1, §3.1.3, PDF p4-5 / j.160-161 | Yes |
| Maleki-Moghaddam et al. 2013 | Toe: theta_T = (-1.01 J_t - 0.156 (c_s* - c_s) + 158.5)(1 - exp(-0.69 (c_s* - c_s))) + 90 (Eq. 3.1; J_t, c_s in %); c_s* = max(c_s, A), A = -0.5 J_t - 0.914 H_l + 148.9, H_l = lifter height / (0.001 D) (Eqs. 3.2a-c); shoulder: theta_S = 90 - (theta_T - 90)(-0.7 J_t - 0.57 c_s + 0.28 l_a + 103.7)/100, l_a = lifter face angle (Eq. 3.4). "The effect of liner type on the position of toe ... was not found to be significant"; the shoulder depends on the liner | §3.1.1-3.1.3, PDF p4-5 / j.160-161 | Yes |
| Maleki-Moghaddam et al. 2013 | Validation on a 1:9 scaled model of the **Gol-E-Gohar iron ore AG mill**'s new liner in the same model mill: average relative error 1 %; shoulder, toe, toe departure and impact point predicted with relative errors of 5 %, 0.7 %, 2 % and 0.2 % | Abstract, PDF p1; §3.3, PDF p7; Conclusions, PDF p9 / j.165 | Yes |
| Doll 2013 | Cone ends: "5% extra power should be added" instead of Austin's factor (based on Barratt, Brodie & Pfeifer 1999); Austin's factor at 15 deg = 0.17; Morrell's cone term 8-13 % of cylinder power in 13 surveys (Table 2); example 3,374 kW at the motor vs 3,190 kW at the mill shell; Morrell no-load estimate 265 kW of 3,349 kW | PDF p3, p5, p6, Table 2 p9 | Yes (online PDF) |
| Cleary & Morrison 2016 | Power = torque applied to the mill by all particle contacts x rotation speed; must balance collisional dissipation within a few % | §2, PDF p3 / j.77 | Yes |

## PPT

| Slide | Content |
|---|---|
| -- | **Naming:** the PPT labels the reference mill SAG_B and the other one SAG_A; swapped in these docs (reference = SAG_A), see [README](README.md) |
| 2 | Jb and Jc box plots for SAG_A/B/C (operating-range justification) |
| 3 | Toe and shoulder box plots for SAG_A/B/C; SAG_A toe 215 deg, shoulder 24.6 deg (other campaign, whole period; **superseded** by the post-reline analysis) |
| 4 | Speed box plots; range 8.6-10 rpm; SAG_A 8.99 rpm |
| 31 | Simulation snapshot annotated 212 deg / 26.5 deg (read by eye; likely run with the friction bug, see [05](05_friction.md)) |

## Current state

No toe / shoulder measurement exists in code. `monitor.py` logs the contact
torque on the mill facets and the drive power P = -T_z * omega every monitor
interval.

## Analysis

### Plant values vs. Owen & Cleary in this convention

Owen's mill turns the other way (charge on the left), so their angles map to
this convention as theta' = 180 deg - theta:

| Feature | Owen Table 5, 12 cases (their convention) | In this convention | Owen 27.5 % fill, 175 mm lifters | SAG_A |
|---|---|---|---|---|
| Shoulder | 146-164 | **16-34** | 28-32 | **26.6** |
| Bulk toe | 306-324 | **216-234** | 226 | **213.8** |
| Impact toe | 306-338 | 202-234 | 208-210 | -- |

The SAG_A shoulder lies inside Owen's range, close to Owen's comparable
case. The SAG_A bulk toe (213.8 deg) is ~2 deg past the edge of Owen's
bulk-toe range (216 deg, reached in Owen's highest-fill case, 32.8 %), i.e.
the plant charge extends ~12 deg further round the mill than Owen's
27.5 % case at practically the same fill. Plausible causes: different mill
(8.4 m, 56 lifters of 50-300 mm, 75 % critical, wide PSD vs. SAG_A's
10.71 m inside liners, 36 lifters of 395 mm, 73 %, binary charge). This is a quantitative check of the targets, not a
contradiction.

### Plant values vs. nominal SAG values

All angles in this convention (0 deg at 3 o'clock, counter-clockwise).
Morrell's toe is evaluated at SAG_A's operating point (J_t = 0.276,
phi = 0.730 -> phi_c = 1.0808).

| Source | Mill / conditions | Shoulder (deg) | Bulk toe (deg) |
|---|---|---|---|
| **SAG_A (target)** | 36 ft x 19 ft (10.71 m inside liners), 36 lifters 395 mm / 35 deg, 9.5 rpm (73 % CS), Jb 18.8 %, Jc 27.6 % | **26.6** | **213.8** |
| SAG_B-E (plant, medians of usable data) | B, C: SAG_A's 36 ft design; D, E: 40 ft; 70-76 % CS, Jc 25-34 % | 23.0-35.7 | 208.6-215.4 |
| Owen & Cleary 2015, Table 5 (DEM) | 8.4 m SAG, 75 % CS, 12 cases of fill and lifter height | 16-34 | 216-234 |
| Owen & Cleary 2015 (DEM) | Same, 27.5 % fill, 175 mm lifters | 28-32 | 226 |
| Govender 2015, Fig. 26 (DEM tuned to a measured profile) | Los Bronces SAG, 10.12 m, 10 rpm (~75 % CS), 41 % fill | ~30 ("nearly at 2 o'clock") | 210-240 ("between 7 and 8 o'clock") |
| Morrell 1993 correlation (lab mills) | J_t = 0.276, 73 % CS | -- | 235 |

**Shoulder:** 26.6 deg is inside Owen's DEM range (16-34 deg), a little
below Owen's comparable case (28-32 deg) and Govender's Los Bronces
(~30 deg), and inside the range of the five plant mills (23.0-35.7 deg). It
is a nominal SAG shoulder.

**Toe:** 213.8 deg lies inside the Los Bronces range (210-240 deg) and the
range of the five plant mills (208.6-215.4 deg), and ~2 deg past the edge of
Owen's DEM range (216 deg, reached at Owen's highest fill, 32.8 %). It is,
however, **higher than the correlations predict at 27.6 % fill**: Owen's
comparable case gives 226 deg and Morrell's correlation 235 deg. In
Morrell's correlation 213.8 deg corresponds to J_t ~ 0.43, i.e. SAG_A's toe
looks like that of a fuller mill (compare Govender's 41 % fill). That all
five plant mills report 208.6-215.4 deg suggests a systematic feature, not
noise in one mill. The reason is the model behind the plant angles:
Maleki-Moghaddam's toe equation (Eq. 3.1), fitted to a model mill with
scaled industrial liners, gives ~214 deg at SAG_A's fill and speed, ~21 deg
below Morrell's correlation fitted to other laboratory data; the two
empirical correlations differ, and the plant values follow Maleki-Moghaddam
(claim 3: reproduced within 0.7 deg). The liner enters Maleki-Moghaddam's toe
only through the centrifuging speed (lifter height, Eq. 3.2c), and its own
data show no significant liner effect on the toe. It is taken as given (Decision); the consequence for
calibration is that matching 213.8 deg at 27.6 % fill may require friction /
rolling resistance at the upper end of the literature range. If the
calibration cannot reach the toe within that range, this section is the
explanation to report.

### Reference-mill argument (plan, 2026-10-20)

The comparison above uses angles at different operating points, which a
reviewer can dismiss as coincidence. The argument is rebuilt as four
claims, each compared at matched conditions:

1. **SAG_A's operating point is typical.** Jc, Jb and % CS of SAG_A against
   SAG_A-E (box plots; % CS computed here from rpm, [11](11_mill_speed.md))
   and against usual SAG practice: total filling ~20-35 % (Owen & Cleary's
   "usual operating range"; "SAG mills typically operate at mill fillings
   below 40 %", Toor et al. 2023, p10) and speed up to ~80 % CS ("most
   variable-speed drives do not go above 80% CS", ibid.). SAG_A's 73.0 % CS
   is in the middle of SAG_B-E (70.4-76.2 %) and close to the ~75 % of the
   DEM references. Jc / Jb are trustworthy because they are
   measured (load cells / bearing pressure plus power model) and calibrated
   with crash stops / grind-outs.
2. **The target is SAG_A's angle at the simulated operating point**, not
   its all-time median: from the 10 s time series, keep steady periods with
   Jc, Jb and speed near the simulated values (Jc 27.6 +- 1.5 %,
   Jb 18.8 +- 0.5 %, 9.5 +- 0.2 rpm; 239 h) and, since the simulated liners
   are new
   ([10](10_mill_geometry.md)), from the **first ~2 months after the
   reline**, while the plant's models still use the new-liner profiles
   (the period covered by the operational data). Target =
   median in that window; acceptance band = its interquartile range.
3. **The angle model is published and reproducible** (checked 2026-11-04).
   The angles come from Maleki-Moghaddam et al. (2013), an empirical model
   fitted to bulk toe / shoulder photographed in a model mill with scaled
   industrial liners (validated on a scaled model of the Gol-E-Gohar AG
   liner: toe 0.7 %, shoulder 5 % relative error). Its published equations
   with SAG_A's inputs (J_t 27.6 %, c_s 73 %, lifters 265 mm above the
   plate, 35 deg faces, D 10.71 m) give **toe 214.5 deg** (plant 213.8 deg,
   inside the IQR) and **shoulder 24.6 deg** (plant 26.6 deg); with the
   395 mm height from the shell, 216.2 / 23.7 deg. The plant angles
   therefore behave as Maleki-Moghaddam's model; the ~2 deg shoulder
   difference reflects the plant's exact inputs or local calibration.
   Note: regressing the plant toe on Jc / speed only reproduces the model's
   own sensitivities, so it is **not** used as physical evidence.
4. **Independent literature agrees at matched conditions.** One table in
   this convention with the fill, speed and liner of each entry: Morrell's
   correlation and lab data (trend and level), Owen & Cleary's DEM cases,
   Govender's Los Bronces, and published plant measurements if found.
   SAG_A is compared with entries at similar fill and speed; any remaining
   offset is quantified and explained (claim 3: the plant angles follow
   Maleki-Moghaddam's correlation, which sits ~21 deg below Morrell's for
   the toe).

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
   full mill (P_mill ~ P_slice x L / 0.6 m), and the plant figure
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
  steady window ([16](16_validation_checks.md), V7) -- the power delivered
  **to the charge**. Scaled to the full mill as
  **P_mill = P_slice x (L / 0.6 m) x (1 + c_cone)**:
  - L: SAG_A's belly length, **5.244 m** (17.21 ft), measured by the plant
    on the cylindrical section between the cone junctions -- the
    cylindrical length Morrell's model uses,
    the cones being added separately (c_cone). Factor 8.74.
  - c_cone = **0.05**, the cone-end allowance recommended by Doll (2013)
    ("5% extra power should be added", based on Barratt, Brodie & Pfeifer
    1999), since SAG_A's cone angle and trunnion diameter are not
    available. Sensitivity band 0.05-0.13: Morrell's explicit cone term in
    Doll's 13 surveys is 8-13 % of the cylinder power; Austin's published
    factor (0.17 at 15 deg) predicts high according to Doll.
- Plant power: median SAG_A power in the same operating window used for the
  toe / shoulder target (claim 2: Jc, Jb, speed near the simulated point),
  brought to the simulation's basis (power reaching the charge):
  **P_charge,plant = eta_d x (P_motor - P_NL)**
  - P_motor: plant (motor input) power, median in the window.
  - P_NL: no-load power -- motor power of the empty mill (bearings,
    windage, and the motor / drive losses at no load). Measured value if
    available (rarely, per Morrell); otherwise Morrell's empirical no-load
    estimate or ~8 % of gross (Doll's example: 265 of 3,349 kW).
  - eta_d: motor + drive efficiency for the load-dependent part; plant
    value if known, otherwise ~0.95 (Doll's example: 3,190 kW at the mill
    shell for 3,374 kW at the motor).
  - If the plant tag is shaft / pinion power, eta_d = 1 and P_NL is taken
    at that same point.
  - **SAG_A (2026-11-01):** the power tag is taken as **motor input**
    (not known); no measured no-load power and no efficiency data, so
    P_NL ~ 8 % of gross and eta_d ~ 0.95 are used as stated assumptions.
  - P_NL is subtracted at the motor before applying eta_d, so the drive
    losses contained in the no-load power are not counted twice.
  - Morrell's k = 1.26 is **not** applied: it corrects his analytical
    continuum model for losses it does not represent, whereas the DEM
    power is the mechanical power the simulated charge actually absorbs.
- **SAG_A values** (target window, 239 h): P_motor median 12,627 kW (IQR
  12,445-12,846), so P_charge,plant = 0.95 x (1 - 0.08) x 12,627 =
  **11,036 kW**.
- Deviation = (P_mill - P_charge,plant) / P_charge,plant, reported with the
  cone band (c_cone 0.05-0.13), the length used, and the eta_d / P_NL
  values and whether they are measured or assumed.
- Remaining differences, stated with the result: slurry and the real size
  distribution are not modelled (binary, dry charge).
- Interpretation only: deviations within roughly +-20 % are consistent
  with the comparison uncertainty (Govender et al. 2015 obtained 6.8 vs
  7.1 MW, -4 %, for a full-length SAG model); a much larger deviation
  points to a gross error (fill, density, geometry) and is investigated,
  not tuned away.

## Verdict and how to defend it

"SAG_A is the reference mill: the operating point (9.5 rpm, Jb 18.8 %,
Jc 27.6 %, medians of its steady running data in the first two months after
a reline)
and the charge-shape targets were taken from it; the plant angles are
computed with the Maleki-Moghaddam et al. (2013) charge-shape model from the
measured operating point and liner geometry. SAG_B and SAG_C, which share SAG_A's 36 ft design, are evidence that the
selected values are typical (medians: 72-76 % of critical speed, bulk toe
208.6-210.5 deg, shoulder 29.6-35.7 deg), and the 40 ft SAG_D and SAG_E extend the
comparison in dimensionless terms (% of critical speed, filling, angles). Contact parameters were calibrated so the simulated
steady-state bulk toe and shoulder, read from the position-density contour
(Boemer & Ponthot 2017, §2.3), fall within the SAG_A interquartile ranges
(widened to the replicate scatter where that is larger): toe 213.8 deg
(213.4-214.5), shoulder 26.6 deg (26.0-27.3), counter-clockwise from 3
o'clock. The shoulder lies within the
ranges of DEM SAG studies (Owen & Cleary 2015, Table 5: 16-34 deg; Govender
et al. 2015: ~30 deg). The toe lies within the plant range of the five SAG
mills and of Govender's Los Bronces simulation (210-240 deg) and ~2 deg
past Owen & Cleary's range (216-234 deg); it is higher than Morrell's
empirical correlation predicts at 27.6 % fill (235 deg), a difference shared
by all five plant mills: the plant angles follow Maleki-Moghaddam et al.'s
correlation (2013, Eqs. 3.1-3.4), which reproduces SAG_A's toe within
0.7 deg and its shoulder within 2 deg. Power was not used as a calibration target, since it is
insensitive to the contact parameters (Boemer & Ponthot 2017, §3.1.4); it
was used to check the internal energy balance of the simulations and, after
calibration, compared with the reference mill's plant power as an
independent check (deviation reported in %)."

## Open items

Plant data (author):
- **Time series: received 2026-11-02** -- one parquet file per mill in
  Zotero `bppm_dem_sm/data/operational_data/data`, each covering that
  mill's first ~2 months after a reline (new liners, 2025-2026 campaigns),
  10 s samples. Analysed with `operational_data_analysis.py` / `.ipynb`
  (Zotero `.../operational_data/analysis`); results (Markdown, CSV, plots)
  in `.../operational_data/results`. Plant data and results are kept out of
  the public repository.
- **Mill design, SAG_A-E: complete** (`mill_dimensions.csv`,
  [10](10_mill_geometry.md)). Cone geometry not available (V15 uses the
  5 % allowance).
- **Angle convention of the plant data** (author, 2026-11-03): the same as
  here -- 0 deg at 3 o'clock, counter-clockwise -- consistent with the
  values of all five mills (toe 208-215 deg, shoulder 23-36 deg). Rotation
  direction is not needed: the lifters are symmetric, so it only matters
  for converting angles, and none is required.
- **Jb / Jc basis** (confirmed by the author, 2026-11-03): Morrell's --
  bulk filling (including voids) of the cylinder inside the liners, lifters
  not subtracted; the basis of [12](12_charge_fill_and_particles.md).

To do (Claude):
- Claims 1-3 are done (operational-data analysis 2026-11-02; Maleki-Moghaddam
  reproduction 2026-11-04). Claim 4: search the literature for published
  plant toe / shoulder measurements (e.g. Burns et al. 2018, Lihir, cited by
  Toor et al. 2023).
- Morrell 1993 / 1996a only if obtainable (cited through Toor et al. and
  the SMC help file); verify Morrell's shoulder equation in a primary
  source before quoting a Morrell shoulder value.
- Implement bulk toe / shoulder extraction from the time-averaged position
  density (plus the liner-force cross-check).

## Pending code changes

| ID | Change | Current code | When |
|---|---|---|---|
| C15-1 | Bulk toe / shoulder from the time-averaged position-density contour (Boemer & Ponthot §2.3), in this angle convention; liner-force cross-check | None | Before calibration |
| C15-2 | Plant-data analysis: post-reline window, steady-period filter near the operating point, target medians / IQR; SAG_A-E typicality (claims 1-2) | **Done 2026-11-02** as `operational_data_analysis.py` / `.ipynb` in Zotero (kept out of the public repo with the data) | -- |
| C15-3 | V15 power comparison (P_mill vs P_charge,plant with the stated assumptions) | Monitor logs P only | After calibration |


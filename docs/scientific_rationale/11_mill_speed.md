# 11 -- Mill speed

## Decision

**9.5 rpm**, the median speed of **SAG_A, the reference mill**, over its
steady running data in the first ~2 months after a reline (operational-data
analysis, decided 2026-11-02), i.e. **73.0 % of critical speed** (SAG_A:
36 ft, diameter inside liners 10.7128 m, N_c = 13.01 rpm;
[10](10_mill_geometry.md)). SAG_A's interquartile range is 9.25-9.70 rpm
(P5-P95 7.97-9.90). SAG_B-E are evidence that this value is typical: their
medians are 70.4-76.2 % of critical (8.76-9.90 rpm). Rotation direction:
counter-clockwise seen from +Z (positive angular velocity in YADE), so the
charge rises on the +X side. Angles are measured counter-clockwise from the
3 o'clock position (+X); fixed 2026-10-18, see [15](15_calibration_targets.md).
The liner is symmetric, so the orientation is a free choice in simulation.

- The % of critical speed is quoted with N_c = 42.3 / sqrt(D - d), D inside
  liners.
- SAG_D and SAG_E are 40 ft mills (N_c ~12.4 rpm): their speeds are compared
  as % of critical, not rpm ([15](15_calibration_targets.md), claim 1).

## Evidence

| Source | What it says | Where | Verified |
|---|---|---|---|
| Owen & Cleary 2015 | "the same rotational speed of 11 rpm (75% critical speed)" for an 8.4 m SAG mill | §3, PDF p3 / j.21 | Yes |
| Govender 2015 | Los Bronces SAG 10.12 m "rotating at 10 rpm" (~75 % critical by the formula below) | §3, PDF p12 / j.163 | Yes |
| Boemer & Ponthot 2017 | Calibration at 70 % critical, validation at 70 % and 80 % | Table 1, PDF p3 / j.55 | Yes |
| Cleary 2001 (2D) | Behaviour vs. speed; at N <= 70-75 % power insensitive to lifter pattern and to particle shape | §5, PDF p7 / j.85; §10, PDF p29 / j.107; §11, PDF p34 / j.112 | Yes |
| Toor et al. 2023 | "Most variable-speed drives do not go above 80% CS, and SAG mills typically operate at mill fillings below 40%" | p10 | Yes |
| Kishida 2025 | Drum 120 mm at 15 rpm, i.e. ~12 % of critical (rolling / cascading regime, not cataracting) | Fig. 2(a), PDF p4 | Yes (figure read) |

## PPT

| Slide | Content |
|---|---|
| 4 | "Rangos de Velocidad de Rotacion (RPM) usuales: Valor Superior = 10 RPM, Valor Inferior = 8.6 RPM, Valor Seleccionado -> SAG_B = 8.99 RPM ~ 9 RPM" (plant data, box plots; the PPT's SAG_B is SAG_A in these docs) |
| 33, 34 | Snapshots "VELOCIDAD 8 RPM", "VELOCIDAD 6 RPM" |

## Current state

| Where | What |
|---|---|
| `scenario.py:116` | `speed_rpm = 9.5` (positive = counter-clockwise seen from +Z), also in `sag_slice_*.json` (C11-1, commit `5c194ab`) |
| `scenario.py:662-672, 765-799` | `critical_speed_rpm()` and `fraction_critical` use `mill.diameter_m`, now 10.7128 m (C10-1): the defaults report N_c = 13.01 rpm and 73.0 % of critical |
| Existing dataset (old 40 ft STL, run at 9 rpm) | Shell-contact particles move at ~8.7 rpm |

## Analysis

Critical speed N_c = 42.3 / sqrt(D - d) rpm (D, d in m), equivalent to
(60 / 2 pi) sqrt(g / (R - r)):

| Mill | D inside liners | N_c | Median speed (usable data) | % of critical |
|---|---|---|---|---|
| **SAG_A** | 10.713 m | 13.01 rpm | **9.50 rpm** | **73.0 %** |
| SAG_B | 10.727 m | 13.00 rpm | 9.90 rpm | 76.2 % |
| SAG_C | 10.727 m | 13.00 rpm | 9.41 rpm | 72.4 % |
| SAG_D | 11.732 m | 12.42 rpm | 8.91 rpm | 71.7 % |
| SAG_E | 11.692 m | 12.45 rpm | 8.76 rpm | 70.4 % |

(SAG_B and SAG_C: N_c = 13.00 rpm, as SAG_A. The old 40 ft STL gave 72.8 %;
superseded.)

Convention: with N_c = 42.3 / sqrt(D) (no ball-diameter correction, also
common in plant practice) 9.5 rpm is 73.5 % instead of 73.0 % -- a 0.5-point
difference, small next to the spread between the mills. Plant speeds are
recorded in rpm for all five mills, so % of critical is computed here with
one convention for all of them; the literature comparisons hold under
either: Owen & Cleary 74.7-75.4 %,
Govender 74.7-75.2 %.

SAG_A's 73.0 % sits in the middle of SAG_B-E (70.4-76.2 %), close to the
~75 % of the SAG DEM references (Owen & Cleary, Govender) and between
Boemer & Ponthot's calibration and validation speeds (70 and 80 %); it is
inside the usual SAG band (variable-speed drives rarely exceed 80 %,
Toor et al. 2023, p10). One revolution takes 6.32 s; the shell speed is
5.33 m/s.

Kishida's drum runs at ~12 % of critical, a different flow regime. The
surrogate method is transferable, but time scales must be compared in
**revolutions**, not seconds ([14](14_dataset_runs_and_recording.md)).

## Verdict and how to defend it

"The mill turns at 9.5 rpm, the median steady operating speed of SAG_A,
the reference mill, in the first two months after a reline -- 73 % of its
critical speed (10.71 m inside liners). The four other mills operate at
70-76 % of critical, and the value matches the ~75 % of the SAG DEM studies
of Owen & Cleary and Govender et al."

## Pending code changes

| ID | Change | Current code | When |
|---|---|---|---|
| C11-1 | Default `speed_rpm = 9.5` (SAG_A median) in `MillGeometry` and the scenario JSONs | Done (`5c194ab`) | Before calibration |

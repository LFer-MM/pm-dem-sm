# 10 -- Mill geometry (slice, lifters, diameter, end walls)

## Decision

Decided 2026-10-22.

- **Mill design: SAG_A's own design, with new (unworn) liners.** Diameter,
  lifter rows, lifter height, base / top width and face angle are taken from
  the mill reports. The same data are collected for SAG_A-E to show that
  SAG_A's design is typical (as done for the operating point in
  [15](15_calibration_targets.md)); an average "generic" mill is not used,
  because the plant toe / shoulder targets are computed for SAG_A's liner.
- **SAG_A's design (received 2026-10-30, campaign start 2026 H1, new
  liners):** 36 ft x 19 ft (inside shell; length to be confirmed as belly
  length inside liners). Shell liner of **36 lifters** (height 395 mm
  measured from the inside shell, face angle 35 deg) alternating with **36
  flat plates** 130 mm thick (verified by the author 2026-10-30: SAG_A-D
  have flat plates, no low lifters). The lifters therefore stand
  395 - 130 = **265 mm above the plate surface**. Diameter inside liners
  **D = 10.9728 - 2 x 0.130 = 10.7128 m**. Full table and the SAG_A-E
  comparison in Analysis.
- **Geometry is generated in code** from those parameters (the author's mill
  generator, to be added to the repo), not read from an input STL file. The
  old STL (`sag_mill_40ft_m.stl`, PPT slide 1: 40 ft, 30 lifters, 11.8375 m)
  is **not SAG_A** and is retired.
- **Slice depth 0.6 m** (was 0.375 m): 4.3 diameters of the 139.7 mm balls,
  the same depth as Owen & Cleary's SAG slice, and 10.4 % of SAG_A's 19 ft
  length -- Govender's 10 % as well (Analysis).
- **End walls frictionless** (baseline). The liner-friction case is a
  one-off sensitivity check (V11), compared on toe, shoulder, power **and
  segregation**. Periodic axial boundaries are not used.
- Every diameter-based quantity uses SAG_A's diameter inside liners,
  10.7128 m: critical speed 13.01 rpm, Lacey cell 0.04 D = 0.4285 m.

## Evidence

| Source | What it says | Where | Verified |
|---|---|---|---|
| Plant design data (`mill_dimensions.csv`, Zotero `bppm_dem_sm/data/mill_dimensions`, attachment `ZBFFQY29`) | SAG_A-E at the start of the 2026 H1 campaign (new liners): diameter inside shell (ft), length (ft), lifter rows LQ, lifter height LH, lifter angle LA, plate rows PQ, plate thickness PH, plate angle PA | CSV, columns as named | Yes (read 2026-10-30) |
| Owen & Cleary 2015 | "a 3D slice of a generic SAG mill": shell inner diameter 8.4 m, slice length 0.6 m "along the cylindrical belly", 56 lifters, base width 320 mm, height 50-300 mm, face angle 15-25 deg; how the slice ends are treated is not stated | §3 and Table 1, PDF p2 / j.20 | Yes |
| Owen & Cleary 2015 | Charge: balls 145 mm down to 30 mm, rocks 200 mm down to 25 mm (Table 3) -> slice = 4.1 top-ball diameters, 3.0 top-rock diameters | §3 and Table 3, PDF p3 / j.21 | Yes |
| Govender 2015 | "Fig. 30(b) depicts the charge profile for a slice of 10% of length. We notice that the pattern is very similar to the full length of the mill. Clearly the effect of the axial direction cannot just be neglected as the 2D case cannot fully reproduce the dynamics." | §3.1, PDF p16 / j.167 | Yes |
| Govender 2015 | Los Bronces SAG 10.12 m x 4.7 m, "64 rows of high low lifters"; balls 12.4 cm top size, ore 15.0 cm top size (Table 7) -> a 10 % slice (0.47 m) = 3.8 top-ball / 3.1 top-ore diameters | §3, PDF p12-14 / j.163-165 | Yes |
| Govender 2015 | ~68 % of power enters through lifters, ~18 % through the shell | §3, PDF p14 / j.165 | Yes |
| Boemer & Ponthot 2017 | Lab mill 800 x 400 mm "closed by flat end walls and a window of transparent tempered glass"; modelled with "two planes representing the flat axial end walls"; the charge in contact with the glass end wall "is obviously lifted a little higher than the charge at the center of the mill due to the contact with the end wall" | §2.1, PDF p2 / j.54; §2.2.1, PDF p3 / j.55; §3.2, PDF p11 / j.63 | Yes |
| Kishida 2025 | Drums with real end walls: large particles accumulate "near the end walls" (axial segregation, part of their result) | §3, PDF p8-9 | Yes |
| Cleary 2001 (2D) | Lifter wear (height / face angle) changes cataracting, toe and power; at N <= 70 % critical power "highly insensitive to the lifter pattern" | §7-8 and §11, PDF p16-21, p34 / j.94-99, j.112 | Yes |

## PPT

| Slide | Content |
|---|---|
| 1 | "Diametro Total = 40 ft = 12.192 m (medicion exterior molino real)"; "Diametro Interno = 11,837.5 mm (sin grosor cilindro)"; "Cantidad de Elevadores = 30 elevadores (STL y real)"; "Profundidad del Slice = 375 mm (del STL)"; "Volumen Interno = 39.4693 m^3 (STL via MeshMixer)"; "Diametro Efectivo = 11.576 m (calculado con volumen STL)"; bounding box X = 11.8227, Y = 11.8375, Z = 0.375 m. **Old 40 ft STL, not SAG_A: superseded by SAG_A's design data** |
| 21 | Lacey cell_size = 0.04 D = 0.04 x 11.83 = 0.4732 m (old STL; SAG_A: 0.4285 m) |
| 31 | Snapshot of the STL slice with lifters visible |

## Current state

| Where | What |
|---|---|
| `config.py:68` | `SAGMILL_STL_PATH = "sag_mill_40ft_m.stl"`; the file is not in the repo |
| `config.py:72` | `MILL_DIAMETER_M = 11.0` -- **wrong**: it is the default `MillGeometry.diameter_m` (`scenario.py:76`), which sizes the fill boxes and derived checks, and it sets `MetricsOptions.cell_size` (`config.py:209`, 0.44 m instead of SAG_A's 0.4285 m) |
| `configs/pipeline_example.json:32` | `cell_size = 0.4732` (old 40 ft STL; SAG_A: 0.4285) |
| `scenario.py:77` | `depth_m = 0.375` |
| `scenario.py:85` | `end_walls = "liner"` (default); `"frictionless"` available (`run_simulation.py:145-154`: friction 0, restitution copied from the liner) |
| `scenario.py:467-470` | Warns when the slice is < 4 large diameters deep with frictional end walls |
| `scenario.py:53-70`, `stl.py` | Parametric shell + trapezoidal lifters exist as an alternative source (`source = "parametric"`) |
| Existing dataset | Particle centres reach 5.88 m from the axis, consistent with the old 40 ft STL (inside radius 5.92 m), not with SAG_A |

## Analysis

### Slice depth: why 0.6 m

- Wall effects (layering of particles against a flat wall, wall contacts)
  scale with particle size, so the meaningful criterion is the slice depth
  in **largest-particle diameters**; Govender's 10 % of length is an
  empirical observation ("very similar to the full length"), not a rule.
- The two reference slices are both ~3-4 largest-particle diameters deep:
  Owen & Cleary 0.6 m = 4.1 top-ball / 3.0 top-rock diameters; Govender's
  10 % slice 0.47 m = 3.8 / 3.1.
- 0.6 m here = **4.3 ball diameters**: the same absolute depth as Owen &
  Cleary and a larger ratio under either reading. This matters more here
  because every ball is at the top size, whereas in their charges the top
  size is a minority of the balls.
- SAG_A is 19 ft = 5.79 m long, so 0.6 m is **10.4 % of the length**:
  the slice also meets Govender's 10 %.
- Side benefits: the Lacey cell (0.4285 m, [14](14_dataset_runs_and_recording.md))
  fits inside the slice, which it did not at 0.375 m; the code's own
  thin-slice warning no longer applies.
- Cost: ~1.7 h per calibration run, ~15 h for the 9-run grid
  ([05](05_friction.md)); particle counts in
  [12](12_charge_fill_and_particles.md).

### SAG_A-E design data and why SAG_A is typical

Campaign start, 2026 H1, new liners. Lifter height is measured from the
inside shell; plates are flat (SAG_A-D). D inside liners = D inside shell
- 2 x plate thickness; N_c = 42.3 / sqrt(D - d_ball).

| Mill | D shell | L | Lifters (rows / height from shell / angle) | Lifter above plate | Plates (rows / thickness) | D inside liners | N_c | Slice 0.6 m / L |
|---|---|---|---|---|---|---|---|---|
| **SAG_A** | **36 ft (10.973 m)** | **19 ft (5.791 m)** | **36 / 395 mm / 35 deg** | **265 mm** | **36 / 130 mm** | **10.713 m** | **13.01 rpm** | **10.4 %** |
| SAG_B | 36 ft | 19 ft | 36 / 396 mm / 35 deg | 273 mm | 36 / 123 mm | 10.727 m | 13.00 rpm | 10.4 % |
| SAG_C | 36 ft | 19 ft | 30 / 387 mm / 35 deg | 264 mm | 30 / 123 mm | 10.727 m | 13.00 rpm | 10.4 % |
| SAG_D | 40 ft (12.192 m) | 29 ft (8.839 m) | 30 / 530 mm / 34 deg | 300 mm | 30 / 230 mm | 11.732 m | 12.42 rpm | 6.8 % |
| SAG_E | 40 ft | 26 ft (7.925 m) | 27 / 458 mm / 30 deg | 208 mm | 27 / 250 mm (*) | 11.692 m | 12.45 rpm | 7.6 % |

(*) SAG_E actually has a high-low liner; its low lifters are entered as a
250 mm plate. SAG_E is only used for comparison and is not simulated, so
this simplification does not affect any model input.

- SAG_A, B and C share one design (36 x 19 ft, ~390-395 mm lifters at
  35 deg; C has 30 instead of 36 rows). SAG_D and E are larger 40 ft mills
  with taller lifters and plates. SAG_A is therefore representative of the
  36 ft group, and D / E show the range across mill sizes.
- Comparisons of operating data between the groups use dimensionless
  quantities (% of critical speed, J, angles), not rpm
  ([11](11_mill_speed.md), [15](15_calibration_targets.md)).
- Not yet in the data: lifter and plate widths (or the liner drawing),
  needed by the generator.

### End walls: frictionless, and what it leaves behind

- In the mill's belly, a slice has charge on both sides, not a wall. A
  frictionless wall confines the particles without adding wall shear that
  does not exist there. With liner-friction walls the end walls would carry
  the calibrated mu_w ([05](05_friction.md)), possibly 0.7-0.9, and add
  artificial lift to the shoulder being calibrated; Boemer & Ponthot saw the
  charge lifted at their (glass) end wall.
- What remains with frictionless walls: normal contacts, the rolling
  resistance moment ([06](06_rolling_resistance.md)), and particle layering
  next to a flat wall (local, ~1-2 diameters). V11 bounds the friction part.
- **Consequence for segregation metrics:** any segregation that develops
  next to the end walls is an artefact here -- the real belly has no walls
  -- unlike Kishida's drums, where it is physical. Segregation results must
  report the near-wall layers separately from the slice centre (or show that
  they agree); see [14](14_dataset_runs_and_recording.md).

### Periodic boundaries: not used

- YADE supports periodic cells, but a rotating facet shell in a periodic
  cell leaked particles even when static (tested on yadedaily 20260115), so
  it would need development with no guarantee of success.
- Moving particles from one face to the other by script is not equivalent:
  particles near each face would have no neighbours across it, leaving an
  unconfined layer.
- Owen & Cleary do not state their slice boundary treatment in this paper;
  no source in the library documents periodic slice ends, so the choice is
  not presented as literature practice.

### Diameter

Use SAG_A's **diameter inside liners** (Morrell's D: inside shell minus
2 x liner plate thickness = 10.7128 m) everywhere. The PPT's "effective"
11.576 m (a volume-equivalent diameter of the old 40 ft STL, lifters
subtracted) is not used; the word "effective" is avoided because its
meaning varies ([12](12_charge_fill_and_particles.md)).

### Geometry source

Generating the mill from the report parameters makes the geometry
documented and reproducible (the parameters go into each run manifest) and
removes the dependency on an external file. With new liners, the plant
target window for toe / shoulder must come from the period just after a
reline ([15](15_calibration_targets.md), claim 2).

## Verdict and how to defend it

"The mill is modelled as a 0.6 m slice of SAG_A, generated from its design
data with new liners (36 ft x 19 ft, 36 lifters of 395 mm at 35 deg
alternating with 130 mm plates; 10.71 m inside liners); SAG_B and SAG_C
share this design and SAG_D-E show the range for larger 40 ft mills. Slice models are standard for SAG mills: Owen & Cleary (2015) use a
0.6 m slice of an 8.4 m mill, and a slice of ~10 % of the length reproduces
the full-mill charge profile whereas a 2D model does not (Govender et al.
2015, §3.1). Our slice is 4.3 ball diameters deep, at least as deep as
theirs relative to the largest particles, and 10.4 % of SAG_A's length. The end walls are frictionless,
so they confine the slice without adding wall shear; a run with frictional
end walls bounds their effect, and segregation next to the end walls is
reported separately because it has no counterpart in the real mill."

## Open items / validation

- Design data SAG_A-E received (CSV, 2026-10-30; plates verified flat, LH
  from the inside shell). Still open: lifter and plate widths (or the liner
  drawing); confirm the CSV length is the belly length inside liners; cone
  geometry (cone angle, trunnion diameter) for the power check V15. The
  Zotero CSV still has the `pa_deg` column; replace it with the edited
  version.
- Add the author's mill generator to the repo as the primary geometry
  source; record its parameters (and a hash of the generated mesh) in each
  run manifest; cross-check the old STL against it.
- V11 end-wall check ([16](16_validation_checks.md)): frictionless vs liner
  friction, 3 revolutions each; compare toe, shoulder, power and
  segregation.

## Pending code changes

| ID | Change | Current code | When |
|---|---|---|---|
| C10-1 | `MILL_DIAMETER_M` = SAG_A diameter inside liners, 10.7128 m | 11.0 (`config.py:72`) | Before any production run |
| C10-2 | Default `end_walls = "frictionless"` | `"liner"` (`scenario.py:85`) | Before calibration |
| C10-3 | Default `depth_m = 0.6` | 0.375 (`scenario.py:77`) | Before calibration |
| C10-4 | Add the author's mill generator as the primary geometry source (SAG_A: 36 lifters, 395 mm from the inside shell, alternating with 36 flat 130 mm plates); geometry parameters in the run manifest; drop the STL input and retire `sag_mill_40ft_m.stl` | `source = "stl"` with an external file | Before calibration |

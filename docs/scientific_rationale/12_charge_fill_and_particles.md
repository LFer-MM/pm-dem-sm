# 12 -- Charge: fill level, particle sizes, packing and counts

## Decision

Decided 2026-10-23.

| Quantity | Value | Basis |
|---|---|---|
| Ball filling Jb | **17 %** | SAG_A, the reference mill (slide 2); SAG_B / SAG_C show it is typical (15.2-18.5 %); to confirm in the post-reline window (author to-do A1) |
| Total filling Jc | **26 %** | SAG_A (slide 2); SAG_B / SAG_C typical (24.9-35.1 %); same confirmation |
| Ball diameter | **0.1397 m** (5.5 in) | plant practice (slide 5) |
| Rock diameter | **0.06985 m** (2.75 in) | 2:1 size ratio (slide 6), as Kishida |
| Filling convention | **Morrell's**: J = bulk charge volume (incl. voids) / pi/4 D^2 L of the cylindrical section, with **D = diameter inside liners** (inside shell minus 2 x liner plate thickness); lifter volume **not** subtracted | SMC gross power calculator (Morrell model); plant Jc / Jb come from a model of this kind |
| How the counts are set | **Simulated grind-out and crash stop** (below), matching the charge **surface**, not an assumed packing | this doc |
| Packing fraction phi | a **result** of that procedure, not an input | -- |

**Diameter naming.** "Effective diameter" is not used: it means the
inside-liner diameter in some documents and a volume-equivalent diameter
in others (PPT slide 1: 11.576 m for the old 40 ft STL, lifters subtracted). These docs say:

| Name | Value now | Use |
|---|---|---|
| D inside liners (Morrell's D) | **10.7128 m** = 10.9728 - 2 x 0.130 (SAG_A, [10](10_mill_geometry.md); provisional until the plate re-check) | J, critical speed, Lacey cell, Morrell comparisons |
| D inside shell and liner plate thickness t | 36 ft = 10.9728 m and 130 mm (SAG_A design data) | the two inputs of Morrell's model; D inside liners = D inside shell - 2 t |
| Volume-equivalent diameter | 11.576 m (old 40 ft STL) | not used |

**Procedure for the counts (simulated grind-out and crash stop).** Both
stages run in the 0.6 m slice ([10](10_mill_geometry.md)) with damping 0
([04](04_numerical_damping.md), [13](13_initial_conditions.md)):

1. **Ball stage (grind-out analogue):** balls only; run 2-3 revolutions at
   9 rpm, stop, settle; measure J. Adjust the ball count until J = Jb.
2. **Full stage (crash-stop analogue):** add rocks **mixed** with the
   balls; run 2-3 revolutions (operating mixing / segregation state), stop,
   settle; measure J. Adjust the rock count until J = Jc.
3. **Measuring J:** the stopped surface is not flat, so J is the area of
   the smooth inside-liner circle lying below the measured surface profile
   (top particle per column across the section, integrated), divided by
   pi/4 D^2. Particles cannot occupy the lifters, so the lifters under the
   bed are excluded automatically -- exactly as in the plant convention.
4. Tolerance J within +-0.5 points; 3 seeds; report counts, J and the
   resulting phi (solid volume / bulk volume between the lifters) with
   their spread. Surface height is nearly proportional to the count, so
   2-3 iterations per stage are expected (~1 h each).
5. Run provisionally now, then again after calibration (friction and
   rolling resistance change the packing) and once SAG_A's design (A2)
   is in.

**Provisional counts** (SAG_A, 0.6 m slice, D inside liners 10.7128 m,
cylinder 54.08 m^3, phi = 0.5617 from the PPT): **at most ~3,620 balls +
~15,320 rocks** (~18,940), before removing the lifters and plates under
each bed (~13 of 36 lifters under the 26 % bed, ~11 under the 17 % ball
bed), which lowers them by a few percent; the lifter widths needed to
compute that are not yet in the design data. Estimates only, until the
procedure above runs; a mixed charge will probably take somewhat more rock
than a separate-bulk estimate.

## Evidence

| Source | What it says | Where | Verified |
|---|---|---|---|
| SMC Testing, gross power calculator help (Morrell model) | "This model uses the equations from Morrell's 1993 PhD thesis"; "The mill diameter input relates to the inside-shell dimension. The model actually requires the inside liner diameter and hence the liner thickness must also be input"; liner thickness drawn as the **plate** thickness between lifters (Fig. 4); "The ball filling relates to the volume (including voids) that the balls occupy when the mill is completely ground out ... expressed as a % of the total mill volume ... for the cylindrical part of the mill only"; "In SAG mills the total filling relates to the combined rock and ball volume (including voids)"; total filling measured at a crash stop, ball filling after a grind-out | p1-2; Fig. 4, p5 | Yes (online PDF, figure rendered) |
| Toor et al. 2023 | Morrell C-model inputs: "D Diameter inside liners", "L Belly length inside liners", "Jt Total fractional mill filling of cylindrical section", "JB Ball fractional mill filling of cylindrical section" | p5-6 | Yes |
| Hilden, Powell & Yahyaei 2021 | Classic filling formulas assume a smooth cylinder and ignore the cone ends and the volume occupied by lifters; new equations for load volume including those; survey of a non-level surface profile | Abstract / highlights (Minerals Engineering 160, 106638) | **No** -- abstract and highlights via search only; full text paywalled |
| Owen & Cleary 2015 | SAG fill levels 20-35 % studied ("the majority of the usual operating range for SAG mills"); constant 6 % ball charge, fill varied through rock | §3, PDF p3 / j.21; Table 2, PDF p3 | Yes |
| Govender 2015 | Los Bronces SAG charge "31% ore and 10% balls by volume" | §3, PDF p12 / j.163 | Yes |
| Cleary 2001 (2D) | Filling above 25-30 % gives significantly lower specific power; ball fraction has little effect for rock fractions >= 20 % by volume | §11, PDF p34 / j.112 | Yes |
| Kishida 2025 | Binary system with **2:1 size ratio** (0.5 / 0.25 mm), 1 M large + 2 M small (small = 20 % of solid volume) | Fig. 2(b), PDF p4 | Yes |
| Shi & Zhang 2008 | Monosize loose random packing 0.565-0.578 (Table 1); bimodal packing with d2/d1 = 2.0: 0.581-0.600 depending on number fraction (Table 3): a 2:1 mixture packs denser than its parts | Table 1, PDF p4 / j.624; Table 3, PDF p5 / j.625 | Yes |
| Brouwers 2024 | For size ratio u = 2 the maximum binary packing occurs at a large-particle volume fraction c_L between 0.7 and 0.8 | PDF p29 | Yes |

## PPT

| Slide | Content |
|---|---|
| 1 | "Diametro Efectivo = 11.576 m (calculado con volumen STL)" -- a volume-equivalent diameter, **not** Morrell's D |
| 2 | Plant ranges: Jb 15.2-18.5 % (SAG_A 16.8 % ~ 17 %); Jc 24.9-35.1 % (SAG_A 25.9 % ~ 26 %) |
| 5 | 5.5 in steel balls used in SAG_A/B/C "a lo largo de multiples campanas"; recent trial of 6 in balls in SAG_A/B, not confirmed as permanent |
| 6 | "2.75 pulgadas -> Ratio 2:1"; "relacion 2:1, 3:1, superior 5:1 es ineficiente y 2:1 permite reducir cantidad de particulas" (no citation) |
| 7 | Counts with phi = 1.0: 4,696 balls, 19,888 rocks (text divides the rock volume by the ball volume -- typo; numbers use 1.786e-4 m^3) |
| 13-15 | Packing-factor simulation: random mix of 19,888 rocks + 4,696 balls, damping 0.2 -> 0.0, "Ingresado + Asentado" and "Rotado (10) + Asentado"; bed height at 26 %: Y26% = 3.6826 m; Ydiff = 2.23615 m. The "rotate then settle" idea is kept; damping and the separate-bulk counting are replaced |
| 16 | Final: phi = 0.5617 -> 2,638 balls + 11,171 rocks = 13,809 (0.375 m slice, net STL volume; superseded) |

## Current state

| Where | What |
|---|---|
| `config.py:75, 79` | `ROCK_COUNT = 19888`, `BALL_COUNT = 4696`: the phi = 1.0 numbers of slide 7 for the 0.375 m slice -- superseded |
| `config.py:77, 82` | `ROCK_DIAM_M = 0.06985`, `BALL_DIAM_M = 0.1397` -- match |
| `scenario.py:382-393` | `fill_fraction(packing=0.6)`: gross cylinder pi R^2 L (Morrell-consistent denominator) but an **assumed** packing 0.6 and the solid volume of all particles, so it reports J of a lifter-free, perfectly packed charge |
| `scenario.py:247` | Species counts are scenario inputs (no derivation from Jc / Jb) |
| Existing `sic_dataset_20s_dt0p0001` | 11,581 rocks with **r = 0.0381 m** (3 in) + 3,195 balls -- matches neither the slides nor this procedure |

## Analysis

### Filling convention: why Morrell's, lifters included

J is a measurement convention, not "the volume available to the charge".
It is measured on site from the charge surface and the inside-liner
diameter with circle geometry, which needs no lifter drawings and does not
change as lifters wear; Morrell's model is calibrated on data measured that
way, and the plant's Jc / Jb come from a model of that kind. A J of 26 %
therefore fixes **where the charge surface lies** (the height of a 26 %
segment of the smooth cylinder). The real charge volume is smaller by the
lifters under the bed: at rest the 26 % bed covers ~37 % of the
circumference, ~13 of SAG_A's 36 lifters (~11 under the 17 % ball bed). Matching the surface in the simulation reproduces this
without computing lifter volumes.

### Mixed rather than layered

A 2:1 mixture packs denser than its parts (Shi & Zhang Tables 1 and 3), so
more rock fits under the same surface when mixed. The plant's crash stop
freezes an operating, mixed charge; layering rock over balls (the old
Jc - Jb separate-bulk split) would give too little rock. Running a few
revolutions before stopping also gives the charge its operating mixing /
segregation state, as the PPT's "Rotado + Asentado" intended.

### Packing

phi is now an outcome. The PPT's 0.5617 (0.375 m slice, damping 0.2 -> 0)
is below bulk binary values (~0.58-0.62), as expected near walls and
lifters; the deeper 0.6 m slice and the damping-free settle will change it.
The ball volume fraction of the solids (~0.64 in the provisional counts) is
near the densest composition for u = 2 (c_L ~ 0.7-0.8, Brouwers).

### Sizes

The 2:1 ratio matches Kishida and keeps the count tractable. Owen & Cleary
and Govender use full PSDs; the binary simplification is a project choice
needed for the binary-mixing surrogate.

### Fill check

Jc = 26 % is inside Owen's 20-35 % and the plant range; Cleary 2001 notes
specific power falls above 25-30 %.

## Verdict and how to defend it

"The charge reproduces SAG_A, the reference mill: Jb = 17 %, Jc = 26 %
(plant data; SAG_B and SAG_C show these fillings are typical). Fillings
follow Morrell's convention -- bulk volume as a fraction of the cylindrical
section at the inside-liner diameter, lifters not subtracted -- the
convention of the plant's filling model. Particle numbers were set by a
simulated grind-out and crash stop: the ball count until the stopped ball
bed reached Jb, then the rock count, mixed with the balls, until the stopped
charge reached Jc, J being measured from the stopped surface profile as in
plant practice. The packing fraction is a result of this procedure (phi =
X, spread over 3 seeds); it is below bulk binary packings (0.58-0.62, Shi &
Zhang 2008) because of the walls and lifters."

## Open items / validation

- Run the procedure provisionally (current STL, 0.6 m), after calibration,
  and with SAG_A's report geometry; record counts, J, phi and seeds in the
  scenario.
- Confirm Jb / Jc in the post-reline window (A1) and SAG_A's inside-shell
  diameter and liner plate thickness (A2).
- Regenerate the datasets (the existing one uses 3 in rock and other
  counts).

## Pending code changes

| ID | Change | Current code | When |
|---|---|---|---|
| C12-1 | Remove the hard-coded `ROCK_COUNT` / `BALL_COUNT`; counts come from the scenario, produced by C12-3 | phi = 1.0 constants (`config.py:75, 79`) | Before calibration |
| C12-2 | `fill_fraction` measured from the settled surface profile (Morrell convention), not from an assumed packing | `scenario.py:382-393` | With C12-3 |
| C12-3 | Grind-out / crash-stop script: ball stage then mixed stage, iterate counts to Jb / Jc +-0.5, 3 seeds, writes counts and phi to the scenario | Slides 13-15 procedure (manual, with damping) | Before calibration |

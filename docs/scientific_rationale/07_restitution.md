# 07 -- Coefficient of restitution

## Decision

| Pair | e |
|---|---|
| rock-rock | **0.3** |
| rock-steel | **0.5** |
| steel-steel | **0.8** |
| liner-steel | **0.8** |
| liner-rock | **0.5** |

- The liner material ([05](05_friction.md)) is **steel** (SAG_A shell liners
  and lifters are steel, stated by the author 2026-10-21), so its pairs take
  the steel values; only its friction differs. The frictionless end walls
  take their restitution from the liner.
- Applied per pair through a `MatchMaker` on
  `Ip2_FrictMat_FrictMat_MindlinPhys.en`, built from material **labels**.
  `es` is not set, so YADE uses the same value tangentially (es = en).
- Fixed, not calibrated; checked by a +-0.1 sensitivity run on toe /
  shoulder and segregation (Open items).

## Evidence

| Source | What it says | Where | Verified |
|---|---|---|---|
| Cleary & Morrison 2016 | e = 0.3 (rock-rock), 0.5 (rock-steel), 0.8 (steel-steel) | Table 2, PDF p7 / j.81 | Yes |
| Owen & Cleary 2015 | e = 0.75 steel-steel, 0.5 steel-rock, 0.3 rock-rock; "highest for steel-steel collisions which are relatively elastic and lowest for rock-rock collisions which have significant local fracture at contacts". Table 4 has no separate liner entry: the steel liner uses the steel pairs for both e and friction | Table 4 and §3 text, PDF p3 / j.21 | Yes |
| Owen & Cleary 2015 | "DEM simulation of mill behaviour has been shown to be only weakly sensitive to the specific choices of these material parameters (Cleary, 2001a)" | §3, PDF p3 / j.21 | Yes |
| Boemer & Ponthot 2017 | "different values are sometimes used for ball-ball and ball-liner collisions" (citing their refs. 19, 42) | §1, PDF p2 / j.54 | Yes |
| Boemer & Ponthot 2017 | Influence of e "becomes important for values close to 1; apart from that, the charge motion is again relatively insensitive"; e = 0.3, 0.6, 0.9 tested; stiffness and e "only have a relatively small impact on the power draw" | §3.1.3-3.1.4, PDF p10 / j.62 | Yes |
| Govender 2015 | Los Bronces: friction particle 0.40 vs lifter 0.70, but e = 0.75 for **both** particles and lifters; power could be matched "exactly by changing the coefficient of restitution" | Table 8 and §3 text, PDF p14 / j.165 | Yes |
| Kishida 2025 | e = 0.75 (single material) | Fig. 2(b), PDF p4 | Yes |
| Cleary 2001 (2D) | Friction and restitution "relatively unimportant" (citing Cleary 1998a) | §9, PDF p22 / j.100 | Yes |
| YADE source (`7c8d01e`) | With `en` given, the normal damping ratio is computed from "formula (B6) of [Thornton2013], written specifically for the Hertz-Mindlin model (no-slip solution) where the end of contact is considered to take place once the normal force is zero"; alpha from Eq. (B7); dashpot c_n = beta_n 2 sqrt(m* k_n) with the current Hertz stiffness k_n | `pkg/dem/HertzMindlin.hpp:90`; `HertzMindlin.cpp:184-207, 458-463` | Yes (source read) |
| YADE source / docs 2021 | "If neither e_s nor beta_s is given, the value of en is used for es" | `HertzMindlin.hpp:97`; docs printed p. 562 (PDF p569) | Yes |
| Thornton et al. 2013 | Hertz-Mindlin + damper (HM + D): damping coefficient gamma = sqrt(1 / (1 - (1 + e_n)^2 exp(alpha)) - 1) (Eq. B6), alpha a polynomial in e_n (Eq. B7) with coefficients h1-h10 (Table 2: -6.918798, -16.41105, 146.8049, -796.4559, 2928.711, -7206.864, 11494.29, -11342.18, 6276.757, -1489.915) -- **identical** to the constants in YADE's `HertzMindlin.cpp`. The older relation (their Eq. 46, the one in YADE 2021/2022) "is incorrect since it is based on the assumption that the contact ends when the displacement ... first returns to zero"; for non-adhesive spheres the contact ends when the normal force first returns to zero | Appendix B and Table 2, PDF p16-17 / j.45-46 | Yes (2026-11-04) |
| YADE releases 2021.01a and 2022.01a (source) | **Older mapping:** "If e_n is given, MindlinPhys.betan is computed using beta_n = -(log e_n) / sqrt(pi^2 + (log e_n)^2)" -- the linear-spring formula, which does not recover e exactly for a Hertzian contact; no "es = en" rule. The Thornton (B6) mapping is present from the 2023.02a release on, and in the build used (`7c8d01e`, 2026-01-15) | `pkg/dem/HertzMindlin.hpp:92` and `.cpp:77-91` at tag 2021.01a; tags 2022.01a / 2023.02a | Yes (source read, 2026-11-03) |

## PPT

| Slide | Content |
|---|---|
| 8, 9, 12 | "Coeficientes de Restitucion (Pares): Roca-Roca = 0.3 [1], Roca-Acero = 0.5 [1], Acero-Acero = 0.8 [1]" ([1] = Cleary & Morrison 2016, Table 2) |
| 8 | Reason to use Hertz-Mindlin: pair-wise restitution |

## Current state

| Where | What |
|---|---|
| `config.py` (`RESTITUTION_COEFFICIENTS`) | 0.8 / 0.5 / 0.3 plus liner-steel 0.8 and liner-rock 0.5 -- matches the decision (C07-1, commit `4bb17e4`) |
| `simulation/yade_dem/materials.py` | `pair_matchmaker(pairs)` builds the MatchMaker (restitution, and friction since C05-2) from material **labels** (fixed since the old review); the pairs come from `SimulationScenario.contact_tables()`, which also gives the frictionless end walls the liner's restitution; the old id-based `config.build_yade_material_interactions()` and its BlazeDEM placeholder were removed (C07-2, commit `5c194ab`) |
| `simulation/scenario.py` (`validate()`) | Validation: every particle-particle and particle-liner pair must have an e, otherwise the scenario fails (liner-liner is not needed: facets do not touch each other) |
| `simulation/scenario.py` (`contact_tables()`), `run_simulation.py` (build stage) | End-wall material derives from the liner (friction 0); its restitution pairs copy the liner's |
| `simulation/yade_dem/version.py`, `run_simulation.py:103-104` | At start-up `run()` parses `yade.config.version` (releases `2023.02a`, daily builds `20260115-...`) and refuses anything older than 2023.02 or unparseable; the version goes into the manifest (C07-3, commit `5c194ab`). The build used here, `20260115-8983~7c8d01e~noble1`, passes |

## Analysis

The PPT values come directly from Cleary & Morrison 2016 and agree with Owen
& Cleary 2015 (only steel-steel differs: 0.8 vs 0.75). Boemer shows the
charge is insensitive to e unless e approaches 1, so the 0.75-0.8 difference
is immaterial. Govender's remark that e can tune power is a reason to keep e
fixed: tuning it would hide errors elsewhere (e.g. damping).

- **Liner pairs: same e as steel, different friction -- why this is
  consistent.** e is a material property of the impact (energy lost to
  plastic deformation and fracture: low for rock, high for steel), and
  liners and balls are both steel. The liner friction mu_w is an
  **effective, calibrated** parameter: it absorbs what the smooth, idealised
  lifter facets do not represent (worn profile, ore / slurry layer on the
  liner, packing against the lifter face), which is why it is fitted to the
  shoulder ([05](05_friction.md)). This is exactly Govender et al.'s
  Los Bronces set (Table 8: friction 0.40 particle / 0.70 lifter, e = 0.75
  for both); Owen & Cleary treat the steel liner as steel for both
  (Table 4). Separate ball-liner e values exist in the literature (Boemer &
  Ponthot, §1), but no source in the library gives one, and the charge is
  insensitive to e (below).
- **Why e is fixed rather than calibrated.**
  1. The calibration targets barely respond to it: Boemer & Ponthot
     (§3.1.3, Fig. 12) tested e = 0.3 / 0.6 / 0.9 -- important only close
     to 1, "apart from that, the charge motion is again relatively
     insensitive"; Cleary 2001 (§9) and Owen & Cleary (§3) report the same
     weak sensitivity.
  2. Hence it is not identifiable from toe / shoulder: with two targets
     already used by mu_p and mu_w, a parameter that hardly moves them would
     fit equally well over a wide range, so a "calibrated" e would be
     arbitrary.
  3. The values are physically grounded and consistent across sources
     (0.3 / 0.5 / 0.8 Cleary & Morrison; 0.3 / 0.5 / 0.75 Owen & Cleary;
     0.75 Govender).
  4. e does move power (Govender), but power is not a target
     ([15](15_calibration_targets.md)).
- **Limits of that argument.** Boemer's test is a lab ball mill with steel
  balls only, and steel-steel 0.8 lies nearer the 0.9 where sensitivity
  starts. None of the sources tests e against **segregation**, the
  surrogate's output. A restitution sensitivity check (Open items) covers
  this.
- **YADE version floor.** The e -> beta mapping changed between releases:
  2021 and 2022 used the linear-spring formula -- which Thornton et al.
  (2013, App. B) show is incorrect for Hertzian contacts -- and 2023.02
  onwards uses Thornton's Hertz-specific relation. The method here therefore requires
  **YADE >= 2023.02** (the build used is 2026-01-15); with an older release
  the same input e gives a different, velocity-dependent restitution.
  Citing the YADE manual's 3rd edition as "2021" is correct for its other
  statements used here, but not for this one, which must be cited to the
  build used (README source registry).
- **Velocity independence.** YADE's Hertz-Mindlin maps e to a damping ratio
  with Thornton et al.'s formula for Hertzian contacts and scales the dashpot
  with the current stiffness, so the input e should be recovered at any
  impact speed. The binary-collision test (C01-4) confirms it at the
  run's dt.
- **Tangential damping.** With es = en the tangential dashpot uses the same
  ratio. Accepted (the friction limit governs most tangential dissipation in
  a mill); recorded so it is not mistaken for an omission.
- **Slurry.** A SAG charge is wet; the source values (Cleary & Morrison,
  Owen & Cleary) come from dry DEM. This is standard in those studies and is
  stated as a limitation, not corrected.

## Verdict and how to defend it

"Restitution coefficients follow Cleary & Morrison (2016, Table 2), consistent
with Owen & Cleary (2015, Table 4): rock-rock collisions are strongly
dissipative because of local fracture, steel-steel ones nearly elastic.
Charge motion is insensitive to e away from 1 (Boemer & Ponthot 2017, §3.1),
so e is fixed rather than calibrated. The steel liners and lifters take
the steel values, as in Govender et al. (2015, Table 8). YADE converts each
e into a viscous damping ratio with the Hertz-specific relation of Thornton
et al. (2013), so the coefficient holds at all impact velocities."

## Open items / validation

- Binary-collision test in YADE at the chosen dt: measured e must match the
  input within ~2 % for each pair ([16](16_validation_checks.md)).
- Interstitial slurry not modelled (limitation, see Analysis).
- **Restitution sensitivity check** (accepted 2026-10-21): at the calibrated point, one
  run with all e lowered and one with all raised (e.g. +-0.1, steel-steel
  capped at 0.9); compare toe / shoulder and steel / rock segregation with
  the reference. Small change -> fixing e is shown for segregation too.

## Pending code changes

| ID | Change | Current code | When |
|---|---|---|---|
| C07-1 | Add liner-steel 0.8 and liner-rock 0.5 to `RESTITUTION_COEFFICIENTS` (with C05-3) | Done (`4bb17e4`) | Before calibration |
| C07-2 | Delete the unused id-based `config.build_yade_material_interactions()` (and its BlazeDEM placeholder) | Done (`5c194ab`) | Any time |
| C07-3 | At start-up, record the YADE version and refuse releases older than 2023.02 (e -> beta mapping, see Analysis) | Done (`5c194ab`): unparseable versions are refused too | Before calibration |

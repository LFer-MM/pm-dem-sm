# Scientific rationale for the DEM simulation parameters

This directory justifies every parameter of the YADE SAG-mill simulations used
to generate the SIC / RMIC datasets. Each topic file has the same structure:

1. **Decision** -- the value or rule we use.
2. **Evidence** -- one table row per source: what it says, the exact location
   (PDF page, journal page, section, table / figure, or PPT slide), and whether
   the quote was verified against the PDF.
3. **Current state** -- what the code (`main`) and the existing dataset do.
4. **Analysis** -- how the evidence and the numbers lead to the decision.
5. **Verdict and how to defend it** -- the argument to use in the thesis.
6. **Open items / validation** -- what still has to be measured.

All page locations below were checked by text search in the PDFs stored in
Zotero (`/home/pher/Zotero/storage/<key>/`). "PDF p" is the page index of the
file; "j." is the printed journal page. Slide numbers refer to
`avances_tt.pptx` (Zotero item `YM2798IJ`, file `J8ID6KEP`, collection
`bppm_dem_sm/project`) in presentation order (slide *N* is the
*N*-th slide; verified against `ppt/presentation.xml`).

## Plant data: one reference mill, two supporting mills

**Mill naming (2026-10-21):** the reference mill is **SAG_A** in these
docs. The PPT (slides 2-5) labels it SAG_B and calls the other mill SAG_A;
the two labels are swapped here so the reference comes first. SAG_C keeps
its name. These docs, not the PPT, are the source of truth.

Operational data from three SAG mills (SAG_A, SAG_B, SAG_C; PPT slides 2-5)
is used in one specific way throughout these documents:

- **SAG_A is the reference.** Its operating point (9 rpm, Jb 17 %, Jc 26 %)
  sets the simulation, and its bulk toe and shoulder angles (215 deg,
  24.6 deg) are the targets the simulation is compared to.
- **SAG_B and SAG_C are evidence that the selected values are typical.**
  Their designs and dimensions differ slightly from SAG_A, so they are not
  simulated or used as validation cases; their box plots show that SAG_A's
  values sit inside the normal operating ranges of SAG mills (speed
  8.6-10 rpm, Jb 15.2-18.5 %, Jc 24.9-35.1 %, bulk toe 206-215 deg,
  shoulder 24.6-38.2 deg).

Plant power and mill lengths are not used (decided 2026-10-18; see
[15](15_calibration_targets.md) for why power would not be a determining
target anyway).

## Topics

| # | File | Decision in one line |
|---|------|----------------------|
| 01 | [01_contact_model.md](01_contact_model.md) | Hertz-Mindlin with pair-wise restitution, pair-wise friction and rolling resistance |
| 02 | [02_time_step.md](02_time_step.md) | dt = 2.5e-5 s (not 1e-4 s): every contact gets >= 20 steps at the worst-case impact speed |
| 03 | [03_stiffness_young_modulus.md](03_stiffness_young_modulus.md) | Physical moduli (207 / 55 GPa) / 26 = 7.96 / 2.115 GPa, uniform to keep the stiffness ratio; overlaps checked |
| 04 | [04_numerical_damping.md](04_numerical_damping.md) | NewtonIntegrator damping = 0 everywhere; the "explosions" it hid were an unstable dt (tested) |
| 05 | [05_friction.md](05_friction.md) | Calibrate; uniform particle friction mu_p (baseline 0.5) plus liner friction mu_w; Owen 0.4 / 0.5 / 0.8 as a sensitivity run |
| 06 | [06_rolling_resistance.md](06_rolling_resistance.md) | Uniform rolling resistance mu_r (YADE eta) on all contacts, fixed by an angle-of-repose heap test (target 37 deg, band 33-41); ktwist = 0 |
| 07 | [07_restitution.md](07_restitution.md) | Fixed pair-wise e (Cleary & Morrison 2016): 0.3 / 0.5 / 0.8; steel liners take the steel values; es = en |
| 08 | [08_density.md](08_density.md) | Steel 7850 / ore 2850 kg/m^3 (Chilean porphyry copper: Vergara 2020, Govender 2015); not calibrated; sensitivity 2650 incl. segregation |
| 09 | [09_poisson_ratio.md](09_poisson_ratio.md) | Steel 0.292 (Shigley), rock 0.25 (Vergara 2020, El Teniente andesite); physical, not calibrated; effect < 7 % on contact stiffness |
| 10 | [10_mill_geometry.md](10_mill_geometry.md) | SAG_A design with new liners (from reports, generated in code); 0.6 m slice (4.3 ball diameters, as Owen & Cleary); frictionless end walls, V11 checks liner friction |
| 11 | [11_mill_speed.md](11_mill_speed.md) | SAG_A median 9 rpm = 72.8 % of critical (73.2 % with plain D); SAG_B / SAG_C typical (8.6-10 rpm); confirm from post-reline window (A1) |
| 12 | [12_charge_fill_and_particles.md](12_charge_fill_and_particles.md) | Jb 17 % / Jc 26 % in Morrell's convention (D inside liners, lifters not subtracted); counts from a simulated grind-out + mixed crash stop; phi is a result |
| 13 | [13_initial_conditions.md](13_initial_conditions.md) | SIC / RMIC at rest, undamped settle with a geometric stop rule, velocities zeroed; SIC = rock bottom, balls top |
| 14 | [14_dataset_runs_and_recording.md](14_dataset_runs_and_recording.md) | Record from rest; durations in revolutions; training window after measured quasi-steady state |
| 15 | [15_calibration_targets.md](15_calibration_targets.md) | Match the SAG_A (reference) bulk toe 215 / shoulder 24.6 deg (0 deg at 3 o'clock, CCW); SAG_B / SAG_C show these values are typical; power only for the internal energy balance |
| 16 | [16_validation_checks.md](16_validation_checks.md) | Acceptance tests every run must pass |

## Pending code changes

Each topic file ends with a **"Pending code changes"** table (IDs `Cnn-k`,
nn = topic number) listing what the code must change to implement its
decisions. Status after reviewing topics 01-04 (2026-10-19): nothing
implemented yet; decided to collect all topics first and implement at the
end.

| Topic | IDs | Must be done before any production run |
|---|---|---|
| [01](01_contact_model.md) | C01-1 ... C01-4 | -- (C01-1, C01-2 need values from 05 / 06) |
| [02](02_time_step.md) | C02-1 ... C02-3 | **C02-1** (default dt), C02-2 |
| [03](03_stiffness_young_modulus.md) | C03-1 ... C03-3 | **C03-1** (moduli), C03-2 |
| [04](04_numerical_damping.md) | C04-1 ... C04-5 | **C04-1** (damping), C04-2, C04-4 |
| [05](05_friction.md) | C05-1 ... C05-3 | **C05-1**, **C05-2**, **C05-3** |
| [06](06_rolling_resistance.md) | C06-1 ... C06-4 | **C06-1**, C06-2, **C06-3** |
| [07](07_restitution.md) | C07-1, C07-2 | **C07-1** |
| [08](08_density.md) | C08-1 | **C08-1** |
| [10](10_mill_geometry.md) | C10-1 ... C10-4 | **C10-1**, **C10-2**, **C10-3**, **C10-4** |
| [12](12_charge_fill_and_particles.md) | C12-1 ... C12-3 | **C12-1**, **C12-2**, **C12-3** |

Related items from later topics (not yet reviewed): split the runner into
calibrate / make-IC / dataset run types ([14](14_dataset_runs_and_recording.md)).

## Author to-do list (after the review sweep)

Everything the author must provide or do, collected from the topic files
(each item links to where it is used). Claude's own follow-ups stay in the
topics' open items.

| # | Item | Details | Used in |
|---|---|---|---|
| A1 | Plant time series, SAG_A-E | 10 s resolution; toe, shoulder, Jc, Jb, speed, **power** (state motor input vs shaft power), reline dates; at least one full liner campaign (min ~3 months, ideally 6-12) | [15](15_calibration_targets.md) claims 1-2, V15 |
| A2 | Mill design data, SAG_A-E (reports) | Diameter inside shell **and** liner plate thickness (Morrell's two inputs; D inside liners = D shell - 2 x plate thickness), belly length inside liners, lifter rows, lifter height, base / top width, face angle (new; worn if available), liner / grate design, plant's critical-speed definition | [10](10_mill_geometry.md), [15](15_calibration_targets.md) |
| A3 | Plant Maleki-model inputs | Which liner geometry feeds the plant's Maleki-Moghaddam model, and whether it is updated with wear | [15](15_calibration_targets.md) claim 3 |
| A4 | Mill generator code | Add the author's mill-generation code to the repo as the primary geometry source | [10](10_mill_geometry.md) C10-4 |
| A5 | Zotero additions | Work through "Pending Zotero additions" below (priority: Maleki-Moghaddam 2013; read Wensrich & Katterfeld 2012, Ai 2011, Thornton 2013) | registry below |
| A6 | Optional | Official CEMA 550 material table (ore angle of repose) | [06](06_rolling_resistance.md) |

Confirmed unavailable (no action): plant ore SG ([08](08_density.md)),
plant angle of repose ([06](06_rolling_resistance.md)).

## Source registry

Bibliographic data below is taken from the Zotero records (checked against
the Zotero database on 2026-10-19; item and file keys re-checked after the
library was reorganised, 2026-10-26: all present). Library collections:
`bppm_dem_sm/core` (Kishida 2025, with its supplementary PDF and video),
`bppm_dem_sm/dem` (all other cited papers, books and the YADE docs),
`bppm_dem_sm/project` (the PPT), `bppm_dem_sm/unison` (university
guidelines, not cited here). New items from "Pending Zotero additions" go
into `bppm_dem_sm/dem`. "Item" is the Zotero item key, "File" the
storage folder of the PDF actually read. Page references in these documents
are to that PDF ("PDF p") and, where the PDF is the published version, to
the printed page ("j.").

| Key used in docs | Reference | DOI | Item / File | Page mapping |
|---|---|---|---|---|
| **Kishida 2025** | N. Kishida, H. Nakamura, S. Ohsaki, S. Watano, *Surrogate model of DEM simulation for binary-sized particle mixing and segregation*, Powder Technol. 455 (2025) 120811 | 10.1016/j.powtec.2025.120811 | `U6DHI89A` / `U6NKB3KZ` | PDF p = article p (1-13) |
| **Kishida 2025 SM** | Supplementary material of the above (Figs. S1-S2) | -- | `U6DHI89A` / `LZXF23SG` | 3 pages |
| **Cleary & Morrison 2016** | P.W. Cleary, R.D. Morrison, *Comminution mechanisms, particle shape evolution and collision energy partitioning in tumbling mills*, Miner. Eng. 86 (2016) 75-95 | 10.1016/j.mineng.2015.12.006 | `BQR6XF9R` / `9S5TJQ2P` | j. = PDF p + 74 |
| **Owen & Cleary 2015** | P. Owen, P.W. Cleary, *The relationship between charge shape characteristics and fill level and lifter height for a SAG mill*, Miner. Eng. 83 (2015) 19-32 | 10.1016/j.mineng.2015.08.009 | `GZR4AELH` / `AYIPPK53` | j. = PDF p + 18 |
| **Boemer & Ponthot 2017** | D. Boemer, J.-P. Ponthot, *DEM modeling of ball mills with experimental validation: influence of contact parameters on charge motion and power draw*, Comp. Part. Mech. 4(1) (2017) 53-67 | 10.1007/s40571-016-0125-4 | `HFTDYRM2` / `4LNBNEIZ` | j. = PDF p + 52 |
| **Cleary 2001** | P.W. Cleary, *Charge behaviour and power consumption in ball mills: sensitivity to mill operating conditions, liner geometry and charge composition*, Int. J. Miner. Process. 63(2) (2001) 79-114 (**2D** DEM) | 10.1016/S0301-7516(01)00037-0 | `APTRYTA5` / `VRMUBFRG` | j. = PDF p + 78 |
| **Govender 2015** | N. Govender, R.K. Rajamani, S. Kok, D.N. Wilke, *Discrete element simulation of mill charge in 3D using the BLAZE-DEM GPU framework*, Miner. Eng. 79 (2015) 152-168 | 10.1016/j.mineng.2015.05.010 | `ALAZVPIQ` / `W9YT6FNT` | j. = PDF p + 151 |
| **Thakur 2016** | S.C. Thakur, J.Y. Ooi, H. Ahmadian, *Scaling of discrete element model parameters for cohesionless and cohesive solid*, Powder Technol. 293 (2016) 130-137 | 10.1016/j.powtec.2015.05.051 | `Y4CWQDST` / `AJF55YJ2` | j. = PDF p + 129 |
| **Gercek 2007** | H. Gercek, *Poisson's ratio values for rocks*, Int. J. Rock Mech. Min. Sci. 44(1) (2007) 1-13 | 10.1016/j.ijrmms.2006.04.011 | `56ASD2GS` / `JPTAYGXS` | PDF p = j. |
| **Vergara et al. 2020** | M. Vergara, A. Arismendy Agudelo, A. Libreros, A. Brzovic, *Numerical investigation into strength and deformability of veined rock mass*, Int. J. Rock Mech. Min. Sci. 135 (2020) 104510 | 10.1016/j.ijrmms.2020.104510 | `5HS5T7DE` / `QR9D245M` | The PDF is the **author manuscript**: page numbers are manuscript pages, not journal pages |
| **Shigley** | R.G. Budynas, J.K. Nisbett, *Diseno en ingenieria mecanica de Shigley*, 8th ed. (Spanish), McGraw-Hill Interamericana, 2008, ISBN 978-970-10-6404-7 (translation of *Shigley's Mechanical Engineering Design*, 8th ed., 2008) | -- | `2WRCXH99` / `4RP3VQXB` (also `V3V5BMNV`, English edition, no file) | inside-cover table = PDF p3 |
| **Shi & Zhang 2008** | Y. Shi, Y. Zhang, *Simulation of random packing of spherical particles with different size distributions*, Appl. Phys. A 92 (2008) 621-626 | 10.1007/s00339-008-4547-6 | `DWL7JH3T` / `ZNTAYS7X` | j. = PDF p + 620 |
| **Brouwers 2024** | H.J.H. Brouwers, *Random packing fraction of binary similar particles: Onsager's excluded volume model revisited*, Physics-Uspekhi 67(5) (2024) 510-529 | 10.3367/UFNe.2023.11.039606 | `SFYYQ45R` / `TS9GXXKP` | The PDF is the **arXiv:2209.09873v5 preprint** (27 Jun 2024): page numbers are arXiv pages |
| **Johnson 1985** | K.L. Johnson, *Contact Mechanics*, 1st ed., Cambridge University Press, 1985 (digital ed. 2012), ISBN 978-0-521-34796-9 | 10.1017/CBO9781139171731 | `PDKNRX4P` / `LECT8BKG` | book p = PDF p - 10 (scanned, no text layer) |
| **Li et al. 2005** | Y. Li, Y. Xu, C. Thornton, *A comparison of discrete element simulations and experiments for 'sandpiles' composed of spherical particles*, Powder Technol. 160(3) (2005) 219-228 | 10.1016/j.powtec.2005.09.002 | `BN556RC8` / `6CHXZ76U` | j. = PDF p + 218 |
| **Nan et al. 2022** | W. Nan, W.P. Goh, M.T. Rahman, *Elasto-plastic and adhesive contact: an improved linear model and its application*, Powder Technol. 407 (2022) 117634 | 10.1016/j.powtec.2022.117634 | `M78ZRT88` / `MEHLVFKI` | The PDF is the **author manuscript** (49 pages, same text as arXiv:2202.09520): page numbers are manuscript pages |
| **McLaskey & Glaser 2010** | G.C. McLaskey, S.D. Glaser, *Hertzian impact: Experimental study of the force pulse and resulting stress waves*, J. Acoust. Soc. Am. 128(3) (2010) 1087-1096 | 10.1121/1.3466847 | `J45IS7SQ` / `PWTRWT5T` | j. = PDF p + 1086 |
| **YADE docs 2021** | V. Smilauer et al. (27 authors), *Yade documentation*, 3rd ed., 2021 (the latest official edition; PPT ref. [8] cites the 2nd ed., 2015, DOI 10.5281/zenodo.34073) | 10.5281/zenodo.5705394 | `4NJP35ET` / `86JYU2WN` | printed p = PDF p - 7 |
| **PPT** | `avances_tt.pptx` (project progress deck) | -- | `YM2798IJ` / `J8ID6KEP` | slide numbers |

Govender et al. 2016 (Blaze-DEMGPU framework, SoftwareX 5 (2016) 62-66,
`2GMEKA42`) and Chou et al. 2017 (mixing index, KONA 34 (2017) 275-281,
`4GN5HB5Y`) were searched but give no DEM parameter used here.

### References added on 2026-10-19 (verified in the PDFs)

| Reference | Used for | Exact location (verified) |
|---|---|---|
| Johnson 1985 | Hertz force law, maximum overlap, impact duration | §11.4 "Elastic impact", (a) "Collinear impact of spheres", book pp. 351-353 (PDF pp. 361-363): Eq. (11.20) P = (4/3) R^(1/2) E* delta^(3/2) with 1/R = 1/R1 + 1/R2, 1/E* = (1-nu1^2)/E1 + (1-nu2^2)/E2, 1/m = 1/m1 + 1/m2 (p. 352); Eq. (11.22) delta* = (15 m V^2 / (16 R^(1/2) E*))^(2/5) (p. 353); Eq. (11.24) T_c = 2.94 delta*/V = 2.87 (m^2 / (R E*^2 V))^(1/5) (p. 353). Force law originally Eq. (4.23), Ch. 4. |
| Li et al. 2005 | Rayleigh critical time step | End of §2, Eqs. (8)-(10), j.221 (PDF p3): Delta t_c = (pi R_bar / beta) sqrt(rho / G); beta from the exact Eq. (9), approximated by beta = 0.8766 + 0.163 nu (Eq. 10); R_bar = average particle radius, G = shear modulus |
| Nan et al. 2022 | Open statement of the Rayleigh step; practical dt fraction | Eq. (71), manuscript p18 (credited to Raji 1999, PhD thesis, Newcastle); same page: "much smaller time step should be used, i.e. Delta t = 0.01~0.1 Delta T_R" to resolve contact details |
| YADE docs 2021 | P-wave critical step used by YADE | Ch. 2 "Yade for users", §2.1 "DEM formulation", "Stability considerations -- Critical timestep", Eqs. (2.12)-(2.13), printed p. 72 (PDF p79); `yade.utils.SpherePWaveTimeStep(radius, density, young)`: "Delta t_c = r / sqrt(E / rho)", printed p. 838 (PDF p845), example `SpherePWaveTimeStep(1e-3, 2400, 30e9)` = 2.83e-7 s (confirms plain E) |
| McLaskey & Glaser 2010 | Secondary pointer to Johnson | Reference list, PDF p10: "Johnson, K. (1985). Contact Mechanics (Cambridge University Press, Cambridge), pp. 351-369"; derivation pointer in section "B. The source function and Hertzian impact", PDF p3 (j.1089) |

The Johnson PDF (`LECT8BKG`) is attached to the book record `PDKNRX4P`
(created from the DOI via Crossref; verified 2026-10-19).

### Pending Zotero additions (checklist, audited 2026-10-21)

Every source used as justification in docs 01-16 is either in the registry
above (all 19 entries checked: Zotero item and attached file present) or in
this list. Add each item and attach the file, then move its row to the
registry with its item / file keys and page mapping.

| Key used in docs | Reference | DOI / source | Used in | Status in docs | Action |
|---|---|---|---|---|---|
| **Maleki-Moghaddam et al. 2013** | M. Maleki-Moghaddam, M. Yahyaei, S. Banisi, *A method to predict shape and trajectory of charge in industrial mills*, Miner. Eng. 46-47 (2013) 157-166 | 10.1016/j.mineng.2013.04.013 | [15](15_calibration_targets.md) | Abstract only (marked "No") | Add by DOI; PDF via library access. **Priority**: the plant angles come from this model |
| **Toor et al. 2023** | P. Toor, W. Valery, S. Morrell, K. Duffy, *Real-Time Estimation of SAG Mill Charge Characteristics for Process Optimization*, SAG Conference, Vancouver, 2023 (page footers read "SAG CONFERENCE 2019 VANCOUVER \| June 18, 2023") | ceecthefuture.org publication 4122 (free PDF) | [15](15_calibration_targets.md) | Read (PDF) | Add as conference paper; attach the free PDF |
| **Pural & Boylu 2025** | Y.E. Pural, F. Boylu, *Prediction and visualization of charge shape and ball trajectory in tumbling mills: a python-based tool for liner design and operational optimizations*, Physicochem. Probl. Miner. Process. 61(3) (2025) 204533 | 10.37190/ppmp/204533 (open access) | [15](15_calibration_targets.md) | Read (PDF) | Add by DOI (Zotero fetches the PDF) |
| **Wei et al. 2022** | S. Wei, H. Wei, H. Saxen, Y. Yu, *Numerical analysis of the relationship between friction coefficient and repose angle of blast furnace raw materials by discrete element method*, Materials 15(3) (2022) 903 | 10.3390/ma15030903 (open access) | [06](06_rolling_resistance.md) | Read (online full text) | Add by DOI (Zotero fetches the PDF) |
| **Marin Perez et al. 2024** | J. Marin Perez, T. Comlekci, Y. Gorash, D. MacKenzie, *Calibration of the DEM sliding friction and rolling friction parameters of a cohesionless bulk material*, preprint, 28 May 2024 | strathprints.strath.ac.uk/89399 (free PDF) | [06](06_rolling_resistance.md) | Read (PDF) | Add as preprint; attach the PDF; check for a published version |
| **Wensrich & Katterfeld 2012** | C.M. Wensrich, A. Katterfeld, *Rolling friction as a technique for modelling particle shape in DEM*, Powder Technol. 217 (2012) 409-417 | 10.1016/j.powtec.2011.10.057 | [06](06_rolling_resistance.md) | **Not read** (citation only) | Add by DOI; PDF via library access; then verify what doc 06 attributes to it |
| **Ai et al. 2011** | J. Ai, J.-F. Chen, J.M. Rotter, J.Y. Ooi, *Assessment of rolling resistance models in discrete element simulations*, Powder Technol. 206 (2011) 269-282 | 10.1016/j.powtec.2010.09.030 | [06](06_rolling_resistance.md) | **Not read** (citation only) | Add by DOI; PDF via library access; then compare its krot rule with doc 06 |
| **Engineering Toolbox** | *Angles of Repose* (table) | engineeringtoolbox.com/dumping-angles-d_1531.html | [06](06_rolling_resistance.md) | Read (web page) | Add as web page with a snapshot (accessed 2026-10-21) |
| **PDHonline M344** | J. Primo, *Belt Conveyor for Bulk Materials -- Practical Calculations*, PDHonline course M344, 2026 | pdhonline.com/courses/m344/m344content.pdf | [06](06_rolling_resistance.md) | Read (PDF) | Add as document; attach the PDF (the edition changes yearly) |
| **Thornton et al. 2013** | C. Thornton, S.J. Cummins, P.W. Cleary, *An investigation of the comparative behaviour of alternative contact force models during inelastic collisions*, Powder Technol. 233 (2013) 30-46 | 10.1016/j.powtec.2012.08.012 | [07](07_restitution.md) | **Not read** (cited through the YADE source) | Add by DOI; PDF via library; verify Eqs. B6-B7 |
| **SMC gross power calculator** | SMC Testing, *Gross Power Calculator* help (model from Morrell 1993 thesis): definitions of inside-liner diameter, liner thickness, ball / total filling | smctesting.com/documents/gross_power_calculation_help.pdf | [12](12_charge_fill_and_particles.md) | Read (PDF, Fig. 4 rendered) | Add as document; attach the PDF |
| **Hilden et al. 2021** | M.M. Hilden, M.S. Powell, M. Yahyaei, *An improved method for grinding mill filling measurement and the estimation of load volume and mass*, Miner. Eng. 160 (2021) 106638 | 10.1016/j.mineng.2020.106638 | [12](12_charge_fill_and_particles.md) | **Not read** (abstract / highlights via search) | Add by DOI; PDF via library; verify the smooth-cylinder statement |
| **YADE source** | YADE, source code at commit `7c8d01e` (the installed `yadedaily` 20260115 build), files `pkg/dem/HertzMindlin.{hpp,cpp}`, `ViscoelasticPM.*`, `CohesiveFrictionalContactLaw.*` | gitlab.com/yade-dev/trunk, commit 7c8d01e | [06](06_rolling_resistance.md) | Read (source) | Optional: add as "computer program" with the commit; line numbers are quoted in doc 06 |

Cited only **through** another source (add only if you want to cite them
directly): Morrell 1993, PhD thesis, University of Queensland (via Toor et
al. 2023); Burns et al. 2018, Lihir toe measurement (via Toor et al. 2023,
a lead for doc 15); Rajamani et al. 2011 (via Govender 2015); Raji 1999,
PhD thesis, Newcastle (via Nan et al. 2022); Cleary 1998a (via Cleary
2001). Optional strengthening for doc 06: the official CEMA 550 material
table.

## Citation problems found in the PPT

These do not change the values, but the references must be corrected before
they go into the thesis:

| Slide | As written | Problem | Correct support |
|---|---|---|---|
| 8 | "Se busca mantener ... dt = 1e-4 [5]" (Boemer & Ponthot) | Boemer uses 1e-5, 2.5e-6, 1e-6 s (§3.1, PDF p7 / j.59); 1e-4 does not appear in the paper | Cleary 2001 §2, PDF p5 / j.83 gives "typically 1e-4 to 1e-6 s" **with** 15-25 steps per collision -- see [02](02_time_step.md) |
| 8, 9, 11, 12 | "[3] Thakur et al. (2014) ... Powder Technology, 293" for reducing E | Year is 2016; the paper is about **coarse-graining** (stiffness scales linearly with particle size, abstract PDF p1); it does not discuss lowering E to enlarge dt | Cleary & Morrison 2016 §2 PDF p3 / j.77; Boemer §3.1.2 PDF p8 / j.60 and §4 PDF p13; Owen & Cleary §3 PDF p3 / j.21 -- see [03](03_stiffness_young_modulus.md) |
| 8 | "[7] Vergara & Mork (2017) ... J. Rock Mech. Geotech. Eng., 9(2)" | The Zotero item is Vergara, Arismendy Agudelo, Libreros & Brzovic, *Numerical investigation into strength and deformability of veined rock mass*, Int. J. Rock Mech. Min. Sci. 135 (2020) 104510 | Cite that paper, Table 1 (manuscript PDF p3): E_i = 55 GPa, nu = 0.25 |
| 8 | "[8] Smilauer et al. (2015). Yade Documentation, 2nd ed. doi:10.5281/zenodo.34073" | Not wrong, but superseded | Cite the 3rd ed. (2021, DOI 10.5281/zenodo.5705394) held in Zotero, the latest official edition |
| 9 | dt_cr = R_min sqrt(rho / E_eff), E_eff = E / (1 - nu^2), presented as YADE's P-wave step | YADE's `PWaveTimeStep` uses plain E (YADE docs 2021, printed p. 838) | Use dt_cr = r / sqrt(E / rho) -- see [02](02_time_step.md) |
| 8 | "Segun Cleary (2015), Boehmer & Ponthot (2017) y Thakur (2016) la influencia ... se ordena: friccion, restitucion y rigidez" | No "Cleary (2015)" in the library (Owen & Cleary 2015 is meant?); Thakur says nothing about this ordering; Cleary 2001 says friction and restitution are "relatively unimportant" (PDF p22) | Boemer abstract (PDF p1) and §3.1.4 (PDF p10) -- see [05](05_friction.md) |
| 8 | "En Cleary & Owen (2016) utilizan ... Cundall-Strack ... [1]" | [1] is Cleary & **Morrison** 2016; it uses a linear spring-dashpot with restitution (PDF p7 / j.81), which in YADE is **not** `Law2_ScGeom_FrictPhys_CundallStrack` (that law has no dashpot) | see [01](01_contact_model.md) |
| 8 vs 10 | Overlap target "< 0.1 %" (slide 8) vs "between 0.1 % and 0.5 %" (slide 10) | Inconsistent; literature gives 0.1-1 % of the diameter (Boemer) and ~0.8 % (Owen) | see [03](03_stiffness_young_modulus.md) |
| 7, 16 | Rock count line divides by 0.001429 (ball volume) | Typo only: the result 19,888 / 11,171 uses the rock volume 0.0001786 m^3 | see [12](12_charge_fill_and_particles.md) |

## How the derived numbers were computed

Every derived number (Rayleigh time step, Hertz collision time, peak overlap,
critical speed, particle counts) uses the formulas written out in the topic
file, with the decided material set (physical moduli / 26, see
[03](03_stiffness_young_modulus.md)): steel rho = 7850, E = 7.962e9,
nu = 0.292, r = 0.06985 m; rock rho = 2850 (2650 until 2026-10-21, now the
sensitivity case), E = 2.115e9, nu = 0.25, r = 0.034925 m. Particle masses:
ball 11.206 kg, rock 0.5086 kg (0.4729 kg at 2650). Numbers in docs 02-04
that depend on rock density were recomputed on 2026-10-21; the historical
test setups in [04](04_numerical_damping.md) keep the 2650 they were run with. Where a
doc compares with the PPT's slide-12 set (33.16e9 / 2.868e9), it says so.

## Code state referenced

"`main`" means the `main` branch at commit `bb04dfd` (the code that produced
or will produce the datasets). Branch `worktree-yade-sim-structure` contains
the structural rework and the bug fixes referenced in some files.

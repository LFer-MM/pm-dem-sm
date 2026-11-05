r"""V1 side study: how the recovered restitution depends on the contact-onset phase (YADE).

Shows why ``collision_check.py`` averages over contact-onset phases
(docs/scientific_rationale/01_contact_model.md, Open items): one head-on
collision of a material pair is repeated with initial gaps that make the
contact start at different fractions of one time step.

Run from the repository root::

    yadedaily -n -x scripts/validation/v1_onset_phase_sweep.py \
        --scenario configs/simulation/sag_slice_lifters.json --pair rock rock \
        --speeds 5 14.5 --phases 6 --out scripts/validation/results/v1/onset_phase_sweep.json
"""

import argparse
import json
from pathlib import Path
import sys

REPO = Path(sys.argv[0]).resolve().parents[2]
sys.path.insert(0, str(REPO))

from pm_dem_sm.simulation.scenario import load_scenario
from pm_dem_sm.simulation.yade_dem import collision_check as cc

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("--scenario", default="configs/simulation/sag_slice_lifters.json")
p.add_argument("--pair", nargs=2, default=["rock", "rock"], help="Two particle materials.")
p.add_argument("--speeds", type=float, nargs="+", default=[5.0, 14.5])
p.add_argument("--phases", type=int, default=6)
p.add_argument("--out", required=True)
args = p.parse_args(sys.argv[1:])

s = load_scenario(REPO / args.scenario)
s.validate()
tables, krot, dt = s.contact_tables(), s.rolling_stiffness(), s.time_step_s()
radius = {sp.material: sp.radius_m for sp in s.species}
a, b = args.pair
rows = []
for v in args.speeds:
    for k in range(args.phases):
        frac = k / args.phases
        res = cc.collide(s, tables, krot, a, b, radius[a], radius[b], v, gap=1e-7 + frac * v * dt)
        rows.append({"speed_m_s": v, "onset_fraction_of_step": frac, **res})
        print(
            f"[sweep] v = {v} m/s, onset {frac:.2f} dt: e = {res['e_measured']:.4f} "
            f"({100 * res['rel_error']:+.2f} %), {res['contact_steps']} steps"
        )
Path(args.out).parent.mkdir(parents=True, exist_ok=True)
Path(args.out).write_text(
    json.dumps({"scenario": args.scenario, "dt_s": dt, "rows": rows}, indent=2), encoding="utf-8"
)
print(f"[sweep] -> {args.out}")

"""Write the friction-calibration grid scenarios (mu_p x mu_w), ``calibrate`` runs from one IC.

docs/scientific_rationale/05_friction.md: mu_p x mu_w in {0.3, 0.5, 0.7} x
{0.3, 0.5, 0.7}, every run starting from one shared settled initial
condition. Each scenario is the base ``make_ic`` scenario (the IC's own, so
everything but friction matches) with:

- ``run.type = "calibrate"`` with ``run.ic_dir`` = that ``make_ic`` run (it
  loads the IC instead of pouring its own);
- ``contact.particle_friction`` = mu_p and ``contact.wall_friction`` = mu_w;
- ``record.duration_s`` = ``--record-revolutions`` revolutions (default 2:
  enough for the time-averaged toe / shoulder, docs/scientific_rationale/15_...).

Run from the repository root with the project environment::

    python scripts/calibration/make_grid_scenarios.py
    python scripts/calibration/make_grid_scenarios.py --mu-p 0.6 0.7 0.8 --mu-w 0.7 0.8 0.9

The packaged grid was written on 2026-11-06, when the base (and the pilot's
IC) had mu_r = 0.13; since the calibrated defaults (mu_r 0.16) it is
reproduced with ``--rolling-resistance 0.13``. A new grid needs a new IC
made with its rolling resistance (rolling resistance is part of an IC's
material-set id).

Names are ``cal_mup<mu_p>_muw<mu_w>`` (``0p5`` for 0.5), one file each in
``configs/simulation/calibration/``.
"""

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from pm_dem_sm.simulation.scenario import load_scenario

BASE = "configs/simulation/sag_a_make_ic_rmic.json"
IC_DIR = "data/raw/yade_runs/sag_a_make_ic_rmic_s0"
OUT_DIR = "configs/simulation/calibration"
GRID = (0.3, 0.5, 0.7)


def tag(value):
    """Return ``value`` for a file name: 0.5 -> ``0p5``."""
    return f"{value:g}".replace(".", "p")


def grid_scenario(base, mu_p, mu_w, ic_dir, record_revolutions, rolling_resistance=None):
    """Return the scenario dict of one grid point (``base`` is not modified).

    ``rolling_resistance`` overrides the base's (``None`` keeps it).
    """
    data = json.loads(json.dumps(base))
    if rolling_resistance is not None:
        data.setdefault("contact", {})["rolling_resistance"] = rolling_resistance
    data["name"] = f"cal_mup{tag(mu_p)}_muw{tag(mu_w)}"
    data["run"] = {"type": "calibrate", "ic_dir": ic_dir}
    data.setdefault("contact", {}).update(particle_friction=mu_p, wall_friction=mu_w)
    revolution_s = 60.0 / data["mill"]["speed_rpm"]
    data["record"]["duration_s"] = round(record_revolutions * revolution_s, 4)
    return data


def main(argv=None):
    """Write the grid scenarios; print one line per file."""
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--mu-p", type=float, nargs="+", default=list(GRID))
    p.add_argument("--mu-w", type=float, nargs="+", default=list(GRID))
    p.add_argument("--base", default=BASE, help="The IC's make_ic scenario.")
    p.add_argument("--ic-dir", default=IC_DIR, help="The make_ic run directory.")
    p.add_argument("--record-revolutions", type=float, default=2.0)
    p.add_argument(
        "--rolling-resistance",
        type=float,
        default=None,
        help="mu_r of the grid (default: the base's; 0.13 reproduces the packaged grid).",
    )
    p.add_argument("--out-dir", default=OUT_DIR)
    args = p.parse_args(argv)

    base = json.loads((REPO_ROOT / args.base).read_text())
    out = REPO_ROOT / args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    for mu_p in args.mu_p:
        for mu_w in args.mu_w:
            data = grid_scenario(
                base, mu_p, mu_w, args.ic_dir, args.record_revolutions, args.rolling_resistance
            )
            path = out / f"{data['name']}.json"
            path.write_text(json.dumps(data, indent=2) + "\n")
            s = load_scenario(path)  # validates
            shown = path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path
            print(
                f"wrote {shown}  (mu_p {mu_p}, mu_w {mu_w}, "
                f"record {s.record.duration_s} s, warnings: {len(s.warnings())})"
            )


if __name__ == "__main__":
    main()

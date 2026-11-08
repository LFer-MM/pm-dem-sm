"""Write the calibrated point's scenario (option 1, decided 2026-11-08).

The friction grid and the probes showed that SAG_A's reference toe / shoulder
(214 / 27 deg, outputs of Maleki-Moghaddam et al.'s correlation) cannot be
reached with physically admissible contact parameters
(docs/scientific_rationale/15_calibration_targets.md). The calibration is
therefore constrained: particle friction at the lower end of the DEM
literature range, the value closest to the targets (mu_p = 0.3; mu_w = 0.5,
which hardly matters), and rolling resistance re-fitted with the heap test
so the ore's angle of repose is 37 deg at that mu_p
(docs/scientific_rationale/06_rolling_resistance.md, step 3).

The scenario is the grid's base with these values, a ``calibrate`` run that
pours and settles its own bed (rolling resistance is part of an IC's
material-set id, so the grid's shared IC does not fit) and records 2
revolutions. Replicates (V12) are run with ``--seed`` 0, 1, 2. Run from the
repository root with the project environment::

    python scripts/calibration/make_final_scenario.py --mu-r 0.17
"""

import argparse
import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "configs" / "simulation" / "calibration" / "final"
MU_P = 0.3
MU_W = 0.5


def _grid_module():
    """Import make_grid_scenarios.py (same folder) as a module."""
    spec = importlib.util.spec_from_file_location(
        "make_grid_scenarios", Path(__file__).with_name("make_grid_scenarios.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None):
    """Write the final scenario; print its path."""
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--mu-r", type=float, required=True, help="Re-fitted rolling resistance.")
    args = p.parse_args(argv)
    grid = _grid_module()
    base = json.loads((grid.REPO_ROOT / grid.BASE).read_text())
    data = grid.grid_scenario(base, MU_P, MU_W, grid.IC_DIR, 2.0)
    data["name"] = f"cal_final_mup{grid.tag(MU_P)}_muw{grid.tag(MU_W)}_mur{grid.tag(args.mu_r)}"
    data["run"] = {"type": "calibrate"}
    data["contact"]["rolling_resistance"] = args.mu_r
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{data['name']}.json"
    path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"wrote {path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path}")


if __name__ == "__main__":
    main()

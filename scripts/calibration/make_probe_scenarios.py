"""Write the probe scenarios that follow the 3 x 3 friction grid (2026-11-07).

The grid (``make_grid_scenarios.py``) left the bulk toe at 240-242 deg and
the shoulder at 36-41 deg against SAG_A's 214 / 27 deg, with mu_w hardly
mattering and mu_p moving the angles ~1 deg per 0.1. Two probes, each one
change from the best grid point (mu_p 0.3, mu_w 0.5, mu_r 0.13), test the
two remaining levers (docs/scientific_rationale/05_friction.md,
06_rolling_resistance.md):

- ``probe_mup0p1_muw0p5``: lower particle friction, mu_p = 0.1;
- ``probe_mup0p3_muw0p5_mur0p08``: lower rolling resistance, mu_r = 0.08
  (the 33 deg end of the repose band, the V11e value).

Same spin-up rule and 2-revolution record as the grid. Probe A loads the
grid's shared IC (only friction differs). Probe B cannot: rolling
resistance is part of the IC's material-set id (only friction may differ
when an IC is shared), so it pours and settles its own bed (a plain
``calibrate`` run, same seed and pour as the IC; ~1 h longer); the
spin-up to steady state removes the bed's memory of how it was made. Written to
``configs/simulation/calibration/probes/``. Run from the repository root
with the project environment::

    python scripts/calibration/make_probe_scenarios.py
"""

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "configs" / "simulation" / "calibration" / "probes"
#: (name, mu_p, mu_w, mu_r) of each probe.
PROBES = (
    ("probe_mup0p1_muw0p5", 0.1, 0.5, 0.13),
    ("probe_mup0p3_muw0p5_mur0p08", 0.3, 0.5, 0.08),
)


def _grid_module():
    """Import make_grid_scenarios.py (same folder) as a module."""
    spec = importlib.util.spec_from_file_location(
        "make_grid_scenarios", Path(__file__).with_name("make_grid_scenarios.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    """Write the probe scenarios; print one line per file."""
    grid = _grid_module()
    base = json.loads((REPO_ROOT / grid.BASE).read_text())
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, mu_p, mu_w, mu_r in PROBES:
        data = grid.grid_scenario(base, mu_p, mu_w, grid.IC_DIR, 2.0)
        data["name"] = name
        data["contact"]["rolling_resistance"] = mu_r
        if mu_r != base["contact"]["rolling_resistance"]:
            data["run"] = {"type": "calibrate"}
        path = OUT_DIR / f"{name}.json"
        path.write_text(json.dumps(data, indent=2) + "\n")
        print(f"wrote {path.relative_to(REPO_ROOT)}  (mu_p {mu_p}, mu_w {mu_w}, mu_r {mu_r})")


if __name__ == "__main__":
    main()

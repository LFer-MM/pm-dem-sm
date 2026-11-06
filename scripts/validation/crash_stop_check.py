r"""Crash-stop check of a turning charge: J after stopping the mill (YADE).

docs/scientific_rationale/13_initial_conditions.md (pilot run). A poured,
settled starting packing (``make_ic``) packs denser than the plant's
crash-stopped charge, so its J at rest is below the plant's Jc with the
grind-out counts (pilot: 0.2588 vs 0.276). This checks that the same
packing, once it has turned, gives the plant's J when stopped like the
plant (and like the grind-out, C12-3):

1. load a checkpoint of a turning charge (default: the end of a
   ``dataset`` run's record stage);
2. stop the mill, settle undamped by the geometric rule and measure J and
   phi -- :func:`pm_dem_sm.simulation.yade_dem.grind_out.crash_stop`, the
   grind-out's own step;
3. compare with the grind-out (0.2766 +- 0.0006) and the plant target
   (0.276 +- 0.005), and with the starting packing's J at rest.

The run directory is not modified; the result goes to
``data/raw/validation/results/crash_stop/<run>_<stage>.json``.

Run from the repository root::

    yadedaily -n -x -j 16 scripts/validation/crash_stop_check.py \
        data/raw/yade_runs/sag_a_dataset_rmic_s0
"""

from pathlib import Path
import sys

_REPO_ROOT = str(Path(sys.argv[0]).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import argparse
import json
import math

from yade.wrapper import O

from pm_dem_sm.simulation.scenario import SimulationScenario
from pm_dem_sm.simulation.yade_dem import grind_out, run_simulation

# --- Constants ---------------------------------------------------------------

#: Grind-out J with the default counts, mean of 3 seeds (C12-3).
GRIND_OUT_J = 0.2766
#: Stages in which the mill turns.
ROTATING_STAGES = ("spinup", "record")


# --- Public functions --------------------------------------------------------


def revolutions_before(manifest, scenario, t):
    """Return the mill revolutions from the first rotating stage's start to time ``t``."""
    done = manifest["stages"]
    starts = [done[s]["sim_time_start_s"] for s in ROTATING_STAGES if s in done]
    if not starts:
        return 0.0
    return scenario.mill.speed_rpm / 60.0 * (t - min(starts))


def check(run_dir, stage="record"):
    """Load ``stage``'s checkpoint of ``run_dir``, crash-stop it and return the result dict."""
    run_dir = Path(run_dir)
    manifest = run_simulation._read_manifest(run_dir)
    scenario = SimulationScenario.from_dict(manifest["scenario"])
    run_simulation._load_checkpoint(run_dir, stage, manifest)
    t_stop = float(O.time)
    settle, escaped, fill = grind_out.crash_stop(scenario)
    ic = manifest.get("initial_condition", {})
    j = fill["J"]
    return {
        "run": run_dir.name,
        "stage": stage,
        "stopped_at_s": t_stop,
        "revolutions_before_stop": revolutions_before(manifest, scenario, t_stop),
        "J": j,
        "phi": fill["phi"],
        "free_bulk_area_m2": fill["free_bulk_area_m2"],
        "escaped": escaped,
        "settle_after_stop": settle,
        "starting_packing": {"name": ic.get("name"), "J": ic.get("J"), "phi": ic.get("phi")},
        "grind_out_J": GRIND_OUT_J,
        "target_Jc": grind_out.JC_TARGET,
        "within_target": abs(j - grind_out.JC_TARGET) <= grind_out.TOLERANCE,
        "material_set_id": scenario.material_set_id(),
    }


# --- Private helper functions ------------------------------------------------


def _parse_args(argv):
    """Parse this script's command line."""
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("run_dir", help="Run directory whose checkpoint to stop.")
    p.add_argument("--stage", default="record", help="Checkpoint stage (default: record).")
    p.add_argument("--out", default=None, help="Result JSON (default: results/crash_stop/).")
    return p.parse_args(argv)


# --- Script entry point ------------------------------------------------------

if __name__ == "__main__":
    _args = _parse_args(sys.argv[1:])
    _res = check(_args.run_dir, _args.stage)
    _out = Path(
        _args.out
        or Path(_REPO_ROOT)
        / "data/raw/validation/results/crash_stop"
        / f"{_res['run']}_{_res['stage']}.json"
    )
    _out.parent.mkdir(parents=True, exist_ok=True)
    _out.write_text(json.dumps(_res, indent=2, default=str), encoding="utf-8")
    print(
        f"[crash-stop] {_res['run']} ({_res['stage']}, {_res['revolutions_before_stop']:.2f} rev): "
        f"J = {_res['J']:.4f}, phi = {_res['phi']:.4f} (starting packing J = "
        f"{_res['starting_packing']['J']}, grind-out {GRIND_OUT_J}, target "
        f"{grind_out.JC_TARGET} +- {grind_out.TOLERANCE}: "
        f"{'within' if _res['within_target'] else 'OUTSIDE'}); settle "
        f"{_res['settle_after_stop']['reason']} after "
        f"{_res['settle_after_stop']['settle_time_s']:.1f} s; escaped {_res['escaped']}"
    )
    print(f"[crash-stop] -> {_out}")
    if not math.isfinite(_res["J"]):
        sys.exit(1)

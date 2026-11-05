r"""Simulated grind-out and crash stop: particle counts for the target fill levels (YADE).

docs/scientific_rationale/12_charge_fill_and_particles.md (C12-3, V16). The
counts are set by matching the charge **surface** (Morrell's J, measured
from the stopped bed), not by an assumed packing:

1. **Ball stage (grind-out analogue):** balls only; fill, settle, run
   ``--revolutions`` at the scenario speed, stop, settle (geometric rule,
   damping 0), measure J. Rescale the ball count (J nearly proportional to
   the count) until J is within ``--tol`` of Jb.
2. **Mixed stage (crash-stop analogue):** that ball count plus rocks,
   poured randomly mixed; the same cycle; iterate the rock count until J is
   within ``--tol`` of Jc.
3. Repeat for each seed; report counts, J and the packing fraction phi
   (solid volume / bulk volume between the lifters) with their spread.

Each cycle runs the stages build -> fill -> settle -> spinup of
:mod:`~pm_dem_sm.simulation.yade_dem.run_simulation` (so every per-stage
check applies), with spin-up fixed to ``--revolutions``, then stops the mill,
settles and measures J with :func:`pm_dem_sm.simulation.checks.fill_level`.

Run it with YADE (hours at full scale)::

    yadedaily -n -x -j 16 grind_out.py --scenario configs/simulation/sag_slice_lifters.json \\
        --out-dir data/raw/grind_out --seeds 0 1 2
"""

from pathlib import Path
import sys

_SCRIPT = Path(__file__ if __file__.endswith("grind_out.py") else sys.argv[0])
_REPO_ROOT = str(_SCRIPT.resolve().parents[3])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import argparse
import json
import math
import statistics

from yade.wrapper import O

from pm_dem_sm.simulation import checks, mill_geometry
from pm_dem_sm.simulation.scenario import load_scenario
from pm_dem_sm.simulation.yade_dem import diagnostics, engines, monitor, run_simulation

# --- Constants ---------------------------------------------------------------

#: Target ball and total fill levels, SAG_A (docs/scientific_rationale/12_...).
JB_TARGET = 0.188
JC_TARGET = 0.276
#: Accepted |J - target| (0.5 points).
TOLERANCE = 0.005
#: Mill revolutions before the stop (the procedure says 2-3).
REVOLUTIONS = 2.0
#: Maximum count iterations per stage.
MAX_ITERATIONS = 5


# --- Public functions --------------------------------------------------------


def cycle(base, out_dir, label, n_balls, n_rocks, seed, revolutions):
    """Run one fill / turn / stop / settle cycle and measure J.

    Args:
        base: Scenario as a dict (``to_dict()``); copied, not modified.
        out_dir: Directory for this cycle's run directory and scenario.
        label: Run name.
        n_balls: Ball count.
        n_rocks: Rock count.
        seed: Placement seed.
        revolutions: Revolutions before the stop.

    Returns:
        dict: Counts, J, phi, free bulk area, settle result, wall time per stage.
    """
    data = json.loads(json.dumps(base))
    data["name"] = label
    data["seed"] = seed
    for s in data["species"]:
        s["count"] = n_balls if s["material"] == "steel" else n_rocks
    data["spinup"].update(
        min_revolutions=revolutions,
        max_revolutions=revolutions,
        angle_tol_deg=0.0,
        power_rel_tol=0.0,
    )
    run_dir = Path(out_dir) / label
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "scenario.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    O.reset()
    manifest = run_simulation.run(str(path), str(run_dir), to_stage="spinup")
    scenario = load_scenario(path)

    # Crash stop, then settle undamped by the geometric rule.
    engines._get_rotation_engine().angularVelocity = 0.0
    engines.assert_no_damping()
    o = scenario.settle
    settle = monitor.run_until_settled(
        2.0 * scenario.small.radius_m,
        o.max_time_s,
        0.5 * (scenario.small.radius_m + scenario.large.radius_m),
        o.sample_s,
        window_s=o.window_s,
        angle_tol_deg=o.angle_tol_deg,
        height_tol_rel_d=o.height_tol_rel_d,
        speed_tol_m_s=o.speed_tol_m_s,
    )
    spheres = diagnostics.spheres()
    escaped = diagnostics.count_escapes(
        scenario.mill.shell_diameter_m / 2.0, scenario.mill.depth_m
    )
    profile = mill_geometry.liner_profile(scenario.mill)
    fill = checks.fill_level(
        spheres, scenario.mill.diameter_m / 2.0, scenario.mill.depth_m, liner_profile=profile
    )
    result = {
        "label": label,
        "seed": seed,
        "n_balls": n_balls,
        "n_rocks": n_rocks,
        "J": fill["J"],
        "phi": fill["phi"],
        "free_bulk_area_m2": fill["free_bulk_area_m2"],
        "escaped": escaped,
        "settle_after_stop": settle,
        "stage_wall_s": {k: v["wall_s"] for k, v in manifest["stages"].items()},
    }
    (run_dir / "fill_level.json").write_text(
        json.dumps({**result, "surface": fill["surface"]}, indent=2), encoding="utf-8"
    )
    print(
        f"[grind-out] {label}: {n_balls} balls + {n_rocks} rocks -> J = {fill['J']:.4f}, "
        f"phi = {fill['phi']:.4f} (settle: {settle['reason']} after "
        f"{settle['settle_time_s']:.1f} s)"
    )
    return result


def run_seed(
    base,
    out_dir,
    seed,
    n_balls,
    n_rocks,
    jb=JB_TARGET,
    jc=JC_TARGET,
    tol=TOLERANCE,
    revolutions=REVOLUTIONS,
    max_iterations=MAX_ITERATIONS,
):
    """Run the ball stage then the mixed stage for one seed.

    Returns:
        dict: Every cycle, the final ball and rock counts, J of each stage and
        whether both converged.
    """
    cycles = []
    ball = None
    for k in range(max_iterations):
        ball = cycle(base, out_dir, f"seed{seed}_balls_{k}", n_balls, 0, seed, revolutions)
        cycles.append(ball)
        if checks.fill_converged(ball["J"], jb, tol):
            break
        n_balls = checks.next_ball_count(n_balls, ball["J"], jb)
    mixed = None
    for k in range(max_iterations):
        mixed = cycle(base, out_dir, f"seed{seed}_mixed_{k}", n_balls, n_rocks, seed, revolutions)
        cycles.append(mixed)
        if checks.fill_converged(mixed["J"], jc, tol):
            break
        n_rocks = checks.next_rock_count(n_rocks, mixed["J"], ball["J"], jc)
    return {
        "seed": seed,
        "cycles": cycles,
        "n_balls": n_balls,
        "n_rocks": n_rocks,
        "J_balls": ball["J"],
        "J_total": mixed["J"],
        "phi_balls": ball["phi"],
        "phi_total": mixed["phi"],
        "converged": checks.fill_converged(ball["J"], jb, tol)
        and checks.fill_converged(mixed["J"], jc, tol),
    }


def summarize(seeds):
    """Return mean and standard deviation of the final counts, J and phi over the seeds."""
    out = {}
    for key in ("n_balls", "n_rocks", "J_balls", "J_total", "phi_balls", "phi_total"):
        vals = [s[key] for s in seeds]
        out[key] = {
            "mean": statistics.fmean(vals),
            "sd": statistics.stdev(vals) if len(vals) > 1 else 0.0,
            "values": vals,
        }
    return out


# --- Private helper functions ------------------------------------------------


def _parse_args(argv):
    """Parse this script's command line."""
    p = argparse.ArgumentParser(description="Grind-out / crash-stop particle counts (C12-3).")
    p.add_argument("--scenario", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    p.add_argument("--revolutions", type=float, default=REVOLUTIONS)
    p.add_argument("--tol", type=float, default=TOLERANCE)
    p.add_argument("--jb", type=float, default=JB_TARGET)
    p.add_argument("--jc", type=float, default=JC_TARGET)
    p.add_argument("--max-iterations", type=int, default=MAX_ITERATIONS)
    return p.parse_args(argv)


# --- Script entry point ------------------------------------------------------

if __name__ == "__main__":
    _args = _parse_args(sys.argv[1:])
    _scenario = load_scenario(_args.scenario)
    _scenario.validate()
    _base = _scenario.to_dict()
    _counts = {s.material: s.count for s in _scenario.species}
    _out_dir = Path(_args.out_dir)
    _out_dir.mkdir(parents=True, exist_ok=True)
    _seeds = []
    _n_balls, _n_rocks = _counts["steel"], _counts["rock"]
    for _seed in _args.seeds:
        _res = run_seed(
            _base,
            _out_dir,
            _seed,
            _n_balls,
            _n_rocks,
            _args.jb,
            _args.jc,
            _args.tol,
            _args.revolutions,
            _args.max_iterations,
        )
        _seeds.append(_res)
        # Start the next seed from this seed's counts.
        _n_balls, _n_rocks = _res["n_balls"], _res["n_rocks"]
        _summary = {
            "scenario": _args.scenario,
            "targets": {"Jb": _args.jb, "Jc": _args.jc},
            "tolerance": _args.tol,
            "revolutions": _args.revolutions,
            "seeds": _seeds,
            "summary": summarize(_seeds),
            "slice_volume_m3": math.pi
            * (_scenario.mill.diameter_m / 2) ** 2
            * _scenario.mill.depth_m,
        }
        (_out_dir / "grind_out.json").write_text(
            json.dumps(_summary, indent=2, default=str), encoding="utf-8"
        )
    print(f"[grind-out] -> {_out_dir / 'grind_out.json'}")

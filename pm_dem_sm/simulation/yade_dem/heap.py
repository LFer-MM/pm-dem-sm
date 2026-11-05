r"""Angle-of-repose (heap) test for the rolling-resistance coefficient mu_r (YADE).

docs/scientific_rationale/06_rolling_resistance.md (C06-3, C06-4): mu_r is
fixed by reproducing the repose angle of the ore (37 deg; 33 / 41 deg for
the sensitivity band) with a rock-only heap, independently of the mill.
Test design (Open items of 06): rock-only spheres of the simulated rock
size, a rough base of fixed rock spheres, a lifted cylinder, a pile about
20 particle diameters across, damping 0, the run's dt, moduli and contact
law (per-pair friction mu_p, rolling resistance, krot); the slope is fitted
to the surface particles (:func:`pm_dem_sm.simulation.checks.repose_angle`).

Procedure per run: fill a frictionless cylinder (end-wall material) by
random sequential addition, settle (geometric rule), lift the cylinder at
``--lift-speed`` until it clears the pile, remove it, settle again, fit
the slope. The final mean speed is recorded (C06-4: the heap reaches rest
with rolling resistance and damping 0).

Run it with YADE::

    # one heap at a given mu_r
    yadedaily -n -x heap.py --scenario configs/simulation/x.json --mu-r 0.3 --out heap.json
    # bisection on mu_r for a target angle
    yadedaily -n -x heap.py --scenario configs/simulation/x.json --target 37 --out heap.json
"""

from pathlib import Path
import sys

_SCRIPT = Path(__file__ if __file__.endswith("heap.py") else sys.argv[0])
_REPO_ROOT = str(_SCRIPT.resolve().parents[3])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import argparse
import json
import math
import random
import time

from yade import Vector3
from yade.utils import facet, sphere
from yade.wrapper import O

from pm_dem_sm.simulation import checks
from pm_dem_sm.simulation.scenario import END_WALL_MATERIAL, load_scenario
from pm_dem_sm.simulation.yade_dem import engines, materials, monitor, stl
from pm_dem_sm.simulation.yade_dem.version import check_yade_version

# --- Constants ---------------------------------------------------------------

#: Cylinder inner radius in rock diameters (diameter 10 d).
CYLINDER_RADIUS_D = 5.0
#: Rough-base radius in rock diameters.
BASE_RADIUS_D = 17.0
#: Number of rock spheres poured.
N_ROCKS = 900
#: Solid fraction of the random sequential addition inside the cylinder.
RSA_FRACTION = 0.30
#: Cylinder lifting speed (m/s).
LIFT_SPEED_M_S = 0.05
#: Facet segments around the cylinder.
CYLINDER_SEGMENTS = 48
#: Azimuthal sectors fitted separately (spread of one heap).
SECTORS = 8
#: Settling time cap (s).
SETTLE_MAX_S = 15.0


# --- Public functions --------------------------------------------------------


def build_heap_scene(scenario, mu_r, seed=0, n_rocks=N_ROCKS):
    """Build base, floor, cylinder and rock charge; return the cylinder ids and rock radius.

    Args:
        scenario: Scenario giving the rock species, materials, contact law and dt.
        mu_r: Rolling-resistance coefficient for this heap.
        seed: RNG seed of the random sequential addition.
        n_rocks: Number of rock spheres.

    Returns:
        tuple[list[int], float, float]: Cylinder facet ids, rock radius,
        height of the base top (m).
    """
    O.reset()
    materials.MATERIALS_MAP.clear()
    scenario.contact.rolling_resistance = mu_r
    tables = scenario.contact_tables()
    materials.initialize_simulation_materials(
        tables["materials"], young_scale=scenario.solver.young_scale
    )
    rock = next(s for s in scenario.species if s.material == "rock")
    r = rock.radius_m
    d = 2.0 * r

    # Floor under everything, then a hexagonal layer of fixed rock spheres.
    big = 3.0 * BASE_RADIUS_D * d
    for tri in (
        [(-big, -big, 0), (big, -big, 0), (big, big, 0)],
        [(-big, -big, 0), (big, big, 0), (-big, big, 0)],
    ):
        O.bodies.append(facet(tri, material="rock", fixed=True, wire=True))
    r_base = BASE_RADIUS_D * d
    row = 0
    y = -r_base
    while y <= r_base:
        x = -r_base + (r if row % 2 else 0.0)
        while x <= r_base:
            if math.hypot(x, y) <= r_base:
                O.bodies.append(
                    sphere((x, y, r), r, material="rock", fixed=True, color=(0.5, 0.5, 0.5))
                )
            x += d
        y += d * math.sqrt(3) / 2
        row += 1
    base_top = 2.0 * r

    # Frictionless cylinder (end-wall material), open at both ends.
    rc = CYLINDER_RADIUS_D * d
    height = n_rocks * 4 / 3 * math.pi * r**3 / (RSA_FRACTION * math.pi * rc**2) + 2 * d
    cyl = []
    for k in range(CYLINDER_SEGMENTS):
        a0 = 2 * math.pi * k / CYLINDER_SEGMENTS
        a1 = 2 * math.pi * (k + 1) / CYLINDER_SEGMENTS
        p0 = (rc * math.cos(a0), rc * math.sin(a0))
        p1 = (rc * math.cos(a1), rc * math.sin(a1))
        z0, z1 = base_top * 0.5, base_top + height
        for tri in ([(*p0, z0), (*p1, z0), (*p1, z1)], [(*p0, z0), (*p1, z1), (*p0, z1)]):
            cyl.append(
                O.bodies.append(
                    facet(tri, material=END_WALL_MATERIAL, fixed=True, wire=True, color=(0, 1, 0))
                )
            )

    # Random sequential addition of the rocks inside the cylinder.
    rng = random.Random(seed)
    placed = []
    grid = {}
    attempts = 0
    while len(placed) < n_rocks and attempts < 200 * n_rocks:
        attempts += 1
        rho = (rc - r * 1.05) * math.sqrt(rng.random())
        phi = 2 * math.pi * rng.random()
        p = (rho * math.cos(phi), rho * math.sin(phi), base_top + r + rng.random() * (height - d))
        key = tuple(math.floor(c / d) for c in p)
        clash = False
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for q in grid.get((key[0] + dx, key[1] + dy, key[2] + dz), ()):
                        if math.dist(p, q) < d:
                            clash = True
                            break
        if clash:
            continue
        placed.append(p)
        grid.setdefault(key, []).append(p)
    for p in placed:
        O.bodies.append(sphere(p, r, material="rock", color=(1, 0, 0)))

    stl.SAG_MILL_SLICE_BODY_GROUP = []
    engines.initialize_engines(
        contact_model=scenario.contact.model,
        contact_model_params={
            "restitution": materials.pair_matchmaker(tables["restitution"]),
            "friction_angle": materials.pair_matchmaker(tables["friction"]),
            "rolling_resistance": mu_r,
            "rolling_stiffness": scenario.rolling_stiffness(),
        },
    )
    newton = next(e for e in O.engines if getattr(e, "label", None) == "newton_integrator")
    newton.gravity = (0, 0, -9.81)
    O.dt = scenario.time_step_s()
    engines.assert_no_damping()
    return cyl, r, base_top


def run_heap(scenario, mu_r, seed=0, lift_speed=LIFT_SPEED_M_S, n_rocks=N_ROCKS):
    """Build, pour, lift and measure one heap; return its result.

    Args:
        scenario: Scenario (rock species, materials, contact law, dt).
        mu_r: Rolling-resistance coefficient.
        seed: RNG seed.
        lift_speed: Cylinder lifting speed (m/s).
        n_rocks: Number of rock spheres.

    Returns:
        dict: ``mu_r``, ``seed``, the :func:`~pm_dem_sm.simulation.checks.repose_angle`
        result, the final mean speed, settle results and wall time.
    """
    t_wall = time.time()
    cyl, r, base_top = build_heap_scene(scenario, mu_r, seed, n_rocks)
    d = 2.0 * r
    big_r = 10.0  # all rocks count as "small" for the bed state
    first = monitor.run_until_settled(d, SETTLE_MAX_S, big_r)

    for i in cyl:
        O.bodies[i].state.vel = Vector3(0, 0, lift_speed)
    while True:
        O.run(max(1, round(0.05 / O.dt)), True)
        tops = [b.state.pos[2] + b.shape.radius for b in _free_rocks()]
        bottom = min(O.bodies[i].state.pos[2] for i in cyl)
        if bottom > max(tops) + d:
            break
    for i in cyl:
        O.bodies.erase(i)
    final = monitor.run_until_settled(d, SETTLE_MAX_S, big_r)

    rocks = [
        (b.state.pos[0], b.state.pos[1], b.state.pos[2], b.shape.radius) for b in _free_rocks()
    ]
    on_base = [
        s for s in rocks if math.hypot(s[0], s[1]) <= BASE_RADIUS_D * d and s[2] > base_top - r
    ]
    # Whole-heap fit (half-diameter bins) plus per-sector fits for the spread.
    fit = checks.repose_angle(on_base, base_z=base_top, bin_width=r)
    sectors = checks.repose_angle_sectors(on_base, SECTORS, base_z=base_top, bin_width=r)
    speeds = [b.state.vel.norm() for b in _free_rocks()]
    return {
        "mu_r": mu_r,
        "seed": seed,
        **fit,
        "sector_angles_deg": sectors["angles_deg"],
        "sector_mean_deg": sectors["mean_deg"],
        "sector_sd_deg": sectors["sd_deg"],
        "spheres": [[round(v, 5) for v in s] for s in rocks],
        "n_rocks": len(rocks),
        "n_off_base": len(rocks) - len(on_base),
        "final_mean_speed_m_s": sum(speeds) / len(speeds),
        "settle_before_lift": first,
        "settle_after_lift": final,
        "wall_s": time.time() - t_wall,
    }


def find_mu_r(scenario, target_deg, lo=0.0, hi=1.0, tol_deg=0.5, max_runs=10, seed=0, log=None):
    """Bisect mu_r so that the heap angle is within ``tol_deg`` of ``target_deg``.

    Args:
        scenario: Scenario.
        target_deg: Target repose angle (deg).
        lo: Lower bracket of mu_r.
        hi: Upper bracket of mu_r.
        tol_deg: Accepted angle error (deg).
        max_runs: Maximum heap runs.
        seed: RNG seed of every run.
        log: List the run results are appended to.

    Returns:
        dict: ``mu_r`` (best), ``angle_deg`` (its angle), ``converged``, ``runs``.
    """
    runs = [] if log is None else log
    best = None
    for _ in range(max_runs):
        mid = 0.5 * (lo + hi)
        res = run_heap(scenario, mid, seed)
        runs.append(res)
        print(
            f"[heap] target {target_deg}: mu_r = {mid:.4f} -> {res['angle_deg']:.2f} deg "
            f"(R2 {res['r2']:.3f}, {res['wall_s']:.0f} s)"
        )
        if best is None or abs(res["angle_deg"] - target_deg) < abs(
            best["angle_deg"] - target_deg
        ):
            best = res
        if abs(res["angle_deg"] - target_deg) <= tol_deg:
            break
        if res["angle_deg"] < target_deg:
            lo = mid
        else:
            hi = mid
    return {
        "target_deg": target_deg,
        "mu_r": best["mu_r"],
        "angle_deg": best["angle_deg"],
        "converged": abs(best["angle_deg"] - target_deg) <= tol_deg,
        "runs": [r for r in runs if r.get("seed") == seed],
    }


# --- Private helper functions ------------------------------------------------


def _free_rocks():
    """Yield the non-fixed spheres."""
    for b in O.bodies:
        if b and type(b.shape).__name__ == "Sphere" and not b.state.blockedDOFs:
            yield b


def _parse_args(argv):
    """Parse this script's command line."""
    p = argparse.ArgumentParser(description="Angle-of-repose heap test (C06-3).")
    p.add_argument("--scenario", required=True)
    p.add_argument("--out", required=True)
    p.add_argument(
        "--mu-r", type=float, nargs="+", default=None, help="Run one heap per value (and seed)."
    )
    p.add_argument(
        "--target",
        type=float,
        nargs="+",
        default=None,
        help="Bisect mu_r for each target angle (deg).",
    )
    p.add_argument("--seeds", type=int, nargs="+", default=[0])
    p.add_argument("--hi", type=float, default=1.0, help="Upper bracket of the bisection.")
    return p.parse_args(argv)


# --- Script entry point ------------------------------------------------------

if __name__ == "__main__":
    import yade

    check_yade_version(str(getattr(yade.config, "version", "unknown")))
    _args = _parse_args(sys.argv[1:])
    _scenario = load_scenario(_args.scenario)
    _scenario.validate()
    _out = {
        "scenario": _args.scenario,
        "dt_s": _scenario.time_step_s(),
        "particle_friction": _scenario.contact.particle_friction,
        "results": [],
    }
    for _seed in _args.seeds:
        for _mu in _args.mu_r or []:
            _res = run_heap(_scenario, _mu, _seed)
            print(
                f"[heap] mu_r = {_mu} seed {_seed}: {_res['angle_deg']:.2f} deg, sectors "
                f"{_res['sector_mean_deg']:.2f} +- {_res['sector_sd_deg']:.2f} deg"
            )
            _out["results"].append(_res)
        for _target in _args.target or []:
            _out["results"].append(find_mu_r(_scenario, _target, hi=_args.hi, seed=_seed))
        Path(_args.out).write_text(json.dumps(_out, indent=2, default=str), encoding="utf-8")
    print(f"[heap] -> {_args.out}")

r"""V1 restitution recovery: one binary collision per material pair at the run's dt (YADE).

docs/scientific_rationale/16_validation_checks.md (V1, C01-4): "If the
integration is accurate then the coefficient of restitution ... should be
recovered" (Cleary 2001). For each particle-particle and particle-liner
pair of a scenario, two bodies collide head-on with gravity off -- two
spheres with the species' radii, or a sphere and a fixed liner facet --
using the scenario's materials, contact law (per-pair restitution and
friction, rolling resistance), moduli and dt, and the measured
``e = -v_n,after / v_n,before`` is compared with the input.

The recovered e depends on where within a time step the contact starts
(rock-rock at 14.5 m/s, ~25 steps per contact: +0.6 % to -4.7 %), and real
collisions start at random phases. Each pair and speed is therefore run at
``--phases`` contact-onset phases evenly spread over one step; the check
passes when the **mean** relative error is within ``--tolerance`` (2 %).
The range over phases is reported too. Results go to a JSON file.

Run it with YADE::

    yadedaily -n -x collision_check.py --scenario configs/simulation/x.json \\
        --out data/raw/checks/v1.json
"""

from pathlib import Path
import sys

_SCRIPT = Path(__file__ if __file__.endswith("collision_check.py") else sys.argv[0])
_REPO_ROOT = str(_SCRIPT.resolve().parents[3])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import argparse
import json

from yade import Vector3
from yade.utils import facet, sphere
from yade.wrapper import O

from pm_dem_sm.simulation import checks
from pm_dem_sm.simulation.scenario import load_scenario
from pm_dem_sm.simulation.yade_dem import engines, materials, stl
from pm_dem_sm.simulation.yade_dem.version import check_yade_version

# --- Constants ---------------------------------------------------------------

#: Default relative tolerance on the recovered e.
TOLERANCE = 0.02
#: Default normal impact speeds tested (m/s): slow, typical, and the
#: free-fall worst case of the scenario is added on top.
SPEEDS_M_S = (1.0, 5.0)
#: Default number of contact-onset phases per pair and speed.
PHASES = 8


# --- Public functions --------------------------------------------------------


def collide(scenario, tables, krot, mat_a, mat_b, r_a, r_b, speed, gap=1e-4):
    """Collide body ``a`` (sphere) with ``b`` (sphere, or a fixed facet if ``r_b`` is ``None``).

    Args:
        scenario: The :class:`~pm_dem_sm.simulation.scenario.SimulationScenario`.
        tables: Its :meth:`contact_tables`.
        krot: Rolling stiffness (N m/rad).
        mat_a: Material label of body ``a``.
        mat_b: Material label of body ``b``.
        r_a: Radius of sphere ``a`` (m).
        r_b: Radius of sphere ``b`` (m), or ``None`` for a wall.
        speed: Normal approach speed (m/s).
        gap: Initial surface gap (m).

    Returns:
        dict: Input and measured e, relative error and contact duration in steps.
    """
    O.reset()
    materials.MATERIALS_MAP.clear()
    materials.initialize_simulation_materials(
        tables["materials"], young_scale=scenario.solver.young_scale
    )

    if r_b is None:
        b = O.bodies.append(
            facet(
                [Vector3(0, -1, -1), Vector3(0, 1, -1), Vector3(0, 0, 2)],
                material=mat_b,
                fixed=True,
            )
        )
        a = O.bodies.append(sphere((-r_a - gap, 0, 0), r_a, material=mat_a))
        O.bodies[a].state.vel = Vector3(speed, 0, 0)
    else:
        a = O.bodies.append(sphere((-r_a - gap / 2, 0, 0), r_a, material=mat_a))
        b = O.bodies.append(sphere((r_b + gap / 2, 0, 0), r_b, material=mat_b))
        O.bodies[a].state.vel = Vector3(speed / 2, 0, 0)
        O.bodies[b].state.vel = Vector3(-speed / 2, 0, 0)
    stl.SAG_MILL_SLICE_BODY_GROUP = []
    engines.initialize_engines(
        contact_model=scenario.contact.model,
        contact_model_params={
            "restitution": materials.pair_matchmaker(tables["restitution"]),
            "friction_angle": materials.pair_matchmaker(tables["friction"]),
            "rolling_resistance": scenario.contact.rolling_resistance,
            "rolling_stiffness": krot,
        },
    )
    next(e for e in O.engines if getattr(e, "label", None) == "newton_integrator").gravity = (
        0,
        0,
        0,
    )
    O.dt = scenario.time_step_s()

    def v_rel():
        return O.bodies[b].state.vel[0] - O.bodies[a].state.vel[0]

    before = v_rel()
    touched, steps = False, 0
    for _ in range(200000):
        O.step()
        real = any(i.isReal for i in O.interactions)
        if real:
            touched = True
            steps += 1
        elif touched:
            break
    after = v_rel()
    e_in = scenario.restitution_for(
        mat_a, mat_b if r_b is not None else scenario.mill.liner_material
    )
    e = checks.restitution(before, after)
    return {
        "pair": f"{mat_a}-{mat_b}",
        "speed_m_s": speed,
        "e_input": e_in,
        "e_measured": e,
        "rel_error": (e - e_in) / e_in,
        "contact_steps": steps,
    }


def run(scenario_path, out_path, speeds=SPEEDS_M_S, tolerance=TOLERANCE, phases=PHASES):
    """Run V1 for every particle-particle and particle-liner pair; write and return the results.

    Args:
        scenario_path: Scenario JSON.
        out_path: Output JSON path.
        speeds: Normal impact speeds (m/s); the scenario's worst-case
            ``sqrt(2 g D)`` is added.
        tolerance: Relative tolerance on the phase-averaged e.
        phases: Contact-onset phases per pair and speed.

    Returns:
        dict: ``results`` (one per pair and speed: mean, min and max
        relative error over the phases), ``passed`` (bool).
    """
    import yade

    check_yade_version(str(getattr(yade.config, "version", "unknown")))
    scenario = load_scenario(scenario_path)
    scenario.validate()
    tables = scenario.contact_tables()
    krot = scenario.rolling_stiffness()
    radius = {s.material: s.radius_m for s in scenario.species}
    pairs = [(a, b, radius[a], radius[b]) for a, b in scenario._particle_pairs()]
    pairs += [(m, scenario.mill.liner_material, radius[m], None) for m in sorted(radius)]
    all_speeds = sorted({*speeds, round(scenario.impact_speed_m_s(), 2)})
    results = []
    dt = scenario.time_step_s()
    for mat_a, mat_b, r_a, r_b in pairs:
        for v in all_speeds:
            runs = [
                collide(
                    scenario,
                    tables,
                    krot,
                    mat_a,
                    mat_b,
                    r_a,
                    r_b,
                    v,
                    gap=1e-7 + (k / phases) * v * dt,
                )
                for k in range(phases)
            ]
            errs = [r["rel_error"] for r in runs]
            res = {
                "pair": runs[0]["pair"],
                "speed_m_s": v,
                "e_input": runs[0]["e_input"],
                "e_mean": sum(r["e_measured"] for r in runs) / phases,
                "rel_error_mean": sum(errs) / phases,
                "rel_error_min": min(errs),
                "rel_error_max": max(errs),
                "contact_steps": sorted({r["contact_steps"] for r in runs}),
            }
            res["passed"] = abs(res["rel_error_mean"]) <= tolerance
            print(
                f"[V1] {res['pair']:>12s} v = {v:5.2f} m/s: e = {res['e_mean']:.4f} "
                f"(input {res['e_input']}, mean {100 * res['rel_error_mean']:+.2f} %, "
                f"range {100 * min(errs):+.2f} .. {100 * max(errs):+.2f} %), "
                f"{res['contact_steps']} steps"
            )
            results.append(res)
    out = {
        "scenario": str(scenario_path),
        "dt_s": dt,
        "tolerance": tolerance,
        "phases": phases,
        "results": results,
        "passed": all(r["passed"] for r in results),
    }
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[V1] {'PASSED' if out['passed'] else 'FAILED'} -> {out_path}")
    return out


# --- Private helper functions ------------------------------------------------


def _parse_args(argv):
    """Parse this script's command line."""
    p = argparse.ArgumentParser(description="V1 binary-collision restitution check.")
    p.add_argument("--scenario", required=True, help="Scenario JSON.")
    p.add_argument("--out", required=True, help="Output JSON.")
    p.add_argument("--tolerance", type=float, default=TOLERANCE)
    p.add_argument("--speeds", type=float, nargs="+", default=list(SPEEDS_M_S))
    p.add_argument("--phases", type=int, default=PHASES)
    return p.parse_args(argv)


# --- Script entry point ------------------------------------------------------

if __name__ == "__main__":
    _args = _parse_args(sys.argv[1:])
    _result = run(_args.scenario, _args.out, _args.speeds, _args.tolerance, _args.phases)
    sys.exit(0 if _result["passed"] else 1)

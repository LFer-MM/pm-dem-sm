r"""Staged, headless DEM run of the SAG mill slice from a scenario JSON (YADE).

Runs the stages of :data:`pm_dem_sm.simulation.scenario.STAGES` in order:

1. ``build``  -- materials, mill liner (plates + lifters generated from the design
   parameters, see :mod:`~pm_dem_sm.simulation.mill_geometry`), engines, dt.
2. ``fill``   -- chord-box ingress of the bidisperse charge.
3. ``settle`` -- settling until the unbalanced force is small.
4. ``spinup`` -- rotation from rest until the charge angle and drive power
   stop changing (steady state), or ``max_revolutions``.
5. ``record`` -- frame CSVs every ``frame_interval_s`` for ``duration_s``.

Numerical damping is set explicitly to 0 in every stage (YADE's default
differs between versions; docs/scientific_rationale/04_numerical_damping.md).
YADE releases older than 2023.02 are refused at start-up
(:mod:`~pm_dem_sm.simulation.yade_dem.version`).

Each stage ends with a checkpoint ``<run-dir>/checkpoints/<stage>.yade.gz``
and an update of ``<run-dir>/manifest.json`` (scenario, derived checks, dt,
mill geometry with a mesh hash, YADE version, per-stage wall time and
outcome), so a run can resume from any stage with ``--from-stage``.
``<run-dir>/mill_log.csv`` logs the mill state throughout (see
:mod:`~pm_dem_sm.simulation.yade_dem.monitor`), ``<run-dir>/mill_liner.stl``
holds the liner for viewing, and ``<run-dir>/frames/`` holds the frames
``data_processing`` converts.

Run it with YADE, normally through
:func:`pm_dem_sm.simulation.launcher.launch_simulation`::

    yadedaily -n -x -j 8 run_simulation.py --scenario configs/simulation/x.json \\
        --run-dir data/raw/yade_runs/x

YADE executes this file as a script, so it puts the repository root on
``sys.path`` itself. It imports every concern module unaliased so the
``PyRunner`` command strings (``engines._balance_check()``,
``capture._record_frame()``, ``monitor._log_row()``) resolve in this
script's global namespace.
"""

from pathlib import Path
import sys

# Under ``yade -x`` this file is exec'd with YADE's own globals, where
# ``__file__`` names the yade executable; ``sys.argv[0]`` is this script.
_SCRIPT = Path(__file__ if __file__.endswith("run_simulation.py") else sys.argv[0])
_REPO_ROOT = str(_SCRIPT.resolve().parents[3])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import argparse
import json
import math
import time

import yade
from yade.wrapper import O

from pm_dem_sm.simulation import mill_geometry
from pm_dem_sm.simulation.scenario import STAGES, load_scenario
from pm_dem_sm.simulation.yade_dem import (  # noqa: F401
    capture,
    diagnostics,
    engines,
    materials,
    monitor,
    particles,
    state,
    stl,
)
from pm_dem_sm.simulation.yade_dem.version import check_yade_version

# --- Constants ---------------------------------------------------------------

#: ``NewtonIntegrator.damping`` in every stage
#: (docs/scientific_rationale/04_numerical_damping.md).
NUMERICAL_DAMPING = 0.0


# --- Public functions --------------------------------------------------------


def run(scenario_path=None, run_dir=None, from_stage="build", to_stage="record", gui=False):
    """Run stages ``from_stage`` .. ``to_stage`` of a scenario, checkpointing after each.

    Args:
        scenario_path: Scenario JSON; ``None`` uses the
            :class:`~pm_dem_sm.simulation.scenario.SimulationScenario` defaults.
            When resuming, ``None`` reuses the scenario stored in the manifest.
        run_dir: Output directory; defaults to ``data/raw/yade_runs/<name>``.
        from_stage: First stage to run; later than ``build`` loads the
            previous stage's checkpoint from ``run_dir``.
        to_stage: Last stage to run.
        gui: If ``True``, open the YADE Qt controller and 3D view.

    Returns:
        dict: The final manifest.

    Raises:
        RuntimeError: If the running YADE is older than 2023.02.
        ValueError: If the scenario is invalid (e.g. no
            ``contact.rolling_resistance``).
    """
    yade_version = str(getattr(yade.config, "version", "unknown"))
    check_yade_version(yade_version)
    print(f"[yade] version {yade_version}")
    first, last = STAGES.index(from_stage), STAGES.index(to_stage)
    if first > last:
        raise ValueError(f"from_stage {from_stage!r} comes after to_stage {to_stage!r}")

    resume_manifest = None
    if first > 0:
        if run_dir is None:
            raise ValueError("--run-dir is required when resuming from a later stage")
        resume_manifest = _read_manifest(Path(run_dir))
    if scenario_path is None and resume_manifest is not None:
        from pm_dem_sm.simulation.scenario import SimulationScenario

        scenario = SimulationScenario.from_dict(resume_manifest["scenario"])
    else:
        scenario = load_scenario(scenario_path)
    # The defaults are not validated on load; mu_r has no default.
    scenario.validate()

    run_dir = Path(run_dir or Path(_REPO_ROOT) / "data" / "raw" / "yade_runs" / scenario.name)
    (run_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
    manifest = resume_manifest or _new_manifest(scenario)
    manifest["scenario"] = scenario.to_dict()
    manifest["yade_version"] = yade_version
    for w in manifest["warnings"]:
        print(f"[scenario] WARNING: {w}")

    if first > 0:
        _load_checkpoint(run_dir, STAGES[first - 1], manifest)

    if gui:
        from yade import qt

        qt.Controller()
        qt.View()

    for name in STAGES[first:last + 1]:
        print(f"\n=== Stage: {name} ===")
        t_wall = time.time()
        t_sim, it0 = float(O.time), int(O.iter)
        outcome = _stage_function(name)(scenario, run_dir, manifest) or {}
        O.save(str(run_dir / "checkpoints" / f"{name}.yade.gz"))
        manifest["stages"][name] = {
            "wall_s": time.time() - t_wall,
            "sim_time_start_s": t_sim,
            "sim_time_end_s": float(O.time),
            "iterations": int(O.iter) - it0,
            **outcome,
        }
        _write_manifest(run_dir, manifest)
        print(f"=== {name} done in {manifest['stages'][name]['wall_s']:.1f} s wall ===")

    return manifest


# --- Private helper functions ------------------------------------------------


def _stage_build(scenario, run_dir, manifest):
    """Register materials, build the mill and engines, and set dt."""
    tables = scenario.contact_tables()
    cap_material = tables["cap_material"]
    materials.initialize_simulation_materials(
        tables["materials"], young_scale=scenario.solver.young_scale
    )
    krot = scenario.rolling_stiffness()
    scenario.check_rolling_stiffness(krot)

    liner = mill_geometry.liner_triangles(scenario.mill)
    mill_ids = stl.initialize_parametric_mill(scenario.mill, cap_material, liner)
    manifest["mill_geometry"] = mill_geometry.geometry_summary(scenario.mill, liner)
    mill_geometry.write_stl(liner, run_dir / "mill_liner.stl")

    engines.initialize_engines(
        contact_model=scenario.contact.model,
        contact_model_params={
            "restitution": materials.pair_matchmaker(tables["restitution"]),
            "friction_angle": materials.pair_matchmaker(tables["friction"]),
            "rolling_resistance": scenario.contact.rolling_resistance,
            "rolling_stiffness": krot,
        },
        rotation_engine=True,
    )
    engines.set_dt(new_dt=scenario.time_step_s())
    engines.set_gravity_damping(NUMERICAL_DAMPING)

    manifest["mill_body_ids"] = list(mill_ids)
    manifest["dt_s"] = O.dt
    manifest["threads"] = O.numThreads
    manifest["contact_tables"] = {k: tables[k] for k in ("restitution", "friction")}
    manifest["rolling_stiffness"] = krot
    return {"n_mill_bodies": len(mill_ids)}


def _stage_fill(scenario, run_dir, manifest):
    """Pour the bidisperse charge in chord-box batches."""
    _start_monitor(scenario, run_dir, manifest, "fill", omega=0.0)
    engines.set_gravity_damping(NUMERICAL_DAMPING)
    small, large = scenario.small, scenario.large
    # Keep fill boxes inside the lifter tops, clear by one large radius.
    inner_d = 2.0 * (scenario.mill.lifter_top_radius_m - large.radius_m)
    ingress = particles.ingress_random if scenario.fill.method == "random" else (
        particles.ingress_segregated
    )
    ingress(
        diameter=inner_d,
        depth=scenario.mill.depth_m,
        r_small=small.radius_m,
        r_large=large.radius_m,
        n_small=small.count,
        n_large=large.count,
        box_height=scenario.fill.box_height_m,
        material_small=small.material,
        material_large=large.material,
        color_small=tuple(small.color),
        color_large=tuple(large.color),
        settle_steps=scenario.fill.settle_steps,
        seed=scenario.seed,
    )
    inv = diagnostics.get_particle_inventory(small.radius_m, large.radius_m)
    return {"inventory": inv}


def _stage_settle(scenario, run_dir, manifest):
    """Let the charge come to rest, undamped, before the mill starts turning."""
    _start_monitor(scenario, run_dir, manifest, "settle", omega=0.0)
    opts = scenario.settle
    engines.set_gravity_damping(NUMERICAL_DAMPING)
    balanced = engines.run_until_forces_balanced(
        threshold=opts.unbalanced_force,
        interval=opts.check_every,
        wait_chunk=opts.check_every,
        max_chunks=max(1, opts.max_steps // opts.check_every),
    )
    return {
        "balanced": bool(balanced),
        "unbalanced_force": engines.BALANCE_STATE["last_unb"],
        "max_overlap_rel": monitor.max_overlap(),
    }


def _stage_spinup(scenario, run_dir, manifest):
    """Rotate from rest until the mill log reaches steady state."""
    omega = _omega(scenario)
    engines.set_gravity_damping(NUMERICAL_DAMPING)
    engines._get_rotation_engine().angularVelocity = omega
    _start_monitor(scenario, run_dir, manifest, "spinup", omega=omega)

    opts = scenario.spinup
    rev_s = scenario.revolution_s()
    chunk = max(1, round(0.25 * opts.window_revolutions * rev_s / O.dt))
    t0 = float(O.time)
    result = None
    while True:
        O.run(chunk, True)
        revs = (float(O.time) - t0) / rev_s
        if revs >= opts.min_revolutions:
            result = monitor.steady_state(
                opts.window_revolutions * rev_s, opts.angle_tol_deg, opts.power_rel_tol
            )
            if result:
                print(
                    f"[spinup] rev {revs:.2f}: angle {result['angle_deg']:.2f} deg "
                    f"(change {result['angle_change_deg']:+.2f}), power "
                    f"{result['power_kW']:.1f} kW (change {100 * result['power_rel_change']:.1f}%)"
                )
            if result and result["steady"]:
                break
        if revs >= opts.max_revolutions:
            print(f"[spinup] WARNING: no steady state after {revs:.2f} revolutions")
            break
    return {"revolutions": revs, "steady_state": result}


def _stage_record(scenario, run_dir, manifest):
    """Write frames at steady state for ``record.duration_s``."""
    omega = _omega(scenario)
    engines.set_gravity_damping(NUMERICAL_DAMPING)
    engines._get_rotation_engine().angularVelocity = omega
    _start_monitor(scenario, run_dir, manifest, "record", omega=omega)

    opts = scenario.record
    capture.start_recording(run_dir / "frames", opts.frame_interval_s, run_dir / "frames_index.csv")
    O.run(round(opts.duration_s / O.dt), True)
    n_frames = capture.stop_recording()
    return {"frames": n_frames, "frame_interval_s": opts.frame_interval_s,
            "frames_dir": str(run_dir / "frames")}


def _start_monitor(scenario, run_dir, manifest, stage, omega):
    """(Re)start the mill-state log for ``stage``."""
    r_split = 0.5 * (scenario.small.radius_m + scenario.large.radius_m)
    monitor.start_monitor(
        run_dir / "mill_log.csv", scenario.record.monitor_interval_s,
        manifest["mill_body_ids"], r_split, omega, stage,
    )


def _omega(scenario):
    """Return the mill angular velocity (rad/s)."""
    return scenario.mill.speed_rpm * 2.0 * math.pi / 60.0


def _load_checkpoint(run_dir, stage, manifest):
    """Load ``stage``'s checkpoint and restore module state that ``O.load`` does not keep."""
    path = run_dir / "checkpoints" / f"{stage}.yade.gz"
    print(f"Resuming from checkpoint: {path}")
    O.load(str(path))
    materials.rebuild_materials_map()
    stl.SAG_MILL_SLICE_BODY_GROUP = list(manifest["mill_body_ids"])
    for label in ("monitor", "recorder", engines.BALANCE_STATE["label"]):
        O.engines = [e for e in O.engines if getattr(e, "label", None) != label]


def _new_manifest(scenario):
    """Return a fresh manifest for ``scenario``."""
    return {
        "scenario": scenario.to_dict(),
        "checks": scenario.checks(),
        "warnings": scenario.warnings(),
        "provisional_parameters": scenario.provisional_parameters(),
        "stages": {},
    }


def _read_manifest(run_dir):
    """Read ``run_dir/manifest.json``."""
    with (run_dir / "manifest.json").open(encoding="utf-8") as fh:
        return json.load(fh)


def _write_manifest(run_dir, manifest):
    """Write ``run_dir/manifest.json``."""
    with (run_dir / "manifest.json").open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, default=str)


def _parse_args(argv):
    """Parse this script's command line (everything after the script path)."""
    p = argparse.ArgumentParser(description="Staged YADE run of the SAG mill slice.")
    p.add_argument("--scenario", default=None, help="Scenario JSON (default: built-in defaults).")
    p.add_argument("--run-dir", default=None, help="Output directory.")
    p.add_argument("--from-stage", default="build", choices=STAGES)
    p.add_argument("--to-stage", default="record", choices=STAGES)
    p.add_argument("--gui", action="store_true", help="Open the YADE Qt viewer.")
    return p.parse_args(argv)


def _stage_function(name):
    """Return the function that runs stage ``name``."""
    return {
        "build": _stage_build,
        "fill": _stage_fill,
        "settle": _stage_settle,
        "spinup": _stage_spinup,
        "record": _stage_record,
    }[name]


# --- Script entry point ------------------------------------------------------

if __name__ == "__main__":
    _args = _parse_args(sys.argv[1:])
    run(_args.scenario, _args.run_dir, _args.from_stage, _args.to_stage, _args.gui)

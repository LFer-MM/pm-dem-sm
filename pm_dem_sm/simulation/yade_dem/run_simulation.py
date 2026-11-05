r"""Staged, headless DEM run of the SAG mill slice from a scenario JSON (YADE).

Runs the stages of :data:`pm_dem_sm.simulation.scenario.STAGES` in order:

1. ``build``  -- materials, mill liner (plates + lifters generated from the design
   parameters, see :mod:`~pm_dem_sm.simulation.mill_geometry`), engines, dt.
2. ``fill``   -- chord-box ingress of the bidisperse charge.
3. ``settle`` -- settling until the bed geometry is stationary (geometric stop
   rule of docs/scientific_rationale/13_initial_conditions.md) or the time cap.
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
``PyRunner`` command strings (``capture._record_frame()``,
``monitor._log_row()``) resolve in this script's global namespace.

Checks written to each stage's ``checks`` in the manifest
(docs/scientific_rationale/16_validation_checks.md): damping 0 at the start
of every stage (V5), no overlaps before each fill batch (V13, aborts), no
particle outside the mill after each stage (V14, aborts), overlap
statistics relative to the smaller diameter (V3), impact-speed P99 and the
steps per collision at that speed (V2), and the energy balance (V4).
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

from pm_dem_sm.simulation import checks, mill_geometry
from pm_dem_sm.simulation.scenario import STAGES, load_scenario
from pm_dem_sm.simulation.yade_dem import (
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


def run(scenario_path=None, run_dir=None, from_stage=None, to_stage=None, gui=False, seed=None):
    """Run stages ``from_stage`` .. ``to_stage`` of a scenario, checkpointing after each.

    The stages are those of the scenario's run type
    (:attr:`~pm_dem_sm.simulation.scenario.SimulationScenario.stages`):
    ``calibrate``, ``make_ic`` or ``dataset``.

    Args:
        scenario_path: Scenario JSON; ``None`` uses the
            :class:`~pm_dem_sm.simulation.scenario.SimulationScenario` defaults.
            When resuming, ``None`` reuses the scenario stored in the manifest.
        run_dir: Output directory; defaults to ``data/raw/yade_runs/<name>``.
        from_stage: First stage to run (default: the run type's first);
            a later stage loads the previous stage's checkpoint from
            ``run_dir``.
        to_stage: Last stage to run (default: the run type's last).
        gui: If ``True``, open the YADE Qt controller and 3D view.
        seed: Overrides the scenario's seed (replicates) and appends
            ``_s<seed>`` to its name, hence to the default run directory.

    Returns:
        dict: The final manifest.

    Raises:
        RuntimeError: If the running YADE is older than 2023.02.
        ValueError: If the scenario is invalid, a stage is not one of the run
            type's, or a resume has no ``run_dir``.
    """
    yade_version = str(getattr(yade.config, "version", "unknown"))
    check_yade_version(yade_version)
    print(f"[yade] version {yade_version}")

    resuming = from_stage is not None and run_dir is not None and (
        Path(run_dir) / "manifest.json"
    ).exists()
    resume_manifest = _read_manifest(Path(run_dir)) if resuming else None
    if scenario_path is None and resume_manifest is not None:
        from pm_dem_sm.simulation.scenario import SimulationScenario

        scenario = SimulationScenario.from_dict(resume_manifest["scenario"])
    else:
        scenario = load_scenario(scenario_path)
        if seed is not None:
            scenario.seed = int(seed)
            scenario.name = f"{scenario.name}_s{seed}"
    scenario.validate()

    stages = scenario.stages
    for s in (from_stage, to_stage):
        if s is not None and s not in stages:
            raise ValueError(f"Stage {s!r} is not a stage of run type "
                             f"{scenario.run.type!r}: {stages}")
    first = stages.index(from_stage) if from_stage else 0
    last = stages.index(to_stage) if to_stage else len(stages) - 1
    if first > last:
        raise ValueError(f"from_stage {from_stage!r} comes after to_stage {to_stage!r}")
    if first > 0 and resume_manifest is None:
        raise ValueError("--run-dir with a manifest is required when resuming from a later stage")

    run_dir = Path(run_dir or Path(_REPO_ROOT) / "data" / "raw" / "yade_runs" / scenario.name)
    (run_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
    manifest = resume_manifest or _new_manifest(scenario)
    manifest["scenario"] = scenario.to_dict()
    manifest["yade_version"] = yade_version
    for w in manifest["warnings"]:
        print(f"[scenario] WARNING: {w}")

    if first > 0:
        _load_checkpoint(run_dir, stages[first - 1], manifest)

    if gui:
        from yade import qt

        qt.Controller()
        qt.View()

    for name in stages[first:last + 1]:
        print(f"\n=== Stage: {name} ===")
        t_wall = time.time()
        t_sim, it0 = float(O.time), int(O.iter)
        if name not in ("build", "load_ic"):
            # V5: damping set explicitly and checked at the start of every stage
            # (build and load_ic create the engines and check it themselves).
            engines.set_gravity_damping(NUMERICAL_DAMPING)
            engines.assert_no_damping()
        outcome = _stage_function(name)(scenario, run_dir, manifest) or {}
        stage_checks = _stage_checks(scenario, name)
        O.save(str(run_dir / "checkpoints" / f"{name}.yade.gz"))
        manifest["stages"][name] = {
            "wall_s": time.time() - t_wall,
            "sim_time_start_s": t_sim,
            "sim_time_end_s": float(O.time),
            "iterations": int(O.iter) - it0,
            **outcome,
            "checks": stage_checks,
        }
        _write_manifest(run_dir, manifest)
        print(f"=== {name} done in {manifest['stages'][name]['wall_s']:.1f} s wall ===")
        if stage_checks["escaped"]:
            raise RuntimeError(
                f"V14 failed: {stage_checks['escaped']} particles outside the mill after {name}"
            )

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
    engines.assert_no_damping()

    manifest["mill_body_ids"] = list(mill_ids)
    manifest["liner_body_ids"] = list(mill_ids[: len(liner)])
    manifest["dt_s"] = O.dt
    manifest["threads"] = O.numThreads
    manifest["contact_tables"] = {k: tables[k] for k in ("restitution", "friction")}
    manifest["rolling_stiffness"] = krot
    return {"n_mill_bodies": len(mill_ids)}


def _stage_fill(scenario, run_dir, manifest):
    """Pour the bidisperse charge in chord-box batches, checking every batch for overlaps (V13)."""
    _start_monitor(scenario, run_dir, manifest, "fill", omega=0.0)
    small, large = scenario.small, scenario.large
    # Keep fill boxes inside the lifter tops, clear by one large radius.
    inner_d = 2.0 * (scenario.mill.lifter_top_radius_m - large.radius_m)
    ingress = particles.ingress_random if scenario.fill.method == "random" else (
        particles.ingress_segregated
    )
    liner = mill_geometry.liner_triangles(scenario.mill)
    v13 = {"batches": 0, "spheres": 0, "overlaps": 0}

    def check_batch(ids):
        r = diagnostics.check_new_batch(
            ids, liner, scenario.mill.depth_m, scenario.mill.lifter_top_radius_m
        )
        v13["batches"] += 1
        v13["spheres"] += r["spheres"]

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
        check_batch=check_batch,
    )
    inv = diagnostics.get_particle_inventory(small.radius_m, large.radius_m)
    return {"inventory": inv, "v13_initial_overlaps": v13}


def _stage_settle(scenario, run_dir, manifest):
    """Let the charge come to rest, undamped, by the geometric stop rule (V18)."""
    _start_monitor(scenario, run_dir, manifest, "settle", omega=0.0)
    opts = scenario.settle
    result = monitor.run_until_settled(
        d_small=2.0 * scenario.small.radius_m,
        max_time_s=opts.max_time_s,
        r_split=_r_split(scenario),
        sample_s=opts.sample_s,
        window_s=opts.window_s,
        angle_tol_deg=opts.angle_tol_deg,
        height_tol_rel_d=opts.height_tol_rel_d,
        speed_tol_m_s=opts.speed_tol_m_s,
    )
    return {"settle": result}


def _stage_spinup(scenario, run_dir, manifest):
    """Rotate from rest until the mill log reaches steady state."""
    omega = _omega(scenario)
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
    engines._get_rotation_engine().angularVelocity = omega
    _start_monitor(scenario, run_dir, manifest, "record", omega=omega)

    opts = scenario.record
    capture.start_recording(run_dir / "frames", opts.frame_interval_s, run_dir / "frames_index.csv")
    O.run(round(opts.duration_s / O.dt), True)
    n_frames = capture.stop_recording()
    return {"frames": n_frames, "frame_interval_s": opts.frame_interval_s,
            "frames_dir": str(run_dir / "frames")}


def _stage_save_ic(scenario, run_dir, manifest):
    """Zero all velocities and save the settled bed as an initial condition (``make_ic``).

    docs/scientific_rationale/13_initial_conditions.md, steps 4-5: all
    particles at rest; positions (CSV) and scene saved with the seed,
    counts, phi, J, material-set id and settle stop condition. Files go to
    ``<run-dir>/ic/``: ``positions.csv``, ``scene.yade.gz`` and ``ic.json``;
    the IC's name includes the material-set id.
    """
    ic_dir = run_dir / "ic"
    ic_dir.mkdir(parents=True, exist_ok=True)
    for b in O.bodies:
        if b and isinstance(b.shape, yade.Sphere):
            b.state.vel = yade.Vector3(0, 0, 0)
            b.state.angVel = yade.Vector3(0, 0, 0)
    state.save_particle_positions(str(ic_dir / "positions.csv"))
    O.save(str(ic_dir / "scene.yade.gz"))
    fill = checks.fill_level(
        diagnostics.spheres(), scenario.mill.diameter_m / 2.0, scenario.mill.depth_m,
        liner_profile=mill_geometry.liner_profile(scenario.mill),
    )
    ic_type = "SIC" if scenario.fill.method == "segregated" else "RMIC"
    msid = scenario.material_set_id()
    info = {
        "name": f"{scenario.name}_{ic_type}_seed{scenario.seed}_{msid}",
        "ic_type": ic_type,
        "seed": scenario.seed,
        "material_set_id": msid,
        "counts": {s.name: s.count for s in scenario.species},
        "J": fill["J"],
        "phi": fill["phi"],
        "settle": manifest["stages"].get("settle", {}).get("settle"),
        "sim_time_s": float(O.time),
    }
    (ic_dir / "ic.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    manifest["initial_condition"] = info
    print(f"[make_ic] saved {info['name']}: J = {fill['J']:.4f}, phi = {fill['phi']:.4f}")
    return {"initial_condition": info["name"], "J": fill["J"], "phi": fill["phi"]}


def _stage_load_ic(scenario, run_dir, manifest):
    """Build the scene and load a saved initial condition at rest (``dataset``).

    The IC (``<run.ic_dir>/ic/``) must carry this scenario's material-set id;
    the mill then starts from rest at t = 0 in the record stage
    (docs/scientific_rationale/14_dataset_runs_and_recording.md).

    Raises:
        ValueError: If the IC's material-set id differs from the scenario's.
    """
    # "{seed}" in ic_dir pairs dataset replicate N with make_ic replicate N.
    ic_root = Path(str(scenario.run.ic_dir).format(seed=scenario.seed))
    if not ic_root.is_absolute():
        ic_root = Path(_REPO_ROOT) / ic_root
    info = json.loads((ic_root / "ic" / "ic.json").read_text(encoding="utf-8"))
    msid = scenario.material_set_id()
    if info["material_set_id"] != msid:
        raise ValueError(
            f"IC {info['name']} was made with material set {info['material_set_id']}, "
            f"this scenario has {msid}: an IC is never reused with different materials"
        )
    outcome = _stage_build(scenario, run_dir, manifest)
    ids = state.load_particle_positions(str(ic_root / "ic" / "positions.csv"))
    manifest["initial_condition"] = info
    print(f"[dataset] loaded IC {info['name']}: {len(ids)} particles at rest")
    return {**outcome, "initial_condition": info["name"], "n_particles": len(ids)}


def _start_monitor(scenario, run_dir, manifest, stage, omega):
    """(Re)start the mill-state log for ``stage``."""
    monitor.start_monitor(
        run_dir / "mill_log.csv", scenario.record.monitor_interval_s,
        manifest["mill_body_ids"], _r_split(scenario), omega, stage,
        liner_ids=manifest.get("liner_body_ids"),
    )


def _r_split(scenario):
    """Return the radius separating small from large spheres (m)."""
    return 0.5 * (scenario.small.radius_m + scenario.large.radius_m)


def _stage_checks(scenario, stage):
    """Return the end-of-stage checks for the manifest.

    V14 escape count; for monitored stages also the contact statistics
    (overlaps relative to the smaller diameter, V3; impact-speed P99 and the
    steps per collision at that speed, V2) and the energy balance over the
    stage (V4, :func:`pm_dem_sm.simulation.checks.energy_balance`).
    """
    out = {
        "damping": engines.assert_no_damping(),
        "escaped": diagnostics.count_escapes(
            scenario.mill.shell_diameter_m / 2.0, scenario.mill.depth_m
        ),
    }
    if stage in ("build", "load_ic", "save_ic"):
        return out
    summary = monitor.stage_summary()
    v99 = summary["impact_v_p99_m_s"]
    if v99:
        dt = scenario.time_step_s()
        out["steps_per_collision_at_p99"] = min(
            scenario.contact_time_s(a, b, v99) / dt
            for i, a in enumerate(scenario.species) for b in scenario.species[i:]
        )
    rows = monitor.MONITOR_STATE["rows"]
    if len(rows) >= 2:
        out["energy_balance"] = checks.energy_balance(rows)
    out.update(summary)
    return out


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
    for label in ("monitor", "recorder"):
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
    p.add_argument("--from-stage", default=None, choices=STAGES)
    p.add_argument("--to-stage", default=None, choices=STAGES)
    p.add_argument("--seed", type=int, default=None, help="Override the scenario seed (replicates).")
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
        "save_ic": _stage_save_ic,
        "load_ic": _stage_load_ic,
    }[name]


# --- Script entry point ------------------------------------------------------

if __name__ == "__main__":
    _args = _parse_args(sys.argv[1:])
    run(_args.scenario, _args.run_dir, _args.from_stage, _args.to_stage, _args.gui, _args.seed)

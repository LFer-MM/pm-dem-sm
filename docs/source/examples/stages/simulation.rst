DEM simulation
==============

The DEM run happens under YADE's own Python interpreter, which cannot be
imported into this package's environment.
:func:`~pm_dem_sm.simulation.launcher.launch_simulation` therefore starts
it as a subprocess; this is what ``pm-dem-sm dem-sim`` and
``do_simulate`` call. ``dem-sim`` does not import pandas or TensorFlow, so it
works on a machine that only has YADE (``yade`` or the ``yadedaily`` build).

Scenarios
---------

A run is described by one JSON file, loaded into a
:class:`~pm_dem_sm.simulation.scenario.SimulationScenario`: mill geometry
and speed, the two particle species, materials (rock, steel and the steel
``liner`` of shell and lifters) and restitution, contact law with per-pair
friction (``contact.particle_friction`` mu_p, ``contact.wall_friction``
mu_w) and rolling resistance, time step, and the settings of each stage.
Keys left out keep their defaults (which come from :mod:`pm_dem_sm.config`
and the decisions in ``docs/scientific_rationale/``), except
``contact.rolling_resistance`` (mu_r), which every scenario must set: it
has no sourced value yet, and runs record it as provisional. Two scenarios
ship in ``configs/simulation/``, both with mu_r = 0.25:

``smoke_test.json``
   A 2 m mill with 360 particles; runs every stage in about a minute.
   Use it to check the pipeline, not the physics.
``sag_slice_lifters.json``
   The SAG_A slice (10.7128 m inside liners, 0.6 m deep, 9.5 rpm) with the
   provisional charge (14,650 rocks, 3,750 steel balls), 36 placeholder
   lifters and frictionless slice end walls.

Check a scenario before spending DEM time on it:

.. code-block:: python

   from pm_dem_sm.simulation.scenario import load_scenario

   s = load_scenario("configs/simulation/sag_slice_lifters.json")
   print(s.checks())    # critical speed, fill level J, steps per collision, lifter gap, ...
   print(s.warnings())  # e.g. < 20 steps per collision, speed outside 60-85% critical

Stages
------

``run_simulation.py`` runs five stages and writes a checkpoint after each;
numerical damping is 0 in all of them:

1. ``build`` -- materials, mill (STL or parametric shell with lifters), end
   walls, Hertz-Mindlin engines with per-pair restitution and friction and
   a rolling moment (``eta`` = mu_r, ``krot`` from the time step), and
   ``dt = solver.dt_s`` (2.5e-5 s by default).
2. ``fill`` -- the charge is poured in chord-box batches.
3. ``settle`` -- settling until the unbalanced force is small.
4. ``spinup`` -- rotation from rest until the charge
   centre-of-mass angle and the drive power stop changing between
   consecutive windows (steady state).
5. ``record`` -- frame CSVs every ``record.frame_interval_s`` for
   ``record.duration_s``, starting at steady state.

Running
-------

.. code-block:: bash

   pm-dem-sm dem-sim --scenario configs/simulation/sag_slice_lifters.json \
       --run-dir data/raw/yade_runs/sag_slice_lifters --threads 16

   # Resume from the settle checkpoint (e.g. after changing spin-up settings):
   pm-dem-sm dem-sim --run-dir data/raw/yade_runs/sag_slice_lifters --from-stage spinup

   # Watch it in the YADE viewer:
   pm-dem-sm dem-sim --scenario configs/simulation/smoke_test.json --gui

From Python:

.. code-block:: python

   from pm_dem_sm.simulation.launcher import launch_simulation

   result = launch_simulation(
       scenario="configs/simulation/smoke_test.json",
       run_dir="data/raw/yade_runs/smoke_test",
       threads=4,
   )
   print(result.returncode)  # nonzero exit codes are returned, not raised

``FileNotFoundError`` is raised when neither ``yade`` nor ``yadedaily`` is on
``PATH``; an invalid scenario raises ``ValueError`` before YADE starts.

Outputs
-------

Everything lands in the run directory:

``manifest.json``
   The full scenario, derived checks and warnings, YADE version, ``dt``,
   threads, and per stage: wall time, simulated time span, iterations and
   outcome (inventory, settle balance, revolutions to steady state, frames).
``mill_log.csv``
   One row per ``record.monitor_interval_s``: charge angle (all, small,
   large), kinetic energy, drive torque and power, largest overlap.
``frames/frame_00000.csv`` ...
   ``id, x, y, z, r, m, vx, vy, vz`` -- the input of
   :doc:`data_processing`. ``frames_index.csv`` gives each frame's exact time.
``checkpoints/<stage>.yade.gz``
   YADE scenes to resume from or open in the viewer.

As a pipeline stage
-------------------

.. code-block:: python

   from pm_dem_sm import run_experiment_pipeline

   results = run_experiment_pipeline(
       do_simulate=True,
       dem_scenario="configs/simulation/sag_slice_lifters.json",
       dem_run_dir="data/raw/yade_runs/sag_slice_lifters",
       do_predict=False, do_metrics=False, do_visualization=False,
   )
   print(results["dem_simulation"].returncode)

Point ``raw_data_dir`` at the run's ``frames/`` directory for ``do_process``.

Backends
--------

``backend="yade"`` is the only implemented backend. ``backend="blaze"``
(:mod:`pm_dem_sm.simulation.blaze_dem`) is a placeholder and raises
``NotImplementedError``.

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
and the decisions in ``docs/scientific_rationale/``); mu_r = 0.13 (heap
test, C06-3) is recorded as provisional in every run until it is
re-checked with the calibrated friction. Scenarios in ``configs/simulation/``:

``smoke_test.json``, ``smoke_make_ic.json``, ``smoke_dataset.json``
   A 2 m mill with 360 particles; each runs in about a minute. Use them to
   check the pipeline (calibrate, make_ic -> dataset), not the physics.
``sag_slice_lifters.json``
   The SAG_A slice (10.7128 m inside liners, 0.6 m deep, 9.5 rpm) with the
   grind-out charge (16,082 rocks, 3,437 steel balls; C12-3), SAG_A's new
   liner (36 lifters of 395 mm at 35 deg alternating with 130 mm plates)
   and frictionless slice end walls; a ``calibrate`` run.
``sag_a_make_ic_rmic.json``, ``sag_a_make_ic_sic.json``, ``sag_a_dataset_rmic.json``, ``sag_a_dataset_sic.json``
   The same slice as initial conditions (randomly mixed / segregated) and
   datasets recorded from them (20 s / 35 s).
``sensitivity/``
   The one-off sensitivity runs (V9, V10, V11, V11b-e), each one change
   from ``sens_baseline.json``.
``calibration/``
   The friction grid, mu_p x mu_w in {0.3, 0.5, 0.7}\ :sup:`2`: ``calibrate``
   runs that load the pilot's RMIC IC (``run.ic_dir``) and record 2
   revolutions; written by ``scripts/calibration/make_grid_scenarios.py``.
   ``smoke_calibrate_from_ic.json`` is its smoke-scale counterpart.

Check a scenario before spending DEM time on it:

.. code-block:: python

   from pm_dem_sm.simulation.scenario import load_scenario

   s = load_scenario("configs/simulation/sag_slice_lifters.json")
   print(s.checks())    # critical speed, fill level J, steps per collision, lifter gap, ...
   print(s.warnings())  # e.g. < 20 steps per collision, speed outside 60-85% critical

Run types and stages
--------------------

``run.type`` in the scenario selects the stages ``run_simulation.py`` runs
(a checkpoint after each; numerical damping is 0 in all of them):

``calibrate`` (default)
   ``build``, ``fill``, ``settle``, ``spinup``, ``record``: the charge is
   spun up to steady state and then recorded; used for the friction
   calibration and the sensitivity runs (``configs/simulation/sensitivity/``).
   With ``run.ic_dir`` set it loads that saved IC instead of pouring its own
   (``load_ic``, ``spinup``, ``record``); the IC must match in everything
   except friction, so one settled IC serves the whole friction grid
   (``configs/simulation/calibration/``).
``make_ic``
   ``build``, ``fill``, ``settle``, ``save_ic``: an initial condition is
   poured (``fill.method`` ``random`` for RMIC, ``segregated`` for SIC),
   settled, set at rest and saved in ``ic/`` under a name that includes the
   material-set id.
``dataset``
   ``load_ic``, ``record``: the IC of ``run.ic_dir`` is loaded (refused if its
   material-set id differs) and recorded from rest at t = 0 for
   ``record.duration_s`` (20 s RMIC, 35 s SIC).

The stages:

1. ``build`` -- materials, mill liner generated from the design parameters
   (:mod:`~pm_dem_sm.simulation.mill_geometry`; parameters and a mesh hash
   go into the manifest, ``mill_liner.stl`` into the run directory), end
   walls, Hertz-Mindlin engines with per-pair restitution and friction and
   a rolling moment (``eta`` = mu_r, ``krot`` from the time step), and
   ``dt = solver.dt_s`` (2.5e-5 s by default).
2. ``fill`` -- the charge is poured in chord-box batches, each checked for
   overlaps before its first step.
3. ``settle`` -- until the bed geometry is stationary (charge angle and
   height over 1 s, mean speed < 1 cm/s) or the time cap.
4. ``spinup`` -- rotation from rest until the charge centre-of-mass angle
   and the drive power stop changing between consecutive windows.
5. ``record`` -- frames every ``record.frame_interval_s`` for
   ``record.duration_s``.
6. ``save_ic`` / ``load_ic`` -- see ``make_ic`` / ``dataset`` above.

Running
-------

.. code-block:: bash

   pm-dem-sm dem-sim --scenario configs/simulation/sag_slice_lifters.json \
       --run-dir data/raw/yade_runs/sag_slice_lifters --threads 16

   # Resume from the settle checkpoint (e.g. after changing spin-up settings):
   pm-dem-sm dem-sim --run-dir data/raw/yade_runs/sag_slice_lifters --from-stage spinup

   # Watch it in the YADE viewer:
   pm-dem-sm dem-sim --scenario configs/simulation/smoke_test.json --gui

   # Initial conditions and datasets, replicate 0 (--seed N for replicate N):
   pm-dem-sm dem-sim --scenario configs/simulation/sag_a_make_ic_rmic.json --seed 0
   pm-dem-sm dem-sim --scenario configs/simulation/sag_a_dataset_rmic.json --seed 0

   # Post-process a run directory again (dem-sim does it after every successful run):
   pm-dem-sm dem-post data/raw/yade_runs/sag_a_dataset_rmic_s0

   # Watch it from another terminal, while it runs or afterwards:
   pm-dem-sm dem-view data/raw/yade_runs/sag_a_dataset_rmic_s0

   # The friction grid, two points at a time with 10 threads each, then the ranking:
   PARALLEL=2 THREADS=10 scripts/calibration/run_grid.sh
   python scripts/calibration/grid_summary.py

From Python:

.. code-block:: python

   from pm_dem_sm.simulation.launcher import launch_simulation

   result = launch_simulation(
       scenario="configs/simulation/smoke_test.json",
       run_dir="data/raw/yade_runs/smoke_test",
       threads=4,
   )
   print(result.returncode)  # nonzero exit codes are returned, not raised

``--gui`` needs a working desktop session for YADE's Qt window; when that
fails (or for long runs), use ``pm-dem-sm dem-view`` instead, which reads
the run's files and never touches the YADE process (see
:doc:`visualization`).

``FileNotFoundError`` is raised when neither ``yade`` nor ``yadedaily`` is on
``PATH``; an invalid scenario raises ``ValueError`` before YADE starts.

Outputs
-------

Everything lands in the run directory:

``manifest.json``
   The full scenario, derived checks and warnings, YADE version, ``dt``,
   threads, the mill geometry with its mesh hash, and per stage: wall time,
   simulated time span, iterations, outcome and ``checks`` (damping,
   escapes, overlaps, impact speeds, energy balance). After post-processing
   also ``postprocess`` and ``validation`` (the per-run checks with value,
   criterion and status; also in ``validation.json``).
``mill_log.csv``
   One row per ``record.monitor_interval_s``: charge angle and height, mean
   speed, kinetic energy, drive torque and power, overlaps relative to the
   smaller diameter, impact-speed P99, energy terms.
``liner_forces.csv``
   Contact force on the liner per 5-degree bin, one row per log row.
``frames/frame_00000.parquet`` ...
   ``id, x, y, z, r, m, vx, vy, vz`` as float32 (CSV while YADE runs;
   converted by the post-processing). ``frames_index.csv`` gives each
   frame's exact time.
``analysis/``
   ``radial_fraction.parquet`` and ``lacey.csv`` (dataset runs),
   ``charge_shape.json`` with the bulk toe / shoulder and the liner-force
   cross-check (calibrate runs).
``ic/`` (make_ic runs)
   ``positions.csv``, ``scene.yade.gz``, ``ic.json``.
``preview/snap_00000.csv`` ...
   Snapshots in every stage every ``record.preview_interval_s`` (0.5 s by
   default, 0 = off), for ``dem-view``; ``preview_index.csv`` gives each
   one's time, stage and mill angle. Not training data.
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

Visualization
=============

:mod:`pm_dem_sm.visualization` holds every plot and animation in the
project. Other stages only compute and save, so each plot here reads its
input from disk (or from a dict you pass) and works in a separate process
from the stage that produced it.

Every figure from one call
--------------------------

:func:`~pm_dem_sm.visualization.run_visualization.generate_visualizations`
is the ``do_visualization`` stage. It renders whatever has inputs on disk
and skips the rest:

.. code-block:: python

   from pm_dem_sm import ExperimentConfig, VisualizationOptions
   from pm_dem_sm.visualization.run_visualization import generate_visualizations

   cfg = ExperimentConfig(
       visualization=VisualizationOptions(plane="xy", fps=30, save_figures=True, show_plots=False),
   )
   artifacts = generate_visualizations(cfg)  # metrics loaded from disk
   # or, with metrics already in memory:
   # artifacts = generate_visualizations(cfg, metrics=m)

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Figure
     - Needs
     - Saved to (``save_figures=True``)
   * - Training curves
     - ``<model_path>.history.json``
     - ``data/interim/figures/training_curves.png``
   * - Lacey and SR cell grids
     - a frame in ``data_dir``
     - ``data/interim/figures/cell_grid_frame_{lacey,sr}.png``
   * - Five metrics comparisons
     - ``gt`` Lacey results
     - ``reports/figures/*_comparison.png``
   * - Prediction animation
     - frames in ``pred_frames_dir``
     - ``data/interim/figures/pred_animation.mp4`` (``.gif`` without ffmpeg)

With ``show_plots=False`` and ``save_figures=False``, the training curves
and grids are skipped.

Training curves
---------------

Takes the history file ``train_and_save`` wrote, a loaded dict, or a Keras
``History``:

.. code-block:: python

   from pm_dem_sm.visualization.training_curves import plot_training_history

   fig = plot_training_history(
       "models/rnn_gru_sic_model.history.json",
       save_path="reports/figures/training_curves.png",
       show=False,
   )
   # or: plot_training_history(history) right after train_and_save

.. figure:: ../_images/training_curves.png
   :alt: Training and validation MSE over 20 epochs.
   :width: 60%

   20 epochs on the 3.0-4.0 s window. The first epoch's loss dominates the scale; both curves are flat from epoch 2.

Metrics comparison plots
------------------------

Each takes the metrics dict from ``compute_metrics`` or ``load_metrics``
and draws DEM against surrogate (DEM only when no ``*_pred`` keys exist). A
plot whose input is missing prints a message and returns ``None``:

.. code-block:: python

   from pm_dem_sm import ExperimentConfig, VisualizationOptions
   from pm_dem_sm.metrics.run_metrics import load_metrics
   from pm_dem_sm.visualization import metrics_plots

   cfg = ExperimentConfig(visualization=VisualizationOptions(save_figures=True))
   m = load_metrics(cfg)

   metrics_plots.plot_lacey_comparison(m, cfg, show=False)       # Lacey index vs. time
   metrics_plots.plot_segregation_profile(m, cfg, show=False)    # radial + axial, last frame
   metrics_plots.plot_velocity_distribution(m, cfg, show=False)  # speed histograms per species
   metrics_plots.plot_granular_temperature(m, cfg, show=False)   # per-cell boxplots
   metrics_plots.plot_computing_speed(m, cfg, show=False)        # speedup bars

These save under ``reports/figures/`` when
``visualization.save_figures`` is set.

.. figure:: ../_images/metrics_overview.png
   :alt: Four comparison plots: Lacey index over time, segregation profiles, velocity distributions, granular temperature.
   :width: 100%

   Four of the five plots, as rendered; SiC dataset, trained on 3.0-4.0 s, autoregressive with SR from 4.05 s (the walkthrough settings). ``plot_computing_speed`` is left out: it needs a measured DEM wall-clock time.

Cell-grid overlay on one frame
------------------------------

A frame's XY scatter (rocks red, balls blue) with a square grid of
``cell_size``. Use it to check a cell size against the particle sizes:

.. code-block:: python

   from pm_dem_sm.visualization.cell_grid import plot_particles_with_grid

   frame = "data/processed/sic_dataset_20s_dt0p0001_parquet/frame_00000.parquet"
   plot_particles_with_grid(frame, cell_size=0.44, save_path="reports/figures/grid_lacey.png", show=False)
   plot_particles_with_grid(frame, cell_size=0.5588, save_path="reports/figures/grid_sr.png", show=False)

``0.44`` is the Lacey / granular-temperature cell
(``metrics.cell_size``); ``0.5588`` is the SR cell
(``stochastic.velocity_cell_size``).
:func:`~pm_dem_sm.visualization.run_visualization.plot_frame_grid` and
:func:`~pm_dem_sm.visualization.run_visualization.plot_sr_grid` read
those values from a config.

.. figure:: ../_images/cell_grids.png
   :alt: The first DEM frame in XY with a 0.44 m grid (left) and a 0.5588 m grid (right); balls on top, rocks below.
   :width: 100%

   Frame 0 of the SiC dataset with the Lacey grid (0.44 m, left) and the SR grid (0.5588 m, right).

Watching a DEM run
------------------

``pm-dem-sm dem-view <run-dir>``
(:mod:`~pm_dem_sm.visualization.run_viewer`) shows a run directory end-on:
the particles projected on the x-y plane, coloured by species (balls blue,
rocks orange) or by speed, inside the liner outline rotated to the mill
angle of that moment, with the stage, time, revolutions, charge angle,
power, kinetic energy and mean speed from ``mill_log.csv`` below the plot.
It reads only the files the run writes, so it can follow a run from another
terminal while YADE records, without slowing it or depending on YADE's Qt
window:

.. code-block:: bash

   # Live: opens on the newest frame and follows new ones (checks every 2 s).
   pm-dem-sm dem-view data/raw/yade_runs/sag_a_dataset_rmic_s0

   # Speed colours, starting on frame 100 (not following).
   pm-dem-sm dem-view data/raw/yade_runs/sag_a_dataset_rmic_s0 --color speed --frame 100

   # Files instead of a window: one frame as PNG, or every 4th frame as GIF.
   pm-dem-sm dem-view data/raw/yade_runs/sag_a_dataset_rmic_s0 --save frame.png
   pm-dem-sm dem-view data/raw/yade_runs/sag_a_dataset_rmic_s0 --save run.gif --every 4

Keys in the window: left / right one frame, down / up ten frames, home /
end first / last, space play / pause (``--fps``), ``f`` follow new frames,
``c`` species / speed colours, ``s`` save the current view as
``<run-dir>/view_frame_NNNNN.png``.

Inputs (read only): ``manifest.json`` (scenario, mill design, stage times),
``frames_index.csv`` with ``frames/frame_*.csv`` or ``.parquet`` (a frame is
shown once its index row exists, which YADE writes after the file), and
``mill_log.csv``. A ``make_ic`` run has no frames; it shows the saved
starting packing (``ic/positions.csv``) at the time it was saved. The mill
outline comes from the scenario's liner design
(:func:`~pm_dem_sm.simulation.mill_geometry.liner_profile`), turned
counter-clockwise at the scenario speed from the start of the first rotating
stage (``spinup`` or ``record``).

At full scale (19,519 particles) a frame takes about 0.6 s to draw, so a GIF
of a 20 s dataset (400 frames) takes about 4 minutes. MP4 output needs
``ffmpeg`` on ``PATH``. Stages without frames (fill, settle, spin-up) are not
shown yet; the stage checkpoints can be opened in YADE instead.

Animating frames
----------------

From a config (plane, fps, marker size, and stride come from
``visualization``); MP4 falls back to GIF when ffmpeg is missing:

.. code-block:: python

   from pm_dem_sm.visualization.run_visualization import animate_frames

   anim, path = animate_frames(
       cfg.prediction.pred_frames_dir, cfg, pattern="pred_frame_*.parquet",
       save_path="reports/figures/pred_animation.mp4",
   )

.. only:: html

   .. figure:: ../_images/pred_animation.gif
      :alt: Animation of the predicted particle positions in XY over the rollout.
      :width: 60%

      Predicted frames 4.05-19.85 s, every 4th frame; SiC dataset, trained on 3.0-4.0 s, autoregressive with SR from 4.05 s (the walkthrough settings).

.. only:: latex

   .. figure:: ../_images/pred_animation_last_frame.png
      :alt: Last predicted frame in XY.
      :width: 60%

      Last frame of the prediction animation (19.85 s); SiC dataset, trained on 3.0-4.0 s, autoregressive with SR from 4.05 s (the walkthrough settings).

Without a config, for any frame directory:

.. code-block:: python

   from pm_dem_sm.visualization.animate_particles import animate_particles

   animate_particles(
       "data/processed/sic_dataset_20s_dt0p0001_parquet",
       glob_pattern="frame_*.parquet",
       plane="xz",
       every_nth_frame=5,
       fps=30,
       save_path="reports/figures/gt_animation.mp4",
   )

``animate_particles`` has no GIF fallback: saving ``.mp4`` needs ffmpeg.

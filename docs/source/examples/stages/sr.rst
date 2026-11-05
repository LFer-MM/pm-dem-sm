Stochastic random (SR) model
============================

:mod:`pm_dem_sm.model.sr` implements the SR model, the second half of the
extended-RNNSR method (Kishida et al., 2025). The GRU predicts each
particle's local mean motion; the SR model supplies the local velocity
fluctuation around it. :class:`~pm_dem_sm.model.sr.model.SRModel` holds a
per-cell velocity standard deviation sigma_v(x), fitted once from reference
DEM frames (Step 3, Eq. 2), and samples ``v_tilde ~ N(0, sigma_v(x)^2)`` per
axis (Step 4, Eq. 3). The prediction loop combines the two as
``x = x_bar + v_tilde * dt_step`` (Eq. 4).

The subpackage mirrors the GRU's ``model`` / ``training`` / ``loading``,
with one name changed to fit a statistical model: ``fitting`` instead of
``training``, because sigma_v is a closed-form, one-pass estimate with no
loss, optimizer, or epochs. ``SRModel`` itself is a lookup table with a
Gaussian draw, not a network, and plays the same role as ``RNNModel``: hold
the fitted model, sample (``predict`` for the GRU), and save/load.

Enabling it in prediction
-------------------------

Training (``do_train``) fits the SR model on ``train_data_dir`` and saves
it next to the GRU, e.g. ``models/rnn_gru_sic_model.sr.npz``. With SR
enabled, ``predict_frames`` loads that file and adds a draw to every
predicted position:

.. code-block:: python

   from pm_dem_sm import ExperimentConfig
   from pm_dem_sm.config import StochasticOptions
   from pm_dem_sm.model.prediction import predict_frames

   cfg = ExperimentConfig(
       stochastic=StochasticOptions(enabled=True, stochastic_seed=0),
   ).with_overrides(autoregressive=True)
   preds = predict_frames(cfg)

From the CLI: ``pm-dem-sm ml-pipeline --enabled --autoregressive``. The
same ``stochastic_seed`` gives the same draws. If no ``.sr.npz`` sits next
to ``model_path``, prediction raises ``FileNotFoundError``; run training
first, or pass a fitted model as ``predict_frames(cfg, sr_model=...)``.

Fitting the SR model
--------------------

From position and velocity arrays of shape ``(T, N, 3)``:

.. code-block:: python

   from pm_dem_sm.data_processing import frames as data_io
   from pm_dem_sm.model.sr.fitting import fit_sr

   frames_dir = "data/processed/sic_training_dataset_3s_4s_parquet"
   pos, _, _ = data_io.load_frames_stacked(frames_dir)
   vel = data_io.load_velocities_stacked(frames_dir)
   sr_model = fit_sr(pos, vel, cell_size=0.5588, min_particles_per_cell=15)  # 4 x large diameter
   print(len(sr_model.sigma_by_cell), "cells with a sigma_v")

Or as training does, with the ``stochastic`` cell settings from the config,
saving the result next to ``model_path``:

.. code-block:: python

   from pm_dem_sm.model.sr.fitting import fit_and_save_sr

   sr_model = fit_and_save_sr(pos, vel, cfg)  # writes <model_path stem>.sr.npz

Each particle's DEM velocity (the ``vx``, ``vy``, ``vz`` columns) is binned
by its position in the same frame and pooled over all frames per cell, and
sigma_v is the standard deviation of each velocity component (paper Eq. 2),
so it is a 3-vector per cell. Large and small particles share one model.
Cells with fewer than ``min_particles_per_cell`` observations get
sigma_v = 0, i.e. no added noise.

.. note::

   ``velocity_cell_size`` (0.5588 m, ``4 x BALL_DIAM_M``) is deliberately
   not the Lacey cell size (0.3 m, ``MetricsOptions.cell_size``); see
   :class:`~pm_dem_sm.config.StochasticOptions`. Both grids can be drawn
   with :func:`~pm_dem_sm.visualization.cell_grid.plot_particles_with_grid`
   -- see :doc:`visualization`.

Sampling
--------

What ``predict_frames`` does at each step, for any ``(N, 3)`` positions:

.. code-block:: python

   import numpy as np
   from pm_dem_sm.data_processing import frames as data_io
   from pm_dem_sm.model.sr.loading import load_sr

   sr_model = load_sr("models/rnn_gru_sic_model.keras")  # reads models/rnn_gru_sic_model.sr.npz

   paths = data_io.sorted_frame_files("data/processed/sic_dataset_20s_dt0p0001_parquet")
   df = data_io.load_frame(paths[0], ["id", "x", "y", "z"])  # rows sorted by id
   pos = df[["x", "y", "z"]].to_numpy(np.float32)

   rng = np.random.default_rng(0)
   sigma = sr_model.sigma_at(pos)        # (N, 3) per-axis sigma_v at each particle's cell
   v_tilde = sr_model.sample(pos, rng)   # (N, 3) Eq. 3
   new_pos = pos + v_tilde * 0.05        # Eq. 4; in the pipeline pos is the GRU's x_bar

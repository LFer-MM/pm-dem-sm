Getting started
===============

Install
-------

From the repository root (Python 3.12):

.. code-block:: bash

   pip install -e ".[docs]"
   # or, for runtime work:
   pip install -r requirements.txt
   pip install -e .

This registers the ``pm-dem-sm`` console script, with four subcommands:
``dem-sim`` (launch a DEM simulation), ``dem-post`` (post-process a run
directory), ``dem-view`` (look at a run, live or afterwards) and
``ml-pipeline`` (run the experiment pipeline).

Run the pipeline (CLI)
----------------------

Preferred: pass a JSON file whose keys match :class:`~pm_dem_sm.config.ExperimentConfig`
(nested ``training`` / ``prediction`` / ``metrics`` / ``visualization`` objects).
When ``--config`` is set, other pipeline flags are ignored.

.. code-block:: bash

   pm-dem-sm ml-pipeline --config configs/pipeline_example.json

Override individual fields without JSON (Boolean flags use ``--flag`` /
``--no-flag``):

.. code-block:: bash

   pm-dem-sm ml-pipeline --do-train --no-do-predict --epochs 10

See ``pm-dem-sm ml-pipeline --help`` for the full flag list.

Example config
--------------

Minimal shape (paths and stage toggles). A fuller example lives at
``configs/pipeline_example.json`` in the repo:

.. code-block:: json

   {
     "data_dir": "data/processed/frames_parquet",
     "train_data_dir": "data/processed/train_parquet",
     "model_path": "models/rnn_gru_model.keras",
     "frames_in": 15,
     "do_train": false,
     "do_predict": true,
     "do_metrics": true,
     "do_visualization": true,
     "visualization": {
       "save_figures": true,
       "show_plots": false
     }
   }

Stages gated by ``do_simulate``, ``do_process``, ``do_train``, ``do_predict``,
``do_metrics``, and ``do_visualization`` run in that order inside
:func:`~pm_dem_sm.experiment_pipeline.run_experiment_pipeline`.
``do_simulate`` additionally needs YADE installed and on ``PATH``
(``dem_backend="yade"``, the default) -- BlazeDEM (``dem_backend="blaze"``)
is not implemented yet.

Use from Python
---------------

.. code-block:: python

   from pm_dem_sm import ExperimentConfig, TrainingOptions, run_experiment_pipeline

   cfg = ExperimentConfig.from_json("configs/pipeline_example.json")
   results = run_experiment_pipeline(cfg)
   # or: run_experiment_pipeline(do_train=True, do_predict=False, epochs=10)
   # or: ExperimentConfig(do_train=True, training=TrainingOptions(epochs=10))

More snippets
-------------

CLI recipes, the Python pipeline, stage-by-stage snippets (data prep,
training, prediction, SR, metrics, visualization, DEM simulation), and
end-to-end walkthroughs are in :doc:`examples/index`.

Build these docs locally
------------------------

.. code-block:: bash

   python -m sphinx -b html docs/source docs/build/html

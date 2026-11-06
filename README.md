# pm-dem-sm

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![pytest](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-data-150458?logo=pandas&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-RNN-FF6F00?logo=tensorflow&logoColor=white)
![YADE](https://img.shields.io/badge/YADE-DEM-2C5282)

Repository dedicated to the development of the project titled **DEM Surrogate Modeling for Time Series Prediction in Bidisperse Particle Mixing and Segregation** as terminal project, conformant of the UNISON MCD academic program.

## Contents

`pm_dem_sm/` is organized by pipeline stage. Two runtimes coexist in one
package: `simulation/` runs only inside YADE's embedded Python interpreter
and only ever produces CSV frames on disk; everything else runs in a normal
TensorFlow/pandas venv and only ever *consumes* those frames as files. The
two sides never call each other in-process.

- **`simulation/`** — YADE-only DEM simulation: mill/material/engine setup, chord-box ingress (random or segregated), balance/rotation utilities (`sim_functions.py`, `simulation.py`), and a subprocess launcher (`launcher.py`) that the CLI's `dem-sim` subcommand uses without ever importing `yade` itself.
- **`data_processing/`** — Raw DEM CSV frame dumps to Parquet (`csv_to_parquet.py`), particle-size integrity checks (`integrity.py`), and frame loading / supervised-dataset construction for training (`frames.py`).
- **`model/`** — The extended-RNNSR surrogate: the GRU (`rnn/`: model, training, loading), the stochastic-random (SR) model (`sr/`: model, fitting, loading), and the two steps that combine them, `training.py` (train the GRU, fit the SR) and `prediction.py` (sliding-window prediction plus SR noise).
- **`metrics/`** — Post-hoc computation over ground-truth/predicted frames: Lacey's mixing index, radial/axial segregation profile, velocity distribution and granular temperature, and dimensionless computing speed (`run_metrics.py`). Computation only — no plotting.
- **`visualization/`** — All plotting and animation: frame snapshots with a cell-grid overlay (`cell_grid.py`), 2D particle animation (`animate_particles.py`, `run_visualization.py`), training loss curves (`training_curves.py`), and the ground-truth-vs-surrogate comparison plots for every `metrics` computation (`metrics_plots.py`).
- **`config.py` / `pipeline.py` / `cli.py` / `progress.py` / `tf_quiet.py`** — Top-level configuration, end-to-end orchestration, the `pm-dem-sm` CLI (`dem-sim`, `dem-post`, `dem-view`, `ml-pipeline` subcommands), progress banners, and TensorFlow startup-noise suppression.
- **`tests/`** — Mirrors the package layout above. YADE-backed tests are skipped when YADE is not installed.

## Development

- Install dev dependencies: `pip install -r requirements-dev.txt`
- Run tests from the repo root: `python -m pytest tests -q`

## Relevant links

## Citation and license

If you use this software, please cite it using the metadata in
[`CITATION.cff`](CITATION.cff) (GitHub's "Cite this repository" button
renders it as APA/BibTeX). Released under the [MIT License](LICENSE).

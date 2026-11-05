"""Configuration for the whole pm-dem-sm project.

Two tiers, both in this one file:

- Plain module constants for DEM simulation setup -- paths, particle
  diameters, material properties, mill geometry. They hold backend-agnostic
  data only; each backend turns them into its own objects (e.g.
  :mod:`pm_dem_sm.simulation.yade_dem.materials`). These are hardcoded
  values with no CLI flag or JSON key -- edit them here directly. Particle
  counts are not constants: they are scenario inputs
  (:class:`~pm_dem_sm.simulation.scenario.Species`).
- :class:`ExperimentConfig`, a dataclass tree (with nested per-stage option
  groups) that drives the RNN surrogate pipeline and DEM-backend selection.
  Drivable from Python, JSON (``configs/pipeline_example.json``), or
  :mod:`pm_dem_sm.cli` flags.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass, replace
import json
from pathlib import Path
from typing import Any, get_type_hints

# --- Constants: paths and dataset defaults -----------------------------------

#: Repository root (the directory containing ``pm_dem_sm/``).
REPO_ROOT = Path(__file__).resolve().parents[1]
#: Root of all on-disk datasets.
DATA_DIR = REPO_ROOT / "data"
#: Raw DEM CSV frame dumps, as written by the simulation.
RAW_DIR = DATA_DIR / "raw"
#: Intermediate outputs (predictions, scratch figures).
INTERIM_DIR = DATA_DIR / "interim"
#: Training-ready parquet datasets.
PROCESSED_DIR = DATA_DIR / "processed"
#: Saved surrogate models and their training histories.
MODELS_DIR = REPO_ROOT / "models"
#: Persisted metric results (e.g. ``computing_speed.json``).
REPORTS_DIR = REPO_ROOT / "reports"
#: Saved comparison figures.
FIGURES_DIR = REPORTS_DIR / "figures"

#: Default ground-truth dataset directory name under :data:`PROCESSED_DIR`.
DEFAULT_DATASET = "sic_dataset_20s_dt0p0001_parquet"
#: Default short-time training dataset directory name under :data:`PROCESSED_DIR`.
DEFAULT_TRAIN_DATASET = "sic_training_dataset_3s_4s_parquet"
#: Default model file stem under :data:`MODELS_DIR`.
DEFAULT_MODEL_NAME = "rnn_gru_sic_model"

#: Particle id column shared by every frame table.
ID_COL = "id"
#: Per-timestep GRU input features (position plus radius).
FEATURE_COLS = ["x", "y", "z", "r"]
#: GRU regression targets (next-step position).
TARGET_COLS = ["x", "y", "z"]
#: Instantaneous DEM particle velocity, the ``v_i`` of Kishida et al. (2025)
#: Eqs. 1-2. Every frame file is expected to carry these columns.
VELOCITY_COLS = ["vx", "vy", "vz"]


# --- Constants: DEM simulation, shared / backend-agnostic --------------------

#: Valid values for ``ExperimentConfig.dem_backend``.
DEM_BACKENDS = ("yade", "blaze")

#: SAG_A liner design, new liners (docs/scientific_rationale/10_mill_geometry.md):
#: inside-shell diameter (36 ft, m) ...
SHELL_DIAMETER_M = 10.9728
#: ... flat liner plates (m) ...
LINER_PLATE_THICKNESS_M = 0.130
#: ... lifter rows, alternating with the plates ...
N_LIFTERS = 36
#: ... lifter width at the shell (m) ...
LIFTER_BASE_WIDTH_M = 0.523
#: ... lifter height measured from the inside shell (m; 265 mm above the plates) ...
LIFTER_HEIGHT_M = 0.395
#: ... and face angle of both lifter faces from the radial direction (deg).
LIFTER_FACE_ANGLE_DEG = 35.0
#: Mill diameter inside liners (m), 10.7128 for SAG_A: Morrell's D, used for the
#: fill level, critical speed and the derived checks
#: (``MillGeometry.diameter_m``).
MILL_DIAMETER_M = SHELL_DIAMETER_M - 2.0 * LINER_PLATE_THICKNESS_M

#: Rock particle diameter (m); 2.75 inches
#: (docs/scientific_rationale/12_charge_fill_and_particles.md).
ROCK_DIAM_M = 0.06985
#: Steel-ball diameter (m); 5.5 inches. The large/tracer species
#: (``material_large="steel"``).
BALL_DIAM_M = 0.1397

#: Particle-particle friction coefficient mu_p, one value for steel-steel,
#: steel-rock and rock-rock: the calibration baseline
#: (docs/scientific_rationale/05_friction.md).
PARTICLE_FRICTION = 0.5
#: Particle-liner friction coefficient mu_w (shell and lifters): the
#: calibration baseline (docs/scientific_rationale/05_friction.md).
WALL_FRICTION = 0.5
#: Owen & Cleary (2015, Table 4) particle-pair friction, run once as a
#: sensitivity case (``ContactOptions.particle_friction_set = "owen"``;
#: docs/scientific_rationale/05_friction.md).
OWEN_PARTICLE_FRICTION = {
    ("steel", "steel"): 0.4,
    ("steel", "rock"): 0.5,
    ("rock", "rock"): 0.8,
}

#: Per-material DEM properties (density in kg/m^3, **physical** Young's
#: modulus in Pa -- scaled by ``SolverOptions.young_scale`` when the scene is
#: built --, Poisson ratio) plus the label the DEM backend registers each
#: material under. Friction is set per pair from ``ContactOptions``, not per
#: material. ``"liner"`` (shell and lifters) is steel with its own friction
#: mu_w. Sources in docs/scientific_rationale/: moduli 03, density 08,
#: Poisson ratio 09, liner material 05.
MATERIALS = {
    "steel": {
        "density": 7850,
        "young": 207e9,
        "poisson": 0.292,
        "label": "steel",
    },
    "rock": {
        "density": 2850,
        "young": 55e9,
        "poisson": 0.25,
        "label": "rock",
    },
    "liner": {
        "density": 7850,
        "young": 207e9,
        "poisson": 0.292,
        "label": "liner",
    },
}

#: Pairwise coefficients of restitution keyed by material-name pair
#: (docs/scientific_rationale/07_restitution.md; liner pairs take the steel
#: values); a scenario looks them up order-independently via
#: ``SimulationScenario.restitution_for``.
RESTITUTION_COEFFICIENTS = {
    ("steel", "steel"): 0.8,
    ("steel", "rock"): 0.5,
    ("rock", "rock"): 0.3,
    ("liner", "steel"): 0.8,
    ("liner", "rock"): 0.5,
}


# --- Public classes: experiment configuration --------------------------------


@dataclass
class TrainingOptions:
    """GRU training hyperparameters.

    Attributes:
        epochs: Number of training epochs.
        batch_size: Samples per gradient step.
        learning_rate: Adam optimizer learning rate.
        val_fraction: Fraction of samples held out for validation.
        seed: RNG seed for the train/validation shuffle.
        gru_units: Hidden size of the GRU layer.
        dense_units: Units in the intermediate Dense layer.
        local_mean_conversion: If ``True``, train on the local mean component
            of each trajectory, ``x_i - v_i * Delta t_RNN`` (Kishida et al.
            2025, Eq. 1, with ``prediction.dt_step`` as Delta t_RNN), rather
            than on raw positions.
    """

    epochs: int = 20
    batch_size: int = 500
    learning_rate: float = 0.01
    val_fraction: float = 0.1
    seed: int = 0
    gru_units: int = 20
    dense_units: int = 15
    local_mean_conversion: bool = True


@dataclass
class PredictionOptions:
    """Sliding-window prediction settings and output paths.

    Attributes:
        start_frame: Index of the first seed frame in ``data_dir``.
        autoregressive: If ``True``, feed each prediction back as the next
            input; otherwise slide over ground-truth frames.
        predict_until_end: If ``True``, predict through the last available
            frame; otherwise stop after ``max_steps``.
        max_steps: Number of steps to predict when ``predict_until_end`` is
            ``False``.
        predict_batch_size: Particles per model forward pass.
        dt0: Time stamp (s) written for the first predicted frame.
        dt_step: Time (s) between predicted frames; also the SR term's
            Delta t_RNN.
        pred_out_dir: Root directory for prediction outputs.
    """

    start_frame: int = 66
    autoregressive: bool = False
    predict_until_end: bool = True
    max_steps: int = 200
    predict_batch_size: int = 2048
    dt0: float = 4.05
    dt_step: float = 0.05
    pred_out_dir: Path = INTERIM_DIR / "rnn_predictions"

    @property
    def pred_frames_dir(self) -> Path:
        """Directory holding one parquet per predicted frame (``pred_out_dir / "pred_frames"``)."""
        return Path(self.pred_out_dir) / "pred_frames"

    @property
    def pred_combined_parquet(self) -> Path:
        """Combined predictions table (``pred_out_dir / "predictions_all.parquet"``)."""
        return Path(self.pred_out_dir) / "predictions_all.parquet"


@dataclass
class MetricsOptions:
    """Cell grid, time-axis, and spatial-profile settings for the metrics stage.

    ``cell_size`` and ``min_particles_per_cell`` are shared by Lacey's mixing
    index and granular temperature (the paper uses the same grid for both:
    ``0.04 x drum_diameter``, Kishida et al. 2025 Sec 4.1; 0.3 m here, see
    docs/scientific_rationale/14_dataset_runs_and_recording.md -- distinct from
    ``StochasticOptions.velocity_cell_size``, which follows a different
    formula for a different purpose; see that class's docstring).
    ``center_x``/``center_y``/``center_z`` and the bin counts configure the
    radial/axial large-particle fraction profile; the mill's circular cross
    section is assumed to lie in the XY plane (see
    :mod:`pm_dem_sm.metrics.segregation_profile`).

    Attributes:
        cell_size: Cubic cell edge length (m) for Lacey and granular temperature.
        min_particles_per_cell: Minimum particles for a cell to contribute.
        metrics_dt: Time (s) per frame index; ``time = frame * metrics_dt``.
        center_x: Mill central-axis X coordinate (m).
        center_y: Mill central-axis Y coordinate (m).
        center_z: Axial reference point (m) for the axial profile.
        n_radial_bins: Number of equal-width radial bins.
        n_axial_bins: Number of equal-width axial bins.
    """

    # Two cells across the 0.6 m slice
    # (docs/scientific_rationale/14_dataset_runs_and_recording.md).
    cell_size: float = 0.3
    min_particles_per_cell: int = 15
    metrics_dt: float = 0.05
    center_x: float = 0.0
    center_y: float = 0.0
    center_z: float = 0.0
    n_radial_bins: int = 12
    n_axial_bins: int = 12


@dataclass
class ComputingSpeedOptions:
    """Reference DEM wall-clock times for the dimensionless computing-speed metric.

    :func:`~pm_dem_sm.experiment_pipeline.run_experiment_pipeline` times its own
    training/prediction stages, but the DEM side of the comparison (Kishida
    et al. 2025, Powder Technology 455, 120811, Fig. 15) has no equivalent
    unless ``do_simulate`` is timed too: DEM simulations may run separately
    under YADE, outside this pipeline. There is no way to derive their
    wall-clock time automatically in that case, so both fields here are
    plain user-supplied measurements, in seconds for consistency with every
    other time-valued field in this config (e.g. ``metrics_dt``, ``dt_step``).

    Attributes:
        dem_reference_seconds: Wall-clock time of a full DEM run reproducing
            the same target simulated duration as your training/prediction
            run, on the same hardware. The default (24 h) is a placeholder,
            not a measurement.
        dem_data_acquisition_seconds: Wall-clock time of the short reference
            DEM run used to generate this GRU's training data (paper Steps
            1-2). Defaults to 0.0 (excluded), matching the paper's "all
            RNNSR steps" figure once set; leave at 0.0 to report only the
            Python-side train+predict time.
    """

    dem_reference_seconds: float = 86400.0
    dem_data_acquisition_seconds: float = 0.0


@dataclass
class StochasticOptions:
    """Stochastic random (SR) velocity perturbation settings.

    Applied after the GRU's deterministic prediction, per the extended-RNNSR
    method of Kishida et al. (2025), Powder Technology 455, 120811: the SR
    model's local (Eulerian) velocity standard deviation sigma_v(x) is
    fitted on ``train_data_dir`` on a cubic grid during training and saved
    next to the GRU; at prediction it is sampled per axis and added to each
    predicted position, scaled by ``prediction.dt_step`` (Delta t_RNN).
    ``enabled`` only controls prediction; training always fits the model.

    ``velocity_cell_size`` follows the paper's SR-specific formula --
    ``4 x large-particle diameter`` (Sec 2.2.3, Sec 3) -- which is *not* the
    same cell as ``MetricsOptions.cell_size`` (Lacey/granular temperature,
    0.3 m here); the two default to different numbers on
    purpose (0.5588 m vs. 0.3 m) because they answer different
    questions over different reference lengths, even though the paper's own
    reference DEM happens to use a small cell for both.

    Attributes:
        enabled: If ``True``, add the SR displacement to every prediction.
        velocity_cell_size: Cubic cell edge length (m) for the sigma_v(x) grid.
        velocity_min_particles_per_cell: Minimum pooled observations for a
            cell to receive a non-zero sigma_v.
        stochastic_seed: RNG seed for the SR draws.
    """

    enabled: bool = False
    velocity_cell_size: float = 4 * BALL_DIAM_M  # 0.5588 m
    velocity_min_particles_per_cell: int = 15
    stochastic_seed: int = 0


@dataclass
class VisualizationOptions:
    """Animation and figure display / save settings.

    Attributes:
        plane: Projection plane for animations: ``"xy"``, ``"xz"``, or ``"yz"``.
        fps: Animation frames per second.
        marker_size: Scatter marker size.
        every_nth_frame: Subsample stride over frame files when animating.
        save_figures: If ``True``, write figures and animations to disk.
        show_plots: If ``True``, display figures interactively.
    """

    plane: str = "xy"
    fps: int = 30
    marker_size: float = 4.0
    every_nth_frame: int = 1
    save_figures: bool = False
    show_plots: bool = True


@dataclass
class ExperimentConfig:
    """Knobs for one reproducible run of the study: DEM simulation through surrogate validation.

    Core fields are data paths, model identity, DEM-backend selection, and
    stage toggles. Simulation, training, prediction, metrics, and
    visualization knobs live on nested option dataclasses (defaults apply
    when a group is omitted). Used by
    :func:`pm_dem_sm.experiment_pipeline.run_experiment_pipeline`.

    Attributes:
        data_dir: Ground-truth parquet frames (prediction seed and metrics).
        train_data_dir: Short-time parquet frames used for training and for
            the SR velocity field.
        raw_data_dir: Raw DEM CSV dumps converted by ``do_process``.
        frame_glob: Glob pattern for ground-truth frame files.
        feature_cols: Per-timestep model input columns.
        model_path: Saved model path (``.keras``, ``.h5``, or SavedModel dir).
        frames_in: Input window length (frames per GRU sequence).
        dem_backend: DEM backend launched by ``do_simulate``; one of
            :data:`DEM_BACKENDS`.
        dem_scenario: Scenario JSON for ``do_simulate`` (see
            :class:`~pm_dem_sm.simulation.scenario.SimulationScenario`);
            ``None`` uses the scenario defaults.
        dem_run_dir: Output directory for ``do_simulate``; ``None`` uses
            ``data/raw/yade_runs/<scenario name>``. Frames land in its
            ``frames/`` subdirectory -- point ``raw_data_dir`` there for
            ``do_process``.
        do_simulate: Run the DEM simulation stage.
        do_process: Run the raw-CSV-to-parquet stage.
        do_train: Run the training stage.
        do_predict: Run the prediction stage.
        do_metrics: Run the metrics stage.
        do_visualization: Run the visualization stage.
        training: Training hyperparameters.
        prediction: Prediction settings and output paths.
        metrics: Metrics-stage settings.
        stochastic: SR (stochastic-random) perturbation settings.
        computing_speed: DEM reference times for the computing-speed metric.
        visualization: Figure and animation settings.
    """

    # Data
    data_dir: Path = PROCESSED_DIR / DEFAULT_DATASET
    train_data_dir: Path = PROCESSED_DIR / DEFAULT_TRAIN_DATASET
    raw_data_dir: Path = RAW_DIR
    frame_glob: str = "frame_*.parquet"
    feature_cols: list[str] = field(default_factory=lambda: list(FEATURE_COLS))

    # Model
    model_path: Path = MODELS_DIR / f"{DEFAULT_MODEL_NAME}.keras"
    frames_in: int = 15

    # DEM backend selection and run (do_simulate only)
    dem_backend: str = "yade"
    dem_scenario: Path | None = None
    dem_run_dir: Path | None = None

    # Stage toggles, in end-to-end run order
    do_simulate: bool = False
    do_process: bool = False
    do_train: bool = False
    do_predict: bool = True
    do_metrics: bool = True
    do_visualization: bool = True

    training: TrainingOptions = field(default_factory=TrainingOptions)
    prediction: PredictionOptions = field(default_factory=PredictionOptions)
    metrics: MetricsOptions = field(default_factory=MetricsOptions)
    stochastic: StochasticOptions = field(default_factory=StochasticOptions)
    computing_speed: ComputingSpeedOptions = field(default_factory=ComputingSpeedOptions)
    visualization: VisualizationOptions = field(default_factory=VisualizationOptions)

    def to_dict(self) -> dict[str, Any]:
        """Serialize config fields; ``Path`` values become strings.

        Nested option groups are nested objects. Omitted groups in
        :meth:`from_dict` keep dataclass defaults.

        Returns:
            dict[str, Any]: Field name to JSON-serializable value.
        """
        return _to_plain_dict(self)

    def with_overrides(self, **overrides: Any) -> ExperimentConfig:
        """Return a copy with top-level or nested leaf fields replaced.

        Nested group objects may be passed by name (``training=TrainingOptions(...)``)
        or individual leaf names may be passed flat (``epochs=5``), matching CLI
        flags. Leaf overrides apply after whole-group replacements.

        Args:
            **overrides: ``ExperimentConfig`` field names, option-group names, or
                leaf names from a nested options dataclass.

        Returns:
            ExperimentConfig: New instance with overrides applied.

        Raises:
            ValueError: If an override name is not a known field.
            TypeError: If a group override is not the matching options class.
        """
        group_types = _option_group_types()
        leaf_to_group = _leaf_to_group()
        top_names = {f.name for f in fields(self)} - set(group_types)

        top: dict[str, Any] = {}
        nested_updates: dict[str, dict[str, Any]] = {}
        for key, value in overrides.items():
            if key in group_types:
                expected = group_types[key]
                if not isinstance(value, expected):
                    raise TypeError(
                        f"{key} override must be {expected.__name__}, "
                        f"got {type(value).__name__}"
                    )
                top[key] = value
            elif key in top_names:
                top[key] = value
            elif key in leaf_to_group:
                nested_updates.setdefault(leaf_to_group[key], {})[key] = value
            else:
                raise ValueError(f"Unknown ExperimentConfig override: {key!r}")

        updated = replace(self, **top) if top else self
        for group, leafs in nested_updates.items():
            current = getattr(updated, group)
            updated = replace(updated, **{group: replace(current, **leafs)})
        return updated

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperimentConfig:
        """Build a config from a mapping such as parsed JSON; unknown keys raise.

        Nested groups are objects keyed ``training``, ``prediction``,
        ``metrics``, and ``visualization``. Paths may be strings; bools may be
        common string forms.

        Args:
            data: Mapping of ``ExperimentConfig`` field names to values.

        Returns:
            ExperimentConfig: Coerced configuration instance.

        Raises:
            ValueError: If ``data`` contains keys not defined on this class or
                a nested options class.
            TypeError: If a bool field cannot be coerced, or a nested group
                is not a mapping.
        """
        return _from_plain_dict(cls, data)

    @classmethod
    def from_json(cls, path: Path | str) -> ExperimentConfig:
        """Load config from a JSON file.

        Args:
            path: Path to a JSON object whose keys are ``ExperimentConfig``
                fields (nested option groups as objects).

        Returns:
            ExperimentConfig: Configuration built via :meth:`from_dict`.

        Raises:
            ValueError: If the JSON root is not an object.
            OSError: If the file cannot be read.
        """
        path = Path(path)
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError(f"Config JSON must be an object, got {type(data).__name__}")
        return cls.from_dict(data)


# --- Private helper functions ------------------------------------------------


def _option_group_types() -> dict[str, type]:
    """Map ``ExperimentConfig`` field name to nested options dataclass."""
    return {
        "training": TrainingOptions,
        "prediction": PredictionOptions,
        "metrics": MetricsOptions,
        "stochastic": StochasticOptions,
        "computing_speed": ComputingSpeedOptions,
        "visualization": VisualizationOptions,
    }


def _leaf_to_group() -> dict[str, str]:
    """Map nested options field name to its group name on ``ExperimentConfig``."""
    mapping: dict[str, str] = {}
    for group, cls in _option_group_types().items():
        for f in fields(cls):
            mapping[f.name] = group
    return mapping


def _to_plain_dict(obj: Any) -> dict[str, Any]:
    """Recursively serialize a config dataclass; ``Path`` values become strings."""
    cls = type(obj)
    hints = get_type_hints(cls)
    raw: dict[str, Any] = {}
    for f in fields(cls):
        val = getattr(obj, f.name)
        hint = hints[f.name]
        if isinstance(hint, type) and is_dataclass(hint):
            raw[f.name] = _to_plain_dict(val)
        elif hint is Path and val is not None:
            raw[f.name] = str(val)
        else:
            raw[f.name] = val
    return raw


def _from_plain_dict(cls: type, data: dict[str, Any]) -> Any:
    """Coerce a mapping into ``cls``, recursing into nested dataclasses."""
    known = {f.name for f in fields(cls)}
    unknown = set(data) - known
    if unknown:
        raise ValueError(f"Unknown {cls.__name__} keys: {sorted(unknown)}")

    hints = get_type_hints(cls)
    coerced: dict[str, Any] = {}
    for key, value in data.items():
        hint = hints[key]
        if isinstance(hint, type) and is_dataclass(hint):
            if not isinstance(value, dict):
                raise TypeError(
                    f"{key} must be an object, got {type(value).__name__}"
                )
            coerced[key] = _from_plain_dict(hint, value)
        elif hint is Path and value is not None:
            coerced[key] = Path(value)
        elif hint is bool and not isinstance(value, bool):
            coerced[key] = _coerce_bool(value, key)
        else:
            coerced[key] = value
    return cls(**coerced)


def _coerce_bool(value: Any, key: str) -> bool:
    """Coerce a common string/truthy form into a bool for config loading.

    Args:
        value: Value to coerce (typically a string such as ``"true"`` / ``"0"``).
        key: Field name used only in the error message.

    Returns:
        bool: Parsed boolean.

    Raises:
        TypeError: If ``value`` is not a recognized boolean string form.
    """
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    raise TypeError(f"Cannot coerce {key!r}={value!r} to bool")

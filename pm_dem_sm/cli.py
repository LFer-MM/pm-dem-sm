"""Command-line interface for the bidisperse DEM surrogate-model toolkit.

Subcommands:

- ``dem-sim``: launches a DEM simulation as a subprocess (``--dem-backend
  yade``, the default, requires YADE installed and on PATH; ``blaze`` is not
  implemented yet). Never imports a DEM engine's own Python API itself --
  see :mod:`pm_dem_sm.simulation.launcher`. When the run succeeds, its run
  directory is post-processed (unless ``--no-postprocess``).
- ``dem-post``: post-processes a finished run directory (frames to float32
  parquet, segregation profiles, toe / shoulder, validation summary; see
  :mod:`pm_dem_sm.simulation.postprocess`).
- ``dem-view``: 2D end-on view of a run directory, live while the run
  writes frames or afterwards; or saves a PNG / GIF (see
  :mod:`pm_dem_sm.visualization.run_viewer`).
- ``ml-pipeline``: runs the experiment pipeline (simulate / process / train /
  predict / metrics / visualization). Config can be supplied either as
  individual flags or as a JSON file via ``--config``. When ``--config`` is
  set, all other pipeline config flags are ignored. Flags stay flat
  (``--epochs``); they are mapped onto nested option groups on
  :class:`~pm_dem_sm.config.ExperimentConfig`.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import fields
from pathlib import Path
import sys
from typing import Any, get_type_hints

from .config import DEM_BACKENDS, ExperimentConfig, _option_group_types
from .simulation import launcher
from .simulation.scenario import STAGES

# --- Constants ---------------------------------------------------------------

# Fields with a hand-written flag instead of the generic per-field one.
_SKIP_CLI_FIELDS = frozenset({"feature_cols"})


# --- Public functions --------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level ``pm-dem-sm`` parser with its two subcommands.

    Returns:
        argparse.ArgumentParser: Configured parser with ``dem-sim`` and
        ``ml-pipeline`` subparsers (``args.command`` selects between them).
    """
    parser = argparse.ArgumentParser(
        prog="pm-dem-sm",
        description=(
            "Bidisperse DEM surrogate-model toolkit: launch a DEM "
            "simulation, or run the RNN surrogate experiment pipeline."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    dem_parser = subparsers.add_parser(
        "dem-sim",
        help="Launch a DEM simulation as a subprocess (YADE implemented; BlazeDEM not yet).",
        description="Launch a DEM simulation as a subprocess. --dem-backend yade requires YADE installed and on PATH.",
    )
    _add_dem_sim_arguments(dem_parser)

    post_parser = subparsers.add_parser(
        "dem-post",
        help="Post-process a finished DEM run directory (parquet frames, profiles, validation).",
        description=(
            "Convert the frames to float32 parquet, compute the segregation profiles "
            "(dataset runs) or the bulk toe / shoulder (calibrate runs), and write the "
            "validation summary to the manifest and validation.json."
        ),
    )
    post_parser.add_argument("run_dir", type=Path, help="Run directory of run_simulation.py.")
    post_parser.add_argument(
        "--keep-csv", action="store_true", help="Keep the frame CSVs after conversion."
    )

    view_parser = subparsers.add_parser(
        "dem-view",
        help="View a DEM run directory in 2D or 3D (live while it runs), or save a PNG / GIF.",
        description=(
            "End-on (or 3D) view of the slice: particles coloured by species or speed "
            "inside the rotating liner, with angle marks, the toe / shoulder targets and "
            "the stage, time and mill-log values. Shows the recorded frames and the preview "
            "snapshots of every stage. Without --save it opens a window that follows new "
            "views; keys: left/right, up/down (10 views), home/end, space play/pause, "
            "f follow, c colours, m angle marks, s save PNG; in 3D drag to turn."
        ),
    )
    view_parser.add_argument("run_dir", type=Path, help="Run directory of run_simulation.py.")
    view_parser.add_argument(
        "--frame",
        type=int,
        default=None,
        help="Frame (or preview snapshot) to show (default: newest, following).",
    )
    view_parser.add_argument(
        "--3d", dest="three_d", action="store_true", help="3D view (drag to turn it)."
    )
    view_parser.add_argument(
        "--no-marks", action="store_true", help="Hide the angle marks and target guides."
    )
    view_parser.add_argument(
        "--source",
        choices=("all", "frames", "preview"),
        default="all",
        help="Recorded frames, preview snapshots, or both (default).",
    )
    view_parser.add_argument(
        "--color", choices=("species", "speed"), default="species", help="Particle colours."
    )
    view_parser.add_argument(
        "--vmax",
        type=float,
        default=None,
        help="Top of the speed scale, m/s (default 1.5 x liner speed).",
    )
    view_parser.add_argument(
        "--save",
        type=Path,
        default=None,
        help="Write instead of opening a window: .png (one frame) or .gif / .mp4 (all frames).",
    )
    view_parser.add_argument(
        "--every", type=int, default=1, help="Animation: use every N-th frame."
    )
    view_parser.add_argument(
        "--fps", type=int, default=10, help="Playback / animation frames per second."
    )

    ml_parser = subparsers.add_parser(
        "ml-pipeline",
        help="Run the experiment pipeline (simulate / process / train / predict / metrics / visualization).",
        description=(
            "Run the experiment pipeline (simulate / process / train / predict / "
            "metrics / visualization). Pass --config path.json to load settings from "
            "JSON; when set, other pipeline flags are ignored."
        ),
    )
    _add_ml_pipeline_arguments(ml_parser)

    return parser


def config_from_args(args: argparse.Namespace) -> ExperimentConfig:
    """Resolve ``ExperimentConfig`` from parsed ``ml-pipeline`` CLI args.

    If ``args.config`` is set, load only from that JSON file; all other
    pipeline flags are ignored. Otherwise apply any non-``None`` flags via
    :meth:`~pm_dem_sm.config.ExperimentConfig.with_overrides` (flat leaf names).

    Args:
        args: Namespace produced by parsing the ``ml-pipeline`` subcommand.

    Returns:
        ExperimentConfig: Defaults with any non-``None`` CLI overrides
        applied, or the JSON-loaded config when ``--config`` is present.
    """
    if args.config is not None:
        return ExperimentConfig.from_json(args.config)

    overrides: dict[str, Any] = {}
    for name in _leaf_override_names():
        value = getattr(args, name, None)
        if value is not None:
            overrides[name] = value
    return ExperimentConfig().with_overrides(**overrides) if overrides else ExperimentConfig()


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI args, dispatch to the selected subcommand, return process exit code.

    Args:
        argv: Optional argument list (as for ``ArgumentParser.parse_args``);
            ``None`` uses ``sys.argv``.

    Returns:
        int: ``0`` on success; a nonzero exit code on failure (e.g. YADE not
        found, an unimplemented DEM backend, or the DEM subprocess itself
        exiting nonzero).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "dem-sim":
        return _run_dem_sim(args)
    if args.command == "dem-post":
        return _run_dem_post(args.run_dir, keep_csv=args.keep_csv)
    if args.command == "dem-view":
        return _run_dem_view(args)
    return _run_ml_pipeline(args)


# --- Private helper functions ------------------------------------------------


def _bool_fields(cls: type) -> frozenset[str]:
    """Return the names of ``cls``'s fields annotated as ``bool``."""
    return frozenset(name for name, hint in get_type_hints(cls).items() if hint is bool)


def _path_fields(cls: type) -> frozenset[str]:
    """Return the names of ``cls``'s fields annotated as ``Path``."""
    return frozenset(name for name, hint in get_type_hints(cls).items() if hint is Path)


def _add_config_flag(container: Any, f, owning_cls: type) -> None:
    """Add one typed flag for a dataclass field; dest is the leaf field name."""
    flag = f"--{f.name.replace('_', '-')}"
    hint = get_type_hints(owning_cls)[f.name]
    default_repr = f.default
    if f.name in _bool_fields(owning_cls):
        container.add_argument(
            flag,
            action=argparse.BooleanOptionalAction,
            default=None,
            help=f"Override {f.name} (default: {default_repr}).",
        )
    elif f.name in _path_fields(owning_cls):
        container.add_argument(
            flag,
            type=Path,
            default=None,
            help=f"Override {f.name} (default: {default_repr}).",
        )
    elif hint is int:
        container.add_argument(
            flag,
            type=int,
            default=None,
            help=f"Override {f.name} (default: {default_repr}).",
        )
    elif hint is float:
        container.add_argument(
            flag,
            type=float,
            default=None,
            help=f"Override {f.name} (default: {default_repr}).",
        )
    else:
        container.add_argument(
            flag,
            type=str,
            default=None,
            help=f"Override {f.name} (default: {default_repr}).",
        )


def _add_ml_pipeline_arguments(parser: argparse.ArgumentParser) -> None:
    """Add all ``ExperimentConfig`` flags (plus ``--config``) to the ``ml-pipeline`` subparser.

    Emits one flag per core ``ExperimentConfig`` field and per nested options
    leaf (except ``feature_cols``, which uses ``--feature-cols``). Help text
    is grouped to match the nested JSON layout; flag names stay independent
    (``--epochs``, not ``--training-epochs``). This is also where
    ``--dem-backend``, ``--do-simulate``, and ``--do-process`` come from --
    they're plain ``ExperimentConfig`` fields like any other, so no extra
    wiring is needed here beyond this generic loop.
    """
    parser.add_argument(
        "--config",
        type=Path,
        metavar="JSON",
        help=(
            "JSON file with ExperimentConfig fields (nested option groups). "
            "When provided, all other pipeline config arguments are ignored."
        ),
    )

    core = parser.add_argument_group("pipeline")
    group_types = _option_group_types()
    for f in fields(ExperimentConfig):
        if f.name in _SKIP_CLI_FIELDS or f.name in group_types:
            continue
        _add_config_flag(core, f, ExperimentConfig)

    core.add_argument(
        "--feature-cols",
        nargs="+",
        default=None,
        metavar="COL",
        dest="feature_cols",
        help="Override feature_cols (space-separated column names).",
    )

    for group_name, group_cls in group_types.items():
        arg_group = parser.add_argument_group(group_name)
        for sf in fields(group_cls):
            _add_config_flag(arg_group, sf, group_cls)


def _add_dem_sim_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the ``dem-sim`` subcommand's flags (backend, script, executable, scenario, stages)."""
    parser.add_argument(
        "--dem-backend",
        choices=DEM_BACKENDS,
        default="yade",
        dest="dem_backend",
        help="DEM backend to launch (default: 'yade'; 'blaze' not yet implemented).",
    )
    parser.add_argument(
        "--script",
        type=Path,
        default=None,
        metavar="PATH",
        help="DEM script to run (default: the packaged run_simulation.py for --dem-backend).",
    )
    parser.add_argument(
        "--yade-executable",
        type=str,
        default=None,
        metavar="NAME",
        help="YADE executable name or path (default: first of 'yade', 'yadedaily' on PATH).",
    )
    parser.add_argument(
        "--scenario",
        type=Path,
        default=None,
        metavar="PATH",
        help="Scenario JSON (see configs/simulation/); default: built-in defaults.",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        metavar="PATH",
        help="Output directory (default: data/raw/yade_runs/<scenario name>).",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=None,
        metavar="N",
        help="OpenMP threads for YADE (default: scenario solver.threads, else YADE's default).",
    )
    parser.add_argument(
        "--from-stage",
        choices=STAGES,
        default=None,
        help="Resume from this stage using the previous stage's checkpoint in --run-dir.",
    )
    parser.add_argument(
        "--to-stage",
        choices=STAGES,
        default=None,
        help="Stop after this stage (default: record).",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Open the YADE Qt viewer instead of running headless.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="N",
        help="Override the scenario seed (replicates); '_s<N>' is appended to the run name.",
    )
    parser.add_argument(
        "--no-postprocess",
        action="store_true",
        help="Do not post-process the run directory after a successful run.",
    )
    parser.add_argument(
        "--extend-record",
        type=float,
        default=None,
        metavar="SECONDS",
        help="Record SECONDS more after the finished record stage of --run-dir "
        "(e.g. a dataset whose charge is still evolving); post-processed again after.",
    )


def _leaf_override_names() -> list[str]:
    """Return the CLI dest names that map onto ``ExperimentConfig.with_overrides``."""
    names = []
    group_types = _option_group_types()
    for f in fields(ExperimentConfig):
        if f.name in group_types:
            continue
        names.append(f.name)
    for group_cls in group_types.values():
        names.extend(sf.name for sf in fields(group_cls))
    return names


def _run_dem_sim(args: argparse.Namespace) -> int:
    """Handle the ``dem-sim`` subcommand: launch the DEM backend, return its exit code."""
    try:
        extra = []
        if args.from_stage:
            extra += ["--from-stage", args.from_stage]
        if args.to_stage:
            extra += ["--to-stage", args.to_stage]
        if args.gui:
            extra.append("--gui")
        if args.seed is not None:
            extra += ["--seed", str(args.seed)]
        if args.extend_record is not None:
            if args.run_dir is None:
                print("--extend-record needs --run-dir")
                return 1
            extra += ["--extend-record", str(args.extend_record)]
        result = launcher.launch_simulation(
            script=args.script,
            yade_executable=args.yade_executable,
            extra_args=extra,
            backend=args.dem_backend,
            scenario=args.scenario,
            run_dir=args.run_dir,
            threads=args.threads,
            headless=not args.gui,
        )
    except (FileNotFoundError, NotImplementedError, ValueError) as exc:
        print(str(exc))
        return 1
    if result.returncode != 0 or args.no_postprocess or args.dem_backend != "yade":
        return result.returncode
    run_dir = args.run_dir or launcher.default_run_dir(args.scenario, args.seed)
    return _run_dem_post(run_dir)


def _run_dem_post(run_dir: Path, keep_csv: bool = False) -> int:
    """Handle ``dem-post`` (and the post-processing after ``dem-sim``); return an exit code."""
    from .simulation import postprocess

    if not (Path(run_dir) / "manifest.json").exists():
        print(f"No manifest.json in {run_dir}: nothing to post-process.")
        return 1
    validation = postprocess.postprocess_run(run_dir, delete_csv=not keep_csv)
    failed = [k for k, v in validation.items() if v["status"] == "fail"]
    if failed:
        print(f"[validation] failed checks: {', '.join(failed)} (see {run_dir}/validation.json)")
    return 0


def _run_dem_view(args: argparse.Namespace) -> int:
    """Handle ``dem-view``; return an exit code."""
    from .visualization import run_viewer

    if not (Path(args.run_dir) / "manifest.json").exists():
        print(f"No manifest.json in {args.run_dir}: not a run directory.")
        return 1
    view = run_viewer.RunView.open(args.run_dir, source=args.source)
    try:
        if args.save is not None:
            out = run_viewer.save(
                view,
                args.save,
                frame=args.frame,
                color=args.color,
                every=args.every,
                fps=args.fps,
                vmax=args.vmax,
                three_d=args.three_d,
                marks=not args.no_marks,
            )
            print(f"[dem-view] wrote {out}")
        else:
            run_viewer.show(
                view,
                frame=args.frame,
                color=args.color,
                vmax=args.vmax,
                fps=args.fps,
                three_d=args.three_d,
                marks=not args.no_marks,
            )
    except ValueError as err:
        print(f"[dem-view] {err}")
        return 1
    return 0


def _run_ml_pipeline(args: argparse.Namespace) -> int:
    """Handle the ``ml-pipeline`` subcommand: resolve config and run the pipeline."""
    from .tf_quiet import silence_tensorflow

    silence_tensorflow()
    config = config_from_args(args)
    # Attribute lookup (not a bare name) so the lazy module __getattr__ below applies.
    sys.modules[__name__].run_experiment_pipeline(config)
    return 0


def __getattr__(name):
    """Import ``run_experiment_pipeline`` on first access (PEP 562).

    The pipeline pulls in pandas and TensorFlow; importing it lazily keeps
    ``dem-sim`` usable on a machine that only has YADE.
    """
    if name == "run_experiment_pipeline":
        from .experiment_pipeline import run_experiment_pipeline

        return run_experiment_pipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# --- Script entry point ------------------------------------------------------

if __name__ == "__main__":
    raise SystemExit(main())

"""Tests for ExperimentConfig JSON loading and CLI argument resolution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pm_dem_sm.cli import build_parser, config_from_args, main
from pm_dem_sm.config import REPO_ROOT, ExperimentConfig, PredictionOptions, TrainingOptions
from pm_dem_sm.experiment_pipeline import run_experiment_pipeline


def test_from_dict_coerces_paths_and_bools():
    cfg = ExperimentConfig.from_dict(
        {
            "data_dir": "data/processed/foo",
            "do_train": True,
            "frames_in": 10,
        }
    )
    assert cfg.data_dir == Path("data/processed/foo")
    assert cfg.do_train is True
    assert cfg.frames_in == 10
    assert cfg.training.epochs == 20
    # C14-5 defaults: seed frames 126-140 (6.30-7.00 s), first prediction at 7.05 s.
    assert cfg.prediction.start_frame == 126
    assert cfg.prediction.dt0 == 7.05


def test_from_dict_nested_groups():
    cfg = ExperimentConfig.from_dict(
        {
            "do_train": True,
            "training": {"epochs": 3, "batch_size": 32},
            "prediction": {"start_frame": 7, "pred_out_dir": "data/interim/preds"},
            "visualization": {"show_plots": False},
        }
    )
    assert cfg.do_train is True
    assert cfg.training.epochs == 3
    assert cfg.training.batch_size == 32
    assert cfg.training.learning_rate == 0.01
    assert cfg.prediction.start_frame == 7
    assert cfg.prediction.pred_out_dir == Path("data/interim/preds")
    assert cfg.visualization.show_plots is False


def test_from_dict_rejects_unknown_keys():
    with pytest.raises(ValueError, match="Unknown ExperimentConfig keys"):
        ExperimentConfig.from_dict({"not_a_field": 1})


def test_from_dict_rejects_flat_nested_keys():
    with pytest.raises(ValueError, match="Unknown ExperimentConfig keys"):
        ExperimentConfig.from_dict({"epochs": 5})


def test_from_dict_rejects_unknown_nested_keys():
    with pytest.raises(ValueError, match="Unknown TrainingOptions keys"):
        ExperimentConfig.from_dict({"training": {"not_a_field": 1}})


def test_from_json_roundtrip(tmp_path: Path):
    original = ExperimentConfig(
        do_train=True,
        do_predict=False,
        prediction=PredictionOptions(start_frame=42),
        data_dir=Path("data/processed/example"),
    )
    path = tmp_path / "pipeline.json"
    path.write_text(json.dumps(original.to_dict()), encoding="utf-8")

    loaded = ExperimentConfig.from_json(path)
    assert loaded.do_train is True
    assert loaded.do_predict is False
    assert loaded.prediction.start_frame == 42
    assert loaded.data_dir == Path("data/processed/example")
    assert "prediction" in original.to_dict()
    assert original.to_dict()["prediction"]["start_frame"] == 42


def test_default_fields_for_simulate_and_process_stages():
    cfg = ExperimentConfig()
    assert cfg.dem_backend == "yade"
    assert cfg.do_simulate is False
    assert cfg.do_process is False
    assert cfg.raw_data_dir == REPO_ROOT / "data" / "raw"


def test_cli_config_json_ignores_other_flags(tmp_path: Path):
    path = tmp_path / "cfg.json"
    path.write_text(
        json.dumps(
            {
                "do_train": True,
                "do_predict": False,
                "prediction": {"start_frame": 99},
            }
        ),
        encoding="utf-8",
    )
    parser = build_parser()
    args = parser.parse_args(
        [
            "ml-pipeline",
            "--config",
            str(path),
            "--do-train",
            "--start-frame",
            "1",
            "--do-predict",
        ]
    )
    cfg = config_from_args(args)
    assert cfg.do_train is True
    assert cfg.prediction.start_frame == 99
    assert cfg.do_predict is False


def test_cli_flags_override_defaults():
    parser = build_parser()
    args = parser.parse_args(
        [
            "ml-pipeline",
            "--do-train",
            "--no-show-plots",
            "--start-frame",
            "10",
            "--epochs",
            "5",
            "--feature-cols",
            "x",
            "y",
            "z",
        ]
    )
    cfg = config_from_args(args)
    assert cfg.do_train is True
    assert cfg.visualization.show_plots is False
    assert cfg.prediction.start_frame == 10
    assert cfg.training.epochs == 5
    assert cfg.feature_cols == ["x", "y", "z"]


def test_cli_flags_cover_simulate_and_process_stages():
    parser = build_parser()
    args = parser.parse_args(
        ["ml-pipeline", "--do-simulate", "--do-process", "--dem-backend", "blaze"]
    )
    cfg = config_from_args(args)
    assert cfg.do_simulate is True
    assert cfg.do_process is True
    assert cfg.dem_backend == "blaze"


def test_with_overrides_flat_leaves_and_groups():
    cfg = ExperimentConfig().with_overrides(epochs=8, start_frame=3)
    assert cfg.training.epochs == 8
    assert cfg.prediction.start_frame == 3

    cfg2 = cfg.with_overrides(training=TrainingOptions(epochs=1), batch_size=16)
    assert cfg2.training.epochs == 1
    assert cfg2.training.batch_size == 16


def test_example_pipeline_json_loads():
    cfg = ExperimentConfig.from_json(REPO_ROOT / "configs" / "pipeline_example.json")
    assert cfg.prediction.start_frame == 66
    assert cfg.training.epochs == 20
    assert cfg.visualization.save_figures is True
    # Fields added after this file was written should still default cleanly.
    assert cfg.dem_backend == "yade"
    assert cfg.do_simulate is False


def test_run_experiment_pipeline_accepts_flat_overrides(monkeypatch):
    monkeypatch.setattr("pm_dem_sm.experiment_pipeline.silence_tensorflow", lambda: None)
    results = run_experiment_pipeline(
        ExperimentConfig(do_train=False, do_predict=False, do_metrics=False, do_visualization=False),
        epochs=9,
    )
    assert results["config"].training.epochs == 9
    assert results["config"].do_predict is False


def test_run_experiment_pipeline_prints_enabled_stage_banners(capsys, monkeypatch):
    monkeypatch.setattr("pm_dem_sm.experiment_pipeline.silence_tensorflow", lambda: None)
    run_experiment_pipeline(
        ExperimentConfig(do_train=False, do_predict=False, do_metrics=False, do_visualization=False)
    )
    out = capsys.readouterr().out
    assert "pm-dem-sm ml-pipeline" in out
    assert "Stages: (none enabled)" in out
    assert "Pipeline complete." in out
    assert "STAGE" not in out


def test_build_parser_dem_sim_defaults():
    parser = build_parser()
    args = parser.parse_args(["dem-sim"])
    assert args.command == "dem-sim"
    assert args.script is None
    assert args.yade_executable is None
    assert args.scenario is None
    assert args.gui is False
    assert args.dem_backend == "yade"


def test_build_parser_dem_sim_rejects_unknown_backend():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["dem-sim", "--dem-backend", "not-a-backend"])


def test_build_parser_requires_a_subcommand():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_main_dem_sim_missing_yade_returns_nonzero(monkeypatch, capsys):
    def _raise(**kwargs):
        """Simulate YADE missing from PATH."""
        raise FileNotFoundError("YADE executable 'yade' not found on PATH.")

    monkeypatch.setattr("pm_dem_sm.cli.launcher.launch_simulation", _raise)
    exit_code = main(["dem-sim"])
    assert exit_code == 1
    assert "not found on PATH" in capsys.readouterr().out


def test_main_dem_sim_blaze_backend_not_implemented(capsys):
    exit_code = main(["dem-sim", "--dem-backend", "blaze"])
    assert exit_code == 1
    assert "not yet implemented" in capsys.readouterr().out


def test_main_ml_pipeline_dispatches_to_run_experiment_pipeline(monkeypatch):
    monkeypatch.setattr("pm_dem_sm.tf_quiet.silence_tensorflow", lambda: None)
    captured = {}
    monkeypatch.setattr(
        "pm_dem_sm.cli.run_experiment_pipeline",
        lambda config: captured.setdefault("config", config),
    )
    exit_code = main(["ml-pipeline", "--do-train"])
    assert exit_code == 0
    assert captured["config"].do_train is True


def test_progress_helpers_emit_banners_and_track(capsys):
    from pm_dem_sm.progress import complete, plan, stage, track

    plan(["Prediction", "Metrics"])
    stage(1, 2, "Prediction")
    assert list(track(range(3), desc="test", unit="n", disable=True)) == [0, 1, 2]
    complete()
    out = capsys.readouterr().out
    assert "Stages: Prediction -> Metrics" in out
    assert "STAGE 1/2: Prediction" in out
    assert "Pipeline complete." in out

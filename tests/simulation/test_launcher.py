"""Tests for the YADE subprocess launcher (never imports yade itself)."""

from __future__ import annotations

import subprocess

import pytest

from pm_dem_sm.simulation import launcher as dem_launcher


def test_default_simulation_script_points_at_packaged_file():
    assert dem_launcher.DEFAULT_SIMULATION_SCRIPT.name == "run_simulation.py"
    assert dem_launcher.DEFAULT_SIMULATION_SCRIPT.parent.name == "yade_dem"
    assert dem_launcher.DEFAULT_SIMULATION_SCRIPT.exists()


def test_default_simulation_scripts_cover_both_backends():
    assert set(dem_launcher.DEFAULT_SIMULATION_SCRIPTS) == {"yade", "blaze"}
    for backend, path in dem_launcher.DEFAULT_SIMULATION_SCRIPTS.items():
        assert path.name == "run_simulation.py"
        assert path.parent.name == f"{backend}_dem"
        assert path.exists()


def test_find_yade_executable_returns_none_when_missing():
    assert dem_launcher.find_yade_executable("definitely-not-a-real-executable-xyz") is None


def test_launch_simulation_raises_when_yade_missing(monkeypatch):
    monkeypatch.setattr(dem_launcher, "find_yade_executable", lambda name: None)
    with pytest.raises(FileNotFoundError, match="not found on PATH"):
        dem_launcher.launch_simulation()


def test_launch_simulation_uses_default_script_and_resolved_executable(monkeypatch):
    monkeypatch.setattr(dem_launcher, "find_yade_executable", lambda name: "/usr/bin/yade")

    captured = {}

    def fake_run(cmd, check=False):
        """Record the command instead of running it."""
        captured["cmd"] = cmd
        captured["check"] = check
        return subprocess.CompletedProcess(cmd, returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = dem_launcher.launch_simulation()
    assert captured["cmd"] == [
        "/usr/bin/yade", "-n", "-x", str(dem_launcher.DEFAULT_SIMULATION_SCRIPT)
    ]
    assert captured["check"] is False
    assert result.returncode == 0


def test_launch_simulation_custom_script_and_extra_args(monkeypatch, tmp_path):
    monkeypatch.setattr(dem_launcher, "find_yade_executable", lambda name: "/opt/yade/yade-2024")

    custom_script = tmp_path / "custom_sim.py"
    custom_script.write_text("# custom", encoding="utf-8")

    captured = {}

    def fake_run(cmd, check=False):
        """Record the command instead of running it."""
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    dem_launcher.launch_simulation(
        script=custom_script,
        yade_executable="yade-2024",
        extra_args=["--from-stage", "spinup"],
        headless=False,
    )
    assert captured["cmd"] == [
        "/opt/yade/yade-2024", str(custom_script), "--from-stage", "spinup"
    ]


def test_launch_simulation_propagates_nonzero_returncode(monkeypatch):
    monkeypatch.setattr(dem_launcher, "find_yade_executable", lambda name: "/usr/bin/yade")
    monkeypatch.setattr(
        subprocess, "run", lambda cmd, check=False: subprocess.CompletedProcess(cmd, returncode=3)
    )

    result = dem_launcher.launch_simulation()
    assert result.returncode == 3


def test_launch_simulation_blaze_backend_not_implemented():
    with pytest.raises(NotImplementedError, match="not yet implemented"):
        dem_launcher.launch_simulation(backend="blaze")


def test_find_yade_executable_falls_back_to_daily_build(monkeypatch):
    monkeypatch.setattr(
        dem_launcher.shutil,
        "which",
        lambda name: "/usr/bin/yadedaily" if name == "yadedaily" else None,
    )
    assert dem_launcher.find_yade_executable() == "/usr/bin/yadedaily"
    assert dem_launcher.find_yade_executable("yade") is None


def test_build_command_with_scenario_threads_and_run_dir():
    cmd = dem_launcher.build_command(
        "/usr/bin/yadedaily", scenario="s.json", run_dir="out", threads=8
    )
    assert cmd == [
        "/usr/bin/yadedaily", "-n", "-x", "-j", "8", str(dem_launcher.DEFAULT_SIMULATION_SCRIPT),
        "--scenario", "s.json", "--run-dir", "out",
    ]


def test_launch_simulation_validates_scenario_and_uses_its_threads(monkeypatch, tmp_path):
    monkeypatch.setattr(dem_launcher, "find_yade_executable", lambda name: "/usr/bin/yade")
    captured = {}

    def fake_run(cmd, check=False):
        """Record the command instead of running it."""
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    scenario = tmp_path / "s.json"
    scenario.write_text('{"solver": {"threads": 6}, "contact": {"rolling_resistance": 0.25}}', encoding="utf-8")
    dem_launcher.launch_simulation(scenario=scenario)
    assert captured["cmd"][3:5] == ["-j", "6"]

    scenario.write_text('{"mill": {"source": "cad"}}', encoding="utf-8")
    with pytest.raises(ValueError, match="mill.source"):
        dem_launcher.launch_simulation(scenario=scenario)

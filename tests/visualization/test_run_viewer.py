"""Tests for the 2D run viewer (``dem-view``), headless (Agg backend)."""

from __future__ import annotations

import json
import math
from pathlib import Path
from types import SimpleNamespace

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest
from matplotlib.backend_bases import KeyEvent

from pm_dem_sm import cli
from pm_dem_sm.simulation import mill_geometry
from pm_dem_sm.simulation.scenario import load_scenario
from pm_dem_sm.visualization import run_viewer

# --- Setup -------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE = REPO_ROOT / "configs" / "simulation" / "smoke_test.json"


# --- Helpers -----------------------------------------------------------------


def _frame(rng, n=80):
    """Return one synthetic frame of rocks and steel balls in the 2 m smoke mill."""
    r = np.where(np.arange(n) < 60, 0.03, 0.05)
    a = rng.uniform(math.radians(200), math.radians(340), n)
    rho = rng.uniform(0.3, 0.8, n)
    return pd.DataFrame(
        {
            "id": np.arange(n),
            "x": rho * np.cos(a),
            "y": rho * np.sin(a),
            "z": rng.uniform(0.02, 0.18, n),
            "r": r,
            "m": np.where(r < 0.05, "rock", "steel"),
            "vx": rng.normal(0, 1, n),
            "vy": 0.0,
            "vz": 0.0,
        }
    )


def _write_frame(run, k, t, rng, parquet=False):
    """Write frame ``k`` at time ``t`` and its index row."""
    df = _frame(rng)
    stem = run / "frames" / f"frame_{k:05d}"
    if parquet:
        df.to_parquet(stem.with_suffix(".parquet"))
    else:
        df.to_csv(stem.with_suffix(".csv"), index=False)
    with open(run / "frames_index.csv", "a") as f:
        f.write(f"{k},{t},{k * 100}\n")


def _run(tmp_path, run_type="dataset", n_frames=5, stages=None):
    """Write a synthetic run directory and return its path."""
    rng = np.random.default_rng(1)
    scen = load_scenario(SMOKE).to_dict()
    scen["run"] = {"type": run_type, "ic_dir": "x" if run_type == "dataset" else None}
    run = tmp_path / f"{run_type}_run"
    (run / "frames").mkdir(parents=True)
    if stages is None:
        stages = {"load_ic": {"sim_time_start_s": 0.0, "sim_time_end_s": 0.0}}
    (run / "manifest.json").write_text(json.dumps({"scenario": scen, "stages": stages}))
    if n_frames:
        (run / "frames_index.csv").write_text("frame,time,iter\n")
        for k in range(n_frames):
            _write_frame(run, k, 0.1 * k, rng, parquet=k % 2 == 1)
    log = pd.DataFrame(
        {
            "time": np.arange(0, 1.0, 0.05),
            "stage": "record",
            "revolutions": 0.01,
            "angle_all_deg": 30.0,
            "power_kW": 5.0,
            "kinetic_J": 2000.0,
            "mean_speed_m_s": 0.5,
        }
    )
    log.to_csv(run / "mill_log.csv", index=False)
    return run


def _key(fig, key):
    """Send a key press to ``fig``."""
    fig.canvas.callbacks.process("key_press_event", KeyEvent("key_press_event", fig.canvas, key))


# --- Tests -------------------------------------------------------------------


def test_rotation_start_per_run_type(tmp_path):
    scen = load_scenario(SMOKE)
    done = {
        "build": {"sim_time_start_s": 0.0, "sim_time_end_s": 0.0},
        "settle": {"sim_time_start_s": 3.0, "sim_time_end_s": 5.0},
    }
    # calibrate, spin-up still running: it started when settle ended.
    assert run_viewer.rotation_start({"stages": done}, scen) == 5.0
    done["spinup"] = {"sim_time_start_s": 5.0, "sim_time_end_s": 9.0}
    assert run_viewer.rotation_start({"stages": done}, scen) == 5.0
    scen.run.type = "make_ic"
    assert run_viewer.rotation_start({"stages": done}, scen) is None
    view = run_viewer.RunView.open(_run(tmp_path))
    assert view.rotation_start_s == 0.0
    assert view.mill_phase(2.0) == pytest.approx(view.omega * 2.0)
    assert view.mill_phase(-1.0) == 0.0


def test_frame_table_reads_csv_and_parquet_and_skips_partial(tmp_path):
    run = _run(tmp_path)
    (run / "frames" / "frame_00004.csv").unlink()  # e.g. mid-conversion
    with open(run / "frames_index.csv", "a") as f:
        f.write("5,0.5")  # row being written
    table = run_viewer.frame_table(run)
    assert list(table["frame"]) == [0, 1, 2, 3]
    assert [p.suffix for p in table["path"]] == [".csv", ".parquet", ".csv", ".parquet"]
    assert len(run_viewer.read_frame(table["path"][1])) == 80


def test_make_ic_shows_the_saved_packing(tmp_path):
    run = _run(tmp_path, "make_ic", n_frames=0, stages={})
    (run / "ic").mkdir()
    _frame(np.random.default_rng(0)).to_csv(run / "ic" / "positions.csv", index=False)
    (run / "ic" / "ic.json").write_text(json.dumps({"sim_time_s": 13.2}))
    view = run_viewer.RunView.open(run)
    table = view.frames()
    assert len(table) == 1 and table["time"][0] == 13.2
    assert view.mill_phase(13.2) == 0.0
    out = run_viewer.save(view, tmp_path / "ic.png")
    assert out.stat().st_size > 0


def test_liner_outline_is_the_profile_rotated(tmp_path):
    scen = load_scenario(SMOKE)
    phase = 0.3
    base = np.asarray(mill_geometry.liner_profile(scen.mill))
    rot = np.array([[math.cos(phase), -math.sin(phase)], [math.sin(phase), math.cos(phase)]])
    outline = run_viewer.liner_outline(scen, phase)
    assert np.allclose(outline[0], outline[-1])
    assert np.allclose(outline[:-1], base @ rot.T, atol=1e-9)


def test_log_at_nearest_row(tmp_path):
    run = _run(tmp_path)
    assert run_viewer.log_at(run, 0.31)["time"] == pytest.approx(0.30)
    assert run_viewer.log_at(tmp_path, 0.0) is None


@pytest.mark.parametrize(
    "name,color", [("f.png", "species"), ("s.png", "speed"), ("a.gif", "species")]
)
def test_save(tmp_path, name, color):
    view = run_viewer.RunView.open(_run(tmp_path))
    out = run_viewer.save(view, tmp_path / name, color=color, every=2, fps=4)
    assert out.exists() and out.stat().st_size > 0
    with pytest.raises(ValueError, match="No frame 99"):
        run_viewer.save(view, tmp_path / "x.png", frame=99)


def test_interactive_keys_and_follow(tmp_path):
    run = _run(tmp_path)
    viewer = run_viewer.show(run_viewer.RunView.open(run), block=False)
    fig, state = viewer["fig"], viewer["state"]
    assert state["follow"] and state["k"] == 4
    _key(fig, "left")
    assert state["k"] == 3 and not state["follow"]
    _key(fig, "home")
    assert state["k"] == 0
    _key(fig, "down")
    assert state["k"] == 0
    _key(fig, "up")
    assert state["k"] == 4
    _key(fig, "c")
    assert state["color"] == "speed"
    _key(fig, "s")
    assert (run / "view_frame_00004.png").exists()
    # Following picks up a frame written after the window opened.
    _key(fig, "f")
    _write_frame(run, 5, 0.5, np.random.default_rng(2))
    viewer["tick"]()
    assert state["k"] == 5
    # Playback from the start, one frame per tick, stops at the end.
    _key(fig, " ")
    assert state["play"] and state["k"] == 0
    for _ in range(10):
        viewer["tick"]()
    assert state["k"] == 5 and not state["play"]


def test_dem_view_cli(tmp_path):
    assert cli.main(["dem-view", str(tmp_path)]) == 1
    run = _run(tmp_path)
    assert cli.main(["dem-view", str(run), "--save", str(tmp_path / "v.png"), "--frame", "2"]) == 0
    assert (tmp_path / "v.png").exists()
    assert cli.main(["dem-view", str(run), "--save", str(tmp_path / "w.png"), "--frame", "9"]) == 1


def test_as_row():
    row = run_viewer._as_row({"frame": 3, "time": 0.25, "path": Path("p.csv")})
    assert row == SimpleNamespace(frame=3, time=0.25, path=Path("p.csv"))

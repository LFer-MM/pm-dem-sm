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


def _write_previews(run, times, stages, angles):
    """Write preview snapshots and their index (as capture.start_preview does)."""
    (run / "preview").mkdir(exist_ok=True)
    rng = np.random.default_rng(5)
    lines = ["snap,time,iter,stage,mill_angle_deg"]
    for k, (t, stage, angle) in enumerate(zip(times, stages, angles)):
        _frame(rng).to_csv(run / "preview" / f"snap_{k:05d}.csv", index=False)
        lines.append(f"{k},{t},{k},{stage},{'' if angle is None else angle}")
    (run / "preview_index.csv").write_text("\n".join(lines) + "\n")


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
    assert (row.kind, row.frame, row.time, row.path) == ("frame", 3, 0.25, Path("p.csv"))
    assert np.isnan(row.angle_deg)


def test_previews_merge_with_frames(tmp_path):
    run = _run(
        tmp_path,
        "calibrate",
        n_frames=3,
        stages={"spinup": {"sim_time_start_s": 0.0, "sim_time_end_s": 0.0}},
    )
    # frames at 0.0, 0.1, 0.2: shift them after the snapshots
    idx = run / "frames_index.csv"
    idx.write_text("frame,time,iter\n0,2.0,1\n1,2.1,2\n2,2.2,3\n")
    _write_previews(
        run,
        [0.0, 0.5, 1.0, 2.1, 2.5],
        ["fill", "settle", "spinup", "record", "record"],
        [0.0, None, 30.0, 40.0, 50.0],
    )
    every = run_viewer.frame_table(run)
    assert list(every["kind"]) == ["preview"] * 3 + ["frame"] * 3 + ["preview"]
    assert list(every["time"]) == [0.0, 0.5, 1.0, 2.0, 2.1, 2.2, 2.5]
    assert len(run_viewer.frame_table(run, "preview")) == 5
    assert set(run_viewer.frame_table(run, "frames")["kind"]) == {"frame"}
    view = run_viewer.RunView.open(run)
    rows = [run_viewer._as_row(r) for _, r in every.iterrows()]
    # A recorded mill angle wins; without one the angle comes from the time.
    assert view.row_phase(rows[2]) == pytest.approx(math.radians(30.0))
    assert view.row_phase(rows[1]) == pytest.approx(view.mill_phase(0.5))
    assert rows[1].stage == "settle"
    assert run_viewer.find_frame(every, 1) == 4  # recorded frame 1
    assert run_viewer.find_frame(every, 4) == 6  # snapshot 4 (no frame 4)
    with pytest.raises(ValueError, match="No frame 9"):
        run_viewer.find_frame(every, 9)
    with pytest.raises(ValueError, match="source"):
        run_viewer.RunView.open(run, source="nope")


def test_angle_marks_follow_the_convention():
    marks = run_viewer.angle_marks(2.0)
    labels = {text: (x, y) for x, y, text in marks["labels"]}
    assert len(marks["ticks"]) == 36 and len(labels) == 12
    assert labels["0°"][0] > 0 and labels["0°"][1] == pytest.approx(0, abs=1e-9)
    assert labels["90°"][1] > 0 and labels["90°"][0] == pytest.approx(0, abs=1e-9)
    (p0, p1, x, y, text), shoulder = marks["targets"]
    assert "toe" in text and math.degrees(math.atan2(p1[1], p1[0])) % 360 == pytest.approx(
        run_viewer.TOE_MID_DEG
    )
    assert "shoulder" in shoulder[4]


@pytest.mark.parametrize("marks", [True, False])
def test_save_3d_and_marks(tmp_path, marks):
    run = _run(tmp_path)
    view = run_viewer.RunView.open(run)
    for three_d in (False, True):
        out = run_viewer.save(
            view,
            tmp_path / f"v{three_d}{marks}.png",
            three_d=three_d,
            marks=marks,
            color="speed" if three_d else "species",
        )
        assert out.stat().st_size > 0
    assert run_viewer.save(view, tmp_path / "a.gif", three_d=True, every=2).exists()


def test_interactive_3d_keeps_view_angle(tmp_path):
    viewer = run_viewer.show(run_viewer.RunView.open(_run(tmp_path)), block=False, three_d=True)
    fig, state = viewer["fig"], viewer["state"]
    ax = fig.axes[0]
    ax.view_init(elev=40.0, azim=10.0)
    _key(fig, "left")
    assert (ax.elev, ax.azim) == (40.0, 10.0)
    _key(fig, "m")
    assert state["marks"] is False


def test_dem_view_cli_3d(tmp_path):
    run = _run(tmp_path)
    out = tmp_path / "c.png"
    assert (
        cli.main(
            ["dem-view", str(run), "--3d", "--no-marks", "--source", "frames", "--save", str(out)]
        )
        == 0
    )
    assert out.exists()

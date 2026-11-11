"""Tests for the post-processing of DEM run directories (no YADE needed)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pm_dem_sm import cli
from pm_dem_sm.simulation import launcher, postprocess
from pm_dem_sm.simulation.scenario import load_scenario

# --- Setup -------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE = REPO_ROOT / "configs" / "simulation" / "smoke_test.json"
LOG_COLUMNS = ["time", "iter", "stage", "revolutions", "angle_all_deg", "angle_small_deg",
               "angle_large_deg", "com_height_m", "mean_speed_m_s", "kinetic_J", "torque_Nm",
               "power_kW", "overlap_mean_rel_d", "overlap_p99_rel_d", "overlap_max_rel_d",
               "impact_v_p99_m_s", "potential_J", "elastic_J", "dissipated_J",
               "rolling_dissipated_J", "unbalanced"]


# --- Helpers -----------------------------------------------------------------


def _frame(rng, n_small=300, n_large=60, arc=(214.0, 387.0)):
    """Return one synthetic frame: particles in an arc of the 2 m smoke mill."""
    rows = []
    for k in range(n_small + n_large):
        r = 0.03 if k < n_small else 0.05
        a = math.radians(rng.uniform(*arc))
        rho = rng.uniform(0.5, 0.92)
        rows.append({"id": k, "x": rho * math.cos(a), "y": rho * math.sin(a),
                     "z": rng.uniform(0.02, 0.18), "r": r, "m": "rock" if r < 0.05 else "steel",
                     "vx": 0.1, "vy": 0.0, "vz": 0.0})
    return pd.DataFrame(rows)


def _run_dir(tmp_path, run_type, n_frames=40, duration=4.0, ic_dir=None):
    """Write a synthetic run directory of the given run type."""
    rng = np.random.default_rng(0)
    scen = load_scenario(SMOKE).to_dict()
    if run_type == "dataset":
        ic_dir = ic_dir or "x"
    scen["run"] = {"type": run_type, "ic_dir": ic_dir}
    run = tmp_path / run_type
    (run / "frames").mkdir(parents=True)
    times = np.linspace(0, duration, n_frames)
    for k, t in enumerate(times):
        _frame(rng).to_csv(run / "frames" / f"frame_{k:05d}.csv", index=False)
    pd.DataFrame({"frame": range(n_frames), "time": times, "iter": range(n_frames)}).to_csv(
        run / "frames_index.csv", index=False)
    lt = np.arange(0, duration, 0.05)
    log = pd.DataFrame({c: 0.0 for c in LOG_COLUMNS}, index=range(lt.size))
    log["time"], log["stage"] = lt, "record"
    log["kinetic_J"], log["power_kW"], log["angle_all_deg"] = 50.0, 3.0, 60.0
    log["overlap_mean_rel_d"], log["overlap_p99_rel_d"], log["overlap_max_rel_d"] = 0.001, 0.005, 0.01
    log.to_csv(run / "mill_log.csv", index=False)
    forces = pd.DataFrame(np.zeros((lt.size, 72)), columns=[f"f_{5 * k}" for k in range(72)])
    forces.iloc[:, 44:72] = 10.0
    forces.iloc[:, 0:4] = 10.0
    forces.insert(0, "stage", "record")
    forces.insert(0, "time", lt)
    forces.to_csv(run / "liner_forces.csv", index=False)
    checks_ok = {"damping": 0.0, "escaped": 0, "overlap_p99_rel_d_max": 0.005,
                 "overlap_max_rel_d_max": 0.01, "steps_per_collision_at_p99": 30.0,
                 "energy_balance": {"residual_rel": 0.02}}
    stages = {"record": {"wall_s": 1.0, "checks": checks_ok}}
    if run_type == "calibrate":
        stages["spinup"] = {"checks": {"damping": 0.0, "escaped": 0},
                            "steady_state": {"steady": True}}
    if run_type != "calibrate" or ic_dir is not None:
        stages["load_ic"] = {"checks": {"damping": 0.0, "escaped": 0}}
    (run / "manifest.json").write_text(json.dumps({"scenario": scen, "stages": stages}))
    return run


# --- Tests -------------------------------------------------------------------


def test_convert_frames_to_float32_parquet(tmp_path):
    run = _run_dir(tmp_path, "dataset", n_frames=3)
    csv_before = pd.read_csv(run / "frames" / "frame_00001.csv")
    res = postprocess.convert_frames(run)
    assert res == {"converted": 3, "parquet": 3, "bytes": res["bytes"]}
    assert not list((run / "frames").glob("*.csv"))
    df = pd.read_parquet(run / "frames" / "frame_00001.parquet")
    assert df["x"].dtype == np.float32 and df["id"].dtype == np.int32
    assert np.allclose(df["x"], csv_before["x"], atol=1e-6)
    assert list(df["m"].unique()) == ["rock", "steel"]
    # Idempotent: nothing left to convert.
    assert postprocess.convert_frames(run)["converted"] == 0


def test_postprocess_dataset_run(tmp_path):
    run = _run_dir(tmp_path, "dataset")
    validation = postprocess.postprocess_run(run)
    assert (run / "analysis" / "radial_fraction.parquet").exists()
    assert (run / "analysis" / "lacey.csv").exists()
    prof = pd.read_parquet(run / "analysis" / "radial_fraction.parquet")
    assert set(prof["layer"]) == {"all", "centre", "near_wall"}
    for key in ("V2", "V3", "V4", "V5", "V6", "V14"):
        assert validation[key]["status"] == "pass", key
    assert validation["V8"]["status"] == "n/a"
    assert validation["V19"]["status"] == "reported"
    manifest = json.loads((run / "manifest.json").read_text())
    assert manifest["validation"]["V6"]["value"]["constant_counts"]
    assert json.loads((run / "validation.json").read_text()) == manifest["validation"]


@pytest.mark.parametrize("ic_dir", [None, "x"])
def test_postprocess_calibrate_run_charge_shape(tmp_path, ic_dir):
    run = _run_dir(tmp_path, "calibrate", ic_dir=ic_dir)
    validation = postprocess.postprocess_run(run)
    shape = json.loads((run / "analysis" / "charge_shape.json").read_text())
    assert shape["bulk"]["toe_deg"] == pytest.approx(214.0, abs=2.0)
    assert shape["bulk"]["shoulder_deg"] == pytest.approx(27.0, abs=2.0)
    assert shape["liner_force"]["toe_deg"] == pytest.approx(220.0, abs=3.0)
    assert validation["V7"]["status"] == "pass"
    assert validation["V8"]["status"] == "reported"


def test_validation_flags_failures(tmp_path):
    run = _run_dir(tmp_path, "dataset", n_frames=4)
    manifest = json.loads((run / "manifest.json").read_text())
    manifest["stages"]["record"]["checks"]["damping"] = 0.2
    manifest["stages"]["record"]["checks"]["escaped"] = 3
    v = postprocess.validation_summary(manifest, run, {})
    assert v["V5"]["status"] == "fail" and v["V14"]["status"] == "fail"


def test_default_run_dir_and_dem_post_without_manifest(tmp_path):
    d = launcher.default_run_dir(SMOKE, seed=3)
    assert d.name == "smoke_test_s3" and d.parent.name == "yade_runs"
    assert cli.main(["dem-post", str(tmp_path)]) == 1
    # Extending a record stage needs the run directory to extend.
    assert cli.main(["dem-sim", "--extend-record", "25"]) == 1

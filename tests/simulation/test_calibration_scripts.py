"""Tests for scripts/calibration (grid scenarios and summary), no YADE needed."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from pm_dem_sm.simulation.scenario import load_scenario

# --- Setup -------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts" / "calibration"


# --- Helpers -----------------------------------------------------------------


def _module(name):
    """Import a script of scripts/calibration as a module."""
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- Tests -------------------------------------------------------------------


def test_make_grid_scenarios_matches_the_packaged_grid(tmp_path):
    grid = _module("make_grid_scenarios")
    out = tmp_path / "grid"
    # The grid was written when the base had mu_r 0.13 (before the calibrated defaults).
    grid.main(
        ["--out-dir", str(out), "--rolling-resistance", "0.13", "--rock-count", "16082"]
    )
    made = sorted(p.name for p in out.glob("*.json"))
    packaged = sorted(
        p.name for p in (REPO_ROOT / "configs/simulation/calibration").glob("*.json")
    )
    assert made == packaged
    for name in made:
        assert json.loads((out / name).read_text()) == json.loads(
            (REPO_ROOT / "configs/simulation/calibration" / name).read_text()
        )


def test_grid_scenario_changes_only_run_friction_record():
    grid = _module("make_grid_scenarios")
    base = json.loads((REPO_ROOT / grid.BASE).read_text())
    data = grid.grid_scenario(base, 0.7, 0.9, "data/raw/yade_runs/ic", 3.0)
    assert data["name"] == "cal_mup0p7_muw0p9"
    assert data["contact"]["particle_friction"] == 0.7
    assert data["contact"]["wall_friction"] == 0.9
    assert data["record"]["duration_s"] == pytest.approx(3 * 60 / 9.5, abs=1e-3)
    for key in ("mill", "species", "solver", "fill"):
        assert data[key] == base[key]
    assert base["run"]["type"] == "make_ic"  # base not modified


def test_grid_summary_ranks_points(tmp_path):
    summary = _module("grid_summary")
    scen = load_scenario(REPO_ROOT / "configs/simulation/calibration/cal_mup0p5_muw0p5.json")
    for name, toe, shoulder in (("cal_a", 214.0, 26.5), ("cal_b", 230.0, 20.0)):
        run = tmp_path / name
        (run / "analysis").mkdir(parents=True)
        (run / "manifest.json").write_text(
            json.dumps(
                {
                    "scenario": scen.to_dict(),
                    "stages": {"spinup": {"revolutions": 3.0, "steady_state": {"steady": True}}},
                }
            )
        )
        (run / "analysis" / "charge_shape.json").write_text(
            json.dumps(
                {
                    "bulk": {"toe_deg": toe, "shoulder_deg": shoulder},
                    "liner_force": {"toe_deg": toe + 5, "shoulder_deg": shoulder - 5},
                }
            )
        )
        (run / "validation.json").write_text(json.dumps({"V4": {"status": "pass"}}))
    rows = [summary.point(tmp_path / n) for n in ("cal_b", "cal_a")]
    assert rows[1]["toe_in"] and rows[1]["shoulder_in"] and not rows[0]["toe_in"]
    assert rows[1]["distance_deg"] < rows[0]["distance_deg"]
    assert rows[0]["status"] == "done" and rows[0]["failed"] == "-"
    assert summary.point(tmp_path / "missing") is None


def test_final_scenario_changes_only_mu_r_and_pours_its_own_bed(tmp_path, monkeypatch):
    final = _module("make_final_scenario")
    monkeypatch.setattr(final, "OUT_DIR", tmp_path)
    final.main(["--mu-r", "0.17", "--tag", "r17270"])
    s = load_scenario(tmp_path / "cal_final_mup0p3_muw0p5_mur0p17_r17270.json")
    assert s.run.type == "calibrate" and s.run.ic_dir is None
    assert s.stages == ("build", "fill", "settle", "spinup", "record")
    best = load_scenario(REPO_ROOT / "configs/simulation/calibration/cal_mup0p3_muw0p5.json")
    assert (s.contact.particle_friction, s.contact.wall_friction) == (0.3, 0.5)
    assert s.contact.rolling_resistance == 0.17
    assert s.record.duration_s == best.record.duration_s
    assert s.mill == best.mill
    # Counts from the base (rechecked 2026-11-09); the grid ran with 16082 rocks.
    assert {sp.material: sp.count for sp in s.species} == {"rock": 17270, "steel": 3437}
    assert {sp.material: sp.count for sp in best.species} == {"rock": 16082, "steel": 3437}


def test_final_point_summary_v12_and_v15():
    summary = _module("final_point_summary")
    rows = [
        {"toe_deg": 240.0, "shoulder_deg": 36.0, "power_slice_kW": 1100.0, "depth_m": 0.6},
        {"toe_deg": 242.0, "shoulder_deg": 38.0, "power_slice_kW": 1120.0, "depth_m": 0.6},
    ]
    res = summary.summary(rows)
    assert res["toe_deg"]["mean"] == pytest.approx(241.0)
    assert res["toe_deg"]["sd"] == pytest.approx(2**0.5)
    v15 = res["V15"]
    # Topic 15: 0.95 x (1 - 0.08) x 12,627 kW = 11,036 kW; length factor 5.244 / 0.6.
    assert v15["P_charge_plant_kW"] == pytest.approx(11036, abs=1)
    assert v15["length_factor"] == pytest.approx(8.74, abs=0.001)
    low = v15["cases"][0]
    assert low["c_cone"] == 0.05
    assert low["P_mill_kW"] == pytest.approx(1110 * 8.74 * 1.05, rel=1e-3)

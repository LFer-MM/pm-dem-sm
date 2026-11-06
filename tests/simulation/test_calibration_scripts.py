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
    grid.main(["--out-dir", str(out)])
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

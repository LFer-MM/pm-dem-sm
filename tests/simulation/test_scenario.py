"""Tests for the backend-agnostic DEM scenario (no YADE needed)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from pm_dem_sm.simulation.scenario import SimulationScenario, load_scenario

# --- Setup -------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_FILES = sorted((REPO_ROOT / "configs" / "simulation").glob("*.json"))


# --- Tests -------------------------------------------------------------------


def test_defaults_round_trip_through_dict():
    s = SimulationScenario()
    assert SimulationScenario.from_dict(s.to_dict()).to_dict() == s.to_dict()


def test_to_dict_is_json_serializable():
    json.dumps(SimulationScenario().to_dict())


@pytest.mark.parametrize("path", SCENARIO_FILES, ids=lambda p: p.name)
def test_packaged_scenarios_load(path):
    s = load_scenario(path)
    assert s.name == path.stem


def test_partial_json_keeps_other_defaults(tmp_path):
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"mill": {"speed_rpm": 7.5}}), encoding="utf-8")
    s = load_scenario(path)
    assert s.mill.speed_rpm == 7.5
    assert s.mill.depth_m == SimulationScenario().mill.depth_m


def test_unknown_key_raises():
    with pytest.raises(ValueError, match="Unknown"):
        SimulationScenario.from_dict({"mill": {"not_a_field": 1}})


def test_bad_choice_raises():
    with pytest.raises(ValueError, match="mill.source"):
        SimulationScenario.from_dict({"mill": {"source": "cad"}})


def test_species_material_must_exist():
    data = SimulationScenario().to_dict()
    data["species"][0]["material"] = "granite"
    with pytest.raises(ValueError, match="granite"):
        SimulationScenario.from_dict(data)


def test_overlapping_lifters_raise():
    with pytest.raises(ValueError, match="Lifters overlap"):
        SimulationScenario.from_dict(
            {"mill": {"source": "parametric", "diameter_m": 1.0, "n_lifters": 40,
                      "lifter_base_width_m": 0.2}}
        )


def test_small_and_large_species():
    s = SimulationScenario()
    assert s.small.radius_m < s.large.radius_m


def test_restitution_lookup_is_order_independent():
    s = SimulationScenario()
    assert s.restitution_for("rock", "steel") == s.restitution_for("steel", "rock")


def test_critical_speed_matches_classic_formula():
    s = SimulationScenario.from_dict({"mill": {"diameter_m": 11.9}})
    d_large = 2 * s.large.radius_m
    assert s.critical_speed_rpm() == pytest.approx(42.3 / math.sqrt(11.9 - d_large), rel=1e-3)


def test_rayleigh_dt_scales_with_young():
    stiff = SimulationScenario.from_dict({"solver": {"young_scale": 1.0}})
    soft = SimulationScenario.from_dict({"solver": {"young_scale": 0.01}})
    assert soft.rayleigh_dt_s() == pytest.approx(10 * stiff.rayleigh_dt_s())


def test_defaults_match_decisions():
    s = SimulationScenario()
    assert s.solver.dt_s == 2.5e-5
    assert s.solver.young_scale == pytest.approx(1 / 26)
    assert s.mill.diameter_m == 10.7128
    assert s.mill.depth_m == 0.6
    assert s.mill.speed_rpm == 9.5
    assert s.mill.end_walls == "frictionless"
    assert s.contact.model == "hertz_mindlin"
    assert {sp.name: sp.count for sp in s.species} == {"rock": 14650, "ball": 3750}
    assert s.materials["steel"]["young"] == 207e9
    assert s.materials["rock"]["young"] == 55e9
    assert s.materials["rock"]["density"] == 2850
    assert s.materials["steel"]["friction_angle"] == s.materials["rock"]["friction_angle"]
    assert math.tan(s.materials["rock"]["friction_angle"]) == pytest.approx(0.5)


def test_damping_is_not_an_option():
    with pytest.raises(ValueError, match="Unknown"):
        SimulationScenario.from_dict({"fill": {"damping": 0.2}})
    with pytest.raises(ValueError, match="Unknown"):
        SimulationScenario.from_dict({"settle": {"damping": 0.2}})


def test_cundall_strack_is_rejected():
    with pytest.raises(ValueError, match="contact.model"):
        SimulationScenario.from_dict({"contact": {"model": "cundall_strack"}})


def test_impact_speed_is_free_fall_across_the_mill():
    assert SimulationScenario().impact_speed_m_s() == pytest.approx(14.5, abs=0.01)


@pytest.mark.parametrize(
    ("pair", "steps"),
    [("rock-rock", 20.9), ("rock-ball", 21.3), ("ball-ball", 36.6)],
)
def test_steps_per_collision_reproduce_time_step_table(pair, steps):
    # docs/scientific_rationale/02_time_step.md, steps @ 2.5e-5 at 14.5 m/s.
    assert SimulationScenario().steps_per_collision()[pair] == pytest.approx(steps, abs=0.05)


def test_contact_time_matches_time_step_table():
    s = SimulationScenario()
    rock = s.small
    assert s.contact_time_s(rock, rock, 14.5) == pytest.approx(5.23e-4, rel=2e-3)


def test_default_dt_gives_no_steps_warning():
    s = SimulationScenario()
    assert s.checks()["min_steps_per_collision"] >= 20
    assert not any("steps" in w for w in s.warnings())


def test_dt_1e4_is_flagged():
    s = SimulationScenario.from_dict({"solver": {"dt_s": 1e-4}})
    assert s.checks()["min_steps_per_collision"] < 20
    flagged = [w for w in s.warnings() if "steps" in w]
    assert len(flagged) == 3


def test_fill_fraction_counts_both_species():
    s = SimulationScenario()
    solids = sum(sp.volume_m3 for sp in s.species)
    mill = math.pi * (s.mill.diameter_m / 2) ** 2 * s.mill.depth_m
    assert s.fill_fraction(packing=1.0) == pytest.approx(solids / mill)

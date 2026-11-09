"""Tests for the backend-agnostic DEM scenario (no YADE needed)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from pm_dem_sm.simulation.scenario import RUN_TYPE_STAGES, SimulationScenario, load_scenario

# --- Setup -------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_FILES = sorted((REPO_ROOT / "configs" / "simulation").glob("**/*.json"))
# Any value: mu_r is a required input with no sourced default yet.
MU_R = 0.25


# --- Helpers -----------------------------------------------------------------


def _from(data):
    """Build a validated scenario from ``data``, adding ``MU_R`` unless set."""
    data = json.loads(json.dumps(data))
    data.setdefault("contact", {}).setdefault("rolling_resistance", MU_R)
    return SimulationScenario.from_dict(data)


def _valid():
    """Return the default scenario with ``MU_R`` set."""
    return _from({})


# --- Tests -------------------------------------------------------------------


def test_defaults_round_trip_through_dict():
    s = _valid()
    assert SimulationScenario.from_dict(s.to_dict()).to_dict() == s.to_dict()


def test_rolling_resistance_default_and_validation():
    # Default from the heap test (C06-3); null is rejected.
    assert SimulationScenario.from_dict({}).contact.rolling_resistance == 0.16
    with pytest.raises(ValueError, match="rolling_resistance"):
        SimulationScenario.from_dict({"contact": {"rolling_resistance": None}})
    with pytest.raises(ValueError, match=">= 0"):
        _from({"contact": {"rolling_resistance": -0.1}})


def test_to_dict_is_json_serializable():
    json.dumps(SimulationScenario().to_dict())


@pytest.mark.parametrize("path", SCENARIO_FILES, ids=lambda p: p.name)
def test_packaged_scenarios_load(path):
    s = load_scenario(path)
    assert s.name == path.stem


def test_partial_json_keeps_other_defaults(tmp_path):
    path = tmp_path / "s.json"
    path.write_text(
        json.dumps({"mill": {"speed_rpm": 7.5}, "contact": {"rolling_resistance": MU_R}}),
        encoding="utf-8",
    )
    s = load_scenario(path)
    assert s.mill.speed_rpm == 7.5
    assert s.mill.depth_m == SimulationScenario().mill.depth_m


def test_unknown_key_raises():
    with pytest.raises(ValueError, match="Unknown"):
        SimulationScenario.from_dict({"mill": {"not_a_field": 1}})


def test_bad_choice_raises():
    with pytest.raises(ValueError, match="mill.end_walls"):
        SimulationScenario.from_dict({"mill": {"end_walls": "cad"}})


@pytest.mark.parametrize("key", ["source", "stl_path", "diameter_m", "n_shell_segments"])
def test_retired_mill_keys_raise(key):
    # The STL input is retired and the diameter inside liners is derived.
    with pytest.raises(ValueError, match="Unknown"):
        _from({"mill": {key: 1}})


def test_species_material_must_exist():
    data = SimulationScenario().to_dict()
    data["species"][0]["material"] = "granite"
    with pytest.raises(ValueError, match="granite"):
        SimulationScenario.from_dict(data)


def test_overlapping_lifters_raise():
    with pytest.raises(ValueError, match="Lifters overlap"):
        _from({"mill": {"n_lifters": 80}})


@pytest.mark.parametrize(
    ("mill", "match"),
    [
        ({"n_lifters": 0}, "n_lifters"),
        ({"plate_segments": 0}, "plate_segments"),
        ({"lifter_face_angle_deg": 90.0}, "face_angle"),
        ({"plate_thickness_m": 0.4}, "plate_thickness_m"),
        ({"lifter_face_angle_deg": 50.0}, "top width"),
    ],
)
def test_invalid_liner_raises(mill, match):
    with pytest.raises(ValueError, match=match):
        _from({"mill": mill})


def test_mill_derived_values():
    m = _valid().mill
    assert m.diameter_m == pytest.approx(10.9728 - 2 * 0.130)
    assert m.lifter_top_radius_m == pytest.approx(10.9728 / 2 - 0.395)
    assert m.lifter_top_width_m == pytest.approx(
        0.523 - 2 * 0.265 * math.tan(math.radians(35.0))
    )


def test_small_and_large_species():
    s = SimulationScenario()
    assert s.small.radius_m < s.large.radius_m


def test_restitution_lookup_is_order_independent():
    s = SimulationScenario()
    assert s.restitution_for("rock", "steel") == s.restitution_for("steel", "rock")


def test_critical_speed_matches_classic_formula():
    s = _from({"mill": {"shell_diameter_m": 11.9 + 2 * 0.130}})
    d_large = 2 * s.large.radius_m
    assert s.critical_speed_rpm() == pytest.approx(42.3 / math.sqrt(11.9 - d_large), rel=1e-3)


def test_rayleigh_dt_scales_with_young():
    stiff = _from({"solver": {"young_scale": 1.0}})
    soft = _from({"solver": {"young_scale": 0.01}})
    assert soft.rayleigh_dt_s() == pytest.approx(10 * stiff.rayleigh_dt_s())


def test_defaults_match_decisions():
    s = SimulationScenario()
    assert s.solver.dt_s == 2.5e-5
    assert s.solver.young_scale == pytest.approx(1 / 26)
    assert s.mill.diameter_m == pytest.approx(10.7128)
    assert s.mill.depth_m == 0.6
    assert s.mill.speed_rpm == 9.5
    assert s.mill.end_walls == "frictionless"
    assert s.contact.model == "hertz_mindlin"
    assert {sp.name: sp.count for sp in s.species} == {"rock": 16082, "ball": 3437}
    assert s.materials["steel"]["young"] == 207e9
    assert s.materials["rock"]["young"] == 55e9
    assert s.materials["rock"]["density"] == 2850
    assert s.contact.particle_friction == 0.3
    assert s.contact.wall_friction == 0.5
    assert s.contact.particle_friction_set == "uniform"
    assert s.contact.rolling_resistance == 0.16
    assert s.mill.liner_material == "liner"
    liner, steel = s.materials["liner"], s.materials["steel"]
    assert {k: liner[k] for k in ("density", "young", "poisson")} == {
        k: steel[k] for k in ("density", "young", "poisson")
    }
    assert s.restitution_for("liner", "steel") == 0.8
    assert s.restitution_for("liner", "rock") == 0.5


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
    s = _from({"solver": {"dt_s": 1e-4}})
    assert s.checks()["min_steps_per_collision"] < 20
    flagged = [w for w in s.warnings() if "steps" in w]
    assert len(flagged) == 3


def test_fill_fraction_counts_both_species():
    s = SimulationScenario()
    solids = sum(sp.volume_m3 for sp in s.species)
    mill = math.pi * (s.mill.diameter_m / 2) ** 2 * s.mill.depth_m
    assert s.fill_fraction(packing=1.0) == pytest.approx(solids / mill)


def test_contact_tables_cover_every_pair_once():
    t = _valid().contact_tables()
    walls = ["liner", "end_wall"]
    expected = {frozenset(p) for p in [("rock", "rock"), ("rock", "steel"), ("steel", "steel")]}
    expected |= {frozenset((p, w)) for p in ("rock", "steel") for w in walls}
    for key in ("restitution", "friction"):
        pairs = [frozenset((a, b)) for a, b, _ in t[key]]
        assert len(pairs) == len(set(pairs))
        assert set(pairs) == expected
    assert t["cap_material"] == "end_wall"
    assert set(t["materials"]) == {"steel", "rock", "liner", "end_wall"}


def test_contact_table_values():
    s = _from({"contact": {"particle_friction": 0.3, "wall_friction": 0.7}})
    t = s.contact_tables()
    mu = {frozenset((a, b)): math.tan(v) for a, b, v in t["friction"]}
    e = {frozenset((a, b)): v for a, b, v in t["restitution"]}
    for pair in [("rock", "rock"), ("rock", "steel"), ("steel", "steel")]:
        assert mu[frozenset(pair)] == pytest.approx(0.3)
    for p in ("rock", "steel"):
        assert mu[frozenset((p, "liner"))] == pytest.approx(0.7)
        assert mu[frozenset((p, "end_wall"))] == 0.0
        assert e[frozenset((p, "end_wall"))] == e[frozenset((p, "liner"))]
    assert e[frozenset(("steel", "liner"))] == 0.8
    assert e[frozenset(("rock", "liner"))] == 0.5
    assert math.tan(t["materials"]["liner"]["friction_angle"]) == pytest.approx(0.7)
    assert t["materials"]["end_wall"]["friction_angle"] == 0.0
    assert t["materials"]["end_wall"]["young"] == t["materials"]["liner"]["young"]


def test_friction_lookup_is_order_independent():
    s = _valid()
    for a, b in [("rock", "steel"), ("rock", "liner"), ("steel", "end_wall")]:
        assert s.friction_for(a, b) == s.friction_for(b, a)
    with pytest.raises(KeyError):
        s.friction_for("liner", "liner")


def test_owen_friction_set():
    s = _from({"contact": {"particle_friction_set": "owen", "wall_friction": 0.6}})
    mu = {frozenset((a, b)): math.tan(v) for a, b, v in s.contact_tables()["friction"]}
    assert mu[frozenset(("steel", "steel"))] == pytest.approx(0.4)
    assert mu[frozenset(("rock", "steel"))] == pytest.approx(0.5)
    assert mu[frozenset(("rock", "rock"))] == pytest.approx(0.8)
    assert mu[frozenset(("rock", "liner"))] == pytest.approx(0.6)


def test_liner_end_walls_use_liner_material():
    t = _from({"mill": {"end_walls": "liner"}}).contact_tables()
    assert t["cap_material"] == "liner"
    assert "end_wall" not in t["materials"]


def test_liner_must_be_its_own_material():
    with pytest.raises(ValueError, match="liner_material"):
        _from({"mill": {"liner_material": "steel"}})


def test_per_material_friction_angle_is_rejected():
    data = _valid().to_dict()
    data["materials"]["rock"]["friction_angle"] = 0.5
    with pytest.raises(ValueError, match="friction_angle"):
        SimulationScenario.from_dict(data)


def test_restitution_needs_liner_pairs():
    data = _valid().to_dict()
    data["restitution"] = [p for p in data["restitution"] if "liner" not in p[:2]]
    with pytest.raises(ValueError, match="liner"):
        SimulationScenario.from_dict(data)


def test_rolling_stiffness_hand_computed():
    # Smallest rock: r = 0.034925 m, 2850 kg/m^3; T_r = 20 x 2.5e-5 s.
    s = _valid()
    mass = 2850 * 4 / 3 * math.pi * 0.034925**3
    inertia = 0.4 * mass * 0.034925**2
    krot = inertia * (2 * math.pi / (20 * 2.5e-5)) ** 2
    assert s.rolling_stiffness() == pytest.approx(krot)
    assert s.rolling_stiffness() == pytest.approx(39182.8, rel=1e-4)
    assert s.rolling_period_steps(s.rolling_stiffness()) == pytest.approx(20.0)
    # theta_y = mu_r R F / krot.
    assert s.yield_rotation_rad(krot, force_n=1000.0) == pytest.approx(
        MU_R * 0.034925 * 1000.0 / krot
    )


def test_default_rolling_stiffness_passes_both_criteria():
    s = _valid()
    krot = s.rolling_stiffness()
    s.check_rolling_stiffness(krot)
    c = s.checks()
    assert c["rolling_stiffness"] == pytest.approx(krot)
    assert 1e-5 < c["yield_rotation_rad"] < 0.01
    assert 100 < c["typical_contact_force_n"] < 5000


def test_rolling_stiffness_check_raises():
    s = _valid()
    krot = s.rolling_stiffness()
    with pytest.raises(ValueError, match="rolling period"):
        s.check_rolling_stiffness(1.1 * krot)
    with pytest.raises(ValueError, match="plastic rolling moment"):
        _from({"contact": {"rolling_resistance": 1000.0}}).check_rolling_stiffness(krot)


def test_rolling_stiffness_follows_dt():
    fine = _from({"solver": {"dt_s": 1.25e-5}})
    assert fine.rolling_stiffness() == pytest.approx(4 * _valid().rolling_stiffness())


def test_provisional_parameters_record_mu_r():
    p = _valid().provisional_parameters()
    assert p["contact.rolling_resistance"]["value"] == MU_R
    assert "C06-3" in p["contact.rolling_resistance"]["note"]


@pytest.mark.parametrize("path", SCENARIO_FILES, ids=lambda p: p.name)
def test_packaged_scenarios_pass_rolling_checks(path):
    s = load_scenario(path)
    s.check_rolling_stiffness(s.rolling_stiffness())
    assert s.contact.rolling_resistance is not None


def test_run_type_stages():
    assert _valid().stages == ("build", "fill", "settle", "spinup", "record")
    assert _from({"run": {"type": "make_ic"}}).stages == ("build", "fill", "settle", "save_ic")
    ds = _from({"run": {"type": "dataset", "ic_dir": "data/raw/yade_runs/x_s{seed}"}})
    assert ds.stages == ("load_ic", "record")


def test_dataset_needs_ic_dir_and_known_type():
    with pytest.raises(ValueError, match="ic_dir"):
        _from({"run": {"type": "dataset"}})
    with pytest.raises(ValueError, match="run.type"):
        _from({"run": {"type": "spin"}})


def test_material_set_id():
    base = _valid().material_set_id()
    assert len(base) == 12
    # Same materials and charge: same id, whatever the run type or duration.
    assert _from({"run": {"type": "make_ic"}, "record": {"duration_s": 35.0}}).material_set_id() \
        == base
    # Anything an IC depends on changes it.
    assert _from({"contact": {"rolling_resistance": 0.2}}).material_set_id() != base
    assert _from({"solver": {"young_scale": 0.02}}).material_set_id() != base
    assert _from({"mill": {"n_lifters": 30}}).material_set_id() != base
    data = _valid().to_dict()
    data["species"][0]["count"] += 1
    assert SimulationScenario.from_dict(data).material_set_id() != base


def test_sag_a_dataset_scenarios_pair_with_make_ic():
    root = REPO_ROOT / "configs" / "simulation"
    for kind, seconds in (("rmic", 20.0), ("sic", 35.0)):
        ic = load_scenario(root / f"sag_a_make_ic_{kind}.json")
        ds = load_scenario(root / f"sag_a_dataset_{kind}.json")
        assert ic.run.type == "make_ic" and ds.run.type == "dataset"
        assert ds.record.duration_s == seconds
        assert ic.material_set_id() == ds.material_set_id()
        assert str(ds.run.ic_dir).endswith(f"sag_a_make_ic_{kind}_s{{seed}}")
    assert load_scenario(root / "sag_a_make_ic_sic.json").fill.method == "segregated"


def test_existing_material_set_ids_unchanged():
    # Pinned so a change of any material, contact value or species shows up here.
    # Calibrated defaults (2026-11-08, mu_p 0.3, mu_r 0.16); before them the ICs of
    # phase 5 and the pilot carried d66a6a9c9eb0 / cb4108570cb2.
    root = REPO_ROOT / "configs" / "simulation"
    assert load_scenario(root / "smoke_make_ic.json").material_set_id() == "7bd48fa37a4d"
    assert load_scenario(root / "sag_a_make_ic_rmic.json").material_set_id() == "34a6b28719ad"


def test_material_set_id_ignore_friction():
    base = _valid()
    other = _from({"contact": {"particle_friction": 0.3, "wall_friction": 0.7}})
    assert base.material_set_id() != other.material_set_id()
    assert base.material_set_id(ignore_friction=True) == other.material_set_id(
        ignore_friction=True
    )
    # Everything else still counts.
    assert _from({"contact": {"rolling_resistance": 0.2}}).material_set_id(
        ignore_friction=True
    ) != base.material_set_id(ignore_friction=True)


def test_calibrate_from_a_shared_ic():
    s = _from({"run": {"type": "calibrate", "ic_dir": "data/raw/yade_runs/x"}})
    assert s.stages == ("load_ic", "spinup", "record")
    # Without ic_dir a calibrate run pours its own bed, as before.
    assert _from({"run": {"type": "calibrate"}}).stages == (
        "build", "fill", "settle", "spinup", "record"
    )
    assert set(RUN_TYPE_STAGES) == {"calibrate", "make_ic", "dataset"}


def test_preview_interval():
    assert _valid().record.preview_interval_s == 0.5
    assert _from({"record": {"preview_interval_s": 0}}).record.preview_interval_s == 0
    with pytest.raises(ValueError, match="preview_interval_s"):
        _from({"record": {"preview_interval_s": -1}})


def test_calibration_grid_scenarios_share_the_pilot_ic():
    root = REPO_ROOT / "configs" / "simulation"
    # The pilot's IC was made from sag_a_make_ic_rmic.json before the calibrated
    # defaults: mu_p 0.5, mu_r 0.13.
    ic = SimulationScenario.from_dict(
        {
            **load_scenario(root / "sag_a_make_ic_rmic.json").to_dict(),
            "contact": {"rolling_resistance": 0.13, "particle_friction": 0.5},
        }
    )
    grid = sorted((root / "calibration").glob("cal_*.json"))
    assert len(grid) == 9
    pairs = set()
    for path in grid:
        s = load_scenario(path)
        assert s.run.type == "calibrate"
        assert s.stages == ("load_ic", "spinup", "record")
        assert str(s.run.ic_dir) == "data/raw/yade_runs/sag_a_make_ic_rmic_s0"
        assert s.material_set_id(ignore_friction=True) == ic.material_set_id(ignore_friction=True)
        assert s.record.duration_s == pytest.approx(2 * s.revolution_s(), abs=1e-3)
        pairs.add((s.contact.particle_friction, s.contact.wall_friction))
    assert pairs == {(p, w) for p in (0.3, 0.5, 0.7) for w in (0.3, 0.5, 0.7)}

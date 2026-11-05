"""Tests for the backend-agnostic run checks and measurements (no YADE needed)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from pm_dem_sm.simulation import checks
from pm_dem_sm.simulation import mill_geometry as geom
from pm_dem_sm.simulation.scenario import MillGeometry

# --- Setup -------------------------------------------------------------------

D_SMALL = 0.06985


# --- Helpers -----------------------------------------------------------------


def _rows(n, dt, angle, height, speed):
    """Return ``n`` settle-log rows sampled every ``dt`` from the given functions of time."""
    return [
        {"time": k * dt, "angle_all_deg": angle(k * dt), "com_height_m": height(k * dt),
         "mean_speed_m_s": speed(k * dt)}
        for k in range(n)
    ]


def _segment_fraction(R, h_surface):
    """Return the fraction of a circle of radius ``R`` below the horizontal line ``y = h_surface``."""
    c = -h_surface  # distance from the centre to the chord, below the centre
    area_below = R * R * math.acos(c / R) - c * math.sqrt(R * R - c * c)
    return area_below / (math.pi * R * R)


def _flat_bed(R, y_top, r, depth=0.6):
    """Return spheres of radius ``r`` in a square packing inside a circle, tops at ``y_top``."""
    out = []
    y = -R + r
    while y + r <= y_top + 1e-9:
        x = -R + r
        while x <= R - r:
            if math.hypot(x, y) <= R - r:
                out.append((x, y, depth / 2, r))
            x += 2 * r
        y += 2 * r
    # Make sure the top row reaches y_top exactly.
    top = max(s[1] for s in out) + r
    return [(x, y + (y_top - top), z, rr) for x, y, z, rr in out]


# --- Tests -------------------------------------------------------------------


def test_settle_stop_stationary():
    rows = _rows(41, 0.05, lambda t: 30.0 + 0.1 * math.sin(t), lambda t: -3.0,
                 lambda t: 0.005)
    r = checks.settle_stop(rows, D_SMALL, t_start=0.0, max_time_s=20.0)
    assert r["stop"] and r["reason"] == "stationary"
    assert r["angle_change_deg"] < 0.5


def test_settle_stop_needs_a_full_window():
    rows = _rows(10, 0.05, lambda t: 30.0, lambda t: -3.0, lambda t: 0.0)
    assert checks.settle_stop(rows, D_SMALL, 0.0, 20.0)["stop"] is False


@pytest.mark.parametrize(
    ("angle", "height", "speed"),
    [
        (lambda t: 30.0 + t, lambda t: -3.0, lambda t: 0.005),  # angle drifts 1 deg/s
        (lambda t: 30.0, lambda t: -3.0 + 0.001 * t, lambda t: 0.005),  # 1 mm > 0.7 mm
        (lambda t: 30.0, lambda t: -3.0, lambda t: 0.02),  # too fast
    ],
)
def test_settle_stop_each_criterion_blocks(angle, height, speed):
    rows = _rows(41, 0.05, angle, height, speed)
    assert checks.settle_stop(rows, D_SMALL, 0.0, 20.0)["stop"] is False


def test_settle_stop_time_cap():
    rows = _rows(201, 0.05, lambda t: 30.0 + t, lambda t: -3.0, lambda t: 0.1)
    r = checks.settle_stop(rows, D_SMALL, t_start=0.0, max_time_s=10.0)
    assert r["stop"] and r["reason"] == "time_cap"


def test_settle_stop_ignores_rows_before_the_stage():
    early = _rows(40, 0.05, lambda t: 30.0 + 50 * t, lambda t: -3.0, lambda t: 0.005)
    late = [dict(r, time=r["time"] + 2.0, angle_all_deg=31.0) for r in early]
    late.append(dict(late[-1], time=late[-1]["time"] + 0.05))
    r = checks.settle_stop(early + late, D_SMALL, t_start=2.0, max_time_s=20.0)
    assert r["stop"] and r["reason"] == "stationary"


def test_pair_types():
    assert checks.pair_type(0.03, 0.03, 0.05) == "small-small"
    assert checks.pair_type(0.07, 0.03, 0.05) == "small-large"
    assert checks.pair_type(0.07, 0.07, 0.05) == "large-large"
    assert checks.pair_type(None, 0.03, 0.05) == "small-wall"
    assert checks.pair_type(0.07, None, 0.05) == "large-wall"


def test_overlap_stats():
    samples = [("small-small", v) for v in np.linspace(0.0, 0.01, 101)]
    samples += [("large-wall", 0.02)]
    s = checks.overlap_stats(samples)
    assert s["small-small"]["n"] == 101
    assert s["small-small"]["mean"] == pytest.approx(0.005)
    assert s["small-small"]["max"] == pytest.approx(0.01)
    assert s["small-small"]["p99"] == pytest.approx(0.0099)
    assert s["all"]["max"] == 0.02 and s["all"]["n"] == 102


def test_energy_balance_closes():
    # Constant 1 kW drive for 2 s; 1500 J dissipated, mechanical energy +500 J.
    rows = [
        {"time": t, "power_kW": 1.0, "kinetic_J": 100 + 250 * t, "potential_J": 0.0,
         "elastic_J": 0.0, "dissipated_J": 750 * t}
        for t in (0.0, 0.5, 1.0, 1.5, 2.0)
    ]
    b = checks.energy_balance(rows)
    assert b["drive_work_J"] == pytest.approx(2000.0)
    assert b["dissipated_J"] == pytest.approx(1500.0)
    assert b["delta_mechanical_J"] == pytest.approx(500.0)
    assert b["residual_J"] == pytest.approx(0.0, abs=1e-9)


def test_energy_balance_without_drive():
    rows = [
        {"time": 0.0, "power_kW": 0.0, "kinetic_J": 10.0, "potential_J": 0.0,
         "elastic_J": 0.0, "dissipated_J": 0.0},
        {"time": 1.0, "power_kW": 0.0, "kinetic_J": 0.0, "potential_J": -5.0,
         "elastic_J": 0.1, "dissipated_J": 14.0},
    ]
    b = checks.energy_balance(rows)
    assert b["residual_J"] == pytest.approx(0.9)
    assert b["residual_rel"] == pytest.approx(0.9 / 14.0)


def test_new_sphere_overlaps():
    old = [(0.0, 0.0, 0.0, 0.05)]
    assert checks.new_sphere_overlaps([(0.2, 0.0, 0.0, 0.05)], old) == (0, 0.0)
    n, depth = checks.new_sphere_overlaps([(0.09, 0.0, 0.0, 0.05)], old)
    assert n == 1 and depth == pytest.approx(0.01)
    # Two new spheres overlapping each other count once.
    n, _ = checks.new_sphere_overlaps([(1.0, 0, 0, 0.05), (1.05, 0, 0, 0.05)], old)
    assert n == 1


def test_point_triangle_distance():
    a, b, c = (0, 0, 0), (1, 0, 0), (0, 1, 0)
    assert checks.point_triangle_distance((0.2, 0.2, 0.5), a, b, c) == pytest.approx(0.5)
    assert checks.point_triangle_distance((-1, 0, 0), a, b, c) == pytest.approx(1.0)
    assert checks.point_triangle_distance((1, 1, 0), a, b, c) == pytest.approx(math.sqrt(0.5))
    assert checks.point_triangle_distance((0.5, -2, 0), a, b, c) == pytest.approx(2.0)


def test_sphere_wall_overlaps():
    mill = MillGeometry(depth_m=0.6)
    tris = geom.liner_triangles(mill)
    r_top = mill.lifter_top_radius_m
    inside = [(0.0, -2.0, 0.3, 0.07)]
    assert checks.sphere_wall_overlaps(inside, tris, 0.6, r_top) == (0, 0.0)
    # Pushed 1 cm into the plate surface between two lifters (5 deg off a lifter).
    a = math.radians(-90 + 5)
    r_plate = geom.plate_radius(mill)
    into_plate = [((r_plate - 0.06) * math.cos(a), (r_plate - 0.06) * math.sin(a), 0.3, 0.07)]
    n, depth = checks.sphere_wall_overlaps(into_plate, tris, 0.6, r_top)
    assert n >= 1 and depth == pytest.approx(0.01, abs=2e-3)
    # Through the end wall.
    n, depth = checks.sphere_wall_overlaps([(0.0, -2.0, 0.05, 0.07)], tris, 0.6, r_top)
    assert n == 1 and depth == pytest.approx(0.02)


def test_escaped_spheres():
    s = [(0, 0, 0.3, 0.05), (6.0, 0, 0.3, 0.05), (0, 0, -0.1, 0.05), (0, 0, 0.7, 0.05)]
    assert checks.escaped_spheres(s, shell_radius=5.4864, depth=0.6) == 3


def test_restitution():
    assert checks.restitution(-2.0, 1.0) == pytest.approx(0.5)


def test_repose_angle_of_a_synthetic_cone():
    # Spheres on the surface of a 35 deg cone of radius 1 m, plus a base layer.
    rng = np.random.default_rng(0)
    r = 0.035
    pts = []
    for _ in range(20000):
        rho, phi = 1.0 * math.sqrt(rng.random()), 2 * math.pi * rng.random()
        h = (1.0 - rho) * math.tan(math.radians(35.0))
        pts.append((rho * math.cos(phi), rho * math.sin(phi), h + r * rng.random() - r, r))
    res = checks.repose_angle(pts, base_z=0.0)
    assert res["angle_deg"] == pytest.approx(35.0, abs=1.0)
    assert res["radius_m"] == pytest.approx(1.0, abs=0.15)
    assert res["r2"] > 0.95


def test_boundary_radius_of_circle_and_liner():
    circle = [(2 * math.cos(a), 2 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 3601)[:-1]]
    th = np.linspace(-3, 3, 7)
    assert checks.boundary_radius(th, circle) == pytest.approx(np.full(7, 2.0), abs=1e-6)
    mill = MillGeometry()
    prof = geom.liner_profile(mill)
    # On a lifter centreline (0 deg) the boundary is the lifter top; midway
    # between lifters (5 deg) the plate surface.
    rb = checks.boundary_radius(np.array([0.0, math.radians(5.0)]), prof)
    assert rb[0] == pytest.approx(mill.lifter_top_radius_m, abs=1e-6)
    assert rb[1] == pytest.approx(geom.plate_radius(mill), abs=1e-3)


@pytest.mark.parametrize("y_top", [-3.0, -1.5, 0.0])
def test_fill_level_of_a_flat_bed(y_top):
    R = 5.3564
    beds = _flat_bed(R, y_top, r=0.07)
    res = checks.fill_level(beds, R, depth=0.6, grid=0.02)
    assert res["J"] == pytest.approx(_segment_fraction(R, y_top), abs=0.004)


def test_fill_level_phi_and_lifters():
    mill = MillGeometry()
    R = geom.plate_radius(mill)
    beds = _flat_bed(R, -2.0, r=0.07)
    prof = geom.liner_profile(mill)
    res = checks.fill_level(beds, R, depth=0.6, liner_profile=prof, grid=0.02)
    circle_area = res["J"] * math.pi * R * R
    # The free bulk area is the circle part minus the lifters under the bed:
    # a surface at y = -2 m covers the lifters between about -158 and -22 deg
    # (13-14 of 36), 0.0883 m^2 each.
    lifters = (circle_area - res["free_bulk_area_m2"]) / geom.exposed_lifter_area(mill)
    assert 12.5 < lifters < 14.5
    solids = sum(4 / 3 * math.pi * s[3] ** 3 for s in beds)
    assert res["phi"] == pytest.approx(solids / (res["free_bulk_area_m2"] * 0.6))


def test_count_updates():
    assert checks.fill_converged(0.190, 0.188)
    assert not checks.fill_converged(0.195, 0.188)
    assert checks.next_ball_count(3750, J=0.20, J_target=0.188) == 3525
    # Rock share 0.08 of the bed with 14650 rocks; target share 0.088.
    assert checks.next_rock_count(14650, J=0.268, J_balls=0.188, J_target=0.276) == 16115

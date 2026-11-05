"""Tests for the parametric mill liner geometry (no YADE needed)."""

from __future__ import annotations

import math

import pytest

from pm_dem_sm.simulation import mill_geometry as geom
from pm_dem_sm.simulation.scenario import MillGeometry

# --- Setup -------------------------------------------------------------------

# SAG_A, new liners (docs/scientific_rationale/10_mill_geometry.md).
SAG_A = MillGeometry()
R_SHELL = 10.9728 / 2
R_PLATE = R_SHELL - 0.130
R_TOP = R_SHELL - 0.395
TRAPEZOID = (0.523 + 0.152) / 2 * 0.265  # 0.0894 m^2, flat-base estimate


# --- Helpers -----------------------------------------------------------------


def _lifter_points(mill, k):
    """Return lifter ``k``'s four exposed corners in ``(x, y)`` (CCW)."""
    per_lifter = 4 + mill.plate_segments - 1
    return geom.liner_profile(mill)[k * per_lifter:k * per_lifter + 4]


def _angle(p):
    """Return the polar angle of ``p`` in ``[0, 2 pi)``."""
    return math.atan2(p[1], p[0]) % (2 * math.pi)


# --- Tests -------------------------------------------------------------------


def test_sag_a_defaults():
    assert SAG_A.shell_diameter_m == 10.9728
    assert SAG_A.n_lifters == 36
    assert SAG_A.diameter_m == pytest.approx(10.7128)
    assert SAG_A.lifter_top_width_m == pytest.approx(0.152, abs=0.5e-3)
    assert SAG_A.lifter_top_radius_m == pytest.approx(R_TOP)


def test_profile_vertex_count_and_closure():
    pts = geom.liner_profile(SAG_A)
    assert len(pts) == 36 * (4 + SAG_A.plate_segments - 1)
    assert len(set(pts)) == len(pts)
    # Closed: two triangles per edge, including the last-to-first edge.
    assert len(geom.liner_triangles(SAG_A)) == 2 * len(pts)


def test_profile_is_counter_clockwise_and_angles_increase():
    pts = geom.liner_profile(SAG_A)
    assert geom.polygon_area(pts) > 0
    angles = [math.atan2(y, x) for x, y in pts]
    unwrapped = [angles[0]]
    for a in angles[1:]:
        d = (a - unwrapped[-1]) % (2 * math.pi)
        unwrapped.append(unwrapped[-1] + d)
    assert all(b > a for a, b in zip(unwrapped, unwrapped[1:]))
    assert unwrapped[-1] - unwrapped[0] < 2 * math.pi


def test_lifter_count_and_spacing():
    centres = []
    for k in range(36):
        p = _lifter_points(SAG_A, k)
        top_mid = ((p[1][0] + p[2][0]) / 2, (p[1][1] + p[2][1]) / 2)
        centres.append(_angle(top_mid))
    gaps = [(centres[(k + 1) % 36] - centres[k]) % (2 * math.pi) for k in range(36)]
    assert gaps == [pytest.approx(2 * math.pi / 36)] * 36


def test_plate_and_lifter_top_radii():
    pts = geom.liner_profile(SAG_A)
    radii = [math.hypot(x, y) for x, y in pts]
    assert max(radii) == pytest.approx(R_PLATE)
    lifter = _lifter_points(SAG_A, 3)
    # Plate-side corners on the plate circle; top corners on the top line.
    for p in (lifter[0], lifter[3]):
        assert math.hypot(*p) == pytest.approx(R_PLATE)
    centre = math.radians(3 * 10)
    for p in (lifter[1], lifter[2]):
        assert p[0] * math.cos(centre) + p[1] * math.sin(centre) == pytest.approx(R_TOP)
    # Nothing reaches closer to the axis than the top corners.
    assert min(radii) == pytest.approx(math.hypot(R_TOP, 0.152 / 2), abs=1e-3)


def test_top_width_and_face_angle():
    (t0, s0), (t1, s1), (t2, s2), (t3, s3) = geom.lifter_section(SAG_A)
    assert t2 - t1 == pytest.approx(SAG_A.lifter_top_width_m)
    assert s1 == s2 == pytest.approx(R_TOP)
    for (ta, sa), (tb, sb) in (((t0, s0), (t1, s1)), ((t3, s3), (t2, s2))):
        angle = math.degrees(math.atan2(abs(ta - tb), sa - sb))
        assert angle == pytest.approx(35.0)
    # Width at the shell, on the extended faces: 523 mm.
    k = math.tan(math.radians(35.0))
    assert t2 - t1 + 2 * (R_SHELL - R_TOP) * k == pytest.approx(0.523 + 2 * 0.130 * k)


def test_exposed_lifter_area():
    exact = geom.exposed_lifter_area(SAG_A)
    # Just under the flat-base trapezoid of the docs (curved plate surface).
    assert exact < TRAPEZOID
    assert exact == pytest.approx(TRAPEZOID, rel=0.03)
    # Independent check: the lifter region is the polygon section plus the
    # circular segment, i.e. the profile area with one lifter removed.
    one = MillGeometry(n_lifters=1, plate_segments=20000)
    hole = math.pi * R_PLATE**2 - geom.polygon_area(geom.liner_profile(one))
    assert hole == pytest.approx(exact, rel=1e-4)


def test_net_cross_section_matches_profile():
    analytic = math.pi * R_PLATE**2 - 36 * geom.exposed_lifter_area(SAG_A)
    assert geom.net_cross_section(SAG_A) == pytest.approx(analytic)
    assert geom.polygon_area(geom.liner_profile(SAG_A)) == pytest.approx(analytic, rel=1e-4)
    # Converges as the plate arcs are refined.
    fine = MillGeometry(plate_segments=64)
    assert geom.polygon_area(geom.liner_profile(fine)) == pytest.approx(analytic, rel=1e-6)


def test_plate_gap():
    gap = geom.plate_gap(SAG_A)
    # Pitch at the plate surface minus the base on the plate (~0.414 m).
    assert gap == pytest.approx(math.pi * 10.7128 / 36 - 0.514, abs=0.01)
    assert gap / 0.1397 > 2.9


def test_triangles_span_slice_depth():
    tris = geom.liner_triangles(SAG_A, z0=0.1)
    zs = {round(p[2], 9) for tri in tris for p in tri}
    assert zs == {0.1, round(0.1 + SAG_A.depth_m, 9)}


def test_mesh_hash_is_stable_and_sensitive():
    h = geom.mesh_hash(geom.liner_triangles(SAG_A))
    assert h == geom.mesh_hash(geom.liner_triangles(MillGeometry()))
    assert h != geom.mesh_hash(geom.liner_triangles(MillGeometry(lifter_face_angle_deg=30.0)))


def test_geometry_summary():
    s = geom.geometry_summary(SAG_A)
    assert s["n_lifters"] == 36
    assert s["diameter_inside_liners_m"] == pytest.approx(10.7128)
    assert s["lifter_top_width_m"] == pytest.approx(0.152, abs=0.5e-3)
    assert s["n_triangles"] == 2 * 36 * (4 + SAG_A.plate_segments - 1)
    assert len(s["mesh_sha256"]) == 64


def test_write_stl(tmp_path):
    tris = geom.liner_triangles(MillGeometry(n_lifters=4, plate_segments=2))
    path = geom.write_stl(tris, tmp_path / "liner.stl")
    text = path.read_text(encoding="utf-8")
    assert text.startswith("solid mill_liner")
    assert text.count("facet normal") == len(tris)
    assert text.rstrip().endswith("endsolid mill_liner")


def test_end_wall_covers_the_shell():
    (a, b, c), (_, _, d) = geom.end_wall_triangles(4.0, z=0.3)
    xs = [p[0] for p in (a, b, c, d)]
    assert min(xs) < -2.0 and max(xs) > 2.0
    assert {p[2] for p in (a, b, c, d)} == {0.3}

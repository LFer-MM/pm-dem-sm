"""Parametric SAG mill slice geometry: shell liner (plates + lifters) and end walls.

Backend-agnostic and stdlib-only: every function returns plain vertex
tuples, which a DEM backend turns into its own wall elements (YADE facets in
:mod:`pm_dem_sm.simulation.yade_dem.stl`). The mill axis is the Z axis
through the origin and the slice spans ``z0 <= z <= z0 + depth``.

The liner follows the generator plan of
docs/scientific_rationale/10_mill_geometry.md ("Mill generator"), built from
the design parameters of a :class:`~pm_dem_sm.simulation.scenario.MillGeometry`
(any object with the same attributes works):

- ``n_lifters`` lifters evenly spaced, alternating with flat plates
  ``plate_thickness_m`` thick, so the plate surface is the circle of radius
  ``R_plate = shell_diameter_m / 2 - plate_thickness_m`` (the diameter inside
  liners).
- Each lifter is ``lifter_base_width_m`` wide at the shell and reaches
  ``lifter_height_m`` from the shell, i.e. a flat top at
  ``R_top = shell_diameter_m / 2 - lifter_height_m``. Its sides are
  vertical through the plate thickness (hidden behind the plate surface, so
  not generated) and then both faces are inclined ``lifter_face_angle_deg``
  from the lifter's radial centreline up to the top, whose width is
  ``base - 2 (height - plate) tan(angle)`` (152 mm for SAG_A). Rounded
  corners are ignored.
- The particle-facing profile is therefore: plate arc, leading face (from
  where it meets the plate circle), top, trailing face, next plate arc. It
  is extruded to the slice depth and split into triangles.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

# --- Public functions --------------------------------------------------------


def lifter_top_width(mill) -> float:
    """Return the width of a lifter's flat top (m).

    Args:
        mill: Liner design (``lifter_base_width_m``, ``lifter_height_m``,
            ``plate_thickness_m``, ``lifter_face_angle_deg``).

    Returns:
        float: ``base - 2 (height - plate) tan(angle)``.
    """
    exposed = mill.lifter_height_m - mill.plate_thickness_m
    return mill.lifter_base_width_m - 2.0 * exposed * math.tan(
        math.radians(mill.lifter_face_angle_deg)
    )


def plate_radius(mill) -> float:
    """Return the radius of the plate surface (m): half the diameter inside liners."""
    return mill.shell_diameter_m / 2.0 - mill.plate_thickness_m


def lifter_top_radius(mill) -> float:
    """Return the radius of the lifter tops (m), measured on the lifter centreline."""
    return mill.shell_diameter_m / 2.0 - mill.lifter_height_m


def lifter_section(mill) -> list[tuple[float, float]]:
    """Return one lifter's exposed corners in its local frame ``(t, s)``.

    ``s`` runs along the lifter's radial centreline (outwards), ``t`` across
    it in the direction of increasing angle. The four points are, in
    counter-clockwise order around the mill: leading face on the plate
    circle, leading top corner, trailing top corner, trailing face on the
    plate circle.

    Args:
        mill: Liner design.

    Returns:
        list[tuple[float, float]]: Four ``(t, s)`` points.
    """
    k = math.tan(math.radians(mill.lifter_face_angle_deg))
    s_top = lifter_top_radius(mill)
    half_top = lifter_top_width(mill) / 2.0
    r_plate = plate_radius(mill)
    # Face half-width w(s) = c + k s; it meets the plate circle where
    # s^2 + w(s)^2 = r_plate^2 (positive root).
    c = half_top - k * s_top
    a, b, cc = 1.0 + k * k, 2.0 * c * k, c * c - r_plate**2
    s_base = (-b + math.sqrt(b * b - 4.0 * a * cc)) / (2.0 * a)
    w_base = c + k * s_base
    return [(-w_base, s_base), (-half_top, s_top), (half_top, s_top), (w_base, s_base)]


def plate_gap(mill) -> float:
    """Return the free plate arc between two neighbouring lifters (m).

    Measured on the plate circle between the points where the lifter faces
    meet it; ``<= 0`` means the lifters overlap.
    """
    t_base, s_base = lifter_section(mill)[3]
    pitch = 2.0 * math.pi / mill.n_lifters
    return plate_radius(mill) * (pitch - 2.0 * math.atan2(t_base, s_base))


def liner_profile(mill, phase: float = 0.0) -> list[tuple[float, float]]:
    """Return the closed liner profile as ``(x, y)`` points, counter-clockwise.

    The first point is the leading face of the first lifter (centred at
    ``phase`` from ``+X``); the closing edge runs from the last point back to
    the first. Each plate arc between two lifters is split into
    ``mill.plate_segments`` straight segments with vertices on the plate
    circle.

    Args:
        mill: Liner design (``n_lifters`` >= 1).
        phase: Angle of the first lifter's centreline from ``+X`` (rad).

    Returns:
        list[tuple[float, float]]: Profile vertices.
    """
    n = mill.n_lifters
    r_plate = plate_radius(mill)
    section = lifter_section(mill)
    t_base, s_base = section[3]
    half_angle = math.atan2(t_base, s_base)
    pitch = 2.0 * math.pi / n
    points = []
    for i in range(n):
        theta = phase + i * pitch
        er = (math.cos(theta), math.sin(theta))
        et = (-math.sin(theta), math.cos(theta))
        for t, s in section:
            points.append((s * er[0] + t * et[0], s * er[1] + t * et[1]))
        # Plate arc to the next lifter's leading face (interior vertices only).
        a0, a1 = theta + half_angle, theta + pitch - half_angle
        m = mill.plate_segments
        for j in range(1, m):
            a = a0 + (a1 - a0) * j / m
            points.append((r_plate * math.cos(a), r_plate * math.sin(a)))
    return points


def liner_triangles(mill, z0: float = 0.0, phase: float = 0.0) -> list[tuple]:
    """Return the liner surface (plates and lifters) extruded to the slice depth.

    Args:
        mill: Liner design plus ``depth_m``.
        z0: Z of the back end of the slice (m).
        phase: Angle of the first lifter's centreline from ``+X`` (rad).

    Returns:
        list[tuple]: Two triangles per profile edge, each three ``(x, y, z)``.
    """
    pts = liner_profile(mill, phase)
    z1 = z0 + mill.depth_m
    tris = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        a, b = (x0, y0, z0), (x1, y1, z0)
        c, d = (x1, y1, z1), (x0, y0, z1)
        tris += [(a, b, c), (a, c, d)]
    return tris


def end_wall_triangles(diameter, z, margin=1.5):
    """Return two triangles covering the mill cross-section at ``z``.

    The pair forms a square of half-size ``margin * diameter / 2`` centered on
    the axis, so it closes the shell and the lifters with room to spare.

    Args:
        diameter: Shell diameter (m).
        z: Z position of the wall (m).
        margin: Half-size of the wall relative to the shell radius.

    Returns:
        list[tuple]: Two triangles, each three ``(x, y, z)`` tuples.
    """
    h = margin * diameter / 2.0
    a, b, c, d = (-h, -h, z), (h, -h, z), (h, h, z), (-h, h, z)
    return [(a, b, c), (a, c, d)]


def polygon_area(points) -> float:
    """Return the signed area of a closed polygon (shoelace; > 0 if counter-clockwise)."""
    return 0.5 * sum(
        x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1])
    )


def exposed_lifter_area(mill) -> float:
    """Return the exact cross-section of one lifter above the plate surface (m^2).

    The quadrilateral of :func:`lifter_section` plus the circular segment
    between its two plate-circle corners. Close to, and slightly less than,
    the trapezoid ``(base + top) / 2 x (height - plate)`` (0.0894 m^2 for
    SAG_A), whose base lies on a flat plane instead of the curved plate.

    Args:
        mill: Liner design.

    Returns:
        float: Area (m^2).
    """
    section = lifter_section(mill)
    quad = polygon_area(section)
    t_base, s_base = section[3]
    phi = 2.0 * math.atan2(t_base, s_base)
    r = plate_radius(mill)
    return abs(quad) + 0.5 * r * r * (phi - math.sin(phi))


def net_cross_section(mill) -> float:
    """Return the analytic free cross-section inside the liner (m^2).

    The circle inside liners minus the exposed section of every lifter.
    """
    return math.pi * plate_radius(mill) ** 2 - mill.n_lifters * exposed_lifter_area(mill)


def mesh_hash(triangles) -> str:
    """Return a SHA-256 of the triangle coordinates (rounded to 1 um), for run manifests."""
    h = hashlib.sha256()
    for tri in triangles:
        for p in tri:
            h.update(f"{p[0]:.6f},{p[1]:.6f},{p[2]:.6f};".encode())
    return h.hexdigest()


def geometry_summary(mill, triangles=None) -> dict:
    """Return the liner's input parameters and derived values for a run manifest.

    Args:
        mill: Liner design plus ``depth_m``.
        triangles: The liner triangles; built with :func:`liner_triangles` if
            ``None``.

    Returns:
        dict: Inputs, derived radii and widths, areas, triangle count and
        :func:`mesh_hash`.
    """
    tris = liner_triangles(mill) if triangles is None else triangles
    inputs = (
        "shell_diameter_m",
        "n_lifters",
        "lifter_base_width_m",
        "lifter_height_m",
        "lifter_face_angle_deg",
        "plate_thickness_m",
        "plate_segments",
        "depth_m",
    )
    return {
        **{k: getattr(mill, k) for k in inputs},
        "diameter_inside_liners_m": 2.0 * plate_radius(mill),
        "plate_radius_m": plate_radius(mill),
        "lifter_top_radius_m": lifter_top_radius(mill),
        "lifter_top_width_m": lifter_top_width(mill),
        "exposed_lifter_area_m2": exposed_lifter_area(mill),
        "net_cross_section_m2": net_cross_section(mill),
        "n_triangles": len(tris),
        "mesh_sha256": mesh_hash(tris),
    }


def write_stl(triangles, path: Path | str, name: str = "mill_liner") -> Path:
    """Write triangles as an ASCII STL (for viewing; the simulation uses the triangles directly).

    Args:
        triangles: Iterable of three ``(x, y, z)`` tuples.
        path: Output file.
        name: Solid name in the STL header.

    Returns:
        Path: The written file.
    """
    path = Path(path)
    lines = [f"solid {name}"]
    for a, b, c in triangles:
        n = _normal(a, b, c)
        lines.append(f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}")
        lines.append("    outer loop")
        for p in (a, b, c):
            lines.append(f"      vertex {p[0]:.6e} {p[1]:.6e} {p[2]:.6e}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append(f"endsolid {name}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# --- Private helper functions ------------------------------------------------


def _normal(a, b, c):
    """Return the unit normal of triangle ``abc`` (zero vector if degenerate)."""
    u = [b[i] - a[i] for i in range(3)]
    v = [c[i] - a[i] for i in range(3)]
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    norm = math.sqrt(sum(x * x for x in n))
    return tuple(x / norm for x in n) if norm else (0.0, 0.0, 0.0)

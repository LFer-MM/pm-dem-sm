"""Mill liner and end walls as YADE facets, plus ingress-geometry helpers (YADE)."""

from __future__ import annotations

import math
from math import radians

from yade import FrictMat, Vector3
from yade.utils import facet
from yade.wrapper import O

from .. import mill_geometry

# --- Module state ------------------------------------------------------------

#: Body ids of the loaded mill slice and its end caps; set by
#: :func:`initialize_parametric_mill`.
SAG_MILL_SLICE_BODY_GROUP = None


# --- Public functions --------------------------------------------------------


def initialize_parametric_mill(mill, cap_material, liner=None):
    """Build the liner (plates + lifters) and end walls; set :data:`SAG_MILL_SLICE_BODY_GROUP`.

    Geometry comes from :mod:`pm_dem_sm.simulation.mill_geometry`; the slice
    spans ``0 <= z <= mill.depth_m`` around the Z axis.

    Args:
        mill: :class:`~pm_dem_sm.simulation.scenario.MillGeometry`.
        cap_material: Material label of the two end walls.
        liner: Liner triangles from
            :func:`~pm_dem_sm.simulation.mill_geometry.liner_triangles`;
            built from ``mill`` if ``None``.

    Returns:
        list: Body ids of the liner facets and end walls.
    """
    global SAG_MILL_SLICE_BODY_GROUP

    if liner is None:
        liner = mill_geometry.liner_triangles(mill)
    ids = [O.bodies.append(facet(t, material=mill.liner_material, color=(1, 1, 1))) for t in liner]
    for z, color in ((0.0, (1, 0, 0)), (mill.depth_m, (0, 1, 0))):
        for t in mill_geometry.end_wall_triangles(mill.shell_diameter_m, z):
            ids.append(O.bodies.append(facet(t, material=cap_material, color=color, wire=True)))
    print(
        f"Parametric mill: D inside liners {mill.diameter_m:.4f} m, {mill.n_lifters} lifters, "
        f"{len(ids)} facets."
    )

    SAG_MILL_SLICE_BODY_GROUP = ids
    return ids


def createBox(x, y, z):
    """Append box facets (half-extents ``x``, ``y``; wall height fixed at 0.375 m).

    Args:
        x: Half-extent in X (meters).
        y: Half-extent in Y (meters).
        z: Unused (see note); retained for call-site compatibility.

    Note:
        The ``z`` argument is accepted for API compatibility but the facet
        height is hardcoded to ``0.375``.
    """
    mat = O.materials.append(FrictMat(density=7850, young=1e9, poisson=0.3, frictionAngle=radians(10)))

    # Corner points
    b0 = (-x, -y, 0)
    b1 = ( x, -y, 0)
    b2 = ( x,  y, 0)
    b3 = (-x,  y, 0)
    t0 = (-x, -y, 0.375)
    t1 = ( x, -y, 0.375)
    t2 = ( x,  y, 0.375)
    t3 = (-x,  y, 0.375)

    facets = [
        # Bottom (z=0)
        [b0, b1, b2],
        [b0, b2, b3],
        # Top (z=0.375)
        [t0, t2, t1],
        [t0, t3, t2],
        # -x wall
        [b0, t0, t3],
        [b0, t3, b3],
        # +x wall
        [b1, b2, t2],
        [b1, t2, t1],
        # -y wall
        [b0, b1, t1],
        [b0, t1, t0],
    ]

    for tri in facets:
        O.bodies.append(facet(tri, material=mat))


def createFunnel(x, y, z, fx, fy, dy):
    """Append funnel and deposit-box facets for particle ingress geometry.

    Args:
        x: Half-width of the top box in X (meters).
        y: Full length of the top box in Y (meters).
        z: Height of the top box / funnel walls in Z (meters).
        fx: Half-width of the narrowed funnel/deposit in X (meters).
        fy: Length of the deposit box in Y (meters).
        dy: Funnel slope length in Y (meters).
    """
    mat = O.materials.append(FrictMat(density=7850, young=1e9, poisson=0.3, frictionAngle=radians(10)))

    # --- Top box corners -----------------------------------------------------
    # Centered at (0, 0): X spans -x..+x and Y spans -y/2..+y/2.
    tb0 = (-x, -y/2, 0)
    tb1 = ( x, -y/2, 0)
    tb2 = ( x, -y/2, z)
    tb3 = (-x, -y/2, z)
    tt0 = (-x,  y/2, 0)
    tt1 = ( x,  y/2, 0)
    tt2 = ( x,  y/2, z)
    tt3 = (-x,  y/2, z)

    # --- Funnel corners ------------------------------------------------------
    # Funnel top is the top box's bottom (y = -y/2); its bottom is at
    # y = -y/2 - dy, narrowed to fx.
    fb0 = (-fx, -y/2-dy, 0)
    fb1 = ( fx, -y/2-dy, 0)
    fb2 = ( fx, -y/2-dy, z)
    fb3 = (-fx, -y/2-dy, z)

    # --- Deposit box corners -------------------------------------------------
    # Deposit box top is the funnel bottom (y = -y/2 - dy); its bottom is at
    # y = -y/2 - dy - fy.
    db0 = (-fx, -y/2-dy-fy, 0)
    db1 = ( fx, -y/2-dy-fy, 0)
    db2 = ( fx, -y/2-dy-fy, z)
    db3 = (-fx, -y/2-dy-fy, z)

    facets = [
        # --- Top box ---------------------------------------------------------
        # -z wall
        [tb0, tb1, tt1],
        [tb0, tt1, tt0],
        # +z wall
        [tb2, tt2, tt3],
        [tb2, tt3, tb3],
        # -x wall
        [tb0, tt0, tt3],
        [tb0, tt3, tb3],
        # +x wall
        [tb1, tb2, tt2],
        [tb1, tt2, tt1],
        # +y wall (back)
        [tt0, tt1, tt2],
        [tt0, tt2, tt3],

        # --- Funnel slopes ---------------------------------------------------
        # -x slope
        [tb0, fb0, fb3],
        [tb0, fb3, tb3],
        # +x slope
        [tb1, tb2, fb2],
        [tb1, fb2, fb1],
        # -z slope
        [tb0, tb1, fb1],
        [tb0, fb1, fb0],
        # +z slope
        [tb3, fb3, fb2],
        [tb3, fb2, tb2],

        # --- Deposit box -----------------------------------------------------
        # Bottom face (closed)
        [db0, db2, db1],
        [db0, db3, db2],
        # -z wall
        [fb0, fb1, db1],
        [fb0, db1, db0],
        # +z wall
        [fb2, fb3, db3],
        [fb2, db3, db2],
        # -x wall
        [fb0, db0, db3],
        [fb0, db3, fb3],
        # +x wall
        [fb1, fb2, db2],
        [fb1, db2, db1],
        # +y wall (back of deposit box)
        [fb3, db3, db2],
        [fb3, db2, fb2],
    ]

    for tri in facets:
        O.bodies.append(facet(tri, material=mat))


def chord_box_3d(diameter, y, box_height, depth):
    """Return the widest 3D box from ``y`` to ``y + box_height`` that fits in the circle.

    The box width is the shorter of the chords at its bottom and top faces,
    so its corners stay inside the mill whether it sits below or above the
    axis. It spans the full Z depth.

    Args:
        diameter: Mill / circle diameter in meters.
        y: Bottom Y of the chord box (clamped to ``[-r, r]``).
        box_height: Box height in Y (meters).
        depth: Slice depth in Z (meters).

    Returns:
        dict: Geometry with corner extents, dimensions, and
        ``min_corner`` / ``max_corner`` ``Vector3`` values for ``SpherePack``.
    """
    r = diameter / 2.0
    y = max(-r, min(r, y))
    farthest = max(abs(y), abs(y + box_height))
    half_chord = math.sqrt(max(0.0, r ** 2 - farthest ** 2))
    x_min, x_max = -half_chord, half_chord
    return {
        "x_min": x_min, "x_max": x_max,
        "y_bottom": y, "y_top": y + box_height,
        "z_min": 0.0, "z_max": depth,
        "width": x_max - x_min, "height": box_height, "depth": depth,
        "min_corner": Vector3(x_min, y, 0.0),
        "max_corner": Vector3(x_max, y + box_height, depth),
    }


def get_surface_y(padding=0.1):
    """Return the highest sphere-top Y in the current scene plus ``padding``.

    Args:
        padding: Extra clearance above the tallest sphere top (meters).

    Returns:
        float: Y coordinate for the next ingress chord-box bottom.
    """
    tops = [b.state.pos[1] + b.shape.radius for b in O.bodies if type(b.shape).__name__ == "Sphere"]
    return max(tops) + padding

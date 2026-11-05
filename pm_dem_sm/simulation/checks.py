"""Run checks and measurements on simulation data, independent of the DEM backend.

Pure Python and numpy, so it runs both under YADE and in the project venv
(and is unit-tested there). The YADE side collects the raw data (positions,
contacts, the mill log) and calls these functions; the decisions they
implement are in ``docs/scientific_rationale/``:

- :func:`settle_stop` -- geometric settle stop rule
  (13_initial_conditions.md; C04-5, V18).
- :func:`overlap_stats` -- overlaps relative to the smaller **diameter**, per
  pair type (03_stiffness_young_modulus.md; C03-2, V3).
- :func:`percentile` -- e.g. the P99 normal impact speed (02_time_step.md;
  C02-3, V2).
- :func:`energy_balance` -- drive work against contact dissipation
  (04_numerical_damping.md, 16_validation_checks.md; C04-3, V4).
- :func:`new_sphere_overlaps`, :func:`sphere_wall_overlaps`,
  :func:`escaped_spheres` -- V13 / V14 (C04-4).
- :func:`restitution` -- V1 (C01-4).
- :func:`repose_angle` -- heap slope (06_rolling_resistance.md; C06-3).
- :func:`fill_level` -- J from the settled surface profile, Morrell's
  convention, and the packing fraction phi (12_charge_fill_and_particles.md;
  C12-2, V16); :func:`next_ball_count` / :func:`next_rock_count` -- the count
  updates of the grind-out / crash-stop procedure (C12-3).
"""

from __future__ import annotations

from itertools import pairwise
import math

import numpy as np

# --- Constants ---------------------------------------------------------------

#: Geometric settle stop rule (docs/scientific_rationale/13_initial_conditions.md):
#: window over which the bed geometry must be stationary (s) ...
SETTLE_WINDOW_S = 1.0
#: ... largest change of the charge centre-of-mass angle in the window (deg) ...
SETTLE_ANGLE_TOL_DEG = 0.5
#: ... largest change of its height, as a fraction of the small diameter ...
SETTLE_HEIGHT_TOL_REL_D = 0.01
#: ... and largest mean particle speed at the end of the window (m/s).
SETTLE_SPEED_TOL_M_S = 0.01
#: Pair-type labels for overlap statistics.
PAIR_TYPES = ("small-small", "small-large", "large-large", "small-wall", "large-wall")


# --- Public functions --------------------------------------------------------


def percentile(values, q: float) -> float:
    """Return the ``q``-th percentile of ``values`` (``nan`` if empty)."""
    a = np.asarray(list(values), dtype=float)
    return float(np.percentile(a, q)) if a.size else float("nan")


def settle_stop(
    rows,
    d_small: float,
    t_start: float,
    max_time_s: float,
    window_s: float = SETTLE_WINDOW_S,
    angle_tol_deg: float = SETTLE_ANGLE_TOL_DEG,
    height_tol_rel_d: float = SETTLE_HEIGHT_TOL_REL_D,
    speed_tol_m_s: float = SETTLE_SPEED_TOL_M_S,
) -> dict:
    """Evaluate the geometric settle stop rule on the mill-log rows of a settle stage.

    The bed is settled when, over the last ``window_s`` of simulated time,
    the charge centre-of-mass angle varies by less than ``angle_tol_deg``,
    its height by less than ``height_tol_rel_d x d_small``, and the mean
    particle speed of the last row is below ``speed_tol_m_s``. The stage
    also ends once ``max_time_s`` has elapsed since ``t_start`` (time cap).

    Args:
        rows: Log rows (dicts) with ``time``, ``angle_all_deg``,
            ``com_height_m`` and ``mean_speed_m_s``, in time order.
        d_small: Small-particle diameter (m).
        t_start: Simulated time at the start of the stage (s).
        max_time_s: Time cap (s).
        window_s: Stationarity window (s).
        angle_tol_deg: Angle tolerance (deg).
        height_tol_rel_d: Height tolerance relative to ``d_small``.
        speed_tol_m_s: Mean-speed tolerance (m/s).

    Returns:
        dict: ``stop`` (bool), ``reason`` (``"stationary"``, ``"time_cap"``
        or ``None``), and the window's ``angle_change_deg``,
        ``height_change_m``, ``mean_speed_m_s`` (``None`` before a full
        window exists).
    """
    rows = [r for r in rows if r["time"] >= t_start]
    out = {
        "stop": False,
        "reason": None,
        "angle_change_deg": None,
        "height_change_m": None,
        "mean_speed_m_s": None,
    }
    if rows:
        t_end = rows[-1]["time"]
        if t_end - rows[0]["time"] >= window_s - 1e-9:
            win = [r for r in rows if r["time"] >= t_end - window_s - 1e-9]
            angles = [r["angle_all_deg"] for r in win]
            heights = [r["com_height_m"] for r in win]
            out["angle_change_deg"] = max(angles) - min(angles)
            out["height_change_m"] = max(heights) - min(heights)
            out["mean_speed_m_s"] = rows[-1]["mean_speed_m_s"]
            if (
                out["angle_change_deg"] < angle_tol_deg
                and out["height_change_m"] < height_tol_rel_d * d_small
                and out["mean_speed_m_s"] < speed_tol_m_s
            ):
                out.update(stop=True, reason="stationary")
                return out
        if t_end - t_start >= max_time_s:
            out.update(stop=True, reason="time_cap")
    return out


def pair_type(r1: float | None, r2: float | None, r_split: float) -> str:
    """Return the pair-type label of a contact; ``None`` radius means a wall (facet)."""
    order = {"small": 0, "large": 1, "wall": 2}
    sizes = sorted(
        ("wall" if r is None else ("small" if r < r_split else "large") for r in (r1, r2)),
        key=order.get,
    )
    if sizes[1] == "wall":
        return f"{sizes[0]}-wall"
    return "-".join(sizes)


def overlap_stats(samples) -> dict:
    """Return overlap statistics relative to the smaller diameter, per pair type and overall.

    Args:
        samples: Iterable of ``(pair_type, overlap / smaller diameter)``; for
            a sphere-wall contact the diameter is the sphere's.

    Returns:
        dict: Pair type (and ``"all"``) -> ``{"n", "mean", "p99", "max"}``.
    """
    groups: dict[str, list[float]] = {}
    for kind, rel in samples:
        groups.setdefault(kind, []).append(float(rel))
        groups.setdefault("all", []).append(float(rel))
    out = {}
    for kind, vals in groups.items():
        a = np.asarray(vals)
        out[kind] = {
            "n": int(a.size),
            "mean": float(a.mean()),
            "p99": float(np.percentile(a, 99)),
            "max": float(a.max()),
        }
    return out


def energy_balance(rows) -> dict:
    """Return the energy balance between the first and last of ``rows`` (V4).

    ``W_drive = integral of power dt`` (trapezoid) must equal the change of
    mechanical energy (kinetic + gravitational potential + elastic) plus the
    energy dissipated in the contacts. YADE tracks the dashpot and friction
    dissipation (``dissipated_J``) but not the plastic dissipation of the
    rolling moment; if the rows carry the monitor's sampled estimate of the
    latter (``rolling_dissipated_J``), it is added.

    Args:
        rows: Log rows with ``time``, ``power_kW``, ``kinetic_J``,
            ``potential_J``, ``elastic_J``, ``dissipated_J`` (cumulative)
            and optionally ``rolling_dissipated_J`` (cumulative).

    Returns:
        dict: ``drive_work_J``, ``dissipated_J`` (tracked),
        ``rolling_dissipated_J`` (estimate, 0 if absent), ``delta_mechanical_J``,
        ``residual_J`` (drive - dissipated - rolling - delta mechanical) and
        ``residual_rel`` (relative to the larger of drive work and total
        dissipation).
    """
    rows = list(rows)
    w = 0.0
    for a, b in pairwise(rows):
        w += 0.5 * (a["power_kW"] + b["power_kW"]) * 1000.0 * (b["time"] - a["time"])
    first, last = rows[0], rows[-1]
    mech = ("kinetic_J", "potential_J", "elastic_J")
    d_mech = sum(last[k] - first[k] for k in mech)
    diss = last["dissipated_J"] - first["dissipated_J"]
    rolling = last.get("rolling_dissipated_J", 0.0) - first.get("rolling_dissipated_J", 0.0)
    resid = w - diss - rolling - d_mech
    scale = max(abs(w), abs(diss + rolling), 1e-12)
    return {
        "drive_work_J": w,
        "dissipated_J": diss,
        "rolling_dissipated_J": rolling,
        "delta_mechanical_J": d_mech,
        "residual_J": resid,
        "residual_rel": resid / scale,
    }


def new_sphere_overlaps(new, existing, tol: float = 0.0) -> tuple[int, float]:
    """Return the number and depth of overlaps involving the new spheres (V13).

    Args:
        new: Spheres ``(x, y, z, r)`` just inserted.
        existing: All other spheres ``(x, y, z, r)``.
        tol: Penetration below which a contact is not counted (m).

    Returns:
        tuple[int, float]: Overlapping pairs and the largest penetration (m).
    """
    new = np.asarray(new, dtype=float).reshape(-1, 4)
    old = np.asarray(existing, dtype=float).reshape(-1, 4)
    allp = np.vstack([new, old]) if old.size else new
    if not new.size:
        return 0, 0.0
    cell = 2.0 * allp[:, 3].max()
    keys = np.floor(allp[:, :3] / cell).astype(int)
    grid: dict[tuple, list[int]] = {}
    for i, k in enumerate(map(tuple, keys)):
        grid.setdefault(k, []).append(i)
    count, worst = 0, 0.0
    for i in range(len(new)):
        kx, ky, kz = keys[i]
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in grid.get((kx + dx, ky + dy, kz + dz), ()):
                        # New-new pairs once (j > i); new-old pairs always.
                        if j == i or (j < len(new) and j < i):
                            continue
                        pen = allp[i, 3] + allp[j, 3] - np.linalg.norm(allp[i, :3] - allp[j, :3])
                        if pen > tol:
                            count += 1
                            worst = max(worst, float(pen))
    return count, worst


def point_triangle_distance(p, a, b, c) -> float:
    """Return the distance from point ``p`` to triangle ``abc`` (Ericson, Real-Time Collision Detection 5.1.5)."""
    p, a, b, c = (np.asarray(v, dtype=float) for v in (p, a, b, c))
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = ab @ ap, ac @ ap
    if d1 <= 0 and d2 <= 0:
        return float(np.linalg.norm(p - a))
    bp = p - b
    d3, d4 = ab @ bp, ac @ bp
    if d3 >= 0 and d4 <= d3:
        return float(np.linalg.norm(p - b))
    vc = d1 * d4 - d3 * d2
    if vc <= 0 and d1 >= 0 and d3 <= 0:
        q = a + d1 / (d1 - d3) * ab
        return float(np.linalg.norm(p - q))
    cp = p - c
    d5, d6 = ab @ cp, ac @ cp
    if d6 >= 0 and d5 <= d6:
        return float(np.linalg.norm(p - c))
    vb = d5 * d2 - d1 * d6
    if vb <= 0 and d2 >= 0 and d6 <= 0:
        q = a + d2 / (d2 - d6) * ac
        return float(np.linalg.norm(p - q))
    va = d3 * d6 - d5 * d4
    if va <= 0 and (d4 - d3) >= 0 and (d5 - d6) >= 0:
        q = b + (d4 - d3) / ((d4 - d3) + (d5 - d6)) * (c - b)
        return float(np.linalg.norm(p - q))
    denom = 1.0 / (va + vb + vc)
    q = a + ab * (vb * denom) + ac * (vc * denom)
    return float(np.linalg.norm(p - q))


def sphere_wall_overlaps(
    spheres, triangles, depth: float, inner_radius: float, tol: float = 0.0
) -> tuple[int, float]:
    """Return the number and depth of sphere-wall overlaps (V13).

    Walls are the liner ``triangles`` and the two flat end walls at
    ``z = 0`` and ``z = depth``. Spheres entirely inside ``inner_radius``
    (the lifter-top radius) cannot touch the liner and skip the triangle
    test.

    Args:
        spheres: ``(x, y, z, r)`` tuples.
        triangles: Liner triangles, three ``(x, y, z)`` each.
        depth: Slice depth (m).
        inner_radius: Radius inside which nothing of the liner lies (m).
        tol: Penetration below which a contact is not counted (m).

    Returns:
        tuple[int, float]: Overlapping sphere-wall pairs and the largest
        penetration (m).
    """
    count, worst = 0, 0.0
    tris = [tuple(np.asarray(v, dtype=float) for v in t) for t in triangles]
    for x, y, z, r in spheres:
        for pen in (r - z, z + r - depth):
            if pen > tol:
                count += 1
                worst = max(worst, pen)
        if math.hypot(x, y) + r < inner_radius:
            continue
        for a, b, c in tris:
            pen = r - point_triangle_distance((x, y, z), a, b, c)
            if pen > tol:
                count += 1
                worst = max(worst, pen)
    return count, worst


def escaped_spheres(spheres, shell_radius: float, depth: float) -> int:
    """Return how many sphere centres lie outside the shell radius or the slice depth (V14)."""
    n = 0
    for x, y, z, _ in spheres:
        if math.hypot(x, y) > shell_radius or not 0.0 <= z <= depth:
            n += 1
    return n


def restitution(v_normal_before: float, v_normal_after: float) -> float:
    """Return ``e = -v_n,after / v_n,before`` for the relative normal velocity of a collision."""
    return -v_normal_after / v_normal_before


def repose_angle(
    spheres,
    centre=(0.0, 0.0),
    base_z: float = 0.0,
    bin_width: float | None = None,
    fit_range=(0.2, 0.8),
) -> dict:
    """Return the angle of repose of a conical heap from its surface particles (deg).

    The heap axis is vertical (``+Z``) through ``centre``. Particles are
    binned by horizontal distance from the axis; the top of each bin is the
    highest sphere top. The heap edge is the outermost bin whose top stands
    more than one particle diameter above ``base_z``; a straight line is
    fitted to the bin tops between ``fit_range`` fractions of that radius
    (excluding the rounded top and the toe).

    Args:
        spheres: ``(x, y, z, r)`` tuples (z up).
        centre: Heap axis ``(x, y)``.
        base_z: Height of the base surface.
        bin_width: Radial bin width (m); one mean diameter by default.
        fit_range: Fraction of the heap radius over which the slope is fitted.

    Returns:
        dict: ``angle_deg``, ``radius_m`` (heap edge), ``height_m`` (top),
        ``n_bins_fitted``, ``r2`` of the fit.
    """
    a = np.asarray(spheres, dtype=float).reshape(-1, 4)
    rho = np.hypot(a[:, 0] - centre[0], a[:, 1] - centre[1])
    top = a[:, 2] + a[:, 3]
    d = 2.0 * a[:, 3].mean()
    w = bin_width or d
    idx = np.floor(rho / w).astype(int)
    tops = {}
    for i, t in zip(idx, top):
        tops[i] = max(tops.get(i, -np.inf), t)
    bins = np.array(sorted(tops))
    heights = np.array([tops[i] for i in bins])
    covered = bins[heights > base_z + d]
    edge = (covered.max() + 1) * w if covered.size else 0.0
    centres = (bins + 0.5) * w
    sel = (centres >= fit_range[0] * edge) & (centres <= fit_range[1] * edge)
    x, y = centres[sel], heights[sel]
    if x.size < 3:
        return {
            "angle_deg": float("nan"),
            "radius_m": edge,
            "height_m": float(heights.max()),
            "n_bins_fitted": int(x.size),
            "r2": float("nan"),
        }
    slope, icpt = np.polyfit(x, y, 1)
    resid = y - (slope * x + icpt)
    r2 = 1.0 - (resid @ resid) / max(((y - y.mean()) ** 2).sum(), 1e-30)
    return {
        "angle_deg": float(math.degrees(math.atan(-slope))),
        "radius_m": float(edge),
        "height_m": float(heights.max()),
        "n_bins_fitted": int(x.size),
        "r2": float(r2),
    }


def boundary_radius(theta, profile) -> np.ndarray:
    """Return the radius of a star-shaped closed profile along the rays at angles ``theta``.

    Args:
        theta: Ray angles (rad), any range.
        profile: Closed counter-clockwise ``(x, y)`` polygon, star-shaped
            from the origin (e.g.
            :func:`~pm_dem_sm.simulation.mill_geometry.liner_profile`).

    Returns:
        np.ndarray: Distance from the origin to the polygon along each ray.
    """
    p = np.asarray(profile, dtype=float)
    ang = np.arctan2(p[:, 1], p[:, 0])
    order = np.argsort(ang)
    p, ang = p[order], ang[order]
    theta = np.asarray(theta, dtype=float)
    th = np.mod(theta.ravel() + np.pi, 2 * np.pi) - np.pi
    k = np.searchsorted(ang, th) % len(p)
    p1, p0 = p[k], p[k - 1]
    e = p1 - p0
    dx, dy = np.cos(th), np.sin(th)
    num = p0[:, 0] * e[:, 1] - p0[:, 1] * e[:, 0]
    den = dx * e[:, 1] - dy * e[:, 0]
    return (num / den).reshape(theta.shape)


def fill_level(
    spheres,
    plate_radius: float,
    depth: float,
    liner_profile=None,
    column_width: float | None = None,
    grid: float = 0.01,
) -> dict:
    """Return the fill level J from the settled surface profile, and the packing fraction.

    Morrell's convention (docs/scientific_rationale/12_charge_fill_and_particles.md):
    J is the area of the circle inside liners (radius ``plate_radius``) that
    lies below the charge surface, divided by the circle's area; lifters
    under the bed are not subtracted. The surface is the top of the highest
    sphere in each vertical column of width ``column_width`` across the
    section (spheres projected along the slice axis), interpolated linearly
    between column centres. If ``liner_profile`` is given, the free bulk
    area (inside the liner, below the surface) is also returned and
    ``phi = solid volume / (free bulk area x depth)``.

    Args:
        spheres: ``(x, y, z, r)`` tuples; gravity along ``-Y``.
        plate_radius: Radius inside liners (m).
        depth: Slice depth (m), for phi.
        liner_profile: Closed liner profile (see :func:`boundary_radius`).
        column_width: Column width (m); the mean sphere diameter by default.
        grid: Raster spacing for the area integration (m).

    Returns:
        dict: ``J``, ``surface`` (list of ``(x_centre, y_top)``), and with a
        profile ``free_bulk_area_m2`` and ``phi``.
    """
    a = np.asarray(spheres, dtype=float).reshape(-1, 4)
    w = column_width or 2.0 * a[:, 3].mean()
    col = np.floor(a[:, 0] / w).astype(int)
    tops: dict[int, float] = {}
    for c, t in zip(col, a[:, 1] + a[:, 3]):
        tops[c] = max(tops.get(c, -np.inf), t)
    cols = np.array(sorted(tops))
    xc, yt = (cols + 0.5) * w, np.array([tops[c] for c in cols])

    r = plate_radius
    xs = np.arange(-r, r, grid) + grid / 2
    ys = np.arange(-r, r, grid) + grid / 2
    X, Y = np.meshgrid(xs, ys)
    surface = np.interp(xs, xc, yt, left=-np.inf, right=-np.inf)
    below = Y <= surface[None, :]
    circle = X**2 + Y**2 <= r * r
    cell = grid * grid
    out = {
        "J": float((below & circle).sum() * cell / (math.pi * r * r)),
        "surface": list(zip(xc.tolist(), yt.tolist())),
    }
    if liner_profile is not None:
        rb = boundary_radius(np.arctan2(Y, X), liner_profile)
        inside = np.hypot(X, Y) <= rb
        area = float((below & inside).sum() * cell)
        solids = float((4.0 / 3.0 * math.pi * a[:, 3] ** 3).sum())
        out["free_bulk_area_m2"] = area
        out["phi"] = solids / (area * depth) if area > 0 else float("nan")
    return out


def fill_converged(J: float, target: float, tol: float = 0.005) -> bool:
    """Return whether ``J`` is within ``tol`` (0.5 points) of ``target``."""
    return abs(J - target) <= tol


def next_ball_count(n_balls: int, J: float, J_target: float) -> int:
    """Return the next ball count of the ball stage (J nearly proportional to the count)."""
    return max(1, round(n_balls * J_target / J))


def next_rock_count(n_rocks: int, J: float, J_balls: float, J_target: float) -> int:
    """Return the next rock count of the mixed stage.

    The rock share of the bed, ``J - J_balls``, is taken as proportional to
    the rock count.

    Args:
        n_rocks: Current rock count.
        J: Measured total fill.
        J_balls: Fill of the ball stage (balls alone).
        J_target: Target total fill (Jc).

    Returns:
        int: Next rock count.
    """
    share = J - J_balls
    if share <= 0:
        return 2 * n_rocks
    return max(1, round(n_rocks * (J_target - J_balls) / share))

"""Overlap statistics, V13 / V14 geometry checks and particle inventory (YADE).

The decisions are implemented in :mod:`pm_dem_sm.simulation.checks`; this
module collects the scene data for them.
"""

from __future__ import annotations

from yade import Sphere
from yade.wrapper import O

from .. import checks
from . import monitor

# --- Public functions --------------------------------------------------------


def check_overlaps(r_split=0.0):
    """Return overlap statistics of the current contacts, relative to the smaller diameter (V3).

    Args:
        r_split: Radius threshold separating small from large spheres (m).

    Returns:
        dict: Pair type (and ``"all"``) -> ``{"n", "mean", "p99", "max"}``
        (see :func:`pm_dem_sm.simulation.checks.overlap_stats`).
    """
    overlaps, _ = monitor.contact_samples(r_split)
    stats = checks.overlap_stats(overlaps) if overlaps else {}
    if stats:
        a = stats["all"]
        print(
            f"Overlap / smaller d: mean {100 * a['mean']:.3f} %, P99 {100 * a['p99']:.3f} %, "
            f"max {100 * a['max']:.3f} % over {a['n']} contacts"
        )
    return stats


def spheres(ids=None):
    """Return ``(x, y, z, r)`` of the given sphere ids (all spheres if ``None``)."""
    bodies = (O.bodies[i] for i in ids) if ids is not None else O.bodies
    out = []
    for b in bodies:
        if b and isinstance(b.shape, Sphere):
            p = b.state.pos
            out.append((p[0], p[1], p[2], b.shape.radius))
    return out


def check_new_batch(new_ids, liner_triangles, depth, inner_radius, tol=0.0):
    """Raise unless the new spheres overlap nothing (V13); return the counts.

    Checks the new spheres against each other, against every other sphere,
    and against the liner and the end walls, before the batch's first step.

    Args:
        new_ids: Body ids of the batch.
        liner_triangles: Liner triangles (see
            :func:`pm_dem_sm.simulation.mill_geometry.liner_triangles`).
        depth: Slice depth (m).
        inner_radius: Lifter-top radius (m).
        tol: Penetration ignored (m).

    Returns:
        dict: ``spheres`` checked, ``sphere_overlaps``, ``wall_overlaps``.

    Raises:
        RuntimeError: On any overlap.
    """
    new_set = set(new_ids)
    new = spheres(new_ids)
    old = [s for b, s in _sphere_items() if b not in new_set]
    n_ss, d_ss = checks.new_sphere_overlaps(new, old, tol)
    n_sw, d_sw = checks.sphere_wall_overlaps(new, liner_triangles, depth, inner_radius, tol)
    if n_ss or n_sw:
        raise RuntimeError(
            f"V13 failed: new batch of {len(new)} spheres has {n_ss} sphere overlaps "
            f"(max {d_ss:.3g} m) and {n_sw} wall overlaps (max {d_sw:.3g} m)"
        )
    return {"spheres": len(new), "sphere_overlaps": 0, "wall_overlaps": 0}


def count_escapes(shell_radius, depth):
    """Return how many spheres lie outside the shell radius or the slice depth (V14)."""
    return checks.escaped_spheres(spheres(), shell_radius, depth)


def get_particle_inventory(r_small, r_large, tol=1e-6, verbose=True):
    """Count spheres per size class (small/large) within ``tol`` of each radius.

    Args:
        r_small: Expected small-species radius (meters).
        r_large: Expected large-species radius (meters).
        tol: Absolute radius tolerance for classification.
        verbose: If ``True``, print the inventory summary.

    Returns:
        dict: Counts with keys ``"small"``, ``"large"``, and ``"unclassified"``.
    """
    inv = {"small": 0, "large": 0, "unclassified": 0}
    for b in O.bodies:
        if type(b.shape).__name__ != "Sphere":
            continue
        r = b.shape.radius
        if abs(r - r_small) <= tol:
            inv["small"] += 1
        elif abs(r - r_large) <= tol:
            inv["large"] += 1
        else:
            inv["unclassified"] += 1
    if verbose:
        print(
            f"Inventory: {inv['small']} small, {inv['large']} large, {inv['unclassified']} unclassified"
        )
    return inv


# --- Private helper functions ------------------------------------------------


def _sphere_items():
    """Yield ``(id, (x, y, z, r))`` for every sphere in the scene."""
    for b in O.bodies:
        if b and isinstance(b.shape, Sphere):
            p = b.state.pos
            yield b.id, (p[0], p[1], p[2], b.shape.radius)

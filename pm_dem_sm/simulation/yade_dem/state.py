"""Save/load particle positions as CSV snapshots, and settle-zero-save of initial conditions (YADE)."""

from __future__ import annotations

import csv

from yade import Sphere, Vector3
from yade.utils import sphere
from yade.wrapper import O

from . import engines, materials, monitor


def save_particle_positions(csv_path, include_velocity=True, include_ang_vel=True):
    """Write sphere states to CSV.

    Args:
        csv_path: Output CSV path.
        include_velocity: If ``True``, include ``vx, vy, vz`` columns.
        include_ang_vel: If ``True``, include ``wx, wy, wz`` columns.

    Returns:
        str: The ``csv_path`` written.
    """
    header = ["id", "x", "y", "z", "r", "m"]

    if include_velocity:
        header += ["vx", "vy", "vz"]

    if include_ang_vel:
        header += ["wx", "wy", "wz"]

    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)

        for b in O.bodies:
            if not b:
                continue
            if not isinstance(getattr(b, "shape", None), Sphere):
                continue

            p = b.state.pos
            r = float(b.shape.radius)
            m = materials._mat_label(b)

            row = [int(b.id), float(p[0]), float(p[1]), float(p[2]), r, m]

            if include_velocity:
                v = b.state.vel
                row += [float(v[0]), float(v[1]), float(v[2])]

            if include_ang_vel:
                om = b.state.angVel
                row += [float(om[0]), float(om[1]), float(om[2])]

            w.writerow(row)

    print("Saved particle positions to path:", csv_path)
    return csv_path


def load_particle_positions(csv_path, *, set_vel_zero = True, set_ang_vel_zero = True):
    """Recreate spheres from a CSV snapshot.

    Materials are looked up by label in
    :data:`~pm_dem_sm.simulation.yade_dem.materials.MATERIALS_MAP`.

    Args:
        csv_path: CSV written by :func:`save_particle_positions` (needs
            ``x, y, z, r, m``; optional velocity columns).
        set_vel_zero: If ``True``, zero linear velocity regardless of CSV.
        set_ang_vel_zero: If ``True``, zero angular velocity regardless of CSV.

    Returns:
        list: YADE body ids of the created spheres.
    """
    created_ids = []

    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)

        has_v = {"vx", "vy", "vz"}.issubset(reader.fieldnames)
        has_w = {"wx", "wy", "wz"}.issubset(reader.fieldnames)

        for row in reader:
            x = float(row["x"])
            y = float(row["y"])
            z = float(row["z"])
            r = float(row["r"])
            mat_label = (row.get("m", "") or "").strip()

            mat = materials.MATERIALS_MAP[mat_label]

            if mat_label == "rock":
                sph_color = (1,0,0)
            else:
                sph_color = (0,0,1)

            bid = O.bodies.append(sphere((x, y, z), r, material=mat, color=sph_color))
            created_ids.append(bid)

            b = O.bodies[bid]

            # Restore velocities unless zeroing was requested or the CSV lacks them.
            if set_vel_zero or not has_v:
                b.state.vel = Vector3(0, 0, 0)
            else:
                b.state.vel = Vector3(
                    float(row["vx"]),
                    float(row["vy"]),
                    float(row["vz"]),
                )

            if set_ang_vel_zero or not has_w:
                b.state.angVel = Vector3(0, 0, 0)
            else:
                b.state.angVel = Vector3(
                    float(row["wx"]),
                    float(row["wy"]),
                    float(row["wz"]),
                )

    return created_ids


def settle_and_save(csv_path, d_small, r_split, max_time_s, **tolerances):
    """Settle undamped by the geometric stop rule, zero all velocities, and save positions.

    The initial-condition protocol of
    docs/scientific_rationale/13_initial_conditions.md (steps 3-5): damping 0
    (checked, V5), settle until the bed geometry is stationary or the time
    cap, then all particles at rest.

    Args:
        csv_path: Destination CSV for :func:`save_particle_positions`.
        d_small: Small-particle diameter (m).
        r_split: Radius threshold separating small from large spheres (m).
        max_time_s: Settling time cap (s).
        **tolerances: Overrides passed to
            :func:`~pm_dem_sm.simulation.yade_dem.monitor.run_until_settled`.

    Returns:
        dict: The settle result (stop reason, window changes, settle time).
    """
    engines.set_gravity_damping(0.0)
    engines.assert_no_damping()
    result = monitor.run_until_settled(d_small, max_time_s, r_split, **tolerances)
    for b in O.bodies:
        if b and isinstance(b.shape, Sphere):
            b.state.vel = Vector3(0, 0, 0)
            b.state.angVel = Vector3(0, 0, 0)
    save_particle_positions(csv_path)
    return result

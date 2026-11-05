"""Particle loading and chord-box ingress of bidisperse rock/steel charges (YADE)."""

from __future__ import annotations

import math
import random

from yade import Vector3, pack
from yade.wrapper import O

from . import stl

# --- Constants ---------------------------------------------------------------

# Solid fraction requested from SpherePack.makeCloud per ingress batch.
_CLOUD_FRACTION = 0.30


# --- Public functions --------------------------------------------------------


def load_rock_particles(rock_diam_m, rock_count):
    """Spawn rock spheres in four vertical regions of the mill slice.

    Args:
        rock_diam_m: Rock particle diameter in meters.
        rock_count: Total number of rock spheres (split across regions).
    """
    rock_sphere_pack_0 = pack.SpherePack()
    rock_sphere_pack_0.makeCloud(minCorner=(-4.5, 1, 0), maxCorner=(4.5, -2, 0.375), rMean=rock_diam_m/2, rRelFuzz=0, num=int(rock_count*0.5))
    rock_sphere_pack_0.toSimulation(material="rock", color=(1,0,0), wire=False)

    rock_sphere_pack_1 = pack.SpherePack()
    rock_sphere_pack_1.makeCloud(minCorner=(-4, -2, 0), maxCorner=(4, -3, 0.375), rMean=rock_diam_m/2, rRelFuzz=0, num=int(rock_count*0.25))
    rock_sphere_pack_1.toSimulation(material="rock", color=(1,0,0), wire=False)

    rock_sphere_pack_2 = pack.SpherePack()
    rock_sphere_pack_2.makeCloud(minCorner=(-3, -3, 0), maxCorner=(3, -4, 0.375), rMean=rock_diam_m/2, rRelFuzz=0, num=int(rock_count*0.15))
    rock_sphere_pack_2.toSimulation(material="rock", color=(1,0,0), wire=False)

    rock_sphere_pack_3 = pack.SpherePack()
    rock_sphere_pack_3.makeCloud(minCorner=(-2, -4, 0), maxCorner=(2, -5, 0.375), rMean=rock_diam_m/2, rRelFuzz=0, num=int(rock_count*0.1))
    rock_sphere_pack_3.toSimulation(material="rock", color=(1,0,0), wire=False)

    message = "Added %s rock particles of %s m diameter to simulation." % (rock_count, rock_diam_m)
    print(message)


def load_ball_particles(ball_diam_m, ball_count):
    """Spawn ``ball_steel`` spheres in four vertical regions of the mill slice.

    Args:
        ball_diam_m: Steel ball diameter in meters.
        ball_count: Total number of ball spheres (split across regions).
    """
    ball_sphere_pack_0 = pack.SpherePack()
    ball_sphere_pack_0.makeCloud(minCorner=(-2.75, 4, 0), maxCorner=(2.75, 5, 0.375), rMean=ball_diam_m/2, rRelFuzz=0, num=int(ball_count*0.1))
    ball_sphere_pack_0.toSimulation(material="ball_steel", color=(0,0,1), wire=False)

    ball_sphere_pack_1 = pack.SpherePack()
    ball_sphere_pack_1.makeCloud(minCorner=(-3.75, 2.5, 0), maxCorner=(3.75, 4, 0.375), rMean=ball_diam_m/2, rRelFuzz=0, num=int(ball_count*0.15))
    ball_sphere_pack_1.toSimulation(material="ball_steel", color=(0,0,1), wire=False)

    ball_sphere_pack_2 = pack.SpherePack()
    ball_sphere_pack_2.makeCloud(minCorner=(-4.25, 0, 0), maxCorner=(4.25, 2.5, 0.375), rMean=ball_diam_m/2, rRelFuzz=0, num=int(ball_count*0.25))
    ball_sphere_pack_2.toSimulation(material="ball_steel", color=(0,0,1), wire=False)

    ball_sphere_pack_3 = pack.SpherePack()
    ball_sphere_pack_3.makeCloud(minCorner=(-4.5, -3, 0), maxCorner=(4.5, 0, 0.375), rMean=ball_diam_m/2, rRelFuzz=0, num=int(ball_count*0.5))
    ball_sphere_pack_3.toSimulation(material="ball_steel", color=(0,0,1), wire=False)

    message = "Added %s ball particles of %s m diameter to simulation." % (ball_count, ball_diam_m)
    print(message)


def load_all_particles(particle_diam_m, particle_count):
    """Spawn white ``ball_steel`` particles across vertical stack regions.

    Args:
        particle_diam_m: Particle diameter in meters.
        particle_count: Total number of particles (split across regions).
    """
    particle_sphere_pack_0 = pack.SpherePack()
    particle_sphere_pack_0.makeCloud(minCorner=(-2.75, 4, 0), maxCorner=(2.75, 5, 0.375), rMean=particle_diam_m/2, rRelFuzz=0, num=int(particle_count*0.05))
    particle_sphere_pack_0.toSimulation(material="ball_steel", color=(1,1,1), wire=False)

    particle_sphere_pack_1 = pack.SpherePack()
    particle_sphere_pack_1.makeCloud(minCorner=(-3.75, 3, 0), maxCorner=(3.75, 4, 0.375), rMean=particle_diam_m/2, rRelFuzz=0, num=int(particle_count*0.1))
    particle_sphere_pack_1.toSimulation(material="ball_steel", color=(1,1,1), wire=False)

    particle_sphere_pack_2 = pack.SpherePack()
    particle_sphere_pack_2.makeCloud(minCorner=(-4.25, 2, 0), maxCorner=(4.25, 3, 0.375), rMean=particle_diam_m/2, rRelFuzz=0, num=int(particle_count*0.15))
    particle_sphere_pack_2.toSimulation(material="ball_steel", color=(1,1,1), wire=False)

    particle_sphere_pack_4 = pack.SpherePack()
    particle_sphere_pack_4.makeCloud(minCorner=(-4.5, 0, 0), maxCorner=(4.5, 2, 0.375), rMean=particle_diam_m/2, rRelFuzz=0, num=int(particle_count*0.2))
    particle_sphere_pack_4.toSimulation(material="ball_steel", color=(1,1,1), wire=False)

    particle_sphere_pack_5 = pack.SpherePack()
    particle_sphere_pack_5.makeCloud(minCorner=(-4.5, 0, 0), maxCorner=(4.5, -2, 0.375), rMean=particle_diam_m/2, rRelFuzz=0, num=int(particle_count*0.2))
    particle_sphere_pack_5.toSimulation(material="ball_steel", color=(1,1,1), wire=False)

    particle_sphere_pack_6 = pack.SpherePack()
    particle_sphere_pack_6.makeCloud(minCorner=(-4.25, -2, 0), maxCorner=(4.25, -3, 0.375), rMean=particle_diam_m/2, rRelFuzz=0, num=int(particle_count*0.15))
    particle_sphere_pack_6.toSimulation(material="ball_steel", color=(1,1,1), wire=False)

    particle_sphere_pack_7 = pack.SpherePack()
    particle_sphere_pack_7.makeCloud(minCorner=(-3.75, -3, 0), maxCorner=(3.75, -4, 0.375), rMean=particle_diam_m/2, rRelFuzz=0, num=int(particle_count*0.1))
    particle_sphere_pack_7.toSimulation(material="ball_steel", color=(1,1,1), wire=False)

    particle_sphere_pack_8 = pack.SpherePack()
    particle_sphere_pack_8.makeCloud(minCorner=(-2.75, -4, 0), maxCorner=(2.75, -5, 0.375), rMean=particle_diam_m/2, rRelFuzz=0, num=int(particle_count*0.05))
    particle_sphere_pack_8.toSimulation(material="ball_steel", color=(1,1,1), wire=False)

    message = "Added %s particles of %s m diameter to simulation." % (particle_count, particle_diam_m)
    print(message)


def ingress_random(diameter, depth, r_small, r_large, n_small, n_large, box_height,
                   material_small, material_large, color_small, color_large,
                   settle_steps=10000, padding=0.1, verbose=True, seed=None,
                   check_batch=None):
    """Ingress bidisperse particles in random mixed batches via chord boxes.

    Each batch packs spheres at ``r_large``, then randomly shrinks a subset to
    ``r_small`` and assigns the small material/color. Settles after every batch.

    Args:
        diameter: Mill diameter used for chord geometry (meters).
        depth: Slice depth in Z (meters).
        r_small: Small-species radius (meters).
        r_large: Large-species radius (meters).
        n_small: Target number of small particles.
        n_large: Target number of large particles.
        box_height: Ingress box height in Y (meters).
        material_small: YADE material label for small particles.
        material_large: YADE material label for large particles.
        color_small: RGB tuple for small particles.
        color_large: RGB tuple for large particles.
        settle_steps: DEM steps to run after each batch.
        padding: Clearance for :func:`pm_dem_sm.simulation.yade_dem.stl.get_surface_y`
            on later batches.
        verbose: If ``True``, print batch progress.
        seed: RNG seed for placement and species assignment; ``None`` draws
            a fresh one each run.
        check_batch: Called with the new body ids of every batch before its
            first step (the V13 overlap check); ``None`` skips it.
    """
    rng = random.Random(seed)
    remaining_small, remaining_large = n_small, n_large
    batch_idx = 0

    while remaining_small > 0 or remaining_large > 0:
        batch_idx += 1
        total_remaining = remaining_small + remaining_large
        valid_y = (diameter / 2.0) * -0.9 if batch_idx == 1 else stl.get_surface_y(padding)
        box = stl.chord_box_3d(diameter, valid_y, box_height, depth)

        box_vol = box["width"] * box["height"] * box["depth"]
        vol_large = (4 / 3) * math.pi * r_large ** 3
        # A random cloud rarely exceeds ~30% solids; makeCloud stops early beyond that.
        batch_n = min(total_remaining, max(1, int(_CLOUD_FRACTION * box_vol / vol_large)))

        sp = pack.SpherePack()
        sp.makeCloud(minCorner=box["min_corner"], maxCorner=box["max_corner"],
                     rMean=r_large, rRelFuzz=0.0, num=batch_n, periodic=False,
                     seed=rng.randrange(2**31))
        new_ids = sp.toSimulation(material=material_large, color=color_large, wire=False)

        # Split by what makeCloud actually placed, not by what was requested.
        frac_small = remaining_small / total_remaining
        n_s = min(remaining_small, round(len(new_ids) * frac_small))
        n_l = min(remaining_large, len(new_ids) - n_s)

        ids_to_shrink = set(rng.sample(list(new_ids), n_s))
        for bid in [i for i in new_ids if i not in ids_to_shrink][n_l:]:
            O.bodies.erase(bid)
        new_ids = [i for i in new_ids if O.bodies[i] is not None]
        for bid in new_ids:
            b = O.bodies[bid]
            if bid in ids_to_shrink:
                b.shape.radius = r_small
                b.material = O.materials[material_small]
                b.shape.color = Vector3(*color_small)
                _reset_sphere_mass(b)
            else:
                b.shape.color = Vector3(*color_large)

        remaining_small -= n_s
        remaining_large -= n_l
        if verbose:
            print(f"[batch {batch_idx}] +{n_s}s +{n_l}L  remaining: ({remaining_small}s, {remaining_large}L)")
        if check_batch is not None:
            check_batch(new_ids)
        O.run(settle_steps, True)

    if verbose:
        print(f"Ingress complete. {batch_idx} batches.")


def ingress_segregated(diameter, depth, r_small, r_large, n_small, n_large, box_height,
                       material_small, material_large, color_small, color_large,
                       settle_steps=10000, padding=0.1, verbose=True, seed=None,
                       check_batch=None):
    """Ingress all small particles first, then all large.

    Same chord-box batching as :func:`ingress_random`, but species are poured
    sequentially (fully segregated charge).

    Args:
        diameter: Mill diameter used for chord geometry (meters).
        depth: Slice depth in Z (meters).
        r_small: Small-species radius (meters).
        r_large: Large-species radius (meters).
        n_small: Target number of small particles.
        n_large: Target number of large particles.
        box_height: Ingress box height in Y (meters).
        material_small: YADE material label for small particles.
        material_large: YADE material label for large particles.
        color_small: RGB tuple for small particles.
        color_large: RGB tuple for large particles.
        settle_steps: DEM steps to run after each batch.
        padding: Clearance for :func:`pm_dem_sm.simulation.yade_dem.stl.get_surface_y`
            on later batches.
        verbose: If ``True``, print batch progress.
        seed: RNG seed for placement and species assignment; ``None`` draws
            a fresh one each run.
        check_batch: Called with the new body ids of every batch before its
            first step (the V13 overlap check); ``None`` skips it.
    """
    rng = random.Random(seed)
    for size_label, r, n_target, material, color in (
        ("SMALL", r_small, n_small, material_small, color_small),
        ("LARGE", r_large, n_large, material_large, color_large),
    ):
        remaining = n_target
        batch_idx = 0

        while remaining > 0:
            batch_idx += 1
            first_small = batch_idx == 1 and size_label == "SMALL"
            valid_y = (diameter / 2.0) * -0.9 if first_small else stl.get_surface_y(padding)
            box = stl.chord_box_3d(diameter, valid_y, box_height, depth)

            box_vol = box["width"] * box["height"] * box["depth"]
            vol_sphere = (4 / 3) * math.pi * r ** 3
            batch_n = min(remaining, max(1, int(_CLOUD_FRACTION * box_vol / vol_sphere)))

            sp = pack.SpherePack()
            sp.makeCloud(minCorner=box["min_corner"], maxCorner=box["max_corner"],
                         rMean=r, rRelFuzz=0.0, num=batch_n, periodic=False,
                         seed=rng.randrange(2**31))
            new_ids = sp.toSimulation(material=material, wire=False)
            for bid in new_ids:
                O.bodies[bid].shape.color = Vector3(*color)

            remaining -= len(new_ids)
            if verbose:
                print(f"[{size_label} batch {batch_idx}] +{len(new_ids)}  remaining: {remaining}")
            if check_batch is not None:
                check_batch(list(new_ids))
            O.run(settle_steps, True)

        if verbose:
            print(f"[{size_label}] done after {batch_idx} batches.")


# --- Private helper functions ------------------------------------------------


def _reset_sphere_mass(b):
    """Recompute mass and inertia of sphere body ``b`` from its radius and material density.

    Needed after changing ``b.shape.radius`` or ``b.material``: YADE sets mass
    and inertia only when the body is created.

    Args:
        b: YADE sphere body.
    """
    r = b.shape.radius
    mass = b.material.density * 4.0 / 3.0 * math.pi * r**3
    b.state.mass = mass
    b.state.inertia = Vector3(1, 1, 1) * (0.4 * mass * r**2)

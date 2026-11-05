"""Save/load particle positions, and settle-then-save (BlazeDEM placeholder).

Mirrors :mod:`pm_dem_sm.simulation.yade_dem.state`'s public API.
"""

from __future__ import annotations


def save_particle_positions(csv_path, include_velocity=True, include_ang_vel=True):
    """Raise ``NotImplementedError`` (BlazeDEM placeholder).

    Reserves the signature of
    :func:`pm_dem_sm.simulation.yade_dem.state.save_particle_positions`.

    Raises:
        NotImplementedError: Always; the BlazeDEM backend is not implemented yet.
    """
    raise NotImplementedError("BlazeDEM backend not yet implemented")


def load_particle_positions(csv_path, *, set_vel_zero=True, set_ang_vel_zero=True):
    """Raise ``NotImplementedError`` (BlazeDEM placeholder).

    Reserves the signature of
    :func:`pm_dem_sm.simulation.yade_dem.state.load_particle_positions`.

    Raises:
        NotImplementedError: Always; the BlazeDEM backend is not implemented yet.
    """
    raise NotImplementedError("BlazeDEM backend not yet implemented")


def settle_and_save(csv_path, d_small, r_split, max_time_s, **tolerances):
    """Raise ``NotImplementedError`` (BlazeDEM placeholder).

    Reserves the signature of
    :func:`pm_dem_sm.simulation.yade_dem.state.settle_and_save`.

    Raises:
        NotImplementedError: Always; the BlazeDEM backend is not implemented yet.
    """
    raise NotImplementedError("BlazeDEM backend not yet implemented")

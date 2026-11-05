"""Contact model, dt, damping and its V5 check, and rotation (BlazeDEM placeholder).

Mirrors :mod:`pm_dem_sm.simulation.yade_dem.engines`'s public API.
"""

from __future__ import annotations

# --- Public functions --------------------------------------------------------


def initialize_engines(contact_model, contact_model_params, rotation_engine=False):
    """Raise ``NotImplementedError`` (BlazeDEM placeholder).

    Reserves the signature of
    :func:`pm_dem_sm.simulation.yade_dem.engines.initialize_engines`.

    Raises:
        NotImplementedError: Always; the BlazeDEM backend is not implemented yet.
    """
    raise NotImplementedError("BlazeDEM backend not yet implemented")


def set_dt(new_dt=None, factor=0.3):
    """Raise ``NotImplementedError`` (BlazeDEM placeholder).

    Reserves the signature of
    :func:`pm_dem_sm.simulation.yade_dem.engines.set_dt`.

    Raises:
        NotImplementedError: Always; the BlazeDEM backend is not implemented yet.
    """
    raise NotImplementedError("BlazeDEM backend not yet implemented")


def set_gravity_damping(new_gravity_damping):
    """Raise ``NotImplementedError`` (BlazeDEM placeholder).

    Reserves the signature of
    :func:`pm_dem_sm.simulation.yade_dem.engines.set_gravity_damping`.

    Raises:
        NotImplementedError: Always; the BlazeDEM backend is not implemented yet.
    """
    raise NotImplementedError("BlazeDEM backend not yet implemented")




def assert_no_damping():
    """Raise ``NotImplementedError`` (BlazeDEM placeholder).

    Reserves the signature of
    :func:`pm_dem_sm.simulation.yade_dem.engines.assert_no_damping`.

    Raises:
        NotImplementedError: Always; the BlazeDEM backend is not implemented yet.
    """
    raise NotImplementedError("BlazeDEM backend not yet implemented")


def rotate_mill_indefinitely(speed_rpm=9):
    """Raise ``NotImplementedError`` (BlazeDEM placeholder).

    Reserves the signature of
    :func:`pm_dem_sm.simulation.yade_dem.engines.rotate_mill_indefinitely`.

    Raises:
        NotImplementedError: Always; the BlazeDEM backend is not implemented yet.
    """
    raise NotImplementedError("BlazeDEM backend not yet implemented")


def rotate_mill_by_degrees(degrees, speed_rpm=9):
    """Raise ``NotImplementedError`` (BlazeDEM placeholder).

    Reserves the signature of
    :func:`pm_dem_sm.simulation.yade_dem.engines.rotate_mill_by_degrees`.

    Raises:
        NotImplementedError: Always; the BlazeDEM backend is not implemented yet.
    """
    raise NotImplementedError("BlazeDEM backend not yet implemented")


def rotate_mill_by_time(virtual_time_seconds, speed_rpm=9):
    """Raise ``NotImplementedError`` (BlazeDEM placeholder).

    Reserves the signature of
    :func:`pm_dem_sm.simulation.yade_dem.engines.rotate_mill_by_time`.

    Raises:
        NotImplementedError: Always; the BlazeDEM backend is not implemented yet.
    """
    raise NotImplementedError("BlazeDEM backend not yet implemented")


# --- Private helper functions ------------------------------------------------


def _get_rotation_engine(label="rotation_engine"):
    """Raise ``NotImplementedError`` (BlazeDEM placeholder).

    Reserves the signature of
    ``pm_dem_sm.simulation.yade_dem.engines._get_rotation_engine``.

    Raises:
        NotImplementedError: Always; the BlazeDEM backend is not implemented yet.
    """
    raise NotImplementedError("BlazeDEM backend not yet implemented")

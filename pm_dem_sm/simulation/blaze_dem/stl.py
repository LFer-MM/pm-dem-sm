"""Mill geometry helpers (BlazeDEM placeholder).

Mirrors :mod:`pm_dem_sm.simulation.yade_dem.stl`'s public API.
"""

from __future__ import annotations

# --- Module state ------------------------------------------------------------

#: Mirrors :data:`pm_dem_sm.simulation.yade_dem.stl.SAG_MILL_SLICE_BODY_GROUP`.
SAG_MILL_SLICE_BODY_GROUP = None


# --- Public functions --------------------------------------------------------


def initialize_parametric_mill(mill, cap_material, liner=None):
    """Raise ``NotImplementedError`` (BlazeDEM placeholder).

    Reserves the signature of
    :func:`pm_dem_sm.simulation.yade_dem.stl.initialize_parametric_mill`.

    Raises:
        NotImplementedError: Always; the BlazeDEM backend is not implemented yet.
    """
    raise NotImplementedError("BlazeDEM backend not yet implemented")


def createBox(x, y, z):
    """Raise ``NotImplementedError`` (BlazeDEM placeholder).

    Reserves the signature of
    :func:`pm_dem_sm.simulation.yade_dem.stl.createBox`.

    Raises:
        NotImplementedError: Always; the BlazeDEM backend is not implemented yet.
    """
    raise NotImplementedError("BlazeDEM backend not yet implemented")


def createFunnel(x, y, z, fx, fy, dy):
    """Raise ``NotImplementedError`` (BlazeDEM placeholder).

    Reserves the signature of
    :func:`pm_dem_sm.simulation.yade_dem.stl.createFunnel`.

    Raises:
        NotImplementedError: Always; the BlazeDEM backend is not implemented yet.
    """
    raise NotImplementedError("BlazeDEM backend not yet implemented")


def chord_box_3d(diameter, y, box_height, depth):
    """Raise ``NotImplementedError`` (BlazeDEM placeholder).

    Reserves the signature of
    :func:`pm_dem_sm.simulation.yade_dem.stl.chord_box_3d`.

    Raises:
        NotImplementedError: Always; the BlazeDEM backend is not implemented yet.
    """
    raise NotImplementedError("BlazeDEM backend not yet implemented")


def get_surface_y(padding=0.1):
    """Raise ``NotImplementedError`` (BlazeDEM placeholder).

    Reserves the signature of
    :func:`pm_dem_sm.simulation.yade_dem.stl.get_surface_y`.

    Raises:
        NotImplementedError: Always; the BlazeDEM backend is not implemented yet.
    """
    raise NotImplementedError("BlazeDEM backend not yet implemented")

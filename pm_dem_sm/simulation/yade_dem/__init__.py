"""YADE backend for the bidisperse SAG mill slice simulation (implemented).

One module per concern: ``materials``, ``stl``, ``engines``, ``particles``,
``state``, ``capture``, ``diagnostics``, ``monitor``, plus the staged
entry-point script ``run_simulation`` driven by a
:class:`~pm_dem_sm.simulation.scenario.SimulationScenario`. Everything here
runs inside YADE's embedded Python interpreter, except ``version`` (YADE
version floor), which is stdlib-only.
"""

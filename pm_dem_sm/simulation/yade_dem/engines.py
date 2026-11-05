"""Contact model, dt/damping, mill rotation, and force-balance settling (YADE).

``PyRunner`` command strings below (e.g. ``"engines._balance_check()"``) are
evaluated by YADE in the top-level running script's global namespace, so
``yade_dem/run_simulation.py`` must import this module unaliased
(``from . import engines``) for the name ``engines`` to resolve there.
"""

from __future__ import annotations

from math import pi

from yade.utils import PWaveTimeStep, unbalancedForce
from yade.wrapper import (
    Bo1_Facet_Aabb,
    Bo1_Sphere_Aabb,
    ForceResetter,
    Ig2_Facet_Sphere_ScGeom,
    Ig2_Sphere_Sphere_ScGeom,
    InsertionSortCollider,
    InteractionLoop,
    Ip2_FrictMat_FrictMat_MindlinPhys,
    Law2_ScGeom_MindlinPhys_Mindlin,
    NewtonIntegrator,
    O,
    PyRunner,
    RotationEngine,
)

from . import stl

# --- Module state ------------------------------------------------------------

#: Shared state for the force-balance monitor (:func:`run_until_forces_balanced`).
BALANCE_STATE = {
    "done": False,
    "threshold": 1e-3,
    "label": "balance_monitor",
    "last_unb": None,
}


# --- Public functions --------------------------------------------------------


def initialize_engines(contact_model, contact_model_params, rotation_engine=False):
    """Build ``O.engines`` for Hertz-Mindlin; optionally add a RotationEngine.

    Args:
        contact_model: ``"hertz_mindlin"``, the only supported law (YADE's
            Cundall-Strack law has no collisional dissipation; see
            docs/scientific_rationale/01_contact_model.md).
        contact_model_params: Must include a ``"restitution"`` MatchMaker (see
            :func:`~pm_dem_sm.simulation.yade_dem.materials.restitution_matchmaker`).
        rotation_engine: If ``True``, append a ``RotationEngine`` labeled
            ``rotation_engine`` using ``stl.SAG_MILL_SLICE_BODY_GROUP``.

    Raises:
        ValueError: If ``contact_model`` is not ``"hertz_mindlin"``.
    """
    if contact_model != "hertz_mindlin":
        raise ValueError(f"Unsupported contact model: {contact_model!r}")

    O.engines = [
        ForceResetter(),
        InsertionSortCollider([Bo1_Sphere_Aabb(), Bo1_Facet_Aabb()], verletDist=.02),
        InteractionLoop(
            [Ig2_Sphere_Sphere_ScGeom(),
            Ig2_Facet_Sphere_ScGeom()],
            [Ip2_FrictMat_FrictMat_MindlinPhys(
                en = contact_model_params["restitution"]
            )],
            [Law2_ScGeom_MindlinPhys_Mindlin()]
        ),
        NewtonIntegrator(damping=0, gravity=(0,-9.81,0), label="newton_integrator"),
    ]

    if rotation_engine:
        O.engines += [RotationEngine(rotateAroundZero=True, zeroPoint=(0,0,0), rotationAxis=(0,0,1), angularVelocity=0, ids=stl.SAG_MILL_SLICE_BODY_GROUP, label="rotation_engine")]

    print("Initialized engines:", O.engines)


def set_dt(new_dt=None, factor=0.3):
    """Set simulation timestep explicitly or from P-wave factor.

    Args:
        new_dt: Explicit timestep in seconds; if falsy, use
            ``factor * PWaveTimeStep()``.
        factor: Safety factor applied to the P-wave critical timestep.
    """
    if new_dt:
        O.dt = new_dt
    else:
        O.dt = factor * PWaveTimeStep()
    print("O.dt set to: ", O.dt)


def set_gravity_damping(new_gravity_damping):
    """Set ``NewtonIntegrator`` damping by label.

    Args:
        new_gravity_damping: Numerical damping coefficient for the engine
            labeled ``newton_integrator``.
    """
    newton_integrator = next(e for e in O.engines if getattr(e, "label", None) == "newton_integrator")
    newton_integrator.damping = new_gravity_damping
    print("Newton Integrator Gravity Damping set to: ", newton_integrator.damping)


def run_until_forces_balanced(threshold=0.001, interval=1000, motion_start_steps=20, wait_chunk=1000, max_chunks=5000):
    """Run until ``unbalancedForce`` falls below ``threshold``.

    Installs a ``PyRunner`` that calls ``_balance_check`` every
    ``interval`` iterations. Returns early when ``BALANCE_STATE["done"]``.

    Args:
        threshold: Maximum unbalanced force ratio considered balanced.
        interval: ``PyRunner`` iteration period for balance checks.
        motion_start_steps: Steps to run before installing the monitor.
        wait_chunk: Steps per wait loop iteration.
        max_chunks: Maximum wait-loop iterations before giving up.

    Returns:
        bool | None: ``True`` if balanced; ``None`` if ``max_chunks`` is
        exhausted without meeting the threshold.
    """
    print("Starting balanced forces monitoring ...")

    BALANCE_STATE["done"] = False
    BALANCE_STATE["threshold"] = threshold

    for e in list(O.engines):
        if getattr(e, "label", None) == BALANCE_STATE["label"]:
            O.engines.remove(e)

    O.run(motion_start_steps, True)

    O.engines += [PyRunner(iterPeriod=interval, command="engines._balance_check()", label=BALANCE_STATE["label"])]

    for k in range(max_chunks):
        if BALANCE_STATE["done"]:
            return True
        O.run(wait_chunk, True)


def rotate_mill_indefinitely(speed_rpm=9):
    """Set ``rotation_engine`` angular velocity from RPM and ``O.run()`` open-ended.

    Args:
        speed_rpm: Mill rotation speed in revolutions per minute.
    """
    rotation_engine = next(e for e in O.engines if getattr(e, "label", None) == "rotation_engine")
    rotation_engine.angularVelocity = float(speed_rpm) * (2*pi) / 60
    O.run()


def rotate_mill_by_degrees(degrees, speed_rpm=9):
    """Rotate the mill for the time matching ``degrees`` at the given RPM.

    Args:
        degrees: Signed rotation angle in degrees (sign sets direction).
        speed_rpm: Absolute rotation speed in RPM.
    """
    rotation_engine = _get_rotation_engine("rotation_engine")

    rpm = abs(float(speed_rpm))
    omega = rpm * (2*pi) / 60.0  # rad/s

    direction = 1.0 if degrees > 0 else -1.0
    rotation_engine.angularVelocity = direction * omega

    t_needed = (abs(float(degrees)) / 360.0) * (60.0 / rpm)  # simulated seconds
    n_steps = int(round(t_needed / O.dt))
    if n_steps > 0:
        O.run(n_steps)


def rotate_mill_by_time(virtual_time_seconds, speed_rpm=9):
    """Run rotation for ``virtual_time_seconds`` of simulation time.

    Args:
        virtual_time_seconds: Signed simulation time in seconds (sign sets
            rotation direction).
        speed_rpm: Absolute rotation speed in RPM.
    """
    rotation_engine = _get_rotation_engine("rotation_engine")

    rpm = abs(float(speed_rpm))
    omega = rpm * (2*pi) / 60.0  # rad/s

    direction = 1.0 if virtual_time_seconds > 0 else -1.0
    rotation_engine.angularVelocity = direction * omega

    n_steps = int(round(abs(float(virtual_time_seconds)) / O.dt))
    if n_steps > 0:
        O.run(n_steps)


# --- Private helper functions ------------------------------------------------


def _get_rotation_engine(label="rotation_engine"):
    """Find a ``RotationEngine`` in ``O.engines`` by label.

    Args:
        label: Engine label to match (default ``"rotation_engine"``).

    Returns:
        RotationEngine: The matching engine instance.

    Raises:
        StopIteration: If no engine with that label exists.
    """
    return next(e for e in O.engines if getattr(e, "label", None) == label)


def _balance_check():
    """Pause the simulation once ``unbalancedForce`` is below threshold (``PyRunner`` hook).

    Updates ``BALANCE_STATE``, removes the monitor engine, and calls
    ``O.pause()`` when balanced.
    """
    unb = unbalancedForce()
    print("UNBALANCED FORCES:", unb)
    BALANCE_STATE["last_unb"] = unb

    if unb < BALANCE_STATE["threshold"]:
        print(f"[balance] BALANCED at iter {O.iter}. UNBALANCED FORCES: {unb:.6g}")
        BALANCE_STATE["done"] = True

        for e in list(O.engines):
            if getattr(e, "label", None) == BALANCE_STATE["label"]:
                O.engines.remove(e)
                break

        O.pause()

"""Contact model, dt, numerical damping (and its V5 check), and mill rotation (YADE).

Settling is in :func:`pm_dem_sm.simulation.yade_dem.monitor.run_until_settled`
(geometric stop rule).
"""

from __future__ import annotations

from math import pi

from yade.utils import PWaveTimeStep
from yade.wrapper import (
    Bo1_Facet_Aabb,
    Bo1_Sphere_Aabb,
    ForceResetter,
    Ig2_Facet_Sphere_ScGeom6D,
    Ig2_Sphere_Sphere_ScGeom6D,
    InsertionSortCollider,
    InteractionLoop,
    Ip2_FrictMat_FrictMat_MindlinPhys,
    Law2_ScGeom_MindlinPhys_Mindlin,
    NewtonIntegrator,
    O,
    RotationEngine,
)

from . import stl

# --- Public functions --------------------------------------------------------


def initialize_engines(contact_model, contact_model_params, rotation_engine=False):
    """Build ``O.engines`` for Hertz-Mindlin with rolling resistance; optionally add a RotationEngine.

    6-DOF geometry (``ScGeom6D``) and ``Law2_ScGeom_MindlinPhys_Mindlin``
    with ``includeMoment=True``: a rolling moment with stiffness ``krot``
    capped at ``eta R_mean |F_n|``, no twisting moment (``ktwist = 0``)
    (docs/scientific_rationale/06_rolling_resistance.md). Energy tracking is
    on (``O.trackEnergy`` and the law's ``calcEnergy``) for the V4 balance
    (docs/scientific_rationale/04_numerical_damping.md).

    Args:
        contact_model: ``"hertz_mindlin"``, the only supported law (YADE's
            Cundall-Strack law has no collisional dissipation; see
            docs/scientific_rationale/01_contact_model.md).
        contact_model_params: Must include ``"restitution"`` and
            ``"friction_angle"`` MatchMakers (see
            :func:`~pm_dem_sm.simulation.yade_dem.materials.pair_matchmaker`),
            ``"rolling_resistance"`` (mu_r, YADE's ``eta``) and
            ``"rolling_stiffness"`` (``krot``, N m/rad).
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
            [Ig2_Sphere_Sphere_ScGeom6D(),
            Ig2_Facet_Sphere_ScGeom6D()],
            [Ip2_FrictMat_FrictMat_MindlinPhys(
                en=contact_model_params["restitution"],
                frictAngle=contact_model_params["friction_angle"],
                eta=contact_model_params["rolling_resistance"],
                krot=contact_model_params["rolling_stiffness"],
                ktwist=0.0,
            )],
            [Law2_ScGeom_MindlinPhys_Mindlin(includeMoment=True, calcEnergy=True)]
        ),
        NewtonIntegrator(damping=0, gravity=(0,-9.81,0), label="newton_integrator"),
    ]
    O.trackEnergy = True

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


def assert_no_damping():
    """Raise unless ``NewtonIntegrator.damping`` is exactly 0 (V5).

    docs/scientific_rationale/04_numerical_damping.md: no artificial damping
    in any stage. Called at the start of every stage.

    Returns:
        float: The damping value (0.0).

    Raises:
        RuntimeError: If the damping is not 0.
    """
    newton = next(e for e in O.engines if getattr(e, "label", None) == "newton_integrator")
    if newton.damping != 0.0:
        raise RuntimeError(f"V5 failed: NewtonIntegrator.damping = {newton.damping}, not 0")
    return float(newton.damping)


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

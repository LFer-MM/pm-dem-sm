r"""V4 side study: which energy terms YADE tracks for the Hertz-Mindlin law (YADE).

Two rock spheres dropped onto a facet floor with the project's contact law
(rolling moment on, damping 0). Prints ``O.energy`` (only ``kinetic`` and
``gravWork`` = potential-energy change) and the law's own accumulators
(normal / shear dashpot dissipation, friction dissipation, elastic energy),
then the residual of the balance. Findings in
docs/scientific_rationale/04_numerical_damping.md (Open items, V4):
the Mindlin terms are attributes of the law, not ``O.energy`` entries;
friction dissipation can be slightly negative in this build; the rolling
moment's plastic dissipation is not tracked at all.

Run from the repository root::

    yadedaily -n -x scripts/validation/energy_probe.py
"""

from yade import FrictMat, MatchMaker, O
from yade.utils import facet, sphere
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
)

O.materials.append(
    FrictMat(density=2850, young=55e9 / 26, poisson=0.25, frictionAngle=0.4636, label="rock")
)
O.bodies.append(facet([(-1, 0, -1), (1, 0, -1), (0, 0, 2)], material="rock", fixed=True))
O.bodies.append(sphere((0, 0.2, 0), 0.035, material="rock"))
O.bodies.append(sphere((0.05, 0.4, 0.01), 0.035, material="rock"))
law = Law2_ScGeom_MindlinPhys_Mindlin(includeMoment=True, calcEnergy=True)
O.engines = [
    ForceResetter(),
    InsertionSortCollider([Bo1_Sphere_Aabb(), Bo1_Facet_Aabb()]),
    InteractionLoop(
        [Ig2_Sphere_Sphere_ScGeom6D(), Ig2_Facet_Sphere_ScGeom6D()],
        [
            Ip2_FrictMat_FrictMat_MindlinPhys(
                en=MatchMaker(matches=[(0, 0, 0.3)]), eta=0.25, krot=39000, ktwist=0
            )
        ],
        [law],
    ),
    NewtonIntegrator(damping=0, gravity=(0, -9.81, 0)),
]
O.dt = 2.5e-5
O.trackEnergy = True
for _ in range(6):
    O.run(8000, True)
    e = dict(O.energy.items())
    print(f"[energy] t = {O.time:.2f} s: O.energy {e}")
diss = law.normDampDissip + law.shearDampDissip + law.frictionDissipation
elastic = law.normElastEnergy() + law.shearEnergy
print(
    f"[energy] law terms: normDampDissip {law.normDampDissip:.5f}, shearDampDissip "
    f"{law.shearDampDissip:.5f}, frictionDissipation {law.frictionDissipation:.5f}, "
    f"normElastEnergy {law.normElastEnergy():.6f}, shearEnergy {law.shearEnergy:.6f}"
)
released = -O.energy["gravWork"]
resid = released - O.energy["kinetic"] - diss - elastic
print(
    f"[energy] released {released:.4f} J = kinetic + dissipated + elastic + residual "
    f"{resid:.4f} J ({100 * resid / released:.1f} %)"
)

r"""Inspect a saved run checkpoint: engines, per-pair contact values, overlaps, escapes (YADE).

Used to verify, from the saved scene itself rather than from the code, what
a run actually simulated (phases 1-4 smoke tests):

- the interaction functors and the moment-law settings (6-DOF geometry,
  ``includeMoment``, ``eta``, ``krot``, ``ktwist``) and the damping;
- the friction (``tan`` of the contact friction angle) and restitution found
  on live contacts, grouped by material pair (per-pair MatchMakers working,
  no fallback to YADE's min rule);
- the largest overlap relative to the smaller diameter, particles outside
  the mill, and the particle speeds (settling);
- with ``--attributes``, the attribute names of one contact's physics and
  geometry (how ``maxBendPl``, ``momentBend`` etc. were found).

Run from the repository root::

    yadedaily -n -x scripts/validation/inspect_checkpoint.py \
        data/raw/yade_runs/<run>/checkpoints/settle.yade.gz --shell-radius 1.03 --depth 0.2
"""

import argparse
import math
import sys

from yade import O
from yade.wrapper import Sphere

p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
p.add_argument("checkpoint")
p.add_argument("--shell-radius", type=float, required=True, help="Inside-shell radius (m).")
p.add_argument("--depth", type=float, required=True, help="Slice depth (m).")
p.add_argument("--attributes", action="store_true")
args = p.parse_args(sys.argv[1:])

O.load(args.checkpoint)
# Contact geometry (penetrationDepth) is not restored by O.load; one step
# recomputes it (the scene moves by one dt).
O.run(1, True)
loop = next(e for e in O.engines if type(e).__name__ == "InteractionLoop")
ip2, law = loop.physDispatcher.functors[0], loop.lawDispatcher.functors[0]
newton = next(e for e in O.engines if type(e).__name__ == "NewtonIntegrator")
print("[inspect] geometry functors:", [type(f).__name__ for f in loop.geomDispatcher.functors])
print(f"[inspect] {type(ip2).__name__}: eta {ip2.eta}, krot {ip2.krot}, ktwist {ip2.ktwist}")
print(f"[inspect] {type(law).__name__}: includeMoment {law.includeMoment}")
print(f"[inspect] damping {newton.damping}, dt {O.dt}, time {O.time}")
print("[inspect] materials:", {i: m.label for i, m in enumerate(O.materials)})

mu, e, worst = {}, {}, 0.0
for i in O.interactions:
    if not i.isReal:
        continue
    b1, b2 = O.bodies[i.id1], O.bodies[i.id2]
    pair = tuple(sorted((b1.material.label, b2.material.label)))
    mu.setdefault(pair, set()).add(round(i.phys.tangensOfFrictionAngle, 4))
    e.setdefault(pair, set()).add(round(ip2.en(b1.material.id, b2.material.id), 4))
    radii = [b.shape.radius for b in (b1, b2) if isinstance(b.shape, Sphere)]
    pen = i.geom.penetrationDepth
    if radii and not math.isnan(pen):
        worst = max(worst, pen / (2 * min(radii)))
print("[inspect] friction by pair:", {k: sorted(v) for k, v in mu.items()})
print("[inspect] restitution by pair:", {k: sorted(v) for k, v in e.items()})
print(f"[inspect] max overlap / smaller diameter: {worst:.4f}")

n, out, vsum, vmax, wmax = 0, 0, 0.0, 0.0, 0.0
for b in O.bodies:
    if not isinstance(b.shape, Sphere):
        continue
    n += 1
    x, y, z = b.state.pos
    if math.hypot(x, y) > args.shell_radius or not 0 <= z <= args.depth:
        out += 1
    v = b.state.vel.norm()
    vsum, vmax, wmax = vsum + v, max(vmax, v), max(wmax, b.state.angVel.norm())
print(
    f"[inspect] spheres {n}, outside the mill {out}, mean speed {vsum / max(n, 1):.3g} m/s, "
    f"max speed {vmax:.3g} m/s, max spin {wmax:.3g} rad/s"
)

if args.attributes:
    i = next(i for i in O.interactions if i.isReal)
    print("[inspect] phys attributes:", [a for a in dir(i.phys) if not a.startswith("_")])
    print("[inspect] geom attributes:", [a for a in dir(i.geom) if not a.startswith("_")])

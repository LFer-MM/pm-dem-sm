r"""Probe the installed YADE build for the API facts the implementation relies on (YADE).

Prints, for the build in use:

- ``yade.config.version`` (C07-3 parses it; daily builds look like
  ``20260115-8983~7c8d01e~noble1``);
- the defaults of ``Ip2_FrictMat_FrictMat_MindlinPhys`` (``eta``, ``krot``,
  ``ktwist`` = 0; ``frictAngle``, ``en``, ``es`` = None, i.e. min rule /
  no restitution) and ``Law2_ScGeom_MindlinPhys_Mindlin`` (``includeMoment``,
  ``calcEnergy`` off);
- that ``MatchMaker`` matches by material **id**, falls back to ``algo``
  (``avg``) for unmatched pairs, and rejects label tuples (C05-2 builds the
  tables from labels and resolves the ids);
- that the 6-DOF geometry functors exist.

Run from the repository root::

    yadedaily -n -x scripts/validation/yade_api_probe.py
"""

import yade
from yade.wrapper import (
    Ig2_Facet_Sphere_ScGeom6D,
    Ig2_Sphere_Sphere_ScGeom6D,
    Ip2_FrictMat_FrictMat_MindlinPhys,
    Law2_ScGeom_MindlinPhys_Mindlin,
    MatchMaker,
)

print("[api] yade.config.version:", repr(getattr(yade.config, "version", None)))
ip2 = Ip2_FrictMat_FrictMat_MindlinPhys()
for name in ("eta", "krot", "ktwist", "frictAngle", "en", "es"):
    print(f"[api] Ip2 default {name}: {getattr(ip2, name)!r}")
law = Law2_ScGeom_MindlinPhys_Mindlin()
print(f"[api] Law2 default includeMoment {law.includeMoment}, calcEnergy {law.calcEnergy}")
print("[api] Law2 energy attributes:", [a for a in dir(law) if "nerg" in a or "Dissip" in a])
mm = MatchMaker(matches=[(0, 1, 0.3)])
print(f"[api] MatchMaker algo {mm.algo!r}, matches {mm.matches}")
try:
    MatchMaker(matches=[("liner", "rock", 0.3)])
    print("[api] MatchMaker accepts label tuples")
except Exception as exc:  # noqa: BLE001
    print(f"[api] MatchMaker rejects label tuples: {type(exc).__name__}")
print("[api] 6-DOF functors:", Ig2_Sphere_Sphere_ScGeom6D(), Ig2_Facet_Sphere_ScGeom6D())

"""Material registration, per-pair ``MatchMaker`` tables and body labeling (YADE)."""

from __future__ import annotations

from yade import FrictMat, MatchMaker
from yade.wrapper import O

# --- Module state ------------------------------------------------------------

#: Registered ``FrictMat`` objects keyed by material label.
MATERIALS_MAP = {}


# --- Public functions --------------------------------------------------------


def initialize_simulation_materials(materials, young_scale=1.0):
    """Register ``FrictMat`` entries into ``O.materials`` and :data:`MATERIALS_MAP`.

    Args:
        materials: Mapping of material name to property dicts with keys
            ``density`` (kg/m^3), ``young`` (Pa), ``poisson``,
            ``friction_angle`` (rad; YADE's fallback for unmatched pairs, see
            :meth:`~pm_dem_sm.simulation.scenario.SimulationScenario.contact_tables`),
            and ``label``.
        young_scale: Multiplier applied to every Young's modulus.
    """
    for material_properties in materials.values():
        m = FrictMat(density=material_properties["density"],
                     young=material_properties["young"] * young_scale,
                     poisson=material_properties["poisson"],
                     frictionAngle=material_properties["friction_angle"],
                     label=material_properties["label"])

        O.materials.append(m)
        MATERIALS_MAP[material_properties["label"]] = m
        print("Added material:", material_properties["label"])


def pair_matchmaker(pairs):
    """Build a ``MatchMaker`` from material-label pairs, resolving YADE material ids.

    Used for restitution (``en``) and friction angles (``frictAngle``); see
    :meth:`~pm_dem_sm.simulation.scenario.SimulationScenario.contact_tables`.

    Args:
        pairs: Iterable of ``(label_a, label_b, value)``; both orders are
            added. Labels must already be registered in ``O.materials``.

    Returns:
        MatchMaker: Pairwise values by material id.
    """
    ids = {m.label: i for i, m in enumerate(O.materials)}
    matches = []
    for a, b, e in pairs:
        matches.append((ids[a], ids[b], float(e)))
        if a != b:
            matches.append((ids[b], ids[a], float(e)))
    return MatchMaker(matches=matches)


def rebuild_materials_map():
    """Refill :data:`MATERIALS_MAP` from ``O.materials`` (after ``O.load``)."""
    MATERIALS_MAP.clear()
    for m in O.materials:
        if m.label:
            MATERIALS_MAP[m.label] = m


# --- Private helper functions ------------------------------------------------


def _mat_label(b):
    """Return the material label of body ``b``, or ``""`` if it has none.

    Args:
        b: YADE body.

    Returns:
        str: Material ``label``, or ``""`` if missing.
    """
    m = getattr(b, "material", None)
    if m is None:
        return ""
    return str(getattr(m, "label", ""))

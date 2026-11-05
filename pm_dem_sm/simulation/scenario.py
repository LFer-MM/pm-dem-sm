"""DEM scenario definition: one JSON file describing a full mill simulation run.

A :class:`SimulationScenario` holds everything a DEM backend needs to build,
fill, settle, spin up, and record a SAG mill slice: geometry, particle
species, materials, contact model, time step, and per-stage settings. It is
backend-agnostic and stdlib-only, so it imports both under the project venv
(CLI, launcher, tests) and under YADE's own interpreter
(:mod:`pm_dem_sm.simulation.yade_dem.run_simulation`).

Defaults come from the DEM constants in :mod:`pm_dem_sm.config`; a scenario
JSON (see ``configs/simulation/``) overrides any subset of them. The derived
checks (:meth:`SimulationScenario.checks`) are plain formulas -- critical
speed, fill level, Rayleigh time step, integration steps per collision -- so
a scenario can be sanity-checked before any DEM time is spent. The defaults
follow the decisions in ``docs/scientific_rationale/``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from pathlib import Path
from typing import Any

from .. import config
from ..config import _from_plain_dict, _to_plain_dict

# --- Constants ---------------------------------------------------------------

#: Pipeline stages run by a DEM backend, in order.
STAGES = ("build", "fill", "settle", "spinup", "record")
#: Valid ``MillGeometry.source`` values.
MILL_SOURCES = ("stl", "parametric")
#: Valid ``MillGeometry.end_walls`` values.
END_WALLS = ("liner", "frictionless")
#: Valid ``ContactOptions.model`` values.
CONTACT_MODELS = ("hertz_mindlin",)
#: Valid ``ContactOptions.particle_friction_set`` values.
PARTICLE_FRICTION_SETS = ("uniform", "owen")
#: Material label given to frictionless end walls; derived from the liner.
END_WALL_MATERIAL = "end_wall"
#: Fewest time steps per rolling oscillation period of the smallest sphere,
#: ``T_r = 2 pi sqrt(I / krot)`` (docs/scientific_rationale/06_rolling_resistance.md).
MIN_STEPS_PER_ROLLING_PERIOD = 20
#: Largest accepted rotation to reach the plastic rolling moment,
#: ``theta_y = mu_r R |F_n| / krot``, at the typical contact force (rad)
#: (docs/scientific_rationale/06_rolling_resistance.md; Ai et al. 2011 §7).
MAX_YIELD_ROTATION_RAD = 0.01
#: Bulk solid fraction assumed for the typical-contact-force estimate.
TYPICAL_PACKING = 0.6
#: Scenario fields with no sourced value yet; runs record them as provisional.
PROVISIONAL_PARAMETERS = {
    "contact.rolling_resistance": (
        "mu_r has no sourced value until the heap test (C06-3) fixes it for a 37 deg "
        "repose angle (docs/scientific_rationale/06_rolling_resistance.md)"
    ),
}
#: Valid ``FillOptions.method`` values.
FILL_METHODS = ("random", "segregated")
#: Standard gravity (m/s^2).
GRAVITY = 9.81
#: Fewest integration steps per collision accepted at the worst-case impact
#: speed (Boemer & Ponthot 2017: 20-70; Cleary 2001: 15-25; see
#: docs/scientific_rationale/02_time_step.md).
MIN_STEPS_PER_COLLISION = 20
#: Young's modulus reduction ``1 / f`` with f = 26
#: (docs/scientific_rationale/03_stiffness_young_modulus.md).
YOUNG_SCALE = 1.0 / 26.0
#: Provisional SAG_A counts for the 0.6 m slice (Jb 18.8 %, Jc 27.6 %), until
#: the grind-out / crash-stop procedure sets them
#: (docs/scientific_rationale/12_charge_fill_and_particles.md).
PROVISIONAL_ROCK_COUNT = 14650
PROVISIONAL_BALL_COUNT = 3750


# --- Public classes ----------------------------------------------------------


@dataclass
class MillGeometry:
    """Mill slice geometry, liner, and drive speed.

    The mill axis is the Z axis through the origin; the slice spans
    ``0 <= z <= depth_m``, and gravity points along ``-Y``.

    Attributes:
        source: ``"stl"`` (load ``stl_path``) or ``"parametric"`` (build a
            shell with lifters from the fields below).
        stl_path: Mill slice STL, used when ``source == "stl"``.
        diameter_m: Inside-liner diameter (m). For ``"stl"`` it must match the
            STL; it sizes the fill boxes and the derived checks.
        depth_m: Slice depth along Z (m); 0.6 m by default
            (docs/scientific_rationale/10_mill_geometry.md).
        speed_rpm: Drive speed (rev/min); positive rotates counter-clockwise
            seen from ``+Z``. Default 9.5, the SAG_A median
            (docs/scientific_rationale/11_mill_speed.md).
        n_shell_segments: Facet segments around the parametric shell.
        n_lifters: Lifter rows on the parametric shell (``0`` = smooth liner).
        lifter_height_m: Lifter height above the shell (m).
        lifter_base_width_m: Lifter width at the shell (m).
        lifter_top_width_m: Lifter width at its top face (m).
        liner_material: Material key (in ``materials``) of shell and lifters;
            ``"liner"`` by default, steel with its own friction mu_w
            (docs/scientific_rationale/05_friction.md).
        end_walls: ``"liner"`` gives the flat slice end walls the liner
            material; ``"frictionless"`` (default) gives them a material
            derived from the liner with zero friction, to limit the wall
            effects of a thin slice.
    """

    source: str = "stl"
    stl_path: Path = Path(config.SAGMILL_STL_PATH)
    diameter_m: float = config.MILL_DIAMETER_M
    depth_m: float = 0.6
    speed_rpm: float = 9.5
    n_shell_segments: int = 120
    n_lifters: int = 0
    lifter_height_m: float = 0.25
    lifter_base_width_m: float = 0.30
    lifter_top_width_m: float = 0.15
    liner_material: str = "liner"
    end_walls: str = "frictionless"


@dataclass
class ContactOptions:
    """Contact law, per-pair friction and rolling resistance.

    Friction is set per material pair (a YADE ``frictAngle`` ``MatchMaker``),
    not per material: particle pairs get ``particle_friction`` (or the Owen
    set), particle-liner pairs ``wall_friction``, particle-end-wall pairs 0
    when the end walls are frictionless
    (docs/scientific_rationale/05_friction.md). See
    :meth:`SimulationScenario.contact_tables`.

    Attributes:
        model: ``"hertz_mindlin"`` (nonlinear, restitution from
            ``restitution``), the only law offered
            (docs/scientific_rationale/01_contact_model.md).
        particle_friction: mu_p, one value for every particle pair.
        wall_friction: mu_w, particle-liner pairs.
        particle_friction_set: ``"uniform"`` (``particle_friction`` for all
            particle pairs) or ``"owen"`` (Owen & Cleary 2015 steel-steel /
            steel-rock / rock-rock 0.4 / 0.5 / 0.8, the sensitivity case).
        rolling_resistance: mu_r, YADE's ``eta`` (plastic rolling moment
            ``mu_r R_mean |F_n|``), one value for all contacts
            (docs/scientific_rationale/06_rolling_resistance.md). **Required**:
            there is no default until the heap test (C06-3) fixes it, and runs
            record it as provisional.
    """

    model: str = "hertz_mindlin"
    particle_friction: float = config.PARTICLE_FRICTION
    wall_friction: float = config.WALL_FRICTION
    particle_friction_set: str = "uniform"
    rolling_resistance: float | None = None


@dataclass
class SolverOptions:
    """Time integration settings.

    Attributes:
        dt_s: Explicit time step (s); 2.5e-5 s by default
            (docs/scientific_rationale/02_time_step.md). ``None`` uses
            ``dt_safety`` times the Rayleigh step of the scenario.
        dt_safety: Fraction of the Rayleigh time step used when ``dt_s`` is
            ``None``.
        young_scale: Multiplier on every material's (physical) Young's
            modulus; default :data:`YOUNG_SCALE` = 1/26. Values below 1 soften
            contacts, which lengthens the contact time (as
            ``young_scale ** -0.4``) at the cost of larger overlaps; the
            manifest records it so runs stay comparable.
        threads: OpenMP threads for the backend (``None`` = backend default).
    """

    dt_s: float | None = 2.5e-5
    dt_safety: float = 0.3
    young_scale: float = YOUNG_SCALE
    threads: int | None = None


@dataclass
class FillOptions:
    """Charge generation (stage ``fill``).

    Numerical damping is 0 in this and every other stage; there is no option
    for it (docs/scientific_rationale/04_numerical_damping.md).

    Attributes:
        method: ``"random"`` (species mixed in every batch) or
            ``"segregated"`` (small species first, then large).
        box_height_m: Height of each chord-box ingress batch (m).
        settle_steps: DEM steps run after each batch.
    """

    method: str = "random"
    box_height_m: float = 1.0
    settle_steps: int = 20000


@dataclass
class SettleOptions:
    """Static settling before rotation (stage ``settle``), undamped.

    Attributes:
        unbalanced_force: Stop once YADE's unbalanced-force ratio is below this.
        check_every: Steps between unbalanced-force checks.
        max_steps: Give up (and continue) after this many steps.
    """

    unbalanced_force: float = 0.01
    check_every: int = 1000
    max_steps: int = 200_000


@dataclass
class SpinupOptions:
    """Rotation from rest until the charge reaches steady state (stage ``spinup``).

    Steady state is declared when, after ``min_revolutions``, the mean charge
    centre-of-mass angle and mean drive power over the last
    ``window_revolutions`` differ from the window before by less than
    ``angle_tol_deg`` and ``power_rel_tol``. Numerical damping is 0, as in
    every stage.

    Attributes:
        min_revolutions: Revolutions run before steady state is tested.
        max_revolutions: Revolutions after which spin-up stops regardless.
        window_revolutions: Length of each comparison window (revolutions).
        angle_tol_deg: Allowed change of mean charge angle between windows.
        power_rel_tol: Allowed relative change of mean power between windows.
    """

    min_revolutions: float = 2.0
    max_revolutions: float = 10.0
    window_revolutions: float = 1.0
    angle_tol_deg: float = 1.0
    power_rel_tol: float = 0.05


@dataclass
class RecordOptions:
    """Frame recording at steady state (stage ``record``).

    Attributes:
        duration_s: Simulated time to record (s).
        frame_interval_s: Simulated time between frame CSVs (s).
        monitor_interval_s: Simulated time between mill-log rows (s), in
            every stage from ``fill`` on.
    """

    duration_s: float = 20.0
    frame_interval_s: float = 0.05
    monitor_interval_s: float = 0.05


@dataclass
class Species:
    """One particle species of the charge.

    Attributes:
        name: Species name (e.g. ``"rock"``, ``"ball"``).
        material: Material key in ``SimulationScenario.materials``; written
            as the ``m`` column of every frame.
        radius_m: Sphere radius (m).
        count: Number of particles.
        color: RGB triple for the YADE viewer.
    """

    name: str
    material: str
    radius_m: float
    count: int
    color: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])

    @property
    def volume_m3(self) -> float:
        """Total solid volume of this species (m^3)."""
        return self.count * 4.0 / 3.0 * math.pi * self.radius_m**3


@dataclass
class SimulationScenario:
    """A complete, reproducible DEM run of the mill slice.

    Attributes:
        name: Scenario name; default run directory name.
        seed: RNG seed for particle placement.
        mill: Geometry, liner, and speed.
        species: Particle species; the fill stage supports exactly two
            (small and large).
        materials: Material properties keyed by material name (same shape
            as :data:`pm_dem_sm.config.MATERIALS`).
        restitution: Pairwise restitution ``[material_a, material_b, e]``.
        contact: Contact law.
        solver: Time step, stiffness scaling, threads.
        fill: Fill-stage settings.
        settle: Settle-stage settings.
        spinup: Spin-up stage settings.
        record: Record-stage settings.
    """

    name: str = "sag_slice"
    seed: int = 0
    mill: MillGeometry = field(default_factory=MillGeometry)
    species: list[Species] = field(default_factory=lambda: _default_species())
    materials: dict[str, dict[str, Any]] = field(
        default_factory=lambda: {k: dict(v) for k, v in config.MATERIALS.items()}
    )
    restitution: list[list[Any]] = field(
        default_factory=lambda: [[a, b, e] for (a, b), e in config.RESTITUTION_COEFFICIENTS.items()]
    )
    contact: ContactOptions = field(default_factory=ContactOptions)
    solver: SolverOptions = field(default_factory=SolverOptions)
    fill: FillOptions = field(default_factory=FillOptions)
    settle: SettleOptions = field(default_factory=SettleOptions)
    spinup: SpinupOptions = field(default_factory=SpinupOptions)
    record: RecordOptions = field(default_factory=RecordOptions)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SimulationScenario:
        """Build a scenario from a mapping such as parsed JSON; unknown keys raise.

        Args:
            data: Mapping of field names to values; nested groups are objects
                and ``species`` is a list of objects.

        Returns:
            SimulationScenario: The coerced scenario, validated.

        Raises:
            ValueError: If a key is unknown or :meth:`validate` fails.
        """
        data = dict(data)
        species = data.pop("species", None)
        scenario = _from_plain_dict(cls, data)
        if species is not None:
            scenario.species = [_from_plain_dict(Species, s) for s in species]
        scenario.validate()
        return scenario

    @classmethod
    def from_json(cls, path: Path | str) -> SimulationScenario:
        """Load a scenario from a JSON file.

        Args:
            path: JSON object whose keys are :class:`SimulationScenario` fields.

        Returns:
            SimulationScenario: Scenario built via :meth:`from_dict`.
        """
        with Path(path).open(encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-ready plain types (paths become strings).

        Returns:
            dict[str, Any]: Field name to value; round-trips through
            :meth:`from_dict`.
        """
        species = [_to_plain_dict(s) for s in self.species]
        out = _to_plain_dict(self)
        out["species"] = species
        return out

    def validate(self) -> None:
        """Check enumerated fields and cross-references.

        Raises:
            ValueError: On an unknown option value, a species or liner whose
                material is not in ``materials``, a material that still
                carries a per-material ``friction_angle``, a restitution pair
                (particle-particle or particle-liner) that is missing, an
                Owen friction set without steel / rock species, a missing or
                negative ``contact.rolling_resistance``, or a species count
                other than two.
        """
        _check_choice("mill.source", self.mill.source, MILL_SOURCES)
        _check_choice("mill.end_walls", self.mill.end_walls, END_WALLS)
        _check_choice("contact.model", self.contact.model, CONTACT_MODELS)
        _check_choice(
            "contact.particle_friction_set",
            self.contact.particle_friction_set,
            PARTICLE_FRICTION_SETS,
        )
        _check_choice("fill.method", self.fill.method, FILL_METHODS)
        if len(self.species) != 2:
            raise ValueError(f"Exactly two species are supported, got {len(self.species)}")
        used = {s.material for s in self.species} | {self.mill.liner_material}
        missing = used - set(self.materials)
        if missing:
            raise ValueError(f"Materials not defined in 'materials': {sorted(missing)}")
        if self.mill.liner_material in {s.material for s in self.species}:
            raise ValueError(
                f"mill.liner_material {self.mill.liner_material!r} is also a particle material; "
                "the liner needs its own material so mu_w is independent of mu_p"
            )
        with_angle = sorted(k for k, m in self.materials.items() if "friction_angle" in m)
        if with_angle:
            raise ValueError(
                f"Materials {with_angle} set 'friction_angle'; friction is set per pair in "
                "'contact' (particle_friction, wall_friction)"
            )
        pairs = {frozenset((a, b)) for a, b, _ in self.restitution}
        for a, b in self._contact_pairs():
            if frozenset((a, b)) not in pairs:
                raise ValueError(f"No restitution coefficient for pair ({a}, {b})")
        if self.contact.particle_friction_set == "owen":
            owen = {frozenset(k) for k in config.OWEN_PARTICLE_FRICTION}
            for a, b in self._particle_pairs():
                if frozenset((a, b)) not in owen:
                    raise ValueError(f"No Owen friction coefficient for pair ({a}, {b})")
        mu_r = self.contact.rolling_resistance
        if mu_r is None:
            raise ValueError(
                "contact.rolling_resistance (mu_r) is required: "
                + PROVISIONAL_PARAMETERS["contact.rolling_resistance"]
            )
        if mu_r < 0:
            raise ValueError(f"contact.rolling_resistance must be >= 0, got {mu_r}")
        if self.mill.n_lifters and self.lifter_gap_m <= 0:
            raise ValueError("Lifters overlap: reduce n_lifters or lifter_base_width_m")

    @property
    def small(self) -> Species:
        """The species with the smaller radius."""
        return min(self.species, key=lambda s: s.radius_m)

    @property
    def large(self) -> Species:
        """The species with the larger radius."""
        return max(self.species, key=lambda s: s.radius_m)

    @property
    def lifter_gap_m(self) -> float:
        """Free arc length between neighbouring lifter bases at the shell (m)."""
        if not self.mill.n_lifters:
            return math.inf
        pitch = math.pi * self.mill.diameter_m / self.mill.n_lifters
        return pitch - self.mill.lifter_base_width_m

    def restitution_for(self, a: str, b: str) -> float:
        """Return the restitution coefficient of material pair ``(a, b)``, in either order.

        Args:
            a: First material name.
            b: Second material name.

        Returns:
            float: Coefficient of restitution.

        Raises:
            KeyError: If the pair is not in ``restitution``.
        """
        for x, y, e in self.restitution:
            if {x, y} == {a, b}:
                return float(e)
        raise KeyError((a, b))

    def friction_for(self, a: str, b: str) -> float:
        """Return the friction coefficient of material pair ``(a, b)``, in either order.

        Particle pairs get ``contact.particle_friction`` (or the Owen value),
        particle-liner pairs ``contact.wall_friction``, and pairs with the
        frictionless end-wall material 0.

        Args:
            a: First material name.
            b: Second material name.

        Returns:
            float: Friction coefficient mu (not an angle).

        Raises:
            KeyError: If ``(a, b)`` is not a particle-particle, particle-liner
                or particle-end-wall pair.
        """
        particles = {s.material for s in self.species}
        pair = {a, b}
        if pair <= particles:
            if self.contact.particle_friction_set == "owen":
                for (x, y), mu in config.OWEN_PARTICLE_FRICTION.items():
                    if {x, y} == pair:
                        return float(mu)
                raise KeyError((a, b))
            return float(self.contact.particle_friction)
        for wall, mu in (
            (self.mill.liner_material, self.contact.wall_friction),
            (END_WALL_MATERIAL, 0.0),
        ):
            if wall in pair and (pair - {wall} <= particles) and len(pair) == 2:
                return float(mu)
        raise KeyError((a, b))

    def contact_tables(self) -> dict[str, Any]:
        """Return the materials and per-pair tables the backend registers.

        Adds the frictionless end-wall material (a copy of the liner) when
        ``mill.end_walls == "frictionless"``, with the liner's restitution.
        Friction is returned as angles in radians, ``atan(mu)``, for YADE's
        ``frictAngle`` ``MatchMaker``; every material also gets the matching
        ``friction_angle`` (YADE's fallback for unmatched pairs, which do not
        occur). Pairs cover every particle-particle and particle-wall
        combination, each once (unordered).

        Returns:
            dict[str, Any]: ``materials`` (name -> properties incl.
            ``friction_angle``), ``restitution`` and ``friction`` (lists of
            ``[material_a, material_b, value]``), and ``cap_material`` (the
            end walls' material).
        """
        liner = self.mill.liner_material
        materials = {k: dict(v) for k, v in self.materials.items()}
        walls = [liner]
        cap_material = liner
        if self.mill.end_walls == "frictionless":
            cap_material = END_WALL_MATERIAL
            materials[END_WALL_MATERIAL] = dict(materials[liner], label=END_WALL_MATERIAL)
            walls.append(END_WALL_MATERIAL)
        particles = sorted({s.material for s in self.species})
        for name, props in materials.items():
            if name in particles:
                mu = self.contact.particle_friction
            elif name == liner:
                mu = self.contact.wall_friction
            else:
                mu = 0.0
            props["friction_angle"] = math.atan(mu)
        restitution, friction = [], []
        for a, b in self._particle_pairs() + [(p, w) for w in walls for p in particles]:
            e_pair = (a, liner) if b == END_WALL_MATERIAL else (a, b)
            restitution.append([a, b, self.restitution_for(*e_pair)])
            friction.append([a, b, math.atan(self.friction_for(a, b))])
        return {
            "materials": materials,
            "restitution": restitution,
            "friction": friction,
            "cap_material": cap_material,
        }

    def rolling_stiffness(self) -> float:
        """Return ``krot`` (N m/rad): the stiffest the time step resolves.

        Sized on the smallest sphere so that its rolling oscillation period,
        ``T_r = 2 pi sqrt(I / krot)`` with ``I = (2/5) m r^2``, is exactly
        :data:`MIN_STEPS_PER_ROLLING_PERIOD` time steps -- "as high as
        numerical stability allows" (Wensrich & Katterfeld 2012, §2; see
        docs/scientific_rationale/06_rolling_resistance.md).

        Returns:
            float: Rolling stiffness ``krot``.
        """
        s = self.small
        mass = self.materials[s.material]["density"] * 4.0 / 3.0 * math.pi * s.radius_m**3
        inertia = 0.4 * mass * s.radius_m**2
        omega = 2.0 * math.pi / (MIN_STEPS_PER_ROLLING_PERIOD * self.time_step_s())
        return inertia * omega**2

    def rolling_period_steps(self, krot: float) -> float:
        """Return the smallest sphere's rolling period ``2 pi sqrt(I / krot)`` in time steps."""
        s = self.small
        mass = self.materials[s.material]["density"] * 4.0 / 3.0 * math.pi * s.radius_m**3
        inertia = 0.4 * mass * s.radius_m**2
        return 2.0 * math.pi * math.sqrt(inertia / krot) / self.time_step_s()

    def typical_contact_force_n(self) -> float:
        """Return a typical (high-end) static contact force on a small sphere (N).

        The weight of a column of bulk charge, as deep as the static bed,
        standing on one small-particle cross-section ``(2 r_small)^2``:
        ``F = phi rho_s g h (2 r_small)^2`` with phi = :data:`TYPICAL_PACKING`,
        ``rho_s`` the mean solid density of the charge and ``h`` the depth of
        a flat bed holding the fill fraction :meth:`fill_fraction`. An order
        of magnitude for the yield-rotation check, not a measurement.

        Returns:
            float: Force (N).
        """
        mass = sum(self.materials[s.material]["density"] * s.volume_m3 for s in self.species)
        rho_solid = mass / sum(s.volume_m3 for s in self.species)
        r_mill = self.mill.diameter_m / 2.0
        target = min(self.fill_fraction(TYPICAL_PACKING), 1.0) * math.pi * r_mill**2
        lo, hi = 0.0, 2.0 * r_mill
        for _ in range(60):
            h = 0.5 * (lo + hi)
            c = r_mill - h
            area = r_mill**2 * math.acos(c / r_mill) - c * math.sqrt(max(0.0, r_mill**2 - c**2))
            lo, hi = (h, hi) if area < target else (lo, h)
        h = 0.5 * (lo + hi)
        return TYPICAL_PACKING * rho_solid * GRAVITY * h * (2.0 * self.small.radius_m) ** 2

    def yield_rotation_rad(self, krot: float, force_n: float | None = None) -> float:
        """Return the rotation to reach the plastic rolling moment, ``mu_r R F / krot`` (rad).

        For two small spheres (``R_mean = r_small``) at ``force_n``, by
        default :meth:`typical_contact_force_n`.

        Args:
            krot: Rolling stiffness (N m/rad).
            force_n: Normal contact force (N).

        Returns:
            float: Yield rotation theta_y (rad).
        """
        force = self.typical_contact_force_n() if force_n is None else force_n
        mu_r = self.contact.rolling_resistance or 0.0
        return mu_r * self.small.radius_m * force / krot

    def check_rolling_stiffness(self, krot: float) -> None:
        """Raise unless ``krot`` meets both criteria of the rolling-resistance decision.

        ``T_r >= MIN_STEPS_PER_ROLLING_PERIOD`` steps for the smallest sphere,
        and ``theta_y <= MAX_YIELD_ROTATION_RAD`` at the typical contact force
        (docs/scientific_rationale/06_rolling_resistance.md).

        Args:
            krot: Rolling stiffness to check (N m/rad).

        Raises:
            ValueError: If either criterion fails.
        """
        steps = self.rolling_period_steps(krot)
        # Allow round-off when krot is exactly at the limit.
        if steps < MIN_STEPS_PER_ROLLING_PERIOD * (1.0 - 1e-9):
            raise ValueError(
                f"krot = {krot:.4g} N m/rad gives a rolling period of {steps:.1f} steps "
                f"(< {MIN_STEPS_PER_ROLLING_PERIOD}) for the smallest sphere"
            )
        theta = self.yield_rotation_rad(krot)
        if theta > MAX_YIELD_ROTATION_RAD:
            raise ValueError(
                f"krot = {krot:.4g} N m/rad needs {theta:.3g} rad to reach the plastic rolling "
                f"moment at the typical contact force (> {MAX_YIELD_ROTATION_RAD} rad)"
            )

    def provisional_parameters(self) -> dict[str, Any]:
        """Return the provisional (unsourced) parameters of this scenario with their values.

        Returns:
            dict[str, Any]: Field path -> ``{"value": ..., "note": ...}``.
        """
        return {
            "contact.rolling_resistance": {
                "value": self.contact.rolling_resistance,
                "note": PROVISIONAL_PARAMETERS["contact.rolling_resistance"],
            }
        }

    def _particle_pairs(self) -> list[tuple[str, str]]:
        """Return every unordered pair of particle materials, each once."""
        mats = sorted({s.material for s in self.species})
        return [(a, b) for i, a in enumerate(mats) for b in mats[i:]]

    def _contact_pairs(self) -> list[tuple[str, str]]:
        """Return particle-particle and particle-liner material pairs (restitution needed)."""
        mats = sorted({s.material for s in self.species})
        return self._particle_pairs() + [(m, self.mill.liner_material) for m in mats]

    def critical_speed_rpm(self) -> float:
        """Return the mill critical speed (rev/min) for the large species.

        ``N_c = (60 / 2 pi) sqrt(g / (R - r_large))``, i.e. the classic
        ``42.3 / sqrt(D - d)`` with ``D`` and ``d`` in meters.

        Returns:
            float: Critical speed (rev/min).
        """
        r_eff = self.mill.diameter_m / 2.0 - self.large.radius_m
        return 60.0 / (2.0 * math.pi) * math.sqrt(GRAVITY / r_eff)

    def fill_fraction(self, packing: float = 0.6) -> float:
        """Return the charge filling ``J`` (bulk charge volume / mill slice volume).

        Args:
            packing: Assumed solid fraction of the bulk charge.

        Returns:
            float: ``J`` in ``[0, 1]`` (lifter volume neglected).
        """
        solids = sum(s.volume_m3 for s in self.species)
        mill = math.pi * (self.mill.diameter_m / 2.0) ** 2 * self.mill.depth_m
        return solids / packing / mill

    def rayleigh_dt_s(self) -> float:
        """Return the smallest Rayleigh critical time step over all species (s).

        ``dt_R = pi r sqrt(rho / G) / (0.1631 nu + 0.8766)`` with
        ``G = E young_scale / (2 (1 + nu))``. Uses the scenario's materials, so
        it can be checked before building the scene.

        Returns:
            float: Rayleigh time step (s).
        """
        out = math.inf
        for s in self.species:
            m = self.materials[s.material]
            nu = m["poisson"]
            shear = m["young"] * self.solver.young_scale / (2.0 * (1.0 + nu))
            dt = math.pi * s.radius_m * math.sqrt(m["density"] / shear) / (0.1631 * nu + 0.8766)
            out = min(out, dt)
        return out

    def time_step_s(self) -> float:
        """Return the time step the run uses (s): ``dt_s``, else ``dt_safety`` x Rayleigh."""
        return self.solver.dt_s or self.solver.dt_safety * self.rayleigh_dt_s()

    def impact_speed_m_s(self) -> float:
        """Return the worst-case impact speed ``sqrt(2 g D)`` (m/s).

        Free fall across the mill, Boemer & Ponthot (2017, §3.1.2); see
        docs/scientific_rationale/02_time_step.md.
        """
        return math.sqrt(2.0 * GRAVITY * self.mill.diameter_m)

    def contact_time_s(self, a: Species, b: Species, speed_m_s: float) -> float:
        """Return the Hertz elastic impact duration of a sphere pair (s).

        ``t_c = 2.87 (m*^2 / (R* E*^2 v))^(1/5)`` (Johnson 1985, Eq. 11.24),
        with ``1/m* = 1/m_a + 1/m_b``, ``1/R* = 1/r_a + 1/r_b`` and
        ``1/E* = (1 - nu_a^2)/E_a + (1 - nu_b^2)/E_b``, the moduli scaled by
        ``solver.young_scale``.

        Args:
            a: First species.
            b: Second species.
            speed_m_s: Normal impact speed (m/s).

        Returns:
            float: Contact duration (s).
        """
        mats = [self.materials[s.material] for s in (a, b)]
        masses = [m["density"] * 4.0 / 3.0 * math.pi * s.radius_m**3 for m, s in zip(mats, (a, b))]
        m_eff = 1.0 / sum(1.0 / m for m in masses)
        r_eff = 1.0 / (1.0 / a.radius_m + 1.0 / b.radius_m)
        e_eff = 1.0 / sum(
            (1.0 - m["poisson"] ** 2) / (m["young"] * self.solver.young_scale) for m in mats
        )
        return 2.87 * (m_eff**2 / (r_eff * e_eff**2 * speed_m_s)) ** 0.2

    def steps_per_collision(self) -> dict[str, float]:
        """Return integration steps per collision for every species pair.

        The Hertz contact time (:meth:`contact_time_s`) at the worst-case
        impact speed (:meth:`impact_speed_m_s`) divided by
        :meth:`time_step_s`; the governing time-step criterion of
        docs/scientific_rationale/02_time_step.md (>= 20 steps per pair).

        Returns:
            dict[str, float]: ``"<species>-<species>"`` to steps per collision.
        """
        v, dt = self.impact_speed_m_s(), self.time_step_s()
        out = {}
        for i, a in enumerate(self.species):
            for b in self.species[i:]:
                out[f"{a.name}-{b.name}"] = self.contact_time_s(a, b, v) / dt
        return out

    def revolution_s(self) -> float:
        """Return the duration of one mill revolution (s)."""
        return 60.0 / abs(self.mill.speed_rpm)

    def checks(self) -> dict[str, float]:
        """Return derived quantities used to sanity-check a scenario.

        Returns:
            dict[str, float]: ``critical_speed_rpm``, ``fraction_critical``,
            ``fill_fraction_J``, ``ball_volume_fraction``, ``dt_s``
            (:meth:`time_step_s`), ``rayleigh_dt_s``, ``dt_over_rayleigh``,
            ``impact_speed_m_s``, ``min_steps_per_collision`` (fewest over the
            species pairs of :meth:`steps_per_collision`), ``rolling_stiffness``
            (``krot``, :meth:`rolling_stiffness`), ``rolling_period_steps``,
            ``typical_contact_force_n``, ``yield_rotation_rad``,
            ``revolution_s``, ``lifter_gap_over_large_d``.
        """
        nc = self.critical_speed_rpm()
        dt_r = self.rayleigh_dt_s()
        dt = self.time_step_s()
        krot = self.rolling_stiffness()
        solids = sum(s.volume_m3 for s in self.species)
        return {
            "critical_speed_rpm": nc,
            "fraction_critical": abs(self.mill.speed_rpm) / nc,
            "fill_fraction_J": self.fill_fraction(),
            "ball_volume_fraction": self.large.volume_m3 / solids,
            "dt_s": dt,
            "rayleigh_dt_s": dt_r,
            "dt_over_rayleigh": dt / dt_r,
            "impact_speed_m_s": self.impact_speed_m_s(),
            "min_steps_per_collision": min(self.steps_per_collision().values()),
            "rolling_stiffness": krot,
            "rolling_period_steps": self.rolling_period_steps(krot),
            "typical_contact_force_n": self.typical_contact_force_n(),
            "yield_rotation_rad": self.yield_rotation_rad(krot),
            "revolution_s": self.revolution_s(),
            "lifter_gap_over_large_d": self.lifter_gap_m / (2.0 * self.large.radius_m),
        }

    def warnings(self) -> list[str]:
        """Return human-readable warnings for physically doubtful settings.

        Returns:
            list[str]: One message per problem; empty when nothing stands out.
        """
        c = self.checks()
        out = []
        for pair, steps in self.steps_per_collision().items():
            if steps < MIN_STEPS_PER_COLLISION:
                out.append(
                    f"{pair} collisions get {steps:.1f} steps at the worst-case impact speed "
                    f"{c['impact_speed_m_s']:.1f} m/s (dt = {c['dt_s']:.3g} s); at least "
                    f"{MIN_STEPS_PER_COLLISION} are needed (lower dt or young_scale)."
                )
        if not 0.6 <= c["fraction_critical"] <= 0.85:
            out.append(
                f"Speed is {100 * c['fraction_critical']:.0f}% of critical; SAG mills "
                "usually run at 70-80%."
            )
        if not 0.15 <= c["fill_fraction_J"] <= 0.40:
            out.append(f"Fill level J = {c['fill_fraction_J']:.2f} is outside 0.15-0.40.")
        if self.mill.source == "parametric" and self.mill.n_lifters == 0:
            out.append("Smooth liner (no lifters): charge lift relies on wall friction alone.")
        elif c["lifter_gap_over_large_d"] < 2.0:
            out.append("Gap between lifters is under two large-particle diameters (packing risk).")
        if self.mill.depth_m < 4 * 2 * self.large.radius_m and self.mill.end_walls == "liner":
            out.append(
                "Slice is under 4 large diameters deep with frictional end walls; "
                "consider end_walls='frictionless'."
            )
        if not math.isclose(self.solver.young_scale, YOUNG_SCALE):
            out.append(
                f"Young's moduli scaled by {self.solver.young_scale:g}, not the decided "
                f"1/26 = {YOUNG_SCALE:.4g}."
            )
        return out


# --- Public functions --------------------------------------------------------


def load_scenario(path: Path | str | None = None) -> SimulationScenario:
    """Load a scenario JSON, or return the defaults when ``path`` is ``None``.

    Args:
        path: Scenario JSON path, or ``None``.

    Returns:
        SimulationScenario: The loaded (or default) scenario.
    """
    if path is None:
        return SimulationScenario()
    return SimulationScenario.from_json(path)


# --- Private helper functions ------------------------------------------------


def _default_species() -> list[Species]:
    """Build the bidisperse rock/steel charge with the provisional SAG_A counts."""
    r_rock, r_ball = config.ROCK_DIAM_M / 2.0, config.BALL_DIAM_M / 2.0
    return [
        Species("rock", "rock", r_rock, PROVISIONAL_ROCK_COUNT, [1.0, 0.0, 0.0]),
        Species("ball", "steel", r_ball, PROVISIONAL_BALL_COUNT, [0.0, 0.0, 1.0]),
    ]


def _check_choice(name: str, value: str, choices: tuple[str, ...]) -> None:
    """Raise ``ValueError`` unless ``value`` is one of ``choices``."""
    if value not in choices:
        raise ValueError(f"{name} must be one of {choices}, got {value!r}")

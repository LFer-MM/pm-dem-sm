"""Mill-state log, contact diagnostics and settling / steady-state detection (YADE).

A ``PyRunner`` appends one row to ``mill_log.csv`` every monitor interval
(``revolutions`` counts from the start of the current stage):

- the charge centre-of-mass angle (all particles and per species) and height,
  the mean particle speed and the kinetic energy;
- the torque the charge exerts on the mill and the matching drive power;
- overlap mean / P99 / max relative to the smaller **diameter**
  (docs/scientific_rationale/03_stiffness_young_modulus.md, V3);
- the P99 normal relative speed of contacts that formed during the last
  step, a sample of impact speeds (docs/scientific_rationale/02_time_step.md,
  V2); all such samples of a stage are kept for its summary;
- the energy terms of the V4 balance: gravitational potential
  (``O.energy["gravWork"]``), elastic energy and cumulative contact
  dissipation of the Hertz-Mindlin law (``calcEnergy``);
- YADE's unbalanced-force ratio (information only).

Spin-up uses the in-memory copy of the log to decide when the charge has
reached steady state; the settle stage uses :func:`run_until_settled`.

Angles are measured from straight down (``-Y``), positive toward ``+X``: a
mill turning counter-clockwise seen from ``+Z`` lifts its charge to positive
angles.

The ``PyRunner`` command string below is evaluated by YADE in the top-level
running script's global namespace, so ``yade_dem/run_simulation.py`` must
import this module unaliased (``from ... import monitor``).
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

from yade import Sphere
from yade.utils import kineticEnergy, unbalancedForce
from yade.wrapper import O, PyRunner

from .. import checks

# --- Constants ---------------------------------------------------------------

#: Angular bin width of the liner contact-force log (deg).
LINER_BIN_DEG = 5
#: Columns of ``mill_log.csv``, in order.
LOG_COLUMNS = [
    "time",
    "iter",
    "stage",
    "revolutions",
    "angle_all_deg",
    "angle_small_deg",
    "angle_large_deg",
    "com_height_m",
    "mean_speed_m_s",
    "kinetic_J",
    "torque_Nm",
    "power_kW",
    "overlap_mean_rel_d",
    "overlap_p99_rel_d",
    "overlap_max_rel_d",
    "impact_v_p99_m_s",
    "potential_J",
    "elastic_J",
    "dissipated_J",
    "rolling_dissipated_J",
    "unbalanced",
]


# --- Module state ------------------------------------------------------------

#: Monitor configuration, the in-memory log rows and the stage's impact speeds.
MONITOR_STATE = {"rows": [], "impact_speeds": []}


# --- Public functions --------------------------------------------------------


def start_monitor(
    log_path, interval, mill_ids, r_split, omega, stage, runner_label="monitor", liner_ids=None
):
    """Append a ``PyRunner`` that logs the mill state every ``interval`` seconds.

    Appends to ``log_path`` if it exists (resumed runs keep one log). With
    ``liner_ids``, each row also appends the liner contact-force distribution
    to ``liner_forces.csv`` beside the log (see :func:`liner_force_histogram`).

    Args:
        log_path: CSV path of the mill log.
        interval: Simulated time between rows (s).
        mill_ids: Body ids of the mill liner and end walls.
        r_split: Radius threshold separating small from large spheres (m).
        omega: Mill angular velocity (rad/s); converts torque to power.
        stage: Stage name written in the ``stage`` column.
        runner_label: Label for the ``PyRunner`` engine.
        liner_ids: Body ids of the liner facets (shell and lifters), or ``None``.

    Returns:
        PyRunner: The appended runner.
    """
    stop_monitor(runner_label)
    MONITOR_STATE["liner_ids"] = list(liner_ids) if liner_ids else []
    MONITOR_STATE["liner_path"] = str(Path(log_path).with_name("liner_forces.csv"))
    if MONITOR_STATE["liner_ids"] and not Path(MONITOR_STATE["liner_path"]).exists():
        with open(MONITOR_STATE["liner_path"], "w", newline="") as f:
            csv.writer(f).writerow(
                ["time", "stage"] + [f"f_{k * LINER_BIN_DEG}" for k in range(360 // LINER_BIN_DEG)]
            )
    MONITOR_STATE.update(
        {
            "path": str(log_path),
            "mill_ids": list(mill_ids),
            "r_split": float(r_split),
            "omega": float(omega),
            "stage": stage,
            "rows": [],
            "impact_speeds": [],
            "rolling_J": 0.0,
            "t0": float(O.time),
        }
    )
    MONITOR_STATE.pop("rolling_last", None)
    try:
        with open(log_path, newline="") as f:
            header = f.readline().strip()
    except FileNotFoundError:
        header = ""
    if header != ",".join(LOG_COLUMNS):
        if header:
            # An older log with other columns: start a fresh one beside it.
            MONITOR_STATE["path"] = str(log_path).replace(".csv", "_v2.csv")
        with open(MONITOR_STATE["path"], "w", newline="") as f:
            csv.writer(f).writerow(LOG_COLUMNS)

    runner = PyRunner(
        command="monitor._log_row()", virtPeriod=float(interval), initRun=True, label=runner_label
    )
    O.engines += [runner]
    return runner


def stop_monitor(runner_label="monitor"):
    """Remove the monitor ``PyRunner`` if present.

    Args:
        runner_label: Label used in :func:`start_monitor`.
    """
    O.engines = [e for e in O.engines if getattr(e, "label", None) != runner_label]


def steady_state(window_s, angle_tol_deg, power_rel_tol):
    """Compare the last two ``window_s`` windows of the current stage's log.

    Args:
        window_s: Length of each window (s).
        angle_tol_deg: Allowed change of mean charge angle (deg).
        power_rel_tol: Allowed relative change of mean power.

    Returns:
        dict | None: ``None`` until two full windows exist; otherwise the
        window means and ``steady`` (bool).
    """
    rows = MONITOR_STATE["rows"]
    if not rows or rows[-1]["time"] - rows[0]["time"] < 2 * window_s:
        return None
    t_end = rows[-1]["time"]
    last = [r for r in rows if r["time"] > t_end - window_s]
    prev = [r for r in rows if t_end - 2 * window_s < r["time"] <= t_end - window_s]
    if not last or not prev:
        return None
    a1, a0 = _mean(last, "angle_all_deg"), _mean(prev, "angle_all_deg")
    p1, p0 = _mean(last, "power_kW"), _mean(prev, "power_kW")
    d_power = abs(p1 - p0) / max(abs(p0), 1e-9)
    return {
        "time": t_end,
        "angle_deg": a1,
        "angle_change_deg": a1 - a0,
        "power_kW": p1,
        "power_rel_change": d_power,
        "steady": abs(a1 - a0) < angle_tol_deg and d_power < power_rel_tol,
    }


def bed_state(r_split):
    """Return the charge's centre-of-mass angles and height and its mean speed.

    Args:
        r_split: Radius threshold separating small from large spheres (m).

    Returns:
        dict: ``angle_all_deg``, ``angle_small_deg``, ``angle_large_deg``
        (``nan`` for an empty group), ``com_height_m`` and
        ``mean_speed_m_s``.
    """
    sums = {"all": [0.0, 0.0, 0.0], "small": [0.0, 0.0, 0.0], "large": [0.0, 0.0, 0.0]}
    speed, n = 0.0, 0
    for b in O.bodies:
        if not b or not isinstance(b.shape, Sphere):
            continue
        m, p = b.state.mass, b.state.pos
        group = "small" if b.shape.radius < r_split else "large"
        for key in ("all", group):
            s = sums[key]
            s[0] += m * p[0]
            s[1] += m * p[1]
            s[2] += m
        speed += b.state.vel.norm()
        n += 1
    angles = [
        math.degrees(math.atan2(s[0], -s[1])) if s[2] else float("nan")
        for s in (sums["all"], sums["small"], sums["large"])
    ]
    s = sums["all"]
    return {
        "angle_all_deg": angles[0],
        "angle_small_deg": angles[1],
        "angle_large_deg": angles[2],
        "com_height_m": s[1] / s[2] if s[2] else float("nan"),
        "mean_speed_m_s": speed / n if n else float("nan"),
    }


def charge_angles(r_split):
    """Return the charge centre-of-mass angle of all, small, and large spheres (deg).

    Args:
        r_split: Radius threshold separating small from large spheres (m).

    Returns:
        tuple[float, float, float]: ``(all, small, large)``.
    """
    s = bed_state(r_split)
    return s["angle_all_deg"], s["angle_small_deg"], s["angle_large_deg"]


def mill_torque(mill_ids):
    """Return the Z torque the particles exert on the mill about its axis (N m).

    Args:
        mill_ids: Body ids of the mill liner and end walls.

    Returns:
        float: Torque about ``+Z`` through the origin.
    """
    tz = 0.0
    for i in mill_ids:
        f = O.forces.f(i)
        p = O.bodies[i].state.pos
        tz += p[0] * f[1] - p[1] * f[0] + O.forces.t(i)[2]
    return tz


def contact_samples(r_split, fresh_steps=1):
    """Return overlap samples of all real contacts and the normal speeds of new ones.

    Args:
        r_split: Radius threshold separating small from large spheres (m).
        fresh_steps: A contact counts as an impact if it became real within
            this many steps.

    Returns:
        tuple[list, list]: ``[(pair_type, overlap / smaller diameter), ...]``
        and the normal relative speeds (m/s) of the fresh contacts.
    """
    overlaps, speeds = [], []
    it = int(O.iter)
    for i in O.interactions:
        if not i.isReal:
            continue
        b1, b2 = O.bodies[i.id1], O.bodies[i.id2]
        r1 = b1.shape.radius if isinstance(b1.shape, Sphere) else None
        r2 = b2.shape.radius if isinstance(b2.shape, Sphere) else None
        if r1 is None and r2 is None:
            continue
        d = 2.0 * min(r for r in (r1, r2) if r is not None)
        overlaps.append((checks.pair_type(r1, r2, r_split), i.geom.penetrationDepth / d))
        if it - i.iterMadeReal <= fresh_steps:
            c, n = i.geom.contactPoint, i.geom.normal
            v1 = b1.state.vel + b1.state.angVel.cross(c - b1.state.pos)
            v2 = b2.state.vel + b2.state.angVel.cross(c - b2.state.pos)
            speeds.append(abs((v2 - v1).dot(n)))
    return overlaps, speeds


def max_overlap():
    """Return the largest contact overlap relative to the smaller diameter."""
    overlaps, _ = contact_samples(r_split=0.0)
    return max((rel for _, rel in overlaps), default=0.0)


def stage_summary():
    """Return the current stage's contact statistics for the run manifest.

    Returns:
        dict: ``overlap`` (per pair type, from the contacts now, see
        :func:`pm_dem_sm.simulation.checks.overlap_stats`), the largest
        logged overall P99 and max overlaps, and the stage's impact-speed
        sample size and P99.
    """
    st = MONITOR_STATE
    overlaps, _ = contact_samples(st.get("r_split", 0.0))
    rows = st["rows"]
    speeds = st["impact_speeds"]
    return {
        "overlap_now": checks.overlap_stats(overlaps) if overlaps else {},
        "overlap_p99_rel_d_max": max((r["overlap_p99_rel_d"] for r in rows), default=None),
        "overlap_max_rel_d_max": max((r["overlap_max_rel_d"] for r in rows), default=None),
        "impact_speed_samples": len(speeds),
        "impact_v_p99_m_s": checks.percentile(speeds, 99) if speeds else None,
    }


def energy_terms():
    """Return the potential, elastic and cumulative dissipated energy (J).

    Requires ``O.trackEnergy`` and the Mindlin law's ``calcEnergy``
    (:func:`~pm_dem_sm.simulation.yade_dem.engines.initialize_engines` sets
    both); ``nan`` otherwise.
    """
    law = _mindlin_law()
    if law is None or not law.calcEnergy:
        return {
            "potential_J": float("nan"),
            "elastic_J": float("nan"),
            "dissipated_J": float("nan"),
        }
    potential = dict(O.energy.items()).get("gravWork", 0.0)
    return {
        "potential_J": float(potential),
        "elastic_J": float(law.normElastEnergy() + law.shearEnergy),
        "dissipated_J": float(law.normDampDissip + law.shearDampDissip + law.frictionDissipation),
    }


def rolling_dissipation_rate():
    """Return the current plastic dissipation rate of the rolling moments (W).

    YADE does not track it. Contacts whose bending moment is at the plastic
    cap ``maxBendPl |F_n|`` (``eta R_mean |F_n|``) dissipate
    ``|M_bend| x |relative angular velocity normal to the contact|``;
    elastic contacts only store energy. The monitor integrates this rate
    between rows (a sampled estimate) for the V4 balance.
    """
    rate = 0.0
    for i in O.interactions:
        if not i.isReal or not hasattr(i.phys, "maxBendPl"):
            continue
        cap = i.phys.maxBendPl * i.phys.normalForce.norm()
        m = i.phys.momentBend.norm()
        if cap <= 0.0 or m < 0.999 * cap:
            continue
        n = i.geom.normal
        w = O.bodies[i.id2].state.angVel - O.bodies[i.id1].state.angVel
        rate += m * (w - n * w.dot(n)).norm()
    return rate


def liner_force_histogram(liner_ids, bin_deg=None):
    """Return the contact-force magnitude on the liner facets, summed per angular bin (N).

    The angle of each facet is that of its position in the lab frame in the
    calibration-target convention: 0 deg at 3 o'clock (+X), counter-clockwise
    (docs/scientific_rationale/15_calibration_targets.md). Owen & Cleary's
    liner-force distribution, the cross-check of the bulk toe / shoulder
    (C15-1).

    Args:
        liner_ids: Body ids of the liner facets.
        bin_deg: Bin width (deg); :data:`LINER_BIN_DEG` by default.

    Returns:
        list[float]: ``360 / bin_deg`` sums, bin k covering
        ``[k bin_deg, (k + 1) bin_deg)``.
    """
    w = bin_deg or LINER_BIN_DEG
    out = [0.0] * (360 // w)
    for i in liner_ids:
        f = O.forces.f(i)
        mag = f.norm()
        if mag == 0.0:
            continue
        p = O.bodies[i].state.pos
        angle = math.degrees(math.atan2(p[1], p[0])) % 360.0
        out[int(angle // w) % len(out)] += mag
    return out


def run_until_settled(d_small, max_time_s, r_split, sample_s=0.05, **tolerances):
    """Run the scene until the bed geometry is stationary (or the time cap).

    Samples the bed every ``sample_s`` of simulated time and applies
    :func:`pm_dem_sm.simulation.checks.settle_stop` (geometric rule of
    docs/scientific_rationale/13_initial_conditions.md). Independent of the
    logging ``PyRunner``.

    Args:
        d_small: Small-particle diameter (m).
        max_time_s: Time cap (s).
        r_split: Radius threshold separating small from large spheres (m).
        sample_s: Simulated time between samples (s).
        **tolerances: Overrides of the rule's ``window_s``,
            ``angle_tol_deg``, ``height_tol_rel_d``, ``speed_tol_m_s``.

    Returns:
        dict: The final :func:`~pm_dem_sm.simulation.checks.settle_stop`
        result plus ``settle_time_s``.
    """
    t0 = float(O.time)
    steps = max(1, round(sample_s / O.dt))
    samples = [{"time": t0, **bed_state(r_split)}]
    while True:
        O.run(steps, True)
        samples.append({"time": float(O.time), **bed_state(r_split)})
        result = checks.settle_stop(samples, d_small, t0, max_time_s, **tolerances)
        if result["stop"]:
            result["settle_time_s"] = float(O.time) - t0
            print(
                f"[settle] {result['reason']} after {result['settle_time_s']:.2f} s: "
                f"angle change {result['angle_change_deg']}, height change "
                f"{result['height_change_m']}, mean speed {result['mean_speed_m_s']}"
            )
            return result


# --- Private helper functions ------------------------------------------------


def _mindlin_law():
    """Return the ``Law2_ScGeom_MindlinPhys_Mindlin`` functor of the scene, if any."""
    for e in O.engines:
        if type(e).__name__ == "InteractionLoop":
            for f in e.lawDispatcher.functors:
                if type(f).__name__ == "Law2_ScGeom_MindlinPhys_Mindlin":
                    return f
    return None


def _log_row():
    """Append one mill-state row to the log (``PyRunner`` hook)."""
    st = MONITOR_STATE
    if "path" not in st:
        return
    bed = bed_state(st["r_split"])
    torque = mill_torque(st["mill_ids"])
    omega = st["omega"]
    overlaps, speeds = contact_samples(st["r_split"])
    st["impact_speeds"].extend(speeds)
    rels = [rel for _, rel in overlaps]
    t, rate = float(O.time), rolling_dissipation_rate()
    if "rolling_last" in st:
        t_prev, rate_prev = st["rolling_last"]
        st["rolling_J"] += 0.5 * (rate + rate_prev) * (t - t_prev)
    st["rolling_last"] = (t, rate)
    row = {
        "time": float(O.time),
        "iter": int(O.iter),
        "stage": st["stage"],
        "revolutions": (float(O.time) - st["t0"]) * abs(omega) / (2 * math.pi),
        **bed,
        "kinetic_J": kineticEnergy(),
        "torque_Nm": torque,
        # The drive supplies the opposite of the charge's torque on the mill.
        "power_kW": -torque * omega / 1000.0,
        "overlap_mean_rel_d": sum(rels) / len(rels) if rels else 0.0,
        "overlap_p99_rel_d": checks.percentile(rels, 99) if rels else 0.0,
        "overlap_max_rel_d": max(rels, default=0.0),
        "impact_v_p99_m_s": checks.percentile(speeds, 99) if speeds else float("nan"),
        **energy_terms(),
        "rolling_dissipated_J": st["rolling_J"],
        "unbalanced": unbalancedForce(),
    }
    st["rows"].append(row)
    with open(st["path"], "a", newline="") as f:
        csv.writer(f).writerow([row[c] for c in LOG_COLUMNS])
    if st.get("liner_ids"):
        with open(st["liner_path"], "a", newline="") as f:
            csv.writer(f).writerow(
                [row["time"], st["stage"]] + liner_force_histogram(st["liner_ids"])
            )


def _mean(rows, key):
    """Return the mean of ``key`` over ``rows``."""
    return sum(r[key] for r in rows) / len(rows)

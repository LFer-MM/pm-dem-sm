"""Post-process a DEM run directory in the project environment (pandas / pyarrow).

YADE's interpreter has neither pandas nor pyarrow, so everything that needs
them runs here, after the YADE process has finished
(:func:`postprocess_run`; called by ``pm-dem-sm dem-sim`` and available as
``pm-dem-sm dem-post``). For one run directory it:

1. **Frames to float32 parquet** (C14-4): every ``frames/frame_*.csv`` becomes
   ``frame_*.parquet`` (``id`` int32, ``m`` string, all other columns
   float32) and the CSV is deleted.
2. **Segregation profiles** (C14-3, ``dataset`` runs): the radial
   large-particle fraction per frame for the whole slice, the centre layer
   and the two near-wall layers (one ball diameter from each end wall,
   V19), and Lacey's index per frame on 0.3 m cells.
3. **Charge shape** (C15-1, ``calibrate`` runs): bulk toe and shoulder from
   the time-averaged position density of the recorded frames
   (:func:`pm_dem_sm.simulation.checks.toe_shoulder`) and the liner-force
   cross-check (:func:`~pm_dem_sm.simulation.checks.liner_force_arc`).
4. **Validation summary** (C16-1): V2-V7, V8 (reported), V13, V14, V16, V18
   and V19 with value, criterion and status, written to the manifest
   (``validation``) and to ``validation.json``
   (docs/scientific_rationale/16_validation_checks.md).

Outputs go to ``<run-dir>/analysis/``.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import re

import numpy as np
import pandas as pd

from ..metrics.lacey_mixing_index import detect_tracer_radius, lacey_index_for_frame
from ..metrics.segregation_profile import radial_fraction_profile
from . import checks
from .scenario import CALIBRATION_RUN_TYPES, SimulationScenario

# --- Constants ---------------------------------------------------------------

#: Frame columns stored as float32 in the parquet frames.
FLOAT_COLUMNS = ["x", "y", "z", "r", "vx", "vy", "vz"]
#: Radial bins of the segregation profile (inside the liner).
RADIAL_BINS = 12
#: Calibration targets: SAG_A bulk toe / shoulder interquartile ranges (deg)
#: (docs/scientific_rationale/15_calibration_targets.md).
TOE_TARGET_DEG = (213.4, 214.5)
SHOULDER_TARGET_DEG = (26.0, 27.3)
#: V3 limits, overlap relative to the smaller diameter, and the stages they apply to.
V3_STAGES = ("settle", "spinup", "record")
V3_MEAN, V3_P99, V3_MAX = 0.005, 0.02, 0.10
#: V4 acceptance of the energy balance residual (relative).
V4_TOL = 0.05
#: Training window length (s) that must fit after the quasi-steady time (V7).
TRAINING_WINDOW_S = 1.0
_FRAME_RE = re.compile(r"frame_(\d+)\.(csv|parquet)$")


# --- Public functions --------------------------------------------------------


def convert_frames(run_dir: Path | str, delete_csv: bool = True) -> dict:
    """Convert ``frames/frame_*.csv`` to float32 parquet (C14-4).

    Args:
        run_dir: Run directory.
        delete_csv: Remove each CSV once its parquet is written.

    Returns:
        dict: ``converted`` (frames written now), ``parquet`` (total parquet
        frames), ``bytes`` (their total size).
    """
    frames = Path(run_dir) / "frames"
    n = 0
    for csv_path in sorted(frames.glob("frame_*.csv")):
        df = pd.read_csv(csv_path)
        df[FLOAT_COLUMNS] = df[FLOAT_COLUMNS].astype("float32")
        df["id"] = df["id"].astype("int32")
        df["m"] = df["m"].astype(str)
        df.to_parquet(csv_path.with_suffix(".parquet"), index=False)
        if delete_csv:
            csv_path.unlink()
        n += 1
    parquet = sorted(frames.glob("frame_*.parquet"))
    return {
        "converted": n,
        "parquet": len(parquet),
        "bytes": int(sum(p.stat().st_size for p in parquet)),
    }


def load_frames(run_dir: Path | str):
    """Yield ``(frame, time, DataFrame)`` for every parquet frame, in order.

    Times come from ``frames_index.csv`` (exact frame times).
    """
    run_dir = Path(run_dir)
    times = {}
    index = run_dir / "frames_index.csv"
    if index.exists():
        idx = pd.read_csv(index)
        times = dict(zip(idx["frame"].astype(int), idx["time"].astype(float)))
    for path in sorted((run_dir / "frames").glob("frame_*.parquet")):
        k = int(_FRAME_RE.search(path.name).group(1))
        yield k, times.get(k, float("nan")), pd.read_parquet(path)


def segregation_profiles(
    frames, scenario: SimulationScenario, n_bins: int = RADIAL_BINS
) -> pd.DataFrame:
    """Radial large-particle fraction per frame and layer (C14-3, V19).

    Layers: ``all`` (the slice), ``centre`` (more than one ball diameter from
    both end walls) and ``near_wall`` (within one ball diameter of either
    end wall; an artefact check, docs/scientific_rationale/10_mill_geometry.md).
    Radial bins span 0 to the radius inside liners.

    Returns:
        pandas.DataFrame: ``frame``, ``time``, ``layer``, ``bin``,
        ``bin_center``, ``fraction_large``, ``n_particles``.
    """
    large_r = scenario.large.radius_m
    layer_w = 2.0 * large_r
    depth = scenario.mill.depth_m
    edges = np.linspace(0.0, scenario.mill.diameter_m / 2.0, n_bins + 1)
    out = []
    for k, t, df in frames:
        z = df["z"].to_numpy(float)
        near = (z < layer_w) | (z > depth - layer_w)
        # Radii of float32 frames: take the tracer radius from the data.
        tracer = detect_tracer_radius(df["r"])
        for layer, mask in (("all", np.ones_like(near)), ("centre", ~near), ("near_wall", near)):
            prof = radial_fraction_profile(df[mask], tracer, edges)
            prof.insert(0, "layer", layer)
            prof.insert(0, "time", t)
            prof.insert(0, "frame", k)
            out.append(prof)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def lacey_series(
    frames, scenario: SimulationScenario, cell_size: float = 0.3, min_particles: int = 15
) -> pd.DataFrame:
    """Lacey's mixing index per frame on cubic cells (balls as tracers; V7 plateau).

    Returns:
        pandas.DataFrame: ``frame``, ``time``, ``lacey``, ``cells``.
    """
    rows = []
    for k, t, df in frames:
        m, cells, _, _ = lacey_index_for_frame(
            df, cell_size, detect_tracer_radius(df["r"]), min_particles
        )
        rows.append({"frame": k, "time": t, "lacey": m, "cells": cells})
    return pd.DataFrame(rows)


def charge_shape(
    run_dir: Path | str, frames, scenario: SimulationScenario, band_large_diameters: float = 2.0
) -> dict:
    """Bulk toe / shoulder from the recorded frames plus the liner-force cross-check (C15-1).

    The position density is taken in the annulus of ``band_large_diameters``
    ball diameters just inside the lifter tops (the layer of the charge next
    to the liner, excluding particles held between the lifters).

    Returns:
        dict: ``bulk`` (:func:`pm_dem_sm.simulation.checks.toe_shoulder`
        without the density array), ``liner_force`` (cross-check), the band
        and the targets.
    """
    r_top = scenario.mill.lifter_top_radius_m
    band = (r_top - band_large_diameters * 2.0 * scenario.large.radius_m, r_top)
    bulk = checks.toe_shoulder((df[["x", "y"]].to_numpy(float) for _, _, df in frames), *band)
    out = {
        "band_m": list(band),
        "bulk": {k: v for k, v in bulk.items() if k != "density"},
        "targets": {"toe_deg": TOE_TARGET_DEG, "shoulder_deg": SHOULDER_TARGET_DEG},
    }
    liner = Path(run_dir) / "liner_forces.csv"
    if liner.exists():
        lf = pd.read_csv(liner)
        lf = lf[lf["stage"] == "record"]
        if len(lf):
            cols = [c for c in lf.columns if c.startswith("f_")]
            bin_deg = 360.0 / len(cols)
            arc = checks.liner_force_arc(lf[cols].to_numpy(float), bin_deg)
            out["liner_force"] = {k: v for k, v in arc.items() if k != "force"}
    return out


def validation_summary(manifest: dict, run_dir: Path | str, extras: dict) -> dict:
    """Collect the per-run checks into one table (C16-1).

    Args:
        manifest: The run manifest (stage ``checks`` from the YADE side).
        run_dir: Run directory (for the mill log).
        extras: Post-processing results: ``inventory`` (V6), ``lacey``
            (V7 plateau), ``charge_shape`` (V8), ``segregation`` (V19).

    Returns:
        dict: Check id -> ``{"value", "criterion", "status"}`` with status
        ``pass``, ``fail``, ``reported`` (no acceptance limit, or a limit to be
        judged later) or ``n/a``.
    """
    stages = manifest.get("stages", {})
    chk = {name: st.get("checks", {}) for name, st in stages.items()}
    out = {}

    def put(key, value, criterion, ok):
        status = (
            "n/a" if value is None else ("reported" if ok is None else ("pass" if ok else "fail"))
        )
        out[key] = {"value": value, "criterion": criterion, "status": status}

    steps = [
        c["steps_per_collision_at_p99"]
        for c in chk.values()
        if c.get("steps_per_collision_at_p99") is not None
    ]
    put(
        "V2",
        min(steps) if steps else None,
        ">= 20 steps per collision at the P99 impact speed",
        min(steps) >= 20 if steps else None,
    )

    # V3 describes the charge, not the pouring transient: judged over the
    # settle, spin-up and record stages (fill overlaps stay in the manifest);
    # the mean is the time average of the logged per-row means.
    log = _mill_log(run_dir)
    charge = {name: c for name, c in chk.items() if name in V3_STAGES}
    rows = None if log is None else log[log["stage"].isin(list(charge))]
    mean_ov = float(rows["overlap_mean_rel_d"].mean()) if rows is not None and len(rows) else None
    p99s = [c["overlap_p99_rel_d_max"] for c in charge.values() if c.get("overlap_p99_rel_d_max")]
    maxs = [c["overlap_max_rel_d_max"] for c in charge.values() if c.get("overlap_max_rel_d_max")]
    v3 = None if not maxs else {"mean": mean_ov, "p99": max(p99s), "max": max(maxs)}
    put(
        "V3",
        v3,
        f"overlap / smaller d: mean <= {V3_MEAN}, P99 <= {V3_P99}, max < {V3_MAX}",
        None
        if v3 is None
        else (v3["mean"] or 0) <= V3_MEAN and v3["p99"] <= V3_P99 and v3["max"] < V3_MAX,
    )

    rec = chk.get("record", {}).get("energy_balance")
    put(
        "V4",
        None if rec is None else rec["residual_rel"],
        f"|energy residual| <= {V4_TOL} of the drive work over the record stage",
        None if rec is None else abs(rec["residual_rel"]) <= V4_TOL,
    )

    damping = [c.get("damping") for c in chk.values()]
    put(
        "V5",
        damping,
        "NewtonIntegrator.damping == 0 in every stage",
        all(d == 0.0 for d in damping),
    )

    inv = extras.get("inventory")
    put(
        "V6",
        inv,
        "same counts in every frame, no particle outside the mill",
        None if inv is None else inv["constant_counts"] and inv["max_outside"] == 0,
    )

    put(
        "V7",
        extras.get("quasi_steady"),
        "quasi-steady before the training window; Lacey plateau within the run",
        extras.get("quasi_steady_ok"),
    )

    shape = extras.get("charge_shape")
    put(
        "V8",
        None if shape is None else shape["bulk"],
        f"bulk toe in {TOE_TARGET_DEG}, shoulder in {SHOULDER_TARGET_DEG} deg (calibration)",
        None,
    )

    v13 = stages.get("fill", {}).get("v13_initial_overlaps")
    put(
        "V13",
        v13,
        "0 overlaps before every fill batch",
        None if v13 is None else v13["overlaps"] == 0,
    )

    esc = {name: c.get("escaped") for name, c in chk.items()}
    put(
        "V14",
        esc,
        "0 particles outside the mill after every stage",
        all(v == 0 for v in esc.values()),
    )

    ic = manifest.get("initial_condition")
    put(
        "V16",
        None if ic is None else {"J": ic.get("J"), "phi": ic.get("phi")},
        "settled J of the IC (the counts come from the grind-out, C12-3)",
        None,
    )

    settle = stages.get("settle", {}).get("settle")
    put(
        "V18",
        None if settle is None else settle["reason"],
        "settle ends by the geometric rule ('stationary'), not the time cap",
        None if settle is None else settle["reason"] == "stationary",
    )

    put("V19", extras.get("segregation"), "near-wall vs centre large fraction (reported)", None)
    return out


def postprocess_run(run_dir: Path | str, delete_csv: bool = True) -> dict:
    """Run every post-processing step on a run directory and update its manifest.

    Args:
        run_dir: Run directory written by ``run_simulation.py``.
        delete_csv: Remove frame CSVs after conversion.

    Returns:
        dict: The ``validation`` table (also in ``manifest.json`` and
        ``validation.json``).
    """
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    scenario = SimulationScenario.from_dict(manifest["scenario"])
    analysis = run_dir / "analysis"
    analysis.mkdir(exist_ok=True)
    extras = {}
    post = {"frames": convert_frames(run_dir, delete_csv)}

    if post["frames"]["parquet"]:
        r_split = 0.5 * (scenario.small.radius_m + scenario.large.radius_m)
        invs = [
            checks.frame_inventory(
                df["r"],
                df[["x", "y", "z"]],
                scenario.mill.shell_diameter_m / 2.0,
                scenario.mill.depth_m,
                r_split,
            )
            for _, _, df in load_frames(run_dir)
        ]
        extras["inventory"] = {
            "frames": len(invs),
            "small": sorted({i["small"] for i in invs}),
            "large": sorted({i["large"] for i in invs}),
            "constant_counts": len({(i["small"], i["large"]) for i in invs}) == 1,
            "max_outside": max(i["outside"] for i in invs),
        }

    log = _mill_log(run_dir)
    rec = None if log is None else log[log["stage"] == "record"]
    spin = manifest.get("stages", {}).get("spinup", {}).get("steady_state")
    if scenario.run.type in CALIBRATION_RUN_TYPES:
        # V7 for calibration: the record starts after spin-up reached steady state.
        extras["quasi_steady"] = {"spinup_steady_state": spin}
        extras["quasi_steady_ok"] = bool(spin and spin.get("steady"))
    elif rec is not None and len(rec) > 2:
        t = rec["time"].to_numpy(float) - float(rec["time"].iloc[0])
        window = (
            0.5 * scenario.revolution_s() if scenario.run.type in CALIBRATION_RUN_TYPES else 1.0
        )
        qs = {
            "kinetic_s": checks.quasi_steady_time(t, rec["kinetic_J"], window),
            "power_s": checks.quasi_steady_time(t, rec["power_kW"], window),
            "angle_s": checks.quasi_steady_time(t, rec["angle_all_deg"], window, abs_tol=2.0),
        }
        extras["quasi_steady"] = qs
        duration = float(t[-1])
        times = [v for v in qs.values() if v is not None]
        extras["quasi_steady_ok"] = len(times) == 3 and max(times) + TRAINING_WINDOW_S <= duration

    if scenario.run.type == "dataset" and post["frames"]["parquet"]:
        prof = segregation_profiles(load_frames(run_dir), scenario)
        prof.to_parquet(analysis / "radial_fraction.parquet", index=False)
        lacey = lacey_series(load_frames(run_dir), scenario)
        lacey.to_csv(analysis / "lacey.csv", index=False)
        extras["lacey"] = checks.plateau(lacey["lacey"])
        qs = extras.get("quasi_steady") or {}
        qs["lacey_plateau"] = extras["lacey"]
        extras["quasi_steady"] = qs
        if "quasi_steady_ok" in extras:
            extras["quasi_steady_ok"] = extras["quasi_steady_ok"] and extras["lacey"]["plateau"]
        last = prof[prof["frame"] >= prof["frame"].max() - 19]
        frac = {}
        for layer, g in last.groupby("layer"):
            n = g["n_particles"].to_numpy(float)
            f = g["fraction_large"].fillna(0).to_numpy(float)
            frac[layer] = float((f * n).sum() / n.sum()) if n.sum() else float("nan")
        extras["segregation"] = {
            "large_fraction_last_20_frames": frac,
            "near_wall_minus_centre": float(
                frac.get("near_wall", math.nan) - frac.get("centre", math.nan)
            ),
        }

    if scenario.run.type in CALIBRATION_RUN_TYPES and post["frames"]["parquet"]:
        shape = charge_shape(run_dir, load_frames(run_dir), scenario)
        (analysis / "charge_shape.json").write_text(json.dumps(shape, indent=2), encoding="utf-8")
        extras["charge_shape"] = shape

    validation = validation_summary(manifest, run_dir, extras)
    manifest["postprocess"] = {
        **post,
        **{k: v for k, v in extras.items() if k not in ("charge_shape",)},
    }
    manifest["validation"] = validation
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8"
    )
    (run_dir / "validation.json").write_text(
        json.dumps(validation, indent=2, default=str), encoding="utf-8"
    )
    for key, v in validation.items():
        print(f"[validation] {key}: {v['status']} ({v['criterion']})")
    return validation


# --- Private helper functions ------------------------------------------------


def _mill_log(run_dir: Path | str):
    """Return the run's mill log (current schema) as a DataFrame, or ``None``."""
    for name in ("mill_log.csv", "mill_log_v2.csv"):
        path = Path(run_dir) / name
        if path.exists():
            log = pd.read_csv(path)
            if "overlap_mean_rel_d" in log.columns:
                return log
    return None

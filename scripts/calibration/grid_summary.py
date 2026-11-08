"""Summarise the friction-calibration grid: toe / shoulder per point against SAG_A.

Reads every ``data/raw/yade_runs/cal_*`` run directory (or those given):
mu_p and mu_w from the manifest, the bulk and liner-force toe / shoulder
from ``analysis/charge_shape.json``, the spin-up revolutions and steady
state, the drive power over the record stage and the failed checks from
``validation.json``. Points are ranked by the distance of the bulk toe /
shoulder from the middle of the SAG_A target ranges
(docs/scientific_rationale/15_calibration_targets.md). Writes
``data/raw/calibration/grid_summary.csv`` and prints the table.

Run from the repository root with the project environment::

    python scripts/calibration/grid_summary.py
"""

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd

from pm_dem_sm.simulation.postprocess import SHOULDER_TARGET_DEG, TOE_TARGET_DEG

TOE_MID = sum(TOE_TARGET_DEG) / 2.0
SHOULDER_MID = sum(SHOULDER_TARGET_DEG) / 2.0


def point(run_dir):
    """Return one grid point's row (``None`` if the run has no manifest)."""
    run_dir = Path(run_dir)
    if not (run_dir / "manifest.json").exists():
        return None
    m = json.loads((run_dir / "manifest.json").read_text())
    contact = m["scenario"]["contact"]
    row = {
        "run": run_dir.name,
        "mu_p": contact.get("particle_friction"),
        "mu_w": contact.get("wall_friction"),
        "status": "running",
    }
    spin = m.get("stages", {}).get("spinup", {})
    if spin:
        row["spinup_rev"] = round(spin.get("revolutions", float("nan")), 2)
        row["steady"] = bool((spin.get("steady_state") or {}).get("steady"))
    shape_path = run_dir / "analysis" / "charge_shape.json"
    if shape_path.exists():
        shape = json.loads(shape_path.read_text())
        for kind in ("bulk", "liner_force"):
            part = shape.get(kind) or {}
            row[f"{kind}_toe"] = part.get("toe_deg")
            row[f"{kind}_shoulder"] = part.get("shoulder_deg")
        toe, sh = row.get("bulk_toe"), row.get("bulk_shoulder")
        if toe is not None and sh is not None:
            row["toe_in"] = TOE_TARGET_DEG[0] <= toe <= TOE_TARGET_DEG[1]
            row["shoulder_in"] = SHOULDER_TARGET_DEG[0] <= sh <= SHOULDER_TARGET_DEG[1]
            row["distance_deg"] = round(abs(toe - TOE_MID) + abs(sh - SHOULDER_MID), 2)
    log = run_dir / "mill_log.csv"
    if log.exists():
        rec = pd.read_csv(log, on_bad_lines="skip")
        rec = rec[rec["stage"] == "record"]
        if len(rec):
            row["power_kW"] = round(float(rec["power_kW"].mean()), 1)
    val = run_dir / "validation.json"
    if val.exists():
        v = json.loads(val.read_text())
        row["failed"] = ",".join(k for k, x in v.items() if x["status"] == "fail") or "-"
        row["status"] = "done"
    return row


def main(argv=None):
    """Print and write the grid table."""
    argv = sys.argv[1:] if argv is None else argv
    dirs = [Path(a) for a in argv] or sorted((REPO_ROOT / "data/raw/yade_runs").glob("cal_*"))
    rows = [r for r in (point(d) for d in dirs) if r is not None]
    if not rows:
        print("[grid] no calibration runs found")
        return
    table = pd.DataFrame(rows)
    if "distance_deg" in table:
        table = table.sort_values("distance_deg", na_position="last")
    out = REPO_ROOT / "data/raw/calibration/grid_summary.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out, index=False)
    print(f"[grid] targets: toe {TOE_TARGET_DEG}, shoulder {SHOULDER_TARGET_DEG} deg")
    print(table.to_string(index=False))
    print(f"[grid] -> {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()

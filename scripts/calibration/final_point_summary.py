"""Calibrated point: replicate scatter (V12) and the plant power check (V15).

docs/scientific_rationale/16_validation_checks.md (V12, V15) and
15_calibration_targets.md ("Post-calibration plant power check"):

- V12: bulk toe / shoulder (and power) of each replicate (different seeds,
  everything else identical) with their mean and standard deviation.
- V15: P_mill = P_slice x (L / depth) x (1 + c_cone), P_slice the mean
  drive power of the record stage (after the spin-up's steady state), for
  c_cone 0.05 (Doll) and 0.13 (top of the band), against
  P_charge,plant = eta_d x (1 - f_NL) x P_motor; the % deviation is
  reported (not a pass / fail target; ~+-20 % is the comparison's
  uncertainty).

The plant figures default to topic 15's SAG_A values (target window, 239 h):
P_motor median 12,627 kW, no-load 8 % of gross, eta_d 0.95 (assumed), belly
length 5.244 m. Run from the repository root with the project environment::

    python scripts/calibration/final_point_summary.py data/raw/yade_runs/cal_final_*_s*
"""

import argparse
import json
from pathlib import Path
import statistics
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd

BELLY_LENGTH_M = 5.244
P_MOTOR_KW = 12627.0
NO_LOAD_FRACTION = 0.08
DRIVE_EFFICIENCY = 0.95
CONE_FACTORS = (0.05, 0.13)


def run_row(run_dir):
    """Return one replicate's seed, toe, shoulder, record power and failed checks."""
    run_dir = Path(run_dir)
    m = json.loads((run_dir / "manifest.json").read_text())
    shape = json.loads((run_dir / "analysis" / "charge_shape.json").read_text())
    log = pd.read_csv(run_dir / "mill_log.csv")
    rec = log[log["stage"] == "record"]
    v = json.loads((run_dir / "validation.json").read_text())
    return {
        "run": run_dir.name,
        "seed": m["scenario"]["seed"],
        "toe_deg": shape["bulk"]["toe_deg"],
        "shoulder_deg": shape["bulk"]["shoulder_deg"],
        "power_slice_kW": float(rec["power_kW"].mean()),
        "depth_m": m["scenario"]["mill"]["depth_m"],
        "failed": [k for k, x in v.items() if x["status"] == "fail"],
    }


def summary(rows, p_motor_kw=P_MOTOR_KW, length_m=BELLY_LENGTH_M):
    """Return the V12 statistics and the V15 comparison for replicate ``rows``."""

    def stats(key):
        vals = [r[key] for r in rows]
        sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
        return {"mean": statistics.fmean(vals), "sd": sd, "values": vals}

    out = {key: stats(key) for key in ("toe_deg", "shoulder_deg", "power_slice_kW")}
    p_plant = DRIVE_EFFICIENCY * (1.0 - NO_LOAD_FRACTION) * p_motor_kw
    scale = length_m / rows[0]["depth_m"]
    out["V15"] = {
        "P_charge_plant_kW": p_plant,
        "length_factor": scale,
        "cases": [
            {
                "c_cone": c,
                "P_mill_kW": out["power_slice_kW"]["mean"] * scale * (1.0 + c),
                "deviation": out["power_slice_kW"]["mean"] * scale * (1.0 + c) / p_plant - 1.0,
            }
            for c in CONE_FACTORS
        ],
    }
    return out


def main(argv=None):
    """Print and write the summary of the given replicate run directories."""
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("run_dirs", nargs="+")
    p.add_argument("--out", default=str(REPO_ROOT / "data/raw/calibration/final_point.json"))
    args = p.parse_args(argv)
    rows = [run_row(d) for d in args.run_dirs]
    res = {"replicates": rows, **summary(rows)}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=2))
    for r in rows:
        print(
            f"{r['run']}: toe {r['toe_deg']:.1f}, shoulder {r['shoulder_deg']:.1f} deg, "
            f"P_slice {r['power_slice_kW']:.0f} kW, failed {r['failed'] or '-'}"
        )
    for key in ("toe_deg", "shoulder_deg", "power_slice_kW"):
        s = res[key]
        print(f"V12 {key}: {s['mean']:.2f} +- {s['sd']:.2f} (n = {len(s['values'])})")
    v15 = res["V15"]
    for c in v15["cases"]:
        print(
            f"V15 c_cone {c['c_cone']:.2f}: P_mill {c['P_mill_kW']:.0f} kW vs plant "
            f"{v15['P_charge_plant_kW']:.0f} kW: {100 * c['deviation']:+.1f} %"
        )
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()

"""Print the per-stage checks recorded in run manifests (plain Python).

For each stage of ``run_simulation.py``'s ``manifest.json``: damping (V5),
escapes (V14), V13 batch counts, settle stop result (V18), overlap
statistics relative to the smaller diameter (V3), impact-speed P99 and the
steps per collision at that speed (V2), and the energy balance (V4).

Run from the repository root (project venv)::

    python scripts/validation/summarize_manifest.py data/raw/validation/results/smoke/*/manifest.json
"""

import json
import sys


def _fmt(value):
    """Round floats for printing."""
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, dict):
        return {k: _fmt(v) for k, v in value.items()}
    return value


for path in sys.argv[1:]:
    with open(path) as fh:
        m = json.load(fh)
    print(f"== {path}")
    print(
        f"   yade {m.get('yade_version')}, dt {m.get('dt_s')}, "
        f"provisional {_fmt(m.get('provisional_parameters', {}))}"
    )
    for name, st in m.get("stages", {}).items():
        c = st.get("checks", {})
        print(
            f"   [{name}] wall {st.get('wall_s', 0):.0f} s, damping {c.get('damping')}, "
            f"escaped {c.get('escaped')}"
        )
        for key in ("v13_initial_overlaps", "settle", "inventory", "steady_state"):
            if key in st:
                print(f"      {key}: {_fmt(st[key])}")
        if c.get("overlap_now"):
            print(
                f"      overlap / smaller d now: {_fmt(c['overlap_now'].get('all'))}; "
                f"max P99 {_fmt(c.get('overlap_p99_rel_d_max'))}, "
                f"max {_fmt(c.get('overlap_max_rel_d_max'))}"
            )
        if c.get("impact_v_p99_m_s") is not None:
            print(
                f"      impact P99 {_fmt(c['impact_v_p99_m_s'])} m/s over "
                f"{c.get('impact_speed_samples')} samples -> "
                f"{_fmt(c.get('steps_per_collision_at_p99'))} steps per collision"
            )
        if "energy_balance" in c:
            print(f"      energy balance: {_fmt(c['energy_balance'])}")

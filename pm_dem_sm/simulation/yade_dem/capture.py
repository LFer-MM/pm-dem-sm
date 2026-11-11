"""Periodic frame recording during a run, via CSV sphere dumps (YADE).

Every frame is one CSV with columns ``id, x, y, z, r, m, vx, vy, vz`` -- the
schema :mod:`pm_dem_sm.data_processing` converts to parquet.

The ``PyRunner`` command strings in :func:`start_frame_capture` and
:func:`start_recording` are evaluated
by YADE in the top-level running script's global namespace, so
``yade_dem/run_simulation.py`` must import this module unaliased
(``from . import capture``) for the name ``capture`` to resolve there.
"""

from __future__ import annotations

import csv
import math
import os

from yade import Sphere
from yade.wrapper import O, PyRunner

from . import materials

# --- Module state ------------------------------------------------------------

# Runner state shared between start_frame_capture and the PyRunner hook.
_frameCaptureState = {}
# Runner state shared between start_recording and the PyRunner hook.
_recordingState = {}
# Runner state shared between start_preview and the PyRunner hook.
_previewState = {}


# --- Public functions --------------------------------------------------------


def start_frame_capture(folder_name, interval, runner_label="frameCapture", iter_period=50):
    """Configure periodic CSV sphere dumps via PyRunner.

    Creates a folder named ``folder_name + str(O.dt) + "_"`` under the CWD and
    appends a runner that calls ``_save_sphere_frame``.

    Args:
        folder_name: Base name for the output folder (``O.dt`` is appended).
        interval: Simulation-time interval between CSV dumps (seconds).
        runner_label: Label for the ``PyRunner`` engine.
        iter_period: How often (in DEM iterations) the runner fires.

    Returns:
        list: The appended ``PyRunner`` engine(s).
    """
    folder_name = folder_name + str(O.dt) + "_"
    folder = os.path.join(os.getcwd(), folder_name)
    os.makedirs(folder, exist_ok=True)

    _frameCaptureState.clear()
    _frameCaptureState.update({
        "interval": float(interval),
        "next_save_time": float(O.time),
        "frame_id": 0,
        "folder": folder,
    })

    r = [PyRunner(command="capture._save_sphere_frame()", iterPeriod=int(iter_period), label=runner_label)]
    O.engines += r

    print(f"[FrameCapture] Saving spheres every {interval}s into: {folder}")
    return r


def start_recording(frames_dir, interval, index_path, runner_label="recorder", append=False):
    """Write a frame CSV every ``interval`` seconds of simulated time, from now on.

    Frames go to ``frames_dir/frame_00000.csv``, ``frame_00001.csv``, ...;
    the first one is written on the next step. ``index_path`` gets one row
    per frame (``frame, time, iter``) so frame times are exact even though
    the runner fires on the first step past each period.

    Args:
        frames_dir: Output directory for frame CSVs (created if needed).
        interval: Simulated time between frames (s).
        index_path: CSV path for the frame-time index.
        runner_label: Label for the ``PyRunner`` engine.
        append: Continue an existing recording (an extended record stage):
            keep ``index_path`` and number the new frames after its last one.

    Returns:
        PyRunner: The appended runner.
    """
    os.makedirs(frames_dir, exist_ok=True)
    first = 0
    if append and os.path.exists(index_path):
        with open(index_path, newline="") as f:
            ids = [int(r[0]) for r in list(csv.reader(f))[1:] if r and r[0].isdigit()]
        first = max(ids) + 1 if ids else 0
    _recordingState.clear()
    _recordingState.update(
        {"folder": str(frames_dir), "index": str(index_path), "frame_id": first}
    )
    if not (append and os.path.exists(index_path)):
        with open(index_path, "w", newline="") as f:
            csv.writer(f).writerow(["frame", "time", "iter"])

    runner = PyRunner(command="capture._record_frame()", virtPeriod=float(interval),
                      initRun=True, label=runner_label)
    O.engines += [runner]
    print(f"[Recorder] Saving spheres every {interval}s into: {frames_dir}")
    return runner


def start_preview(preview_dir, index_path, interval, angle_body_id=None, runner_label="preview"):
    """Write a preview snapshot every ``interval`` seconds of simulated time, in any stage.

    Snapshots go to ``preview_dir/snap_00000.csv``, ... (the frame columns),
    each written under a temporary name and renamed when complete;
    ``index_path`` gets one row per snapshot (``snap, time, iter, stage,
    mill_angle_deg``) after its file. A resumed run continues the numbering
    of an existing index and drops its snapshots later than the current
    time (left by the abandoned continuation of a resumed run). Replaces
    a runner already labelled
    ``runner_label``. The runner's command imports this module itself, so it
    works whatever script YADE runs.

    Args:
        preview_dir: Output directory (created if needed).
        index_path: CSV path for the snapshot index.
        interval: Simulated time between snapshots (s); <= 0 does nothing.
        angle_body_id: Id of a mill body (liner facet) whose orientation gives
            the mill angle; ``None`` writes no angle.
        runner_label: Label for the ``PyRunner`` engine.

    Returns:
        PyRunner | None: The appended runner.
    """
    if interval <= 0:
        return None
    os.makedirs(preview_dir, exist_ok=True)
    index_path = str(index_path)
    if _previewState.get("index") != index_path:
        stage = _previewState.get("stage", "")
        _previewState.clear()
        n = _resume_preview_index(preview_dir, index_path, float(O.time))
        _previewState.update(
            {"folder": str(preview_dir), "index": index_path, "snap_id": n, "stage": stage}
        )
    _previewState["angle_body_id"] = angle_body_id
    O.engines = [e for e in O.engines if getattr(e, "label", None) != runner_label]
    runner = PyRunner(
        command=(
            "from pm_dem_sm.simulation.yade_dem import capture as _capture; "
            "_capture._preview_snapshot()"
        ),
        virtPeriod=float(interval),
        initRun=True,
        label=runner_label,
    )
    O.engines += [runner]
    return runner


def set_preview_stage(stage):
    """Set the stage name written to the preview index from now on."""
    _previewState["stage"] = stage


def has_runner(label):
    """Return ``True`` if ``O.engines`` holds an engine labelled ``label``."""
    return any(getattr(e, "label", None) == label for e in O.engines)


def stop_recording(runner_label="recorder"):
    """Remove the recording ``PyRunner`` and return the number of frames written.

    Args:
        runner_label: Label used in :func:`start_recording`.

    Returns:
        int: Frames written since :func:`start_recording`.
    """
    O.engines = [e for e in O.engines if getattr(e, "label", None) != runner_label]
    return _recordingState.get("frame_id", 0)


# --- Private helper functions ------------------------------------------------


def _save_sphere_frame():
    """Write a sphere CSV once ``O.time`` reaches the next interval (``PyRunner`` hook).

    Uses module-level ``_frameCaptureState`` configured by
    :func:`start_frame_capture`. Advances ``frame_id`` and ``next_save_time``.
    """
    st = _frameCaptureState
    if not st:
        return

    t = O.time
    if t < st["next_save_time"]:
        return

    frame_id = st["frame_id"]
    _write_frame(os.path.join(st["folder"], f"frame_{frame_id:05d}.csv"))

    st["frame_id"] += 1
    st["next_save_time"] += st["interval"]


def _record_frame():
    """Write the next frame and its index row (``PyRunner`` hook for :func:`start_recording`)."""
    st = _recordingState
    if not st:
        return
    frame_id = st["frame_id"]
    _write_frame(os.path.join(st["folder"], f"frame_{frame_id:05d}.csv"))
    with open(st["index"], "a", newline="") as f:
        csv.writer(f).writerow([frame_id, repr(float(O.time)), int(O.iter)])
    st["frame_id"] += 1


def _resume_preview_index(preview_dir, index_path, t_now):
    """Prepare the preview index for writing from ``t_now``; return the next snapshot number.

    A missing index is created with its header. An existing one (a resumed
    run) keeps its rows before ``t_now``; the others and their files are
    removed. Numbering continues after the highest number ever used, so no
    file name is reused.
    """
    header = ["snap", "time", "iter", "stage", "mill_angle_deg"]
    if not os.path.exists(index_path):
        with open(index_path, "w", newline="") as f:
            csv.writer(f).writerow(header)
        return 0
    with open(index_path, newline="") as f:
        rows = [r for r in csv.reader(f)][1:]
    keep, n = [], 0
    for r in rows:
        try:
            snap, t = int(r[0]), float(r[1])
        except (ValueError, IndexError):
            continue
        n = max(n, snap + 1)
        if t < t_now - 1e-9:
            keep.append(r)
        else:
            stale = os.path.join(str(preview_dir), f"snap_{snap:05d}.csv")
            if os.path.exists(stale):
                os.remove(stale)
    with open(index_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(keep)
    return n


def _preview_snapshot():
    """Write the next preview snapshot and its index row (``PyRunner`` hook for :func:`start_preview`)."""
    st = _previewState
    if not st:
        return
    snap = st["snap_id"]
    path = os.path.join(st["folder"], f"snap_{snap:05d}.csv")
    _write_frame(path + ".tmp")
    os.replace(path + ".tmp", path)
    angle = _mill_angle_deg(st.get("angle_body_id"))
    with open(st["index"], "a", newline="") as f:
        csv.writer(f).writerow(
            [snap, repr(float(O.time)), int(O.iter), st["stage"], "" if angle is None else angle]
        )
    st["snap_id"] += 1


def _mill_angle_deg(body_id):
    """Return the rotation of body ``body_id`` about +Z in degrees [0, 360), or ``None``."""
    if body_id is None:
        return None
    b = O.bodies[int(body_id)]
    if b is None:
        return None
    axis, angle = b.state.ori.toAxisAngle()
    if axis[2] < 0:
        angle = -angle
    return round(math.degrees(angle) % 360.0, 4)


def _write_frame(filename):
    """Write every sphere's id, position, radius, material label, and velocity to ``filename``.

    Args:
        filename: Output CSV path.
    """
    with open(filename, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id","x","y","z","r","m","vx","vy","vz"])

        for b in O.bodies:
            if not b:
                continue
            if not isinstance(getattr(b, "shape", None), Sphere):
                continue

            p = b.state.pos
            v = b.state.vel

            w.writerow([
                int(b.id),
                float(p[0]), float(p[1]), float(p[2]),
                float(b.shape.radius),
                materials._mat_label(b),
                float(v[0]), float(v[1]), float(v[2]),
            ])

"""Viewer of a DEM run directory (2D end-on or 3D), live while YADE runs or afterwards.

Reads only files the run already writes (``manifest.json``,
``frames_index.csv`` with ``frames/frame_*.csv`` or ``.parquet``,
``preview_index.csv`` with ``preview/snap_*.csv``, ``mill_log.csv``,
``ic/positions.csv``), so it never touches the YADE process and can follow a
run from another terminal. The 2D view shows the particles projected on the
x-y plane (the slice seen from the end wall); the 3D view shows them in the
slice, with the liner's front and back outlines. Particles are coloured by
species or by speed, the liner is turned to the mill angle of the moment,
angle marks (0 deg at 3 o'clock, counter-clockwise, as in
docs/scientific_rationale/15_calibration_targets.md) and the toe / shoulder
targets help read the charge shape by eye, and the stage, time and mill-log
values of that moment are printed below.

Run from the project environment: ``pm-dem-sm dem-view <run-dir>``.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from ..simulation import mill_geometry
from ..simulation.postprocess import SHOULDER_TARGET_DEG, TOE_TARGET_DEG
from ..simulation.scenario import SimulationScenario

# --- Constants ---------------------------------------------------------------

#: Species colours (validated categorical pair, light surface): balls, rocks.
BALL_COLOR = "#2a78d6"
ROCK_COLOR = "#eb6834"
#: Speed colour ramp, one hue from near zero (light) to fast (dark).
SPEED_RAMP = ("#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b")
#: Chart surface, liner, text and guide colours.
SURFACE = "#fcfcfb"
LINER_COLOR = "#52514e"
TEXT_COLOR = "#2b2b29"
GUIDE_COLOR = "#6b6a65"
#: Stages in which the mill turns.
ROTATING_STAGES = ("spinup", "record")
#: Seconds between checks for new frames while following a run.
FOLLOW_INTERVAL_S = 2.0
#: Which views to show: recorded frames, preview snapshots, or both.
SOURCES = ("all", "frames", "preview")
#: Angle marks: a tick every MINOR_TICK_DEG, a label every MAJOR_TICK_DEG.
MINOR_TICK_DEG = 10
MAJOR_TICK_DEG = 30
#: Middle of the SAG_A toe / shoulder target ranges (deg).
TOE_MID_DEG = sum(TOE_TARGET_DEG) / 2.0
SHOULDER_MID_DEG = sum(SHOULDER_TARGET_DEG) / 2.0
#: Columns of :func:`frame_table`.
TABLE_COLUMNS = ["kind", "frame", "time", "path", "stage", "angle_deg"]


# --- Public classes ----------------------------------------------------------


@dataclass
class RunView:
    """What the viewer needs from a run directory.

    Attributes:
        run_dir: The run directory.
        manifest: Parsed ``manifest.json``.
        scenario: The run's scenario.
        omega: Mill angular velocity (rad/s, counter-clockwise).
        rotation_start_s: Simulated time at which the mill starts turning
            (``None`` if it never turns, e.g. ``make_ic``).
        source: Views to list: ``"all"``, ``"frames"`` or ``"preview"``
            (see :func:`frame_table`).
    """

    run_dir: Path
    manifest: dict
    scenario: SimulationScenario
    omega: float
    rotation_start_s: float | None
    source: str = "all"

    @classmethod
    def open(cls, run_dir: Path | str, source: str = "all") -> RunView:
        """Read ``run_dir``'s manifest; raise ``FileNotFoundError`` without one."""
        if source not in SOURCES:
            raise ValueError(f"source must be one of {SOURCES}, got {source!r}")
        run_dir = Path(run_dir)
        manifest = json.loads((run_dir / "manifest.json").read_text())
        scenario = SimulationScenario.from_dict(manifest["scenario"])
        omega = scenario.mill.speed_rpm * 2.0 * math.pi / 60.0
        return cls(run_dir, manifest, scenario, omega, rotation_start(manifest, scenario), source)

    def frames(self) -> pd.DataFrame:
        """Return the views written so far (see :func:`frame_table`)."""
        return frame_table(self.run_dir, self.source)

    def mill_phase(self, t: float) -> float:
        """Return the mill rotation angle (rad) at simulated time ``t``."""
        if self.rotation_start_s is None or t <= self.rotation_start_s:
            return 0.0
        return self.omega * (t - self.rotation_start_s)

    def row_phase(self, row) -> float:
        """Return the mill angle (rad) of a :func:`frame_table` row.

        The angle a preview snapshot recorded (from a liner facet's
        orientation) if present, else :meth:`mill_phase` of its time.
        """
        angle = getattr(row, "angle_deg", None)
        if angle is not None and np.isfinite(angle):
            return math.radians(float(angle))
        return self.mill_phase(float(row.time))


# --- Public functions --------------------------------------------------------


def rotation_start(manifest: dict, scenario: SimulationScenario) -> float | None:
    """Return the simulated time at which the mill starts turning.

    The first rotating stage of the run starts it. If that stage is
    still running (not yet in the manifest), it started when the last
    finished stage ended.

    Args:
        manifest: Parsed ``manifest.json``.
        scenario: The run's scenario.

    Returns:
        float | None: Start time (s), or ``None`` for run types that never rotate.
    """
    stages = scenario.stages
    first = next((s for s in stages if s in ROTATING_STAGES), None)
    if first is None:
        return None
    done = manifest.get("stages", {})
    if first in done:
        return float(done[first]["sim_time_start_s"])
    ends = [float(s["sim_time_end_s"]) for s in done.values() if "sim_time_end_s" in s]
    return max(ends) if ends else 0.0


def frame_table(run_dir: Path | str, source: str = "all") -> pd.DataFrame:
    """Return the views of ``run_dir`` that can be read, in time order.

    - **Frames** (``kind`` ``"frame"``): the recorded frames. A frame counts
      once its ``frames_index.csv`` row exists (YADE writes the row after the
      file); frames that are neither CSV nor parquet (e.g. while ``dem-post``
      converts them) are left out.
    - **Preview snapshots** (``kind`` ``"preview"``): written in every stage
      (``preview_index.csv``, also after the file). With ``source="all"``
      only those outside the recorded frames' time span are kept, since the
      frames are denser there.
    - A run with neither (a ``make_ic`` run made before previews existed)
      gives its saved initial condition (``kind`` ``"ic"``) at the time it
      was saved.

    Args:
        run_dir: Run directory.
        source: ``"all"``, ``"frames"`` or ``"preview"``.

    Returns:
        pandas.DataFrame: Columns :data:`TABLE_COLUMNS` (``stage`` and
        ``angle_deg`` are known for snapshots only).
    """
    run_dir = Path(run_dir)
    frames = _frames(run_dir) if source in ("all", "frames") else []
    previews = _previews(run_dir) if source in ("all", "preview") else []
    if source == "all" and frames:
        t0, t1 = frames[0][2], frames[-1][2]
        previews = [p for p in previews if p[2] < t0 or p[2] > t1]
    rows = sorted(frames + previews, key=lambda r: r[2])
    ic = run_dir / "ic"
    if not rows and source != "preview" and (ic / "positions.csv").exists():
        info = json.loads((ic / "ic.json").read_text()) if (ic / "ic.json").exists() else {}
        rows = [("ic", 0, float(info.get("sim_time_s", 0.0)), ic / "positions.csv", "", np.nan)]
    return pd.DataFrame(rows, columns=TABLE_COLUMNS)


def find_frame(frames: pd.DataFrame, frame: int) -> int:
    """Return the table position of recorded frame ``frame`` (or snapshot ``frame``).

    Raises:
        ValueError: If neither exists.
    """
    for kind in ("frame", "preview", "ic"):
        hits = np.flatnonzero((frames["kind"] == kind).to_numpy() & (frames["frame"] == frame))
        if hits.size:
            return int(hits[0])
    raise ValueError(f"No frame {frame}")


def read_frame(path: Path | str) -> pd.DataFrame:
    """Read one frame (CSV or parquet); columns ``x, y, z, r, m`` and velocities."""
    path = Path(path)
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def log_at(run_dir: Path | str, t: float) -> dict | None:
    """Return the ``mill_log.csv`` row closest to time ``t`` (``None`` if no log)."""
    path = Path(run_dir) / "mill_log.csv"
    if not path.exists():
        return None
    log = pd.read_csv(path, on_bad_lines="skip").dropna(subset=["time"])
    if log.empty:
        return None
    return log.iloc[int((log["time"] - t).abs().idxmin())].to_dict()


def liner_outline(scenario: SimulationScenario, phase: float) -> np.ndarray:
    """Return the closed liner profile at mill angle ``phase`` (rad), shape (N + 1, 2)."""
    points = np.asarray(mill_geometry.liner_profile(scenario.mill, phase=phase))
    return np.vstack([points, points[:1]])


def speed_limit(view: RunView) -> float:
    """Return the top of the speed colour scale: 1.5 x the liner speed (m/s)."""
    return 1.5 * view.omega * mill_geometry.plate_radius(view.scenario.mill) or 1.0


def angle_marks(radius: float) -> dict:
    """Return the angle-mark geometry around a circle of ``radius`` (2D, x-y).

    Angles follow the project convention: 0 deg at 3 o'clock, increasing
    counter-clockwise.

    Returns:
        dict: ``ticks`` (list of ((x0, y0), (x1, y1)) segments, longer at
        labelled angles), ``labels`` (list of (x, y, text)) and ``targets``
        (list of ((x0, y0), (x1, y1), x, y, text): radial guides at the
        middle of the toe and shoulder target ranges, labelled outside the
        angle labels).
    """
    ticks, labels = [], []
    for a in range(0, 360, MINOR_TICK_DEG):
        major = a % MAJOR_TICK_DEG == 0
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        r1 = radius * (1.045 if major else 1.025)
        ticks.append(((radius * 1.005 * c, radius * 1.005 * s), (r1 * c, r1 * s)))
        if major:
            labels.append((radius * 1.10 * c, radius * 1.10 * s, f"{a}°"))
    targets = []
    for a, name in ((TOE_MID_DEG, "toe"), (SHOULDER_MID_DEG, "shoulder")):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        targets.append(
            (
                (0.30 * radius * c, 0.30 * radius * s),
                (1.17 * radius * c, 1.17 * radius * s),
                1.24 * radius * c,
                1.24 * radius * s,
                f"{name}\ntarget {a:.0f}°",
            )
        )
    return {"ticks": ticks, "labels": labels, "targets": targets}


def draw(
    ax,
    view: RunView,
    row,
    color: str = "species",
    vmax: float | None = None,
    live: bool = False,
    marks: bool = True,
):
    """Draw one view in 2D (end-on, x-y) on ``ax`` (cleared first).

    Args:
        ax: Matplotlib axes.
        view: The run.
        row: A row of :meth:`RunView.frames` (see :func:`frame_table`).
        color: ``"species"`` (balls / rocks) or ``"speed"`` (magnitude of the velocity).
        vmax: Top of the speed scale (m/s); ``None`` uses :func:`speed_limit`.
        live: Mark the title as following a running simulation.
        marks: Draw the angle marks and, when the mill turns, the toe /
            shoulder target guides.

    Returns:
        The particle collection (for a colour bar in speed mode).
    """
    from matplotlib.collections import EllipseCollection, LineCollection

    df = read_frame(row.path).sort_values("z")
    ax.clear()
    ax.set_facecolor(SURFACE)
    outline = liner_outline(view.scenario, view.row_phase(row))
    ax.fill(outline[:, 0], outline[:, 1], color="#ffffff", zorder=0)
    ax.plot(outline[:, 0], outline[:, 1], color=LINER_COLOR, lw=1.2, zorder=3)

    diam = 2.0 * df["r"].to_numpy()
    kw = {
        "units": "xy",
        "offsets": df[["x", "y"]].to_numpy(),
        "offset_transform": ax.transData,
        "linewidths": 0,
        "zorder": 2,
    }
    colors, values, cmap, clim = _particle_colors(view, df, color, vmax)
    if values is not None:
        coll = EllipseCollection(diam, diam, 0.0, array=values, cmap=cmap, **kw)
        coll.set_clim(*clim)
    else:
        coll = EllipseCollection(diam, diam, 0.0, facecolors=colors, **kw)
        _species_legend(ax, view, df)
    ax.add_collection(coll)

    radius = float(np.abs(outline).max())
    if marks:
        m = angle_marks(radius)
        ax.add_collection(LineCollection(m["ticks"], colors=GUIDE_COLOR, lw=0.8, zorder=3))
        for x, y, text in m["labels"]:
            ax.text(x, y, text, ha="center", va="center", fontsize=8, color=GUIDE_COLOR)
        if view.rotation_start_s is not None:
            for p0, p1, x, y, text in m["targets"]:
                ax.plot(*zip(p0, p1), color=GUIDE_COLOR, lw=0.9, ls=(0, (4, 3)), zorder=4)
                ax.text(
                    x, y, text, ha="center", va="center", fontsize=8, color=TEXT_COLOR, zorder=4
                )
    lim = radius * (1.32 if marks else 1.04)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(_title(view, row, live), loc="left", fontsize=10, color=TEXT_COLOR)
    ax.text(
        0.0,
        -0.01,
        _status(view, float(row.time)),
        transform=ax.transAxes,
        fontsize=8.5,
        color=TEXT_COLOR,
        family="monospace",
        va="top",
    )
    return coll


def draw3d(
    ax,
    view: RunView,
    row,
    color: str = "species",
    vmax: float | None = None,
    live: bool = False,
    marks: bool = True,
):
    """Draw one view in 3D on ``ax`` (a ``projection="3d"`` axes, cleared first).

    Plot axes: x across, the mill axis z in depth, y up, at true scale (a
    0.6 m slice of a 10.7 m mill is thin). The liner's front (z = 0) and
    back (z = depth) outlines and one lengthwise line per lifter are drawn
    at the mill angle; the angle marks sit on the front face. Drag with
    the mouse to turn the view.

    Args: as :func:`draw`.

    Returns:
        The particle collection (for a colour bar in speed mode).
    """
    df = read_frame(row.path)
    elev, azim = getattr(ax, "elev", 15.0), getattr(ax, "azim", -60.0)
    ax.clear()
    ax.view_init(elev=elev, azim=azim)
    ax.set_facecolor(SURFACE)
    mill = view.scenario.mill
    depth = mill.depth_m
    outline = liner_outline(view.scenario, view.row_phase(row))
    radius = float(np.abs(outline).max())
    for z in (0.0, depth):
        ax.plot(outline[:, 0], np.full(len(outline), z), outline[:, 1], color=LINER_COLOR, lw=0.9)
    step = max(1, (len(outline) - 1) // mill.n_lifters)
    for x, y in outline[:-1:step]:
        ax.plot([x, x], [0.0, depth], [y, y], color=LINER_COLOR, lw=0.4, alpha=0.6)

    colors, values, cmap, clim = _particle_colors(view, df, color, vmax)
    size = _marker_area(ax, 2.0 * df["r"].to_numpy(), 2.0 * radius * 1.1)
    kw = {"s": size, "linewidths": 0, "depthshade": True}
    if values is not None:
        coll = ax.scatter(
            df["x"], df["z"], df["y"], c=values, cmap=cmap, vmin=clim[0], vmax=clim[1], **kw
        )
    else:
        coll = ax.scatter(df["x"], df["z"], df["y"], c=colors, **kw)
        _species_legend(ax, view, df)

    if marks:
        m = angle_marks(radius)
        for (x0, y0), (x1, y1) in m["ticks"]:
            ax.plot([x0, x1], [0.0, 0.0], [y0, y1], color=GUIDE_COLOR, lw=0.7)
        for x, y, text in m["labels"]:
            ax.text(x, 0.0, y, text, ha="center", va="center", fontsize=7, color=GUIDE_COLOR)
        if view.rotation_start_s is not None:
            for p0, p1, x, y, text in m["targets"]:
                ax.plot(
                    [p0[0], p1[0]],
                    [0.0, 0.0],
                    [p0[1], p1[1]],
                    color=GUIDE_COLOR,
                    lw=0.9,
                    ls=(0, (4, 3)),
                )
                ax.text(x, 0.0, y, text, ha="center", va="center", fontsize=7, color=TEXT_COLOR)
    lim = radius * (1.32 if marks else 1.04)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(0.0, depth)
    ax.set_zlim(-lim, lim)
    ax.set_box_aspect((2 * lim, depth, 2 * lim), zoom=1.45)
    ax.set_axis_off()
    ax.set_title(_title(view, row, live), loc="left", fontsize=10, color=TEXT_COLOR)
    ax.text2D(
        0.0,
        0.0,
        _status(view, float(row.time)),
        transform=ax.transAxes,
        fontsize=8.5,
        color=TEXT_COLOR,
        family="monospace",
        va="top",
    )
    return coll


def save(
    view: RunView,
    out: Path | str,
    frame: int | None = None,
    color: str = "species",
    every: int = 1,
    fps: int = 10,
    vmax: float | None = None,
    three_d: bool = False,
    marks: bool = True,
) -> Path:
    """Write a PNG of one view, or a GIF / MP4 of all views.

    Args:
        view: The run.
        out: Output path; ``.png`` gives one view, ``.gif`` / ``.mp4`` an
            animation (``.mp4`` needs ``ffmpeg`` on ``PATH``).
        frame: Frame (or snapshot) for a PNG, see :func:`find_frame`
            (default: the last view).
        color: ``"species"`` or ``"speed"``.
        every: Animation: use every ``every``-th view.
        fps: Animation frames per second.
        vmax: Top of the speed scale (m/s).
        three_d: Draw in 3D (:func:`draw3d`).
        marks: Draw angle marks and target guides.

    Returns:
        Path: ``out``.
    """
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import animation
    import matplotlib.pyplot as plt

    out = Path(out)
    frames = view.frames()
    if frames.empty:
        raise ValueError(f"No frames in {view.run_dir}")
    fig, ax, cax = _figure(plt, three_d)
    paint = draw3d if three_d else draw
    if out.suffix == ".png":
        k = len(frames) - 1 if frame is None else find_frame(frames, frame)
        coll = paint(ax, view, _as_row(frames.iloc[k]), color, vmax, marks=marks)
        _colorbar(fig, cax, coll, color)
        fig.savefig(out, dpi=120, facecolor=SURFACE)
    else:
        rows = [_as_row(r) for _, r in frames.iloc[:: max(1, every)].iterrows()]
        _colorbar(fig, cax, paint(ax, view, rows[0], color, vmax, marks=marks), color)
        anim = animation.FuncAnimation(
            fig,
            lambda k: [paint(ax, view, rows[k], color, vmax, marks=marks)],
            frames=len(rows),
        )
        if out.suffix == ".mp4":
            writer = animation.FFMpegWriter(fps=fps)
        else:
            writer = animation.PillowWriter(fps=fps)
        anim.save(out, writer=writer, dpi=90, savefig_kwargs={"facecolor": SURFACE})
    plt.close(fig)
    return out


def show(
    view: RunView,
    frame: int | None = None,
    color: str = "species",
    vmax: float | None = None,
    fps: int = 10,
    follow_s: float = FOLLOW_INTERVAL_S,
    block: bool = True,
    three_d: bool = False,
    marks: bool = True,
) -> dict:
    """Open the interactive viewer window.

    It starts on ``frame`` (or the newest view, following new ones as the
    run writes them). Keys: left / right one view, down / up ten views,
    home / end first / last, space play / pause, ``f`` follow new views,
    ``c`` species / speed colours, ``m`` angle marks on / off, ``s`` save a
    PNG next to the run. In 3D, drag with the mouse to turn the view.

    Args:
        view: The run.
        frame: Frame (or snapshot) to start on, see :func:`find_frame`
            (``None``: newest, following).
        color: ``"species"`` or ``"speed"``.
        vmax: Top of the speed scale (m/s).
        fps: Playback speed (views per second).
        follow_s: Seconds between checks for new views while following.
        block: Wait until the window is closed.
        three_d: Draw in 3D (:func:`draw3d`).
        marks: Start with the angle marks shown.

    Returns:
        dict: ``fig``, ``state`` (``frames``, ``k``, ``follow``, ``play``,
        ``color``, ``marks``) and ``tick`` (the timer callback), for tests.
    """
    import matplotlib.pyplot as plt

    state = {
        "frames": view.frames(),
        "k": 0,
        "follow": frame is None,
        "play": False,
        "color": color,
        "marks": marks,
    }
    if state["frames"].empty:
        raise ValueError(f"No frames yet in {view.run_dir}")
    state["k"] = len(state["frames"]) - 1 if frame is None else find_frame(state["frames"], frame)
    fig, ax, cax = _figure(plt, three_d)
    fig.canvas.manager.set_window_title(f"dem-view: {view.run_dir.name}")
    paint = draw3d if three_d else draw

    def render():
        k = max(0, min(state["k"], len(state["frames"]) - 1))
        state["k"] = k
        row = _as_row(state["frames"].iloc[k])
        coll = paint(
            ax, view, row, state["color"], vmax, live=state["follow"], marks=state["marks"]
        )
        _colorbar(fig, cax, coll, state["color"])
        fig.canvas.draw_idle()

    def tick():
        if state["play"]:
            if state["k"] < len(state["frames"]) - 1:
                state["k"] += 1
                render()
            else:
                state["play"] = False
                _retime()
            return
        if state["follow"]:
            fresh = view.frames()
            if len(fresh) > len(state["frames"]):
                state["frames"] = fresh
                state["k"] = len(fresh) - 1
                render()

    timer = fig.canvas.new_timer(interval=int(follow_s * 1000))
    timer.add_callback(tick)

    def _retime():
        timer.stop()
        timer.interval = int(1000 / fps) if state["play"] else int(follow_s * 1000)
        timer.start()

    def on_key(event):
        n = len(state["frames"])
        steps = {"right": 1, "left": -1, "up": 10, "down": -10}
        if event.key in steps:
            state["follow"] = False
            state["k"] += steps[event.key]
        elif event.key == "home":
            state["follow"], state["k"] = False, 0
        elif event.key == "end":
            state["frames"] = view.frames()
            state["k"] = len(state["frames"]) - 1
        elif event.key == " ":
            state["play"] = not state["play"]
            state["follow"] = False
            if state["play"] and state["k"] >= n - 1:
                state["k"] = 0
            _retime()
        elif event.key == "f":
            state["follow"] = not state["follow"]
            state["play"] = False
            if state["follow"]:
                state["frames"] = view.frames()
                state["k"] = len(state["frames"]) - 1
            _retime()
        elif event.key == "c":
            state["color"] = "speed" if state["color"] == "species" else "species"
        elif event.key == "m":
            state["marks"] = not state["marks"]
        elif event.key == "s":
            row = state["frames"].iloc[state["k"]]
            name = "snap" if row["kind"] == "preview" else "frame"
            out = view.run_dir / f"view_{name}_{int(row['frame']):05d}.png"
            fig.savefig(out, dpi=120, facecolor=SURFACE)
            print(f"[dem-view] saved {out}")
            return
        else:
            return
        render()

    fig.canvas.mpl_connect("key_press_event", on_key)
    render()
    timer.start()
    if block:
        plt.show()
    return {"fig": fig, "state": state, "tick": tick}


# --- Private helper functions ------------------------------------------------


def _frames(run_dir):
    """Return the readable recorded frames as table tuples."""
    index = run_dir / "frames_index.csv"
    rows = []
    if not index.exists():
        return rows
    table = pd.read_csv(index, on_bad_lines="skip").dropna()
    for frame, time in zip(table["frame"].astype(int), table["time"].astype(float)):
        stem = run_dir / "frames" / f"frame_{frame:05d}"
        for path in (stem.with_suffix(".parquet"), stem.with_suffix(".csv")):
            if path.exists():
                rows.append(("frame", frame, time, path, "record", np.nan))
                break
    return rows


def _previews(run_dir):
    """Return the preview snapshots as table tuples."""
    index = run_dir / "preview_index.csv"
    rows = []
    if not index.exists():
        return rows
    table = pd.read_csv(index, on_bad_lines="skip").dropna(subset=["snap", "time"])
    for rec in table.itertuples(index=False):
        path = run_dir / "preview" / f"snap_{int(rec.snap):05d}.csv"
        if path.exists():
            angle = pd.to_numeric(rec.mill_angle_deg, errors="coerce")
            stage = "" if pd.isna(rec.stage) else str(rec.stage)
            rows.append(("preview", int(rec.snap), float(rec.time), path, stage, float(angle)))
    return rows


def _as_row(row):
    """Return a table row as an object with attribute access."""
    angle = row.get("angle_deg", np.nan)
    return SimpleNamespace(
        kind=row.get("kind", "frame"),
        frame=int(row["frame"]),
        time=float(row["time"]),
        path=row["path"],
        stage=row.get("stage", ""),
        angle_deg=float(angle) if angle is not None else np.nan,
    )


def _particle_colors(view, df, color, vmax):
    """Return (colors, values, cmap, clim): species colours or speed values."""
    if color == "speed":
        from matplotlib.colors import LinearSegmentedColormap

        speed = np.sqrt(df["vx"] ** 2 + df["vy"] ** 2 + df["vz"] ** 2).to_numpy()
        cmap = LinearSegmentedColormap.from_list("speed", SPEED_RAMP)
        return None, speed, cmap, (0.0, vmax or speed_limit(view))
    return np.where(_is_ball(view, df), BALL_COLOR, ROCK_COLOR), None, None, None


def _is_ball(view, df):
    """Return a boolean array: rows of the large species."""
    large = max(view.scenario.species, key=lambda sp: sp.radius_m).material
    return (df["m"].astype(str) == large).to_numpy()


def _species_legend(ax, view, df):
    """Add the balls / rocks legend with counts."""
    n_ball = int(_is_ball(view, df).sum())
    ax.legend(
        handles=[
            _dot(BALL_COLOR, f"balls ({n_ball:,})"),
            _dot(ROCK_COLOR, f"rocks ({len(df) - n_ball:,})"),
        ],
        loc="upper left",
        frameon=False,
        labelcolor=TEXT_COLOR,
        fontsize=9,
    )


def _marker_area(ax, diam, span):
    """Return scatter areas (pt^2) that draw diameters ``diam`` at roughly data scale."""
    fig = ax.get_figure()
    width_pt = fig.get_figwidth() * 72.0 * ax.get_position().width * 0.75
    return (np.asarray(diam) / span * width_pt) ** 2


def _figure(plt, three_d=False):
    """Return a figure with the plot axes and a colour-bar axes beside it."""
    fig = plt.figure(figsize=(8.6, 8.6), facecolor=SURFACE)
    rect = (0.02, 0.07, 0.86, 0.87)
    ax = fig.add_axes(rect, projection="3d") if three_d else fig.add_axes(rect)
    cax = fig.add_axes((0.90, 0.30, 0.018, 0.40))
    return fig, ax, cax


def _colorbar(fig, cax, coll, color):
    """Show the speed colour bar in ``cax`` (hidden in species mode)."""
    cax.clear()
    cax.set_visible(color == "speed")
    if color == "speed":
        bar = fig.colorbar(coll, cax=cax)
        bar.set_label("speed |v| (m/s)", color=TEXT_COLOR)
        bar.outline.set_visible(False)


def _dot(color, label):
    """Return a legend handle: a filled circle of ``color``."""
    from matplotlib.lines import Line2D

    return Line2D(
        [],
        [],
        marker="o",
        ls="",
        markersize=8,
        markerfacecolor=color,
        markeredgewidth=0,
        label=label,
    )


def _title(view, row, live):
    """Return the title line: run, type, view, time, mill speed and direction."""
    s = view.scenario
    tag = "  [following]" if live else ""
    if view.rotation_start_s is None:
        motion = "mill at rest"
    else:
        motion = f"{s.mill.speed_rpm:g} rpm counter-clockwise"
    kind = getattr(row, "kind", "frame")
    if kind == "ic" or Path(row.path).parent.name == "ic":
        what = "saved starting packing"
    elif kind == "preview":
        what = f"snapshot {row.frame} ({row.stage})"
    else:
        what = f"frame {row.frame}"
    return f"{view.run_dir.name}  ({s.run.type})   {what}   t = {row.time:.2f} s   {motion}{tag}"


def _status(view, t):
    """Return the mill-log lines for time ``t`` (empty if there is no log)."""
    log = log_at(view.run_dir, t)
    if log is None:
        return ""
    return (
        f"stage {log['stage']}   revolutions {float(log['revolutions']):.2f}   "
        f"charge angle {float(log['angle_all_deg']):.1f} deg\n"
        f"power {float(log['power_kW']):.0f} kW   kinetic energy "
        f"{float(log['kinetic_J']) / 1000:.1f} kJ   mean speed "
        f"{float(log['mean_speed_m_s']):.2f} m/s"
    )

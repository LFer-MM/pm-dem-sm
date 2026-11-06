"""2D end-on viewer of a DEM run directory, live while YADE runs or afterwards.

Reads only files the run already writes (``manifest.json``,
``frames_index.csv``, ``frames/frame_*.csv`` or ``.parquet``, ``mill_log.csv``,
``ic/positions.csv``), so it never touches the YADE process and can follow a
run from another terminal. Each view shows the particles projected on the
x-y plane (the slice seen from the end wall), coloured by species or by
speed, inside the liner outline rotated to the frame's mill angle, with the
stage, time and mill-log values of that moment.

Run from the project environment: ``pm-dem-sm dem-view <run-dir>``.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from ..simulation import mill_geometry
from ..simulation.scenario import RUN_TYPE_STAGES, SimulationScenario

# --- Constants ---------------------------------------------------------------

#: Species colours (validated categorical pair, light surface): balls, rocks.
BALL_COLOR = "#2a78d6"
ROCK_COLOR = "#eb6834"
#: Speed colour ramp, one hue from near zero (light) to fast (dark).
SPEED_RAMP = ("#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b")
#: Chart surface, liner and text colours.
SURFACE = "#fcfcfb"
LINER_COLOR = "#52514e"
TEXT_COLOR = "#2b2b29"
#: Stages in which the mill turns.
ROTATING_STAGES = ("spinup", "record")
#: Seconds between checks for new frames while following a run.
FOLLOW_INTERVAL_S = 2.0


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
    """

    run_dir: Path
    manifest: dict
    scenario: SimulationScenario
    omega: float
    rotation_start_s: float | None

    @classmethod
    def open(cls, run_dir: Path | str) -> RunView:
        """Read ``run_dir``'s manifest; raise ``FileNotFoundError`` without one."""
        run_dir = Path(run_dir)
        manifest = json.loads((run_dir / "manifest.json").read_text())
        scenario = SimulationScenario.from_dict(manifest["scenario"])
        omega = scenario.mill.speed_rpm * 2.0 * math.pi / 60.0
        return cls(run_dir, manifest, scenario, omega, rotation_start(manifest, scenario))

    def frames(self) -> pd.DataFrame:
        """Return the frames written so far (see :func:`frame_table`)."""
        return frame_table(self.run_dir)

    def mill_phase(self, t: float) -> float:
        """Return the mill rotation angle (rad) at simulated time ``t``."""
        if self.rotation_start_s is None or t <= self.rotation_start_s:
            return 0.0
        return self.omega * (t - self.rotation_start_s)


# --- Public functions --------------------------------------------------------


def rotation_start(manifest: dict, scenario: SimulationScenario) -> float | None:
    """Return the simulated time at which the mill starts turning.

    The first rotating stage of the run type starts it. If that stage is
    still running (not yet in the manifest), it started when the last
    finished stage ended.

    Args:
        manifest: Parsed ``manifest.json``.
        scenario: The run's scenario.

    Returns:
        float | None: Start time (s), or ``None`` for run types that never rotate.
    """
    stages = RUN_TYPE_STAGES[scenario.run.type]
    first = next((s for s in stages if s in ROTATING_STAGES), None)
    if first is None:
        return None
    done = manifest.get("stages", {})
    if first in done:
        return float(done[first]["sim_time_start_s"])
    ends = [float(s["sim_time_end_s"]) for s in done.values() if "sim_time_end_s" in s]
    return max(ends) if ends else 0.0


def frame_table(run_dir: Path | str) -> pd.DataFrame:
    """Return the frames of ``run_dir`` that can be read, in order.

    A frame counts once its ``frames_index.csv`` row exists (YADE writes the
    row after the file). Frames that are neither CSV nor parquet (e.g. while
    ``dem-post`` converts them) are left out. A ``make_ic`` run without frames
    gives its saved initial condition as a single frame (at the time it was
    saved, from ``ic/ic.json``).

    Args:
        run_dir: Run directory.

    Returns:
        pandas.DataFrame: Columns ``frame``, ``time``, ``path``.
    """
    run_dir = Path(run_dir)
    index = run_dir / "frames_index.csv"
    rows = []
    if index.exists():
        table = pd.read_csv(index, on_bad_lines="skip").dropna()
        for frame, time in zip(table["frame"].astype(int), table["time"].astype(float)):
            stem = run_dir / "frames" / f"frame_{frame:05d}"
            path = next(
                (
                    p
                    for p in (stem.with_suffix(".parquet"), stem.with_suffix(".csv"))
                    if p.exists()
                ),
                None,
            )
            if path is not None:
                rows.append((frame, time, path))
    ic = run_dir / "ic"
    if not rows and (ic / "positions.csv").exists():
        info = json.loads((ic / "ic.json").read_text()) if (ic / "ic.json").exists() else {}
        rows.append((0, float(info.get("sim_time_s", 0.0)), ic / "positions.csv"))
    return pd.DataFrame(rows, columns=["frame", "time", "path"])


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


def draw(
    ax, view: RunView, row, color: str = "species", vmax: float | None = None, live: bool = False
):
    """Draw one frame on ``ax`` (cleared first).

    Args:
        ax: Matplotlib axes.
        view: The run.
        row: A row of :meth:`RunView.frames` (``frame``, ``time``, ``path``).
        color: ``"species"`` (balls / rocks) or ``"speed"`` (magnitude of the velocity).
        vmax: Top of the speed scale (m/s); ``None`` uses :func:`speed_limit`.
        live: Mark the title as following a running simulation.

    Returns:
        The particle collection (for a colour bar in speed mode).
    """
    from matplotlib.collections import EllipseCollection
    from matplotlib.colors import LinearSegmentedColormap

    df = read_frame(row.path).sort_values("z")
    t = float(row.time)
    ax.clear()
    ax.set_facecolor(SURFACE)
    outline = liner_outline(view.scenario, view.mill_phase(t))
    ax.fill(outline[:, 0], outline[:, 1], color="#ffffff", zorder=0)
    ax.plot(outline[:, 0], outline[:, 1], color=LINER_COLOR, lw=1.2, zorder=3)

    xy = df[["x", "y"]].to_numpy()
    diam = 2.0 * df["r"].to_numpy()
    kw = {
        "units": "xy",
        "offsets": xy,
        "offset_transform": ax.transData,
        "linewidths": 0,
        "zorder": 2,
    }
    if color == "speed":
        speed = np.sqrt(df["vx"] ** 2 + df["vy"] ** 2 + df["vz"] ** 2).to_numpy()
        cmap = LinearSegmentedColormap.from_list("speed", SPEED_RAMP)
        coll = EllipseCollection(diam, diam, 0.0, array=speed, cmap=cmap, **kw)
        coll.set_clim(0.0, vmax or speed_limit(view))
    else:
        large = max(view.scenario.species, key=lambda sp: sp.radius_m).material
        is_ball = (df["m"].astype(str) == large).to_numpy()
        colors = np.where(is_ball, BALL_COLOR, ROCK_COLOR)
        coll = EllipseCollection(diam, diam, 0.0, facecolors=colors, **kw)
        n_ball = int(is_ball.sum())
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
    ax.add_collection(coll)

    r = float(np.abs(outline).max()) * 1.04
    ax.set_xlim(-r, r)
    ax.set_ylim(-r, r)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(_title(view, row, live), loc="left", fontsize=10, color=TEXT_COLOR)
    ax.text(
        0.0,
        -0.01,
        _status(view, t),
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
) -> Path:
    """Write a PNG of one frame, or a GIF / MP4 of all frames.

    Args:
        view: The run.
        out: Output path; ``.png`` gives one frame, ``.gif`` / ``.mp4`` an
            animation (``.mp4`` needs ``ffmpeg`` on ``PATH``).
        frame: Frame for a PNG (default: the last one).
        color: ``"species"`` or ``"speed"``.
        every: Animation: use every ``every``-th frame.
        fps: Animation frames per second.
        vmax: Top of the speed scale (m/s).

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
    fig, ax, cax = _figure(plt)
    if out.suffix == ".png":
        if frame is None:
            row = frames.iloc[-1]
        else:
            match = frames[frames["frame"] == frame]
            if match.empty:
                raise ValueError(f"No frame {frame} in {view.run_dir}")
            row = match.iloc[0]
        _colorbar(fig, cax, draw(ax, view, _as_row(row), color, vmax), color)
        fig.savefig(out, dpi=120, facecolor=SURFACE)
    else:
        rows = list(frames.iloc[:: max(1, every)].itertuples(index=False))
        _colorbar(fig, cax, draw(ax, view, rows[0], color, vmax), color)
        anim = animation.FuncAnimation(
            fig, lambda k: [draw(ax, view, rows[k], color, vmax)], frames=len(rows)
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
) -> dict:
    """Open the interactive viewer window.

    It starts on ``frame`` (or the newest frame, following new ones as the
    run writes them). Keys: left / right one frame, down / up ten frames,
    home / end first / last, space play / pause, ``f`` follow new frames,
    ``c`` species / speed colours, ``s`` save a PNG next to the run.

    Args:
        view: The run.
        frame: Frame to start on (``None``: newest, following).
        color: ``"species"`` or ``"speed"``.
        vmax: Top of the speed scale (m/s).
        fps: Playback speed (frames per second).
        follow_s: Seconds between checks for new frames while following.
        block: Wait until the window is closed.

    Returns:
        dict: ``fig``, ``state`` (``frames``, ``k``, ``follow``, ``play``,
        ``color``) and ``tick`` (the timer callback), for tests.
    """
    import matplotlib.pyplot as plt

    state = {
        "frames": view.frames(),
        "k": 0,
        "follow": frame is None,
        "play": False,
        "color": color,
    }
    if state["frames"].empty:
        raise ValueError(f"No frames yet in {view.run_dir}")
    state["k"] = (
        len(state["frames"]) - 1
        if frame is None
        else int(np.searchsorted(state["frames"]["frame"].to_numpy(), frame))
    )
    fig, ax, cax = _figure(plt)
    fig.canvas.manager.set_window_title(f"dem-view: {view.run_dir.name}")

    def render():
        k = max(0, min(state["k"], len(state["frames"]) - 1))
        state["k"] = k
        row = state["frames"].iloc[k]
        coll = draw(ax, view, _as_row(row), state["color"], vmax, live=state["follow"])
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
        elif event.key == "s":
            row = state["frames"].iloc[state["k"]]
            out = view.run_dir / f"view_frame_{int(row.frame):05d}.png"
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


def _as_row(row):
    """Return ``row`` as an object with ``frame``, ``time`` and ``path`` attributes."""
    from types import SimpleNamespace

    frame = int(row["frame"])
    return SimpleNamespace(frame=frame, time=float(row["time"]), path=row["path"])


def _figure(plt):
    """Return a figure with the plot axes and a colour-bar axes beside it."""
    fig = plt.figure(figsize=(8.6, 8.6), facecolor=SURFACE)
    ax = fig.add_axes((0.02, 0.07, 0.86, 0.87))
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
    """Return the title line: run, type, frame, time, mill speed and direction."""
    s = view.scenario
    tag = "  [following]" if live else ""
    t = float(row.time)
    if view.rotation_start_s is None:
        motion = "mill at rest"
    else:
        motion = f"{s.mill.speed_rpm:g} rpm counter-clockwise"
    what = (
        "saved starting packing"
        if Path(row.path).parent.name == "ic"
        else f"frame {int(row.frame)}"
    )
    return f"{view.run_dir.name}  ({s.run.type})   {what}   t = {t:.2f} s   {motion}{tag}"


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

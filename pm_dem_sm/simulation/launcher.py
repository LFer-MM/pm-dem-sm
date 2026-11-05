"""Launches a DEM simulation as a subprocess from the normal Python environment.

Shared across DEM backends -- it dispatches on ``backend`` but never imports
either backend's own Python API itself. YADE ships as its own patched Python
interpreter (Boost.Python bindings baked in) and cannot be imported into this
package's TensorFlow/pandas venv -- that's why
:mod:`pm_dem_sm.simulation.yade_dem` only runs under ``yade``, never under
this package's own interpreter. This module never imports yade (or a future
BlazeDEM binding); it only shells out to the backend's executable, gated on
it actually being installed on the workstation.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from .scenario import load_scenario

# --- Constants ---------------------------------------------------------------

#: Packaged scenario script per DEM backend, run by :func:`launch_simulation`.
DEFAULT_SIMULATION_SCRIPTS = {
    "yade": Path(__file__).resolve().parent / "yade_dem" / "run_simulation.py",
    "blaze": Path(__file__).resolve().parent / "blaze_dem" / "run_simulation.py",
}
#: The YADE entry of :data:`DEFAULT_SIMULATION_SCRIPTS`.
DEFAULT_SIMULATION_SCRIPT = DEFAULT_SIMULATION_SCRIPTS["yade"]
#: YADE executable names tried, in order, when none is given (release, then daily build).
YADE_EXECUTABLES = ("yade", "yadedaily")


# --- Public functions --------------------------------------------------------


def find_yade_executable(name: str | None = None) -> str | None:
    """Locate the YADE executable on PATH.

    Args:
        name: Executable name or path to look up (e.g. a version-suffixed
            build like ``"yade-2024.02a"``); ``None`` tries each of
            :data:`YADE_EXECUTABLES` in turn.

    Returns:
        str | None: Absolute path to the executable, or ``None`` if not found.
    """
    for candidate in (name,) if name else YADE_EXECUTABLES:
        resolved = shutil.which(candidate)
        if resolved is not None:
            return resolved
    return None


def default_run_dir(scenario: Path | str | None = None, seed: int | None = None) -> Path:
    """Return the run directory ``run_simulation.py`` uses when none is given.

    ``data/raw/yade_runs/<scenario name>``, with ``_s<seed>`` appended when a
    seed override is passed (as ``run_simulation.run`` does).

    Args:
        scenario: Scenario JSON, or ``None`` for the defaults.
        seed: Seed override, or ``None``.

    Returns:
        Path: The run directory.
    """
    name = load_scenario(scenario).name
    if seed is not None:
        name = f"{name}_s{seed}"
    return Path(__file__).resolve().parents[2] / "data" / "raw" / "yade_runs" / name


def build_command(
    yade_path: str,
    script: Path | str | None = None,
    scenario: Path | str | None = None,
    run_dir: Path | str | None = None,
    threads: int | None = None,
    headless: bool = True,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build the YADE command line for a scenario run.

    Args:
        yade_path: Resolved YADE executable.
        script: Script to run; defaults to :data:`DEFAULT_SIMULATION_SCRIPT`.
        scenario: Scenario JSON passed as ``--scenario``.
        run_dir: Output directory passed as ``--run-dir``.
        threads: OpenMP threads (YADE ``-j``); ``None`` leaves YADE's default.
        headless: If ``True``, run without the GUI and exit when the script
            ends (YADE ``-n -x``).
        extra_args: Further arguments for the script (e.g.
            ``["--from-stage", "spinup"]``).

    Returns:
        list[str]: The command, ready for :func:`subprocess.run`.
    """
    cmd = [yade_path]
    if headless:
        cmd += ["-n", "-x"]
    if threads:
        cmd += ["-j", str(threads)]
    cmd.append(str(Path(script) if script is not None else DEFAULT_SIMULATION_SCRIPT))
    if scenario is not None:
        cmd += ["--scenario", str(scenario)]
    if run_dir is not None:
        cmd += ["--run-dir", str(run_dir)]
    return cmd + list(extra_args or [])


def launch_simulation(
    script: Path | str | None = None,
    yade_executable: str | None = None,
    extra_args: list[str] | None = None,
    backend: str = "yade",
    scenario: Path | str | None = None,
    run_dir: Path | str | None = None,
    threads: int | None = None,
    headless: bool = True,
) -> subprocess.CompletedProcess:
    """Run a DEM simulation script as a subprocess.

    When ``scenario`` is given it is loaded first
    (:func:`pm_dem_sm.simulation.scenario.load_scenario`), so an invalid
    scenario fails here instead of inside YADE; its warnings are printed and
    its ``solver.threads`` is used when ``threads`` is ``None``.

    Args:
        script: Path to the script to run; defaults to the packaged
            ``run_simulation.py`` for ``backend``
            (:data:`DEFAULT_SIMULATION_SCRIPTS`).
        yade_executable: YADE executable name or path; ``None`` tries
            :data:`YADE_EXECUTABLES`. Only used when ``backend == "yade"``.
        extra_args: Additional arguments forwarded to the script.
        backend: Which DEM backend to launch -- ``"yade"`` (implemented) or
            ``"blaze"`` (not yet implemented; raises ``NotImplementedError``).
        scenario: Scenario JSON for the run.
        run_dir: Output directory for the run.
        threads: OpenMP threads for YADE.
        headless: Run without the GUI (``-n -x``).

    Returns:
        subprocess.CompletedProcess: Result of the completed DEM run (check
        ``.returncode``; this function does not raise on a nonzero exit).

    Raises:
        FileNotFoundError: If no YADE executable is found on PATH.
        NotImplementedError: If ``backend`` is not ``"yade"`` -- BlazeDEM's
            launch mechanism (executable name, invocation style) isn't
            decided yet; see :mod:`pm_dem_sm.simulation.blaze_dem`.
    """
    if backend != "yade":
        raise NotImplementedError(
            f"DEM backend {backend!r} not yet implemented in launch_simulation() "
            "-- only 'yade' can be launched today."
        )

    resolved = find_yade_executable(yade_executable)
    if resolved is None:
        tried = yade_executable or " / ".join(YADE_EXECUTABLES)
        raise FileNotFoundError(
            f"YADE executable {tried!r} not found on PATH. "
            "Install YADE and ensure it is on PATH to run DEM simulations."
        )

    if scenario is not None:
        loaded = load_scenario(scenario)
        for warning in loaded.warnings():
            print(f"[scenario] WARNING: {warning}")
        if threads is None:
            threads = loaded.solver.threads

    cmd = build_command(
        resolved,
        script if script is not None else DEFAULT_SIMULATION_SCRIPTS[backend],
        scenario=scenario,
        run_dir=run_dir,
        threads=threads,
        headless=headless,
        extra_args=extra_args,
    )
    print(f"Launching DEM simulation: {' '.join(cmd)}")
    return subprocess.run(cmd, check=False)

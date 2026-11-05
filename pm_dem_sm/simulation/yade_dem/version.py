"""YADE version parsing and the release floor of the restitution mapping.

YADE's Hertz-Mindlin law maps the input restitution e to a damping ratio with
Thornton et al.'s Hertz-specific relation only from release 2023.02 on;
2021-2022 releases used the linear-spring formula, which gives a different,
velocity-dependent restitution (docs/scientific_rationale/07_restitution.md).
:func:`check_yade_version` refuses those older builds. Stdlib-only, so it is
tested without YADE.
"""

from __future__ import annotations

import re

# --- Constants ---------------------------------------------------------------

#: Oldest accepted YADE release, as ``(year, month)``.
MIN_YADE_VERSION = (2023, 2)

# Release tags such as ``2023.02a`` and daily builds such as
# ``20260115-8983~7c8d01e~noble1`` (``yadedaily``).
_RELEASE = re.compile(r"^(\d{4})\.(\d{2})")
_DAILY = re.compile(r"^(\d{4})(\d{2})(\d{2})(?!\d)")


# --- Public functions --------------------------------------------------------


def parse_yade_version(version: str) -> tuple[int, int]:
    """Return ``(year, month)`` of a YADE version string.

    Args:
        version: ``yade.config.version``, e.g. ``"2023.02a"`` (release) or
            ``"20260115-8983~7c8d01e~noble1"`` (daily build).

    Returns:
        tuple[int, int]: Release (or build) year and month.

    Raises:
        ValueError: If the string matches neither form.
    """
    text = str(version).strip()
    match = _RELEASE.match(text) or _DAILY.match(text)
    if not match:
        raise ValueError(f"Unrecognized YADE version string: {version!r}")
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12:
        raise ValueError(f"Unrecognized YADE version string: {version!r}")
    return year, month


def check_yade_version(version: str) -> tuple[int, int]:
    """Raise unless ``version`` is YADE 2023.02 or newer; return its ``(year, month)``.

    Args:
        version: ``yade.config.version``.

    Returns:
        tuple[int, int]: Parsed ``(year, month)``.

    Raises:
        RuntimeError: If the version is older than :data:`MIN_YADE_VERSION`
            or cannot be parsed (the floor cannot be verified).
    """
    floor = f"{MIN_YADE_VERSION[0]}.{MIN_YADE_VERSION[1]:02d}"
    try:
        parsed = parse_yade_version(version)
    except ValueError as exc:
        raise RuntimeError(f"{exc}; cannot verify YADE >= {floor}") from exc
    if parsed < MIN_YADE_VERSION:
        raise RuntimeError(
            f"YADE {version} is older than {floor}: its Hertz-Mindlin restitution mapping "
            "differs (docs/scientific_rationale/07_restitution.md). Use a newer YADE."
        )
    return parsed

"""Tests for the YADE version floor (stdlib only, no YADE needed)."""

from __future__ import annotations

import pytest

from pm_dem_sm.simulation.yade_dem.version import check_yade_version, parse_yade_version


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("2023.02", (2023, 2)),
        ("2023.02a", (2023, 2)),
        ("2022.01a", (2022, 1)),
        ("20260115", (2026, 1)),
        ("20260115-8983~7c8d01e~noble1", (2026, 1)),
    ],
)
def test_parse_yade_version(version, expected):
    assert parse_yade_version(version) == expected


@pytest.mark.parametrize("version", ["unknown", "", "2023", "20261315", "202601151"])
def test_parse_rejects_unrecognized(version):
    with pytest.raises(ValueError, match="Unrecognized"):
        parse_yade_version(version)


@pytest.mark.parametrize("version", ["2023.02", "2023.02a", "20260115-8983~7c8d01e~noble1"])
def test_check_accepts_2023_02_and_newer(version):
    assert check_yade_version(version) >= (2023, 2)


@pytest.mark.parametrize("version", ["2022.01", "2022.01a", "2021.01a", "20230115"])
def test_check_refuses_older(version):
    with pytest.raises(RuntimeError, match="older than 2023.02"):
        check_yade_version(version)


def test_check_refuses_unparseable():
    with pytest.raises(RuntimeError, match="cannot verify"):
        check_yade_version("unknown")

"""Golden tests: the vendored verifier must reproduce the dual-verifier
outputs committed alongside coordinates, byte-for-byte on the exact fields.
Fixtures live under tests/fixtures/golden/ only: submission directories
get overwritten by better coordinates, so a verify_output.json must never sit
next to live data."""

import json
import pathlib

import pytest

from build.vendor.verify_exact import parse_points_text, verify

SOURCES = pathlib.Path(__file__).resolve().parent.parent / "data" / "sources"

GOLDEN = pathlib.Path(__file__).resolve().parent / "fixtures" / "golden"

FIXTURES = sorted(d for d in GOLDEN.iterdir()
                  if d.is_dir() and (d / "verify_output.json").exists())


@pytest.mark.parametrize("d", FIXTURES, ids=lambda d: d.name)
def test_matches_upstream_verify_output(d):
    variant = d.name.split("-")[0]
    points = parse_points_text((d / "coordinates.txt").read_text())
    expected = json.loads((d / "verify_output.json").read_text())["a"]
    got = verify(variant, points)
    assert got["value_fraction"] == expected["value_fraction"]
    assert got["min_triple"] == expected["min_triple"]
    assert got["num_min_ties"] == expected["num_min_ties"]
    assert got["feasible"] is True
    assert got["hull_vertex_count"] == expected["hull_vertex_count"]


def test_square_n11_is_goldberg_exact():
    """Goldberg's n=11 value is exactly 1/27 only in the limit; the vendored
    float coordinates must evaluate within the published display window."""
    import fractions
    data = json.loads((SOURCES / "spiralulam" / "config_n11.json").read_text())
    pts = [(fractions.Fraction(repr(float(x))), fractions.Fraction(repr(float(y))))
           for x, y in data["points"]]
    res = verify("square", pts)
    assert abs(res["_value"] - fractions.Fraction(1, 27)) < fractions.Fraction(1, 10**12)

"""Exact one-parameter families of optimal configurations.

Five proven entries are non-unique, and for each the family (or a
one-parameter slice of it) has an exact closed form derived on this site:

  square n=3    apex slides along the top edge: p2 = (x, 1), x in [0, 1].
  square n=6    the shear x -> x + t(1-2y) applied to the point set,
                t in [0, 1/2]; a shear is area-preserving, so every
                triangle's area is invariant. t = 1/2 is the 90-degree
                rotation image of t = 0. (Dress-Yang-Zeng family.)
  triangle n=5  p1 slides along the hypotenuse: (1-x, x),
                x in [2-sqrt(2), 1/sqrt(2)]  (right frame, mirror
                oriented vertically as ingest stores it).
  triangle n=6  p2 slides along the left edge: (0, y), y in [1/4, 3/8].
  convex n=7    center + two equilateral orbits 30 degrees apart, radius
                ratio s in [sqrt(3)/2, 2/sqrt(3)]; samples rescaled so the
                hull area stays that of the stored member.

Every emitted sample is a 30-decimal truncation of an exact family member,
and generate() verifies each sample's exact-literal value against the
stored configuration's exact value at relative 1e-20 — the build fails if
any sample falls short.
"""

import itertools
from fractions import Fraction

import sympy as sp

from .vendor.verify_exact import triangle_area, convex_hull

DIGITS = 30
VERIFY_REL = Fraction(1, 10 ** 20)


def _dec(v):
    """Exact sympy number -> 30-decimal string (round-half-even at 30)."""
    s = sp.Float(sp.N(v, DIGITS + 10), DIGITS + 10)
    from decimal import Decimal, Context
    d = Context(prec=DIGITS).create_decimal(Decimal(str(s)))
    out = format(d, "f")
    return out


def _sq3_family():
    xs = [sp.Rational(k, 16) for k in range(17)]
    samples = [[(sp.S(0), sp.S(0)), (sp.S(1), sp.S(0)), (x, sp.S(1))]
               for x in xs]
    return {
        "samples": samples,
        "moving": [2],
        "param": {"name": "x", "lo": sp.S(0), "hi": sp.S(1),
                  "lo_label": "0", "hi_label": "1", "stored_at": 0.0},
        "caption": (
            "The optimum is not unique: with the two lower corners fixed, the "
            "third point may sit anywhere on the top edge — the triangle keeps "
            "base 1 and height 1, so its area is exactly ½ for every x ∈ [0, 1]. "
            "One slice of the full family of area-½ triangles."),
    }


def _sq6_family():
    base = [(sp.S(0), sp.S(0)), (sp.Rational(1, 2), sp.S(0)),
            (sp.S(1), sp.Rational(1, 2)), (sp.Rational(1, 2), sp.S(1)),
            (sp.S(0), sp.Rational(1, 2)), (sp.S(1), sp.S(1))]
    ts = [sp.Rational(k, 32) for k in range(17)]
    samples = [[(x + t * (1 - 2 * y), y) for (x, y) in base] for t in ts]
    return {
        "samples": samples,
        "moving": [0, 1, 3, 5],
        "param": {"name": "t", "lo": sp.S(0), "hi": sp.Rational(1, 2),
                  "lo_label": "0", "hi_label": "1/2", "stored_at": 0.0},
        "caption": (
            "The Dress–Yang–Zeng family: the shear x ↦ x + t(1−2y) slides the "
            "bottom pair right and the top pair left. A shear preserves every "
            "triangle's area, so all six minimal triangles stay at exactly ⅛ "
            "for the whole range t ∈ [0, ½]; the container is the only "
            "constraint. t = ½ is the 90°-rotated image of the original."),
    }


def _tri5_family():
    s2 = sp.sqrt(2)
    lo, hi = 2 - s2, 1 / s2
    xs = [lo + sp.Rational(k, 16) * (hi - lo) for k in range(17)]
    # Right-frame member with the mirror through vertex (1,0), then the
    # vertex permutation (x, y) -> (1-x-y, x) that ingest applies to every
    # one-mirror triangle configuration (mirror -> vertical display axis).
    samples = [[(1 - px - py, px) for (px, py) in
                [(sp.S(0), sp.S(0)), (x, sp.S(0)), (sp.S(0), sp.S(1)),
                 (2 - s2, s2 - 1), (3 - 2 * s2, s2 - 1)]]
               for x in xs]
    return {
        "samples": samples,
        "moving": [1],
        "param": {"name": "x", "lo": lo, "hi": hi,
                  "lo_label": "2 − √2", "hi_label": "1/√2", "stored_at": 0.0},
        "caption": (
            "One 1-parameter slice of the optimal set: point 1 slides along "
            "the hypotenuse, (1 − x, x) for x ∈ [2 − √2, 1/√2] (right-frame "
            "coordinates; the stored member is the x = 2 − √2 endpoint). Its "
            "motion is parallel "
            "to the segment through points 3 and 4, so the tied triangle "
            "(1,3,4) keeps its area; the released triangle (1,2,4) grows. "
            "Every member achieves exactly A = 3 − 2√2."),
    }


def _tri6_family():
    ys = [sp.Rational(3, 8) - sp.Rational(k, 16) * sp.Rational(1, 8)
          for k in range(17)]
    samples = [[(sp.Rational(1, 4), sp.S(0)), (sp.Rational(3, 4), sp.S(0)),
                (sp.S(0), y), (sp.Rational(3, 4), sp.Rational(1, 4)),
                (sp.S(0), sp.S(1)), (sp.Rational(1, 4), sp.Rational(1, 2))]
               for y in ys]
    return {
        "samples": samples,
        "moving": [2],
        "param": {"name": "y", "lo": sp.Rational(3, 8), "hi": sp.Rational(1, 4),
                  "lo_label": "3/8", "hi_label": "1/4", "stored_at": 0.0},
        "caption": (
            "One 1-parameter slice of the optimal set: point 2 slides down the "
            "left edge for y ∈ [1/4, 3/8] (right-frame coordinates; the stored "
            "member is the top endpoint). Its motion is parallel to the "
            "segment through points 0 and 5, so the tied triangle (0,2,5) "
            "keeps its area; the released triangle (2,3,5) grows. Every "
            "member achieves exactly A = ⅛."),
    }


def _cv7_family():
    s3 = sp.sqrt(3)
    lo, hi = s3 / 2, 2 / s3
    # orbit A (radius 1) at 90, 210, 330 degrees; orbit B (radius s) at
    # 120, 240, 0 degrees; center. Matches the stored point order.
    a_ang = [sp.Rational(90), sp.Rational(210), sp.Rational(330)]
    b_ang = [sp.Rational(120), sp.Rational(240), sp.Rational(0)]

    def member(s):
        pts = [(sp.cos(sp.rad(a)), sp.sin(sp.rad(a))) for a in a_ang]
        pts += [(s * sp.cos(sp.rad(a)), s * sp.sin(sp.rad(a))) for a in b_ang]
        pts.append((sp.S(0), sp.S(0)))
        return pts

    def hex_hull_area(s):
        # hull vertex order by angle: B0(0), A0(90), B120, A210, B240, A330
        pts = member(s)
        order = [5, 0, 3, 1, 4, 2]
        acc = sp.S(0)
        for i in range(6):
            (x1, y1) = pts[order[i]]
            (x2, y2) = pts[order[(i + 1) % 6]]
            acc += x1 * y2 - x2 * y1
        return sp.simplify(sp.Abs(acc) / 2)

    h0 = hex_hull_area(hi)          # stored member is s = 2/sqrt(3)
    ss = [hi + sp.Rational(k, 64) * (lo - hi) for k in range(65)]
    samples = []
    for s in ss:
        k = sp.sqrt(h0 / hex_hull_area(s))
        samples.append([(sp.simplify(k * x), sp.simplify(k * y))
                        for (x, y) in member(s)])
    return {
        "samples": samples,
        "moving": [0, 1, 2, 3, 4, 5],
        "param": {"name": "s", "lo": hi, "hi": lo,
                  "lo_label": "2/√3", "hi_label": "√3/2", "stored_at": 0.0},
        "caption": (
            "The one-parameter optimal family derived on this site: the center "
            "plus two equilateral orbits 30° apart, radius ratio s ∈ [√3/2, "
            "2/√3], every member achieving exactly 1/9. The stored member is "
            "the s = 2/√3 endpoint, where 9 triangles tie; inside the interval "
            "3 of them release. Members are rescaled so the hull area stays "
            "constant."),
    }


FAMILY_BUILDERS = {
    ("square", 3): _sq3_family,
    ("square", 6): _sq6_family,
    ("triangle", 5): _tri5_family,
    ("triangle", 6): _tri6_family,
    ("convex", 7): _cv7_family,
}


def _exact_value(variant, pts_frac):
    n = len(pts_frac)
    m = min(triangle_area(*(pts_frac[i] for i in t))
            for t in itertools.combinations(range(n), 3))
    if variant != "convex":
        return m
    hull = convex_hull([(float(x), float(y)) for x, y in pts_frac])
    idx = {(float(x), float(y)): (x, y) for x, y in pts_frac}
    acc = Fraction(0)
    for i in range(len(hull)):
        (x1, y1) = idx[tuple(hull[i])]
        (x2, y2) = idx[tuple(hull[(i + 1) % len(hull)])]
        acc += x1 * y2 - x2 * y1
    return m / (abs(acc) / 2)


def generate(variant, n, doc):
    """Return the family spec for (variant, n) with decimal-literal samples,
    or None. Every sample is verified in exact arithmetic against the stored
    configuration's exact-literal value; failure raises."""
    builder = FAMILY_BUILDERS.get((variant, n))
    if builder is None:
        return None
    fam = builder()
    stored = [(Fraction(x), Fraction(y)) for x, y in doc["points"]]
    v0 = _exact_value(variant, stored)
    dec_samples = []
    for si, sample in enumerate(fam["samples"]):
        lits = [[_dec(x), _dec(y)] for (x, y) in sample]
        pf = [(Fraction(x), Fraction(y)) for x, y in lits]
        v = _exact_value(variant, pf)
        if v < v0 * (1 - VERIFY_REL):
            raise AssertionError(
                f"family sample {si} of {variant} n={n} verifies at {float(v)} "
                f"< stored {float(v0)}")
        dec_samples.append(lits)
    return {
        "samples": dec_samples,
        "moving": fam["moving"],
        "param": {
            "name": fam["param"]["name"],
            "lo_label": fam["param"]["lo_label"],
            "hi_label": fam["param"]["hi_label"],
            "lo": float(fam["param"]["lo"]),
            "hi": float(fam["param"]["hi"]),
            "stored_at": fam["param"]["stored_at"],
        },
        "caption": fam["caption"],
    }

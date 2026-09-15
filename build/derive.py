"""Derivation: everything computed from the canonical coordinates at build
time — the minimal-triangle tie set (exact), congruence classes among the
minimal triangles, and the symmetry group of the configuration.

Floats are fine for congruence/symmetry (coordinates are polished to
~1e-15); the tie set itself is exact, using the same 1+1e-9 relative rule
as the verifiers.
"""

import itertools
import math
from fractions import Fraction

from .vendor.verify_exact import TIE_FACTOR, triangle_area, convex_hull

# Friedman's GIF palette, reused so our figures rhyme with the originals.
PALETTE = ["#e02020", "#2020e0", "#00a020", "#d4b400", "#f07800",
           "#00b0b0", "#7f007f", "#7f7f7f", "#7f7fff", "#e000e0"]

SQ3 = math.sqrt(3.0)


def minimal_triangles(points_frac):
    """All triples within the exact tie tolerance of the minimum area.
    Returns (min_area: Fraction, ties: list[(i, j, k)])."""
    areas = {}
    min_area = None
    for t in itertools.combinations(range(len(points_frac)), 3):
        a = triangle_area(*(points_frac[i] for i in t))
        areas[t] = a
        if min_area is None or a < min_area:
            min_area = a
    threshold = min_area * TIE_FACTOR
    ties = [t for t, a in areas.items() if a <= threshold]
    return min_area, ties


CONG_TOL = 3e-5  # must exceed the symmetry displacement tolerance (1e-6),
                 # or orbits of congruent triangles split into singletons


def congruence_classes(points, ties):
    """Group minimal triangles by congruence: sorted squared side lengths,
    clustered at relative tolerance CONG_TOL. Returns a list of classes, each
    {"triangles": [(i,j,k)...], "sides": (a,b,c) side lengths ascending},
    ordered by class size (desc) then perimeter."""
    def key(t):
        (i, j, k) = t
        p, q, r = points[i], points[j], points[k]
        d = sorted(((p[0]-q[0])**2 + (p[1]-q[1])**2,
                    (q[0]-r[0])**2 + (q[1]-r[1])**2,
                    (r[0]-p[0])**2 + (r[1]-p[1])**2))
        return d

    classes = []
    for t in ties:
        k = key(t)
        for cls in classes:
            ref = cls["_key"]
            if all(abs(a - b) <= CONG_TOL * max(a, b, 1e-30) for a, b in zip(k, ref)):
                cls["triangles"].append(t)
                break
        else:
            classes.append({"_key": k, "triangles": [t]})
    for cls in classes:
        cls["sides"] = tuple(math.sqrt(s) for s in cls["_key"])
        del cls["_key"]
    classes.sort(key=lambda c: (-len(c["triangles"]), sum(c["sides"])))
    return classes


# ---------------------------------------------------------------------------
# Symmetry detection. Each candidate isometry is an affine map (2x2 matrix A,
# offset b): p -> A p + b. It belongs to the configuration's symmetry group
# if it permutes the point set within TOL.

TOL = 1e-6


def _maps_set_to_itself(points, fn, tol=TOL):
    used = [False] * len(points)
    for (x, y) in points:
        tx, ty = fn(x, y)
        for idx, (px, py) in enumerate(points):
            if not used[idx] and abs(px - tx) <= tol and abs(py - ty) <= tol:
                used[idx] = True
                break
        else:
            return False
    return True


def _rot(cx, cy, angle):
    c, s = math.cos(angle), math.sin(angle)
    return lambda x, y: (cx + c * (x - cx) - s * (y - cy),
                         cy + s * (x - cx) + c * (y - cy))


def _mirror(cx, cy, axis_angle):
    """Reflection across the line through (cx, cy) at axis_angle."""
    c, s = math.cos(2 * axis_angle), math.sin(2 * axis_angle)
    return lambda x, y: (cx + c * (x - cx) + s * (y - cy),
                         cy + s * (x - cx) - c * (y - cy))


def _detect(points, center, rot_orders, mirror_angles, tol=TOL):
    """Try rotations by 2π/m for m in rot_orders and reflections at the given
    axis angles (through center). Returns (rot_order, mirror_axes)."""
    cx, cy = center
    rot_order = 1
    for m in sorted(set(rot_orders), reverse=True):
        if m > 1 and _maps_set_to_itself(points, _rot(cx, cy, 2 * math.pi / m), tol):
            rot_order = m
            break
    axes = []
    seen = []
    for a in mirror_angles:
        a = a % math.pi
        if any(abs(a - b) < 1e-9 or abs(abs(a - b) - math.pi) < 1e-9 for b in seen):
            continue
        seen.append(a)
        if _maps_set_to_itself(points, _mirror(cx, cy, a), tol):
            axes.append(a)
    return rot_order, axes


def detect_symmetry(variant, points, tol=None):
    """Detect the configuration's symmetry group within the container's
    symmetry group (square: D4, triangle: D3 in the equilateral frame,
    convex: the hull's own symmetries about the centroid).

    Runs at the strict tolerance first; if nothing is found, retries at a
    relaxed tolerance and marks the result "approx" — polished optima are
    sometimes a hair off an exactly-symmetric configuration (e.g. triangle
    n=15 sits ~1e-5 from C3 and beats the best symmetric config by ~4e-8).

    Returns {"group", "order", "approx", "rotation": {order, center} | None,
    "axes": [{angle, center}]} with coordinates in the *input* frame.
    """
    if tol is None:
        strict = _detect_at(variant, points, TOL)
        if strict["group"] != "C1":
            return strict
        relaxed = _detect_at(variant, points, 1e-4)
        if relaxed["group"] != "C1":
            relaxed["approx"] = True
        return relaxed
    return _detect_at(variant, points, tol)


def _detect_at(variant, points, tol):
    if variant == "square":
        center = (0.5, 0.5)
        rot_order, axes = _detect(points, center, [4, 2],
                                  [0, math.pi / 2, math.pi / 4, 3 * math.pi / 4], tol)
    elif variant == "triangle":
        # Map right frame -> equilateral frame so the container group is the
        # geometric D3.
        eq = [(x + y / 2, y * SQ3 / 2) for (x, y) in points]
        center = (0.5, SQ3 / 6)  # centroid of (0,0),(1,0),(1/2,√3/2)
        rot_order, axes = _detect(eq, center, [3],
                                  [math.pi / 2, math.pi / 2 + math.pi / 3,
                                   math.pi / 2 - math.pi / 3], tol)
        points = eq  # axes/center are reported in the equilateral frame
    else:  # convex
        n = len(points)
        cx = sum(p[0] for p in points) / n
        cy = sum(p[1] for p in points) / n
        center = (cx, cy)
        # Candidate mirror axes: through each point and through each pair
        # midpoint direction; candidate rotation orders: divisors of hull
        # sizes up to n.
        angles = []
        for (x, y) in points:
            angles.append(math.atan2(y - cy, x - cx))
        cand = []
        for i in range(len(angles)):
            cand.append(angles[i])
            for j in range(i + 1, len(angles)):
                cand.append((angles[i] + angles[j]) / 2)
        rot_order, axes = _detect(points, center, range(2, n + 1), cand, tol)

    order = rot_order * (2 if axes else 1)
    if axes and rot_order > 1:
        group = f"D{rot_order}"
    elif axes:
        group = "D1"
    elif rot_order > 1:
        group = f"C{rot_order}"
    else:
        group = "C1"
    return {
        "group": group,
        "order": order,
        "approx": False,
        "rotation": ({"order": rot_order, "center": center} if rot_order > 1 else None),
        "axes": [{"angle": a, "center": center} for a in axes],
    }


def symmetry_label(sym, variant):
    """Map a detected group to the record ledger's wording, for cross-checking."""
    g, axes = sym["group"], sym["axes"]
    if g == "C1":
        return "Not symmetric"
    if g == "C2":
        return "180° Rotationally symmetric"
    if g == "C3":
        return "120° Rotationally symmetric"
    if g == "C4":
        return "90° Rotationally symmetric"
    if g.startswith("D"):
        k = int(g[1:])
        if k == 1:
            return "Mirror symmetric"
        return f"{k}-fold dihedral symmetry"
    return g


def orbits(variant, points, sym, tol=1e-4):
    """Partition point indices into orbits under the detected group.
    Points are matched through each group element by nearest neighbor at the
    relaxed tolerance (covers approx-symmetric optima too)."""
    if sym["order"] <= 1:
        return [[i] for i in range(len(points))]
    if variant == "triangle":
        pts = [(x + y / 2, y * SQ3 / 2) for (x, y) in points]
    else:
        pts = list(points)
    fns = []
    if sym["rotation"]:
        k = sym["rotation"]["order"]
        cx, cy = sym["rotation"]["center"]
        fns += [_rot(cx, cy, 2 * math.pi * j / k) for j in range(1, k)]
    for ax in sym["axes"]:
        fns.append(_mirror(ax["center"][0], ax["center"][1], ax["angle"]))

    parent = list(range(len(pts)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for fn in fns:
        for i, (x, y) in enumerate(pts):
            tx, ty = fn(x, y)
            j = min(range(len(pts)),
                    key=lambda j: (pts[j][0] - tx) ** 2 + (pts[j][1] - ty) ** 2)
            if abs(pts[j][0] - tx) <= tol and abs(pts[j][1] - ty) <= tol:
                parent[find(i)] = find(j)
    groups = {}
    for i in range(len(pts)):
        groups.setdefault(find(i), []).append(i)
    return sorted(groups.values(), key=lambda g: (-len(g), g[0]))


def derive(variant, points_str):
    """Full derivation for one configuration. points_str: [[xs, ys], ...]."""
    pf = [(Fraction(x), Fraction(y)) for x, y in points_str]
    pts = [(float(x), float(y)) for x, y in pf]
    min_area, ties = minimal_triangles(pf)
    # Congruence is a metric notion. The triangle variant stores coordinates
    # in the right frame, where the container's symmetries are affine but not
    # Euclidean — measure in the unit-area equilateral realization instead,
    # which is also the frame the figures are drawn in.
    if variant == "triangle":
        k = math.sqrt(4 / SQ3)  # scales the equilateral frame to area 1
        metric_pts = [(k * (x + y / 2), k * (y * SQ3 / 2)) for x, y in pts]
    else:
        metric_pts = pts
    classes = congruence_classes(metric_pts, ties)
    sym = detect_symmetry(variant, pts)
    return {
        "min_area": min_area,
        "ties": ties,
        "classes": classes,
        "symmetry": sym,
        "orbits": orbits(variant, pts, sym),
    }

#!/usr/bin/env python3
"""Verify coordinate submissions (data/sources/external/<variant>-nNN/).

Used by the submission-verify GitHub workflow and runnable locally:

    python3 scripts/check_submission.py data/sources/external/square-n17
    python3 scripts/check_submission.py --base origin/main          # changed dirs
    make check-submission DIRS=data/sources/external/square-n17

For each submission directory it validates the file format, re-verifies the
configuration in exact rational arithmetic (same verifier the site uses), and
compares the value against the current canonical entry. It emits a Markdown
report (stdout, or --out FILE) and exits nonzero if any submission is invalid.

Value policy (this feeds auto-merge, so every anomaly must BLOCK, not warn):
- a NEW submission directory that verifies but does not beat the current
  value is valid — the original author's coordinates for a reconstructed
  entry are welcome even when they score lower; ingest keeps using the best
  source, so nothing regresses.
- MODIFYING an existing submission directory must not lower that directory's
  exact value (PR #9 replaced a better configuration with a worse one and
  auto-merge shipped it). Equal is fine (meta edits, added digits, exact
  forms); lower is refused and needs a maintainer-reviewed PR.

Stdlib only, so CI needs no installs. All parsing is bounded (file sizes,
digit counts, point counts) because this runs on untrusted pull requests.
"""

import argparse
import itertools
import json
import pathlib
import re
import subprocess
import sys
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from build.vendor.verify_exact import verify, fraction_to_30sig  # noqa: E402
from build.derive import (detect_symmetry, symmetry_label,  # noqa: E402
                          minimal_triangles, congruence_classes)

# Lanes the automated pipeline verifies. external/ is THE submission lane
# (meta.json needs "ref") — see CONTRIBUTING.md.
SUBMISSION_ROOTS = {
    "data/sources/external": "ref",
}
DIR_RE = re.compile(r"^(square|triangle|convex)-n(\d{2})$")
NUM_RE = re.compile(r"^-?\d{1,6}(\.\d{1,200})?$")
MAX_COORD_BYTES = 64 * 1024
MAX_META_BYTES = 8 * 1024
MAX_POINTS = 100
META_KEYS = {"ref": (True, 300), "credit": (False, 300), "note": (False, 2000)}
MAX_POLY_DEGREE = 64
MAX_COEFF_BITS = 4096


def fail(problems, msg):
    problems.append(msg)


def parse_coordinates(path, problems):
    if path.stat().st_size > MAX_COORD_BYTES:
        fail(problems, f"`coordinates.txt` is larger than {MAX_COORD_BYTES // 1024} KB")
        return None
    return parse_coordinates_text(path.read_text(), problems)


def parse_coordinates_text(text, problems):
    points = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            fail(problems, f"line {lineno}: expected two whitespace-separated numbers")
            return None
        for p in parts:
            if not NUM_RE.match(p):
                fail(problems, f"line {lineno}: `{p[:40]}` is not a plain decimal "
                               "literal (≤6 integer digits, ≤200 decimals, no exponent)")
                return None
        points.append((Fraction(parts[0]), Fraction(parts[1])))
        if len(points) > MAX_POINTS:
            fail(problems, f"more than {MAX_POINTS} points")
            return None
    return points


def meta_keys_for(dirpath):
    lane = str(pathlib.Path(dirpath).parent).replace("\\", "/")
    for root, req in SUBMISSION_ROOTS.items():
        if lane.endswith(root):
            keys = dict(META_KEYS)
            if req != "ref":
                del keys["ref"]
                keys[req] = (True, 300)
                keys["value_fraction"] = (False, 200)
            return keys
    return META_KEYS


def check_meta(path, problems, warnings, keys=META_KEYS):
    if not path.exists():
        fail(problems, "`meta.json` is missing")
        return None
    if path.stat().st_size > MAX_META_BYTES:
        fail(problems, f"`meta.json` is larger than {MAX_META_BYTES // 1024} KB")
        return None
    try:
        meta = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        fail(problems, f"`meta.json` is not valid JSON: {exc}")
        return None
    if not isinstance(meta, dict):
        fail(problems, "`meta.json` must be a JSON object")
        return None
    for key, (required, maxlen) in keys.items():
        if key not in meta:
            if required:
                fail(problems, f"`meta.json` is missing required key `{key}`")
            continue
        if not isinstance(meta[key], str) or not meta[key].strip():
            fail(problems, f"`meta.json` key `{key}` must be a non-empty string")
        elif len(meta[key]) > maxlen:
            fail(problems, f"`meta.json` key `{key}` exceeds {maxlen} characters")
    for key in meta:
        if key not in keys:
            warnings.append(f"`meta.json` has unknown key `{key}` (ignored by ingest)")
    return meta


def parse_poly_coeffs(raw, problems):
    """exact.json's minimal_polynomial: integer coefficients, constant term
    first. Accepts ints or strings of digits (for coefficients too large for
    other tools' JSON parsers). Returns list[int] or None."""
    if not isinstance(raw, list) or not 2 <= len(raw) <= MAX_POLY_DEGREE + 1:
        fail(problems, "`minimal_polynomial` must be a list of 2 to "
                       f"{MAX_POLY_DEGREE + 1} integer coefficients, constant term first")
        return None
    coeffs = []
    for i, c in enumerate(raw):
        if isinstance(c, str) and re.fullmatch(r"-?\d{1,1300}", c):
            c = int(c)
        if not isinstance(c, int) or isinstance(c, bool):
            fail(problems, f"`minimal_polynomial[{i}]` is not an integer")
            return None
        if c.bit_length() > MAX_COEFF_BITS:
            fail(problems, f"`minimal_polynomial[{i}]` exceeds {MAX_COEFF_BITS} bits")
            return None
        coeffs.append(c)
    if coeffs[-1] == 0:
        fail(problems, "`minimal_polynomial` has a zero leading coefficient")
        return None
    return coeffs


def check_exact(path, value, problems, warnings):
    """Validate an exact-value claim against the submission's own exact
    rational value: the polynomial must change sign across
    [value(1-1e-9), value(1+1e-9)], all in exact arithmetic."""
    if path.stat().st_size > MAX_META_BYTES:
        fail(problems, f"`exact.json` is larger than {MAX_META_BYTES // 1024} KB")
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        fail(problems, f"`exact.json` is not valid JSON: {exc}")
        return None
    if not isinstance(data, dict) or "minimal_polynomial" not in data:
        fail(problems, "`exact.json` must be an object with `minimal_polynomial`")
        return None
    for key in data:
        if key not in ("minimal_polynomial", "note"):
            warnings.append(f"`exact.json` has unknown key `{key}` (ignored)")
    coeffs = parse_poly_coeffs(data["minimal_polynomial"], problems)
    if coeffs is None:
        return None

    def P(q):
        acc = Fraction(0)
        for c in reversed(coeffs):
            acc = acc * q + c
        return acc

    delta = value / 10 ** 9
    lo, hi = P(value - delta), P(value + delta)
    if not (lo == 0 or hi == 0 or (lo < 0) != (hi < 0)):
        fail(problems, "`exact.json`: the polynomial has no sign change within "
                       "1e-9 (relative) of the value implied by the coordinates "
                       "— the claimed exact value does not match this submission")
        return None
    from math import gcd
    if gcd(*(abs(c) for c in coeffs)) > 1:
        warnings.append("`exact.json`: coefficients share a common factor")
    return {"degree": len(coeffs) - 1, "coeffs": coeffs}


def canonical_value(variant, n):
    path = ROOT / "data" / "canonical" / variant / f"n{n:02d}.json"
    if not path.exists():
        return None
    doc = json.loads(path.read_text())
    v = doc.get("verify") or {}
    frac = v.get("value_fraction")
    return Fraction(frac) if frac else None


def check_dir(dirpath, base=None):
    """Returns a result dict for one submission directory."""
    res = {"dir": str(dirpath), "problems": [], "warnings": [], "ok": False}
    problems, warnings = res["problems"], res["warnings"]

    m = DIR_RE.match(dirpath.name)
    if not m:
        fail(problems, "directory name must be `<square|triangle|convex>-nNN`")
        return res
    variant, n = m.group(1), int(m.group(2))
    res["variant"], res["n"] = variant, n

    coord_path = dirpath / "coordinates.txt"
    if not coord_path.exists():
        fail(problems, "`coordinates.txt` is missing")
        return res
    points = parse_coordinates(coord_path, problems)
    check_meta(dirpath / "meta.json", problems, warnings, meta_keys_for(dirpath))
    for extra in sorted(p.name for p in dirpath.iterdir()
                        if p.name not in ("coordinates.txt", "meta.json",
                                          "exact.json")):
        warnings.append(f"unexpected file `{extra}` (only coordinates.txt and "
                        "meta.json are read)")
    if points is None:
        return res

    if len(points) != n:
        fail(problems, f"directory says n={n} but coordinates.txt has {len(points)} points")
        return res
    if len(set(points)) != len(points):
        fail(problems, "duplicate points")
        return res

    v = verify(variant, points)
    res["verify"] = v
    if not v["feasible"]:
        for viol in v["violations"][:5]:
            fail(problems, f"infeasible: {viol}")
        return res

    value = v["_value"]
    res["value_30sig"] = fraction_to_30sig(value)
    fpoints = [(float(x), float(y)) for x, y in points]
    sym = detect_symmetry(variant, fpoints)
    res["symmetry"] = symmetry_label(sym, variant) + f" ({sym['group']})" + \
        (" — approximate" if sym.get("approx") else "")

    # Tie structure as the page will render it, plus an under-convergence
    # warning: ties are exact within rel 1e-9, so coordinates need ~12+
    # digits or the intended tie picture collapses to whatever the literals
    # actually achieve.
    min_area, ties = minimal_triangles(points)
    res["classes"] = len(congruence_classes(fpoints, ties))
    res["ties"] = len(ties)
    fmin = float(min_area)
    tie_set = set(ties)
    near = sum(
        1 for t in itertools.combinations(range(len(fpoints)), 3)
        if t not in tie_set
        and abs((fpoints[t[1]][0] - fpoints[t[0]][0]) * (fpoints[t[2]][1] - fpoints[t[0]][1])
                - (fpoints[t[1]][1] - fpoints[t[0]][1]) * (fpoints[t[2]][0] - fpoints[t[0]][0])) / 2
            <= fmin * (1 + 1e-6))
    if near:
        warnings.append(
            f"{near} more triangle(s) lie within 1e-6 of the minimum but outside "
            "the 1e-9 tie window — if these are meant to be exact ties, the "
            "coordinates are under-converged; submit more digits so the page "
            "shows the full tie structure")

    exact_path = dirpath / "exact.json"
    if exact_path.exists():
        ex = check_exact(exact_path, value, problems, warnings)
        if ex:
            res["exact"] = (f"degree-{ex['degree']} polynomial has a root within "
                            "1e-9 of the coordinate value ✓ (minimality/irreducibility "
                            "not machine-checked)")
    cur = canonical_value(variant, n)
    if cur is None:
        res["relation"] = "no canonical entry to compare against"
    elif value > cur:
        res["relation"] = f"IMPROVES the current value by {float((value - cur) / cur):.4%}"
    elif value == cur:
        res["relation"] = "exactly equals the current value"
    else:
        res["relation"] = (f"below the current value by {float((cur - value) / cur):.4%} "
                           "(acceptable only as added provenance, e.g. an original "
                           "author's coordinates — ingest keeps using the better source)")
    # A modification of an existing submission directory must never lower its
    # value: that replaces the only copy of a better configuration, which the
    # best-source-wins ingest cannot undo (PR #9).
    if base is not None:
        prev = base_value(dirpath, base)
        if prev is not None and value < prev:
            fail(problems,
                 f"replaces this directory's previous coordinates (exact value "
                 f"`{fraction_to_30sig(prev)}`) with a value "
                 f"{float((prev - value) / prev):.4%} lower — overwriting a better "
                 f"configuration is refused. Improvements only; worse-but-authentic "
                 f"coordinates need a maintainer-reviewed PR that keeps the better "
                 f"source in place")
    res["ok"] = not problems
    return res


def base_value(dirpath, base):
    """Exact value of this directory's coordinates at the merge-base with
    `base`, or None if the directory (or a verifiable file) wasn't there."""
    m = DIR_RE.match(dirpath.name)
    if not m:
        return None
    rel = pathlib.Path(dirpath).resolve().relative_to(ROOT).as_posix()
    mb = subprocess.run(["git", "merge-base", base, "HEAD"],
                        cwd=ROOT, capture_output=True, text=True)
    ref = mb.stdout.strip() if mb.returncode == 0 and mb.stdout.strip() else base
    proc = subprocess.run(["git", "show", f"{ref}:{rel}/coordinates.txt"],
                          cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0 or len(proc.stdout) > MAX_COORD_BYTES:
        return None
    probs = []
    pts = parse_coordinates_text(proc.stdout, probs)
    if probs or not pts:
        return None
    res = verify(m.group(1), pts)
    return res["_value"] if res.get("feasible") else None


def changed_submission_dirs(base):
    proc = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"git diff against {base!r} failed: {proc.stderr.strip()}")
    out = proc.stdout
    dirs, out_of_scope = set(), []
    for line in out.splitlines():
        if not line:
            continue
        for root in SUBMISSION_ROOTS:
            if line.startswith(root + "/"):
                rel = pathlib.Path(line).parent
                if rel != pathlib.Path(root):
                    dirs.add(ROOT / pathlib.Path(*rel.parts[:4]))
                break
        else:
            out_of_scope.append(line)
    return sorted(dirs), out_of_scope


def render(results, out_of_scope):
    lines = ["<!-- submission-verify -->", "## Coordinate submission check", ""]
    if not results:
        lines.append("No submission directories changed in this PR.")
    for r in results:
        head = f"### `{pathlib.Path(r['dir']).name}`"
        lines.append(head)
        if r["ok"]:
            v = r["verify"]
            lines += [
                "",
                f"| | |",
                f"|---|---|",
                f"| verdict | **valid** — feasible in exact arithmetic |",
                f"| value (exact, 30 digits) | `{r['value_30sig']}` |",
                f"| vs current canonical | {r['relation']} |",
                f"| detected symmetry | {r['symmetry']} |",
                *([f"| exact value claim | {r['exact']} |"] if r.get("exact") else []),
                f"| triples checked | {v['triples_checked']}, "
                f"{r['ties']} tied at the minimum in {r['classes']} congruence "
                f"class{'es' if r['classes'] != 1 else ''} |",
                "",
            ]
        else:
            lines.append("\n**invalid:**\n")
            lines += [f"- {p}" for p in r["problems"]]
            lines.append("")
        for w in r["warnings"]:
            lines.append(f"- ⚠ {w}")
        lines.append("")
    if out_of_scope:
        lines.append(f"This PR also touches {len(out_of_scope)} file(s) outside "
                     "the submission lanes — fine, but they get a human review, "
                     "not this automated one:")
        lines += [f"- `{p}`" for p in out_of_scope[:20]]
        if len(out_of_scope) > 20:
            lines.append(f"- … and {len(out_of_scope) - 20} more")
    lines += ["", "*Verification: exact rational arithmetic over all point "
              "triples (`build/vendor/verify_exact.py`). A valid submission is "
              "adopted by ingest only if its exact value beats every other "
              "source for that entry; a PR may not replace an existing "
              "submission with a lower-valued one.*"]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="*", help="submission directories to check")
    ap.add_argument("--base", help="git ref: check dirs changed since this ref")
    ap.add_argument("--out", help="also write the Markdown report to this file")
    args = ap.parse_args()

    out_of_scope = []
    if args.base:
        dirs, out_of_scope = changed_submission_dirs(args.base)
    else:
        dirs = [pathlib.Path(d).resolve() for d in args.dirs]
    results = [check_dir(d, base=args.base) for d in dirs]

    report = render(results, out_of_scope)
    print(report)
    if args.out:
        pathlib.Path(args.out).write_text(report + "\n")
    sys.exit(0 if all(r["ok"] for r in results) else 1)


if __name__ == "__main__":
    main()

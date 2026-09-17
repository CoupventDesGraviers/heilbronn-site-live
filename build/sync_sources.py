#!/usr/bin/env python3
"""Vendor upstream coordinate sources into data/sources/.

- TejSteadQC/heilbronn-configurations: scan every claims*/ directory, verify
  the dual verifier outputs agree, and keep the BEST configuration per
  (variant, n) by exact value, written into the ordinary submission lane
  data/sources/external/ (never replacing a better entry already there).
  Batch claims re-polish other people's record figures, so "best" is a
  statement about coordinates, not credit.
- spiralulam/heilbronn: square n=3..16 JSONs + LICENSE, copied verbatim.
- AlphaEvolve mirrors (from the tejsteadqc clone): triangle n=11,
  convex n=13/14.

Usage:
    python3 build/sync_sources.py --tejsteadqc DIR [--spiralulam DIR]

Run whenever the upstream repos change; the result is committed so builds
never need network access.
"""

import argparse
import json
import pathlib
import re
import shutil
import sys
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_EXT = ROOT / "data" / "sources" / "external"
OUT_SPIRAL = ROOT / "data" / "sources" / "spiralulam"
OUT_AE = ROOT / "data" / "sources" / "alphaevolve"

CLAIM_DIR_RE = re.compile(r"^\d+-(?:record|exact|extension)-(square|triangle|convex)-n(\d+)$")
BATCH_DIR_RE = re.compile(r"^(square|triangle|convex)-n(\d+)$")


def iter_claims(repo):
    """Yield (variant, n, claim_dir, origin) for every claim directory."""
    for parent in sorted(repo.glob("claims*")):
        if not parent.is_dir():
            continue
        for d in sorted(parent.iterdir()):
            if not d.is_dir():
                continue
            m = CLAIM_DIR_RE.match(d.name) or BATCH_DIR_RE.match(d.name)
            if not m:
                continue
            yield m.group(1), int(m.group(2)), d, f"{parent.name}/{d.name}"


def claim_value(d):
    """Exact value from verify_output.json, or None if unusable."""
    vo = d / "verify_output.json"
    coords = d / "coordinates.txt"
    if not vo.exists() or not coords.exists():
        return None
    data = json.loads(vo.read_text())
    a, b = data.get("a"), data.get("b")
    if not a or not b:
        return None
    if a["value_fraction"] != b["value_fraction"]:
        print(f"  SKIP {d}: verifier disagreement", file=sys.stderr)
        return None
    if not (a["feasible"] and b["feasible"]):
        print(f"  SKIP {d}: infeasible", file=sys.stderr)
        return None
    return Fraction(a["value_fraction"])


def sync_tejsteadqc(repo):
    best = {}  # (variant, n) -> (value, dir, origin)
    for variant, n, d, origin in iter_claims(repo):
        v = claim_value(d)
        if v is None:
            continue
        key = (variant, n)
        if key not in best or v > best[key][0]:
            best[key] = (v, d, origin)

    # Companion-repo claims go into the ordinary submission lane, one
    # directory per (variant, n). An existing external entry is replaced only
    # when the claim strictly improves on it.
    OUT_EXT.mkdir(parents=True, exist_ok=True)
    written = 0
    for (variant, n), (v, d, origin) in sorted(best.items()):
        dest = OUT_EXT / f"{variant}-n{n:02d}"
        if dest.exists():
            a = json.loads((dest / "verify_output.json").read_text())["a"] \
                if (dest / "verify_output.json").exists() else None
            if a is None or Fraction(a["value_fraction"]) >= v:
                continue
            shutil.rmtree(dest)
        dest.mkdir()
        shutil.copy(d / "coordinates.txt", dest / "coordinates.txt")
        shutil.copy(d / "verify_output.json", dest / "verify_output.json")
        (dest / "meta.json").write_text(json.dumps({
            "ref": f"TejSteadQC/heilbronn-configurations {origin}",
            "credit": "Tej Stead",
            "note": "this site's own search campaign (companion repository); "
                    "dual-verified upstream, see verify_output.json",
        }, indent=1) + "\n")
        written += 1
    print(f"tejsteadqc: {written} configurations written to external/")
    return best


def sync_spiralulam(repo):
    if OUT_SPIRAL.exists():
        shutil.rmtree(OUT_SPIRAL)
    OUT_SPIRAL.mkdir(parents=True)
    src = repo / "best-known-configurations"
    count = 0
    for f in sorted(src.glob("config_n*.json")):
        shutil.copy(f, OUT_SPIRAL / f.name)
        count += 1
    shutil.copy(repo / "LICENSE", OUT_SPIRAL / "LICENSE")
    (OUT_SPIRAL / "ATTRIBUTION.md").write_text(
        "# Attribution\n\n"
        "Square configurations for n = 3..16 from [spiralulam/heilbronn]"
        "(https://github.com/spiralulam/heilbronn) (MIT license, vendored\n"
        "alongside), the companion repository to Nathan Sudermann-Merx's\n"
        "certified-optimality work (arXiv:2603.11107). Includes the\n"
        "previously unpublished configurations of Peter Karpov (n=13, 15)\n"
        "and Mark Beyleveld (n=14, 16), shared via Erich Friedman.\n")
    print(f"spiralulam: {count} configurations vendored")


def sync_alphaevolve(tejsteadqc_repo):
    if OUT_AE.exists():
        shutil.rmtree(OUT_AE)
    OUT_AE.mkdir(parents=True)
    count = 0
    for f in sorted((tejsteadqc_repo / "alphaevolve").glob("*.txt")):
        shutil.copy(f, OUT_AE / f.name)
        count += 1
    (OUT_AE / "ATTRIBUTION.md").write_text(
        "# Attribution\n\n"
        "Configurations found by AlphaEvolve (Google DeepMind), published\n"
        "June 2025 (arXiv:2506.13131); coordinates from\n"
        "[google-deepmind/alphaevolve_results]"
        "(https://github.com/google-deepmind/alphaevolve_results)\n"
        "(`mathematical_results.ipynb`), via the mirror in\n"
        "TejSteadQC/heilbronn-configurations.\n")
    print(f"alphaevolve: {count} files vendored")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tejsteadqc", required=True, type=pathlib.Path,
                    help="local clone of TejSteadQC/heilbronn-configurations")
    ap.add_argument("--spiralulam", type=pathlib.Path,
                    help="local clone of spiralulam/heilbronn (skip if absent)")
    args = ap.parse_args()

    sync_tejsteadqc(args.tejsteadqc)
    sync_alphaevolve(args.tejsteadqc)
    if args.spiralulam:
        sync_spiralulam(args.spiralulam)
    return 0


if __name__ == "__main__":
    sys.exit(main())

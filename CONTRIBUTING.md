# Contributing a configuration

Found a better arrangement — or have the original coordinates for an entry
this site only shows as a reconstruction? Submissions are plain pull
requests, verified automatically in exact arithmetic.

Contributions may come from human researchers, numerical solvers, or automated
search pipelines. To ensure consistency and automated validation, all submissions
follow a structured directory format and are verified by continuous integration
in exact rational arithmetic before merging.

**There is one submission lane**: `data/sources/external/`, for everyone,
including this site's own search pipeline.

## What to add

One directory per configuration — two required files, plus an optional
third if you know the exact algebraic value. A single PR may contain any
number of configuration directories; nothing else.

```
data/sources/external/<variant>-nNN/
├── coordinates.txt    required — the configuration
├── meta.json          required — provenance, credit, page note
└── exact.json         optional — the value's minimal polynomial
```

`<variant>` is `square`, `triangle`, or `convex`; `NN` is the zero-padded
point count (e.g. `triangle-n15`, `square-n07`). The number of points in
`coordinates.txt` must equal `NN`.

### coordinates.txt

One point per line, two decimal literals separated by whitespace. Lines
starting with `#` are comments.

```
# any comment you like
0.041156363310095543088824043693	0.917687273379808913822351912614
0.041156363310095543088824043693	0.041156363310095543088824043693
```

- **Plain decimals only** — no exponents, no fractions, at most 6 integer
  digits and 200 decimal places per literal. Literals are parsed as exact
  rationals, so what you write is exactly what is verified.
- **Frames.** `square`: 0 ≤ x, y ≤ 1. `triangle`: the unit right triangle
  x ≥ 0, y ≥ 0, x + y ≤ 1 (values are reported normalized to a unit-area
  triangle, i.e. doubled). `convex`: any coordinates — the domain is the
  points' own convex hull, and the value is area-normalized.
- **Feasibility is checked exactly.** A point at `0.9999999999…` with 200
  digits is fine; a point at `1.0000000001` is not. When rounding interior
  results, truncate toward zero (for the triangle this keeps x + y ≤ 1
  exactly; for the square it keeps coordinates inside [0, 1]).
- **Precision: 15 decimals minimum, 30 recommended.** Two reasons. Sources
  are ranked by the exact value their literals achieve, so a 30-decimal
  literal of a converged optimum beats a shorter one of the same
  arrangement. And the page's tie structure is computed exactly within
  1e-9 of the minimum: below ~12 decimals the intended ties collapse and
  the figure shows fewer minimal triangles than your configuration really
  has (the verifier warns when this is about to happen).

### meta.json

```json
{
 "ref": "where these coordinates come from (paper, repo, pipeline run)",
 "credit": "Your Name, August 2026",
 "note": "anything the configuration page should say about them"
}
```

`ref` is required; `credit` and `note` are optional but encouraged.

- `credit` should be `"Human Name, Month YYYY"` — if your submission beats
  the published record, this string becomes the entry's **Found by** line,
  so use the person's name, not a bot or account name.
- `note` is shown verbatim on the configuration's page provenance — write
  it for readers (method, one sentence, no marketing).

### exact.json (optional — for exact values)

If you know the configuration's exact value, add its **minimal polynomial**
as an integer coefficient list, constant term first, for the normalized
value A the site reports:

```json
{
 "minimal_polynomial": [-4, -13, 5438, 161469, 1609650, 5250987]
}
```

(that example encodes 5250987A⁵ + 1609650A⁴ + 161469A³ + 5438A² − 13A − 4,
the triangle n = 15 value). Coefficients too large for 64-bit tools may be
written as strings. No expression syntax is accepted — coefficients only.

The checker confirms in exact arithmetic that the polynomial has a root
within 1e-9 (relative) of the value implied by your coordinates —
irreducibility/minimality is not machine-checked, so double-check it
yourself before submitting. If your submission wins the entry, the
polynomial is re-validated at build time and rendered on the page.

## What happens on the PR

A workflow re-verifies every changed submission with the site's exact
verifier — all C(n,3) triples in rational arithmetic — and comments on the
PR with the exact value, tie structure, detected symmetry, and how it
compares to the current canonical entry. Invalid submissions (infeasible,
malformed, wrong point count, exact-value mismatch) fail the check; read
the comment, fix, push again.

Contributors listed in `.github/trusted-submitters.txt` skip review: their
PRs merge automatically once verification and CI pass — but only when the
PR touches nothing but `data/sources/external/` directories. Everyone
else's submissions wait for the maintainer to click merge. Any change to
code, templates, workflows, or curated data always requires review.

A submission that verifies but scores **below** the current value is still
welcome when it has provenance value — for example an original author's
arrangement for an entry we only have as a reconstruction. Say so in the
`note`.

After merge, `build/ingest.py` picks the best source per entry by exact
value, regenerates `data/canonical/`, and the site rebuilds and deploys
automatically — your configuration is live within about ten minutes.

Merging never lowers an entry. The check compares your coordinates against
`main` as it was when the check ran; if a better configuration lands in the
same directory before your PR is merged, the build keeps the higher-valued
coordinates (the committed canonical entry competes as a candidate of its
own and the overwrite is flagged in the build log). Rebase and re-check if
you believe you still improve on it.

## Checklist for automated agents

1. One directory per configuration under `data/sources/external/`, named
   `<variant>-nNN`; touch no other paths.
2. `coordinates.txt`: exactly NN points, plain decimals, 30 decimal places,
   truncated toward zero; verify feasibility in exact arithmetic before
   opening the PR.
3. `meta.json`: `ref` (required), `credit` as `"Human Name, Month YYYY"`,
   `note` one informative sentence.
4. `exact.json` only if you have verified the polynomial yourself.
5. Run the same check CI will run:
   `python3 scripts/check_submission.py data/sources/external/<dir>`.
6. After opening the PR, read the verification comment; on failure, fix and
   push to the same branch.

## Notes, corrections, references

Not everything needs coordinates. Corrections to credits, history, or notes
are PRs against `data/curated/` (`overrides.json`, `changelog.json`,
`references.json`) — see the existing entries for the shape. These are
reviewed by hand rather than by the verifier.

## Local check

```
make check-submission DIRS=data/sources/external/<variant>-nNN
make test
```

# Golden Verifier Fixtures

This directory contains a regression test corpus of point configurations alongside certified `verify_output.json` records. It is used by `tests/test_verify.py` and `tests/test_verifier_js.mjs` to ensure that the Python exact-rational verifier and the client-side JavaScript BigInt verifier produce identical results.

## Provenance & Coverage
- **Origin**: Most fixtures come from this site's own search campaigns and were verified by two independent exact verifiers at the time they were found. They span every container and a wide range of n.
- **Superseded Candidates**: Most fixtures were later improved upon by a newer record; the `-live` directories are snapshots of submissions that were current when copied here. Retaining superseded candidates preserves test coverage over large tie sets and near-degenerate triangles that current records may not exercise.

## Build Isolation
These fixtures exist exclusively for unit testing and CI verification. They are isolated from `data/sources/` and are not processed during the static site build or counted on the public leaderboard.

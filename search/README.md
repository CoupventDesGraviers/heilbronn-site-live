# Search toolkit

The record-hunting toolkit behind this site's own campaigns, originally
developed in a separate companion repository that has since been retired.
This copy makes the site repository self-contained:
everything the site shows can be found, polished, and verified with what is
in this tree.

- `attack.py` — basin-hopping search (perturb → local polish → keep best)
- `fastheil.py`, `heil.py` — fast objective evaluation / core geometry
- `search.py`, `ladder.py`, `grow.py`, `mirror.py` — search strategies
  (cold starts, n→n+1 laddering, symmetric seeding)
- `refine.py`, `sym.py` — trust-region SLP polishing, KKT tightening,
  symmetry detection and symmetric restriction
- `consensus.py`, `CONSENSUS_NOTES.md` — cross-checking independent runs
- `alphaevolve_extract.py` — importing configurations from AlphaEvolve runs
- `verify_a.py`, `verify_b.py` — two independent exact verifiers (the
  build's verifier is a library adaptation of `verify_a.py`)
- `render.py`, `gifseed.py` — figures and reconstruction seeds

`reconstruct/` (repo root) holds the site-specific reconstruction pipeline
built on top of these pieces.

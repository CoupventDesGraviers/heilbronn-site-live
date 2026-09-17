# heilbronn-site

Best known configurations for the Heilbronn triangle problem, served at
<https://math.tejstead.com/heilbronn>.

Place n points in a region of unit area so that the smallest triangle they
determine is as large as possible. This site keeps the record tables for
squares, triangles, and convex regions for n = 3 to 36, with exact
coordinates for every entry, closed forms and minimal polynomials where
they are known, symmetry and congruence shown on each figure, links to the
optimality proofs, and a verifier that runs in the browser.

The tables carry on from Erich Friedman's Packing Center, which went
offline in 2026.

Everything is generated ahead of time. The server only serves static files.
The viewer and the verifier are the only JavaScript on the site, and every
page reads fine without it.

Found a better configuration, or the exact value of one? Open a pull
request as described in [CONTRIBUTING.md](CONTRIBUTING.md). CI verifies the
coordinates in exact arithmetic, and the entry is live shortly after merge.

## Layout

- `data/sources/` — coordinate sources, one `ATTRIBUTION.md` per directory; `external/` is the submission lane
- `data/curated/` — the record ledger (`records.json`), references, overrides
- `data/canonical/` — one JSON per configuration, written by ingest and committed
- `build/` — the generator: ingest, verify, derive, render, downloads, compress
- `search/` — the search toolkit used for the site's own records
- `reconstruct/` — optimization to recover configurations whose coordinates were never published
- `proofs/` — formal proofs and external-verifier snapshots
- `scripts/` — submission checker and import helpers
- `templates/`, `assets/` — Jinja2 templates, CSS, JavaScript
- `tests/` — pytest and node golden tests for the two verifiers
- `deploy/` — Caddy snippets and the deploy scripts
- `landing/` — the tejstead.com front page

## Commands

```
make build        # full site into dist/
make test         # pytest + node --test
make serve        # preview at :8080
make serve-caddy  # production-identical preview at :8081
make deploy       # build, rsync to the server, reload Caddy
```

Every push to `main` is also built by the `publish-site` workflow into a
release tarball that the server pulls every five minutes, so a merged PR is
live within about ten minutes. `make deploy` is for immediate manual pushes
and is still needed for Caddyfile changes.

## Data provenance

The historical values, credits, and symmetry labels were recorded from the
Packing Center pages before they went offline and are maintained by hand in
`data/curated/records.json`. All figures are drawn from coordinates; none of
Friedman's images are used. Coordinates come from community submissions and
the site's own search campaigns (`data/sources/external/`),
[spiralulam/heilbronn](https://github.com/spiralulam/heilbronn) (MIT),
[google-deepmind/alphaevolve_results](https://github.com/google-deepmind/alphaevolve_results),
published exact constructions, or local reconstruction, which is labeled as
such on the page.

## License

Code is [MIT](LICENSE). Data under `data/sources/` carries its own
attribution; see the `ATTRIBUTION.md` next to each source.

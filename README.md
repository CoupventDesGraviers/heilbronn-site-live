# heilbronn-site

An open archive and computational atlas for the Heilbronn triangle problem,
served at <https://math.tejstead.com/heilbronn>.

This project continues and expands the historical records maintained for decades
at Erich Friedman's Packing Center (offline since 2026). It provides exact coordinates,
algebraic closed forms, symmetry and congruence visualizers, formal proof references,
and an in-browser exact rational arithmetic verifier across squares, triangles,
and general convex containers for n = 3 to 36.

The site is built as purely static HTML and vector SVGs with zero runtime dependencies.
Interactive features (such as the point viewer and coordinate verifier) enhance the
experience progressively while keeping all pages fully readable without JavaScript.

**Have a better configuration — or the exact value for one?** See
[CONTRIBUTING.md](CONTRIBUTING.md): submissions are plain pull requests
(coordinates, provenance, optionally a minimal polynomial), verified
automatically in exact arithmetic and live on the site minutes after merge.

## Layout

- `data/sources/` — vendored upstream inputs, each with `ATTRIBUTION.md`
- `data/curated/` — hand-maintained record ledger (`records.json`), references, overrides
- `data/canonical/` — the unified per-configuration JSONs (ingest output, committed)
- `build/` — the generator: ingest → verify → derive → render → downloads → compress
- `reconstruct/` — laptop-only optimization to recover unpublished configurations
- `proofs/` — source-only formal proofs and external-verifier snapshots
- `templates/`, `assets/` — jinja2 templates, CSS, vanilla JS
- `deploy/` — Caddy site snippets + `deploy.sh` (rsync + graceful reload)
- `landing/` — the tejstead.com apex page

## Commands

```
make build        # full site into dist/
make test         # pytest + node --test golden fixtures
make serve        # quick preview at :8080
make serve-caddy  # production-identical preview at :8081
make deploy       # build, rsync to the box, reload Caddy
```

Deploys are also continuous: every push to `main` is built by the
`publish-site` workflow into a rolling release tarball, which the server
pulls every 5 minutes (`deploy/site-pull.sh`, cron) — so a merged PR is
live within ~10 minutes with no laptop involved. `make deploy` remains for
instant manual pushes and is still required for Caddyfile changes.

## Data provenance

Historical values, credits, and symmetry labels are facts recorded from Erich
Friedman's Packing Center pages before they went offline, now maintained by
hand in `data/curated/records.json`; all figures are regenerated from
coordinates — none of his images are copied. Coordinates come from
[TejSteadQC/heilbronn-configurations](https://github.com/TejSteadQC/heilbronn-configurations),
[spiralulam/heilbronn](https://github.com/spiralulam/heilbronn) (MIT),
[google-deepmind/alphaevolve_results](https://github.com/google-deepmind/alphaevolve_results),
published exact constructions, or local reconstruction (labeled as such).

## License

Code is [MIT](LICENSE). Vendored data under `data/sources/` carries its own
attribution — see the `ATTRIBUTION.md` next to each source.

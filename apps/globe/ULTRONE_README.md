# ULTRONE Global Eye

Palantir/Anduril-style 3D globe console for ULTRONE: photorealistic Cesium
globe, live public-intel layers, tactical HUD — plus ULTRONE-native tracks
fed by the ULTRONE world model, track system, and battlefield simulation.

## Attribution

This app is built on **[God's Eye View](https://github.com/bilawalsidhu/gods-eye-view)**
by Bilawal Sidhu, MIT-licensed (see `LICENSE.UPSTREAM`). Upstream sources are
kept intact; ULTRONE-owned files are marked with an `ULTRONE-owned` header:

| ULTRONE-owned | Purpose |
|---|---|
| `src/layers/ultrone/` | Native track layer (glyphs, trails, labels, analyst seam) |
| `src/data/ultrone.js` | Layer wiring (source + overlay host) |
| `server/standalone/vite.ultrone-proxy.js` | `/api/ultrone` → Python geo API proxy plugin |
| `vite.config.ultrone.js` | ULTRONE dev config (proxy + iframe-safe headers) |
| `scripts/qa-ultrone-smoke.mjs` | Headless browser smoke QA |
| `ULTRONE_README.md` (this file) | ULTRONE docs |

Small intentional edits to upstream files: `package.json` (renamed to
`ultrone-globe`, added `dev:ultrone`), `src/app/data.js` (registers the
ULTRONE layer), `index.html` (title), 9 test files (package self-reference
`gods-eye-view/…` → `ultrone-globe/…`). Excluded from upstream: `docs/media/`
(68 MB of demo GIFs — see upstream repo), `.github/`, `.git`.

## Architecture

```
browser ──same origin──▶ Vite dev (vite.config.ultrone.js)
  │  /api/ultrone/* ──proxy──▶ Python geo API :8001 (packages/geospatial/api.py)
  │  /api/* (flights/ships/…) ──▶ node provider middleware (server/providers/)
  │
  Cesium globe + src/layers/* + src/layers/ultrone (world-model tracks)
```

The Python geo API (`packages/geospatial/`) snapshots
`world_model` entities + `sim` battlefield state + kinematic `tracks` into
`GET /api/ultrone/entities`, with a live `WS /api/ultrone/stream`. See
`tests/test_geo_service.py` and `docs/GLOBAL_EYE.md`.

## Run (Phase 1)

Requirements: Node ≥ 24 recommended (works on Node 22; see note below),
Python 3.10+ with the repo's `requirements.txt`.

```bash
# 1. Python geo API (terminal 1, repo root)
PYTHONPATH=<all buckets, see pytest.ini> python -m packages.geospatial.api
# serves 127.0.0.1:8001 — 21 demo tracks out of the box

# 2. Globe (terminal 2)
cd apps/globe
npm install
npm run dev:ultrone          # http://localhost:4173, keyless
```

Then toggle **◈ ULTRONE Tracks** in the data panel. No API keys needed:
Cesium renders keyless; key-gated layers (Google 3D, OpenAI voice) stay
dormant until keys are added in Provider Settings (Phase 3 scope).

Useful env vars:

| Var | Default | Purpose |
|---|---|---|
| `ULTRONE_GEO_URL` | `http://127.0.0.1:8001` | Geo API target for the Vite proxy |
| `ULTRONE_GEO_SEED` | `1` | `0` disables demo-theater seeding |
| `ULTRONE_GEO_ANCHOR_LAT/LON/SPAN_DEG` | `11.5/44.0/10.0` | Demo theater box (Gulf of Aden) |
| `HOST` / `PORT` | `localhost` / `4173` | Dev server bind (`0.0.0.0` opens LAN) |

## Tests

```bash
npm test                    # 3,400 unit tests (node:test runner)
node scripts/qa-ultrone-smoke.mjs   # headless browser smoke (needs Chrome)
```

Node 22 note: the suite passes on Node 22 (verified: 3400 pass, 0 fail).
Upstream calibrates two allocation microbenchmarks on Node 24; use Node ≥ 24
to match upstream exactly.

## Roadmap hooks (later phases)

- Phase 2 (intel feeds): more `server/providers/*` + `src/layers/*` — follow
  the earthquakes/ULTRONE layer pattern; Python adapters live in
  `packages/transport/` + `packages/geospatial/`.
- Phase 3 (services): voice (`src/voice/`), key management
  (`server/standalone/key-setup.js`), accounts/billing (new).
- WorldWideView interop: vendored reference at `vendor/worldwideview/`
  (Elastic-2.0, do not copy); its Agent Bus / plugin-SDK patterns are the
  integration seam for LLM globe control.

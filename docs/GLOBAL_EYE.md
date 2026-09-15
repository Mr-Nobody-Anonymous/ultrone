# ULTRONE Global Eye — sub-repo / folder map (Phase 1)

Where every piece of the globe integration lives, and why.

## New / integrated trees

| Path | Origin | Contents |
|---|---|---|
| `apps/globe/` | God's-Eye-View (MIT) + ULTRONE | The console: Cesium app (`src/`), node feed providers (`server/`), Vite configs, tests |
| `apps/globe/src/layers/ultrone/` | ULTRONE (new) | Native track layer: model/source/Cesium layer |
| `apps/globe/src/data/ultrone.js` | ULTRONE (new) | Layer registration wiring |
| `apps/globe/server/standalone/vite.ultrone-proxy.js` | ULTRONE (new) | `/api/ultrone` → Python proxy plugin |
| `apps/globe/vite.config.ultrone.js` | ULTRONE (new) | Dev config (proxy + embed-safe headers) |
| `apps/globe/vite.config.pages.js` | ULTRONE (new) | Pages build config (relative base for the `/ultrone/globe/` subpath) |
| `apps/globe/scripts/qa-pages-assets.mjs` | ULTRONE (new) | Deploy check: the staged build resolves every asset it references |
| `vendor/worldwideview/` | WorldWideView (Elastic-2.0) | Reference copy, as-is + `ULTRONE_VENDORED.txt`. Do not copy from it; integrate via its Agent Bus / plugin-SDK patterns |
| `packages/geospatial/service.py` | ULTRONE (new) | World-model + sim → geo entities, tracks, demo theater |
| `packages/geospatial/api.py` | ULTRONE (new) | FastAPI geo API (`/api/ultrone/*`, WS stream), standalone or mountable |
| `tests/test_geo_service.py` | ULTRONE (new) | 15 service + API tests |

## Reused ULTRONE backends (untouched)

| Path | Role in the globe |
|---|---|
| `packages/core/world_model/` | Canonical entities + positions (globe reads via geo service) |
| `packages/geospatial/tracks/` | `TrackManager` kinematic histories → motion trails |
| `packages/geospatial/layers/` | Canonical layer registry (shared vocabulary) |
| `simulation/sim/battlefield_env.py` | Grid sim → geo-mapped RED/BLUE tracks |
| `packages/transport/comms/` | (Phase 2) home for live-feed adapters |

## Untouched neighboring UIs

| Path | Role |
|---|---|
| `apps/frontend/` | Existing 2D React console (Leaflet/MapLibre) — left as-is |
| `apps/dashboard/` | Memory-system dashboard — left as-is |
| `apps/console/` | Console shell — left as-is |

## Data flow (Phase 1)

```
world_model ─┐
sim env ─────┼─▶ packages/geospatial/service.py ─▶ api.py :8001 ─┐
tracks ──────┘     (snapshot 1 Hz, GeoJSON-ish rows)              │ /api/ultrone/*
                                                                  ▼
public feeds ─▶ apps/globe node providers ─▶ Vite :4173 ─▶ Cesium globe
(USGS/CelesTrak/OpenSky keyless)            (proxy)      layers + ULTRONE tracks
```

## Deployment (GitHub Pages)

`.github/workflows/pages.yml` publishes two trees:

| Staged path | Public URL |
|---|---|
| `docs/` | `https://<owner>.github.io/ultrone/` (showcase) |
| `apps/globe/dist/` | `https://<owner>.github.io/ultrone/globe/` (this console) |

Because the globe build is mounted on a subpath rather than the site root,
`vite.config.pages.js` builds it with a relative base (`./`) and
`scripts/qa-pages-assets.mjs` verifies — before upload — that every referenced
asset exists under `site/globe/`, Cesium runtime included.
`scripts/export_geo_snapshot.py` bakes `ultrone-demo-snapshot.json` into the
build so the ULTRONE layer has data without the Python API.

WorldWideView (`vendor/worldwideview/`) is not on the serving path in
Phase 1; it is the reference implementation for Phase 2/3 plugin and
agent-control patterns.

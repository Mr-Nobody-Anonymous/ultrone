# mock-upstream

Tiny HTTP server used in CI to stand in for upstream data APIs (OpenSky, NASA FIRMS, Overpass, etc.) so seeder CI can run hermetically without real API keys or network flakiness.

## How it works

Mount a fixture directory at `/fixtures`. The directory must contain a `routes.json` mapping request paths → fixture filenames:

```json
{
  "/api/states/all": "opensky-states.json",
  "/api/v2/flights": "flights.json"
}
```

When the server receives `GET /api/states/all`, it serves the contents of `/fixtures/opensky-states.json`.

## Env vars

| Var | Default | Purpose |
|---|---|---|
| `FIXTURE_DIR` | `/fixtures` | Directory mounted from the seeder repo |
| `ROUTES_FILE` | `${FIXTURE_DIR}/routes.json` | Override the routes manifest path |
| `PORT` | `8080` | Listen port |

## Per-seeder convention

Each seeder ships its own `__fixtures__/` folder next to `src/`:

```
wwv-seeders-community/aviation/
├── src/index.ts
└── __fixtures__/
    ├── routes.json
    └── opensky-states.json
```

In CI compose, that folder is mounted into the mock-upstream container at `/fixtures` for the duration of the seeder smoke test.

## Architectural contract

Seeders MUST read upstream URLs from documented env vars with the production URL as the default, e.g.:

```ts
const UPSTREAM = process.env.OPENSKY_API_BASE ?? "https://opensky-network.org";
```

The CI compose then overrides `OPENSKY_API_BASE=http://mock-upstream:8080`. Without this convention, CI mocking is impossible — hardcoded URLs cannot be intercepted.

# Changelog

All notable changes to WorldWideView are documented here. This project follows
Conventional Commits and bumps semver in `package.json` per change.

## v1.3.0 - Location Intelligence (2026-05-31)

AI agents can now find places on Earth, fly the globe camera, bookmark entities,
and filter the live globe over MCP. The MCP server reports version `1.3.0`
(`MCP_SERVER_VERSION` bumped 1.2.0 -> 1.3.0).

### New MCP tools (8)

Geocoding and camera (`src/app/api/mcp/geocodingTools.ts`):

- `geocode_location` - resolve a place name or address to coordinates and a bounding
  box via OpenStreetMap Nominatim (per-user rate limit + 24h Redis cache).
- `fly_to` - fly the live globe camera to a coordinate or bounding box over the SSE bridge.

Favorites (`src/app/api/mcp/favoritesTools.ts`):

- `save_favorite` - bookmark an entity (upsert by entityId).
- `list_favorites` - list the user's bookmarks, each with a live/stale liveness status.
- `remove_favorite` - delete a bookmarked entity.

Live filtering (`src/app/api/mcp/filterTools.ts`):

- `set_filter` - apply filters to a plugin's layer on the live globe (no page reload).
- `clear_filter` - clear one plugin's filters, or all filters in one command.
- `get_plugin_filters` - read a plugin's declared filterable fields.

### Enhancements

- `search_entities` gained an optional `filters` param (`src/lib/mcp/tools.ts`),
  keyed by entity property key, to return only matching entities independent of any
  `set_filter` state.

### Documentation

- New `docs/plugin-filter-guide.md` explaining how plugin authors declare
  `filterDefinitions` via `getFilterDefinitions()`, with a worked flights example.
- All v1.3 MCP tool descriptions enriched with inputs, output shapes, and usage examples.
- `ConnectAgentHelper` agent prompt now lists every callable MCP tool.

### Versioning

- `MCP_SERVER_VERSION` bumped to `1.3.0`; `serverInfo.version` reflects it on every
  MCP initialize handshake.

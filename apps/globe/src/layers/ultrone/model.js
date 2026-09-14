// ULTRONE-owned layer model: presentation + validation for ULTRONE-native
// tracks served by the Python geo API (packages/geospatial/api.py).
// Follows the earthquakes layer conventions (overlay cohort, analyst seam).
import * as Cesium from 'cesium';

export const ULTRONE_OVERLAY_SOURCE_ID = 'ultrone';
export const ULTRONE_OVERLAY_COHORT_LIMIT = 96;
export const ULTRONE_OVERLAY_COLLISION_CAPACITY = 48;

const TEAM_CSS = {
  blue: '#38bdf8',
  red: '#f87171',
  neutral: '#e2e8f0',
  unknown: '#94a3b8',
};

/**
 * Tactical team color. Blue = friendly, red = hostile, neutral = white,
 * unknown = slate. Returns a Cesium.Color (pure — no viewer access).
 */
export function teamColor(team) {
  switch (String(team || '').toLowerCase()) {
    case 'blue':
      return Cesium.Color.fromCssColorString(TEAM_CSS.blue);
    case 'red':
      return Cesium.Color.fromCssColorString(TEAM_CSS.red);
    case 'neutral':
      return Cesium.Color.fromCssColorString(TEAM_CSS.neutral);
    default:
      return Cesium.Color.fromCssColorString(TEAM_CSS.unknown);
  }
}

export function teamAccent(team) {
  return TEAM_CSS[String(team || '').toLowerCase()] || TEAM_CSS.unknown;
}

/**
 * Build the source-owned overlay label for one ULTRONE track.
 * @param {object} input
 * @param {string} input.id Stable ULTRONE entity id.
 * @param {Cesium.Cartesian3} input.position Track anchor.
 * @param {string} input.name Display name.
 * @param {string} input.kind air|land|sea|space|cyber|facility|unknown.
 * @param {string} input.accent Source-owned team color (css).
 * @param {number} input.priority Cohort priority (higher = more important).
 */
export function createUltroneOverlayEntry({
  id,
  position,
  name,
  kind,
  accent,
  priority = 0,
}) {
  const label = String(name || id || 'TRACK');
  return {
    id: String(id),
    position,
    variant: 'label',
    title: kind && kind !== 'unknown' ? `${label} · ${kind.toUpperCase()}` : label,
    accent,
    priority: Number.isFinite(priority) ? priority : 0,
    collisionGroup: 'ambient-label',
    paintLane: 'ambient-label',
    interactive: false,
    edgeFade: 'keyhole',
    horizonCull: true,
    terrainOcclusion: false,
    gapPx: 15,
    verticalOnly: true,
    placement: 'above',
  };
}

/** Keep the highest-priority tracks, stable identity as tie-break. */
export function selectUltroneOverlayCohort(
  entries,
  limit = ULTRONE_OVERLAY_COHORT_LIMIT,
) {
  const cap = Math.max(
    0,
    Math.min(ULTRONE_OVERLAY_COHORT_LIMIT, Math.floor(Number(limit) || 0)),
  );
  if (!Array.isArray(entries) || cap === 0) return [];
  return entries
    .slice()
    .sort(
      (a, b) =>
        b.priority - a.priority || String(a.id).localeCompare(String(b.id)),
    )
    .slice(0, cap);
}

/**
 * Map one ULTRONE track to a JSON-safe analyst record. Pure — no Cesium
 * types. Missing/unknown fields are null, never NaN/undefined.
 */
export function mapUltroneAnalystRecord(raw, index = 0) {
  const num = (v) => (Number.isFinite(v) ? v : null);
  const text = (v) => {
    const t = String(v ?? '').trim();
    return t || null;
  };
  return {
    id: text(raw?.id) || `ULTRONE-${String(index).padStart(4, '0')}`,
    name: text(raw?.name),
    kind: text(raw?.kind),
    team: text(raw?.team),
    status: text(raw?.status),
    source: text(raw?.source),
    lat: num(raw?.lat),
    lon: num(raw?.lon),
    altM: num(raw?.alt_m),
    headingDeg: num(raw?.heading_deg),
    speedMps: num(raw?.speed_mps),
    confidence: num(raw?.confidence),
  };
}

function finiteOr(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

/**
 * Validate a complete /api/ultrone/entities payload before it can replace
 * displayed tracks. Returns normalized rows or null when malformed.
 * Rows: {id,name,kind,lat,lon,alt_m,heading_deg,speed_mps,status,team,
 *        confidence,source,track:[[lon,lat],...]}.
 */
export function normalizeUltroneSnapshot(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload))
    return null;
  const { entities, tracks } = payload;
  if (!Array.isArray(entities)) return null;
  if (tracks != null && (typeof tracks !== 'object' || Array.isArray(tracks)))
    return null;
  const rows = [];
  const ids = new Set();
  for (const entity of entities) {
    if (!entity || typeof entity !== 'object' || Array.isArray(entity))
      return null;
    const id = String(entity.id ?? '').trim();
    const lat = Number(entity.lat);
    const lon = Number(entity.lon);
    if (!id || ids.has(id) || !Number.isFinite(lat) || !Number.isFinite(lon))
      return null;
    if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;
    ids.add(id);
    const rawTrack = tracks?.[id];
    let track = null;
    if (rawTrack != null) {
      if (!Array.isArray(rawTrack)) return null;
      track = [];
      for (const wp of rawTrack) {
        if (!wp || typeof wp !== 'object') return null;
        const wlat = Number(wp.lat);
        const wlon = Number(wp.lon);
        if (!Number.isFinite(wlat) || !Number.isFinite(wlon)) return null;
        track.push([wlon, wlat]);
      }
    }
    rows.push({
      id,
      name: String(entity.name ?? id),
      kind: String(entity.kind ?? 'unknown'),
      lat,
      lon,
      alt_m: finiteOr(entity.alt_m, 0),
      heading_deg: finiteOr(entity.heading_deg, 0),
      speed_mps: finiteOr(entity.speed_mps, 0),
      status: String(entity.status ?? 'active'),
      team: String(entity.team ?? 'unknown'),
      confidence: finiteOr(entity.confidence, 1),
      source: String(entity.source ?? 'world_model'),
      track,
    });
  }
  return rows;
}

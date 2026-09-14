// ULTRONE-owned Cesium layer: native tracks from the ULTRONE world model /
// simulation, rendered with tactical team colors + motion trails.
// Lifecycle mirrors the earthquakes layer (init/enable/disable/update).
import * as Cesium from 'cesium';
import {
  ULTRONE_OVERLAY_COHORT_LIMIT,
  ULTRONE_OVERLAY_COLLISION_CAPACITY,
  ULTRONE_OVERLAY_SOURCE_ID,
  createUltroneOverlayEntry,
  mapUltroneAnalystRecord,
  selectUltroneOverlayCohort,
  teamAccent,
  teamColor,
} from './model.js';
export * from './model.js';
export { createUltroneSource } from './source.js';

/** Own one ULTRONE track display and its refresh lifecycle. */
export function createUltroneLayer({ source, overlayHost } = {}) {
  if (typeof source?.getSnapshot !== 'function')
    throw new TypeError('ULTRONE layer requires a snapshot source');
  if (!overlayHost) throw new TypeError('ULTRONE layer requires an overlay host');
  let _viewer = null;
  let _request = null;
  let _dataSource = null;
  let _count = 0;
  let _lastUpdate = null;
  let _lastError = null;
  let _enabled = false;

  const layer = {
    id: 'ultrone',
    name: 'ULTRONE Tracks',
    icon: '◈',
    source: 'ULTRONE',
    updateInterval: 5000,

    init(viewer) {
      if (_viewer) throw new Error('ULTRONE layer is already initialized');
      _viewer = viewer;
      _dataSource = new Cesium.CustomDataSource('ultrone');
      _dataSource.show = false;
      viewer.dataSources.add(_dataSource);
      _count = 0;
      _lastUpdate = null;
      _lastError = null;
      _enabled = false;
      overlayHost.setVisible(ULTRONE_OVERLAY_SOURCE_ID, false);
      console.log('[Data:ULTRONE] Initialized');
    },

    enable() {
      _enabled = true;
      if (_dataSource) _dataSource.show = true;
      overlayHost.setVisible(ULTRONE_OVERLAY_SOURCE_ID, true);
    },

    disable() {
      _request?.abort();
      _request = null;
      _enabled = false;
      if (_dataSource) _dataSource.show = false;
      overlayHost.clearSource(ULTRONE_OVERLAY_SOURCE_ID);
      overlayHost.setVisible(ULTRONE_OVERLAY_SOURCE_ID, false);
    },

    async update() {
      if (!_enabled || !_dataSource) return false;
      _request?.abort();
      const request = new AbortController();
      _request = request;
      try {
        const rows = await source.getSnapshot({ signal: request.signal });
        if (request.signal.aborted || _request !== request || !_enabled)
          return false;

        const nextEntities = [];
        let count = 0;
        const overlayEntries = [];

        for (const row of rows) {
          count++;
          const color = teamColor(row.team);
          const altitude = row.kind === 'air' ? row.alt_m : 0;
          const position = Cesium.Cartesian3.fromDegrees(
            row.lon,
            row.lat,
            altitude,
          );
          const glyphSize = row.kind === 'facility' ? 12 : 9;
          const glyph = new Cesium.Entity({
            id: `ultrone:${row.id}`,
            position,
            point: {
              pixelSize: glyphSize,
              color,
              outlineColor: Cesium.Color.WHITE.withAlpha(0.9),
              outlineWidth: 2,
              heightReference:
                row.kind === 'air'
                  ? Cesium.HeightReference.NONE
                  : Cesium.HeightReference.CLAMP_TO_GROUND,
              disableDepthTestDistance: Number.POSITIVE_INFINITY,
            },
            properties: {
              ultroneId: row.id,
              name: row.name,
              kind: row.kind,
              team: row.team,
              status: row.status,
              source: row.source,
              heading: row.heading_deg,
              speed: row.speed_mps,
              confidence: row.confidence,
            },
          });
          nextEntities.push(glyph);
          if (Array.isArray(row.track) && row.track.length >= 2) {
            const trailPositions = row.track.map(([lon, lat]) =>
              Cesium.Cartesian3.fromDegrees(lon, lat, altitude),
            );
            trailPositions.push(position);
            nextEntities.push(
              new Cesium.Entity({
                id: `ultrone:${row.id}:trail`,
                polyline: {
                  positions: trailPositions,
                  width: 2,
                  material: new Cesium.PolylineGlowMaterialProperty({
                    glowPower: 0.25,
                    color: color.withAlpha(0.85),
                  }),
                  clampToGround: row.kind !== 'air',
                },
              }),
            );
          }
          overlayEntries.push(
            createUltroneOverlayEntry({
              id: row.id,
              position,
              name: row.name,
              kind: row.kind,
              accent: teamAccent(row.team),
              priority: Math.round(row.confidence * 1000),
            }),
          );
        }

        _dataSource.entities.removeAll();
        for (const entity of nextEntities) _dataSource.entities.add(entity);
        if (_enabled) {
          overlayHost.setEntries(
            ULTRONE_OVERLAY_SOURCE_ID,
            selectUltroneOverlayCohort(overlayEntries),
            {
              cohortLimit: ULTRONE_OVERLAY_COHORT_LIMIT,
              collisionCapacity: ULTRONE_OVERLAY_COLLISION_CAPACITY,
              moving: true,
            },
          );
        }

        _count = count;
        _lastUpdate = Date.now();
        _lastError = null;
        console.log(`[Data:ULTRONE] Updated: ${_count} tracks`);
        return true;
      } catch (e) {
        if (request.signal.aborted || _request !== request || !_enabled)
          return false;
        console.warn('[Data:ULTRONE] Fetch error:', e);
        _lastError = e?.message || 'ULTRONE source unavailable';
        return false;
      } finally {
        if (_request === request) _request = null;
      }
    },

    destroy(viewer = _viewer) {
      _request?.abort();
      _request = null;
      _viewer = null;
      _enabled = false;
      overlayHost.clearSource(ULTRONE_OVERLAY_SOURCE_ID);
      overlayHost.setVisible(ULTRONE_OVERLAY_SOURCE_ID, false);
      if (_dataSource) {
        viewer.dataSources.remove(_dataSource, true);
        _dataSource = null;
      }
      _count = 0;
      _lastUpdate = null;
      _lastError = null;
    },

    /**
     * Snapshot in-memory tracks as plain JSON-safe analyst records.
     * On-demand only — zero per-frame cost.
     */
    getAnalystRecords(maxCount = 2000) {
      if (!_dataSource || !_dataSource.show) return [];
      const entities = _dataSource.entities.values.filter(
        (e) => e?.id && !String(e.id).endsWith(':trail'),
      );
      if (!entities.length) return [];
      const limit = Number.isFinite(maxCount)
        ? Math.max(1, Math.floor(maxCount))
        : 2000;
      const now = Cesium.JulianDate.now();
      const result = [];
      for (const entity of entities) {
        if (result.length >= limit) break;
        const cartesian = entity.position
          ? entity.position.getValue(now)
          : null;
        const carto = cartesian
          ? Cesium.Cartographic.fromCartesian(cartesian)
          : null;
        const p = entity.properties;
        result.push(
          mapUltroneAnalystRecord(
            {
              id: p?.ultroneId?.getValue(now) ?? null,
              name: p?.name?.getValue(now),
              kind: p?.kind?.getValue(now),
              team: p?.team?.getValue(now),
              status: p?.status?.getValue(now),
              source: p?.source?.getValue(now),
              heading_deg: p?.heading?.getValue(now),
              speed_mps: p?.speed?.getValue(now),
              confidence: p?.confidence?.getValue(now),
              lat: carto ? Cesium.Math.toDegrees(carto.latitude) : null,
              lon: carto ? Cesium.Math.toDegrees(carto.longitude) : null,
              alt_m: carto ? carto.height : null,
            },
            result.length,
          ),
        );
      }
      return result;
    },

    getStats() {
      return {
        count: _count,
        lastUpdate: _lastUpdate,
        error: _lastError,
      };
    },
  };
  return layer;
}

// ULTRONE-owned unit tests: pure layer-model functions (no viewer needed).
import assert from 'node:assert/strict';
import test from 'node:test';
import {
  createUltroneOverlayEntry,
  mapUltroneAnalystRecord,
  normalizeUltroneSnapshot,
  selectUltroneOverlayCohort,
  teamAccent,
} from './model.js';

test('normalizeUltroneSnapshot accepts a geo API payload', () => {
  const rows = normalizeUltroneSnapshot({
    generated_at: 1,
    count: 1,
    entities: [
      {
        id: 'demo-001',
        name: 'demo-001',
        kind: 'air',
        lat: 11.5,
        lon: 44.0,
        alt_m: 9000,
        heading_deg: 90,
        speed_mps: 120,
        status: 'active',
        team: 'blue',
        confidence: 0.9,
        source: 'demo',
      },
    ],
    tracks: { 'demo-001': [{ lat: 11.4, lon: 43.9 }] },
  });
  assert.equal(rows.length, 1);
  assert.equal(rows[0].id, 'demo-001');
  assert.deepEqual(rows[0].track, [[43.9, 11.4]]);
});

test('normalizeUltroneSnapshot rejects malformed payloads', () => {
  assert.equal(normalizeUltroneSnapshot(null), null);
  assert.equal(normalizeUltroneSnapshot({}), null);
  assert.equal(normalizeUltroneSnapshot({ entities: 'nope' }), null);
  assert.equal(
    normalizeUltroneSnapshot({ entities: [{ id: 'x', lat: 999, lon: 0 }] }),
    null,
  );
  assert.equal(
    normalizeUltroneSnapshot({
      entities: [
        { id: 'dup', lat: 0, lon: 0 },
        { id: 'dup', lat: 1, lon: 1 },
      ],
    }),
    null,
  );
});

test('overlay cohort keeps priority order with stable tie-break', () => {
  const entries = [
    createUltroneOverlayEntry({ id: 'b', position: null, priority: 5 }),
    createUltroneOverlayEntry({ id: 'a', position: null, priority: 5 }),
    createUltroneOverlayEntry({ id: 'c', position: null, priority: 9 }),
  ];
  const cohort = selectUltroneOverlayCohort(entries);
  assert.deepEqual(
    cohort.map((e) => e.id),
    ['c', 'a', 'b'],
  );
  assert.equal(teamAccent('blue'), '#38bdf8');
  assert.equal(teamAccent('red'), '#f87171');
});

test('mapUltroneAnalystRecord is JSON-safe', () => {
  const record = mapUltroneAnalystRecord({ id: '  ', lat: NaN }, 7);
  assert.equal(record.id, 'ULTRONE-0007');
  assert.equal(record.lat, null);
  assert.equal(record.name, null);
});

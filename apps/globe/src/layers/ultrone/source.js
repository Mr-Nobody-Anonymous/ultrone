// ULTRONE-owned snapshot source: the Python geo API (same origin in dev via
// the Vite /api/ultrone proxy; override with globalThis.__ULTRONE_API_BASE__)
// with a static-snapshot fallback for hosts without a backend (GitHub Pages
// serves apps/globe/public/ultrone-demo-snapshot.json next to the bundle).
import { normalizeUltroneSnapshot } from './model.js';

export const ULTRONE_ENTITIES_PATH = '/api/ultrone/entities';
export const ULTRONE_SNAPSHOT_ASSET = 'ultrone-demo-snapshot.json';

export function resolveUltroneBaseUrl(override) {
  if (typeof override === 'string' && override) return override;
  const globalBase =
    typeof globalThis !== 'undefined'
      ? globalThis.__ULTRONE_API_BASE__
      : undefined;
  if (typeof globalBase === 'string' && globalBase) return globalBase;
  return '';
}

// NOTE: keep the literal `import.meta.env.BASE_URL` access below — Vite
// replaces it statically at build time (dev: '/', Pages: '/ultrone/globe/').
function viteBaseUrl() {
  if (
    typeof import.meta !== 'undefined' &&
    import.meta.env &&
    typeof import.meta.env.BASE_URL === 'string' &&
    import.meta.env.BASE_URL
  ) {
    return import.meta.env.BASE_URL;
  }
  return '/';
}

export function resolveUltroneSnapshotUrl(override) {
  if (typeof override === 'string' && override) return override;
  const globalSnapshot =
    typeof globalThis !== 'undefined'
      ? globalThis.__ULTRONE_SNAPSHOT_URL__
      : undefined;
  if (typeof globalSnapshot === 'string' && globalSnapshot) return globalSnapshot;
  const base = viteBaseUrl();
  const root = base.endsWith('/') ? base : `${base}/`;
  return `${root}${ULTRONE_SNAPSHOT_ASSET}`;
}

async function fetchRows(fetchImpl, url, { signal } = {}) {
  const response = await fetchImpl(url, { signal });
  if (!response.ok) throw new Error(`ULTRONE HTTP ${response.status} (${url})`);
  const payload = await response.json();
  const rows = normalizeUltroneSnapshot(payload);
  if (!rows) throw new Error(`Malformed ULTRONE response (${url})`);
  return rows;
}

/** Request and validate a complete ULTRONE snapshot before display. */
export function createUltroneSource({
  baseUrl,
  snapshotUrl,
  fetchImpl = (...args) => globalThis.fetch(...args),
} = {}) {
  const root = resolveUltroneBaseUrl(baseUrl);
  const liveUrl = `${root}${ULTRONE_ENTITIES_PATH}`;
  const staticUrl = resolveUltroneSnapshotUrl(snapshotUrl);
  return {
    async getSnapshot({ signal } = {}) {
      signal?.throwIfAborted();
      try {
        const rows = await fetchRows(fetchImpl, liveUrl, { signal });
        signal?.throwIfAborted();
        return rows;
      } catch (liveError) {
        signal?.throwIfAborted();
        try {
          const rows = await fetchRows(fetchImpl, staticUrl, { signal });
          signal?.throwIfAborted();
          return rows;
        } catch (staticError) {
          throw new Error(
            `ULTRONE unreachable (live: ${liveError.message}; ` +
              `snapshot: ${staticError.message})`,
          );
        }
      }
    },
  };
}

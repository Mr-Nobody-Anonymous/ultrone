/**
 * @file seederHealthFetcher.ts
 * @description Client-side seeder-health snapshot fetch.
 *
 * On boot (or when the plugin panel opens) the globe asks its own origin for
 * GET /api/health; the globe's route probes the engine and can attach the
 * engine's `seederHealth` map (engine PR #53). The engine contract is frozen
 * but not necessarily deployed yet, so this reader is strictly additive:
 * a missing `seederHealth` field simply yields an empty map and the UI shows
 * no badges (graceful degradation).
 *
 * The response shape is normalized into the store's SeederHealth records so
 * badge derivation only ever sees well-formed entries.
 */

import { normalizeSeederHealth, type SeederHealth } from "@/core/state/seederHealthSlice";

const FETCH_TIMEOUT_MS = 5000;

/**
 * Fetch the current seeder-health snapshot from the globe's own /api/health
 * route and normalize it into a per-plugin SeederHealth map.
 *
 * Returns an empty map on any failure (network, non-2xx, missing field) —
 * this is a best-effort initial fill, never a hard dependency.
 */
export async function fetchSeederHealth(
    fetcher: typeof fetch = fetch,
): Promise<Record<string, SeederHealth>> {
    try {
        const res = await fetcher("/api/health", {
            signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
        });
        if (!res.ok) return {};
        const body: unknown = await res.json();
        const raw = (typeof body === "object" && body !== null ? body : {}) as Record<string, unknown>;
        const entries = raw.seederHealth;
        if (typeof entries !== "object" || entries === null) return {};

        const out: Record<string, SeederHealth> = {};
        for (const [pluginId, entry] of Object.entries(entries)) {
            out[pluginId] = normalizeSeederHealth(pluginId, entry);
        }
        return out;
    } catch {
        return {};
    }
}

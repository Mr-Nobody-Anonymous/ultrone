/**
 * @file seederHealthSlice.ts
 * @description Zustand slice holding per-plugin seeder health telemetry.
 *
 * The data engine reports seeder health in two ways (engine PR #53):
 *   1. Live deltas over WebSocket as `{ type: "status", pluginId, status,
 *      lastGood, health }` frames.
 *   2. A point-in-time snapshot over HTTP at GET /health under `seederHealth`
 *      (per-plugin object, computed at request time).
 *
 * Both feed this single store: HTTP is the initial fill so badges render
 * before the first broadcast (daily seeders could otherwise be blank for
 * hours); WS frames are live deltas that overwrite per-field.
 *
 * IMPORTANT: this interface is a HAND-MIRRORED copy of the engine's
 * SeederHealth contract. It must never be imported from the engine package —
 * the globe and the engine are separate repositories. If the engine contract
 * changes, update this file to match.
 */

import type { StateCreator } from "zustand";
import type { AppStore } from "./store";

// ─── Seeder Health Contract ─────────────────────────────────
/**
 * Mirrored engine SeederHealth contract (engine PR #53). See the module
 * comment for provenance. All staleness fields are server-computed; the
 * client must NEVER derive staleness from Date.now() (clock skew rule).
 */
export interface SeederHealth {
    pluginId: string;
    /** Epoch ms of the last successful run; null = never ran. */
    lastRun: number | null;
    lastError: string | null;
    failureCount: number;
    /** Polling interval in ms; null for cron/unknown. */
    intervalMs: number | null;
    cron: string | null;
    expectedMaxAgeMs: number | null;
    /** Server-computed freshness flag — authoritative, not client-derived. */
    stale: boolean;
}

/**
 * Minimal, defensive normalizer for WS `health` payloads. Unknown fields are
 * dropped, missing fields default to null/0 so badge derivation never has to
 * guard against malformed frames.
 */
export function normalizeSeederHealth(
    pluginId: string,
    raw: unknown,
): SeederHealth {
    const src = (typeof raw === "object" && raw !== null ? raw : {}) as Record<string, unknown>;
    return {
        pluginId,
        lastRun: typeof src.lastRun === "number" ? src.lastRun : null,
        lastError: typeof src.lastError === "string" ? src.lastError : null,
        failureCount: typeof src.failureCount === "number" ? src.failureCount : 0,
        intervalMs: typeof src.intervalMs === "number" ? src.intervalMs : null,
        cron: typeof src.cron === "string" ? src.cron : null,
        expectedMaxAgeMs: typeof src.expectedMaxAgeMs === "number" ? src.expectedMaxAgeMs : null,
        stale: src.stale === true,
    };
}

// ─── Slice ───────────────────────────────────────────────────
export interface SeederHealthSlice {
    /** Per-plugin seeder health, keyed by pluginId. */
    seederHealth: Record<string, SeederHealth>;
    /**
     * Merge a raw, unvalidated delta (e.g. the `health` field of a WebSocket
     * status frame) into one plugin's entry. Unknown fields are dropped and
     * missing fields default, so badge derivation never sees malformed data.
     */
    updateSeederHealth: (pluginId: string, patch: Record<string, unknown>) => void;
    /**
     * Replace the whole map with an HTTP snapshot (GET /health seederHealth).
     */
    setSeederHealth: (entries: Record<string, SeederHealth>) => void;
}

export const createSeederHealthSlice: StateCreator<AppStore, [], [], SeederHealthSlice> = (set) => ({
    seederHealth: {},
    updateSeederHealth: (pluginId, patch) =>
        set((state) => ({
            seederHealth: {
                ...state.seederHealth,
                [pluginId]: normalizeSeederHealth(pluginId, {
                    ...(state.seederHealth[pluginId] ?? null),
                    ...patch,
                }),
            },
        })),
    setSeederHealth: (entries) => set({ seederHealth: entries }),
});

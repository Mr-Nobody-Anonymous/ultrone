/**
 * @file freshness.ts
 * @description Skew-safe helpers for surfacing data freshness (fetchedAt) in the UI.
 *
 * The fetchedAt timestamp is produced by the data engine's server clock. Client
 * clocks may differ (skew), so these helpers never trust the client clock for
 * the displayed value: the label is always the raw server time. The client
 * clock is only used to pick a coarse color tier, with deliberately wide
 * thresholds (5m / 15m) so realistic skew cannot flip a tier.
 */

export type FreshnessTier = "fresh" | "aging" | "stale";

export interface FreshnessInfo {
    /** Coarse staleness tier derived with wide, skew-tolerant thresholds. */
    tier: FreshnessTier;
    /** Absolute server time label, e.g. "14:03:27Z". */
    label: string;
    /** Full server timestamp for tooltips. */
    title: string;
}

/** Wide thresholds so minutes of client/server clock skew cannot flip a tier. */
const FRESH_MAX_AGE_MS = 5 * 60 * 1000;
const AGING_MAX_AGE_MS = 15 * 60 * 1000;

/**
 * Derives display info from a server-provided fetchedAt ISO timestamp.
 * Returns null when fetchedAt is missing or unparseable — callers render nothing.
 */
export function getFreshness(fetchedAt: string | undefined | null, nowMs: number): FreshnessInfo | null {
    if (!fetchedAt) return null;
    const ts = Date.parse(fetchedAt);
    if (Number.isNaN(ts)) return null;

    // Negative age (server clock ahead of client) is treated as fresh.
    const age = Math.max(0, nowMs - ts);
    const tier: FreshnessTier = age < FRESH_MAX_AGE_MS ? "fresh" : age < AGING_MAX_AGE_MS ? "aging" : "stale";

    const date = new Date(ts);
    const hh = String(date.getUTCHours()).padStart(2, "0");
    const mm = String(date.getUTCMinutes()).padStart(2, "0");
    const ss = String(date.getUTCSeconds()).padStart(2, "0");

    return {
        tier,
        label: `${hh}:${mm}:${ss}Z`,
        title: `Data fetched at ${date.toISOString()} (server time)`,
    };
}

/**
 * @file seederHealthBadge.ts
 * @description Pure derivation of the freshness badge state from a
 * SeederHealth record.
 *
 * RULES (premortem-informed):
 *  - Render ONLY from server-provided fields (stale / lastError / lastRun).
 *    NEVER compute staleness client-side from Date.now() (clock skew rule).
 *  - No health data at all -> null (show nothing, graceful).
 *  - Badge priority: error (lastError) > stale > live.
 */

import type { SeederHealth } from "@/core/state/seederHealthSlice";

export type SeederBadgeState = "error" | "stale" | "live";

export interface SeederBadge {
    state: SeederBadgeState;
    label: string;
    title: string;
}

/** Derive the badge for a plugin's seeder health. null = no health data. */
export function deriveSeederBadge(health: SeederHealth | undefined | null): SeederBadge | null {
    if (!health) return null;

    if (health.lastError !== null) {
        return {
            state: "error",
            label: "error",
            title: `Seeder error: ${health.lastError}`,
        };
    }

    if (health.stale === true) {
        return {
            state: "stale",
            label: "stale",
            title: "Seeder is stale (last run exceeded its expected freshness window)",
        };
    }

    // The engine computed this seeder as fresh.
    return {
        state: "live",
        label: "live",
        title: "Seeder is live",
    };
}

/**
 * Checklist rows for the 'why is my layer empty?' panel. Every row is derived
 * from the SAME server-computed SeederHealth object; it is a static checklist
 * only — no interactive diagnostics, no new state machine.
 */
export interface ChecklistRow {
    id: string;
    label: string;
    /** True when this row is a likely culprit (checked/highlighted). */
    suspect: boolean;
}

export function deriveSeederChecklist(health: SeederHealth | undefined | null): ChecklistRow[] {
    if (!health) {
        return [
            {
                id: "no-telemetry",
                label: "No seeder health reported yet — check that the data engine is running.",
                suspect: false,
            },
        ];
    }

    return [
        {
            id: "never-ran",
            label: "Seeder has never run successfully.",
            suspect: health.lastRun === null,
        },
        {
            id: "stale",
            label: "Seeder is stale — it has not refreshed within its expected window.",
            suspect: health.stale === true,
        },
        {
            id: "last-error",
            label: "Seeder reported an error on its last run.",
            suspect: health.lastError !== null,
        },
        {
            id: "failures",
            label: "Seeder has accumulated repeated failures.",
            suspect: health.failureCount > 0,
        },
    ];
}

/**
 * @file entityBudget.ts
 * @description Per-layer entity budget with stable deterministic thinning.
 * Applied at the data layer (before entities enter the store) so the renderer
 * never fights primitive cleanup against truncation churn.
 */

import type { GeoEntity } from "@/core/plugins/PluginTypes";

// ─── Budget Defaults ─────────────────────────────────────────

/**
 * Default per-layer entity budget. Matches the chunked-rendering design point
 * (10k+ datasets chunked at 500) with generous headroom; telemetry from
 * budget-exceeded logs will inform tightening this default later.
 */
export const DEFAULT_LAYER_ENTITY_BUDGET = 5000;

/** Environment override for the global default (parsed once at module load). */
const ENV_BUDGET = Number(process.env.NEXT_PUBLIC_LAYER_ENTITY_BUDGET);

/**
 * Global fallback budget: env override when set to a positive integer,
 * otherwise the built-in default.
 */
export const GLOBAL_LAYER_ENTITY_BUDGET =
    Number.isFinite(ENV_BUDGET) && ENV_BUDGET > 0 ? Math.floor(ENV_BUDGET) : DEFAULT_LAYER_ENTITY_BUDGET;

// ─── Deterministic Thinning ──────────────────────────────────

/**
 * FNV-1a 32-bit hash of an entity id. Pure and stable across sessions,
 * platforms, and feed orderings.
 */
function hashId(id: string): number {
    let hash = 0x811c9dc5;
    for (let i = 0; i < id.length; i++) {
        hash ^= id.charCodeAt(i);
        hash = Math.imul(hash, 0x01000193);
    }
    // Normalize to [0, 1) so budgets compare against a uniform score.
    return (hash >>> 0) / 0x100000000;
}

/** Per-entity deterministic score, memoized by id to keep repeated ticks cheap. */
const scoreCache = new Map<string, number>();

function entityScore(id: string): number {
    let score = scoreCache.get(id);
    if (score === undefined) {
        score = hashId(id);
        // Bound the cache so long-running sessions with churning feeds do not leak.
        if (scoreCache.size > 50000) scoreCache.clear();
        scoreCache.set(id, score);
    }
    return score;
}

/**
 * Result of applying an entity budget to an incoming feed.
 */
export interface BudgetResult {
    /** The entities that survived the budget (original feed order preserved). */
    kept: GeoEntity[];
    /** Whether the budget removed anything. */
    budgetExceeded: boolean;
    /** Total entities received before thinning. */
    totalCount: number;
    /** The effective budget that was applied. */
    budgetCap: number;
}

/**
 * Applies a per-layer entity budget with stable, spatially-uniform thinning.
 *
 * The thinning keeps the `budget` entities with the lowest deterministic hash
 * score of their id. Like dealing every aircraft in the sky a fixed lottery
 * ticket number at birth: no matter how often the list is re-read or reordered,
 * the same ticket numbers win, so the visible fleet stops flickering between
 * ticks. A membership change naturally alters which tickets are in the draw,
 * which is the only legitimate reason for the subset to change. Feed order
 * (newest-first vs oldest-first) never affects who wins, so the newest
 * aircraft are never systematically dropped.
 *
 * @param entities Incoming entities for one plugin.
 * @param budget Maximum number of entities to keep (> 0).
 */
export function applyEntityBudget(entities: GeoEntity[], budget: number): BudgetResult {
    const totalCount = entities.length;
    const budgetCap = budget > 0 ? Math.floor(budget) : GLOBAL_LAYER_ENTITY_BUDGET;

    if (totalCount <= budgetCap) {
        return { kept: entities, budgetExceeded: false, totalCount, budgetCap };
    }

    // Find the score threshold that admits exactly `budgetCap` entities:
    // scores are effectively uniform in [0,1), so the winners are spread
    // uniformly across the dataset rather than clustered (no tail-drop).
    const scores = entities.map((e) => entityScore(e.id));
    const sorted = [...scores].sort((a, b) => a - b);
    const threshold = sorted[budgetCap - 1];

    const kept: GeoEntity[] = [];
    let admittedByThreshold = 0;
    for (let i = 0; i < entities.length; i++) {
        if (scores[i] < threshold) {
            kept.push(entities[i]);
            admittedByThreshold++;
        }
    }
    // Fill the remaining slots with entities sitting exactly on the threshold
    // (hash collisions), in feed order, to land exactly on the budget.
    if (admittedByThreshold < budgetCap) {
        for (let i = 0; i < entities.length && admittedByThreshold < budgetCap; i++) {
            if (scores[i] === threshold) {
                kept.push(entities[i]);
                admittedByThreshold++;
            }
        }
    }

    return { kept, budgetExceeded: true, totalCount, budgetCap };
}

/**
 * Resolves the effective budget for a plugin: per-layer setting first
 * (`dataConfig.pluginSettings[pluginId].entityBudget`), then the global
 * env-configurable default.
 */
export function resolveLayerBudget(pluginId: string, pluginSettings: Record<string, Record<string, unknown>>): number {
    const perLayer = pluginSettings[pluginId]?.entityBudget;
    if (typeof perLayer === "number" && Number.isFinite(perLayer) && perLayer > 0) {
        return Math.floor(perLayer);
    }
    return GLOBAL_LAYER_ENTITY_BUDGET;
}

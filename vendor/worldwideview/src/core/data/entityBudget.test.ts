import { describe, it, expect } from "vitest";
import { applyEntityBudget, resolveLayerBudget, GLOBAL_LAYER_ENTITY_BUDGET, DEFAULT_LAYER_ENTITY_BUDGET } from "./entityBudget";
import type { GeoEntity } from "@/core/plugins/PluginTypes";

function makeEntity(id: string): GeoEntity {
    return {
        id,
        pluginId: "test-plugin",
        latitude: 0,
        longitude: 0,
        timestamp: new Date("2026-01-01T00:00:00Z"),
        properties: {},
    };
}

function makeEntities(n: number): GeoEntity[] {
    return Array.from({ length: n }, (_, i) => makeEntity(`entity-${i}`));
}

describe("applyEntityBudget", () => {
    it("passes through unchanged when budget is not exceeded", () => {
        const entities = makeEntities(100);
        const result = applyEntityBudget(entities, 5000);
        expect(result.kept).toBe(entities);
        expect(result.budgetExceeded).toBe(false);
        expect(result.totalCount).toBe(100);
        expect(result.budgetCap).toBe(5000);
    });

    it("thins to exactly the budget", () => {
        const entities = makeEntities(300);
        const result = applyEntityBudget(entities, 100);
        expect(result.kept).toHaveLength(100);
        expect(result.budgetExceeded).toBe(true);
        expect(result.totalCount).toBe(300);
    });

    it("is deterministic: same input produces the same subset", () => {
        const entities = makeEntities(300);
        const a = applyEntityBudget(entities, 100);
        const b = applyEntityBudget([...entities], 100);
        expect(a.kept.map((e) => e.id)).toEqual(b.kept.map((e) => e.id));
    });

    it("is order-independent: same membership in a different order yields the same subset of ids", () => {
        const entities = makeEntities(300);
        const reversed = [...entities].reverse();
        const a = applyEntityBudget(entities, 100).kept.map((e) => e.id).sort();
        const b = applyEntityBudget(reversed, 100).kept.map((e) => e.id).sort();
        expect(a).toEqual(b);
    });

    it("keeps a stable subset across ticks when membership is unchanged", () => {
        const tick1 = makeEntities(300);
        const result1 = applyEntityBudget(tick1, 100);
        // Simulate a new WS tick: same entities, perturbed order and refreshed payloads.
        const tick2 = [...tick1].reverse().map((e) => ({ ...e, timestamp: new Date() }));
        const result2 = applyEntityBudget(tick2, 100);
        const ids1 = new Set(result1.kept.map((e) => e.id));
        const ids2 = new Set(result2.kept.map((e) => e.id));
        expect(ids1).toEqual(ids2);
    });

    it("admits a new member only through a new deterministic draw when membership changes", () => {
        const base = makeEntities(300);
        const keptBefore = new Set(applyEntityBudget(base, 100).kept.map((e) => e.id));
        // Re-run with identical membership: subset never changes between ticks.
        expect(new Set(applyEntityBudget(base, 100).kept.map((e) => e.id))).toEqual(keptBefore);
        // Adding one member is a membership change; the budget still holds and the
        // subset is again deterministic for the new membership.
        const grown = [...base, makeEntity("newcomer")];
        const grownResult = applyEntityBudget(grown, 100);
        expect(grownResult.kept).toHaveLength(100);
        expect(new Set(applyEntityBudget(grown, 100).kept.map((e) => e.id))).toEqual(
            new Set(grownResult.kept.map((e) => e.id))
        );
    });

    it("does not systematically drop the tail (newest) of the feed", () => {
        const entities = makeEntities(1000);
        const kept = new Set(applyEntityBudget(entities, 100).kept.map((e) => e.id));
        // Entities from the last 10% of the feed must still be represented.
        const tail = entities.slice(-100);
        const tailSurvivors = tail.filter((e) => kept.has(e.id)).length;
        expect(tailSurvivors).toBeGreaterThan(0);
    });

    it("preserves original feed order in the kept array", () => {
        const entities = makeEntities(200);
        const kept = applyEntityBudget(entities, 50).kept;
        const positions = kept.map((e) => entities.indexOf(e));
        expect(positions).toEqual([...positions].sort((a, b) => a - b));
    });
});

describe("resolveLayerBudget", () => {
    it("falls back to the global default without per-layer settings", () => {
        expect(resolveLayerBudget("p", {})).toBe(GLOBAL_LAYER_ENTITY_BUDGET);
        expect(GLOBAL_LAYER_ENTITY_BUDGET).toBe(DEFAULT_LAYER_ENTITY_BUDGET);
    });

    it("prefers a valid per-layer setting", () => {
        expect(resolveLayerBudget("p", { p: { entityBudget: 250 } })).toBe(250);
    });

    it("ignores invalid per-layer settings", () => {
        expect(resolveLayerBudget("p", { p: { entityBudget: -5 } })).toBe(GLOBAL_LAYER_ENTITY_BUDGET);
        expect(resolveLayerBudget("p", { p: { entityBudget: "many" } })).toBe(GLOBAL_LAYER_ENTITY_BUDGET);
    });
});

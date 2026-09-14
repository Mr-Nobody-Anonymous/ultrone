import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { DataBusSubscriber } from "./DataBusSubscriber";
import { dataBus } from "@/core/data/DataBus";
import { useStore } from "@/core/state/store";
import type { GeoEntity } from "@/core/plugins/PluginTypes";

vi.mock("@/core/plugins/PluginManager", () => ({
    pluginManager: {
        setCacheMaxAge: vi.fn(),
        getManifest: vi.fn(() => undefined),
        getAllPlugins: vi.fn(() => []),
    },
}));

vi.mock("@/core/data/WsClient", () => ({
    wsClient: { subscribe: vi.fn(), unsubscribe: vi.fn() },
}));

vi.mock("@/core/data/resolveEngineUrl", () => ({
    resolveEngineUrl: vi.fn(() => "http://localhost:5000"),
}));

vi.mock("@/core/data/engineManifest", () => ({
    fetchLocalEngineManifest: vi.fn(),
}));

function makeEntities(n: number, pluginId = "budget-plugin"): GeoEntity[] {
    return Array.from({ length: n }, (_, i) => ({
        id: `${pluginId}-${i}`,
        pluginId,
        latitude: 0,
        longitude: 0,
        timestamp: new Date("2026-01-01T00:00:00Z"),
        properties: {},
    }));
}

describe("DataBusSubscriber entity budget", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        const { entitiesByPlugin, layers, dataConfig } = useStore.getState();
        // Reset relevant store state without full teardown of other slices.
        for (const key of Object.keys(entitiesByPlugin)) {
            useStore.getState().clearEntities(key);
        }
        for (const key of Object.keys(layers)) {
            useStore.getState().removeLayer(key);
        }
        if (Object.keys(dataConfig.pluginSettings).length > 0) {
            useStore.setState({ dataConfig: { ...dataConfig, pluginSettings: {} } });
        }
    });

    it("stores the thinned subset and records budget state when a feed exceeds the budget", async () => {
        render(<DataBusSubscriber />);
        const entities = makeEntities(6000);
        const debugSpy = vi.spyOn(console, "debug").mockImplementation(() => {});

        dataBus.emit("dataUpdated", { pluginId: "budget-plugin", entities });

        await waitFor(() => {
            const state = useStore.getState();
            expect(state.entitiesByPlugin["budget-plugin"]).toHaveLength(5000);
            expect(state.layers["budget-plugin"].entityCount).toBe(6000);
            expect(state.layers["budget-plugin"].budgetExceeded).toBe(true);
            expect(state.layers["budget-plugin"].renderedCount).toBe(5000);
            expect(state.layers["budget-plugin"].budgetCap).toBe(5000);
        });
        expect(debugSpy).toHaveBeenCalledWith(expect.stringContaining("exceeded entity budget"));
        debugSpy.mockRestore();
    });

    it("passes feeds within budget through untouched with no exceeded flag", async () => {
        render(<DataBusSubscriber />);
        const entities = makeEntities(10);

        dataBus.emit("dataUpdated", { pluginId: "budget-plugin", entities });

        await waitFor(() => {
            const state = useStore.getState();
            expect(state.entitiesByPlugin["budget-plugin"]).toHaveLength(10);
            expect(state.layers["budget-plugin"].budgetExceeded).toBe(false);
            expect(state.layers["budget-plugin"].renderedCount).toBe(10);
            expect(state.layers["budget-plugin"].entityCount).toBe(10);
        });
    });

    it("honors a per-layer entityBudget plugin setting", async () => {
        useStore.getState().updatePluginSettings("budget-plugin", { entityBudget: 100 });
        render(<DataBusSubscriber />);
        const entities = makeEntities(250);

        dataBus.emit("dataUpdated", { pluginId: "budget-plugin", entities });

        await waitFor(() => {
            const state = useStore.getState();
            expect(state.entitiesByPlugin["budget-plugin"]).toHaveLength(100);
            expect(state.layers["budget-plugin"].budgetCap).toBe(100);
            expect(state.layers["budget-plugin"].entityCount).toBe(250);
        });
    });
});

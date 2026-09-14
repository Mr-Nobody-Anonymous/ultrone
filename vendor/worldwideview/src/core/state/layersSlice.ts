/**
 * @file layersSlice.ts
 * @description State slice managing the lifecycle, visibility, and loading status of data layers (plugins).
 */

import type { StateCreator } from "zustand";
import type { AppStore } from "./store";

// ─── Layers Slice ────────────────────────────────────────────
/**
 * Runtime state for a single data layer.
 */
export interface LayerState {
    /** Whether the layer is currently active and fetching/rendering data. */
    enabled: boolean;
    /** The number of entities currently loaded in this layer. */
    entityCount: number;
    /** Whether the layer is currently waiting for a network response. */
    loading: boolean;
    /** Server-provided ISO timestamp of the last snapshot received for this layer, if any. */
    fetchedAt?: string;
    /** The effective entity budget applied to this layer (set when data arrives). */
    budgetCap?: number;
    /** How many entities actually render after budget thinning. */
    renderedCount?: number;
    /** True when the incoming feed exceeded the budget and was thinned. */
    budgetExceeded?: boolean;
}

/**
 * Zustand state slice for managing plugin layers.
 */
export interface LayersSlice {
    /** Map of plugin IDs to their current LayerState. */
    layers: Record<string, LayerState>;
    /** Toggles the active status of a layer. */
    toggleLayer: (pluginId: string) => void;
    /** Explicitly enables or disables a specific layer. */
    setLayerEnabled: (pluginId: string, enabled: boolean) => void;
    /** Updates the entity count displayed in the UI for a specific layer. */
    setEntityCount: (pluginId: string, count: number) => void;
    /** Updates the loading state indicator for a specific layer. */
    setLayerLoading: (pluginId: string, loading: boolean) => void;
    /** Records the server-provided fetchedAt of the latest snapshot for freshness display. */
    setLayerFetchedAt: (pluginId: string, fetchedAt: string | undefined) => void;
    /** Records budget thinning outcome for a layer (never-silent truncation surfacing). */
    setLayerBudget: (pluginId: string, budget: { budgetCap: number; renderedCount: number; budgetExceeded: boolean }) => void;
    /** Initializes a new layer entry in the state if it doesn't already exist. */
    initLayer: (pluginId: string, defaultEnabled?: boolean) => void;
    /** Completely removes a layer from the state. */
    removeLayer: (pluginId: string) => void;
}

export const createLayersSlice: StateCreator<AppStore, [], [], LayersSlice> = (set) => ({
    layers: {},
    toggleLayer: (pluginId) => set((state) => ({
            layers: {
                ...state.layers,
                [pluginId]: {
                    ...state.layers[pluginId],
                    enabled: !state.layers[pluginId]?.enabled,
                },
            },
        })),
    setLayerEnabled: (pluginId, enabled) => set((state) => ({
            layers: {
                ...state.layers,
                [pluginId]: { ...state.layers[pluginId], enabled },
            },
        })),
    setEntityCount: (pluginId, count) => set((state) => ({
            layers: {
                ...state.layers,
                [pluginId]: { ...state.layers[pluginId], entityCount: count },
            },
        })),
    setLayerLoading: (pluginId, loading) => set((state) => ({
            layers: {
                ...state.layers,
                [pluginId]: { ...state.layers[pluginId], loading },
            },
        })),
    setLayerFetchedAt: (pluginId, fetchedAt) => set((state) => ({
            layers: {
                ...state.layers,
                [pluginId]: { ...state.layers[pluginId], fetchedAt },
            },
        })),
    setLayerBudget: (pluginId, budget) => set((state) => ({
            layers: {
                ...state.layers,
                [pluginId]: { ...state.layers[pluginId], ...budget },
            },
        })),
    initLayer: (pluginId, defaultEnabled = false) => set((state) => ({
            layers: {
                ...state.layers,
                [pluginId]: state.layers[pluginId] || { enabled: defaultEnabled, entityCount: 0, loading: false },
            },
        })),
    removeLayer: (pluginId) => set((state) => {
        const copy = { ...state.layers };
        delete copy[pluginId];
        return { layers: copy };
    }),
});

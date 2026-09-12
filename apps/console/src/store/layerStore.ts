import { create } from 'zustand';
import { MapLayer, INITIAL_LAYERS } from '../types/layer';

interface LayerState {
  layers: MapLayer[];
  isLayerDrawerOpen: boolean;

  toggleLayerDrawer: () => void;
  setLayerDrawerOpen: (open: boolean) => void;
  toggleLayer: (id: string) => void;
  setLayerOpacity: (id: string, opacity: number) => void;
  resetLayers: () => void;
}

export const useLayerStore = create<LayerState>((set) => ({
  layers: INITIAL_LAYERS,
  isLayerDrawerOpen: false,

  toggleLayerDrawer: () => set((s) => ({ isLayerDrawerOpen: !s.isLayerDrawerOpen })),
  setLayerDrawerOpen: (open) => set({ isLayerDrawerOpen: open }),

  toggleLayer: (id) =>
    set((s) => ({
      layers: s.layers.map((l) => (l.id === id ? { ...l, enabled: !l.enabled } : l)),
    })),

  setLayerOpacity: (id, opacity) =>
    set((s) => ({
      layers: s.layers.map((l) =>
        l.id === id ? { ...l, opacity: Math.max(0, Math.min(1, opacity)) } : l,
      ),
    })),

  resetLayers: () => set({ layers: INITIAL_LAYERS }),
}));

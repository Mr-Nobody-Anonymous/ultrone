// Copyright (c) Ultrone Contributors. All rights reserved.
/**
 * Centralized Zustand state store for the ULTRONE Cockpit UI.
 */

import { create } from 'zustand';
import { cockpitApi, connectCockpitWebSocket } from '../api/client';
import type {
  CockpitOverview,
  WorldSnapshot,
  SystemTruth,
  AgentRecord,
  DeviceRecord,
  StoredEvent,
  DecisionTrace,
  WhyBlockedResult,
  SearchResultItem,
} from '../api/types';

export type InspectorTab = 'visual' | 'provenance' | 'json';

export interface InspectorTarget {
  type: 'agent' | 'device' | 'event' | 'decision' | 'policy' | 'metric';
  id: string;
  data?: any;
}

interface CockpitState {
  // Global & Connectivity
  overview: CockpitOverview | null;
  world: WorldSnapshot | null;
  truth: SystemTruth | null;
  connectionStatus: 'connected' | 'reconnecting' | 'degraded' | 'disconnected';
  lastSyncTimestamp: number;

  // Selection & Inspector
  inspectorOpen: boolean;
  inspectorTarget: InspectorTarget | null;
  inspectorTab: InspectorTab;

  // Dialogs & Overlays
  commandPaletteOpen: boolean;
  systemTruthModalOpen: boolean;
  whyBlockedResult: WhyBlockedResult | null;
  faultInjectionOpen: boolean;

  // Research Mode & UI Preferences
  researchMode: boolean;
  theme: 'dark' | 'light' | 'contrast';

  // Search
  searchQuery: string;
  searchResults: SearchResultItem[];
  isSearching: boolean;

  // Actions
  init: () => () => void;
  refreshOverview: () => Promise<void>;
  refreshWorld: () => Promise<void>;
  play: (speed?: number) => Promise<void>;
  pause: () => Promise<void>;
  step: (count?: number) => Promise<void>;
  reset: () => Promise<void>;
  setSpeed: (speed: number) => Promise<void>;
  injectFaults: (config: Record<string, any>) => Promise<void>;
  clearFaults: () => Promise<void>;

  // Selection & Inspector actions
  inspect: (type: InspectorTarget['type'], id: string, data?: any) => void;
  closeInspector: () => void;
  setInspectorTab: (tab: InspectorTab) => void;

  // Dialog actions
  setCommandPalette: (open: boolean) => void;
  setSystemTruthModal: (open: boolean) => void;
  setWhyBlockedResult: (result: WhyBlockedResult | null) => void;
  setFaultInjectionOpen: (open: boolean) => void;
  toggleResearchMode: () => void;
  setTheme: (theme: 'dark' | 'light' | 'contrast') => void;

  // Search actions
  setSearchQuery: (q: string) => void;
  executeSearch: (q: string) => Promise<void>;
}

export const useCockpitStore = create<CockpitState>((set, get) => ({
  overview: null,
  world: null,
  truth: null,
  connectionStatus: 'connected',
  lastSyncTimestamp: Date.now(),

  inspectorOpen: false,
  inspectorTarget: null,
  inspectorTab: 'visual',

  commandPaletteOpen: false,
  systemTruthModalOpen: false,
  whyBlockedResult: null,
  faultInjectionOpen: false,

  researchMode: false,
  theme: 'dark',

  searchQuery: '',
  searchResults: [],
  isSearching: false,

  init: () => {
    // 1. Initial REST fetch
    get().refreshOverview();
    get().refreshWorld();

    // 2. Setup periodic polling for resilient sync
    const pollInterval = setInterval(() => {
      get().refreshOverview();
      get().refreshWorld();
    }, 2000);

    // 3. Connect live WebSocket
    const disconnectWs = connectCockpitWebSocket(
      (data) => {
        if (data.type === 'cockpit_tick') {
          set({
            lastSyncTimestamp: Date.now(),
            connectionStatus: 'connected',
          });
          // Update overview run tick in real-time
          const currentOverview = get().overview;
          if (currentOverview) {
            set({
              overview: {
                ...currentOverview,
                run: {
                  ...currentOverview.run,
                  tick: data.tick,
                  health_percent: data.summary.health_percent,
                  playing: data.summary.playing,
                  speed: data.summary.speed,
                },
              },
            });
          }
        }
      },
      (status) => {
        set({ connectionStatus: status });
      }
    );

    return () => {
      clearInterval(pollInterval);
      disconnectWs();
    };
  },

  refreshOverview: async () => {
    try {
      const overview = await cockpitApi.getOverview();
      set({ overview, truth: overview.truth });
    } catch {
      set({ connectionStatus: 'degraded' });
    }
  },

  refreshWorld: async () => {
    try {
      const world = await cockpitApi.getWorld();
      set({ world });
    } catch {
      set({ connectionStatus: 'degraded' });
    }
  },

  play: async (speed) => {
    await cockpitApi.play(speed);
    await get().refreshOverview();
  },

  pause: async () => {
    await cockpitApi.pause();
    await get().refreshOverview();
  },

  step: async (count = 1) => {
    await cockpitApi.step(count);
    await get().refreshWorld();
    await get().refreshOverview();
  },

  reset: async () => {
    await cockpitApi.reset();
    await get().refreshWorld();
    await get().refreshOverview();
  },

  setSpeed: async (speed) => {
    await cockpitApi.setSpeed(speed);
    await get().refreshOverview();
  },

  injectFaults: async (config) => {
    await cockpitApi.injectFaults(config);
    await get().refreshOverview();
  },

  clearFaults: async () => {
    await cockpitApi.clearFaults();
    await get().refreshOverview();
  },

  inspect: (type, id, data) => {
    set({
      inspectorOpen: true,
      inspectorTarget: { type, id, data },
      inspectorTab: 'visual',
    });
  },

  closeInspector: () => {
    set({ inspectorOpen: false, inspectorTarget: null });
  },

  setInspectorTab: (tab) => {
    set({ inspectorTab: tab });
  },

  setCommandPalette: (open) => {
    set({ commandPaletteOpen: open });
  },

  setSystemTruthModal: (open) => {
    set({ systemTruthModalOpen: open });
  },

  setWhyBlockedResult: (result) => {
    set({ whyBlockedResult: result });
  },

  setFaultInjectionOpen: (open) => {
    set({ faultInjectionOpen: open });
  },

  toggleResearchMode: () => {
    set((state) => ({ researchMode: !state.researchMode }));
  },

  setTheme: (theme) => {
    set({ theme });
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  },

  setSearchQuery: (q) => {
    set({ searchQuery: q });
    if (q.trim()) {
      get().executeSearch(q);
    } else {
      set({ searchResults: [] });
    }
  },

  executeSearch: async (q) => {
    if (!q.trim()) return;
    set({ isSearching: true });
    try {
      const results = await cockpitApi.search(q);
      set({ searchResults: results, isSearching: false });
    } catch {
      set({ isSearching: false });
    }
  },
}));

import { create } from 'zustand';

// ─── View Modes ─────────────────────────────────────────────────────────────

export type WorldViewMode = 'map' | 'globe' | 'network' | 'timeline' | 'data';

export type SidebarSection =
  | 'overview'
  | 'world'
  | 'entities'
  | 'investigations'
  | 'simulation'
  | 'ai'
  | 'analytics'
  | 'research'
  | 'admin';

// ─── UI State ───────────────────────────────────────────────────────────────

interface UIState {
  // Sidebar
  sidebarExpanded: boolean;
  activeSection: SidebarSection;

  // Panels
  rightPanelOpen: boolean;
  bottomTimelineOpen: boolean;
  bottomTimelineHeight: number; // px

  // World view
  worldViewMode: WorldViewMode;

  // Command palette
  commandPaletteOpen: boolean;

  // Event filter
  eventTypeFilter: string[];

  // Actions
  toggleSidebar: () => void;
  setActiveSection: (section: SidebarSection) => void;
  setActiveView: (view: SidebarSection) => void;
  toggleRightPanel: () => void;
  setRightPanelOpen: (open: boolean) => void;
  toggleBottomTimeline: () => void;
  setBottomTimelineHeight: (height: number) => void;
  setWorldViewMode: (mode: WorldViewMode) => void;
  toggleCommandPalette: () => void;
  setEventTypeFilter: (types: string[]) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarExpanded: false,
  activeSection: 'world',
  rightPanelOpen: false,
  bottomTimelineOpen: false,
  bottomTimelineHeight: 160,
  worldViewMode: 'map',
  commandPaletteOpen: false,
  eventTypeFilter: [],

  toggleSidebar: () => set((s) => ({ sidebarExpanded: !s.sidebarExpanded })),
  setActiveSection: (section) => set({ activeSection: section }),
  setActiveView: (view) => set({ activeSection: view }),
  toggleRightPanel: () => set((s) => ({ rightPanelOpen: !s.rightPanelOpen })),
  setRightPanelOpen: (open) => set({ rightPanelOpen: open }),
  toggleBottomTimeline: () => set((s) => ({ bottomTimelineOpen: !s.bottomTimelineOpen })),
  setBottomTimelineHeight: (height) =>
    set({ bottomTimelineHeight: Math.max(100, Math.min(400, height)) }),
  setWorldViewMode: (mode) => set({ worldViewMode: mode }),
  toggleCommandPalette: () => set((s) => ({ commandPaletteOpen: !s.commandPaletteOpen })),
  setEventTypeFilter: (types) => set({ eventTypeFilter: types }),
}));

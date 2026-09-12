import { create } from 'zustand';

// ─── Connection State ───────────────────────────────────────────────────────

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'error';

interface ConnectionState {
  wsStatus: ConnectionStatus;
  apiStatus: ConnectionStatus;
  lastPing: number | null;         // ms latency
  messagesReceived: number;
  uptime: number;                  // seconds

  // Actions
  setWsStatus: (status: ConnectionStatus) => void;
  setApiStatus: (status: ConnectionStatus) => void;
  setLastPing: (ping: number) => void;
  incrementMessages: () => void;
  setUptime: (seconds: number) => void;
}

export const useConnectionStore = create<ConnectionState>((set) => ({
  wsStatus: 'disconnected',
  apiStatus: 'disconnected',
  lastPing: null,
  messagesReceived: 0,
  uptime: 0,

  setWsStatus: (status) => set({ wsStatus: status }),
  setApiStatus: (status) => set({ apiStatus: status }),
  setLastPing: (ping) => set({ lastPing: ping }),
  incrementMessages: () => set((s) => ({ messagesReceived: s.messagesReceived + 1 })),
  setUptime: (seconds) => set({ uptime: seconds }),
}));

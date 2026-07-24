import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import type { FC, ReactNode } from 'react';

export interface TelemetryData {
  episode: number;
  successRate: number;
  mutationRate: number;
  avgReward: number;
  noveltyScore: number;
  redSurvivalRate: number;
  generation: number;
  timestamp: number;
}

export interface AgentState {
  id: string;
  type: 'drone' | 'fighter' | 'tank' | 'vessel' | 'missile' | 'infantry';
  domain: 'air' | 'land' | 'sea' | 'space' | 'cyber';
  position: [number, number];
  health: number;
  fuel: number;
  status: 'active' | 'engaged' | 'damaged' | 'destroyed';
  threatLevel: number;
  currentAction: string;
  confidence: number;
  beliefs: string[];
  goals: string[];
  intentions: string[];
  decisionHistory: string[];
  commander: string;
}

export interface WorldState {
  agents: AgentState[];
  threats: Array<{ id: string; position: [number, number]; type: string; confidence: number }>;
  supplyNodes: Array<{ id: string; position: [number, number]; alive: boolean }>;
  timestamp: number;
  phase: string;
}

interface SimulationState {
  isRunning: boolean;
  currentEpisode: number;
  totalEpisodes: number;
  telemetry: TelemetryData[];
  worldState: WorldState | null;
  selectedAgent: AgentState | null;
  speed: number;
}

interface SimulationContextType extends SimulationState {
  startSimulation: () => void;
  pauseSimulation: () => void;
  stopSimulation: () => void;
  setSpeed: (speed: number) => void;
  selectAgent: (agent: AgentState | null) => void;
  updateTelemetry: (data: TelemetryData) => void;
  updateWorldState: (state: WorldState) => void;
}

const initialState: SimulationState = {
  isRunning: false,
  currentEpisode: 0,
  totalEpisodes: 1000,
  telemetry: [],
  worldState: null,
  selectedAgent: null,
  speed: 1,
};

const SimulationContext = createContext<SimulationContextType>({
  ...initialState,
  startSimulation: () => {},
  pauseSimulation: () => {},
  stopSimulation: () => {},
  setSpeed: () => {},
  selectAgent: () => {},
  updateTelemetry: () => {},
  updateWorldState: () => {},
});

export const SimulationProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const [state, setState] = useState<SimulationState>(initialState);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Connect to backend WebSocket for live data
    try {
      const ws = new WebSocket('ws://localhost:8000/ws');
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'telemetry') {
            updateTelemetry(data.payload);
          } else if (data.type === 'world_state') {
            updateWorldState(data.payload);
          }
        } catch {}
      };
      wsRef.current = ws;
    } catch {}

    return () => {
      wsRef.current?.close();
    };
  }, []);

  const startSimulation = useCallback(() => {
    setState(prev => ({ ...prev, isRunning: true }));
  }, []);

  const pauseSimulation = useCallback(() => {
    setState(prev => ({ ...prev, isRunning: false }));
  }, []);

  const stopSimulation = useCallback(() => {
    setState(prev => ({ ...prev, isRunning: false, currentEpisode: 0, telemetry: [] }));
  }, []);

  const setSpeed = useCallback((speed: number) => {
    setState(prev => ({ ...prev, speed }));
  }, []);

  const selectAgent = useCallback((agent: AgentState | null) => {
    setState(prev => ({ ...prev, selectedAgent: agent }));
  }, []);

  const updateTelemetry = useCallback((data: TelemetryData) => {
    setState(prev => ({
      ...prev,
      currentEpisode: data.episode,
      telemetry: [...prev.telemetry.slice(-200), data],
    }));
  }, []);

  const updateWorldState = useCallback((worldState: WorldState) => {
    setState(prev => ({ ...prev, worldState }));
  }, []);

  return (
    <SimulationContext.Provider value={{
      ...state,
      startSimulation,
      pauseSimulation,
      stopSimulation,
      setSpeed,
      selectAgent,
      updateTelemetry,
      updateWorldState,
    }}>
      {children}
    </SimulationContext.Provider>
  );
};

export const useSimulation = () => useContext(SimulationContext);

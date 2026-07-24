import { createContext, useContext, useState, useCallback } from 'react';
import type { FC, ReactNode } from 'react';

export interface DashboardWidget {
  id: string;
  type: 'map' | 'chart' | 'metrics' | 'timeline' | 'agent_inspector' | 'knowledge_graph' 
      | 'experiment_monitor' | 'event_stream' | 'performance_monitor' | 'resource_monitor'
      | 'memory_explorer' | 'command_palette' | 'ai_reasoning';
  title: string;
  position: { x: number; y: number };
  size: { width: number; height: number };
  visible: boolean;
}

interface DashboardState {
  layout: 'grid' | 'freeform';
  widgets: DashboardWidget[];
  selectedWidget: string | null;
  isLocked: boolean;
}

interface DashboardContextType extends DashboardState {
  setLayout: (layout: 'grid' | 'freeform') => void;
  addWidget: (widget: DashboardWidget) => void;
  removeWidget: (id: string) => void;
  updateWidget: (id: string, updates: Partial<DashboardWidget>) => void;
  selectWidget: (id: string | null) => void;
  toggleLock: () => void;
  resetLayout: () => void;
}

const defaultWidgets: DashboardWidget[] = [
  { id: 'map', type: 'map', title: 'Tactical Map', position: { x: 0, y: 0 }, size: { width: 3, height: 2 }, visible: true },
  { id: 'metrics', type: 'metrics', title: 'Live KPIs', position: { x: 3, y: 0 }, size: { width: 1, height: 1 }, visible: true },
  { id: 'timeline', type: 'timeline', title: 'Decision Timeline', position: { x: 3, y: 1 }, size: { width: 1, height: 1 }, visible: true },
  { id: 'agent_inspector', type: 'agent_inspector', title: 'Agent Inspector', position: { x: 4, y: 0 }, size: { width: 1, height: 2 }, visible: true },
  { id: 'knowledge_graph', type: 'knowledge_graph', title: 'Knowledge Graph', position: { x: 0, y: 2 }, size: { width: 2, height: 1 }, visible: true },
  { id: 'event_stream', type: 'event_stream', title: 'Event Stream', position: { x: 2, y: 2 }, size: { width: 1, height: 1 }, visible: true },
  { id: 'ai_reasoning', type: 'ai_reasoning', title: 'AI Reasoning', position: { x: 3, y: 2 }, size: { width: 1, height: 1 }, visible: true },
  { id: 'experiment', type: 'experiment_monitor', title: 'Experiment Monitor', position: { x: 4, y: 2 }, size: { width: 1, height: 1 }, visible: false },
];

const DashboardContext = createContext<DashboardContextType>({
  layout: 'grid',
  widgets: defaultWidgets,
  selectedWidget: null,
  isLocked: false,
  setLayout: () => {},
  addWidget: () => {},
  removeWidget: () => {},
  updateWidget: () => {},
  selectWidget: () => {},
  toggleLock: () => {},
  resetLayout: () => {},
});

export const DashboardProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const [layout, setLayoutState] = useState<'grid' | 'freeform'>('grid');
  const [widgets, setWidgets] = useState<DashboardWidget[]>(defaultWidgets);
  const [selectedWidget, setSelectedWidget] = useState<string | null>(null);
  const [isLocked, setIsLocked] = useState(false);

  const setLayout = useCallback((l: 'grid' | 'freeform') => setLayoutState(l), []);
  const selectWidget = useCallback((id: string | null) => setSelectedWidget(id), []);
  const toggleLock = useCallback(() => setIsLocked(prev => !prev), []);

  const addWidget = useCallback((widget: DashboardWidget) => {
    setWidgets(prev => [...prev, widget]);
  }, []);

  const removeWidget = useCallback((id: string) => {
    setWidgets(prev => prev.filter(w => w.id !== id));
  }, []);

  const updateWidget = useCallback((id: string, updates: Partial<DashboardWidget>) => {
    setWidgets(prev => prev.map(w => w.id === id ? { ...w, ...updates } : w));
  }, []);

  const resetLayout = useCallback(() => {
    setWidgets(defaultWidgets);
    setLayout('grid');
  }, []);

  return (
    <DashboardContext.Provider value={{
      layout, widgets, selectedWidget, isLocked,
      setLayout, addWidget, removeWidget, updateWidget,
      selectWidget, toggleLock, resetLayout,
    }}>
      {children}
    </DashboardContext.Provider>
  );
};

export const useDashboard = () => useContext(DashboardContext);

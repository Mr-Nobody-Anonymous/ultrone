// Copyright (c) Ultrone Contributors. All rights reserved.
import type { FC } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { CockpitShell } from './layouts/CockpitShell';
import { OverviewView } from './features/overview/OverviewView';
import { SimulationWorldView } from './features/simulation/SimulationWorldView';
import { DualWorldCompareView } from './features/simulation/DualWorldCompareView';
import { AgentsView } from './features/agents/AgentsView';
import { CognitiveTraceView } from './features/trace/CognitiveTraceView';
import { DevicesView } from './features/devices/DevicesView';
import { McpInspectorView } from './features/mcp/McpInspectorView';
import { EventStoreView } from './features/events/EventStoreView';
import { SafetyCenterView } from './features/safety/SafetyCenterView';
import { SystemHealthView } from './features/system/SystemHealthView';
import { AlertsCenterView } from './features/system/AlertsCenterView';
import { AuditTrailView } from './features/system/AuditTrailView';
import { EvaluationLabView } from './features/evaluation/EvaluationLabView';
import { GovernanceView } from './features/governance/GovernanceView';
import { RegistriesView } from './features/registries/RegistriesView';
import { ScenariosPage } from './pages/ScenariosPage';
import { DesignSystemPage } from './pages/DesignSystemPage';

const App: FC = () => {
  return (
    <Routes>
      <Route path="/" element={<CockpitShell />}>
        <Route index element={<OverviewView />} />
        <Route path="simulation" element={<SimulationWorldView />} />
        <Route path="simulation/compare" element={<DualWorldCompareView />} />
        <Route path="scenarios" element={<ScenariosPage />} />
        <Route path="agents" element={<AgentsView />} />
        <Route path="agents/:agentId" element={<AgentsView />} />
        <Route path="traces" element={<CognitiveTraceView />} />
        <Route path="devices" element={<DevicesView />} />
        <Route path="mcp" element={<McpInspectorView />} />
        <Route path="events" element={<EventStoreView />} />
        <Route path="safety" element={<SafetyCenterView />} />
        <Route path="system/health" element={<SystemHealthView />} />
        <Route path="system/alerts" element={<AlertsCenterView />} />
        <Route path="system/audit" element={<AuditTrailView />} />
        <Route path="evaluation" element={<EvaluationLabView />} />
        <Route path="governance" element={<GovernanceView />} />
        <Route path="registries" element={<RegistriesView />} />
        <Route path="design-system" element={<DesignSystemPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
};

export default App;

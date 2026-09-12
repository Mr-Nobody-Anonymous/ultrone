import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ConsoleLayout from './layouts/ConsoleLayout';
import OverviewView from './views/OverviewView';
import WorldView from './views/WorldView';
import EntityInspector from './views/EntityInspector';
import EventTimeline from './views/EventTimeline';
import OntologyGraph from './views/OntologyGraph';
import AIAssist from './views/AIAssist';
import SimulationView from './views/SimulationView';
import AnalyticsView from './views/AnalyticsView';
import InvestigationsView from './views/InvestigationsView';
import ResearchView from './views/ResearchView';
import AdminView from './views/AdminView';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<ConsoleLayout />}>
          <Route index element={<OverviewView />} />
          <Route path="world" element={<WorldView />} />
          <Route path="entities" element={<EntityInspector />} />
          <Route path="investigations" element={<InvestigationsView />} />
          <Route path="events" element={<EventTimeline />} />
          <Route path="ontology" element={<OntologyGraph />} />
          <Route path="ai" element={<AIAssist />} />
          <Route path="assist" element={<AIAssist />} />
          <Route path="simulation" element={<SimulationView />} />
          <Route path="analytics" element={<AnalyticsView />} />
          <Route path="research" element={<ResearchView />} />
          <Route path="admin" element={<AdminView />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

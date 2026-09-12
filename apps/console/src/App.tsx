import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ConsoleLayout from './layouts/ConsoleLayout';
import WorldView from './views/WorldView';
import EntityInspector from './views/EntityInspector';
import EventTimeline from './views/EventTimeline';
import OntologyGraph from './views/OntologyGraph';
import AIAssist from './views/AIAssist';
import SimulationView from './views/SimulationView';
import AnalyticsView from './views/AnalyticsView';
import AdminView from './views/AdminView';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<ConsoleLayout />}>
          <Route index element={<WorldView />} />
          <Route path="entities" element={<EntityInspector />} />
          <Route path="events" element={<EventTimeline />} />
          <Route path="ontology" element={<OntologyGraph />} />
          <Route path="assist" element={<AIAssist />} />
          <Route path="simulation" element={<SimulationView />} />
          <Route path="analytics" element={<AnalyticsView />} />
          <Route path="admin" element={<AdminView />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

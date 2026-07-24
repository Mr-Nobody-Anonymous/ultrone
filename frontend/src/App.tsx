import type { FC } from 'react';
import { Routes, Route } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import MainLayout from './layouts/MainLayout';
import DashboardPage from './pages/DashboardPage';
import ExperimentPage from './pages/ExperimentPage';
import AgentInspectorPage from './pages/AgentInspectorPage';
import AnalyticsPage from './pages/AnalyticsPage';
import SettingsPage from './pages/SettingsPage';

const App: FC = () => {
  return (
    <AnimatePresence mode="wait">
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="experiments" element={<ExperimentPage />} />
          <Route path="agents/:agentId" element={<AgentInspectorPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </AnimatePresence>
  );
};

export default App;

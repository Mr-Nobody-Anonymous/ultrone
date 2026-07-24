import type { FC } from 'react';
import { motion } from 'framer-motion';
import LiveMetrics from '../components/LiveMetrics';
import TacticalMapView from '../components/TacticalMapView';
import DecisionTimeline from '../components/DecisionTimeline';
import AgentInspector from '../components/AgentInspector';
import KnowledgeGraph from '../components/KnowledgeGraph';
import EventStream from '../components/EventStream';
import AIReasoningPanel from '../components/AIReasoningPanel';
import PerformanceMonitor from '../components/PerformanceMonitor';
import { useDashboard } from '../contexts/DashboardContext';

const widgetComponents: Record<string, FC<{ widget: any }>> = {
  map: TacticalMapView,
  metrics: LiveMetrics,
  timeline: DecisionTimeline,
  agent_inspector: AgentInspector,
  knowledge_graph: KnowledgeGraph,
  event_stream: EventStream,
  ai_reasoning: AIReasoningPanel,
  performance_monitor: PerformanceMonitor,
};

const DashboardPage: FC = () => {
  const { widgets } = useDashboard();
  const visibleWidgets = widgets.filter(w => w.visible);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="h-full"
    >
      <div className="grid grid-cols-5 auto-rows-fr gap-3 h-full">
        {visibleWidgets.map((widget, i) => {
          const WidgetComponent = widgetComponents[widget.type];
          return WidgetComponent ? (
            <motion.div
              key={widget.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="glass-panel overflow-hidden"
              style={{
                gridColumn: `span ${widget.size.width}`,
                gridRow: `span ${widget.size.height}`,
              }}
            >
              <WidgetComponent widget={widget} />
            </motion.div>
          ) : null;
        })}
      </div>
    </motion.div>
  );
};

export default DashboardPage;

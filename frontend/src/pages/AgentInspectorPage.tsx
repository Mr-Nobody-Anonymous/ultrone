import type { FC } from 'react';
import { useParams } from 'react-router-dom';
import { motion } from 'framer-motion';

const AgentInspectorPage: FC = () => {
  const { agentId } = useParams();

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      <div>
        <h1 className="text-2xl font-bold text-surface-100">Agent Inspector</h1>
        <p className="text-sm text-surface-400 mt-1">Agent ID: {agentId}</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="glass-panel p-4 space-y-3">
          <h3 className="text-sm font-semibold text-surface-300 uppercase tracking-wider">Internal State</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-surface-400">Health</span><span className="text-green-400">92%</span></div>
            <div className="flex justify-between"><span className="text-surface-400">Fuel</span><span className="text-amber-400">67%</span></div>
            <div className="flex justify-between"><span className="text-surface-400">Ammo</span><span className="text-blue-400">45/60</span></div>
            <div className="flex justify-between"><span className="text-surface-400">Position</span><span className="font-mono text-xs">(23, 47)</span></div>
          </div>
        </div>
        <div className="glass-panel p-4 space-y-3">
          <h3 className="text-sm font-semibold text-surface-300 uppercase tracking-wider">Beliefs</h3>
          <div className="space-y-1">
            {['Enemy detected at (45, 30)', 'Supply node active', 'Weather clear'].map((b, i) => (
              <div key={i} className="text-xs text-surface-400 bg-surface-800/50 rounded px-2 py-1">{b}</div>
            ))}
          </div>
        </div>
        <div className="glass-panel p-4 space-y-3">
          <h3 className="text-sm font-semibold text-surface-300 uppercase tracking-wider">Intentions</h3>
          <div className="space-y-1">
            {['Move to objective Alpha', 'Engage hostile targets', 'Return to supply node'].map((b, i) => (
              <div key={i} className="text-xs text-surface-400 bg-surface-800/50 rounded px-2 py-1">{b}</div>
            ))}
          </div>
        </div>
      </div>

      <div className="glass-panel p-4 h-80 flex items-center justify-center text-surface-500">
        <p>Decision History Timeline</p>
      </div>
    </motion.div>
  );
};

export default AgentInspectorPage;

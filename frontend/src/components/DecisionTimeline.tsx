import type { FC } from 'react';
import { motion } from 'framer-motion';
import { Clock, Zap, Target, Shield, Move, Radio } from 'lucide-react';
import { useSimulation } from '../contexts/SimulationContext';

const actionIcons: Record<string, ReactNode> = {
  strike: <Target size={12} className="text-red-400" />,
  jam: <Radio size={12} className="text-purple-400" />,
  move: <Move size={12} className="text-blue-400" />,
  engage: <Zap size={12} className="text-amber-400" />,
  defend: <Shield size={12} className="text-green-400" />,
};

const DecisionTimeline: FC<{ widget: any }> = () => {
  const { telemetry, isRunning } = useSimulation();

  const decisions = [
    { time: '12:00:01', action: 'strike', description: 'Engaged hostile target Alpha', confidence: 0.92 },
    { time: '12:00:02', action: 'jam', description: 'ECM countermeasure deployed', confidence: 0.85 },
    { time: '12:00:03', action: 'move', description: 'Repositioning to flank', confidence: 0.78 },
    { time: '12:00:04', action: 'engage', description: 'Follow-up strike on target', confidence: 0.95 },
  ];

  return (
    <div className="p-3 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Clock size={14} className="text-primary-400" />
          <span className="text-xs font-semibold text-surface-300">Decision Timeline</span>
        </div>
        {isRunning && <span className="badge-green text-[10px]">Live</span>}
      </div>
      <div className="flex-1 overflow-y-auto space-y-2">
        {decisions.map((d, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
            className="flex items-start gap-3 p-2 rounded-lg bg-surface-800/30 hover:bg-surface-800/50 transition-all cursor-pointer"
          >
            <div className="flex-shrink-0 w-6 h-6 rounded-full bg-surface-700/50 flex items-center justify-center">
              {actionIcons[d.action] || <Zap size={12} />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-surface-200 capitalize">{d.action}</span>
                <span className="text-[10px] text-surface-500 font-mono">{d.time}</span>
              </div>
              <p className="text-[11px] text-surface-400 truncate">{d.description}</p>
            </div>
            <div className="flex-shrink-0 text-[10px] font-mono text-surface-500">
              {(d.confidence * 100).toFixed(0)}%
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default DecisionTimeline;

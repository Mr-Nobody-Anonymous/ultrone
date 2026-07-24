import type { FC } from 'react';
import { motion } from 'framer-motion';
import { Brain, Lightbulb, TrendingUp, Target, Shield, Zap, AlertTriangle } from 'lucide-react';
import { useSimulation } from '../contexts/SimulationContext';

const reasoningSteps = [
  { phase: 'OBSERVE', content: 'Detected 3 hostile contacts bearing 045°, range 25km', confidence: 0.95, time: '12:00:00' },
  { phase: 'ORIENT', content: 'Pattern match: Ambush formation (87% confidence) → Mutating kill chain', confidence: 0.87, time: '12:00:01' },
  { phase: 'DECIDE', content: 'Optimal COA: JAM + STRIKE (Cyber-Kinetic Sync, novelty 0.81)', confidence: 0.92, time: '12:00:02' },
  { phase: 'ACT', content: 'Executing: DRONE-01 strike, DRONE-02 jam, total cost 2.3', confidence: 0.94, time: '12:00:03' },
  { phase: 'ASSESS', content: 'Target destroyed. Reward +145. Updating genome weights.', confidence: 0.96, time: '12:00:04' },
];

const phaseColors: Record<string, string> = {
  OBSERVE: 'text-blue-400 border-blue-500/30 bg-blue-500/10',
  ORIENT: 'text-purple-400 border-purple-500/30 bg-purple-500/10',
  DECIDE: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
  ACT: 'text-green-400 border-green-500/30 bg-green-500/10',
  ASSESS: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10',
};

const AIReasoningPanel: FC<{ widget: any }> = () => {
  const { isRunning } = useSimulation();

  return (
    <div className="p-3 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Brain size={14} className="text-primary-400" />
          <span className="text-xs font-semibold text-surface-300">AI Reasoning (OODA)</span>
        </div>
        {isRunning && (
          <span className="flex items-center gap-1 text-[10px] text-green-400">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
            Active
          </span>
        )}
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto">
        {reasoningSteps.map((step, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className={`rounded-lg border p-3 ${phaseColors[step.phase] || 'border-surface-700/30 bg-surface-800/30'}`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-bold uppercase tracking-wider">{step.phase}</span>
              <span className="text-[9px] font-mono opacity-60">{step.time}</span>
            </div>
            <p className="text-xs leading-relaxed">{step.content}</p>
            <div className="flex items-center gap-2 mt-1.5">
              <span className="text-[9px] opacity-60">Confidence</span>
              <div className="flex-1 h-1 bg-black/20 rounded-full overflow-hidden max-w-[80px]">
                <div
                  className="h-full bg-current rounded-full"
                  style={{ width: `${step.confidence * 100}%` }}
                />
              </div>
              <span className="text-[9px] font-mono opacity-60">{(step.confidence * 100).toFixed(0)}%</span>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default AIReasoningPanel;


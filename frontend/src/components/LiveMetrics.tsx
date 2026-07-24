import type { FC } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, Target, Shield, Activity, Zap, Crosshair } from 'lucide-react';
import { useSimulation } from '../contexts/SimulationContext';

const LiveMetrics: FC<{ widget: any }> = () => {
  const { telemetry, isRunning } = useSimulation();
  const latest = telemetry[telemetry.length - 1];

  const metrics = [
    { label: 'Success Rate', value: latest?.successRate ? `${latest.successRate.toFixed(1)}%` : '0%', icon: Target, color: 'text-green-400', change: '+5.2%' },
    { label: 'Avg Reward', value: latest?.avgReward ? latest.avgReward.toFixed(1) : '0', icon: TrendingUp, color: 'text-blue-400', change: '+12.1%' },
    { label: 'Mutation Rate', value: latest?.mutationRate ? `${(latest.mutationRate * 100).toFixed(1)}%` : '0%', icon: Zap, color: 'text-purple-400', change: '+0.02' },
    { label: 'Red Survival', value: latest?.redSurvivalRate ? `${(latest.redSurvivalRate * 100).toFixed(1)}%` : '0%', icon: Shield, color: 'text-red-400', change: '-3.4%' },
  ];

  return (
    <div className="p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-surface-400 uppercase tracking-wider">Live KPIs</h3>
        <div className={`flex items-center gap-1.5 ${isRunning ? 'text-green-400' : 'text-surface-500'}`}>
          <span className="status-dot-active" />
          <span className="text-xs">{isRunning ? 'Live' : 'Paused'}</span>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 flex-1">
        {metrics.map((m, i) => (
          <motion.div
            key={m.label}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.1 }}
            className="glass-card p-3 flex flex-col justify-between"
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-surface-500 uppercase tracking-wider">{m.label}</span>
              <m.span
                key={latest?.episode}
                initial={{ scale: 1.3 }}
                animate={{ scale: 1 }}
              >
                <m.icon size={14} className={m.color} />
              </m.span>
            </div>
            <motion.span
              key={`${m.label}-${latest?.episode}`}
              initial={{ y: -5, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              className={`text-lg font-bold ${m.color}`}
            >
              {m.value}
            </motion.span>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default LiveMetrics;

import type { FC, ReactNode } from 'react';
import { motion } from 'framer-motion';
import { Radio, Target, Shield, Zap, AlertTriangle, Info } from 'lucide-react';
import { useSimulation } from '../contexts/SimulationContext';

const eventIcons: Record<string, ReactNode> = {
  detection: <Radio size={12} className="text-blue-400" />,
  engagement: <Target size={12} className="text-red-400" />,
  defense: <Shield size={12} className="text-green-400" />,
  evolution: <Zap size={12} className="text-purple-400" />,
  alert: <AlertTriangle size={12} className="text-amber-400" />,
  info: <Info size={12} className="text-surface-400" />,
};

const events = [
  { type: 'detection', message: 'Sensor fusion: enemy armor detected at grid 47-23', time: '12:00:05' },
  { type: 'evolution', message: 'Genome mutation: strike weight adjusted +0.15', time: '12:00:04' },
  { type: 'engagement', message: 'DRONE-01 engaging TARGET-X with 92% confidence', time: '12:00:03' },
  { type: 'defense', message: 'ECM countermeasure activated against radar lock', time: '12:00:02' },
  { type: 'alert', message: 'Fuel low warning on DRONE-03: 23% remaining', time: '12:00:01' },
  { type: 'info', message: 'Supply node ALPHA resupplied 3 units', time: '12:00:00' },
];

const EventStream: FC<{ widget: any }> = () => {
  return (
    <div className="p-3 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Radio size={14} className="text-primary-400" />
          <span className="text-xs font-semibold text-surface-300">Event Stream</span>
        </div>
        <span className="badge-blue text-[10px]">Live</span>
      </div>
      <div className="flex-1 overflow-y-auto space-y-1.5">
        {events.map((evt, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className="flex items-start gap-2 p-2 rounded-lg bg-surface-800/20 hover:bg-surface-800/40 transition-all"
          >
            <div className="flex-shrink-0 mt-0.5">{eventIcons[evt.type]}</div>
            <div className="flex-1 min-w-0">
              <p className="text-[11px] text-surface-300 leading-tight">{evt.message}</p>
            </div>
            <span className="flex-shrink-0 text-[9px] text-surface-600 font-mono">{evt.time}</span>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default EventStream;

import type { FC } from 'react';
import { motion } from 'framer-motion';
import { Activity, Cpu, HardDrive, Globe } from 'lucide-react';

const PerformanceMonitor: FC<{ widget: any }> = () => {
  const metrics = [
    { label: 'CPU Usage', value: '34%', icon: Cpu, color: 'text-green-400', bar: 34 },
    { label: 'Memory', value: '2.4/8 GB', icon: HardDrive, color: 'text-blue-400', bar: 30 },
    { label: 'Network', value: '1.2 Mbps', icon: Globe, color: 'text-purple-400', bar: 15 },
    { label: 'FPS', value: '144', icon: Activity, color: 'text-amber-400', bar: 100 },
  ];

  return (
    <div className="p-3 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-3">
        <Activity size={14} className="text-primary-400" />
        <span className="text-xs font-semibold text-surface-300">Performance</span>
      </div>
      <div className="flex-1 space-y-3">
        {metrics.map((m, i) => (
          <motion.div
            key={m.label}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: i * 0.1 }}
          >
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <m.icon size={12} className={m.color} />
                <span className="text-[10px] text-surface-400">{m.label}</span>
              </div>
              <span className={`text-xs font-semibold ${m.color}`}>{m.value}</span>
            </div>
            <div className="h-1.5 bg-surface-700/50 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${m.bar}%` }}
                transition={{ duration: 0.8, delay: i * 0.1 }}
                className={`h-full rounded-full ${m.color.replace('text-', 'bg-')}`}
              />
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default PerformanceMonitor;


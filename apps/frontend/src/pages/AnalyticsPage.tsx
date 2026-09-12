import type { FC } from 'react';
import { motion } from 'framer-motion';
import { BarChart3, PieChart, Activity, TrendingUp, Target, Shield } from 'lucide-react';

const AnalyticsPage: FC = () => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      <div>
        <h1 className="text-2xl font-bold text-surface-100">Analytics</h1>
        <p className="text-sm text-surface-400 mt-1">Comprehensive performance analysis</p>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Avg Success Rate', value: '87.3%', icon: Target, change: '+5.2%', up: true, color: 'text-green-400' },
          { label: 'Avg Reward', value: '312.4', icon: TrendingUp, change: '+12.1%', up: true, color: 'text-blue-400' },
          { label: 'Red Survival', value: '23.7%', icon: Shield, change: '-3.4%', up: false, color: 'text-red-400' },
          { label: 'Genome Diversity', value: '0.74', icon: Activity, change: '+0.08', up: true, color: 'text-purple-400' },
        ].map((metric, i) => (
          <motion.div
            key={metric.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="glass-panel p-4"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="metric-label">{metric.label}</span>
              <metric.icon size={16} className={metric.color} />
            </div>
            <div className="metric-value">{metric.value}</div>
            <span className={metric.up ? 'metric-change-up' : 'metric-change-down'}>
              {metric.change}
            </span>
          </motion.div>
        ))}
      </div>

      {/* Chart grid */}
      <div className="grid grid-cols-2 gap-4">
        <div className="glass-panel p-4 h-72 flex items-center justify-center text-surface-500">
          <div className="text-center">
            <Activity size={48} className="mx-auto mb-2 opacity-50" />
            <p className="text-sm">Performance Over Time</p>
          </div>
        </div>
        <div className="glass-panel p-4 h-72 flex items-center justify-center text-surface-500">
          <div className="text-center">
            <PieChart size={48} className="mx-auto mb-2 opacity-50" />
            <p className="text-sm">Action Distribution</p>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default AnalyticsPage;

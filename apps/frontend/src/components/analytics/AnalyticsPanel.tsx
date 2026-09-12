import type { FC } from 'react';
import { BarChart3, TrendingUp, PieChart, Activity } from 'lucide-react';

const metrics = [
  { label: 'Avg Success Rate', value: '74.2%', trend: '+5.3%', positive: true },
  { label: 'Genome Diversity', value: '0.82', trend: '+0.12', positive: true },
  { label: 'Convergence Speed', value: '23.4', trend: '-2.1', positive: true },
  { label: 'Red Survival', value: '31.8%', trend: '+8.2%', positive: false },
];

const AnalyticsPanel: FC = () => {
  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-surface-700/30">
        <BarChart3 size={16} className="text-primary-400" />
        <span className="text-sm font-semibold text-surface-200">Analytics</span>
      </div>
      <div className="flex-1 p-4 overflow-auto space-y-4">
        <div className="grid grid-cols-2 gap-2">
          {metrics.map(m => (
            <div key={m.label} className="p-3 rounded-lg bg-surface-800/50">
              <div className="text-[10px] text-surface-500 mb-1">{m.label}</div>
              <div className="text-lg font-bold text-surface-200">{m.value}</div>
              <div className={`text-[10px] ${m.positive ? 'text-green-400' : 'text-red-400'}`}>
                {m.trend}
              </div>
            </div>
          ))}
        </div>
        <div className="p-3 rounded-lg bg-surface-800/50">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp size={14} className="text-primary-400" />
            <span className="text-xs font-medium text-surface-300">Performance Trends</span>
          </div>
          <div className="h-32 flex items-end gap-1">
            {[0.3, 0.5, 0.4, 0.7, 0.6, 0.8, 0.75, 0.85, 0.82, 0.9].map((v, i) => (
              <div key={i} className="flex-1 bg-primary-500/30 rounded-t" style={{ height: `${v * 100}%` }} />
            ))}
          </div>
        </div>
        <div className="p-3 rounded-lg bg-surface-800/50">
          <div className="flex items-center gap-2 mb-3">
            <PieChart size={14} className="text-primary-400" />
            <span className="text-xs font-medium text-surface-300">Action Distribution</span>
          </div>
          <div className="space-y-2">
            {[
              { label: 'Strike', value: 35, color: 'bg-red-500' },
              { label: 'Jam', value: 25, color: 'bg-yellow-500' },
              { label: 'Recon', value: 20, color: 'bg-blue-500' },
              { label: 'Hack', value: 20, color: 'bg-purple-500' },
            ].map(a => (
              <div key={a.label} className="flex items-center gap-2">
                <div className="text-[10px] text-surface-400 w-12">{a.label}</div>
                <div className="flex-1 h-2 rounded-full bg-surface-700">
                  <div className={`h-full rounded-full ${a.color}`} style={{ width: `${a.value}%` }} />
                </div>
                <div className="text-[10px] text-surface-400 w-8 text-right">{a.value}%</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsPanel;

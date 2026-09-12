import type { FC } from 'react';
import { motion } from 'framer-motion';
import { Play, BarChart3, LineChart, GitBranch, Users, TrendingUp } from 'lucide-react';

const ExperimentPage: FC = () => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-100">Experiment Manager</h1>
          <p className="text-sm text-surface-400 mt-1">Monitor and compare training experiments</p>
        </div>
        <button className="btn-primary gap-2">
          <Play size={16} />
          New Experiment
        </button>
      </div>

      {/* Experiment cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { name: 'PPO Baseline', status: 'Running', reward: 245.3, episodes: 1200, color: 'blue' },
          { name: 'SAC + Curriculum', status: 'Completed', reward: 389.1, episodes: 5000, color: 'purple' },
          { name: 'MARL Cooperative', status: 'Running', reward: 312.7, episodes: 3400, color: 'green' },
        ].map((exp, i) => (
          <motion.div
            key={exp.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="glass-panel p-5 space-y-4 hover:border-primary-500/30 transition-all cursor-pointer group"
          >
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold text-surface-100">{exp.name}</h3>
                <span className={`badge ${
                  exp.status === 'Running' ? 'badge-green' : 'badge-blue'
                } mt-1`}>{exp.status}</span>
              </div>
              <div className="w-10 h-10 rounded-lg bg-primary-500/10 flex items-center justify-center group-hover:bg-primary-500/20 transition-all">
                <BarChart3 size={20} className="text-primary-400" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="metric-label">Avg Reward</div>
                <div className="text-lg font-bold text-surface-100">{exp.reward.toFixed(1)}</div>
              </div>
              <div>
                <div className="metric-label">Episodes</div>
                <div className="text-lg font-bold text-surface-100">{exp.episodes.toLocaleString()}</div>
              </div>
            </div>
            {/* Mini progress bar */}
            <div className="h-1.5 bg-surface-700/50 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full transition-all"
                   style={{ width: `${(exp.episodes / 5000) * 100}%` }} />
            </div>
          </motion.div>
        ))}
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-2 gap-4">
        <div className="glass-panel p-4 h-80 flex items-center justify-center text-surface-500">
          <div className="text-center">
            <LineChart size={48} className="mx-auto mb-2 opacity-50" />
            <p className="text-sm">Reward Curves</p>
          </div>
        </div>
        <div className="glass-panel p-4 h-80 flex items-center justify-center text-surface-500">
          <div className="text-center">
            <GitBranch size={48} className="mx-auto mb-2 opacity-50" />
            <p className="text-sm">Population Evolution</p>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default ExperimentPage;

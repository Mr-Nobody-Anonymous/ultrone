import type { FC } from 'react';
import { motion } from 'framer-motion';

const SettingsPage: FC = () => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="max-w-3xl space-y-6"
    >
      <div>
        <h1 className="text-2xl font-bold text-surface-100">Settings</h1>
        <p className="text-sm text-surface-400 mt-1">Configure ULTRONE platform</p>
      </div>

      <div className="space-y-4">
        {[
          { title: 'Simulation', fields: ['Max Episodes', 'Population Size', 'Mutation Rate', 'Crossover Rate'] },
          { title: 'Reinforcement Learning', fields: ['Learning Rate', 'Batch Size', 'Gamma', 'Tau'] },
          { title: 'Visualization', fields: ['Theme', 'Update Interval', 'Chart Refresh Rate', 'Map Style'] },
        ].map(section => (
          <div key={section.title} className="glass-panel p-5 space-y-4">
            <h3 className="text-sm font-semibold text-surface-300 uppercase tracking-wider">{section.title}</h3>
            <div className="grid grid-cols-2 gap-4">
              {section.fields.map(field => (
                <div key={field}>
                  <label className="block text-xs text-surface-400 mb-1">{field}</label>
                  <input className="input-field" placeholder={`Enter ${field.toLowerCase()}`} />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  );
};

export default SettingsPage;

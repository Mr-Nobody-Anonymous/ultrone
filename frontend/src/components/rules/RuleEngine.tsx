import type { FC } from 'react';
import { useState } from 'react';
import { Shield, Plus, ToggleLeft, ToggleRight, Edit3, Trash2 } from 'lucide-react';

interface Rule {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  priority: number;
  category: 'roe' | 'engagement' | 'allocation' | 'evolution';
}

const mockRules: Rule[] = [
  { id: '1', name: 'No Blue-on-Blue', description: 'Prevent friendly fire incidents', enabled: true, priority: 1, category: 'roe' },
  { id: '2', name: 'Collateral Avoidance', description: 'Minimize civilian casualties', enabled: true, priority: 2, category: 'roe' },
  { id: '3', name: 'Resource Threshold', description: 'Maintain 30% reserve', enabled: true, priority: 3, category: 'allocation' },
  { id: '4', name: 'Mutate on Failure', description: 'Trigger evolution on 3 consecutive failures', enabled: false, priority: 4, category: 'evolution' },
  { id: '5', name: 'Standoff Engagement', description: 'Engage from max weapon range', enabled: true, priority: 5, category: 'engagement' },
];

const RuleEngine: FC = () => {
  const [rules, setRules] = useState<Rule[]>(mockRules);
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  const toggleRule = (id: string) => {
    setRules(prev => prev.map(r => r.id === id ? { ...r, enabled: !r.enabled } : r));
  };

  const filtered = categoryFilter === 'all' ? rules : rules.filter(r => r.category === categoryFilter);

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-700/30">
        <div className="flex items-center gap-2">
          <Shield size={16} className="text-primary-400" />
          <span className="text-sm font-semibold text-surface-200">Rule Engine</span>
        </div>
        <button className="flex items-center gap-1 text-xs px-2 py-1 rounded bg-primary-500/20 text-primary-300 hover:bg-primary-500/30">
          <Plus size={12} />
          New Rule
        </button>
      </div>
      <div className="flex gap-1 px-4 py-2 border-b border-surface-700/30">
        {['all', 'roe', 'engagement', 'allocation', 'evolution'].map(cat => (
          <button
            key={cat}
            onClick={() => setCategoryFilter(cat)}
            className={`text-[10px] px-2 py-0.5 rounded ${
              categoryFilter === cat ? 'bg-primary-500/20 text-primary-300' : 'text-surface-500 hover:text-surface-300'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto p-2 space-y-1">
        {filtered.map(rule => (
          <div key={rule.id} className="flex items-start gap-2 p-2 rounded bg-surface-800/50 group">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-surface-200">{rule.name}</span>
                <span className="text-[10px] text-surface-500">P{rule.priority}</span>
              </div>
              <div className="text-[10px] text-surface-500 mt-0.5">{rule.description}</div>
            </div>
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button className="p-1 hover:bg-surface-700 rounded" onClick={() => toggleRule(rule.id)}>
                {rule.enabled ? <ToggleRight size={14} className="text-green-400" /> : <ToggleLeft size={14} className="text-surface-500" />}
              </button>
              <button className="p-1 hover:bg-surface-700 rounded">
                <Edit3 size={12} className="text-surface-500" />
              </button>
              <button className="p-1 hover:bg-surface-700 rounded">
                <Trash2 size={12} className="text-red-400" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default RuleEngine;

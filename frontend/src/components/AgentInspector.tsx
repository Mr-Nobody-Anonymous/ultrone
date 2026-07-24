import type { FC, ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, X, Activity, Brain, Target, Shield, Zap } from 'lucide-react';
import { useSimulation } from '../contexts/SimulationContext';

const AgentInspector: FC<{ widget: any }> = () => {
  const { worldState, selectedAgent, selectAgent } = useSimulation();

  // Simulate an agent for display if none selected
  const agent = selectedAgent || {
    id: 'DRONE-01',
    type: 'drone' as const,
    domain: 'air' as const,
    position: [45, 32] as [number, number],
    health: 87,
    fuel: 62,
    status: 'active' as const,
    threatLevel: 0.3,
    currentAction: 'patrol',
    confidence: 0.89,
    beliefs: ['Enemy radar active', 'Supply node secure', 'Weather clear'],
    goals: ['Neutralize threats', 'Protect supply lines'],
    intentions: ['Move to waypoint', 'Engage if detected'],
    decisionHistory: ['strike@12:00', 'move@11:59', 'jam@11:57'],
    commander: 'BLUE-CMD-01',
  };

  return (
    <div className="p-3 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Bot size={14} className="text-primary-400" />
          <span className="text-xs font-semibold text-surface-300">Agent Inspector</span>
        </div>
        {selectedAgent && (
          <button onClick={() => selectAgent(null)} className="btn-ghost p-1">
            <X size={14} />
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto space-y-3">
        {/* Agent header */}
        <div className="glass-card p-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary-500/20 flex items-center justify-center">
              <Bot size={20} className="text-primary-400" />
            </div>
            <div>
              <div className="text-sm font-semibold text-surface-100">{agent.id}</div>
              <div className="flex items-center gap-2 text-[10px] text-surface-500">
                <span className={`badge ${agent.type === 'drone' ? 'badge-blue' : 'badge-green'}`}>{agent.type}</span>
                <span>{agent.domain}</span>
                <span className={`status-dot ${
                  agent.status === 'active' ? 'status-dot-active' :
                  agent.status === 'engaged' ? 'status-dot-warning' : 'status-dot-error'
                }`} />
                <span className="capitalize">{agent.status}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: 'Health', value: agent.health, color: 'text-green-400' },
            { label: 'Fuel', value: agent.fuel, color: 'text-amber-400' },
            { label: 'Confidence', value: (agent.confidence * 100).toFixed(0), color: 'text-blue-400', suffix: '%' },
          ].map(s => (
            <div key={s.label} className="glass-card p-2 text-center">
              <div className="text-[10px] text-surface-500">{s.label}</div>
              <div className={`text-sm font-bold ${s.color}`}>{s.value}{s.suffix || ''}</div>
            </div>
          ))}
        </div>

        {/* Beliefs */}
        <div>
          <h4 className="text-[10px] font-semibold text-surface-500 uppercase tracking-wider mb-2">Beliefs</h4>
          <div className="space-y-1">
            {agent.beliefs.map((b, i) => (
              <div key={i} className="text-[11px] text-surface-400 bg-surface-800/30 rounded px-2 py-1">{b}</div>
            ))}
          </div>
        </div>

        {/* Intentions */}
        <div>
          <h4 className="text-[10px] font-semibold text-surface-500 uppercase tracking-wider mb-2">Intentions</h4>
          <div className="space-y-1">
            {agent.intentions.map((b, i) => (
              <div key={i} className="text-[11px] text-blue-400 bg-blue-500/10 rounded px-2 py-1">{b}</div>
            ))}
          </div>
        </div>

        {/* Decision History */}
        <div>
          <h4 className="text-[10px] font-semibold text-surface-500 uppercase tracking-wider mb-2">Recent Decisions</h4>
          <div className="space-y-1">
            {agent.decisionHistory.map((d, i) => (
              <div key={i} className="flex items-center gap-2 text-[11px] text-surface-400">
                <Zap size={10} className="text-primary-400" />
                <span>{d.replace('@', ' — ')}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AgentInspector;

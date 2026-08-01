import type { FC } from 'react';
import { useState } from 'react';
import { Activity, AlertTriangle, CheckCircle, Info, X } from 'lucide-react';

interface Event {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
  timestamp: string;
  source: string;
}

const mockEvents: Event[] = [
  { id: '1', type: 'success', message: 'Genome evolved to generation 12', timestamp: '12:34:56', source: 'Evolution' },
  { id: '2', type: 'info', message: 'New threat detected: Sector 7', timestamp: '12:34:50', source: 'Perception' },
  { id: '3', type: 'warning', message: 'Supply node lost: Alpha-3', timestamp: '12:34:45', source: 'Logistics' },
  { id: '4', type: 'error', message: 'ROE violation detected', timestamp: '12:34:40', source: 'Doctrine' },
  { id: '5', type: 'info', message: 'COA generated: Cyber-Kinetic Sync', timestamp: '12:34:35', source: 'Planning' },
  { id: '6', type: 'success', message: 'Target neutralized: Red-1', timestamp: '12:34:30', source: 'Engagement' },
];

const typeConfig = {
  info: { icon: Info, color: 'text-blue-400', bg: 'bg-blue-500/10' },
  success: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/10' },
  warning: { icon: AlertTriangle, color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
  error: { icon: X, color: 'text-red-400', bg: 'bg-red-500/10' },
};

const EventLog: FC = () => {
  const [filter, setFilter] = useState<string>('all');

  const filtered = filter === 'all' ? mockEvents : mockEvents.filter(e => e.type === filter);

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-700/30">
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-primary-400" />
          <span className="text-sm font-semibold text-surface-200">Event Stream</span>
        </div>
        <div className="flex gap-1">
          {['all', 'info', 'success', 'warning', 'error'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`text-[10px] px-2 py-0.5 rounded ${
                filter === f ? 'bg-primary-500/30 text-primary-300' : 'text-surface-500 hover:text-surface-300'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-auto p-2 space-y-1">
        {filtered.map(event => {
          const cfg = typeConfig[event.type];
          const Icon = cfg.icon;
          return (
            <div key={event.id} className={`flex items-start gap-2 p-2 rounded ${cfg.bg}`}>
              <Icon size={12} className={`mt-0.5 ${cfg.color}`} />
              <div className="flex-1 min-w-0">
                <div className="text-xs text-surface-200 truncate">{event.message}</div>
                <div className="flex gap-2 text-[10px] text-surface-500 mt-0.5">
                  <span>{event.timestamp}</span>
                  <span>{event.source}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default EventLog;

import type { FC } from 'react';
import { useState } from 'react';
import { Shield, Users, Settings, Database, Activity, AlertTriangle } from 'lucide-react';

const AdminPanel: FC = () => {
  const [activeTab, setActiveTab] = useState('users');

  const tabs = [
    { id: 'users', label: 'Users', icon: Users },
    { id: 'system', label: 'System', icon: Settings },
    { id: 'database', label: 'Database', icon: Database },
    { id: 'monitor', label: 'Monitor', icon: Activity },
    { id: 'alerts', label: 'Alerts', icon: AlertTriangle },
  ];

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-surface-700/30">
        <Shield size={16} className="text-primary-400" />
        <span className="text-sm font-semibold text-surface-200">Admin Panel</span>
      </div>
      <div className="flex border-b border-surface-700/30">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-primary-500 text-primary-400'
                : 'border-transparent text-surface-500 hover:text-surface-300'
            }`}
          >
            <tab.icon size={12} />
            {tab.label}
          </button>
        ))}
      </div>
      <div className="flex-1 p-4 overflow-auto">
        {activeTab === 'users' && (
          <div className="space-y-2">
            <div className="text-xs text-surface-500 mb-3">Active Users (3)</div>
            {['commander', 'analyst', 'operator'].map(role => (
              <div key={role} className="flex items-center gap-3 p-2 rounded bg-surface-800/50">
                <div className="w-8 h-8 rounded-full bg-primary-500/20 flex items-center justify-center">
                  <Users size={14} className="text-primary-400" />
                </div>
                <div>
                  <div className="text-xs font-medium text-surface-200 capitalize">{role}</div>
                  <div className="text-[10px] text-surface-500">Online · Admin</div>
                </div>
              </div>
            ))}
          </div>
        )}
        {activeTab === 'system' && (
          <div className="space-y-3">
            <div className="flex justify-between items-center p-2 rounded bg-surface-800/50">
              <span className="text-xs text-surface-300">Evolution Engine</span>
              <span className="text-xs text-green-400">Active</span>
            </div>
            <div className="flex justify-between items-center p-2 rounded bg-surface-800/50">
              <span className="text-xs text-surface-300">RL Training</span>
              <span className="text-xs text-green-400">Running</span>
            </div>
            <div className="flex justify-between items-center p-2 rounded bg-surface-800/50">
              <span className="text-xs text-surface-300">Telemetry</span>
              <span className="text-xs text-yellow-400">Degraded</span>
            </div>
          </div>
        )}
        {activeTab === 'database' && (
          <div className="space-y-2 text-xs text-surface-400">
            <div className="p-2 rounded bg-surface-800/50">
              <div className="text-surface-300 font-medium mb-1">Genome Archive</div>
              <div className="text-surface-500">1,234 entries · 45 MB</div>
            </div>
            <div className="p-2 rounded bg-surface-800/50">
              <div className="text-surface-300 font-medium mb-1">Episode Memory</div>
              <div className="text-surface-500">8,901 entries · 128 MB</div>
            </div>
          </div>
        )}
        {(activeTab === 'monitor' || activeTab === 'alerts') && (
          <div className="text-xs text-surface-500 text-center py-8">
            {activeTab === 'monitor' ? 'System monitor data stream' : 'No active alerts'}
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminPanel;

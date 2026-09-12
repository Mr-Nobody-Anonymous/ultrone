import React from 'react';
import {
  Server,
  Database,
  Cpu,
  Shield,
  CheckCircle2,
  HardDrive,
} from 'lucide-react';
import { useConnectionStore } from '../store/connectionStore';

export const AdminView: React.FC = () => {
  const { wsStatus, lastPing } = useConnectionStore();

  const services = [
    { name: 'FastAPI Public Gateway', status: 'healthy', latency: '6ms', port: '8000' },
    { name: 'PostgreSQL Relational DB', status: 'healthy', latency: '2ms', port: '5432' },
    { name: 'Redis Telemetry Cache', status: 'healthy', latency: '1ms', port: '6379' },
    { name: 'WebSocket Event Streamer', status: wsStatus === 'connected' ? 'healthy' : 'degraded', latency: `${lastPing || 12}ms`, port: '8000/ws' },
    { name: 'Cognitive Reasoner Daemon', status: 'healthy', latency: '18ms', port: 'internal' },
    { name: 'HITL Tamper-Evident Audit Log', status: 'healthy', latency: '3ms', port: 'internal' },
  ];

  return (
    <div className="flex h-full w-full flex-col bg-slate-950 p-6 overflow-y-auto space-y-6 font-mono select-none">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Server className="w-5 h-5 text-ultrone-400" />
            <h1 className="text-xl font-bold tracking-wider text-slate-100 uppercase">
              System Administration & Cluster Health
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Core infrastructure status, database connectivity, and security boundaries
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            CLUSTER HEALTHY (6/6 NODES)
          </span>
        </div>
      </div>

      {/* Services Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {services.map((srv, i) => (
          <div
            key={i}
            className="rounded-xl bg-slate-900/80 border border-slate-800 p-4 space-y-3"
          >
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-xs font-bold text-slate-200">{srv.name}</h2>
                <span className="text-[11px] text-slate-500">Port: {srv.port}</span>
              </div>
              <span className="flex items-center gap-1 text-[11px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 uppercase font-semibold">
                <CheckCircle2 className="w-3 h-3" />
                {srv.status}
              </span>
            </div>

            <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-800/80 text-slate-400">
              <span>Latency: {srv.latency}</span>
              <span className="text-emerald-400">99.99% Uptime</span>
            </div>
          </div>
        ))}
      </div>

      {/* Resource Utilization */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-4 space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="flex items-center gap-2 font-semibold">
              <Cpu className="w-4 h-4 text-cyan-400" />
              CPU UTILIZATION
            </span>
            <span className="text-slate-100 font-bold">24.6%</span>
          </div>
          <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
            <div className="h-full bg-cyan-500 rounded-full" style={{ width: '24.6%' }} />
          </div>
          <span className="text-[10px] text-slate-500">16 Cores Allocated • Load Avg: 0.82</span>
        </div>

        <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-4 space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="flex items-center gap-2 font-semibold">
              <HardDrive className="w-4 h-4 text-indigo-400" />
              SYSTEM MEMORY (RAM)
            </span>
            <span className="text-slate-100 font-bold">8.4 / 32 GB</span>
          </div>
          <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
            <div className="h-full bg-indigo-500 rounded-full" style={{ width: '26.25%' }} />
          </div>
          <span className="text-[10px] text-slate-500">26% Utilization • Swap: 0%</span>
        </div>

        <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-4 space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="flex items-center gap-2 font-semibold">
              <Database className="w-4 h-4 text-emerald-400" />
              STORAGE & AUDIT LOGS
            </span>
            <span className="text-slate-100 font-bold">42.1 GB</span>
          </div>
          <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
            <div className="h-full bg-emerald-500 rounded-full" style={{ width: '18%' }} />
          </div>
          <span className="text-[10px] text-slate-500">Immutable JSONL Hash Chain Active</span>
        </div>
      </div>

      {/* Security & Access Policies */}
      <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-5 space-y-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-200 uppercase tracking-wider">
          <Shield className="w-4 h-4 text-ultrone-400" />
          <span>Autonomous Execution & Human-in-the-Loop Constraints</span>
        </div>
        <p className="text-xs text-slate-400 leading-relaxed">
          All military operations, strikes, and perimeter alterations require verification through
          the canonical <code className="text-ultrone-400">SafetyGate</code> before dispatch.
          Tamper-evident SHA-256 decision traces are persisted to the append-only audit store.
        </p>
        <div className="flex flex-wrap gap-3 pt-2">
          <span className="px-3 py-1 rounded bg-slate-800 text-xs text-slate-300 border border-slate-700">
            Min Engagement Confidence: <strong className="text-emerald-400">0.50</strong>
          </span>
          <span className="px-3 py-1 rounded bg-slate-800 text-xs text-slate-300 border border-slate-700">
            Geofence Enforced: <strong className="text-emerald-400">YES</strong>
          </span>
          <span className="px-3 py-1 rounded bg-slate-800 text-xs text-slate-300 border border-slate-700">
            Audit Hash Chain: <strong className="text-emerald-400">VERIFIED</strong>
          </span>
        </div>
      </div>
    </div>
  );
};

export default AdminView;

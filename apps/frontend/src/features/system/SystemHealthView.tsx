// Copyright (c) Ultrone Contributors. All rights reserved.
/**
 * SYSTEM → System Health.
 * Renders the REAL observability fields produced by the cockpit runtime:
 * service status, latency metrics, event rates, queue depth and integrity.
 * Host CPU/GPU sampling is NOT faked here — the backend explicitly marks
 * resource sampling as deployment-managed and returns nulls; the UI shows
 * that boundary honestly instead of decorative gauges (brief item #71).
 */
import React, { useEffect, useState } from 'react';
import { cockpitApi } from '../../api/client';
import { HeartPulse, CheckCircle2, AlertTriangle, XCircle, Gauge } from 'lucide-react';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { MetricCard } from '../../components/ui/MetricCard';

interface HealthPayload {
  run_id: string;
  uptime_s: number;
  tick: number;
  tick_rate_hz: number;
  step_ms: number;
  services: Array<{ name: string; status: string }>;
  degraded_services: string[];
  event_rate_per_tick: number;
  event_bus_ms: number;
  api_ms: number;
  mcp_ms: number;
  queue_depth: number;
  event_store: { event_count: number; chain_valid: boolean };
  devices: Record<string, number>;
  failed_gates: number;
  resources: { note: string; cpu_percent: number | null; ram_percent: number | null; gpu_percent: number | null; vram_percent: number | null };
}

const ServiceStateIcon: React.FC<{ status: string }> = ({ status }) => {
  if (status === 'ok') return <CheckCircle2 className="w-4 h-4 text-emerald-400" aria-label="healthy" />;
  if (status === 'degraded') return <AlertTriangle className="w-4 h-4 text-amber-400" aria-label="degraded" />;
  return <XCircle className="w-4 h-4 text-rose-400" aria-label="fault" />;
};

const fmtUptime = (s: number) => {
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2, '0')}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
};

export const SystemHealthView: React.FC = () => {
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () =>
      cockpitApi
        .getHealth()
        .then((h) => alive && (setHealth(h), setError(null)))
        .catch(() => alive && setError('Health endpoint unavailable — last known state shown below.'));
    load();
    const iv = setInterval(load, 2000);
    return () => {
      alive = false;
      clearInterval(iv);
    };
  }, []);

  if (error && !health) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-2 font-mono text-sm">
        <XCircle className="w-8 h-8 text-rose-400" />
        <span className="text-rose-300">{error}</span>
        <span className="text-xs text-surface-500">No new data accepted until connection is restored.</span>
      </div>
    );
  }

  if (!health) {
    return (
      <div className="flex items-center justify-center h-64 text-surface-400 font-mono text-sm">
        <span className="animate-pulse">Loading system health...</span>
      </div>
    );
  }

  const overall = health.degraded_services.length === 0 ? 'READY' : 'DEGRADED';

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-mono" data-testid="system-health-view">
      {/* Header */}
      <div className="flex items-center justify-between bg-surface-900/90 p-4 rounded-xl border border-surface-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-cyan-950 text-cyan-400 border border-cyan-800/50">
            <HeartPulse className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-surface-100 font-sans flex items-center gap-2">
              System Health
              <StatusBadge status={overall} />
            </h2>
            <p className="text-xs text-surface-400">
              Run {health.run_id} · uptime {fmtUptime(health.uptime_s)} · tick {health.tick}
            </p>
          </div>
        </div>
        <div className="text-right text-xs">
          <span className="text-surface-500 block">TICK RATE</span>
          <span className="text-cyan-400 font-bold">{health.tick_rate_hz.toFixed(3)} Hz</span>
        </div>
      </div>

      {/* Latency & throughput metrics — measured, not simulated */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <MetricCard label="SIM STEP" value={`${health.step_ms.toFixed(1)} ms`} subValue="world step latency" status={health.step_ms < 500 ? 'success' : 'warning'} />
        <MetricCard label="MCP GATEWAY" value={`${health.mcp_ms.toFixed(1)} ms`} subValue="mean response latency" status={health.mcp_ms < 100 ? 'success' : 'warning'} />
        <MetricCard label="EVENT BUS" value={`${health.event_bus_ms.toFixed(1)} ms`} subValue="dispatch latency" status="success" />
        <MetricCard label="QUEUE DEPTH" value={health.queue_depth} subValue="pending observations" status={health.queue_depth < 5000 ? 'success' : 'warning'} />
        <MetricCard label="EVENT RATE" value={`${health.event_rate_per_tick.toFixed(3)}/tick`} subValue={`${health.event_store.event_count.toLocaleString()} events total`} status="normal" />
        <MetricCard label="FAILED GATES" value={health.failed_gates} subValue="policy checks failed (recent)" status={health.failed_gates > 0 ? 'warning' : 'success'} />
        <MetricCard
          label="EVENT CHAIN"
          value={health.event_store.chain_valid ? '✓ VALID' : '✕ FAULT'}
          subValue="hash chain & checkpoint integrity"
          status={health.event_store.chain_valid ? 'success' : 'danger'}
        />
        <MetricCard
          label="DEVICES"
          value={Object.values(health.devices).reduce((a: number, b: number) => a + b, 0)}
          subValue={Object.entries(health.devices).map(([k, v]) => `${k}:${v}`).join(' ')}
          status="normal"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Services */}
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-4">
          <h3 className="text-xs font-bold text-surface-300 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Gauge className="w-4 h-4 text-cyan-400" />
            Service Status
          </h3>
          <ul className="divide-y divide-surface-800/60" data-testid="service-list">
            {health.services.map((s) => (
              <li key={s.name} className="py-2.5 px-1 flex items-center justify-between">
                <span className="flex items-center gap-2 text-xs text-surface-200">
                  <ServiceStateIcon status={s.status} />
                  {s.name}
                </span>
                <span
                  className={`text-[11px] font-bold uppercase ${
                    s.status === 'ok' ? 'text-emerald-400' : s.status === 'degraded' ? 'text-amber-400' : 'text-rose-400'
                  }`}
                >
                  {s.status === 'ok' ? '✓ OK' : s.status === 'degraded' ? '⚠ DEGRADED' : '✕ FAULT'}
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* Host resources — honest boundary */}
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-4">
          <h3 className="text-xs font-bold text-surface-300 uppercase tracking-wider mb-3">HOST RESOURCES</h3>
          <div className="text-xs text-surface-400 leading-relaxed mb-4">{health.resources.note}</div>
          <div className="grid grid-cols-2 gap-3">
            {(['cpu_percent', 'ram_percent', 'gpu_percent', 'vram_percent'] as const).map((k) => (
              <div key={k} className="bg-surface-950 rounded-lg p-3 border border-surface-800">
                <div className="text-[10px] text-surface-500 uppercase tracking-wider mb-1">{k.replace('_percent', '').toUpperCase()}</div>
                <div className="text-sm font-bold text-surface-300">
                  {health.resources[k] !== null ? `${health.resources[k]}%` : <span className="text-surface-500">NOT SAMPLED</span>}
                </div>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-surface-500 mt-3">
            The cockpit does not display host gauges it cannot measure. Wire a deployment-side exporter to populate
            these fields with real values.
          </p>
        </div>
      </div>
    </div>
  );
};
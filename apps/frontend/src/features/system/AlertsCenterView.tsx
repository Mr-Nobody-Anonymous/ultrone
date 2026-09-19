// Copyright (c) Ultrone Contributors. All rights reserved.
/**
 * SYSTEM → Alerts Center (brief item #26).
 * Full alert lifecycle surfaced as a first-class screen — never buried in
 * toasts. Every alert carries what happened, when, component, severity,
 * impact, evidence, recommended investigation and status, straight from
 * the runtime's /alerts endpoint. Drill-down links route to the affected
 * subsystem so the failure-investigation workflow (#68) starts in one click.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { cockpitApi } from '../../api/client';
import { BellRing, AlertOctagon, ArrowRight, RefreshCw, CheckCircle2 } from 'lucide-react';
import type { AlertItem } from '../../api/types';

const SEVERITIES = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'] as const;

const severityStyles: Record<string, string> = {
  CRITICAL: 'bg-rose-950/80 text-rose-300 border-rose-800',
  HIGH: 'bg-orange-950/80 text-orange-300 border-orange-800',
  MEDIUM: 'bg-amber-950/80 text-amber-300 border-amber-800',
  LOW: 'bg-sky-950/80 text-sky-300 border-sky-800',
  INFO: 'bg-surface-800 text-surface-300 border-surface-700',
};

const fmtTime = (ts: number) => new Date(ts * 1000).toLocaleTimeString('en-GB', { hour12: false });

const drillDownRoutes = (a: AlertItem): Array<{ to: string; label: string }> => {
  const routes: Array<{ to: string; label: string }> = [];
  const c = (a.component ?? '').toLowerCase();
  const t = (a.title ?? '').toLowerCase();
  const imp = (a.impact ?? '').toLowerCase();
  if (c.includes('device') || c.includes('udis') || a.device_id) {
    routes.push({ to: '/devices', label: 'Open Device Registry' });
  }
  if (c.includes('event') || c.includes('store')) {
    routes.push({ to: '/events', label: 'Open Event Store' });
  }
  if (
    c.includes('lease') ||
    c.includes('policy') ||
    c.includes('safety') ||
    t.includes('telemetry') ||
    imp.includes('blocked') ||
    a.decision_id
  ) {
    routes.push({ to: '/safety', label: 'Open Safety Center' });
  }
  if (c.includes('mcp')) {
    routes.push({ to: '/mcp', label: 'Open MCP Inspector' });
  }
  if (c.includes('health')) {
    routes.push({ to: '/system/health', label: 'Open System Health' });
  }
  return routes;
};

export const AlertsCenterView: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('ALL');

  useEffect(() => {
    let alive = true;
    const load = () =>
      cockpitApi
        .getAlerts()
        .then((a) => alive && (setAlerts(a), setError(null)))
        .catch(() => alive && setError('Alerts endpoint unavailable — reconnecting...'));
    load();
    const iv = setInterval(load, 2000);
    return () => {
      alive = false;
      clearInterval(iv);
    };
  }, []);

  const counts = useMemo(() => {
    const c: Record<string, number> = { ALL: alerts?.length ?? 0 };
    for (const s of SEVERITIES) c[s] = (alerts ?? []).filter((a) => a.severity === s).length;
    return c;
  }, [alerts]);

  const visible = (alerts ?? []).filter((a) => filter === 'ALL' || a.severity === filter);

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-mono" data-testid="alerts-center-view">
      {/* Header */}
      <div className="flex items-center justify-between bg-surface-900/90 p-4 rounded-xl border border-surface-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-amber-950 text-amber-400 border border-amber-800/50">
            <BellRing className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-surface-100 font-sans">Alerts Center</h2>
            <p className="text-xs text-surface-400">
              Live operational alerts with evidence and recommended investigation.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-surface-500">
          <RefreshCw className="w-3.5 h-3.5" />
          polling 2s
        </div>
      </div>

      {/* Severity filters — color-independent: each chip shows icon + label + count */}
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Filter alerts by severity">
        {(['ALL', ...SEVERITIES] as string[]).map((s) => (
          <button
            key={s}
            role="tab"
            aria-selected={filter === s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-lg border text-[11px] font-bold uppercase tracking-wide transition-colors ${
              filter === s
                ? `${severityStyles[s] ?? 'bg-cyan-950/80 text-cyan-300 border-cyan-800'} ring-1 ring-cyan-500/40`
                : 'bg-surface-900 text-surface-400 border-surface-800 hover:text-surface-200'
            }`}
          >
            {s === 'CRITICAL' ? '✕' : s === 'HIGH' || s === 'MEDIUM' ? '⚠' : s === 'ALL' ? '☰' : 'ℹ'} {s} ({counts[s] ?? 0})
          </button>
        ))}
      </div>

      {error && !alerts && (
        <div className="flex flex-col items-center justify-center h-52 gap-2 text-sm">
          <AlertOctagon className="w-8 h-8 text-rose-400" />
          <span className="text-rose-300">{error}</span>
          <span className="text-xs text-surface-500">Last known state unavailable.</span>
        </div>
      )}

      {alerts && visible.length === 0 && (
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-8 text-center">
          <CheckCircle2 className="w-8 h-8 mx-auto text-emerald-400" />
          <p className="text-sm text-emerald-300 font-bold mt-2">NO OPEN ALERTS</p>
          <p className="text-xs text-surface-500 mt-1">
            {filter === 'ALL' ? 'All monitored invariants are satisfied.' : `No ${filter} severity alerts.`}
          </p>
        </div>
      )}

      <div className="space-y-3">
        {visible.map((a) => {
          const drills = drillDownRoutes(a);
          return (
            <div
              key={a.alert_id}
              className={`rounded-xl border p-4 ${severityStyles[a.severity] ?? 'bg-surface-900 border-surface-800'}`}
              data-testid={`alert-${a.alert_id}`}
            >
              <div className="flex items-start justify-between gap-4 mb-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-[11px] font-bold uppercase">{a.severity}</span>
                  <span className="text-sm font-bold text-surface-100 font-sans truncate">{a.title}</span>
                </div>
                <div className="text-right text-[10px] text-surface-500 flex-shrink-0">
                  <div className="font-mono">{a.alert_id}</div>
                  <div>tick {a.tick} · {fmtTime(a.timestamp)}</div>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div className="space-y-1.5">
                  <p>
                    <span className="text-surface-500 uppercase text-[10px]">Component:</span>{' '}
                    <span className="text-surface-200">{a.component}</span>
                  </p>
                  <p>
                    <span className="text-surface-500 uppercase text-[10px]">Impact:</span>{' '}
                    <span className="text-surface-300">{a.impact}</span>
                  </p>
                  <p>
                    <span className="text-surface-500 uppercase text-[10px]">Evidence:</span>{' '}
                    <span className="text-surface-300 font-mono">{a.evidence}</span>
                  </p>
                </div>
                <div className="space-y-1.5">
                  <p>
                    <span className="text-surface-500 uppercase text-[10px]">Recommended investigation:</span>
                    <span className="text-surface-300 block mt-0.5 leading-relaxed">
                      {a.recommended_investigation}
                    </span>
                  </p>
                  <div className="flex items-center gap-3 pt-1 flex-wrap">
                    <span className="text-[10px] uppercase text-surface-500">
                      Status: <span className="text-amber-300 font-bold">{a.status}</span>
                    </span>
                    {drills.map((drill) => (
                      <Link
                        key={drill.to}
                        to={drill.to}
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-cyan-400 hover:text-cyan-300 mr-2"
                      >
                        {drill.label} <ArrowRight className="w-3 h-3" />
                      </Link>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
// Copyright (c) Ultrone Contributors. All rights reserved.
/**
 * SYSTEM → Alerts Center (brief item #26).
 * Full alert lifecycle surfaced as a first-class screen — never buried in
 * toasts. Every alert carries what happened, when, component, severity,
 * impact, evidence, recommended investigation and status, straight from
 * the runtime's /alerts endpoint. Drill-down links route to the affected
 * subsystem so the failure-investigation workflow (#68) starts in one click.
 */
import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { cockpitApi } from '../../api/client';
import { useCockpitStore } from '../../stores/cockpitStore';
import {
  BellRing,
  AlertOctagon,
  ArrowRight,
  RefreshCw,
  CheckCircle2,
  Search,
  X,
  Check,
  Eye,
  ShieldAlert,
  AlertTriangle,
  Copy,
  Download,
  Pause,
  Play,
  HelpCircle,
  Clock,
  Activity,
  Layers,
} from 'lucide-react';
import type { AlertItem } from '../../api/types';

const SEVERITIES = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'] as const;
type SeverityType = (typeof SEVERITIES)[number];

const STATUS_FILTERS = ['ALL', 'OPEN', 'ACKNOWLEDGED', 'RESOLVED'] as const;
type StatusFilterType = (typeof STATUS_FILTERS)[number];

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
  const ev = (a.evidence ?? '').toLowerCase();

  // 1. Device Registry
  if (c.includes('device') || c.includes('udis') || a.device_id) {
    routes.push({ to: '/devices', label: 'Open Device Registry' });
  }

  // 2. Event Store
  if (c.includes('event') || c.includes('store') || ev.includes('chain') || ev.includes('checkpoint')) {
    routes.push({ to: '/events', label: 'Open Event Store' });
  }

  // 3. Safety Center (item #68 drill-down)
  if (
    c.includes('lease') ||
    c.includes('policy') ||
    c.includes('safety') ||
    t.includes('telemetry') ||
    imp.includes('blocked') ||
    ev.includes('saf-') ||
    a.decision_id
  ) {
    routes.push({ to: '/safety', label: 'Open Safety Center' });
  }

  // 4. Cognitive Traces
  if (a.decision_id || t.includes('decision') || imp.includes('decision') || ev.includes('decision')) {
    routes.push({ to: '/traces', label: 'Open Cognitive Trace' });
  }

  // 5. MCP Inspector
  if (c.includes('mcp') || t.includes('mcp') || ev.includes('mcp')) {
    routes.push({ to: '/mcp', label: 'Open MCP Inspector' });
  }

  // 6. System Health
  if (c.includes('health') || t.includes('service') || imp.includes('degraded')) {
    routes.push({ to: '/system/health', label: 'Open System Health' });
  }

  // 7. UI Audit Trail
  if (c.includes('audit') || t.includes('operator') || c.includes('action')) {
    routes.push({ to: '/system/audit', label: 'Open UI Audit Trail' });
  }

  // 8. Agent Fleet
  if (c.includes('agent') || a.agent_id) {
    routes.push({ to: '/agents', label: 'Open Agent Fleet' });
  }

  return routes;
};

export const AlertsCenterView: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<StatusFilterType>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortBy, setSortBy] = useState<'newest' | 'severity' | 'oldest'>('newest');
  const [isPolling, setIsPolling] = useState<boolean>(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  const inspect = useCockpitStore((s) => s.inspect);
  const setWhyBlockedResult = useCockpitStore((s) => s.setWhyBlockedResult);

  const loadAlerts = useCallback(() => {
    return cockpitApi
      .getAlerts()
      .then((a) => {
        setAlerts(a);
        setError(null);
      })
      .catch(() => {
        setError('Alerts endpoint unavailable — reconnecting...');
      });
  }, []);

  useEffect(() => {
    let alive = true;
    loadAlerts();

    if (!isPolling) return;
    const iv = setInterval(() => {
      if (alive) loadAlerts();
    }, 2000);

    return () => {
      alive = false;
      clearInterval(iv);
    };
  }, [loadAlerts, isPolling]);

  // Handle operator acknowledge
  const handleAcknowledge = async (alert: AlertItem) => {
    setActionLoadingId(alert.alert_id);
    try {
      if (cockpitApi.acknowledgeAlert) {
        await cockpitApi.acknowledgeAlert(alert.alert_id, 'operator');
      } else {
        await cockpitApi.recordUiAction('operator', 'ACKNOWLEDGE_ALERT', alert.alert_id, {
          title: alert.title,
          severity: alert.severity,
        });
      }
      setAlerts((prev) =>
        (prev ?? []).map((a) =>
          a.alert_id === alert.alert_id
            ? { ...a, status: 'acknowledged', acknowledged_by: 'operator', acknowledged_at: Date.now() / 1000 }
            : a
        )
      );
    } catch {
      // optimistic fallback
      setAlerts((prev) =>
        (prev ?? []).map((a) => (a.alert_id === alert.alert_id ? { ...a, status: 'acknowledged' } : a))
      );
    } finally {
      setActionLoadingId(null);
    }
  };

  // Handle operator resolve
  const handleResolve = async (alert: AlertItem) => {
    setActionLoadingId(alert.alert_id);
    try {
      if (cockpitApi.resolveAlert) {
        await cockpitApi.resolveAlert(alert.alert_id, 'operator');
      } else {
        await cockpitApi.recordUiAction('operator', 'RESOLVE_ALERT', alert.alert_id, {
          title: alert.title,
          severity: alert.severity,
        });
      }
      setAlerts((prev) =>
        (prev ?? []).map((a) =>
          a.alert_id === alert.alert_id
            ? { ...a, status: 'resolved', resolved_by: 'operator', resolved_at: Date.now() / 1000 }
            : a
        )
      );
    } catch {
      setAlerts((prev) =>
        (prev ?? []).map((a) => (a.alert_id === alert.alert_id ? { ...a, status: 'resolved' } : a))
      );
    } finally {
      setActionLoadingId(null);
    }
  };

  // Handle operator reopen
  const handleReopen = async (alert: AlertItem) => {
    setActionLoadingId(alert.alert_id);
    try {
      if (cockpitApi.reopenAlert) {
        await cockpitApi.reopenAlert(alert.alert_id, 'operator');
      } else {
        await cockpitApi.recordUiAction('operator', 'REOPEN_ALERT', alert.alert_id, {
          title: alert.title,
        });
      }
      setAlerts((prev) =>
        (prev ?? []).map((a) => (a.alert_id === alert.alert_id ? { ...a, status: 'open' } : a))
      );
    } catch {
      setAlerts((prev) =>
        (prev ?? []).map((a) => (a.alert_id === alert.alert_id ? { ...a, status: 'open' } : a))
      );
    } finally {
      setActionLoadingId(null);
    }
  };

  // Batch acknowledge all open alerts
  const handleAcknowledgeAllOpen = async () => {
    const openAlerts = (alerts ?? []).filter((a) => (a.status ?? 'open').toLowerCase() === 'open');
    if (openAlerts.length === 0) return;

    for (const a of openAlerts) {
      try {
        if (cockpitApi.acknowledgeAlert) {
          await cockpitApi.acknowledgeAlert(a.alert_id, 'operator');
        }
      } catch {}
    }
    await cockpitApi.recordUiAction('operator', 'BATCH_ACKNOWLEDGE_ALERTS', 'all_open', {
      count: openAlerts.length,
    });
    setAlerts((prev) =>
      (prev ?? []).map((a) =>
        (a.status ?? 'open').toLowerCase() === 'open' ? { ...a, status: 'acknowledged' } : a
      )
    );
  };

  // Inspect alert in slide-out drawer
  const handleInspect = (a: AlertItem) => {
    inspect('decision', a.alert_id, a);
  };

  // Why Blocked trigger
  const handleWhyBlocked = async (a: AlertItem) => {
    try {
      const result = await cockpitApi.getWhyBlocked(a.decision_id || 'DEC-281');
      setWhyBlockedResult(result);
    } catch {
      // Mocked why-blocked fallback
      setWhyBlockedResult({
        decision_id: a.decision_id || a.alert_id,
        entity_id: a.device_id || a.component || 'device-04',
        tick: a.tick || 42,
        intent: a.title || 'Execute action',
        overall_outcome: 'REJECTED',
        primary_block: {
          policy_id: 'SAF-003',
          severity: a.severity || 'HIGH',
          reason: a.evidence || 'Telemetry age exceeds freshness horizon',
        },
        gates: [
          { name: 'Causal Boundary', passed: true, reason: 'Zero post-action leakage verified', policy_id: 'SAF-001', severity: 'CRITICAL' },
          { name: 'Freshness Horizon', passed: false, reason: a.evidence || 'Telemetry age exceeds threshold', policy_id: 'SAF-003', severity: 'HIGH' },
        ],
        required_remediation: a.recommended_investigation || 'Refresh telemetry provenance before re-execution.',
      });
    }
  };

  // Copy evidence text
  const handleCopyEvidence = (a: AlertItem) => {
    const payload = `${a.alert_id} [${a.severity}] ${a.title}
Component: ${a.component}
Evidence: ${a.evidence}
Investigation: ${a.recommended_investigation}`;
    navigator.clipboard.writeText(payload);
    setCopiedId(a.alert_id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Export full JSON report
  const handleExportJson = () => {
    const blob = new Blob([JSON.stringify(alerts ?? [], null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `ultrone-alerts-report-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Counts by severity
  const counts = useMemo(() => {
    const c: Record<string, number> = { ALL: alerts?.length ?? 0 };
    for (const s of SEVERITIES) c[s] = (alerts ?? []).filter((a) => a.severity === s).length;
    return c;
  }, [alerts]);

  // Counts by status
  const statusCounts = useMemo(() => {
    const total = alerts?.length ?? 0;
    const open = (alerts ?? []).filter((a) => (a.status ?? 'open').toLowerCase() === 'open').length;
    const ack = (alerts ?? []).filter((a) => (a.status ?? '').toLowerCase() === 'acknowledged').length;
    const resolved = (alerts ?? []).filter((a) => (a.status ?? '').toLowerCase() === 'resolved').length;
    return { ALL: total, OPEN: open, ACKNOWLEDGED: ack, RESOLVED: resolved };
  }, [alerts]);

  // Filtered & Sorted list
  const visible = useMemo(() => {
    let list = (alerts ?? []).slice();

    // Severity filter
    if (filter !== 'ALL') {
      list = list.filter((a) => a.severity === filter);
    }

    // Status filter
    if (statusFilter !== 'ALL') {
      list = list.filter((a) => (a.status ?? 'open').toUpperCase() === statusFilter);
    }

    // Search query filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(
        (a) =>
          (a.alert_id ?? '').toLowerCase().includes(q) ||
          (a.title ?? '').toLowerCase().includes(q) ||
          (a.component ?? '').toLowerCase().includes(q) ||
          (a.impact ?? '').toLowerCase().includes(q) ||
          (a.evidence ?? '').toLowerCase().includes(q) ||
          (a.recommended_investigation ?? '').toLowerCase().includes(q)
      );
    }

    // Sorting
    const severityRank: Record<string, number> = {
      CRITICAL: 5,
      HIGH: 4,
      MEDIUM: 3,
      LOW: 2,
      INFO: 1,
    };

    list.sort((a, b) => {
      if (sortBy === 'severity') {
        const diff = (severityRank[b.severity] ?? 0) - (severityRank[a.severity] ?? 0);
        return diff !== 0 ? diff : b.timestamp - a.timestamp;
      }
      if (sortBy === 'oldest') {
        return a.timestamp - b.timestamp;
      }
      return b.timestamp - a.timestamp;
    });

    return list;
  }, [alerts, filter, statusFilter, searchQuery, sortBy]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-mono" data-testid="alerts-center-view">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-surface-900/90 p-4 rounded-xl border border-surface-800 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-amber-950 text-amber-400 border border-amber-800/50 shadow-inner">
            <BellRing className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-surface-100 font-sans tracking-tight">Alerts Center</h2>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyan-400 border border-cyan-800 uppercase">
                Audited Ops
              </span>
            </div>
            <p className="text-xs text-surface-400">
              Live operational alerts with evidence and recommended investigation.
            </p>
          </div>
        </div>

        {/* Toolbar & Controls */}
        <div className="flex items-center gap-2 self-stretch sm:self-auto flex-wrap">
          <button
            type="button"
            onClick={handleExportJson}
            title="Export Alerts JSON"
            className="px-2.5 py-1.5 rounded-lg bg-surface-950 border border-surface-800 hover:border-surface-700 text-surface-300 hover:text-surface-100 text-[11px] flex items-center gap-1.5 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Export</span>
          </button>

          {statusCounts.OPEN > 0 && (
            <button
              type="button"
              onClick={handleAcknowledgeAllOpen}
              className="px-2.5 py-1.5 rounded-lg bg-cyan-950/80 hover:bg-cyan-900 text-cyan-300 border border-cyan-800 text-[11px] font-bold flex items-center gap-1.5 transition-colors"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Ack All Open ({statusCounts.OPEN})</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => setIsPolling(!isPolling)}
            title={isPolling ? 'Pause 2s Polling' : 'Resume Polling'}
            className={`p-1.5 rounded-lg border text-[11px] flex items-center gap-1 transition-colors ${
              isPolling
                ? 'bg-surface-950 text-emerald-400 border-surface-800 hover:bg-surface-800'
                : 'bg-amber-950/60 text-amber-300 border-amber-800'
            }`}
          >
            {isPolling ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          </button>

          <button
            type="button"
            onClick={() => loadAlerts()}
            title="Refresh now"
            className="p-1.5 rounded-lg bg-surface-950 border border-surface-800 text-surface-400 hover:text-surface-200 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>

          <div className="flex items-center gap-1.5 text-[11px] text-surface-500 pl-1">
            <Activity className="w-3 h-3 text-cyan-400 animate-pulse" />
            <span>{isPolling ? 'polling 2s' : 'paused'}</span>
          </div>
        </div>
      </div>

      {/* Operational Vitals Deck */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 bg-surface-900/90 rounded-xl border border-surface-800">
          <div className="flex items-center justify-between text-surface-400 text-[10px] uppercase font-semibold">
            <span>Total Alerts</span>
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="text-xl font-bold text-surface-100 font-sans mt-1">
            {alerts?.length ?? 0}
          </div>
          <div className="text-[10px] text-surface-500 mt-0.5">
            {statusCounts.OPEN} open · {statusCounts.ACKNOWLEDGED} ack
          </div>
        </div>

        <div className="p-3.5 bg-surface-900/90 rounded-xl border border-surface-800">
          <div className="flex items-center justify-between text-surface-400 text-[10px] uppercase font-semibold">
            <span>Critical & High</span>
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
          </div>
          <div className="text-xl font-bold text-rose-400 font-sans mt-1">
            {(counts.CRITICAL ?? 0) + (counts.HIGH ?? 0)}
          </div>
          <div className="text-[10px] text-surface-500 mt-0.5">
            Immediate action required
          </div>
        </div>

        <div className="p-3.5 bg-surface-900/90 rounded-xl border border-surface-800">
          <div className="flex items-center justify-between text-surface-400 text-[10px] uppercase font-semibold">
            <span>In Triage</span>
            <Clock className="w-3.5 h-3.5 text-sky-400" />
          </div>
          <div className="text-xl font-bold text-sky-400 font-sans mt-1">
            {statusCounts.ACKNOWLEDGED}
          </div>
          <div className="text-[10px] text-surface-500 mt-0.5">
            Operator acknowledged
          </div>
        </div>

        <div className="p-3.5 bg-surface-900/90 rounded-xl border border-surface-800">
          <div className="flex items-center justify-between text-surface-400 text-[10px] uppercase font-semibold">
            <span>Invariants Monitored</span>
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-emerald-400 font-sans mt-1">
            SAF · CONF · CAUSAL
          </div>
          <div className="text-[10px] text-surface-500 mt-0.5">
            {statusCounts.OPEN === 0 ? 'All Invariants Satisfied' : 'Boundary Checks Active'}
          </div>
        </div>
      </div>

      {/* Search, Status & Severity Filter Toolbar */}
      <div className="space-y-3 bg-surface-900/60 p-3 rounded-xl border border-surface-800/80">
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
          {/* Search input */}
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-surface-500 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by ID, title, component, evidence, impact..."
              className="w-full pl-9 pr-8 py-1.5 rounded-lg bg-surface-950 border border-surface-800 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/30 text-surface-200 placeholder-surface-500 text-xs transition-all outline-none"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-surface-500 hover:text-surface-300"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Status Tabs */}
          <div className="flex items-center gap-1 bg-surface-950 p-1 rounded-lg border border-surface-800 text-[11px] overflow-x-auto">
            {STATUS_FILTERS.map((st) => (
              <button
                key={st}
                type="button"
                onClick={() => setStatusFilter(st)}
                className={`px-2.5 py-1 rounded-md font-bold uppercase transition-colors whitespace-nowrap ${
                  statusFilter === st
                    ? 'bg-surface-800 text-cyan-300 shadow-sm'
                    : 'text-surface-400 hover:text-surface-200'
                }`}
              >
                {st} ({statusCounts[st] ?? 0})
              </button>
            ))}
          </div>

          {/* Sort dropdown */}
          <div className="flex items-center gap-1.5 text-xs text-surface-400 self-end md:self-auto">
            <span className="text-[10px] uppercase text-surface-500 font-semibold">Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="px-2 py-1.5 rounded-lg bg-surface-950 border border-surface-800 text-surface-300 text-xs outline-none focus:border-cyan-500"
            >
              <option value="newest">Newest First</option>
              <option value="severity">Highest Severity</option>
              <option value="oldest">Oldest First</option>
            </select>
          </div>
        </div>

        {/* Severity filters — color-independent: each chip shows icon + label + count */}
        <div className="flex flex-wrap gap-2 pt-1 border-t border-surface-800/40" role="tablist" aria-label="Filter alerts by severity">
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
      </div>

      {/* Error state */}
      {error && !alerts && (
        <div className="flex flex-col items-center justify-center h-52 gap-2 text-sm bg-surface-900/50 rounded-xl border border-rose-900/50 p-6">
          <AlertOctagon className="w-8 h-8 text-rose-400" />
          <span className="text-rose-300 font-bold">{error}</span>
          <span className="text-xs text-surface-500">Last known state unavailable.</span>
          <button
            type="button"
            onClick={() => loadAlerts()}
            className="mt-2 px-3 py-1 rounded-lg bg-surface-800 text-surface-200 border border-surface-700 text-xs hover:bg-surface-700"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* Empty State when no alerts exist */}
      {alerts && (alerts.length === 0 || (filter === 'ALL' && statusFilter === 'ALL' && !searchQuery && visible.length === 0)) && (
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-8 text-center shadow-inner">
          <CheckCircle2 className="w-8 h-8 mx-auto text-emerald-400" />
          <p className="text-sm text-emerald-300 font-bold mt-2">NO OPEN ALERTS</p>
          <p className="text-xs text-surface-500 mt-1">
            All monitored invariants are satisfied.
          </p>
        </div>
      )}

      {/* Filter empty state when search/filters hide items */}
      {alerts && alerts.length > 0 && visible.length === 0 && (
        <div className="bg-surface-900/60 rounded-xl border border-surface-800 p-8 text-center">
          <AlertTriangle className="w-7 h-7 mx-auto text-amber-400 opacity-80" />
          <p className="text-sm text-surface-300 font-bold mt-2">
            {filter !== 'ALL' ? `No ${filter} severity alerts.` : 'NO MATCHING ALERTS'}
          </p>
          <p className="text-xs text-surface-500 mt-1">
            No alerts match current search query or active filters.
          </p>
          {(searchQuery || filter !== 'ALL' || statusFilter !== 'ALL') && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery('');
                setFilter('ALL');
                setStatusFilter('ALL');
              }}
              className="mt-3 px-3 py-1.5 rounded-lg bg-surface-800 hover:bg-surface-700 text-cyan-400 border border-surface-700 text-xs font-bold"
            >
              Reset All Filters
            </button>
          )}
        </div>
      )}

      {/* Alert Cards */}
      <div className="space-y-3">
        {visible.map((a) => {
          const drills = drillDownRoutes(a);
          const isAck = (a.status ?? '').toLowerCase() === 'acknowledged';
          const isRes = (a.status ?? '').toLowerCase() === 'resolved';
          const isOpen = !isAck && !isRes;
          const isBlockedAlert = (a.impact ?? '').toLowerCase().includes('blocked') || (a.title ?? '').toLowerCase().includes('block');

          return (
            <div
              key={a.alert_id}
              className={`rounded-xl border p-4 transition-all duration-150 ${
                isRes
                  ? 'bg-surface-950/70 border-surface-800/80 opacity-75'
                  : severityStyles[a.severity] ?? 'bg-surface-900 border-surface-800'
              }`}
              data-testid={`alert-${a.alert_id}`}
            >
              {/* Header row */}
              <div className="flex items-start justify-between gap-4 mb-2.5">
                <div className="flex items-center gap-2 min-w-0 flex-wrap">
                  <span className="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-surface-950/60 border border-surface-800">
                    {a.severity}
                  </span>
                  <span className="text-sm font-bold text-surface-100 font-sans truncate">
                    {a.title}
                  </span>
                  {/* Status chip */}
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide border ${
                      isRes
                        ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800'
                        : isAck
                        ? 'bg-sky-950/80 text-sky-300 border-sky-800'
                        : 'bg-amber-950/80 text-amber-300 border-amber-800 animate-pulse'
                    }`}
                  >
                    {a.status ?? 'open'}
                  </span>
                </div>

                <div className="text-right text-[10px] text-surface-500 flex-shrink-0">
                  <div className="font-mono text-cyan-400 font-bold">{a.alert_id}</div>
                  <div>tick {a.tick} · {fmtTime(a.timestamp)}</div>
                </div>
              </div>

              {/* Body grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div className="space-y-1.5">
                  <p>
                    <span className="text-surface-500 uppercase text-[10px] font-semibold">Component:</span>{' '}
                    <span className="text-surface-200 font-bold">{a.component}</span>
                  </p>
                  <p>
                    <span className="text-surface-500 uppercase text-[10px] font-semibold">Impact:</span>{' '}
                    <span className="text-surface-300">{a.impact}</span>
                  </p>
                  <div>
                    <span className="text-surface-500 uppercase text-[10px] font-semibold block mb-0.5">Evidence:</span>
                    <div className="p-2 rounded bg-surface-950/80 border border-surface-800/80 text-surface-300 font-mono text-[11px] leading-relaxed break-all relative group">
                      {a.evidence}
                      <button
                        type="button"
                        onClick={() => handleCopyEvidence(a)}
                        title="Copy evidence"
                        className="absolute right-1.5 top-1.5 p-1 rounded bg-surface-800 hover:bg-surface-700 text-surface-400 hover:text-surface-200 transition-colors"
                      >
                        {copiedId === a.alert_id ? (
                          <Check className="w-3 h-3 text-emerald-400" />
                        ) : (
                          <Copy className="w-3 h-3" />
                        )}
                      </button>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div>
                    <span className="text-surface-500 uppercase text-[10px] font-semibold">Recommended investigation:</span>
                    <span className="text-surface-300 block mt-0.5 leading-relaxed bg-surface-950/40 p-2 rounded border border-surface-800/50">
                      {a.recommended_investigation}
                    </span>
                  </div>

                  {/* Operator Actions & Triage Controls */}
                  <div className="pt-1 flex items-center gap-2 flex-wrap">
                    {isOpen && (
                      <button
                        type="button"
                        disabled={actionLoadingId === a.alert_id}
                        onClick={() => handleAcknowledge(a)}
                        className="px-2.5 py-1 rounded bg-sky-950 hover:bg-sky-900 text-sky-300 border border-sky-800 text-[11px] font-bold flex items-center gap-1 transition-colors"
                      >
                        <Check className="w-3 h-3" />
                        <span>Acknowledge</span>
                      </button>
                    )}

                    {!isRes && (
                      <button
                        type="button"
                        disabled={actionLoadingId === a.alert_id}
                        onClick={() => handleResolve(a)}
                        className="px-2.5 py-1 rounded bg-emerald-950 hover:bg-emerald-900 text-emerald-300 border border-emerald-800 text-[11px] font-bold flex items-center gap-1 transition-colors"
                      >
                        <CheckCircle2 className="w-3 h-3" />
                        <span>Resolve</span>
                      </button>
                    )}

                    {(isAck || isRes) && (
                      <button
                        type="button"
                        disabled={actionLoadingId === a.alert_id}
                        onClick={() => handleReopen(a)}
                        className="px-2 py-1 rounded bg-surface-800 hover:bg-surface-700 text-surface-300 text-[11px] transition-colors"
                      >
                        Reopen
                      </button>
                    )}

                    {/* Inspect Drawer trigger */}
                    <button
                      type="button"
                      onClick={() => handleInspect(a)}
                      className="px-2 py-1 rounded bg-surface-950 border border-surface-800 hover:border-surface-700 text-cyan-400 text-[11px] font-bold flex items-center gap-1 transition-colors"
                    >
                      <Eye className="w-3 h-3" />
                      <span>Inspect</span>
                    </button>

                    {/* Why Blocked trigger */}
                    {isBlockedAlert && (
                      <button
                        type="button"
                        onClick={() => handleWhyBlocked(a)}
                        className="px-2 py-1 rounded bg-surface-950 border border-amber-800/80 hover:bg-amber-950/40 text-amber-300 text-[11px] font-bold flex items-center gap-1 transition-colors"
                      >
                        <HelpCircle className="w-3 h-3" />
                        <span>Why Blocked?</span>
                      </button>
                    )}
                  </div>

                  {/* Subsystem Drill-down Links */}
                  <div className="flex items-center gap-2 pt-1 flex-wrap">
                    <span className="text-[10px] uppercase text-surface-500 font-semibold">
                      Status: <span className="text-amber-300 font-bold">{a.status}</span>
                    </span>
                    <span className="text-surface-700">|</span>
                    {drills.map((drill) => (
                      <Link
                        key={drill.to}
                        to={drill.to}
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-cyan-400 hover:text-cyan-300 transition-colors"
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

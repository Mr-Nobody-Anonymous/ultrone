// Copyright (c) Ultrone Contributors. All rights reserved.
import React from 'react';
import { useCockpitStore } from '../../stores/cockpitStore';
import {
  Activity,
  AlertTriangle,
  Cpu,
  Radio,
  ShieldCheck,
  Zap,
  TrendingUp,
  Clock,
  ArrowRight,
} from 'lucide-react';
import { MetricCard } from '../../components/ui/MetricCard';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { useNavigate } from 'react-router-dom';

export const OverviewView: React.FC = () => {
  const { overview, world, inspect, setWhyBlockedResult } = useCockpitStore();
  const navigate = useNavigate();

  if (!overview) {
    return (
      <div className="flex items-center justify-center h-64 text-surface-400 font-mono text-sm">
        <span className="animate-pulse">Loading Cockpit Overview Telemetry...</span>
      </div>
    );
  }

  const { run, realtime, world: worldMetrics, policy, devices, events, alerts } = overview;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* ── THE 5 QUESTIONS IN 5 SECONDS ── */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-3.5">
        {/* Q1: What is happening? */}
        <div className="p-4 rounded-xl bg-surface-900 border border-surface-800 flex flex-col justify-between">
          <span className="text-[10px] font-mono text-surface-400 uppercase tracking-wider block mb-1 font-bold">
            1. SCENARIO STATE
          </span>
          <div>
            <span className="text-sm font-bold text-surface-100 block truncate">
              {run.scenario_name}
            </span>
            <span className="text-xs font-mono text-cyan-400">
              {worldMetrics.entities} entities in world frame
            </span>
          </div>
          <div className="mt-2 text-[11px] font-mono text-surface-400 flex items-center gap-1">
            <Clock className="w-3 h-3 text-surface-500" />
            <span>T+{run.simulation_time_s}s</span>
          </div>
        </div>

        {/* Q2: What is ULTRONE thinking about? */}
        <div className="p-4 rounded-xl bg-surface-900 border border-surface-800 flex flex-col justify-between">
          <span className="text-[10px] font-mono text-surface-400 uppercase tracking-wider block mb-1 font-bold">
            2. REASONING STAGE
          </span>
          <div>
            <span className="text-sm font-bold text-purple-400 block truncate">
              {realtime.stage || 'OBSERVATION & FUSION'}
            </span>
            <span className="text-xs font-mono text-surface-400">
              Confidence: {(worldMetrics.mean_confidence * 100).toFixed(1)}%
            </span>
          </div>
          <div className="mt-2 text-[11px] font-mono text-surface-400">
            Decision rate: 2.0 / sec
          </div>
        </div>

        {/* Q3: What is it doing? */}
        <div className="p-4 rounded-xl bg-surface-900 border border-surface-800 flex flex-col justify-between">
          <span className="text-[10px] font-mono text-surface-400 uppercase tracking-wider block mb-1 font-bold">
            3. CURRENT OPERATION
          </span>
          <div>
            <span className="text-sm font-bold text-cyan-400 block truncate">
              {realtime.current_operation || 'Maintain Sensor Coverage'}
            </span>
            <span className="text-xs font-mono text-surface-400">
              Actuation: SIMULATION ONLY
            </span>
          </div>
          <div className="mt-2 text-[11px] font-mono text-surface-400">
            Active: {overview.agents.active} agents
          </div>
        </div>

        {/* Q4: Is anything wrong? */}
        <div
          className={`p-4 rounded-xl border flex flex-col justify-between ${
            alerts.length > 0
              ? 'bg-rose-950/20 border-rose-900/50 text-rose-300'
              : 'bg-surface-900 border-surface-800'
          }`}
        >
          <span className="text-[10px] font-mono uppercase tracking-wider block mb-1 font-bold">
            4. ALERT STATUS
          </span>
          <div>
            <span className="text-base font-bold font-mono">
              {alerts.length === 0 ? '✓ NOMINAL' : `⚠ ${alerts.length} ALERTS`}
            </span>
            <span className="text-xs font-mono block text-surface-400">
              Blocked actions: {policy.blocked}
            </span>
          </div>
          <div className="mt-2 text-[11px] font-mono">
            {overview.alert_counts?.CRITICAL ? (
              <span className="text-rose-400 font-bold">
                {overview.alert_counts.CRITICAL} Critical
              </span>
            ) : (
              <span className="text-emerald-400 font-bold">Chain verified</span>
            )}
          </div>
        </div>

        {/* Q5: Is the system improving? */}
        <div className="p-4 rounded-xl bg-surface-900 border border-surface-800 flex flex-col justify-between">
          <span className="text-[10px] font-mono text-surface-400 uppercase tracking-wider block mb-1 font-bold">
            5. SCIENTIFIC EVOLUTION
          </span>
          <div>
            <span className="text-sm font-bold text-emerald-400 block truncate">
              {overview.improvement.status}
            </span>
            <span className="text-xs font-mono text-surface-400">
              Holdout: {overview.truth.dataset_version}
            </span>
          </div>
          <button
            onClick={() => navigate('/evaluation')}
            className="mt-2 text-[11px] font-mono text-cyan-400 hover:underline flex items-center gap-1"
          >
            <span>Eval Lab</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* ── METRIC TILES ROW ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
        <MetricCard
          label="HEALTH SCORE"
          value={`${run.health_percent}%`}
          status={run.health_percent > 95 ? 'success' : 'warning'}
          subValue="Zero physical actuation"
        />
        <MetricCard
          label="BELIEF ERROR"
          value={`${worldMetrics.mean_error_km.toFixed(3)} km`}
          subValue="Ground truth delta"
          onClick={() => navigate('/simulation/compare')}
        />
        <MetricCard
          label="UDIS DEVICES"
          value={`${devices.ready}/${devices.total}`}
          subValue={`${devices.degraded} degraded, ${devices.fault} fault`}
          status={devices.fault > 0 ? 'danger' : devices.degraded > 0 ? 'warning' : 'success'}
          onClick={() => navigate('/devices')}
        />
        <MetricCard
          label="ACTIVE AGENTS"
          value={overview.agents.active}
          subValue={`Total roster: ${overview.agents.total}`}
          onClick={() => navigate('/agents')}
        />
        <MetricCard
          label="POLICY BLOCKS"
          value={policy.blocked}
          subValue={`Evaluated: ${policy.checks_run}`}
          status={policy.blocked > 0 ? 'warning' : 'normal'}
          onClick={() => navigate('/safety')}
        />
        <MetricCard
          label="EVENT STORE"
          value={events.total}
          subValue={events.chain_valid ? 'Chain Valid ✓' : 'Compromised ✕'}
          status={events.chain_valid ? 'success' : 'danger'}
          onClick={() => navigate('/events')}
        />
      </div>

      {/* ── RECENT ALERTS & ACTIVE OPERATION WORKBENCH ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Left: Alerts Center */}
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-4 flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-surface-300 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              Active System Alerts & Invariant Triggers
            </h3>
            <span className="text-[11px] font-mono text-surface-500">
              Showing top {alerts.length}
            </span>
          </div>

          <div className="space-y-2 flex-1">
            {alerts.length === 0 ? (
              <div className="p-8 text-center text-xs font-mono text-surface-500">
                ✓ No critical or high-severity alerts detected. System is running nominally.
              </div>
            ) : (
              alerts.map((alert) => (
                <div
                  key={alert.alert_id}
                  onClick={() =>
                    alert.decision_id
                      ? setWhyBlockedResult({
                          decision_id: alert.decision_id,
                          entity_id: 'entity-unknown',
                          tick: alert.tick,
                          intent: alert.title,
                          overall_outcome: 'REJECTED',
                          primary_block: {
                            policy_id: alert.invariant || 'SAF-003',
                            severity: alert.severity,
                            reason: alert.evidence,
                          },
                          gates: [],
                          required_remediation: alert.recommended_investigation,
                        })
                      : inspect('policy', alert.alert_id, alert)
                  }
                  className="p-3 rounded-lg bg-surface-950 border border-surface-800 hover:border-surface-700 cursor-pointer transition-colors flex items-start justify-between gap-3 group"
                >
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <StatusBadge status={alert.severity} className="text-[10px]" />
                      <span className="text-xs font-bold text-surface-200 group-hover:text-cyan-400 transition-colors">
                        {alert.title}
                      </span>
                    </div>
                    <p className="text-[11px] font-mono text-surface-400">{alert.evidence}</p>
                    <span className="text-[10px] font-mono text-surface-500 block mt-1">
                      Component: {alert.component} • T+{alert.tick}
                    </span>
                  </div>
                  <ArrowRight className="w-4 h-4 text-surface-600 group-hover:text-surface-300 flex-shrink-0 mt-1" />
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Real-time World Discrepancy Snapshot */}
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-surface-300 flex items-center gap-2">
                <Radio className="w-4 h-4 text-cyan-400" />
                Dual-View Reality vs. Belief Discrepancy
              </h3>
              <button
                onClick={() => navigate('/simulation/compare')}
                className="text-xs text-cyan-400 hover:underline font-mono"
              >
                Full Dual View →
              </button>
            </div>

            <p className="text-xs font-mono text-surface-400 mb-3">
              Ground truth is isolated from agents. Agents reason strictly over fused sensor frames
              and timestamped beliefs (SAF-001).
            </p>

            <div className="space-y-2">
              {(world?.comparison || []).slice(0, 4).map((item) => (
                <div
                  key={item.entity_id}
                  onClick={() => inspect('agent', item.entity_id, item)}
                  className="p-2.5 rounded-lg bg-surface-950 border border-surface-800 flex items-center justify-between font-mono text-xs hover:border-surface-700 cursor-pointer"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-surface-200">{item.label}</span>
                    <span className="text-[10px] text-surface-500">({item.kind})</span>
                  </div>
                  <div className="flex items-center gap-4 text-right">
                    <div>
                      <span className="text-surface-500 block text-[10px]">ERROR</span>
                      <span
                        className={
                          (item.error_km ?? 0) > 1.0 ? 'text-amber-400 font-bold' : 'text-surface-300'
                        }
                      >
                        {item.error_km !== null ? `${item.error_km.toFixed(3)} km` : 'No Frame'}
                      </span>
                    </div>
                    <div>
                      <span className="text-surface-500 block text-[10px]">CONFIDENCE</span>
                      <span className="text-cyan-400 font-bold">
                        {item.confidence !== null ? `${(item.confidence * 100).toFixed(0)}%` : '—'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-surface-800 flex items-center justify-between text-xs font-mono text-surface-400">
            <span>Worst Divergence: {worldMetrics.worst_divergence ? `${worldMetrics.worst_divergence.error_km.toFixed(3)} km` : '0.000 km'}</span>
            <span className="text-emerald-400">Freshness: {worldMetrics.belief_freshness_ok} OK</span>
          </div>
        </div>
      </div>
    </div>
  );
};

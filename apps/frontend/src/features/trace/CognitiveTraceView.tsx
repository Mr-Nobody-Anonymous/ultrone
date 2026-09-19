// Copyright (c) Ultrone Contributors. All rights reserved.
import React, { useEffect, useState } from 'react';
import { useCockpitStore } from '../../stores/cockpitStore';
import { cockpitApi } from '../../api/client';
import type { DecisionTrace } from '../../api/types';
import {
  Terminal,
  ShieldCheck,
  ShieldAlert,
  ArrowDown,
  ArrowRight,
  Clock,
  Eye,
  CheckCircle2,
  XCircle,
  Activity,
  Layers,
} from 'lucide-react';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { JsonViewer } from '../../components/ui/JsonViewer';

export const CognitiveTraceView: React.FC = () => {
  const { setWhyBlockedResult } = useCockpitStore();
  const [traces, setTraces] = useState<DecisionTrace[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<DecisionTrace | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    cockpitApi
      .getTraces(50)
      .then((data) => {
        setTraces(data);
        if (data.length > 0) setSelectedTrace(data[data.length - 1]);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-surface-400 font-mono text-sm">
        <span className="animate-pulse">Loading Cognitive Traces & Provenance DAG...</span>
      </div>
    );
  }

  const d = selectedTrace;

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-mono">
      {/* Header */}
      <div className="flex items-center justify-between bg-surface-900/90 p-4 rounded-xl border border-surface-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-purple-950 text-purple-400 border border-purple-800/50">
            <Terminal className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-surface-100 font-sans flex items-center gap-2">
              Cognitive Trace Viewer & Decision Provenance DAG
              <StatusBadge status="ACTIVE" />
            </h2>
            <p className="text-xs text-surface-400">
              Structured causal evidence: Observation → Belief → Plan → Policy → Decision → Action → Outcome (SAF-001).
            </p>
          </div>
        </div>

        <div className="text-right text-xs">
          <span className="text-surface-500 block">CAUSAL BOUNDARY</span>
          <span className="text-emerald-400 font-bold">Time t Strict Isolation</span>
        </div>
      </div>

      {/* Main Split: Trace List + Structured Provenance DAG */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left: Decision History List */}
        <div className="lg:col-span-4 bg-surface-900 rounded-xl border border-surface-800 overflow-hidden flex flex-col shadow-xl">
          <div className="px-4 py-3 bg-surface-950 border-b border-surface-800">
            <span className="text-xs font-bold text-surface-300 uppercase tracking-wider">
              Recorded Decisions ({traces.length})
            </span>
          </div>

          <div className="overflow-y-auto max-h-[640px] divide-y divide-surface-800/60">
            {traces.map((trace) => (
              <div
                key={trace.decision_id}
                onClick={() => setSelectedTrace(trace)}
                className={`p-3 hover:bg-surface-800/50 cursor-pointer transition-colors ${
                  selectedTrace?.decision_id === trace.decision_id ? 'bg-surface-800/80' : ''
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-surface-200">{trace.decision_id}</span>
                  <StatusBadge
                    status={trace.approved ? 'APPROVED' : 'BLOCKED'}
                    className="text-[10px]"
                  />
                </div>
                <div className="flex items-center justify-between text-[11px] text-surface-400">
                  <span>Entity: {trace.entity_id}</span>
                  <span>T+{trace.tick}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: The Structured Provenance DAG Pipeline */}
        <div className="lg:col-span-8 space-y-4">
          {d ? (
            <div className="bg-surface-900 rounded-xl border border-surface-800 p-5 shadow-xl space-y-4">
              <div className="flex items-center justify-between border-b border-surface-800 pb-3">
                <div>
                  <h3 className="text-sm font-bold text-surface-100 font-sans">
                    Decision Provenance Chain: {d.decision_id}
                  </h3>
                  <span className="text-xs text-surface-400">
                    Tick T+{d.tick} • Latency {d.latency_ms.toFixed(2)} ms • Confidence{' '}
                    {(d.confidence * 100).toFixed(1)}%
                  </span>
                </div>

                {!d.approved && (
                  <button
                    onClick={() =>
                      setWhyBlockedResult({
                        decision_id: d.decision_id,
                        entity_id: d.entity_id,
                        tick: d.tick,
                        intent: d.action?.intent || 'Engage simulated asset',
                        overall_outcome: 'REJECTED',
                        primary_block: {
                          policy_id: d.blocked_reason || 'SAF-003',
                          severity: 'HIGH',
                          reason: d.blocked_reason || 'Policy check failed',
                        },
                        gates: d.policy_checks.map((c) => ({
                          name: c.policy_id,
                          policy_id: c.policy_id,
                          passed: c.passed,
                          reason: c.reason,
                          severity: c.severity,
                        })),
                        required_remediation:
                          'Check the telemetry feed freshness or lease expiration for this agent.',
                      })
                    }
                    className="px-3 py-1.5 rounded-lg bg-rose-950 text-rose-300 border border-rose-800 text-xs font-bold hover:bg-rose-900 transition-colors"
                  >
                    Why Blocked? →
                  </button>
                )}
              </div>

              {/* DAG Nodes Stack */}
              <div className="space-y-2.5">
                {/* 1. OBSERVATION */}
                <div className="p-3 bg-surface-950 rounded-lg border border-surface-800">
                  <div className="flex items-center justify-between text-xs text-surface-400 mb-1">
                    <span className="font-bold text-surface-200">1. SENSOR OBSERVATIONS</span>
                    <span className="text-cyan-400">
                      {d.observations?.length || 1} observations fused
                    </span>
                  </div>
                  <p className="text-[11px] text-surface-400">
                    Timestamped measurements ingested under freshness horizon (&lt; 250ms).
                  </p>
                </div>

                <div className="flex justify-center text-surface-600">
                  <ArrowDown className="w-4 h-4" />
                </div>

                {/* 2. BELIEF */}
                <div className="p-3 bg-surface-950 rounded-lg border border-surface-800">
                  <div className="flex items-center justify-between text-xs text-surface-400 mb-1">
                    <span className="font-bold text-surface-200">2. BELIEF STATE (EPISTEMIC)</span>
                    <span className="text-cyan-400 font-bold">
                      Confidence: {(d.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                  <p className="text-[11px] text-surface-400">
                    Fused coordinate estimate with uncertainty bounds. Zero ground truth leakage
                    (SAF-001).
                  </p>
                </div>

                <div className="flex justify-center text-surface-600">
                  <ArrowDown className="w-4 h-4" />
                </div>

                {/* 3. PLAN */}
                <div className="p-3 bg-surface-950 rounded-lg border border-surface-800">
                  <div className="flex items-center justify-between text-xs text-surface-400 mb-1">
                    <span className="font-bold text-surface-200">3. GENERATED PLAN</span>
                    <span className="text-surface-300">Plan #{d.plan?.plan_id || 'P-441'}</span>
                  </div>
                  <p className="text-[11px] text-surface-400">
                    Proposed tactical course of action evaluated against kinodynamic limits.
                  </p>
                </div>

                <div className="flex justify-center text-surface-600">
                  <ArrowDown className="w-4 h-4" />
                </div>

                {/* 4. POLICY CHECK */}
                <div
                  className={`p-3 rounded-lg border ${
                    d.approved
                      ? 'bg-surface-950 border-emerald-900/50'
                      : 'bg-rose-950/40 border-rose-900/60'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-bold text-surface-200">4. POLICY & INVARIANT GATES</span>
                    <span className={d.approved ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                      {d.approved ? '✓ ALL GATES PASSED' : '✕ INVARIANT VIOLATION'}
                    </span>
                  </div>
                  <div className="space-y-1 mt-2">
                    {(d.policy_checks || []).map((chk, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between text-[11px] p-1 rounded bg-surface-900 border border-surface-800"
                      >
                        <span className="text-surface-300">{chk.policy_id}</span>
                        <span className={chk.passed ? 'text-emerald-400' : 'text-rose-400 font-bold'}>
                          {chk.passed ? '✓ PASSED' : `✕ BLOCKED: ${chk.reason}`}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex justify-center text-surface-600">
                  <ArrowDown className="w-4 h-4" />
                </div>

                {/* 5. ACTION & OUTCOME */}
                <div className="p-3 bg-surface-950 rounded-lg border border-surface-800">
                  <div className="flex items-center justify-between text-xs text-surface-400 mb-1">
                    <span className="font-bold text-surface-200">
                      5. SIMULATED EXECUTION (TIME t+1)
                    </span>
                    <span className={d.approved ? 'text-cyan-400 font-bold' : 'text-surface-500'}>
                      {d.approved ? 'Dispatched to World' : 'Blocked from Actuation'}
                    </span>
                  </div>
                  <p className="text-[11px] text-surface-400">
                    Action executed strictly in deterministic simulator environment.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-surface-500 text-xs bg-surface-900 rounded-xl border border-surface-800">
              Select a decision to inspect its structured provenance DAG.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Copyright (c) Ultrone Contributors. All rights reserved.
import React from 'react';
import { useCockpitStore } from '../../stores/cockpitStore';
import { ShieldX, CheckCircle2, XCircle, AlertOctagon, X, Wrench } from 'lucide-react';
import { StatusBadge } from './StatusBadge';

export const WhyBlockedModal: React.FC = () => {
  const { whyBlockedResult, setWhyBlockedResult } = useCockpitStore();

  if (!whyBlockedResult) return null;

  const { decision_id, entity_id, tick, intent, primary_block, gates, required_remediation } =
    whyBlockedResult;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-surface-900 border border-rose-900/50 rounded-xl max-w-2xl w-full shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-rose-950/40 border-b border-rose-900/40 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-rose-900/50 text-rose-400 border border-rose-700/50">
              <ShieldX className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-surface-100">Action Authorization Rejected</h2>
                <StatusBadge status="BLOCKED" />
              </div>
              <p className="text-xs font-mono text-surface-400">
                Decision: {decision_id} | Entity: {entity_id} | Tick: T+{tick}
              </p>
            </div>
          </div>
          <button
            onClick={() => setWhyBlockedResult(null)}
            className="p-1 rounded-lg text-surface-400 hover:text-surface-100 hover:bg-surface-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs font-mono">
          {/* Primary Rejection Banner */}
          <div className="p-4 rounded-lg bg-rose-950/60 border border-rose-800/60 flex items-start gap-3">
            <AlertOctagon className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
            <div>
              <div className="flex items-center gap-2 font-bold text-rose-300 text-sm">
                <span>REJECTED BY {primary_block.policy_id}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-rose-900/80 text-rose-200 uppercase font-sans">
                  {primary_block.severity}
                </span>
              </div>
              <p className="text-surface-300 mt-1 leading-relaxed">{primary_block.reason}</p>
              <p className="text-surface-400 text-[11px] mt-1">Proposed Intent: "{intent}"</p>
            </div>
          </div>

          {/* Policy Gates Chain */}
          <div>
            <h3 className="text-xs font-sans font-semibold text-surface-300 uppercase tracking-wider mb-2.5">
              Invariant & Policy Gate Evaluation Chain
            </h3>
            <div className="space-y-2">
              {gates.map((gate, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg border flex items-start justify-between gap-3 ${
                    gate.passed
                      ? 'bg-surface-950/60 border-surface-800 text-surface-300'
                      : 'bg-rose-950/40 border-rose-900/60 text-rose-300'
                  }`}
                >
                  <div className="flex items-start gap-2.5">
                    {gate.passed ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                    ) : (
                      <XCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                    )}
                    <div>
                      <div className="flex items-center gap-2 font-bold text-xs">
                        <span>{gate.name}</span>
                        <span className="text-[10px] text-surface-400">({gate.policy_id})</span>
                      </div>
                      <p className="text-[11px] text-surface-400 mt-0.5">{gate.reason}</p>
                    </div>
                  </div>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                      gate.passed
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                        : 'bg-rose-950 text-rose-400 border border-rose-800'
                    }`}
                  >
                    {gate.passed ? 'PASSED' : 'BLOCKED'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Remediation */}
          <div className="p-3.5 rounded-lg bg-surface-950 border border-surface-800 flex items-start gap-2.5">
            <Wrench className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <span className="text-surface-300 font-sans font-semibold text-xs block mb-1">
                Required Investigation & Remediation
              </span>
              <p className="text-surface-400 leading-relaxed">{required_remediation}</p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-surface-950 border-t border-surface-800 flex justify-end">
          <button
            onClick={() => setWhyBlockedResult(null)}
            className="px-4 py-1.5 bg-surface-800 hover:bg-surface-700 text-surface-200 text-xs font-semibold rounded-lg transition-colors"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
};

// Copyright (c) Ultrone Contributors. All rights reserved.
import React from 'react';
import { useCockpitStore } from '../../stores/cockpitStore';
import { ShieldCheck, ShieldAlert, X, Radio, Key, Cpu, FileCheck2 } from 'lucide-react';
import { StatusBadge } from './StatusBadge';

export const SystemTruthModal: React.FC = () => {
  const { systemTruthModalOpen, setSystemTruthModal, truth } = useCockpitStore();

  if (!systemTruthModalOpen || !truth) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div className="bg-surface-900 border border-surface-700 rounded-xl max-w-2xl w-full shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-surface-950 border-b border-surface-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="w-5 h-5 text-cyan-400" />
            <div>
              <h2 className="text-base font-bold text-surface-100 flex items-center gap-2">
                System Truth & Epistemic Boundaries
                <StatusBadge status="SIMULATION" />
              </h2>
              <p className="text-xs text-surface-400">
                Machine-verified runtime invariants and boundaries
              </p>
            </div>
          </div>
          <button
            onClick={() => setSystemTruthModal(false)}
            className="p-1 rounded-lg text-surface-400 hover:text-surface-100 hover:bg-surface-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Warning Banner */}
        <div className="px-6 py-2.5 bg-cyan-950/40 border-b border-cyan-800/30 flex items-center gap-2 text-cyan-300 text-xs font-mono">
          <Radio className="w-4 h-4 flex-shrink-0 animate-pulse text-cyan-400" />
          <span>SIMULATION MODE (NO PHYSICAL ACTUATION) — ZERO DIRECT HARDWARE AUTHORITY</span>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs font-mono">
          {/* Grid of truth items */}
          <div className="grid grid-cols-2 gap-3.5">
            <div className="bg-surface-950/70 p-3 rounded-lg border border-surface-800">
              <span className="text-surface-500 block text-[11px]">ENVIRONMENT MODE</span>
              <span className="text-cyan-400 font-bold text-sm">{truth.environment}</span>
            </div>

            <div className="bg-surface-950/70 p-3 rounded-lg border border-surface-800">
              <span className="text-surface-500 block text-[11px]">PHYSICAL ACTUATION</span>
              <span className="text-rose-400 font-bold text-sm">{truth.physical_actuation}</span>
            </div>

            <div className="bg-surface-950/70 p-3 rounded-lg border border-surface-800">
              <span className="text-surface-500 block text-[11px]">GROUND TRUTH VISIBILITY</span>
              <span className="text-amber-400 font-bold">{truth.ground_truth}</span>
            </div>

            <div className="bg-surface-950/70 p-3 rounded-lg border border-surface-800">
              <span className="text-surface-500 block text-[11px]">AGENT OBSERVATION</span>
              <span className="text-surface-200 font-bold">{truth.agent_observation}</span>
            </div>

            <div className="bg-surface-950/70 p-3 rounded-lg border border-surface-800">
              <span className="text-surface-500 block text-[11px]">MODEL & POLICY CONTRACT</span>
              <span className="text-surface-200 font-bold">
                {truth.model_version} / {truth.policy_version}
              </span>
            </div>

            <div className="bg-surface-950/70 p-3 rounded-lg border border-surface-800">
              <span className="text-surface-500 block text-[11px]">MCP WIRE PROTOCOL</span>
              <span className="text-cyan-400 font-bold">{truth.mcp_protocol}</span>
            </div>

            <div className="bg-surface-950/70 p-3 rounded-lg border border-surface-800">
              <span className="text-surface-500 block text-[11px]">EVENT CHAIN INTEGRITY</span>
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                <FileCheck2 className="w-3.5 h-3.5" />
                {truth.event_chain} ({truth.event_count} events)
              </span>
            </div>

            <div className="bg-surface-950/70 p-3 rounded-lg border border-surface-800">
              <span className="text-surface-500 block text-[11px]">AUDIT CHECKPOINT</span>
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                <Key className="w-3.5 h-3.5" />
                Ed25519 {truth.latest_checkpoint}
              </span>
            </div>
          </div>

          {/* Core Architectural Notes */}
          <div className="bg-surface-950 p-4 rounded-lg border border-surface-800 space-y-2">
            <span className="text-surface-400 font-sans font-semibold text-xs flex items-center gap-1.5">
              <ShieldAlert className="w-4 h-4 text-cyan-400" />
              Machine-Enforced Invariants
            </span>
            <ul className="space-y-1.5 text-surface-400 text-xs pl-4 list-disc">
              {truth.notes.map((note, idx) => (
                <li key={idx}>{note}</li>
              ))}
              <li>
                Freshness horizon: Telemetry older than {truth.freshness_horizon_ms} ms triggers
                automatic SAF-003 rejection.
              </li>
            </ul>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-surface-950 border-t border-surface-800 flex justify-end">
          <button
            onClick={() => setSystemTruthModal(false)}
            className="px-4 py-1.5 bg-surface-800 hover:bg-surface-700 text-surface-200 text-xs font-semibold rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

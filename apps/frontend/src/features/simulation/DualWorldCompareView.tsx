// Copyright (c) Ultrone Contributors. All rights reserved.
import React from 'react';
import { useCockpitStore } from '../../stores/cockpitStore';
import { Share2, AlertTriangle, CheckCircle2, XCircle, ArrowRight, ShieldCheck } from 'lucide-react';
import { StatusBadge } from '../../components/ui/StatusBadge';

export const DualWorldCompareView: React.FC = () => {
  const { world, inspect, overview } = useCockpitStore();

  const comparison = world?.comparison || [];
  const horizonMs = world?.freshness_horizon_ms || 250;

  return (
    <div className="space-y-5 max-w-7xl mx-auto font-mono">
      {/* Header */}
      <div className="flex items-center justify-between bg-surface-900/90 p-4 rounded-xl border border-surface-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-cyan-950 text-cyan-400 border border-cyan-800/50">
            <Share2 className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-surface-100 font-sans flex items-center gap-2">
              Dual-View: Ground Truth vs. Agent Belief
              <StatusBadge status="SIMULATION" />
            </h2>
            <p className="text-xs text-surface-400">
              Causal epistemic boundary validation: compare actual simulator coordinates against agent estimates.
            </p>
          </div>
        </div>

        <div className="text-right text-xs">
          <span className="text-surface-500 block">FRESHNESS HORIZON</span>
          <span className="text-emerald-400 font-bold">&lt; {horizonMs} ms</span>
        </div>
      </div>

      {/* Discrepancy Matrix Table */}
      <div className="bg-surface-900 rounded-xl border border-surface-800 overflow-hidden shadow-xl">
        <div className="px-4 py-3 bg-surface-950 border-b border-surface-800 flex items-center justify-between">
          <span className="text-xs font-bold text-surface-300 uppercase tracking-wider">
            Entity Discrepancy & Provenance Ledger ({comparison.length} tracks)
          </span>
          <span className="text-[11px] text-surface-500">
            Click any row to inspect structured confidence provenance
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-surface-800 bg-surface-950/60 text-surface-400 text-[11px]">
                <th className="py-2.5 px-4">ENTITY</th>
                <th className="py-2.5 px-4">GROUND TRUTH (X, Y)</th>
                <th className="py-2.5 px-4">AGENT BELIEF (X, Y)</th>
                <th className="py-2.5 px-4">ERROR DELTA</th>
                <th className="py-2.5 px-4">CONFIDENCE</th>
                <th className="py-2.5 px-4">AGE / HORIZON</th>
                <th className="py-2.5 px-4">STATUS</th>
                <th className="py-2.5 px-4 text-right">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-800/60">
              {comparison.map((item) => {
                const isStale = (item.age_ms || 0) > horizonMs;
                const isDiverged = (item.error_km || 0) > 1.0;

                return (
                  <tr
                    key={item.entity_id}
                    onClick={() => inspect('agent', item.entity_id, item)}
                    className="hover:bg-surface-800/50 cursor-pointer transition-colors"
                  >
                    <td className="py-3 px-4">
                      <div className="font-bold text-surface-200">{item.label}</div>
                      <div className="text-[10px] text-surface-500 uppercase">{item.kind}</div>
                    </td>

                    <td className="py-3 px-4 font-mono text-surface-300">
                      [{item.ground_truth[0].toFixed(2)}, {item.ground_truth[1].toFixed(2)}] km
                    </td>

                    <td className="py-3 px-4 font-mono text-cyan-300">
                      {item.belief
                        ? `[${item.belief[0].toFixed(2)}, ${item.belief[1].toFixed(2)}] km`
                        : 'Unobserved'}
                    </td>

                    <td className="py-3 px-4 font-mono">
                      {item.error_km !== null ? (
                        <span
                          className={
                            isDiverged ? 'text-amber-400 font-bold' : 'text-surface-300'
                          }
                        >
                          Δ {item.error_km.toFixed(3)} km
                        </span>
                      ) : (
                        <span className="text-surface-600">—</span>
                      )}
                    </td>

                    <td className="py-3 px-4 font-mono">
                      {item.confidence !== null ? (
                        <span className="text-cyan-400 font-bold">
                          {(item.confidence * 100).toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-surface-600">—</span>
                      )}
                    </td>

                    <td className="py-3 px-4 font-mono">
                      {item.age_ms !== null ? (
                        <span className={isStale ? 'text-rose-400 font-bold' : 'text-emerald-400'}>
                          {item.age_ms.toFixed(0)} ms
                        </span>
                      ) : (
                        <span className="text-surface-600">—</span>
                      )}
                    </td>

                    <td className="py-3 px-4">
                      {isStale ? (
                        <StatusBadge status="DEGRADED" className="text-[10px]" />
                      ) : (
                        <StatusBadge status="READY" className="text-[10px]" />
                      )}
                    </td>

                    <td className="py-3 px-4 text-right">
                      <button className="text-xs text-cyan-400 hover:text-cyan-300 inline-flex items-center gap-1">
                        <span>Inspect</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

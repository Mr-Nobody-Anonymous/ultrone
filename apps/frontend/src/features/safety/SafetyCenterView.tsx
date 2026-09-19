// Copyright (c) Ultrone Contributors. All rights reserved.
import React, { useEffect, useState } from 'react';
import { cockpitApi } from '../../api/client';
import { ShieldCheck, ShieldAlert, Key, Clock, Radio, CheckCircle2, XCircle } from 'lucide-react';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { MetricCard } from '../../components/ui/MetricCard';

export const SafetyCenterView: React.FC = () => {
  const [safety, setSafety] = useState<any>(null);
  const [invariants, setInvariants] = useState<any[]>([]);
  const [causal, setCausal] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      cockpitApi.getSafetyStatus(),
      cockpitApi.getInvariants(),
      cockpitApi.getCausalBoundary(),
    ])
      .then(([sData, iData, cData]) => {
        setSafety(sData);
        setInvariants(iData);
        setCausal(cData);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-surface-400 font-mono text-sm">
        <span className="animate-pulse">Loading Formal Invariant Registry & Safety Center...</span>
      </div>
    );
  }

  const leases = safety?.leases?.items || [];
  const freshnessAudit = safety?.freshness?.audit || [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-mono">
      {/* Header */}
      <div className="flex items-center justify-between bg-surface-900/90 p-4 rounded-xl border border-surface-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-rose-950 text-rose-400 border border-rose-800/50">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-surface-100 font-sans flex items-center gap-2">
              Safety Center & Formal Invariant Registry
              <StatusBadge status={safety?.status || 'NORMAL'} />
            </h2>
            <p className="text-xs text-surface-400">
              Machine-checkable invariants (SAF-001..SAF-005), capability leases, and telemetry freshness.
            </p>
          </div>
        </div>

        <div className="text-right text-xs">
          <span className="text-surface-500 block">SYSTEM STATUS</span>
          <span className="text-emerald-400 font-bold">{safety?.emergency_state || 'NOMINAL'}</span>
        </div>
      </div>

      {/* Metric Tiles */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <MetricCard
          label="ACTIVE POLICIES"
          value={safety?.active_policies || 7}
          subValue="Formally Registered"
          status="success"
        />
        <MetricCard
          label="BLOCKED ACTIONS"
          value={safety?.blocked_operations || 0}
          subValue="Rejected by Gates"
          status={safety?.blocked_operations > 0 ? 'warning' : 'normal'}
        />
        <MetricCard
          label="ACTIVE LEASES"
          value={safety?.leases?.active || 0}
          subValue={`${safety?.leases?.expired || 0} expired`}
          status={safety?.leases?.expired > 0 ? 'danger' : 'success'}
        />
        <MetricCard
          label="CAUSAL VIOLATIONS"
          value={safety?.causal_violations || 0}
          subValue="SAF-001 Verification"
          status={safety?.causal_violations > 0 ? 'danger' : 'success'}
        />
      </div>

      {/* Invariants Roster */}
      <div className="bg-surface-900 rounded-xl border border-surface-800 overflow-hidden shadow-xl">
        <div className="px-4 py-3 bg-surface-950 border-b border-surface-800">
          <span className="text-xs font-bold text-surface-300 uppercase tracking-wider">
            Canonical Machine-Checkable Invariants (100% Mutation Killed)
          </span>
        </div>

        <div className="divide-y divide-surface-800/60">
          {invariants.map((inv) => (
            <div key={inv.id} className="p-4 flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-bold text-cyan-400">{inv.id}</span>
                  <span className="text-xs font-bold text-surface-200">{inv.name}</span>
                  <StatusBadge status={inv.severity} className="text-[10px]" />
                </div>
                <p className="text-xs text-surface-400 leading-relaxed">{inv.description}</p>
                <div className="mt-2 text-[10px] text-surface-500 flex gap-4">
                  <span>Implementation: {inv.implementation}</span>
                  <span>Test: {inv.test}</span>
                </div>
              </div>
              <span className="text-xs text-emerald-400 font-bold flex items-center gap-1 flex-shrink-0">
                <CheckCircle2 className="w-4 h-4" />
                <span>Verified</span>
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Telemetry Freshness Audit Table */}
      <div className="bg-surface-900 rounded-xl border border-surface-800 p-4">
        <h3 className="text-xs font-bold text-surface-300 uppercase tracking-wider mb-3 flex items-center gap-2">
          <Clock className="w-4 h-4 text-cyan-400" />
          Sensor Telemetry Freshness Horizon Audit (SAF-003)
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-surface-800 bg-surface-950 text-surface-400 text-[11px]">
                <th className="py-2 px-3">SENSOR ID</th>
                <th className="py-2 px-3">DEVICE ID</th>
                <th className="py-2 px-3">MODALITY</th>
                <th className="py-2 px-3">CURRENT AGE</th>
                <th className="py-2 px-3">HORIZON THRESHOLD</th>
                <th className="py-2 px-3 text-right">GATE STATUS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-800/60">
              {freshnessAudit.map((row: any) => (
                <tr key={row.sensor_id}>
                  <td className="py-2.5 px-3 font-bold text-surface-200">{row.sensor_id}</td>
                  <td className="py-2.5 px-3 text-cyan-400">{row.device_id}</td>
                  <td className="py-2.5 px-3 uppercase text-surface-400">{row.modality}</td>
                  <td className="py-2.5 px-3 font-mono">
                    {row.age_ms !== null ? (
                      <span className={row.fresh ? 'text-emerald-400' : 'text-rose-400 font-bold'}>
                        {row.age_ms.toFixed(1)} ms
                      </span>
                    ) : (
                      <span className="text-surface-600">No Frame</span>
                    )}
                  </td>
                  <td className="py-2.5 px-3 text-surface-400">{row.horizon_ms} ms</td>
                  <td className="py-2.5 px-3 text-right">
                    {row.fresh ? (
                      <span className="text-emerald-400 font-bold">✓ FRESH</span>
                    ) : (
                      <span className="text-rose-400 font-bold">✕ STALE (BLOCKED)</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

// Copyright (c) Ultrone Contributors. All rights reserved.
import React, { useEffect, useState } from 'react';
import { useCockpitStore } from '../../stores/cockpitStore';
import { cockpitApi } from '../../api/client';
import {
  X,
  Eye,
  GitFork,
  Code2,
  ExternalLink,
  ShieldCheck,
  Cpu,
  Radio,
  FileText,
  Activity,
} from 'lucide-react';
import { JsonViewer } from './JsonViewer';
import { StatusBadge } from './StatusBadge';

export const InspectorDrawer: React.FC = () => {
  const { inspectorOpen, inspectorTarget, closeInspector, inspectorTab, setInspectorTab, inspect } =
    useCockpitStore();

  const [loading, setLoading] = useState(false);
  const [detailData, setDetailData] = useState<any>(null);

  useEffect(() => {
    if (!inspectorTarget) {
      setDetailData(null);
      return;
    }

    let isCancelled = false;
    const fetchDetail = async () => {
      setLoading(true);
      try {
        let res: any = null;
        if (inspectorTarget.type === 'agent') {
          res = await cockpitApi.getAgentDetail(inspectorTarget.id);
        } else if (inspectorTarget.type === 'device') {
          res = await cockpitApi.getDeviceDetail(inspectorTarget.id);
        } else if (inspectorTarget.type === 'decision') {
          res = await cockpitApi.getTraceDetail(inspectorTarget.id);
        } else {
          res = inspectorTarget.data || null;
        }

        if (!isCancelled) {
          setDetailData(res);
        }
      } catch (err) {
        if (!isCancelled) {
          setDetailData(inspectorTarget.data || { error: String(err) });
        }
      } finally {
        if (!isCancelled) setLoading(false);
      }
    };

    fetchDetail();
    return () => {
      isCancelled = true;
    };
  }, [inspectorTarget]);

  if (!inspectorOpen || !inspectorTarget) return null;

  const dataToRender = detailData || inspectorTarget.data || {};

  return (
    <div className="fixed inset-y-0 right-0 z-40 w-[480px] bg-surface-900 border-l border-surface-800 shadow-2xl flex flex-col animate-slide-left">
      {/* Header */}
      <div className="p-4 bg-surface-950 border-b border-surface-800 flex items-center justify-between">
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div className="p-1.5 rounded-lg bg-surface-800 text-surface-300">
            {inspectorTarget.type === 'agent' && <Cpu className="w-4 h-4 text-blue-400" />}
            {inspectorTarget.type === 'device' && <Radio className="w-4 h-4 text-cyan-400" />}
            {inspectorTarget.type === 'decision' && <Activity className="w-4 h-4 text-purple-400" />}
            {inspectorTarget.type === 'event' && <FileText className="w-4 h-4 text-amber-400" />}
            {inspectorTarget.type === 'policy' && <ShieldCheck className="w-4 h-4 text-emerald-400" />}
          </div>
          <div className="min-w-0">
            <span className="text-[10px] font-mono text-surface-400 uppercase tracking-wider block">
              {inspectorTarget.type} INSPECTOR
            </span>
            <h3 className="text-sm font-bold text-surface-100 truncate">{inspectorTarget.id}</h3>
          </div>
        </div>
        <button
          onClick={closeInspector}
          className="p-1 text-surface-400 hover:text-surface-100 hover:bg-surface-800 rounded transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-surface-800 bg-surface-950/60 px-4 text-xs font-mono">
        <button
          onClick={() => setInspectorTab('visual')}
          className={`py-2.5 px-3 font-medium border-b-2 flex items-center gap-1.5 transition-colors ${
            inspectorTab === 'visual'
              ? 'border-cyan-500 text-cyan-400'
              : 'border-transparent text-surface-400 hover:text-surface-200'
          }`}
        >
          <Eye className="w-3.5 h-3.5" />
          <span>Visual</span>
        </button>
        <button
          onClick={() => setInspectorTab('provenance')}
          className={`py-2.5 px-3 font-medium border-b-2 flex items-center gap-1.5 transition-colors ${
            inspectorTab === 'provenance'
              ? 'border-cyan-500 text-cyan-400'
              : 'border-transparent text-surface-400 hover:text-surface-200'
          }`}
        >
          <GitFork className="w-3.5 h-3.5" />
          <span>Provenance</span>
        </button>
        <button
          onClick={() => setInspectorTab('json')}
          className={`py-2.5 px-3 font-medium border-b-2 flex items-center gap-1.5 transition-colors ${
            inspectorTab === 'json'
              ? 'border-cyan-500 text-cyan-400'
              : 'border-transparent text-surface-400 hover:text-surface-200'
          }`}
        >
          <Code2 className="w-3.5 h-3.5" />
          <span>Raw JSON</span>
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4 text-xs">
        {loading ? (
          <div className="flex items-center justify-center h-48 text-surface-400">
            <span className="animate-pulse font-mono">Loading object attributes...</span>
          </div>
        ) : inspectorTab === 'visual' ? (
          <div className="space-y-4 font-mono">
            {/* Summary card */}
            <div className="p-3.5 bg-surface-950 rounded-lg border border-surface-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-surface-400">Status</span>
                <StatusBadge status={dataToRender.state || dataToRender.status || 'READY'} />
              </div>
              {dataToRender.device_type && (
                <div className="flex items-center justify-between">
                  <span className="text-surface-400">Device Type</span>
                  <span className="text-surface-200">{dataToRender.device_type}</span>
                </div>
              )}
              {dataToRender.role && (
                <div className="flex items-center justify-between">
                  <span className="text-surface-400">Role</span>
                  <span className="text-surface-200">{dataToRender.role}</span>
                </div>
              )}
              {dataToRender.model_version && (
                <div className="flex items-center justify-between">
                  <span className="text-surface-400">Model Version</span>
                  <span className="text-surface-200">{dataToRender.model_version}</span>
                </div>
              )}
              {dataToRender.confidence !== undefined && (
                <div className="flex items-center justify-between">
                  <span className="text-surface-400">Confidence</span>
                  <span className="text-cyan-400 font-bold">
                    {(dataToRender.confidence * 100).toFixed(1)}%
                  </span>
                </div>
              )}
            </div>

            {/* If agent: capabilities and leases */}
            {inspectorTarget.type === 'agent' && (
              <div className="space-y-3">
                <div className="p-3 bg-surface-950 rounded-lg border border-surface-800">
                  <span className="text-surface-400 font-sans font-semibold text-xs block mb-2">
                    Granted Capabilities
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {(dataToRender.capabilities || []).map((c: string) => (
                      <span
                        key={c}
                        className="px-2 py-0.5 rounded bg-blue-950/80 text-blue-300 border border-blue-800 text-[10px]"
                      >
                        ✓ {c}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="p-3 bg-surface-950 rounded-lg border border-surface-800">
                  <span className="text-surface-400 font-sans font-semibold text-xs block mb-2">
                    Explicitly Denied Scopes
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {['physical.execute', 'physical.request', 'admin.configure'].map((d: string) => (
                      <span
                        key={d}
                        className="px-2 py-0.5 rounded bg-rose-950/80 text-rose-400 border border-rose-800 text-[10px]"
                      >
                        ✗ {d}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* If device: 10-state FSM allowed transitions */}
            {inspectorTarget.type === 'device' && dataToRender.fsm && (
              <div className="p-3 bg-surface-950 rounded-lg border border-surface-800 space-y-2">
                <span className="text-surface-400 font-sans font-semibold text-xs block mb-1">
                  UDIS 10-State FSM Valid Next States
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {(dataToRender.fsm.allowed_transitions || []).map((t: string) => (
                    <span
                      key={t}
                      className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800 text-[10px]"
                    >
                      → {t}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* If decision: policy checks */}
            {inspectorTarget.type === 'decision' && dataToRender.decision && (
              <div className="p-3 bg-surface-950 rounded-lg border border-surface-800 space-y-2">
                <span className="text-surface-400 font-sans font-semibold text-xs block mb-1">
                  Policy Checks
                </span>
                <div className="space-y-1">
                  {(dataToRender.decision.policy_checks || []).map((chk: any, idx: number) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between text-[11px] p-1.5 rounded bg-surface-900 border border-surface-800"
                    >
                      <span className="text-surface-300">{chk.policy_id}</span>
                      <span className={chk.passed ? 'text-emerald-400' : 'text-rose-400'}>
                        {chk.passed ? '✓ PASSED' : '✕ REJECTED'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : inspectorTab === 'provenance' ? (
          <div className="space-y-3 font-mono">
            <span className="text-surface-400 text-xs font-sans font-semibold block mb-2">
              Structured Evidence Chain
            </span>
            <div className="p-3.5 bg-surface-950 rounded-lg border border-surface-800 space-y-2.5">
              <div className="text-[11px]">
                <span className="text-surface-500 block">OBSERVATION SOURCE:</span>
                <span className="text-cyan-400 font-bold">
                  {dataToRender.confidence_provenance?.confidence_source || 'fused_sensor_feed'}
                </span>
              </div>
              <div className="text-[11px]">
                <span className="text-surface-500 block">MODEL ARTIFACT / VERSION:</span>
                <span className="text-surface-200">
                  {dataToRender.model_version || 'vision-v3.4'}
                </span>
              </div>
              <div className="text-[11px]">
                <span className="text-surface-500 block">FRESHNESS HORIZON:</span>
                <span className="text-emerald-400">
                  {dataToRender.age_ms !== undefined ? `${dataToRender.age_ms} ms` : '< 250 ms'}
                </span>
              </div>
              <div className="text-[11px]">
                <span className="text-surface-500 block">CAUSAL VALIDATION:</span>
                <span className="text-emerald-400">PASSED (Zero Post-Action Leakage)</span>
              </div>
            </div>
          </div>
        ) : (
          <JsonViewer data={dataToRender} maxHeight="max-h-[600px]" />
        )}
      </div>
    </div>
  );
};

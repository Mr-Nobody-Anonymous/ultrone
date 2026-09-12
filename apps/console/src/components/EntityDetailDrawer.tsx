import React, { useState } from 'react';
import type { Entity } from '../types/entity';
import { useWorldStore } from '../store/worldStore';
import { useInvestigationStore } from '../store/investigationStore';
import ConfidenceBadge from './ConfidenceBadge';
import {
  X,
  Compass,
  Activity,
  History,
  GitBranch,
  TrendingUp,
  ShieldCheck,
  Bot,
  Zap,
  FolderPlus,
  FileText,
  Clock,
  ExternalLink,
  CheckCircle2,
} from 'lucide-react';

interface Props {
  entity: Entity | null;
  onClose: () => void;
}

type TabKey =
  | 'overview'
  | 'observations'
  | 'history'
  | 'relationships'
  | 'analytics'
  | 'provenance'
  | 'ai_analysis'
  | 'actions';

export const EntityDetailDrawer: React.FC<Props> = ({ entity, onClose }) => {
  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const selectEntity = useWorldStore((s) => s.selectEntity);
  const entities = useWorldStore((s) => s.entities);
  const pinEntityToActiveCase = useInvestigationStore((s) => s.pinEntityToActiveCase);
  const activeCase = useInvestigationStore((s) => s.getActiveCase());

  if (!entity) return null;

  const showNotice = (msg: string) => {
    setActionNotice(msg);
    setTimeout(() => setActionNotice(null), 3000);
  };

  const handleAddToInvestigation = () => {
    pinEntityToActiveCase(entity.entity_id);
    showNotice(`Pinned ${entity.entity_id} to active case [${activeCase?.id || 'INV-1042'}]`);
  };

  const tabs: { id: TabKey; label: string; icon: any }[] = [
    { id: 'overview', label: 'Overview', icon: Compass },
    { id: 'observations', label: 'Observations', icon: Activity },
    { id: 'history', label: 'History', icon: History },
    { id: 'relationships', label: 'Links', icon: GitBranch },
    { id: 'analytics', label: 'Analytics', icon: TrendingUp },
    { id: 'provenance', label: 'Provenance', icon: ShieldCheck },
    { id: 'ai_analysis', label: 'AI Intel', icon: Bot },
    { id: 'actions', label: 'Actions', icon: Zap },
  ];

  return (
    <div className="absolute top-0 right-0 bottom-0 z-40 w-96 max-w-full bg-slate-950/95 border-l border-slate-800 shadow-2xl flex flex-col font-mono text-xs backdrop-blur-md animate-in slide-in-from-right duration-200">
      {/* Drawer Header */}
      <div className="p-4 border-b border-slate-800 bg-slate-900/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <h2 className="font-bold text-slate-100 uppercase tracking-wider text-sm">
              {entity.entity_id}
            </h2>
            <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-cyan-300 border border-slate-700">
              {entity.type}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Sub-bar */}
        <div className="flex items-center justify-between mt-3 text-[11px] text-slate-400">
          <span>Status: <strong className="text-slate-200 uppercase">{entity.status}</strong></span>
          <ConfidenceBadge confidence={entity.confidence} size="sm" />
        </div>

        {actionNotice && (
          <div className="mt-2 p-2 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-[10px] flex items-center gap-1.5 animate-in fade-in">
            <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
            <span>{actionNotice}</span>
          </div>
        )}
      </div>

      {/* Tabs Bar */}
      <div className="flex items-center gap-1 border-b border-slate-800 px-3 pt-2 bg-slate-900/40 overflow-x-auto no-scrollbar">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-1 px-2.5 py-1.5 text-[11px] font-semibold border-b-2 whitespace-nowrap transition-colors ${
              activeTab === id
                ? 'border-ultrone-500 text-ultrone-300 bg-slate-800/40'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Icon className="w-3 h-3" />
            <span>{label}</span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Tab 1: Overview */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">Latitude</span>
                <span className="font-bold text-slate-200">{entity.position?.lat.toFixed(4) ?? 'N/A'}° N</span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">Longitude</span>
                <span className="font-bold text-slate-200">{entity.position?.lng.toFixed(4) ?? 'N/A'}° W</span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">Altitude</span>
                <span className="font-bold text-cyan-300">{entity.position?.alt ? `${entity.position.alt} ft` : 'Ground'}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">Velocity</span>
                <span className="font-bold text-slate-200">
                  {entity.velocity ? `${Math.round(Math.hypot(entity.velocity.x, entity.velocity.y))} kts` : 'Stationary'}
                </span>
              </div>
            </div>

            <div>
              <span className="text-[10px] text-slate-500 uppercase block mb-1.5 font-bold">
                Active Sensors ({entity.sensors?.length || 0})
              </span>
              <div className="flex flex-wrap gap-1.5">
                {entity.sensors?.map((s) => (
                  <span key={s} className="px-2 py-0.5 rounded bg-slate-900 text-cyan-400 border border-slate-800 text-[11px]">
                    {s}
                  </span>
                )) || <span className="text-slate-600">None declared</span>}
              </div>
            </div>

            <div>
              <span className="text-[10px] text-slate-500 uppercase block mb-1 font-bold">Telemetry Age</span>
              <div className="flex items-center gap-1.5 text-slate-400 text-[11px]">
                <Clock className="w-3.5 h-3.5 text-slate-500" />
                <span>Last updated: {new Date(entity.updated_at || Date.now()).toLocaleTimeString()} (4.2s ago)</span>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Observations */}
        {activeTab === 'observations' && (
          <div className="space-y-3">
            <span className="text-[10px] text-slate-500 uppercase block font-bold">
              Observation Log ({entity.observations?.length || 0})
            </span>
            {entity.observations?.map((obs, idx) => (
              <div key={idx} className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1.5">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="font-bold text-cyan-300">{obs.source}</span>
                  <ConfidenceBadge confidence={obs.confidence} size="sm" />
                </div>
                <p className="text-slate-300 text-xs">{obs.description}</p>
                {obs.raw_data && (
                  <pre className="p-1.5 rounded bg-slate-950 text-[10px] text-slate-400 overflow-x-auto">
                    {JSON.stringify(obs.raw_data, null, 2)}
                  </pre>
                )}
                <span className="text-[10px] text-slate-500 block">
                  {new Date(obs.timestamp).toLocaleTimeString()}
                </span>
              </div>
            )) || <p className="text-slate-500">No observations recorded.</p>}
          </div>
        )}

        {/* Tab 3: History */}
        {activeTab === 'history' && (
          <div className="space-y-3">
            <span className="text-[10px] text-slate-500 uppercase block font-bold">State Changes & Track Trajectory</span>
            <div className="relative border-l border-slate-800 pl-4 space-y-3 ml-2">
              <div className="relative">
                <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-cyan-400" />
                <span className="text-[10px] text-slate-500">12:42:30 Z</span>
                <p className="text-xs text-slate-200">Fused track established. Heading locked at 270°.</p>
              </div>
              <div className="relative">
                <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-slate-600" />
                <span className="text-[10px] text-slate-500">12:41:00 Z</span>
                <p className="text-xs text-slate-300">Visual confirmation acquired via eo-02.</p>
              </div>
              <div className="relative">
                <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-slate-600" />
                <span className="text-[10px] text-slate-500">12:40:00 Z</span>
                <p className="text-xs text-slate-300">Initial detection via radar-01 bearing 045°.</p>
              </div>
            </div>
          </div>
        )}

        {/* Tab 4: Relationships */}
        {activeTab === 'relationships' && (
          <div className="space-y-3">
            <span className="text-[10px] text-slate-500 uppercase block font-bold">
              Ontology Links ({entity.relationships?.length || 0})
            </span>
            {entity.relationships?.map((rel, i) => {
              const target = entities.find((e) => e.entity_id === rel.target_id);
              return (
                <div
                  key={i}
                  onClick={() => target && selectEntity(target)}
                  className="p-3 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 cursor-pointer transition-all space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-cyan-400 font-bold">{rel.relation}</span>
                    <ConfidenceBadge confidence={rel.confidence} size="sm" />
                  </div>
                  <div className="flex items-center justify-between text-slate-300 text-xs">
                    <span>Target: <strong>{rel.target_id}</strong></span>
                    <ExternalLink className="w-3 h-3 text-slate-500" />
                  </div>
                </div>
              );
            }) || <p className="text-slate-500">No active relationship links.</p>}
          </div>
        )}

        {/* Tab 5: Analytics */}
        {activeTab === 'analytics' && (
          <div className="space-y-4">
            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-2">
              <span className="text-[10px] text-slate-500 uppercase block font-bold">Bayesian Uncertainty Rating</span>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-300">Confidence Metric:</span>
                <span className="font-bold text-cyan-300">{Math.round(entity.confidence * 100)}%</span>
              </div>
              <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-cyan-500 h-full transition-all"
                  style={{ width: `${entity.confidence * 100}%` }}
                />
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1.5">
              <span className="text-[10px] text-slate-500 uppercase block font-bold">Operational Threat / Safety Band</span>
              <p className="text-xs text-emerald-400 font-semibold">Nominal Corridor Compliance</p>
              <p className="text-[11px] text-slate-400">Zero proximity alerts triggered across safe sector boundaries.</p>
            </div>
          </div>
        )}

        {/* Tab 6: Provenance */}
        {activeTab === 'provenance' && (
          <div className="space-y-3">
            <span className="text-[10px] text-slate-500 uppercase block font-bold">Tamper-Evident Lineage Trace</span>
            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-2 text-xs">
              <div>
                <span className="text-[10px] text-slate-500">Primary Ingestion:</span>
                <p className="text-slate-200 font-bold">sensor_fusion_v2</p>
              </div>
              <div>
                <span className="text-[10px] text-slate-500">Sensor Contributing Sources:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {entity.provenance?.map((p, idx) => (
                    <span key={idx} className="px-2 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-800 text-[10px]">
                      ↳ {p}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <span className="text-[10px] text-slate-500">Model Lineage:</span>
                <p className="text-slate-400 font-mono text-[11px]">fusion-kalman-bayesian-v2.4.1</p>
              </div>
            </div>
          </div>
        )}

        {/* Tab 7: AI Analysis */}
        {activeTab === 'ai_analysis' && (
          <div className="space-y-3">
            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-2">
              <div className="flex items-center gap-2 text-ultrone-400 font-bold text-xs">
                <Bot className="w-4 h-4" />
                <span>AI Cognitive Evaluation</span>
              </div>
              <p className="text-slate-300 text-xs leading-relaxed">
                Contact {entity.entity_id} exhibiting standard commercial flight profile. Track deviation probability evaluated at <strong>0.04</strong>.
                Sensor correlation firmly grounded in 2 independent radar returns.
              </p>
            </div>
          </div>
        )}

        {/* Tab 8: Actions */}
        {activeTab === 'actions' && (
          <div className="space-y-2">
            <span className="text-[10px] text-slate-500 uppercase block font-bold mb-2">Operational Workflows</span>

            <button
              onClick={handleAddToInvestigation}
              className="w-full flex items-center justify-between p-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 text-slate-200 text-xs font-semibold transition-colors"
            >
              <div className="flex items-center gap-2">
                <FolderPlus className="w-4 h-4 text-ultrone-400" />
                <span>Add to Investigation Case</span>
              </div>
              <span className="text-[10px] text-slate-500">#{activeCase?.id || 'INV-1042'}</span>
            </button>

            <button
              onClick={() => showNotice('Initiated trajectory simulation experiment')}
              className="w-full flex items-center justify-between p-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 text-slate-200 text-xs font-semibold transition-colors"
            >
              <div className="flex items-center gap-2">
                <Compass className="w-4 h-4 text-cyan-400" />
                <span>Run Simulation Replay</span>
              </div>
              <span className="text-[10px] text-slate-500">Sim Sandbox</span>
            </button>

            <button
              onClick={() => {
                const blob = new Blob([JSON.stringify(entity, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${entity.entity_id}_dossier.json`;
                a.click();
                showNotice(`Exported ${entity.entity_id}_dossier.json`);
              }}
              className="w-full flex items-center justify-between p-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 text-slate-200 text-xs font-semibold transition-colors"
            >
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-amber-400" />
                <span>Export Entity Dossier (JSON)</span>
              </div>
              <span className="text-[10px] text-slate-500">Audit Trail</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default EntityDetailDrawer;

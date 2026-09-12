import React from 'react';
import { useWorldStore } from '../store/worldStore';
import { useInvestigationStore } from '../store/investigationStore';
import { useUIStore } from '../store/uiStore';
import {
  Shield,
  Activity,
  AlertTriangle,
  Radio,
  Compass,
  Cpu,
  ArrowRight,
  Sparkles,
  Layers,
  FolderLock,
} from 'lucide-react';

export const OverviewView: React.FC = () => {
  const entities = useWorldStore((s) => s.entities);
  const events = useWorldStore((s) => s.events);
  const cases = useInvestigationStore((s) => s.cases);
  const setView = useUIStore((s) => s.setActiveView);

  const activeSensors = entities.filter((e) => e.type === 'sensor').length;
  const airAssets = entities.filter((e) => e.type === 'air_asset').length;
  const groundVehicles = entities.filter((e) => e.type === 'ground_vehicle').length;
  const anomalies = events.filter((e) => e.type === 'ANOMALY_DETECTED');

  return (
    <div className="flex h-full w-full flex-col bg-slate-950 p-6 overflow-y-auto space-y-6 font-mono select-none">
      {/* Top Banner: Mission Command Posture */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-ultrone-600/20 border border-ultrone-500/40 text-ultrone-400 shadow-md">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-wider text-slate-100 uppercase flex items-center gap-2">
                ULTRONE Operational Posture
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                  SYSTEM READY
                </span>
              </h1>
              <p className="text-xs text-slate-400">
                Common Operating Picture & Distributed Multi-Domain Intelligence Gateway
              </p>
            </div>
          </div>
        </div>

        {/* DEFCON / Sector Status Badge */}
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-slate-900 border border-slate-800 px-3 py-1.5 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <span className="text-xs text-slate-400">DEFCON LEVEL:</span>
            <span className="text-xs font-bold text-slate-200">5 (NORMAL)</span>
          </div>
          <div className="rounded-lg bg-slate-900 border border-slate-800 px-3 py-1.5 flex items-center gap-2">
            <Radio className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-xs text-slate-400">GATEWAY:</span>
            <span className="text-xs font-bold text-cyan-300">ONLINE (14.2ms)</span>
          </div>
        </div>
      </div>

      {/* KPI Metrics Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Tracked Entities</span>
            <Layers className="w-4 h-4 text-ultrone-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100">{entities.length}</div>
          <div className="text-[10px] text-slate-500">
            {airAssets} Air • {groundVehicles} Ground • {activeSensors} Sensors
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Active Investigations</span>
            <FolderLock className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-cyan-300">{cases.length}</div>
          <div className="text-[10px] text-slate-500">
            {cases.filter((c) => c.status === 'active').length} Active Dossiers
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Active Anomalies</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-300">{anomalies.length}</div>
          <div className="text-[10px] text-slate-500">Bayesian anomaly filters active</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Sensor Stream</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">{events.length}</div>
          <div className="text-[10px] text-slate-500">Streaming at ~1.2 events/sec</div>
        </div>
      </div>

      {/* Critical Operational Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Primary Operational Gateways */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Operational Gateways
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* World Model Gateway */}
            <div
              onClick={() => setView('world')}
              className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-slate-700 hover:bg-slate-900 transition-all cursor-pointer group space-y-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-ultrone-400 font-bold">
                  <Compass className="w-4 h-4" />
                  <span className="text-sm">World View (COP)</span>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-500 group-hover:translate-x-1 transition-transform" />
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                2D Tactical Map & 3D Global Elevation view. 4-tier layer controls with live kinematic telemetry vectors.
              </p>
              <span className="inline-block text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                Launch Anduril-Style COP →
              </span>
            </div>

            {/* Entity Explorer Gateway */}
            <div
              onClick={() => setView('entities')}
              className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-slate-700 hover:bg-slate-900 transition-all cursor-pointer group space-y-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-cyan-400 font-bold">
                  <Layers className="w-4 h-4" />
                  <span className="text-sm">Entity Explorer</span>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-500 group-hover:translate-x-1 transition-transform" />
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Palantir-inspired object inspector. 8-tab deep-dive on telemetry, observations, relationships, and actions.
              </p>
              <span className="inline-block text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                Explore Object Catalog →
              </span>
            </div>

            {/* Intelligence Investigations Gateway */}
            <div
              onClick={() => setView('investigations')}
              className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-slate-700 hover:bg-slate-900 transition-all cursor-pointer group space-y-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-amber-400 font-bold">
                  <FolderLock className="w-4 h-4" />
                  <span className="text-sm">Investigations</span>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-500 group-hover:translate-x-1 transition-transform" />
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Case dossiers, evidence collections, analyst annotations, and structured dossier exports.
              </p>
              <span className="inline-block text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                Open Case Manager →
              </span>
            </div>

            {/* DARPA Simulation Sandbox */}
            <div
              onClick={() => setView('simulation')}
              className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-slate-700 hover:bg-slate-900 transition-all cursor-pointer group space-y-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-emerald-400 font-bold">
                  <Cpu className="w-4 h-4" />
                  <span className="text-sm">DARPA Simulation</span>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-500 group-hover:translate-x-1 transition-transform" />
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Multi-agent swarm experimentation sandbox. Test weather, ECM, conditions, and tactical courses of action.
              </p>
              <span className="inline-block text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                Launch Experiment Sandbox →
              </span>
            </div>
          </div>
        </div>

        {/* Right Col: Live Anomalies & AI Summary */}
        <div className="space-y-4">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Active Alerts & Intel
          </h2>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <div className="flex items-center gap-2 text-amber-400 text-xs font-bold">
              <AlertTriangle className="w-4 h-4" />
              <span>Anomalies Flagged by Cognitive Loop</span>
            </div>
            {anomalies.slice(0, 3).map((anom) => (
              <div
                key={anom.event_id}
                className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-1"
              >
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-slate-300 font-semibold">{anom.entity_id}</span>
                  <span className="text-rose-400 font-bold">CRITICAL</span>
                </div>
                <p className="text-[11px] text-slate-400">
                  Unexpected flight vector outside commercial airway envelope.
                </p>
              </div>
            ))}
          </div>

          {/* AI Copilot Card */}
          <div
            onClick={() => setView('ai')}
            className="p-4 rounded-xl bg-ultrone-600/10 border border-ultrone-500/30 hover:border-ultrone-500/50 cursor-pointer transition-all space-y-2"
          >
            <div className="flex items-center gap-2 text-ultrone-300 text-xs font-bold">
              <Sparkles className="w-4 h-4" />
              <span>AI Multi-Provider Copilot</span>
            </div>
            <p className="text-[11px] text-slate-300">
              Qwen 2.5 (Local Offline) & Cloud models ready for mission planning, threat synthesis, and audit log analysis.
            </p>
            <span className="text-[10px] text-ultrone-400 font-semibold block">
              Consult Copilot →
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OverviewView;

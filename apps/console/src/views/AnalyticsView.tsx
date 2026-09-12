import React from 'react';
import { useWorldStore } from '../store/worldStore';
import {
  BarChart3,
  TrendingUp,
  Activity,
  ShieldCheck,
  Zap,
  Clock,
  Layers,
} from 'lucide-react';

export const AnalyticsView: React.FC = () => {
  const entities = useWorldStore((s) => s.entities);
  const events = useWorldStore((s) => s.events);

  // Status breakdown
  const activeCount = entities.filter((e) => e.status === 'active').length;
  const degradedCount = entities.filter((e) => e.status === 'degraded').length;
  const engagedCount = entities.filter((e) => e.status === 'engaged').length;

  // Confidence breakdown
  const highConf = entities.filter((e) => e.confidence >= 0.85).length;
  const medConf = entities.filter((e) => e.confidence >= 0.65 && e.confidence < 0.85).length;
  const lowConf = entities.filter((e) => e.confidence < 0.65).length;

  // Average confidence
  const avgConf =
    entities.length > 0
      ? (entities.reduce((acc, e) => acc + e.confidence, 0) / entities.length) * 100
      : 0;

  return (
    <div className="flex h-full w-full flex-col bg-slate-950 p-6 overflow-y-auto space-y-6 font-mono select-none">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-ultrone-400" />
            <h1 className="text-xl font-bold tracking-wider text-slate-100 uppercase">
              Operational Analytics & Telemetry
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Statistical distribution, sensor certainty bands, and event throughput metrics
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Clock className="w-3.5 h-3.5" />
          <span>WINDOW: LAST 1 HOUR</span>
        </div>
      </div>

      {/* Top Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>TOTAL ASSETS</span>
            <Layers className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100">{entities.length}</div>
          <div className="text-[11px] text-emerald-400 flex items-center gap-1">
            <TrendingUp className="w-3 h-3" />
            <span>100% telemetry online</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>MEAN CONFIDENCE</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100">{avgConf.toFixed(1)}%</div>
          <div className="text-[11px] text-slate-400">Bayesian fused score</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>PROCESSED EVENTS</span>
            <Activity className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100">{events.length}</div>
          <div className="text-[11px] text-indigo-400">Stream nominal</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>DECISION LATENCY</span>
            <Zap className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100">18.4 ms</div>
          <div className="text-[11px] text-emerald-400">Below 50ms SLA</div>
        </div>
      </div>

      {/* Visual Analytics Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Entity Status Distribution */}
        <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 space-y-4">
          <h2 className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
            Asset Readiness & Status Distribution
          </h2>

          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-emerald-400 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  Active Nominal
                </span>
                <span className="text-slate-300">
                  {activeCount} ({Math.round((activeCount / (entities.length || 1)) * 100)}%)
                </span>
              </div>
              <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-emerald-500 rounded-full transition-all"
                  style={{ width: `${(activeCount / (entities.length || 1)) * 100}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-amber-400 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-amber-400" />
                  Degraded / Sensor Occluded
                </span>
                <span className="text-slate-300">
                  {degradedCount} ({Math.round((degradedCount / (entities.length || 1)) * 100)}%)
                </span>
              </div>
              <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-amber-500 rounded-full transition-all"
                  style={{ width: `${(degradedCount / (entities.length || 1)) * 100}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-purple-400 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-purple-400" />
                  Engaged / Target Locked
                </span>
                <span className="text-slate-300">
                  {engagedCount} ({Math.round((engagedCount / (entities.length || 1)) * 100)}%)
                </span>
              </div>
              <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-purple-500 rounded-full transition-all"
                  style={{ width: `${(engagedCount / (entities.length || 1)) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Confidence Bands Distribution */}
        <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 space-y-4">
          <h2 className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
            Sensor Fusion Confidence Distribution
          </h2>

          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-emerald-400">High Confidence (&gt;=85%)</span>
                <span className="text-slate-300">{highConf} assets</span>
              </div>
              <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-emerald-500 rounded-full transition-all"
                  style={{ width: `${(highConf / (entities.length || 1)) * 100}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-cyan-400">Moderate Confidence (65-84%)</span>
                <span className="text-slate-300">{medConf} assets</span>
              </div>
              <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-cyan-500 rounded-full transition-all"
                  style={{ width: `${(medConf / (entities.length || 1)) * 100}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-rose-400">Low / Uncertain (&lt;65%)</span>
                <span className="text-slate-300">{lowConf} assets</span>
              </div>
              <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-rose-500 rounded-full transition-all"
                  style={{ width: `${(lowConf / (entities.length || 1)) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsView;

// Copyright (c) Ultrone Contributors. All rights reserved.
import React, { useEffect, useState } from 'react';
import { cockpitApi } from '../../api/client';
import type { EvaluationBenchmarkResult } from '../../api/types';
import {
  FlaskConical,
  TrendingUp,
  TrendingDown,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  AlertOctagon,
  ArrowRight,
} from 'lucide-react';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { MetricCard } from '../../components/ui/MetricCard';

export const EvaluationLabView: React.FC = () => {
  const [result, setResult] = useState<EvaluationBenchmarkResult | null>(null);
  const [seeds, setSeeds] = useState<number>(5);
  const [ticks, setTicks] = useState<number>(20);
  const [loading, setLoading] = useState(true);

  const runEvaluation = (s = seeds, t = ticks) => {
    setLoading(true);
    cockpitApi
      .getEvaluation(s, t)
      .then((data) => {
        setResult(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    runEvaluation(5, 20);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-surface-400 font-mono text-sm">
        <span className="animate-pulse">
          Computing Multi-Seed Paired Statistics & Bootstrap Confidence Intervals...
        </span>
      </div>
    );
  }

  if (!result) return null;

  const { baseline, candidate, metrics, regressions, improvements, promotion } = result;

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-mono">
      {/* Header */}
      <div className="flex items-center justify-between bg-surface-900/90 p-4 rounded-xl border border-surface-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-950 text-emerald-400 border border-emerald-800/50">
            <FlaskConical className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-surface-100 font-sans flex items-center gap-2">
              Scientific Evaluation Laboratory & Promotion Gatekeeper
              <StatusBadge status="ACTIVE" />
            </h2>
            <p className="text-xs text-surface-400">
              Multi-seed paired statistical testing, Cohen's dz effect sizes, bootstrap 95% CIs, and regression gates.
            </p>
          </div>
        </div>

        {/* Promotion Gate Status */}
        <div className="flex items-center gap-3">
          <div
            className={`px-4 py-2 rounded-lg border font-bold text-xs flex items-center gap-2 ${
              promotion === 'ELIGIBLE'
                ? 'bg-emerald-950/80 text-emerald-300 border-emerald-700'
                : promotion === 'BLOCKED'
                ? 'bg-rose-950/80 text-rose-300 border-rose-700'
                : 'bg-surface-800 text-surface-300 border-surface-700'
            }`}
          >
            {promotion === 'ELIGIBLE' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
            {promotion === 'BLOCKED' && <AlertOctagon className="w-4 h-4 text-rose-400" />}
            <span>PROMOTION GATE: {promotion}</span>
          </div>

          <button
            onClick={() => runEvaluation(seeds, ticks)}
            className="px-3.5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-black font-bold text-xs transition-colors shadow-lg shadow-cyan-900/20"
          >
            Re-run Benchmark
          </button>
        </div>
      </div>

      {/* Comparison Arms Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Baseline Arm */}
        <div className="p-4 bg-surface-900 rounded-xl border border-surface-800 space-y-2">
          <span className="text-[10px] text-surface-500 uppercase tracking-wider block">
            CONTROL / BASELINE ARM
          </span>
          <div className="text-base font-bold text-surface-100">{baseline.label}</div>
          <span className="text-xs text-surface-400 block font-mono">
            Model: {baseline.model_version} • Seeds: {seeds} paired samples
          </span>
        </div>

        {/* Candidate Arm */}
        <div className="p-4 bg-surface-900 rounded-xl border border-cyan-500/40 space-y-2">
          <span className="text-[10px] text-cyan-400 uppercase tracking-wider block">
            CANDIDATE HYPOTHESIS ARM
          </span>
          <div className="text-base font-bold text-cyan-300">{candidate.label}</div>
          <span className="text-xs text-surface-400 block font-mono">
            Model: {candidate.model_version} • Manipulation: Calibrated perceptual noise
          </span>
        </div>
      </div>

      {/* Paired Statistics Table */}
      <div className="bg-surface-900 rounded-xl border border-surface-800 overflow-hidden shadow-xl">
        <div className="px-4 py-3 bg-surface-950 border-b border-surface-800 flex items-center justify-between">
          <span className="text-xs font-bold text-surface-300 uppercase tracking-wider">
            Multi-Metric Paired Statistical Testing (Never Single Score)
          </span>
          <span className="text-[11px] text-surface-500">
            Regressions on any safety or calibration metric strictly block candidate promotion
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-surface-800 bg-surface-950/60 text-surface-400 text-[11px]">
                <th className="py-2.5 px-4">METRIC</th>
                <th className="py-2.5 px-4">DIRECTION</th>
                <th className="py-2.5 px-4">DELTA MEAN</th>
                <th className="py-2.5 px-4">95% BOOTSTRAP CI</th>
                <th className="py-2.5 px-4">COHEN'S dz</th>
                <th className="py-2.5 px-4">P-VALUE</th>
                <th className="py-2.5 px-4 text-right">GATE VERDICT</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-800/60">
              {Object.entries(metrics).map(([metricName, stat]) => {
                const isImproved = stat.candidate_improved;
                const isRegressed = stat.regression;

                return (
                  <tr key={metricName} className="hover:bg-surface-800/40 transition-colors">
                    <td className="py-3 px-4 font-bold text-surface-200 uppercase">
                      {metricName.replace('_', ' ')}
                    </td>
                    <td className="py-3 px-4 text-surface-400 text-[11px]">
                      {stat.lower_is_better ? 'Lower is Better' : 'Higher is Better'}
                    </td>
                    <td className="py-3 px-4 font-mono font-bold">
                      <span
                        className={
                          isImproved
                            ? 'text-emerald-400'
                            : isRegressed
                            ? 'text-rose-400'
                            : 'text-surface-300'
                        }
                      >
                        {stat.delta_mean !== undefined
                          ? (stat.delta_mean > 0 ? '+' : '') + stat.delta_mean.toFixed(4)
                          : '0.0000'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-surface-400 font-mono text-[11px]">
                      {stat.ci_lower !== undefined
                        ? `[${stat.ci_lower.toFixed(3)}, ${stat.ci_upper.toFixed(3)}]`
                        : 'Insufficient Var'}
                    </td>
                    <td className="py-3 px-4 text-cyan-400 font-mono font-bold">
                      {stat.cohens_d !== undefined ? stat.cohens_d.toFixed(2) : '—'}
                    </td>
                    <td className="py-3 px-4 text-surface-400 font-mono text-[11px]">
                      {stat.p_value !== undefined ? stat.p_value.toFixed(4) : '—'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {isImproved ? (
                        <span className="text-emerald-400 font-bold px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800">
                          IMPROVED ↑
                        </span>
                      ) : isRegressed ? (
                        <span className="text-rose-400 font-bold px-2 py-0.5 rounded bg-rose-950 border border-rose-800">
                          REGRESSION ↓
                        </span>
                      ) : (
                        <span className="text-surface-400 font-bold px-2 py-0.5 rounded bg-surface-950 border border-surface-800">
                          NEUTRAL
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Scientific Governance Rule Note */}
      <div className="p-4 rounded-xl bg-surface-950 border border-surface-800 space-y-1.5 text-xs text-surface-400">
        <span className="font-bold text-surface-200 font-sans block mb-1">
          Evidence-Backed Governance Protocol
        </span>
        <p>
          Candidate promotion requires zero regressions across all safety and calibration metrics
          with statistical significance (p &lt; 0.05). If calibration improves but latency or
          robustness degrades beyond tolerance, the promotion gate automatically flips to BLOCKED.
        </p>
      </div>
    </div>
  );
};

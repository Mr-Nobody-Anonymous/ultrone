import React, { useState } from 'react';
import {
  Microscope,
  CheckCircle2,
  Play,
  RefreshCw,
} from 'lucide-react';

interface BenchmarkRun {
  id: string;
  name: string;
  category: string;
  model: string;
  f1Score: number;
  latencyMs: number;
  hallucinationRate: number;
  timestamp: string;
  status: 'completed' | 'running';
}

const INITIAL_RUNS: BenchmarkRun[] = [
  {
    id: 'RUN-2026-A1',
    name: 'Situational Awareness SA-Bench (400 Entities)',
    category: 'Kinematics & Tracking',
    model: 'Qwen 2.5 7B (Local Offline)',
    f1Score: 0.932,
    latencyMs: 142,
    hallucinationRate: 0.012,
    timestamp: '2026-09-12 11:20:00',
    status: 'completed',
  },
  {
    id: 'RUN-2026-A2',
    name: 'Situational Awareness SA-Bench (400 Entities)',
    category: 'Kinematics & Tracking',
    model: 'Claude 3.5 Sonnet (Direct Cloud)',
    f1Score: 0.968,
    latencyMs: 410,
    hallucinationRate: 0.004,
    timestamp: '2026-09-12 11:25:00',
    status: 'completed',
  },
  {
    id: 'RUN-2026-B1',
    name: 'Deep Reasoning Trace Math & Logic',
    category: 'Frontier Reasoning',
    model: 'DeepSeek R1 (Reasoner)',
    f1Score: 0.954,
    latencyMs: 1820,
    hallucinationRate: 0.008,
    timestamp: '2026-09-12 11:40:00',
    status: 'completed',
  },
  {
    id: 'RUN-2026-C1',
    name: 'HITL Policy Gate Constraint Enforcement',
    category: 'Safety & Alignment',
    model: 'GPT-4o (Direct OpenAI)',
    f1Score: 0.985,
    latencyMs: 380,
    hallucinationRate: 0.002,
    timestamp: '2026-09-12 12:00:00',
    status: 'completed',
  },
];

export const ResearchView: React.FC = () => {
  const [runs, setRuns] = useState<BenchmarkRun[]>(INITIAL_RUNS);
  const [isRunningTest, setIsRunningTest] = useState(false);

  const handleRunNewBenchmark = () => {
    setIsRunningTest(true);
    setTimeout(() => {
      const newRun: BenchmarkRun = {
        id: `RUN-${Date.now().toString(36).toUpperCase()}`,
        name: 'Autonomous Swarm Collision Avoidance Benchmark',
        category: 'Swarm & Simulation',
        model: 'Qwen 2.5 14B (Local)',
        f1Score: 0.948,
        latencyMs: 260,
        hallucinationRate: 0.009,
        timestamp: new Date().toLocaleTimeString(),
        status: 'completed',
      };
      setRuns((prev) => [newRun, ...prev]);
      setIsRunningTest(false);
    }, 1500);
  };

  return (
    <div className="flex h-full w-full flex-col bg-slate-950 p-6 overflow-y-auto space-y-6 font-mono select-none text-xs">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-500/20 border border-purple-500/40 text-purple-400 shadow-md">
            <Microscope className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-wider text-slate-100 uppercase flex items-center gap-2">
              DARPA Research & Evaluation Lab
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/40 font-normal">
                v2.5
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              Cognitive model benchmarks, ablation studies, reproducible seeds, and dataset lineage
            </p>
          </div>
        </div>

        <button
          onClick={handleRunNewBenchmark}
          disabled={isRunningTest}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white font-semibold shadow-md transition-colors"
        >
          {isRunningTest ? (
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Play className="w-3.5 h-3.5" />
          )}
          <span>{isRunningTest ? 'Executing Benchmark...' : 'Run Experiment'}</span>
        </button>
      </div>

      {/* Model Ablation Matrix */}
      <div className="space-y-2">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Cognitive Model Performance Matrix (Ablation Comparison)
        </h2>
        <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60 p-1">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-800 text-[10px] uppercase text-slate-500">
                <th className="p-3">Model Engine</th>
                <th className="p-3">Environment</th>
                <th className="p-3">SA F1-Score</th>
                <th className="p-3">Mean Latency</th>
                <th className="p-3">Hallucination Rate</th>
                <th className="p-3">Privacy / Offline</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              <tr className="hover:bg-slate-800/40">
                <td className="p-3 font-bold text-cyan-300">Qwen 2.5 7B</td>
                <td className="p-3 text-slate-400">Ollama Local GPU</td>
                <td className="p-3 font-bold text-emerald-400">93.2%</td>
                <td className="p-3 text-slate-300 font-mono">142 ms</td>
                <td className="p-3 text-emerald-400 font-mono">1.2%</td>
                <td className="p-3">
                  <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-bold">
                    100% OFFLINE
                  </span>
                </td>
              </tr>
              <tr className="hover:bg-slate-800/40">
                <td className="p-3 font-bold text-purple-300">DeepSeek R1</td>
                <td className="p-3 text-slate-400">Direct API (Open Weights)</td>
                <td className="p-3 font-bold text-emerald-400">95.4%</td>
                <td className="p-3 text-slate-300 font-mono">1820 ms</td>
                <td className="p-3 text-emerald-400 font-mono">0.8%</td>
                <td className="p-3">
                  <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 text-[10px] font-bold">
                    OPEN WEIGHTS
                  </span>
                </td>
              </tr>
              <tr className="hover:bg-slate-800/40">
                <td className="p-3 font-bold text-ultrone-300">Claude 3.5 Sonnet</td>
                <td className="p-3 text-slate-400">Anthropic Cloud</td>
                <td className="p-3 font-bold text-emerald-400">96.8%</td>
                <td className="p-3 text-slate-300 font-mono">410 ms</td>
                <td className="p-3 text-emerald-400 font-mono">0.4%</td>
                <td className="p-3">
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px]">
                    CLOUD API
                  </span>
                </td>
              </tr>
              <tr className="hover:bg-slate-800/40">
                <td className="p-3 font-bold text-slate-100">GPT-4o</td>
                <td className="p-3 text-slate-400">OpenAI Cloud</td>
                <td className="p-3 font-bold text-emerald-400">98.5%</td>
                <td className="p-3 text-slate-300 font-mono">380 ms</td>
                <td className="p-3 text-emerald-400 font-mono">0.2%</td>
                <td className="p-3">
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px]">
                    CLOUD API
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Benchmark History & Experiment Run Logs */}
      <div className="space-y-2">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Reproducible Experiment Runs ({runs.length})
        </h2>
        <div className="space-y-2">
          {runs.map((r) => (
            <div
              key={r.id}
              className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-purple-400">{r.id}</span>
                  <span className="font-semibold text-slate-200">{r.name}</span>
                </div>
                <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
                  <span>Category: {r.category}</span>
                  <span>•</span>
                  <span>Model: <strong className="text-slate-300">{r.model}</strong></span>
                  <span>•</span>
                  <span>Executed: {r.timestamp}</span>
                </div>
              </div>

              <div className="flex items-center gap-4 text-right">
                <div>
                  <span className="text-[10px] text-slate-500 block">F1 Accuracy</span>
                  <span className="font-bold text-emerald-400">{(r.f1Score * 100).toFixed(1)}%</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">Latency</span>
                  <span className="font-bold text-cyan-300">{r.latencyMs} ms</span>
                </div>
                <div className="flex items-center gap-1 text-emerald-400 font-semibold text-[11px]">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>VERIFIED</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ResearchView;

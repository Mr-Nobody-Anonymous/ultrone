// Copyright (c) Ultrone Contributors. All rights reserved.
import React, { useEffect, useState } from 'react';
import { useCockpitStore } from '../stores/cockpitStore';
import { cockpitApi } from '../api/client';
import { Layers, Play, CheckCircle2, Shield, Radio, ArrowRight } from 'lucide-react';
import { StatusBadge } from '../components/ui/StatusBadge';

export const ScenariosPage: React.FC = () => {
  const { refreshOverview, refreshWorld } = useCockpitStore();
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [activeId, setActiveId] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState<string | null>(null);

  const fetchScenarios = () => {
    cockpitApi
      .getScenarios()
      .then((data) => {
        setScenarios(data.scenarios || []);
        setActiveId(data.active_scenario_id || '');
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    fetchScenarios();
  }, []);

  const handleSelect = async (scenarioId: string) => {
    setSwitching(scenarioId);
    try {
      await cockpitApi.selectScenario(scenarioId);
      await refreshOverview();
      await refreshWorld();
      fetchScenarios();
    } finally {
      setSwitching(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-surface-400 font-mono text-sm">
        <span className="animate-pulse">Loading Scenarios Catalog...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-mono">
      {/* Header */}
      <div className="flex items-center justify-between bg-surface-900/90 p-4 rounded-xl border border-surface-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-cyan-950 text-cyan-400 border border-cyan-800/50">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-surface-100 font-sans flex items-center gap-2">
              Declarative Scenario Management & Parameter Pointers
              <StatusBadge status="SIMULATION" />
            </h2>
            <p className="text-xs text-surface-400">
              Scenarios are schema declarations pinning ground-truth entities, sensors, models, and policies.
            </p>
          </div>
        </div>

        <div className="text-right text-xs">
          <span className="text-surface-500 block">ACTIVE SCENARIO</span>
          <span className="text-cyan-400 font-bold">{activeId}</span>
        </div>
      </div>

      {/* Scenario Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {scenarios.map((sc) => {
          const isActive = sc.is_active;

          return (
            <div
              key={sc.scenario_id}
              className={`p-5 rounded-xl border flex flex-col justify-between transition-all ${
                isActive
                  ? 'bg-surface-900 border-cyan-500/50 shadow-lg shadow-cyan-950/40'
                  : 'bg-surface-950 border-surface-800 hover:border-surface-700'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-cyan-400">{sc.scenario_id}</span>
                  {isActive ? (
                    <span className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-700 text-[10px] font-bold flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>ACTIVE</span>
                    </span>
                  ) : (
                    <span className="text-[10px] text-surface-500 uppercase">{sc.environment}</span>
                  )}
                </div>

                <h3 className="text-sm font-bold text-surface-100 font-sans mb-1">{sc.name}</h3>
                <p className="text-xs text-surface-400 leading-relaxed mb-4">{sc.description}</p>

                <div className="space-y-1.5 text-xs text-surface-400 border-t border-surface-800/80 pt-3">
                  <div className="flex justify-between">
                    <span className="text-surface-500">Entities:</span>
                    <span className="text-surface-200">{sc.entities_count} Ground Truth</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-surface-500">Agents:</span>
                    <span className="text-surface-200">{sc.agents_count} Autonomous</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-surface-500">Sensors:</span>
                    <span className="text-surface-200">{sc.sensors_count} Multi-Modal</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-surface-500">Model / Policy:</span>
                    <span className="text-cyan-400">
                      {sc.model_version} / {sc.policy_version}
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-5 pt-3 border-t border-surface-800/80">
                {isActive ? (
                  <button
                    disabled
                    className="w-full py-1.5 rounded-lg bg-surface-800 text-cyan-400 text-xs font-bold flex items-center justify-center gap-1.5 cursor-default"
                  >
                    <span>Loaded in Simulator Engine</span>
                  </button>
                ) : (
                  <button
                    disabled={switching === sc.scenario_id}
                    onClick={() => handleSelect(sc.scenario_id)}
                    className="w-full py-1.5 rounded-lg bg-surface-800 hover:bg-cyan-600 hover:text-black text-surface-200 text-xs font-bold transition-colors flex items-center justify-center gap-1.5"
                  >
                    <Play className="w-3.5 h-3.5" />
                    <span>{switching === sc.scenario_id ? 'Loading Scenario...' : 'Select & Load'}</span>
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

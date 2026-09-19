// Copyright (c) Ultrone Contributors. All rights reserved.
import React, { useEffect, useRef, useState } from 'react';
import { useCockpitStore } from '../../stores/cockpitStore';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  X,
  Play,
  Pause,
  RotateCcw,
  Shield,
  FileDown,
  Layers,
  Cpu,
  Radio,
  FileText,
  Activity,
  ArrowRight,
  ShieldAlert,
} from 'lucide-react';
import { StatusBadge } from './StatusBadge';

interface ActionPreview {
  actionName: string;
  what: string;
  why: string;
  policy: string;
  environment: string;
  execute: () => void;
}

export const CommandPalette: React.FC = () => {
  const {
    commandPaletteOpen,
    setCommandPalette,
    searchQuery,
    setSearchQuery,
    searchResults,
    isSearching,
    play,
    pause,
    reset,
    step,
    setSystemTruthModal,
    setFaultInjectionOpen,
    overview,
  } = useCockpitStore();

  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [selectedPreview, setSelectedPreview] = useState<ActionPreview | null>(null);

  // Keyboard shortcut listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setCommandPalette(!commandPaletteOpen);
      }
      if (e.key === 'Escape' && commandPaletteOpen) {
        setCommandPalette(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [commandPaletteOpen, setCommandPalette]);

  useEffect(() => {
    if (commandPaletteOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setSelectedPreview(null);
    }
  }, [commandPaletteOpen]);

  if (!commandPaletteOpen) return null;

  const quickActions: ActionPreview[] = [
    {
      actionName: 'Step Simulation (+1 Tick)',
      what: 'Advances the simulated kinematic and sensor clock by one tick (dt = 0.5s).',
      why: 'Step-by-step determinism inspection for decision traces.',
      policy: 'SAF-001 (Causal boundary checked on every tick)',
      environment: 'SIMULATION',
      execute: () => step(1),
    },
    {
      actionName: 'Resume Simulation Loop',
      what: 'Starts the background world simulation loop at current speed.',
      why: 'Drive continuous observation and plan generation.',
      policy: 'Simulated Execution Only (Zero Hardware Path)',
      environment: 'SIMULATION',
      execute: () => play(),
    },
    {
      actionName: 'Pause Simulation Loop',
      what: 'Freezes simulation clock and holds state across all entities and sensors.',
      why: 'Allow deep inspection of static belief and decision provenance.',
      policy: 'No Policy Impact',
      environment: 'SIMULATION',
      execute: () => pause(),
    },
    {
      actionName: 'Reset World State',
      what: 'Reverts simulation to tick 0 and clears the ephemeral event store.',
      why: 'Restart scenario from clean baseline conditions.',
      policy: 'Audit Trail Preserved in Run Logs',
      environment: 'SIMULATION',
      execute: () => reset(),
    },
    {
      actionName: 'Inspect System Truth & Invariants',
      what: 'Opens machine-verified epistemic boundaries dialog.',
      why: 'Verify ground truth isolation and active safety invariants.',
      policy: 'SAF-001..SAF-005 Compliance',
      environment: 'SIMULATION',
      execute: () => setSystemTruthModal(true),
    },
    {
      actionName: 'Arm Fault Injection Levers',
      what: 'Opens fault injection controls to introduce delays or dropouts.',
      why: 'Test fail-safe transitions and policy gate rejections under stress.',
      policy: 'SAF-003 Stale Telemetry Protection',
      environment: 'SIMULATION',
      execute: () => setFaultInjectionOpen(true),
    },
  ];

  const handleSelectResult = (item: any) => {
    setCommandPalette(false);
    navigate(item.route);
  };

  const handleExecutePreview = () => {
    if (selectedPreview) {
      selectedPreview.execute();
      setCommandPalette(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-surface-900 border border-surface-700 rounded-xl max-w-2xl w-full shadow-2xl overflow-hidden flex flex-col max-h-[80vh]">
        {/* Search Input Bar */}
        <div className="p-3 bg-surface-950 border-b border-surface-800 flex items-center gap-3">
          <Search className="w-5 h-5 text-cyan-400 flex-shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search agents, devices, events, policies, models, or type an action..."
            className="flex-1 bg-transparent border-none outline-none text-sm text-surface-100 placeholder-surface-500 font-mono"
          />
          <kbd className="hidden sm:inline-block px-2 py-0.5 rounded text-[10px] font-mono bg-surface-800 text-surface-400 border border-surface-700">
            ESC
          </kbd>
          <button
            onClick={() => setCommandPalette(false)}
            className="p-1 text-surface-400 hover:text-surface-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          {/* Action preview safety card */}
          {selectedPreview && (
            <div className="p-4 rounded-lg bg-surface-950 border border-cyan-500/50 shadow-lg space-y-2 text-xs font-mono">
              <div className="flex items-center justify-between text-cyan-400 font-bold">
                <span>ACTION CONFIRMATION & SAFETY PREVIEW</span>
                <StatusBadge status={selectedPreview.environment} />
              </div>
              <div className="space-y-1 text-surface-300">
                <p>
                  <strong className="text-surface-100">WHAT WILL HAPPEN:</strong> {selectedPreview.what}
                </p>
                <p>
                  <strong className="text-surface-100">WHY:</strong> {selectedPreview.why}
                </p>
                <p>
                  <strong className="text-surface-100">APPLIED POLICY:</strong> {selectedPreview.policy}
                </p>
              </div>
              <div className="pt-2 flex justify-end gap-2">
                <button
                  onClick={() => setSelectedPreview(null)}
                  className="px-3 py-1 rounded bg-surface-800 hover:bg-surface-700 text-surface-300 text-xs"
                >
                  Cancel
                </button>
                <button
                  onClick={handleExecutePreview}
                  className="px-3.5 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-black font-bold text-xs flex items-center gap-1.5"
                >
                  <span>Execute Safe Action</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* Search results */}
          {searchQuery.trim() ? (
            <div>
              <div className="text-[10px] font-mono text-surface-400 uppercase tracking-wider px-2 mb-1.5">
                Search Results ({searchResults.length})
              </div>
              {isSearching ? (
                <div className="p-4 text-center text-xs font-mono text-surface-500 animate-pulse">
                  Searching live system catalog...
                </div>
              ) : searchResults.length === 0 ? (
                <div className="p-4 text-center text-xs font-mono text-surface-500">
                  No matching agents, devices, events, or policies found.
                </div>
              ) : (
                <div className="space-y-1">
                  {searchResults.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => handleSelectResult(item)}
                      className="w-full text-left p-2.5 rounded-lg hover:bg-surface-800/80 transition-colors flex items-center justify-between group"
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div className="p-1.5 rounded bg-surface-950 text-surface-400 group-hover:text-cyan-400">
                          {item.category === 'agent' && <Cpu className="w-3.5 h-3.5" />}
                          {item.category === 'device' && <Radio className="w-3.5 h-3.5" />}
                          {item.category === 'policy' && <Shield className="w-3.5 h-3.5" />}
                          {item.category === 'event' && <FileText className="w-3.5 h-3.5" />}
                          {item.category === 'model' && <Layers className="w-3.5 h-3.5" />}
                        </div>
                        <div className="min-w-0">
                          <span className="text-xs font-bold text-surface-200 block truncate">
                            {item.title}
                          </span>
                          <span className="text-[11px] text-surface-400 font-mono block truncate">
                            {item.subtitle}
                          </span>
                        </div>
                      </div>
                      <StatusBadge status={item.badge} className="text-[10px]" />
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            /* Recommended quick actions */
            <div>
              <div className="text-[10px] font-mono text-surface-400 uppercase tracking-wider px-2 mb-1.5">
                Safe Simulator Controls & Quick Navigation
              </div>
              <div className="space-y-1">
                {quickActions.map((action, idx) => (
                  <button
                    key={idx}
                    onClick={() => setSelectedPreview(action)}
                    className="w-full text-left p-2.5 rounded-lg hover:bg-surface-800/80 transition-colors flex items-center justify-between group"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="p-1.5 rounded bg-surface-950 text-surface-400 group-hover:text-cyan-400">
                        {idx === 0 && <Play className="w-3.5 h-3.5" />}
                        {idx === 1 && <Play className="w-3.5 h-3.5" />}
                        {idx === 2 && <Pause className="w-3.5 h-3.5" />}
                        {idx === 3 && <RotateCcw className="w-3.5 h-3.5" />}
                        {idx === 4 && <Shield className="w-3.5 h-3.5" />}
                        {idx === 5 && <ShieldAlert className="w-3.5 h-3.5" />}
                      </div>
                      <div>
                        <span className="text-xs font-semibold text-surface-200 block">
                          {action.actionName}
                        </span>
                        <span className="text-[11px] text-surface-400 font-mono block">
                          {action.what}
                        </span>
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-surface-600 group-hover:text-surface-300" />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

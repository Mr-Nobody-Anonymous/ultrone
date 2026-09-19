// Copyright (c) Ultrone Contributors. All rights reserved.
import React, { useEffect } from 'react';
import { Outlet, NavLink, Link, useLocation } from 'react-router-dom';
import { useCockpitStore } from '../stores/cockpitStore';
import {
  ShieldAlert,
  Play,
  Pause,
  StepForward,
  RotateCcw,
  Search,
  Sliders,
  Cpu,
  Radio,
  Share2,
  FileText,
  ShieldCheck,
  FlaskConical,
  BookOpen,
  Layers,
  Palette,
  Terminal,
  Activity,
  Zap,
  Clock,
  CheckCircle2,
  AlertTriangle,
  HeartPulse,
  BellRing,
  ScrollText,
} from 'lucide-react';
import { StatusBadge } from '../components/ui/StatusBadge';
import { CommandPalette } from '../components/ui/CommandPalette';
import { SystemTruthModal } from '../components/ui/SystemTruthModal';
import { WhyBlockedModal } from '../components/ui/WhyBlockedModal';
import { FaultInjectionModal } from '../components/ui/FaultInjectionModal';
import { InspectorDrawer } from '../components/ui/InspectorDrawer';

export const CockpitShell: React.FC = () => {
  const {
    init,
    overview,
    world,
    truth,
    connectionStatus,
    play,
    pause,
    step,
    reset,
    setSpeed,
    setCommandPalette,
    setSystemTruthModal,
    setFaultInjectionOpen,
    researchMode,
    toggleResearchMode,
    theme,
    setTheme,
  } = useCockpitStore();

  const location = useLocation();

  useEffect(() => {
    const teardown = init();
    return () => teardown();
  }, [init]);

  const isRunning = overview?.run?.playing ?? false;
  const currentSpeed = overview?.run?.speed ?? 1.0;
  const tick = overview?.run?.tick ?? world?.tick ?? 0;
  const simSeconds = Math.round(tick * 0.5);
  const formattedTime = `${String(Math.floor(simSeconds / 60)).padStart(2, '0')}:${String(
    simSeconds % 60
  ).padStart(2, '0')}`;

  const navSections = [
    {
      title: 'COMMAND CENTER',
      links: [
        { to: '/', label: 'Overview', icon: Activity, exact: true },
        { to: '/simulation', label: 'Simulation World', icon: Radio },
        { to: '/simulation/compare', label: 'Truth vs Belief', icon: Share2 },
        { to: '/scenarios', label: 'Scenarios', icon: Layers },
      ],
    },
    {
      title: 'INTELLIGENCE',
      links: [
        { to: '/agents', label: 'Agent Center', icon: Cpu },
        { to: '/traces', label: 'Cognitive Trace DAG', icon: Terminal },
      ],
    },
    {
      title: 'DEVICES',
      links: [{ to: '/devices', label: 'UDIS 10-State FSM', icon: Sliders }],
    },
    {
      title: 'PROTOCOL',
      links: [{ to: '/mcp', label: 'MCP 2026-07-28', icon: Share2 }],
    },
    {
      title: 'TRACE & REPLAY',
      links: [{ to: '/events', label: 'Event Store & Replay', icon: FileText }],
    },
    {
      title: 'SAFETY & INVARIANTS',
      links: [{ to: '/safety', label: 'Safety Center', icon: ShieldCheck }],
    },
    {
      title: 'SYSTEM',
      links: [
        { to: '/system/health', label: 'System Health', icon: HeartPulse },
        { to: '/system/alerts', label: 'Alerts Center', icon: BellRing },
        { to: '/system/audit', label: 'UI Audit Trail', icon: ScrollText },
      ],
    },
    {
      title: 'RESEARCH & GOVERNANCE',
      links: [
        { to: '/evaluation', label: 'Evaluation Lab', icon: FlaskConical },
        { to: '/governance', label: 'L0-L6 Maturity', icon: ShieldAlert },
        { to: '/registries', label: 'Model & Data', icon: Layers },
        { to: '/design-system', label: 'Design System', icon: Palette },
      ],
    },
  ];

  return (
    <div className="h-screen w-screen flex flex-col bg-surface-950 text-surface-100 overflow-hidden select-none font-sans">
      {/* ── PERSISTENT GLOBAL TOP BAR ────────────────────────────────────── */}
      <header className="h-14 bg-surface-950 border-b border-surface-800 px-4 flex items-center justify-between gap-4 z-30 flex-shrink-0">
        {/* Left: Brand + Persistent Simulation Mode Badge */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-base font-black tracking-widest text-cyan-400 font-mono">
              ULTRONE
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-800 text-surface-400 border border-surface-700">
              v2.0
            </span>
          </div>

          {/* CRITICAL PERSISTENT BOUNDARY BANNER */}
          <div
            onClick={() => setSystemTruthModal(true)}
            className="cursor-pointer group flex items-center gap-1.5 px-3 py-1 rounded-md bg-cyan-950/80 border border-cyan-500/60 hover:bg-cyan-900/60 transition-colors shadow-sm shadow-cyan-950"
            title="Epistemic boundary verified: Physical actuation controls are omitted by construction"
          >
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-[11px] font-mono font-bold tracking-wider text-cyan-300">
              SIMULATION MODE • NO PHYSICAL ACTUATION
            </span>
          </div>
        </div>

        {/* Center: System Vitals */}
        <div className="hidden lg:flex items-center gap-4 text-xs font-mono text-surface-400 overflow-x-auto">
          <div className="flex items-center gap-1.5 bg-surface-900/80 px-2.5 py-1 rounded border border-surface-800">
            <span className="text-surface-500">RUN:</span>
            <span className="text-surface-200 font-bold">{overview?.run?.run_id || 'RUN-004281'}</span>
          </div>

          <div className="flex items-center gap-1.5 bg-surface-900/80 px-2.5 py-1 rounded border border-surface-800">
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-surface-200 font-bold">
              T+ {formattedTime} (T:{tick})
            </span>
          </div>

          <div className="flex items-center gap-1.5 bg-surface-900/80 px-2.5 py-1 rounded border border-surface-800">
            <span className="text-surface-500">MCP:</span>
            <span className="text-emerald-400 font-semibold">2026-07-28</span>
          </div>

          <div className="flex items-center gap-1.5 bg-surface-900/80 px-2.5 py-1 rounded border border-surface-800">
            <span className="text-surface-500">STATUS:</span>
            <StatusBadge status={isRunning ? 'RUNNING' : 'PAUSED'} className="text-[10px]" />
          </div>
        </div>

        {/* Right: Controls & Shortcuts */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Simulator Playback Transport */}
          <div className="flex items-center gap-1 bg-surface-900 p-1 rounded-lg border border-surface-800">
            {isRunning ? (
              <button
                onClick={() => pause()}
                className="p-1.5 rounded hover:bg-surface-800 text-amber-400 transition-colors"
                title="Pause Simulation Clock"
              >
                <Pause className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={() => play(currentSpeed)}
                className="p-1.5 rounded hover:bg-surface-800 text-emerald-400 transition-colors"
                title="Run Simulation Clock"
              >
                <Play className="w-4 h-4" />
              </button>
            )}

            <button
              onClick={() => step(1)}
              className="p-1.5 rounded hover:bg-surface-800 text-cyan-400 transition-colors"
              title="Step Simulation (+1 Tick)"
            >
              <StepForward className="w-4 h-4" />
            </button>

            <button
              onClick={() => reset()}
              className="p-1.5 rounded hover:bg-surface-800 text-surface-400 hover:text-surface-200 transition-colors"
              title="Reset World State"
            >
              <RotateCcw className="w-4 h-4" />
            </button>

            {/* Speed Selector */}
            <select
              value={currentSpeed}
              onChange={(e) => setSpeed(Number(e.target.value))}
              className="bg-surface-950 border border-surface-700 text-xs font-mono rounded px-1.5 py-0.5 text-surface-200 outline-none"
            >
              <option value="0.5">0.5x</option>
              <option value="1.0">1.0x</option>
              <option value="2.0">2.0x</option>
              <option value="5.0">5.0x</option>
              <option value="10.0">10.0x</option>
            </select>
          </div>

          {/* Fault lever */}
          <button
            onClick={() => setFaultInjectionOpen(true)}
            className="p-1.5 rounded-lg bg-surface-900 hover:bg-amber-950/60 border border-surface-800 hover:border-amber-700/50 text-amber-400 transition-colors"
            title="Arm Research Fault Injection"
          >
            <Zap className="w-4 h-4" />
          </button>

          {/* Command palette */}
          <button
            onClick={() => setCommandPalette(true)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-surface-900 hover:bg-surface-800 border border-surface-800 text-surface-300 hover:text-surface-100 transition-colors text-xs font-mono"
            title="Universal Command Palette (Ctrl+K)"
          >
            <Search className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline">Ctrl+K</span>
          </button>

          {/* Research Mode toggle */}
          <button
            onClick={toggleResearchMode}
            className={`px-2 py-1 rounded text-xs font-mono border transition-colors ${
              researchMode
                ? 'bg-purple-950 text-purple-300 border-purple-600 font-bold'
                : 'bg-surface-900 text-surface-400 border-surface-800 hover:text-surface-200'
            }`}
            title="Toggle Research Mode (exposing random seeds, distributions, and parameter hashes)"
          >
            {researchMode ? '🔬 RESEARCH' : 'OBSERVE'}
          </button>
        </div>
      </header>

      {/* ── MAIN COCKPIT BODY (Sidebar + Workspace + Inspector) ─────────── */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Navigation Sidebar */}
        <aside className="w-60 bg-surface-950 border-r border-surface-800 flex flex-col justify-between overflow-y-auto flex-shrink-0">
          <div className="p-3 space-y-5">
            {navSections.map((section, idx) => (
              <div key={idx}>
                <div className="text-[10px] font-mono text-surface-500 uppercase tracking-wider px-2 mb-1.5 font-bold">
                  {section.title}
                </div>
                <div className="space-y-0.5">
                  {section.links.map((link) => {
                    const Icon = link.icon;
                    return (
                      <NavLink
                        key={link.to}
                        to={link.to}
                        end={link.exact}
                        className={({ isActive }) =>
                          `flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors ${
                            isActive
                              ? 'bg-cyan-950/70 text-cyan-300 border border-cyan-800/60 font-semibold'
                              : 'text-surface-400 hover:text-surface-100 hover:bg-surface-900'
                          }`
                        }
                      >
                        <Icon className="w-4 h-4 flex-shrink-0" />
                        <span className="truncate">{link.label}</span>
                      </NavLink>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          {/* Sidebar Footer: Health status badge */}
          <div className="p-3 border-t border-surface-800 bg-surface-950/80 text-[11px] font-mono text-surface-400">
            <div className="flex items-center justify-between mb-1">
              <span>SYSTEM HEALTH</span>
              <span className="text-emerald-400 font-bold">
                {overview?.run?.health_percent ?? 99.9}%
              </span>
            </div>
            <div className="w-full bg-surface-800 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                style={{ width: `${overview?.run?.health_percent ?? 99.9}%` }}
              />
            </div>
          </div>
        </aside>

        {/* Center Main Workspace */}
        <main className="flex-1 overflow-auto flex flex-col bg-surface-950">
          <div className="flex-1 p-5 overflow-auto">
            <Outlet />
          </div>

          {/* Bottom Dock / Stream */}
          <div className="h-8 bg-surface-950 border-t border-surface-800 px-4 flex items-center justify-between text-[11px] font-mono text-surface-400 flex-shrink-0">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5">
                <span
                  className={`w-2 h-2 rounded-full ${
                    connectionStatus === 'connected' ? 'bg-emerald-400' : 'bg-amber-400 animate-ping'
                  }`}
                />
                <span className="text-surface-300 uppercase">{connectionStatus}</span>
              </div>
              <span>EVENTS: {overview?.events?.total ?? 0}</span>
              <span>
                ALERTS:{' '}
                <Link
                  to="/system/alerts"
                  data-testid="dock-alerts-link"
                  className={
                    (overview?.alert_counts?.CRITICAL ?? 0) > 0
                      ? 'text-rose-400 font-bold underline decoration-dotted hover:text-rose-300'
                      : 'underline decoration-dotted hover:text-surface-200'
                  }
                >
                  {overview?.alerts?.length ?? 0}
                </Link>
              </span>
            </div>

            <div className="flex items-center gap-3">
              <span>CHAIN: {overview?.events?.chain_valid ? '✓ VALID' : '✕ FAULT'}</span>
              <span>POLICY: {overview?.policy?.safety_status || 'NORMAL'}</span>
            </div>
          </div>
        </main>
      </div>

      {/* ── OVERLAYS & MODALS ────────────────────────────────────────────── */}
      <CommandPalette />
      <SystemTruthModal />
      <WhyBlockedModal />
      <FaultInjectionModal />
      <InspectorDrawer />
    </div>
  );
};

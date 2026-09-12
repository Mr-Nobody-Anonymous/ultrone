import React, { useState, useEffect, useRef } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  Wind,
  Sun,
  Cpu,
} from 'lucide-react';

interface ScenarioSpec {
  id: string;
  name: string;
  category: string;
  assetCount: number;
  objective: string;
  cohesionScore: number;
  collisionMarginMeters: number;
}

const SCENARIOS: ScenarioSpec[] = [
  {
    id: 'SCEN-01',
    name: 'DARPA OFFSET: Autonomous UAV Swarm Coordination',
    category: 'Swarm Tactics',
    assetCount: 16,
    objective: 'Surround and establish perimeter coverage around Sector Alpha',
    cohesionScore: 97.4,
    collisionMarginMeters: 320,
  },
  {
    id: 'SCEN-02',
    name: 'DARPA ACE: Radar Jamming & ECM Spoofing Intercept',
    category: 'Electronic Warfare',
    assetCount: 8,
    objective: 'Penetrate radar degradation zone while maintaining telemetry link',
    cohesionScore: 92.1,
    collisionMarginMeters: 280,
  },
  {
    id: 'SCEN-03',
    name: 'Multi-Domain Cross-Layer Search & Recon',
    category: 'Search & Recon',
    assetCount: 12,
    objective: 'Correlate ground and airborne sensors to identify unknown contact',
    cohesionScore: 98.8,
    collisionMarginMeters: 450,
  },
];

export const SimulationView: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const angleRef = useRef<number>(0);

  const [activeScenario, setActiveScenario] = useState<ScenarioSpec>(SCENARIOS[0]);
  const [isPlaying, setIsPlaying] = useState(true);
  const [speed, setSpeed] = useState<number>(1);
  const [weatherMode, setWeatherMode] = useState<'clear' | 'fog' | 'storm'>('clear');

  // Interactive 3D/Isometric canvas animation
  useEffect(() => {
    let animId: number;

    const render = () => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const dpr = window.devicePixelRatio || 1;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.scale(dpr, dpr);

      // Background
      ctx.fillStyle = '#020617';
      ctx.fillRect(0, 0, w, h);

      const cx = w / 2;
      const cy = h / 2 + 30;

      if (isPlaying) {
        angleRef.current += 0.005 * speed;
      }
      const angle = angleRef.current;

      // Draw 3D Isometric Grid Plane
      const gridSize = 14;
      const spacing = 32;

      ctx.save();
      ctx.translate(cx, cy);

      // Isometric projection transform
      for (let i = -gridSize; i <= gridSize; i++) {
        // Grid lines X
        const x1 = (i - gridSize) * spacing * 0.7;
        const y1 = (i + gridSize) * spacing * 0.35;
        const x2 = (i + gridSize) * spacing * 0.7;
        const y2 = (i - gridSize) * spacing * 0.35;

        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.strokeStyle = weatherMode === 'fog' ? 'rgba(56, 189, 248, 0.08)' : 'rgba(51, 65, 85, 0.3)';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Grid lines Y
        const gx1 = (-gridSize + i) * spacing * 0.7;
        const gy1 = (-gridSize - i) * spacing * 0.35;
        const gx2 = (gridSize + i) * spacing * 0.7;
        const gy2 = (gridSize - i) * spacing * 0.35;

        ctx.beginPath();
        ctx.moveTo(gx1, gy1);
        ctx.lineTo(gx2, gy2);
        ctx.strokeStyle = weatherMode === 'fog' ? 'rgba(56, 189, 248, 0.08)' : 'rgba(51, 65, 85, 0.3)';
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // Draw Swarm Simulation Assets in Isometric Space
      const swarmCount = activeScenario.assetCount;
      for (let s = 0; s < swarmCount; s++) {
        const offsetAngle = (s / swarmCount) * Math.PI * 2 + angle;
        const radius = 180 + Math.sin(s * 1.5 + angle * 2) * 40;
        const isoX = Math.cos(offsetAngle) * radius * 0.8;
        const isoY = Math.sin(offsetAngle) * radius * 0.4;
        const altitude = 60 + Math.cos(s + angle) * 20;

        // Ground shadow dot
        ctx.beginPath();
        ctx.ellipse(isoX, isoY, 6, 3, 0, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(56, 189, 248, 0.2)';
        ctx.fill();

        // Altitude drop pillar
        ctx.beginPath();
        ctx.moveTo(isoX, isoY);
        ctx.lineTo(isoX, isoY - altitude);
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.35)';
        ctx.setLineDash([2, 2]);
        ctx.stroke();
        ctx.setLineDash([]);

        // Swarm Asset Mesh
        ctx.beginPath();
        ctx.arc(isoX, isoY - altitude, 4.5, 0, Math.PI * 2);
        ctx.fillStyle = s % 2 === 0 ? '#38bdf8' : '#34d399';
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Label
        ctx.fillStyle = '#94a3b8';
        ctx.font = '9px JetBrains Mono, monospace';
        ctx.fillText(`UAV-${s + 1}`, isoX + 7, isoY - altitude + 3);
      }

      ctx.restore();

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animId);
  }, [isPlaying, speed, weatherMode, activeScenario]);

  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden bg-slate-950 font-mono select-none text-xs">
      {/* Canvas */}
      <canvas ref={canvasRef} className="h-full w-full cursor-grab" />

      {/* Top Left Scenario Selector */}
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-2 rounded-xl bg-slate-900/90 border border-slate-800 p-3 backdrop-blur shadow-2xl max-w-sm">
        <div className="flex items-center gap-2 text-ultrone-400 font-bold">
          <Cpu className="w-4 h-4" />
          <span className="uppercase tracking-wider">DARPA Experiment Scenario</span>
        </div>

        <select
          value={activeScenario.id}
          onChange={(e) => {
            const found = SCENARIOS.find((s) => s.id === e.target.value);
            if (found) setActiveScenario(found);
          }}
          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 outline-none cursor-pointer"
        >
          {SCENARIOS.map((scen) => (
            <option key={scen.id} value={scen.id}>
              {scen.name}
            </option>
          ))}
        </select>

        <p className="text-[11px] text-slate-400 leading-relaxed">
          Objective: <strong className="text-slate-200">{activeScenario.objective}</strong>
        </p>

        {/* Live Evaluation Metrics */}
        <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/80 text-[10px]">
          <div className="p-2 rounded bg-slate-950 border border-slate-800/60">
            <span className="text-slate-500 block">Swarm Cohesion</span>
            <span className="font-bold text-emerald-400">{activeScenario.cohesionScore}%</span>
          </div>
          <div className="p-2 rounded bg-slate-950 border border-slate-800/60">
            <span className="text-slate-500 block">Collision Margin</span>
            <span className="font-bold text-cyan-300">&gt;{activeScenario.collisionMarginMeters} m</span>
          </div>
        </div>
      </div>

      {/* Top Right Weather & Environment Settings */}
      <div className="absolute top-4 right-4 z-10 flex items-center gap-2 rounded-lg bg-slate-900/90 border border-slate-800 p-1.5 backdrop-blur shadow-lg">
        <button
          onClick={() => setWeatherMode('clear')}
          className={`flex items-center gap-1 px-2.5 py-1 rounded transition-colors ${
            weatherMode === 'clear'
              ? 'bg-slate-800 text-slate-100 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sun className="w-3.5 h-3.5 text-amber-400" />
          <span>Clear</span>
        </button>
        <button
          onClick={() => setWeatherMode('fog')}
          className={`flex items-center gap-1 px-2.5 py-1 rounded transition-colors ${
            weatherMode === 'fog'
              ? 'bg-slate-800 text-slate-100 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Wind className="w-3.5 h-3.5 text-cyan-400" />
          <span>Fog/ECM</span>
        </button>
      </div>

      {/* Bottom Playback Dock */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 flex items-center gap-3 rounded-xl bg-slate-900/95 border border-slate-800 px-4 py-2 shadow-2xl backdrop-blur">
        <button
          onClick={() => setIsPlaying((p) => !p)}
          className="flex h-9 w-9 items-center justify-center rounded-lg bg-ultrone-600 hover:bg-ultrone-500 text-white transition-colors"
          title={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 fill-current" />}
        </button>

        <button
          onClick={() => {
            angleRef.current = 0;
          }}
          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700 transition-colors"
          title="Reset Simulation"
        >
          <RotateCcw className="w-4 h-4" />
        </button>

        <div className="h-4 w-px bg-slate-800" />

        <div className="flex items-center gap-1 text-xs">
          {[1, 2, 4].map((s) => (
            <button
              key={s}
              onClick={() => setSpeed(s)}
              className={`px-2 py-1 rounded font-mono text-[11px] transition-colors ${
                speed === s
                  ? 'bg-slate-800 text-ultrone-400 font-bold border border-slate-700'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SimulationView;

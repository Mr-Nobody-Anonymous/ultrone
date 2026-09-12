import React, { useState, useEffect, useRef } from 'react';
import { useWorldStore } from '../store/worldStore';
import {
  Play,
  Pause,
  RotateCcw,
  Box,
  Wind,
  Sun,
} from 'lucide-react';

export const SimulationView: React.FC = () => {
  const entities = useWorldStore((s) => s.entities);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const [isPlaying, setIsPlaying] = useState(true);
  const [speed, setSpeed] = useState<number>(1);
  const [simTick, setSimTick] = useState<number>(0);
  const [weatherMode, setWeatherMode] = useState<'clear' | 'fog' | 'storm'>('clear');

  // Interactive 3D/Isometric canvas animation
  useEffect(() => {
    let animId: number;
    let angle = 0;

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
      const cy = h / 2 + 40;

      if (isPlaying) {
        angle += 0.004 * speed;
        setSimTick((t) => t + 1);
      }

      // Draw 3D Isometric Grid Plane
      const gridSize = 14;
      const spacing = 32;

      ctx.save();
      ctx.translate(cx, cy);

      // Isometric projection transform
      for (let i = -gridSize; i <= gridSize; i++) {
        // Grid lines X
        const x1 = (i * spacing) * Math.cos(angle) - (-gridSize * spacing) * Math.sin(angle);
        const y1 = ((i * spacing) * Math.sin(angle) + (-gridSize * spacing) * Math.cos(angle)) * 0.45;
        const x2 = (i * spacing) * Math.cos(angle) - (gridSize * spacing) * Math.sin(angle);
        const y2 = ((i * spacing) * Math.sin(angle) + (gridSize * spacing) * Math.cos(angle)) * 0.45;

        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.strokeStyle = i === 0 ? 'rgba(56, 189, 248, 0.35)' : 'rgba(30, 41, 59, 0.5)';
        ctx.lineWidth = i === 0 ? 1.5 : 1;
        ctx.stroke();

        // Grid lines Y
        const x3 = (-gridSize * spacing) * Math.cos(angle) - (i * spacing) * Math.sin(angle);
        const y3 = ((-gridSize * spacing) * Math.sin(angle) + (i * spacing) * Math.cos(angle)) * 0.45;
        const x4 = (gridSize * spacing) * Math.cos(angle) - (i * spacing) * Math.sin(angle);
        const y4 = ((gridSize * spacing) * Math.sin(angle) + (i * spacing) * Math.cos(angle)) * 0.45;

        ctx.beginPath();
        ctx.moveTo(x3, y3);
        ctx.lineTo(x4, y4);
        ctx.strokeStyle = i === 0 ? 'rgba(56, 189, 248, 0.35)' : 'rgba(30, 41, 59, 0.5)';
        ctx.lineWidth = i === 0 ? 1.5 : 1;
        ctx.stroke();
      }

      // Draw simulated 3D entities
      entities.forEach((ent, idx) => {
        const entOffsetAngle = (idx / entities.length) * Math.PI * 2 + angle;
        const radius = 180 + (idx % 3) * 40;
        const ex = Math.cos(entOffsetAngle) * radius;
        const ey = (Math.sin(entOffsetAngle) * radius) * 0.45;
        const altitude = ent.type === 'air_asset' ? 90 : 20;

        // Ground shadow
        ctx.beginPath();
        ctx.ellipse(ex, ey, 14, 6, 0, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(15, 23, 42, 0.7)';
        ctx.fill();

        // Altitude tether line
        ctx.beginPath();
        ctx.moveTo(ex, ey);
        ctx.lineTo(ex, ey - altitude);
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.25)';
        ctx.setLineDash([2, 2]);
        ctx.stroke();
        ctx.setLineDash([]);

        // Elevated entity marker
        const color =
          ent.type === 'air_asset'
            ? '#38bdf8'
            : ent.type === 'ground_unit'
            ? '#34d399'
            : ent.type === 'sensor_station'
            ? '#818cf8'
            : '#f43f5e';

        ctx.beginPath();
        ctx.arc(ex, ey - altitude, 8, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Entity label
        ctx.fillStyle = '#f8fafc';
        ctx.font = '10px JetBrains Mono, monospace';
        ctx.fillText(ent.entity_id, ex + 12, ey - altitude + 3);
      });

      ctx.restore();

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animId);
  }, [isPlaying, speed, entities, weatherMode]);

  return (
    <div className="relative h-full w-full bg-slate-950 overflow-hidden font-mono select-none">
      {/* 3D Canvas */}
      <canvas ref={canvasRef} className="h-full w-full" />

      {/* Top Floating Simulation HUD */}
      <div className="absolute top-4 left-4 z-10 flex items-center gap-3">
        <div className="flex items-center gap-2 rounded-lg bg-slate-900/90 border border-slate-800 px-3 py-1.5 backdrop-blur shadow-lg">
          <Box className="w-4 h-4 text-ultrone-400" />
          <span className="text-xs font-bold text-slate-100 uppercase tracking-wider">
            3D Simulation Sandbox
          </span>
          <span className="text-[10px] text-cyan-400 bg-cyan-950/60 border border-cyan-800/60 px-2 py-0.5 rounded">
            TICK: {simTick}
          </span>
        </div>
      </div>

      {/* Top Right Weather & Environment Settings */}
      <div className="absolute top-4 right-4 z-10 flex items-center gap-2 rounded-lg bg-slate-900/90 border border-slate-800 p-1.5 backdrop-blur shadow-lg text-xs">
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
          onClick={() => setSimTick(0)}
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

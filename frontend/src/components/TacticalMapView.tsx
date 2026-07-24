import type { FC } from 'react';
import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { useSimulation } from '../contexts/SimulationContext';
import { Map, Layers, ZoomIn, ZoomOut, Crosshair, Maximize2 } from 'lucide-react';

// Simulated canvas-based tactical map - no Leaflet dependency needed
const TacticalMapView: FC<{ widget: any }> = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { worldState, selectedAgent, selectAgent } = useSimulation();
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  // Draw the tactical map
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;

    // Clear
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, w, h);

    // Grid
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 0.5;
    for (let x = 0; x < w; x += 50) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    for (let y = 0; y < h; y += 50) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    if (!worldState) {
      ctx.fillStyle = '#475569';
      ctx.font = '14px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Waiting for simulation data...', w / 2, h / 2);
      return;
    }

    // Draw supply nodes
    worldState.supplyNodes?.forEach(node => {
      const [x, y] = node.position;
      ctx.fillStyle = node.alive ? '#22c55e' : '#ef4444';
      ctx.beginPath();
      ctx.arc(x * (w / 100), y * (h / 100), 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = node.alive ? '#16a34a' : '#dc2626';
      ctx.lineWidth = 2;
      ctx.stroke();
    });

    // Draw friendly agents
    worldState.agents?.filter(a => a.status !== 'destroyed').forEach(agent => {
      const [x, y] = agent.position;
      const sx = x * (w / 100) * zoom + offset.x;
      const sy = y * (h / 100) * zoom + offset.y;

      // Agent circle
      const gradient = ctx.createRadialGradient(sx, sy, 2, sx, sy, 10);
      gradient.addColorStop(0, '#3b82f6');
      gradient.addColorStop(1, '#1d4ed8');
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(sx, sy, 8, 0, Math.PI * 2);
      ctx.fill();

      // Health ring
      ctx.strokeStyle = agent.health > 50 ? '#22c55e' : agent.health > 25 ? '#f59e0b' : '#ef4444';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(sx, sy, 11, 0, (agent.health / 100) * Math.PI * 2);
      ctx.stroke();

      // Threat ring
      if (agent.threatLevel > 0.7) {
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.3)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(sx, sy, 20, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Label
      ctx.fillStyle = '#e2e8f0';
      ctx.font = '8px JetBrains Mono, monospace';
      ctx.textAlign = 'center';
      ctx.fillText(agent.id.slice(0, 6), sx, sy - 16);
    });

    // Draw threats
    worldState.threats?.forEach(threat => {
      const [x, y] = threat.position;
      const sx = x * (w / 100) * zoom + offset.x;
      const sy = y * (h / 100) * zoom + offset.y;

      ctx.fillStyle = '#ef4444';
      ctx.beginPath();
      ctx.moveTo(sx, sy - 8);
      ctx.lineTo(sx + 6, sy + 6);
      ctx.lineTo(sx - 6, sy + 6);
      ctx.closePath();
      ctx.fill();

      // Confidence text
      ctx.fillStyle = `rgba(239, 68, 68, ${threat.confidence})`;
      ctx.font = '7px JetBrains Mono';
      ctx.textAlign = 'center';
      ctx.fillText(`${(threat.confidence * 100).toFixed(0)}%`, sx, sy + 18);
    });

    // Legend
    ctx.fillStyle = 'rgba(15, 23, 42, 0.8)';
    ctx.fillRect(8, h - 48, 120, 40);
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 1;
    ctx.strokeRect(8, h - 48, 120, 40);

    ctx.fillStyle = '#3b82f6';
    ctx.beginPath();
    ctx.arc(22, h - 32, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#94a3b8';
    ctx.font = '9px Inter';
    ctx.textAlign = 'left';
    ctx.fillText('Friendly', 32, h - 29);

    ctx.fillStyle = '#ef4444';
    ctx.beginPath();
    ctx.moveTo(22, h - 18);
    ctx.lineTo(26, h - 14);
    ctx.lineTo(18, h - 14);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('Threat', 32, h - 15);

  }, [worldState, zoom, offset]);

  return (
    <div className="relative h-full flex flex-col">
      <div className="flex items-center justify-between px-3 py-2 border-b border-surface-700/30">
        <div className="flex items-center gap-2">
          <Map size={14} className="text-primary-400" />
          <span className="text-xs font-semibold text-surface-300">Tactical Map</span>
        </div>
        <div className="flex items-center gap-1">
          <button className="btn-ghost p-1" onClick={() => setZoom(z => Math.min(z + 0.2, 3))}><ZoomIn size={14} /></button>
          <button className="btn-ghost p-1" onClick={() => setZoom(z => Math.max(z - 0.2, 0.5))}><ZoomOut size={14} /></button>
          <button className="btn-ghost p-1"><Maximize2 size={14} /></button>
        </div>
      </div>
      <div className="flex-1 relative overflow-hidden">
        <canvas
          ref={canvasRef}
          width={800}
          height={600}
          className="w-full h-full"
        />
      </div>
    </div>
  );
};

export default TacticalMapView;

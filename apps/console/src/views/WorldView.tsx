import React, { useRef, useEffect, useState } from 'react';
import { useEntityStream } from '../hooks/useEntityStream';
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
} from 'lucide-react';
import type { Entity } from '../types/entity';

export const WorldView: React.FC = () => {
  const { entities, selectedEntity, selectEntity } = useEntityStream();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [mapMode, setMapMode] = useState<'tactical' | 'satellite' | 'grid'>('tactical');
  const [radarSweep, setRadarSweep] = useState(0);

  // Radar sweep animation
  useEffect(() => {
    let animId: number;
    const animate = () => {
      setRadarSweep((prev) => (prev + 1.2) % 360);
      animId = requestAnimationFrame(animate);
    };
    animId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animId);
  }, []);

  // Center coordinates calculation (around Los Angeles / Southern Cal test zone)
  const baseLat = 34.05;
  const baseLng = -118.25;

  // Render tactical canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Handle high DPI
    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    // Clear background
    ctx.fillStyle = mapMode === 'satellite' ? '#090d16' : '#020617';
    ctx.fillRect(0, 0, width, height);

    const centerX = width / 2 + pan.x;
    const centerY = height / 2 + pan.y;
    const scale = 2200 * zoom;

    // Draw Tactical Grid
    ctx.strokeStyle = mapMode === 'tactical' ? 'rgba(30, 41, 59, 0.4)' : 'rgba(51, 65, 85, 0.3)';
    ctx.lineWidth = 1;
    const gridSize = 50 * zoom;

    const startX = (centerX % gridSize) - gridSize;
    for (let x = startX; x < width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }

    const startY = (centerY % gridSize) - gridSize;
    for (let y = startY; y < height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Range Rings from center
    const ringRadii = [100, 200, 300, 400];
    ringRadii.forEach((r) => {
      const radius = r * zoom;
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.12)';
      ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.setLineDash([]);

      // Ring distance labels
      ctx.fillStyle = 'rgba(56, 189, 248, 0.35)';
      ctx.font = '10px JetBrains Mono, monospace';
      ctx.fillText(`${r} NM`, centerX + radius + 4, centerY - 4);
    });

    // Radar Sweep line
    const sweepRad = (radarSweep * Math.PI) / 180;
    const sweepLen = 400 * zoom;
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.lineTo(
      centerX + Math.cos(sweepRad) * sweepLen,
      centerY + Math.sin(sweepRad) * sweepLen
    );
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.25)';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Draw relationships as connecting links
    entities.forEach((ent) => {
      if (!ent.position || !ent.relationships) return;
      const x1 = centerX + (ent.position.lng - baseLng) * scale;
      const y1 = centerY - (ent.position.lat - baseLat) * scale;

      ent.relationships.forEach((rel) => {
        const target = entities.find((t) => t.entity_id === rel.target_id);
        if (target && target.position) {
          const x2 = centerX + (target.position.lng - baseLng) * scale;
          const y2 = centerY - (target.position.lat - baseLat) * scale;

          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.strokeStyle =
            rel.relation === 'tracks'
              ? 'rgba(244, 63, 94, 0.3)'
              : rel.relation === 'observes'
              ? 'rgba(34, 211, 238, 0.3)'
              : 'rgba(148, 163, 184, 0.2)';
          ctx.setLineDash([2, 4]);
          ctx.stroke();
          ctx.setLineDash([]);
        }
      });
    });

    // Draw entities
    entities.forEach((ent) => {
      if (!ent.position) return;
      const x = centerX + (ent.position.lng - baseLng) * scale;
      const y = centerY - (ent.position.lat - baseLat) * scale;

      const isSel = selectedEntity?.entity_id === ent.entity_id;

      // Selection Halo
      if (isSel) {
        ctx.beginPath();
        ctx.arc(x, y, 22, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(92, 124, 250, 0.8)';
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(x, y, 28, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(92, 124, 250, 0.3)';
        ctx.setLineDash([3, 3]);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Entity symbol colors
      const color =
        ent.type === 'air_asset'
          ? '#38bdf8'
          : ent.type === 'ground_unit'
          ? '#34d399'
          : ent.type === 'sensor_station'
          ? '#818cf8'
          : '#f43f5e';

      // Dot / Core
      ctx.beginPath();
      ctx.arc(x, y, 7, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();

      // Velocity heading vector
      if (ent.velocity) {
        const vLen = 25;
        const angle = Math.atan2(ent.velocity.y, ent.velocity.x);
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x + Math.cos(angle) * vLen, y - Math.sin(angle) * vLen);
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // Label
      ctx.fillStyle = isSel ? '#ffffff' : '#cbd5e1';
      ctx.font = '11px JetBrains Mono, monospace';
      ctx.fillText(ent.entity_id, x + 12, y - 4);

      ctx.fillStyle = '#64748b';
      ctx.font = '9px JetBrains Mono, monospace';
      const altStr = ent.position.alt ? `${ent.position.alt}ft` : ent.type;
      ctx.fillText(altStr, x + 12, y + 8);
    });
  }, [entities, selectedEntity, zoom, pan, mapMode, radarSweep]);

  // Click on canvas to select entity
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    const centerX = width / 2 + pan.x;
    const centerY = height / 2 + pan.y;
    const scale = 2200 * zoom;

    // Find closest entity within click threshold
    let closest: Entity | null = null;
    let minDistance = 25; // px

    entities.forEach((ent) => {
      if (!ent.position) return;
      const x = centerX + (ent.position.lng - baseLng) * scale;
      const y = centerY - (ent.position.lat - baseLat) * scale;
      const dist = Math.hypot(clickX - x, clickY - y);
      if (dist < minDistance) {
        minDistance = dist;
        closest = ent;
      }
    });

    selectEntity(closest);
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  };

  const handleMouseUp = () => setIsDragging(false);

  return (
    <div className="relative h-full w-full bg-slate-950 overflow-hidden select-none">
      {/* Interactive Tactical Canvas */}
      <canvas
        ref={canvasRef}
        onClick={handleCanvasClick}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className="h-full w-full cursor-crosshair"
      />

      {/* Top Floating Controls */}
      <div className="absolute top-4 left-4 flex items-center gap-2 z-10">
        <div className="flex items-center rounded-lg bg-slate-900/90 border border-slate-800 p-1 shadow-lg backdrop-blur">
          <button
            onClick={() => setMapMode('tactical')}
            className={`px-3 py-1 text-xs font-mono rounded transition-colors ${
              mapMode === 'tactical'
                ? 'bg-ultrone-600/30 text-ultrone-300 font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Tactical
          </button>
          <button
            onClick={() => setMapMode('satellite')}
            className={`px-3 py-1 text-xs font-mono rounded transition-colors ${
              mapMode === 'satellite'
                ? 'bg-ultrone-600/30 text-ultrone-300 font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Dark Satellite
          </button>
          <button
            onClick={() => setMapMode('grid')}
            className={`px-3 py-1 text-xs font-mono rounded transition-colors ${
              mapMode === 'grid'
                ? 'bg-ultrone-600/30 text-ultrone-300 font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Grid Mesh
          </button>
        </div>
      </div>

      {/* Top Right Coordinate Overlay */}
      <div className="absolute top-4 right-4 z-10 font-mono text-[11px] rounded-lg bg-slate-900/90 border border-slate-800 p-2.5 space-y-1 backdrop-blur shadow-lg">
        <div className="flex justify-between gap-4">
          <span className="text-slate-500 uppercase">LAT/LON CENTER:</span>
          <span className="text-slate-200">
            {baseLat.toFixed(2)}°N, {Math.abs(baseLng).toFixed(2)}°W
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-slate-500 uppercase">ZOOM FACTOR:</span>
          <span className="text-cyan-400 font-semibold">{zoom.toFixed(2)}x</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-slate-500 uppercase">TRACKED ENTITIES:</span>
          <span className="text-emerald-400 font-semibold">{entities.length} active</span>
        </div>
      </div>

      {/* Bottom Right Floating Zoom & Pan Controls */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-1.5 z-10">
        <button
          onClick={() => setZoom((z) => Math.min(3.5, z * 1.25))}
          className="p-2 rounded-lg bg-slate-900/90 hover:bg-slate-800 border border-slate-800 text-slate-300 shadow-lg backdrop-blur"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={() => setZoom((z) => Math.max(0.4, z / 1.25))}
          className="p-2 rounded-lg bg-slate-900/90 hover:bg-slate-800 border border-slate-800 text-slate-300 shadow-lg backdrop-blur"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={() => {
            setZoom(1);
            setPan({ x: 0, y: 0 });
          }}
          className="p-2 rounded-lg bg-slate-900/90 hover:bg-slate-800 border border-slate-800 text-slate-300 shadow-lg backdrop-blur"
          title="Reset View"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      {/* Bottom Left Legend */}
      <div className="absolute bottom-4 left-4 z-10 flex items-center gap-4 rounded-lg bg-slate-900/90 border border-slate-800 px-3 py-1.5 backdrop-blur font-mono text-[10px]">
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-sky-400" />
          <span className="text-slate-300">Air</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-emerald-400" />
          <span className="text-slate-300">Ground</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-indigo-400" />
          <span className="text-slate-300">Sensors</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-rose-400" />
          <span className="text-slate-300">Target</span>
        </div>
      </div>
    </div>
  );
};

export default WorldView;

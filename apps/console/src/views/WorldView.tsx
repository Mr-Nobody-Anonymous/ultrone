import React, { useRef, useEffect, useState } from 'react';
import { useEntityStream } from '../hooks/useEntityStream';
import { useLayerStore } from '../store/layerStore';
import LayerManager from '../components/LayerManager';
import TimeScrubber from '../components/TimeScrubber';
import EntityDetailDrawer from '../components/EntityDetailDrawer';
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Layers,
} from 'lucide-react';
import type { Entity } from '../types/entity';

export const WorldView: React.FC = () => {
  const { entities, selectedEntity, selectEntity } = useEntityStream();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const { layers, toggleLayerDrawer, isLayerDrawerOpen } = useLayerStore();

  const [dimensionMode, setDimensionMode] = useState<'2D' | '3D'>('2D');
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [pitch, setPitch] = useState(45); // For 3D mode
  const [yaw, setYaw] = useState(30);     // For 3D mode
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
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

  // Layer check helpers
  const isBaseDark = layers.find((l) => l.id === 'base-dark')?.enabled ?? true;
  const isSatellite = layers.find((l) => l.id === 'base-satellite')?.enabled ?? false;
  const isSensorsEnabled = layers.find((l) => l.id === 'ent-sensors')?.enabled ?? true;
  const isAirEnabled = layers.find((l) => l.id === 'ent-air')?.enabled ?? true;
  const isGroundEnabled = layers.find((l) => l.id === 'ent-ground')?.enabled ?? true;
  const isRadarCones = layers.find((l) => l.id === 'env-radar-cones')?.enabled ?? true;
  const isTrajectories = layers.find((l) => l.id === 'anl-trajectories')?.enabled ?? true;
  const isDensity = layers.find((l) => l.id === 'anl-density')?.enabled ?? false;

  // Render tactical canvas (2D Plan-view or 3D Globe Projection)
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
    ctx.fillStyle = isSatellite ? '#060913' : '#020617';
    ctx.fillRect(0, 0, width, height);

    const centerX = width / 2 + pan.x;
    const centerY = height / 2 + pan.y;
    const scale = 2200 * zoom;

    if (dimensionMode === '2D') {
      // ══════════════════════════════════════════════════════════════
      // 2D PLAN-VIEW TACTICAL RADAR CANVAS
      // ══════════════════════════════════════════════════════════════

      // Tactical Grid
      if (isBaseDark) {
        ctx.strokeStyle = 'rgba(30, 41, 59, 0.4)';
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
      }

      // Range Rings
      const ringRadii = [100, 200, 300, 400];
      ringRadii.forEach((r) => {
        const radius = r * zoom;
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.12)';
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.fillStyle = 'rgba(56, 189, 248, 0.35)';
        ctx.font = '10px JetBrains Mono, monospace';
        ctx.fillText(`${r} NM`, centerX + radius + 4, centerY - 4);
      });

      // Radar Sweep
      if (isRadarCones) {
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
      }

      // Density heatmap simulation
      if (isDensity) {
        entities.forEach((ent) => {
          if (!ent.position) return;
          const ex = centerX + (ent.position.lng - baseLng) * scale;
          const ey = centerY - (ent.position.lat - baseLat) * scale;
          const grad = ctx.createRadialGradient(ex, ey, 5, ex, ey, 60 * zoom);
          grad.addColorStop(0, 'rgba(239, 68, 68, 0.35)');
          grad.addColorStop(0.5, 'rgba(245, 158, 11, 0.15)');
          grad.addColorStop(1, 'rgba(245, 158, 11, 0)');
          ctx.fillStyle = grad;
          ctx.beginPath();
          ctx.arc(ex, ey, 60 * zoom, 0, Math.PI * 2);
          ctx.fill();
        });
      }

      // Entity Links
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
              rel.relation === 'observes'
                ? 'rgba(56, 189, 248, 0.35)'
                : 'rgba(148, 163, 184, 0.2)';
            ctx.lineWidth = 1;
            ctx.setLineDash([3, 3]);
            ctx.stroke();
            ctx.setLineDash([]);
          }
        });
      });

      // Draw Entities
      entities.forEach((ent) => {
        if (!ent.position) return;

        // Filter based on active layers
        if (ent.type === 'sensor' && !isSensorsEnabled) return;
        if (ent.type === 'air_asset' && !isAirEnabled) return;
        if (ent.type === 'ground_vehicle' && !isGroundEnabled) return;

        const x = centerX + (ent.position.lng - baseLng) * scale;
        const y = centerY - (ent.position.lat - baseLat) * scale;

        const isSelected = selectedEntity?.entity_id === ent.entity_id;

        // Kinematic trajectory vector
        if (isTrajectories && ent.velocity) {
          const vx = (ent.velocity.x / 4) * zoom;
          const vy = (-ent.velocity.y / 4) * zoom;
          ctx.beginPath();
          ctx.moveTo(x, y);
          ctx.lineTo(x + vx, y + vy);
          ctx.strokeStyle = 'rgba(56, 189, 248, 0.5)';
          ctx.lineWidth = 1.5;
          ctx.stroke();
        }

        // Contact Marker
        ctx.beginPath();
        const markerRadius = isSelected ? 8 : 5;
        ctx.arc(x, y, markerRadius, 0, Math.PI * 2);

        let color = '#94a3b8';
        if (ent.type === 'air_asset') color = '#38bdf8';
        else if (ent.type === 'ground_vehicle') color = '#34d399';
        else if (ent.type === 'sensor') color = '#818cf8';

        ctx.fillStyle = color;
        ctx.fill();
        ctx.lineWidth = isSelected ? 2.5 : 1.5;
        ctx.strokeStyle = isSelected ? '#ffffff' : '#0f172a';
        ctx.stroke();

        // Selection Pulsing Ring
        if (isSelected) {
          ctx.beginPath();
          ctx.arc(x, y, 14, 0, Math.PI * 2);
          ctx.strokeStyle = 'rgba(56, 189, 248, 0.6)';
          ctx.lineWidth = 1;
          ctx.setLineDash([2, 2]);
          ctx.stroke();
          ctx.setLineDash([]);
        }

        // Callsign / ID Label
        ctx.fillStyle = isSelected ? '#ffffff' : '#94a3b8';
        ctx.font = '10px JetBrains Mono, monospace';
        ctx.fillText(ent.entity_id, x + 10, y + 3);
      });
    } else {
      // ══════════════════════════════════════════════════════════════
      // 3D GLOBE / ISOMETRIC SPATIAL ELEVATION PROJECTION
      // ══════════════════════════════════════════════════════════════

      // 3D Grid & Terrain Elevation Mesh
      const radPitch = (pitch * Math.PI) / 180;
      const radYaw = (yaw * Math.PI) / 180;
      const cosYaw = Math.cos(radYaw);
      const sinYaw = Math.sin(radYaw);
      const sinPitch = Math.sin(radPitch);
      const cosPitch = Math.cos(radPitch);

      const project3D = (gx: number, gy: number, gz: number) => {
        // Rotate around Y (yaw)
        const rx = gx * cosYaw - gy * sinYaw;
        const ry = gx * sinYaw + gy * cosYaw;
        // Tilt (pitch)
        const px = rx;
        const py = ry * sinPitch - gz * cosPitch;
        return {
          x: centerX + px * scale,
          y: centerY + py * scale,
        };
      };

      // Draw 3D Ground Elevation Grid
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.12)';
      ctx.lineWidth = 1;
      const gridSteps = 12;
      const stepSize = 0.04;

      for (let i = -gridSteps / 2; i <= gridSteps / 2; i++) {
        const p1 = project3D(i * stepSize, (-gridSteps / 2) * stepSize, 0);
        const p2 = project3D(i * stepSize, (gridSteps / 2) * stepSize, 0);
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();

        const q1 = project3D((-gridSteps / 2) * stepSize, i * stepSize, 0);
        const q2 = project3D((gridSteps / 2) * stepSize, i * stepSize, 0);
        ctx.beginPath();
        ctx.moveTo(q1.x, q1.y);
        ctx.lineTo(q2.x, q2.y);
        ctx.stroke();
      }

      // Draw 3D Entities with Altitude Pillars
      entities.forEach((ent) => {
        if (!ent.position) return;
        const dx = ent.position.lng - baseLng;
        const dy = ent.position.lat - baseLat;
        const altMeters = (ent.position.alt || 0) * 0.00003; // Scale altitude to visual height

        const groundPos = project3D(dx, dy, 0);
        const airPos = project3D(dx, dy, altMeters);

        const isSelected = selectedEntity?.entity_id === ent.entity_id;

        // Altitude Drop Pillar
        if (ent.position.alt && ent.position.alt > 0) {
          ctx.beginPath();
          ctx.moveTo(groundPos.x, groundPos.y);
          ctx.lineTo(airPos.x, airPos.y);
          ctx.strokeStyle = 'rgba(56, 189, 248, 0.4)';
          ctx.lineWidth = 1;
          ctx.setLineDash([2, 2]);
          ctx.stroke();
          ctx.setLineDash([]);

          // Ground shadow dot
          ctx.beginPath();
          ctx.arc(groundPos.x, groundPos.y, 2.5, 0, Math.PI * 2);
          ctx.fillStyle = 'rgba(56, 189, 248, 0.3)';
          ctx.fill();
        }

        // 3D Elevated Asset Marker
        ctx.beginPath();
        ctx.arc(airPos.x, airPos.y, isSelected ? 8 : 5, 0, Math.PI * 2);
        ctx.fillStyle = ent.type === 'air_asset' ? '#38bdf8' : ent.type === 'ground_vehicle' ? '#34d399' : '#818cf8';
        ctx.fill();
        ctx.lineWidth = isSelected ? 2 : 1;
        ctx.strokeStyle = isSelected ? '#ffffff' : '#0f172a';
        ctx.stroke();

        // Label with Altitude
        ctx.fillStyle = isSelected ? '#ffffff' : '#94a3b8';
        ctx.font = '10px JetBrains Mono, monospace';
        const altLabel = ent.position.alt ? ` [${ent.position.alt}ft]` : '';
        ctx.fillText(`${ent.entity_id}${altLabel}`, airPos.x + 8, airPos.y + 3);
      });
    }
  }, [
    zoom,
    pan,
    pitch,
    yaw,
    dimensionMode,
    entities,
    selectedEntity,
    radarSweep,
    layers,
    isSatellite,
    isBaseDark,
    isSensorsEnabled,
    isAirEnabled,
    isGroundEnabled,
    isRadarCones,
    isTrajectories,
    isDensity,
  ]);

  // Click on canvas to select contact
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

    let clicked: Entity | null = null;
    entities.forEach((ent) => {
      if (!ent.position) return;
      const x = centerX + (ent.position.lng - baseLng) * scale;
      const y = centerY - (ent.position.lat - baseLat) * scale;
      const dist = Math.hypot(clickX - x, clickY - y);
      if (dist < 15) {
        clicked = ent;
      }
    });

    selectEntity(clicked);
  };

  // Mouse pan handlers
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
    <div className="relative flex h-full w-full flex-col overflow-hidden bg-slate-950 font-mono select-none">
      {/* Top Floating Action Bar */}
      <div className="absolute top-4 left-4 right-4 z-30 flex items-center justify-between pointer-events-none">
        {/* Left: 2D/3D Mode & Layer Manager Toggle */}
        <div className="flex items-center gap-2 pointer-events-auto">
          {/* 2D ↔ 3D Switcher */}
          <div className="flex items-center rounded-xl bg-slate-900/90 border border-slate-800 p-1 shadow-xl backdrop-blur">
            <button
              onClick={() => setDimensionMode('2D')}
              className={`px-3 py-1 text-xs rounded-lg font-bold transition-colors ${
                dimensionMode === '2D'
                  ? 'bg-ultrone-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              2D TACTICAL
            </button>
            <button
              onClick={() => setDimensionMode('3D')}
              className={`px-3 py-1 text-xs rounded-lg font-bold transition-colors ${
                dimensionMode === '3D'
                  ? 'bg-ultrone-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              3D GLOBE
            </button>
          </div>

          {/* Layer Manager Drawer Toggle */}
          <button
            onClick={toggleLayerDrawer}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold shadow-xl backdrop-blur transition-colors ${
              isLayerDrawerOpen
                ? 'bg-ultrone-600/20 text-ultrone-300 border-ultrone-500/40'
                : 'bg-slate-900/90 text-slate-300 border-slate-800 hover:bg-slate-800'
            }`}
          >
            <Layers className="w-3.5 h-3.5 text-ultrone-400" />
            <span>LAYERS ({layers.filter((l) => l.enabled).length})</span>
          </button>
        </div>

        {/* Right: Sector & Mode Readout */}
        <div className="pointer-events-auto flex items-center gap-2">
          <div className="rounded-xl bg-slate-900/90 border border-slate-800 px-3 py-1.5 text-xs text-slate-300 backdrop-blur shadow-xl">
            <span className="text-slate-500 mr-1.5">SECTOR:</span>
            <span className="font-bold text-slate-100">SOUTHERN CAL [34.05°N, 118.25°W]</span>
          </div>
        </div>
      </div>

      {/* Layer Manager Flyout */}
      <LayerManager />

      {/* Canvas */}
      <canvas
        ref={canvasRef}
        onClick={handleCanvasClick}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className="h-full w-full cursor-crosshair"
      />

      {/* 3D Orbit Controls in 3D Mode */}
      {dimensionMode === '3D' && (
        <div className="absolute top-16 right-4 z-20 flex flex-col gap-2 rounded-xl bg-slate-900/90 border border-slate-800 p-2.5 shadow-xl backdrop-blur text-xs">
          <span className="text-[10px] text-slate-500 uppercase font-bold">Orbital Tilt & Yaw</span>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-400 w-8">PITCH</span>
            <input
              type="range"
              min="15"
              max="85"
              value={pitch}
              onChange={(e) => setPitch(parseInt(e.target.value))}
              className="accent-ultrone-500 h-1 w-20"
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-400 w-8">YAW</span>
            <input
              type="range"
              min="-180"
              max="180"
              value={yaw}
              onChange={(e) => setYaw(parseInt(e.target.value))}
              className="accent-ultrone-500 h-1 w-20"
            />
          </div>
        </div>
      )}

      {/* Bottom Floating Zoom & Pan Controls */}
      <div className="absolute bottom-20 right-4 flex flex-col gap-1.5 z-20">
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
            setPitch(45);
            setYaw(30);
          }}
          className="p-2 rounded-lg bg-slate-900/90 hover:bg-slate-800 border border-slate-800 text-slate-300 shadow-lg backdrop-blur"
          title="Reset Camera"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      {/* Bottom Docked Time Scrubber Bar */}
      <div className="absolute bottom-4 left-4 right-20 z-20">
        <TimeScrubber />
      </div>

      {/* Palantir-Style 8-Tab Entity Detail Drawer */}
      {selectedEntity && (
        <EntityDetailDrawer
          entity={selectedEntity}
          onClose={() => selectEntity(null)}
        />
      )}
    </div>
  );
};

export default WorldView;

// Copyright (c) Ultrone Contributors. All rights reserved.
import React, { useRef, useEffect, useState } from 'react';
import { useCockpitStore } from '../../stores/cockpitStore';
import {
  Layers,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Crosshair,
  Radio,
  Eye,
  Shield,
  Compass,
} from 'lucide-react';
import { StatusBadge } from '../../components/ui/StatusBadge';

export const SimulationWorldView: React.FC = () => {
  const { world, inspect } = useCockpitStore();
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Layers state
  const [showGroundTruth, setShowGroundTruth] = useState(true);
  const [showBelief, setShowBelief] = useState(true);
  const [showSensorCoverage, setShowSensorCoverage] = useState(true);
  const [showUncertainty, setShowUncertainty] = useState(true);
  const [showPaths, setShowPaths] = useState(true);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);

  // Viewport
  const [scale, setScale] = useState(12); // pixels per km
  const [pan, setPan] = useState({ x: 0, y: 0 });

  // Render loop on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !world) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Handle high DPI
    const width = canvas.parentElement?.clientWidth || 800;
    const height = canvas.parentElement?.clientHeight || 600;
    canvas.width = width;
    canvas.height = height;

    const centerX = width / 2 + pan.x;
    const centerY = height / 2 + pan.y;

    // 1. Clear background
    ctx.fillStyle = '#020617';
    ctx.fillRect(0, 0, width, height);

    // 2. Draw tactical coordinate grid (5 km increments)
    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 1;
    const gridSize = 5 * scale;
    const startX = (centerX % gridSize) - gridSize;
    const startY = (centerY % gridSize) - gridSize;

    for (let x = startX; x < width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = startY; y < height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // World Frame Axis
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(0, centerY);
    ctx.lineTo(width, centerY);
    ctx.moveTo(centerX, 0);
    ctx.lineTo(centerX, height);
    ctx.stroke();

    // 3. Draw Sensor Coverage Cones
    if (showSensorCoverage && world.sensors) {
      world.sensors.forEach((sensor) => {
        const radiusPx = sensor.range_km * scale;
        ctx.save();
        ctx.beginPath();
        ctx.arc(centerX, centerY, radiusPx, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(6, 182, 212, 0.04)';
        ctx.fill();
        ctx.strokeStyle = 'rgba(6, 182, 212, 0.2)';
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.restore();
      });
    }

    // 4. Draw Ground Truth Entities (White / Solid Outline)
    if (showGroundTruth && world.ground_truth) {
      world.ground_truth.forEach((entity) => {
        const x = centerX + entity.position[0] * scale;
        const y = centerY - entity.position[1] * scale;

        ctx.save();
        ctx.fillStyle =
          entity.kind === 'hostile'
            ? '#ef4444'
            : entity.kind === 'friendly'
            ? '#3b82f6'
            : '#94a3b8';

        // Draw ground truth icon (solid diamond)
        ctx.beginPath();
        ctx.arc(x, y, 5, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Label
        ctx.fillStyle = '#94a3b8';
        ctx.font = '10px monospace';
        ctx.fillText(`TRUTH: ${entity.label}`, x + 8, y - 4);
        ctx.restore();
      });
    }

    // 5. Draw Agent Beliefs (Cyan dashed rings with uncertainty ellipses)
    if (showBelief && world.belief) {
      world.belief.forEach((belief) => {
        const x = centerX + belief.position[0] * scale;
        const y = centerY - belief.position[1] * scale;

        // Uncertainty ellipse
        if (showUncertainty && belief.uncertainty_km) {
          const uncRadiusPx = Math.max(8, belief.uncertainty_km * scale);
          ctx.save();
          ctx.beginPath();
          ctx.arc(x, y, uncRadiusPx, 0, Math.PI * 2);
          ctx.fillStyle = 'rgba(6, 182, 212, 0.08)';
          ctx.fill();
          ctx.strokeStyle = 'rgba(6, 182, 212, 0.4)';
          ctx.lineWidth = 1;
          ctx.stroke();
          ctx.restore();
        }

        // Draw belief marker (cyan crosshair)
        ctx.save();
        ctx.strokeStyle = '#06b6d4';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x - 6, y);
        ctx.lineTo(x + 6, y);
        ctx.moveTo(x, y - 6);
        ctx.lineTo(x, y + 6);
        ctx.stroke();

        // Confidence badge
        ctx.fillStyle = '#06b6d4';
        ctx.font = 'bold 10px monospace';
        ctx.fillText(`BELIEF: ${(belief.confidence * 100).toFixed(0)}%`, x + 8, y + 10);
        ctx.restore();
      });
    }

    // 6. Draw Discrepancy vectors between Truth and Belief
    if (showGroundTruth && showBelief && world.comparison) {
      world.comparison.forEach((comp) => {
        if (!comp.belief) return;
        const tx = centerX + comp.ground_truth[0] * scale;
        const ty = centerY - comp.ground_truth[1] * scale;
        const bx = centerX + comp.belief[0] * scale;
        const by = centerY - comp.belief[1] * scale;

        ctx.save();
        ctx.strokeStyle = '#f59e0b';
        ctx.lineWidth = 1;
        ctx.setLineDash([2, 2]);
        ctx.beginPath();
        ctx.moveTo(tx, ty);
        ctx.lineTo(bx, by);
        ctx.stroke();
        ctx.restore();
      });
    }
  }, [world, scale, pan, showGroundTruth, showBelief, showSensorCoverage, showUncertainty]);

  return (
    <div className="h-full flex flex-col space-y-3">
      {/* Viewer Header & Controls */}
      <div className="flex items-center justify-between bg-surface-900/90 p-3 rounded-xl border border-surface-800">
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-lg bg-cyan-950 text-cyan-400 border border-cyan-800/50">
            <Radio className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-surface-100 flex items-center gap-2">
              Tactical World Simulation Viewer
              <StatusBadge status="SIMULATION" />
            </h2>
            <span className="text-[11px] font-mono text-surface-400">
              Dual-Frame Kinematic Map (Ground Truth vs Epistemic Belief)
            </span>
          </div>
        </div>

        {/* Layer Toggles */}
        <div className="flex items-center gap-2 text-xs font-mono">
          <button
            onClick={() => setShowGroundTruth(!showGroundTruth)}
            className={`px-2.5 py-1 rounded border transition-colors flex items-center gap-1.5 ${
              showGroundTruth
                ? 'bg-surface-800 text-surface-100 border-surface-600'
                : 'bg-surface-950 text-surface-500 border-surface-800'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-white" />
            <span>Ground Truth</span>
          </button>

          <button
            onClick={() => setShowBelief(!showBelief)}
            className={`px-2.5 py-1 rounded border transition-colors flex items-center gap-1.5 ${
              showBelief
                ? 'bg-cyan-950 text-cyan-300 border-cyan-700'
                : 'bg-surface-950 text-surface-500 border-surface-800'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-cyan-400" />
            <span>Agent Belief</span>
          </button>

          <button
            onClick={() => setShowSensorCoverage(!showSensorCoverage)}
            className={`px-2.5 py-1 rounded border transition-colors ${
              showSensorCoverage
                ? 'bg-surface-800 text-surface-200 border-surface-700'
                : 'bg-surface-950 text-surface-500 border-surface-800'
            }`}
          >
            Sensors
          </button>

          <button
            onClick={() => setShowUncertainty(!showUncertainty)}
            className={`px-2.5 py-1 rounded border transition-colors ${
              showUncertainty
                ? 'bg-surface-800 text-surface-200 border-surface-700'
                : 'bg-surface-950 text-surface-500 border-surface-800'
            }`}
          >
            Uncertainty
          </button>

          {/* Zoom controls */}
          <div className="flex items-center border-l border-surface-800 pl-2 gap-1">
            <button
              onClick={() => setScale((s) => Math.min(30, s + 2))}
              className="p-1 text-surface-400 hover:text-surface-100 hover:bg-surface-800 rounded"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={() => setScale((s) => Math.max(4, s - 2))}
              className="p-1 text-surface-400 hover:text-surface-100 hover:bg-surface-800 rounded"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={() => {
                setScale(12);
                setPan({ x: 0, y: 0 });
              }}
              className="p-1 text-surface-400 hover:text-surface-100 hover:bg-surface-800 rounded"
              title="Reset View"
            >
              <Crosshair className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div className="flex-1 bg-surface-950 rounded-xl border border-surface-800 overflow-hidden relative shadow-inner">
        <canvas ref={canvasRef} className="w-full h-full cursor-crosshair" />

        {/* Legend Overlay */}
        <div className="absolute bottom-3 left-3 bg-surface-950/80 backdrop-blur-md p-2.5 rounded-lg border border-surface-800 text-[10px] font-mono text-surface-300 space-y-1 select-none">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-white border border-surface-400 inline-block" />
            <span>Ground Truth (Simulator State)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 border-2 border-cyan-400 inline-block" />
            <span>Agent Belief (What Swarm Knows)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 border-t border-amber-400 border-dashed inline-block" />
            <span>Spatial Discrepancy Error</span>
          </div>
        </div>
      </div>
    </div>
  );
};

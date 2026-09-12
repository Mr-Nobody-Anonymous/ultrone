import React, { useRef, useEffect, useState } from 'react';
import { useWorldStore } from '../store/worldStore';
import { GitFork, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';
import type { Entity } from '../types/entity';

interface GraphNode {
  id: string;
  type: string;
  confidence: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  entity: Entity;
}

interface GraphLink {
  source: string;
  target: string;
  relation: string;
  confidence: number;
}

export const OntologyGraph: React.FC = () => {
  const entities = useWorldStore((s) => s.entities);
  const selectedEntity = useWorldStore((s) => s.selectedEntity);
  const selectEntity = useWorldStore((s) => s.selectEntity);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [draggedNode, setDraggedNode] = useState<GraphNode | null>(null);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const nodesRef = useRef<GraphNode[]>([]);
  const linksRef = useRef<GraphLink[]>([]);

  // Initialize or update nodes and links
  useEffect(() => {
    const existingMap = new Map(nodesRef.current.map((n) => [n.id, n]));
    const width = 800;
    const height = 600;

    const newNodes: GraphNode[] = entities.map((e, idx) => {
      const existing = existingMap.get(e.entity_id);
      if (existing) {
        existing.entity = e;
        return existing;
      }
      const angle = (idx / entities.length) * Math.PI * 2;
      const dist = 140 + Math.random() * 80;
      return {
        id: e.entity_id,
        type: e.type,
        confidence: e.confidence,
        x: width / 2 + Math.cos(angle) * dist,
        y: height / 2 + Math.sin(angle) * dist,
        vx: 0,
        vy: 0,
        radius: 20,
        entity: e,
      };
    });

    const newLinks: GraphLink[] = [];
    entities.forEach((e) => {
      if (e.relationships) {
        e.relationships.forEach((rel) => {
          newLinks.push({
            source: e.entity_id,
            target: rel.target_id,
            relation: rel.relation,
            confidence: rel.confidence,
          });
        });
      }
    });

    nodesRef.current = newNodes;
    linksRef.current = newLinks;
  }, [entities]);

  // Physics simulation loop
  useEffect(() => {
    let animId: number;
    const simulate = () => {
      const nodes = nodesRef.current;
      const links = linksRef.current;
      const canvas = canvasRef.current;
      if (!canvas) return;

      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      const cx = width / 2;
      const cy = height / 2;

      // 1. Center gravity
      nodes.forEach((n) => {
        n.vx += (cx - n.x) * 0.001;
        n.vy += (cy - n.y) * 0.001;
      });

      // 2. Node repulsion
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i];
          const b = nodes[j];
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dist = Math.hypot(dx, dy) || 1;
          if (dist < 180) {
            const force = (180 - dist) / dist * 0.5;
            a.vx -= dx * force * 0.05;
            a.vy -= dy * force * 0.05;
            b.vx += dx * force * 0.05;
            b.vy += dy * force * 0.05;
          }
        }
      }

      // 3. Link spring force
      const nodeMap = new Map(nodes.map((n) => [n.id, n]));
      links.forEach((link) => {
        const s = nodeMap.get(link.source);
        const t = nodeMap.get(link.target);
        if (s && t) {
          const dx = t.x - s.x;
          const dy = t.y - s.y;
          const dist = Math.hypot(dx, dy) || 1;
          const targetDist = 120;
          const force = (dist - targetDist) * 0.015;
          s.vx += (dx / dist) * force;
          s.vy += (dy / dist) * force;
          t.vx -= (dx / dist) * force;
          t.vy -= (dy / dist) * force;
        }
      });

      // 4. Update positions with damping
      nodes.forEach((n) => {
        if (n !== draggedNode) {
          n.x += n.vx;
          n.y += n.vy;
          n.vx *= 0.85;
          n.vy *= 0.85;
        }
      });

      // Draw Graph
      const ctx = canvas.getContext('2d');
      if (ctx) {
        const dpr = window.devicePixelRatio || 1;
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        ctx.scale(dpr, dpr);

        ctx.fillStyle = '#020617';
        ctx.fillRect(0, 0, width, height);

        ctx.save();
        ctx.translate(pan.x, pan.y);
        ctx.scale(zoom, zoom);

        // Draw Links
        links.forEach((l) => {
          const s = nodeMap.get(l.source);
          const t = nodeMap.get(l.target);
          if (s && t) {
            ctx.beginPath();
            ctx.moveTo(s.x, s.y);
            ctx.lineTo(t.x, t.y);
            ctx.strokeStyle = 'rgba(100, 116, 139, 0.4)';
            ctx.lineWidth = 1.5;
            ctx.stroke();

            // Link label
            const midX = (s.x + t.x) / 2;
            const midY = (s.y + t.y) / 2;
            ctx.fillStyle = 'rgba(148, 163, 184, 0.8)';
            ctx.font = '9px JetBrains Mono, monospace';
            ctx.textAlign = 'center';
            ctx.fillText(l.relation, midX, midY - 3);
          }
        });

        // Draw Nodes
        nodes.forEach((n) => {
          const isSel = selectedEntity?.entity_id === n.id;

          // Selection highlight ring
          if (isSel) {
            ctx.beginPath();
            ctx.arc(n.x, n.y, n.radius + 8, 0, Math.PI * 2);
            ctx.strokeStyle = 'rgba(92, 124, 250, 0.9)';
            ctx.lineWidth = 2.5;
            ctx.stroke();
          }

          // Node body
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
          ctx.fillStyle =
            n.type === 'air_asset'
              ? '#0284c7'
              : n.type === 'ground_unit'
              ? '#059669'
              : n.type === 'sensor_station'
              ? '#4f46e5'
              : '#e11d48';
          ctx.fill();
          ctx.strokeStyle = '#334155';
          ctx.lineWidth = 2;
          ctx.stroke();

          // Label
          ctx.fillStyle = isSel ? '#ffffff' : '#f1f5f9';
          ctx.font = '10px JetBrains Mono, monospace';
          ctx.textAlign = 'center';
          ctx.fillText(n.id, n.x, n.y + 3);

          // Type subtitle
          ctx.fillStyle = '#94a3b8';
          ctx.font = '8px JetBrains Mono, monospace';
          ctx.fillText(n.type, n.x, n.y + n.radius + 12);
        });

        ctx.restore();
      }

      animId = requestAnimationFrame(simulate);
    };

    animId = requestAnimationFrame(simulate);
    return () => cancelAnimationFrame(animId);
  }, [draggedNode, zoom, pan, selectedEntity]);

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = (e.clientX - rect.left - pan.x) / zoom;
    const mouseY = (e.clientY - rect.top - pan.y) / zoom;

    // Check if clicked a node
    const clicked = nodesRef.current.find(
      (n) => Math.hypot(n.x - mouseX, n.y - mouseY) < n.radius
    );

    if (clicked) {
      setDraggedNode(clicked);
      selectEntity(clicked.entity);
    } else {
      setIsDragging(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();

    if (draggedNode) {
      draggedNode.x = (e.clientX - rect.left - pan.x) / zoom;
      draggedNode.y = (e.clientY - rect.top - pan.y) / zoom;
      draggedNode.vx = 0;
      draggedNode.vy = 0;
    } else if (isDragging) {
      setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setDraggedNode(null);
  };

  return (
    <div className="relative h-full w-full bg-slate-950 overflow-hidden font-mono select-none">
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className="h-full w-full cursor-grab active:cursor-grabbing"
      />

      {/* Top Banner */}
      <div className="absolute top-4 left-4 z-10 flex items-center gap-3">
        <div className="flex items-center gap-2 rounded-lg bg-slate-900/90 border border-slate-800 px-3 py-1.5 shadow-lg backdrop-blur">
          <GitFork className="w-4 h-4 text-ultrone-400" />
          <span className="text-xs font-bold text-slate-100 uppercase tracking-wider">
            Ontology & Relationship Graph
          </span>
          <span className="text-[10px] text-slate-400 bg-slate-800 px-1.5 py-0.2 rounded">
            {entities.length} Nodes
          </span>
        </div>
      </div>

      {/* Controls */}
      <div className="absolute bottom-4 right-4 z-10 flex flex-col gap-1.5">
        <button
          onClick={() => setZoom((z) => Math.min(2.5, z * 1.2))}
          className="p-2 rounded-lg bg-slate-900/90 hover:bg-slate-800 border border-slate-800 text-slate-300 backdrop-blur shadow-lg"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={() => setZoom((z) => Math.max(0.4, z / 1.2))}
          className="p-2 rounded-lg bg-slate-900/90 hover:bg-slate-800 border border-slate-800 text-slate-300 backdrop-blur shadow-lg"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={() => {
            setZoom(1);
            setPan({ x: 0, y: 0 });
          }}
          className="p-2 rounded-lg bg-slate-900/90 hover:bg-slate-800 border border-slate-800 text-slate-300 backdrop-blur shadow-lg"
          title="Reset"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export default OntologyGraph;

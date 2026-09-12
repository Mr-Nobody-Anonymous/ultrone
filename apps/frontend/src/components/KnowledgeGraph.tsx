import type { FC } from 'react';
import { useRef, useEffect } from 'react';
import { Network } from 'lucide-react';

// Simple canvas-based knowledge graph visualization
const KnowledgeGraph: FC<{ widget: any }> = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;

    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, w, h);

    // Simulated graph nodes
    const nodes = [
      { x: w * 0.5, y: h * 0.15, label: 'BLUE CMD', color: '#3b82f6' },
      { x: w * 0.2, y: h * 0.4, label: 'DRONE-01', color: '#60a5fa' },
      { x: w * 0.8, y: h * 0.4, label: 'DRONE-02', color: '#60a5fa' },
      { x: w * 0.35, y: h * 0.65, label: 'SUPPLY-A', color: '#22c55e' },
      { x: w * 0.65, y: h * 0.65, label: 'TARGET-X', color: '#ef4444' },
      { x: w * 0.5, y: h * 0.85, label: 'SENSOR-1', color: '#8b5cf6' },
    ];

    const edges = [[0,1],[0,2],[1,3],[1,4],[2,4],[0,5],[3,5]];

    // Draw edges
    ctx.strokeStyle = 'rgba(100, 116, 139, 0.3)';
    ctx.lineWidth = 1;
    edges.forEach(([i, j]) => {
      ctx.beginPath();
      ctx.moveTo(nodes[i].x, nodes[i].y);
      ctx.lineTo(nodes[j].x, nodes[j].y);
      ctx.stroke();
    });

    // Draw nodes
    nodes.forEach(node => {
      const gradient = ctx.createRadialGradient(node.x, node.y, 2, node.x, node.y, 12);
      gradient.addColorStop(0, node.color);
      gradient.addColorStop(1, 'rgba(15, 23, 42, 0.8)');
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(node.x, node.y, 10, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = node.color;
      ctx.lineWidth = 1.5;
      ctx.stroke();

      ctx.fillStyle = '#94a3b8';
      ctx.font = '8px JetBrains Mono';
      ctx.textAlign = 'center';
      ctx.fillText(node.label, node.x, node.y + 20);
    });

  }, []);

  return (
    <div className="p-3 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-3">
        <Network size={14} className="text-primary-400" />
        <span className="text-xs font-semibold text-surface-300">Knowledge Graph</span>
      </div>
      <div className="flex-1 relative">
        <canvas ref={canvasRef} width={800} height={400} className="w-full h-full rounded-lg" />
      </div>
    </div>
  );
};

export default KnowledgeGraph;

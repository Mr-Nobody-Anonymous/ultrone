import React, { useState } from 'react';
import { useWorldStore } from '../../../store/worldStore';
import { Network, Search, Eye, ArrowRight } from 'lucide-react';

interface GraphNode {
  id: string;
  label: string;
  type: 'entity' | 'sensor' | 'region' | 'case' | 'target';
  status?: string;
  coords?: [number, number];
  x: number;
  y: number;
}

interface GraphLink {
  source: string;
  target: string;
  relation: string;
  weight?: number;
}

const INITIAL_NODES: GraphNode[] = [
  { id: 'ALPHA-1', label: 'MQ-9 Reaper (ALPHA-1)', type: 'entity', status: 'active', coords: [35.2, 31.7], x: 260, y: 140 },
  { id: 'BRAVO-2', label: 'Patrol Boat (BRAVO-2)', type: 'entity', status: 'standby', coords: [34.8, 31.9], x: 500, y: 140 },
  { id: 'RADAR-04', label: 'Coastal AN/TPS-75 Radar', type: 'sensor', status: 'operational', coords: [35.1, 31.6], x: 140, y: 320 },
  { id: 'SIGINT-09', label: 'E-8C Joint STARS Sensor', type: 'sensor', status: 'scanning', coords: [35.4, 32.0], x: 380, y: 320 },
  { id: 'SEC-ALPHA', label: 'Sector Alpha Coastal Region', type: 'region', coords: [35.0, 31.8], x: 260, y: 460 },
  { id: 'INV-1042', label: 'Case #1042: Sector Alpha Correlation', type: 'case', status: 'active', x: 620, y: 320 },
  { id: 'TGT-X99', label: 'Uncorrelated Contact TGT-X99', type: 'target', status: 'unidentified', coords: [35.3, 31.85], x: 420, y: 460 },
];

const INITIAL_LINKS: GraphLink[] = [
  { source: 'RADAR-04', target: 'ALPHA-1', relation: 'tracks' },
  { source: 'ALPHA-1', target: 'BRAVO-2', relation: 'communicates_with' },
  { source: 'SIGINT-09', target: 'TGT-X99', relation: 'observed_by' },
  { source: 'ALPHA-1', target: 'SEC-ALPHA', relation: 'located_in' },
  { source: 'BRAVO-2', target: 'SEC-ALPHA', relation: 'patrols' },
  { source: 'TGT-X99', target: 'SEC-ALPHA', relation: 'located_in' },
  { source: 'INV-1042', target: 'TGT-X99', relation: 'investigates' },
  { source: 'INV-1042', target: 'ALPHA-1', relation: 'evidence_source' },
];

export const RelationshipGraph: React.FC = () => {
  const entities = useWorldStore((s) => s.entities);
  const selectEntity = useWorldStore((s) => s.selectEntity);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>('ALPHA-1');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState<string>('all');

  const filteredNodes = INITIAL_NODES.filter((n) => {
    const matchesSearch = n.label.toLowerCase().includes(searchQuery.toLowerCase()) || n.id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = activeFilter === 'all' || n.type === activeFilter;
    return matchesSearch && matchesFilter;
  });

  const selectedNode = INITIAL_NODES.find((n) => n.id === selectedNodeId);

  const handleNodeClick = (node: GraphNode) => {
    setSelectedNodeId(node.id);
    if (node.type === 'entity' || node.type === 'target') {
      const found = entities.find((e) => e.entity_id === node.id);
      if (found) {
        selectEntity(found);
      }
    }
  };

  const getNodeColor = (type: GraphNode['type']) => {
    switch (type) {
      case 'entity':
        return '#06b6d4'; // Cyan
      case 'sensor':
        return '#3b82f6'; // Blue
      case 'region':
        return '#10b981'; // Emerald
      case 'case':
        return '#f59e0b'; // Amber
      case 'target':
        return '#ef4444'; // Red
      default:
        return '#94a3b8';
    }
  };

  return (
    <div className="flex h-full w-full bg-slate-950 font-mono text-xs text-slate-300">
      {/* Main Graph Visualization Canvas */}
      <div className="flex flex-1 flex-col border-r border-slate-800">
        {/* Top Control Bar */}
        <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/60 px-4 py-2">
          <div className="flex items-center space-x-2">
            <Network className="h-4 w-4 text-cyan-400" />
            <span className="font-semibold tracking-wider text-slate-100">ONTOLOGY RELATIONSHIP GRAPH</span>
            <span className="rounded bg-cyan-950/60 px-1.5 py-0.5 text-[10px] text-cyan-400 border border-cyan-800">
              SYNCHRONIZED WITH WORLD MODEL
            </span>
          </div>

          <div className="flex items-center space-x-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search nodes or links..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-48 rounded border border-slate-700 bg-slate-950 py-1 pl-8 pr-2 text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
              />
            </div>

            <div className="flex rounded border border-slate-800 bg-slate-950 p-0.5">
              {(['all', 'entity', 'sensor', 'region', 'case'] as const).map((filter) => (
                <button
                  key={filter}
                  onClick={() => setActiveFilter(filter)}
                  className={`rounded px-2 py-0.5 text-[10px] uppercase transition-colors ${
                    activeFilter === filter
                      ? 'bg-cyan-500 text-slate-950 font-bold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {filter}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* SVG Directed Graph Area */}
        <div className="relative flex-1 overflow-hidden bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px]">
          <svg className="h-full w-full">
            <defs>
              <marker
                id="arrowhead"
                markerWidth="8"
                markerHeight="6"
                refX="18"
                refY="3"
                orient="auto"
              >
                <polygon points="0 0, 8 3, 0 6" fill="#475569" />
              </marker>
              <marker
                id="arrowhead-active"
                markerWidth="8"
                markerHeight="6"
                refX="18"
                refY="3"
                orient="auto"
              >
                <polygon points="0 0, 8 3, 0 6" fill="#06b6d4" />
              </marker>
            </defs>

            {/* Links */}
            {INITIAL_LINKS.map((link, idx) => {
              const src = INITIAL_NODES.find((n) => n.id === link.source);
              const dst = INITIAL_NODES.find((n) => n.id === link.target);
              if (!src || !dst) return null;

              const isHighlighted =
                selectedNodeId === link.source || selectedNodeId === link.target;

              const midX = (src.x + dst.x) / 2;
              const midY = (src.y + dst.y) / 2;

              return (
                <g key={idx}>
                  <line
                    x1={src.x}
                    y1={src.y}
                    x2={dst.x}
                    y2={dst.y}
                    stroke={isHighlighted ? '#06b6d4' : '#334155'}
                    strokeWidth={isHighlighted ? 2 : 1}
                    strokeDasharray={isHighlighted ? '4,4' : undefined}
                    markerEnd={isHighlighted ? 'url(#arrowhead-active)' : 'url(#arrowhead)'}
                  />
                  <rect
                    x={midX - 35}
                    y={midY - 8}
                    width={70}
                    height={16}
                    rx={3}
                    fill="#090d16"
                    stroke={isHighlighted ? '#06b6d4' : '#1e293b'}
                    strokeWidth={0.5}
                  />
                  <text
                    x={midX}
                    y={midY + 3}
                    textAnchor="middle"
                    fill={isHighlighted ? '#38bdf8' : '#64748b'}
                    fontSize={9}
                    fontFamily="monospace"
                  >
                    {link.relation}
                  </text>
                </g>
              );
            })}

            {/* Nodes */}
            {filteredNodes.map((node) => {
              const isSelected = selectedNodeId === node.id;
              const color = getNodeColor(node.type);

              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x}, ${node.y})`}
                  onClick={() => handleNodeClick(node)}
                  className="cursor-pointer transition-transform hover:scale-105"
                >
                  {/* Selection halo */}
                  {isSelected && (
                    <circle
                      r={24}
                      fill="none"
                      stroke={color}
                      strokeWidth={1.5}
                      strokeDasharray="3,3"
                      className="animate-spin-slow"
                    />
                  )}
                  {/* Node Body */}
                  <circle
                    r={18}
                    fill="#0f172a"
                    stroke={color}
                    strokeWidth={isSelected ? 2.5 : 1.5}
                  />
                  <text
                    textAnchor="middle"
                    dy={4}
                    fill={color}
                    fontSize={11}
                    fontWeight="bold"
                  >
                    {node.id.slice(0, 3)}
                  </text>

                  {/* Label below */}
                  <text
                    y={32}
                    textAnchor="middle"
                    fill={isSelected ? '#f8fafc' : '#94a3b8'}
                    fontSize={10}
                    fontWeight={isSelected ? 'bold' : 'normal'}
                  >
                    {node.id}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      </div>

      {/* Right Detail Inspection & Synchronization Panel */}
      <div className="w-80 border-l border-slate-800 bg-slate-900/50 p-4 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <span className="font-semibold text-slate-200">NODE METADATA</span>
            {selectedNode && (
              <span
                className="rounded px-1.5 py-0.5 text-[9px] uppercase font-bold"
                style={{
                  backgroundColor: `${getNodeColor(selectedNode.type)}20`,
                  color: getNodeColor(selectedNode.type),
                  border: `1px solid ${getNodeColor(selectedNode.type)}60`,
                }}
              >
                {selectedNode.type}
              </span>
            )}
          </div>

          {selectedNode ? (
            <div className="mt-4 space-y-3">
              <div>
                <div className="text-[10px] text-slate-500">IDENTIFIER / CALLSIGN</div>
                <div className="font-bold text-slate-100 text-sm">{selectedNode.label}</div>
              </div>

              {selectedNode.status && (
                <div>
                  <div className="text-[10px] text-slate-500">OPERATIONAL STATUS</div>
                  <div className="flex items-center space-x-1.5 text-emerald-400 font-semibold mt-0.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="uppercase">{selectedNode.status}</span>
                  </div>
                </div>
              )}

              {selectedNode.coords && (
                <div>
                  <div className="text-[10px] text-slate-500">GEOSPATIAL ANCHOR</div>
                  <div className="font-mono text-slate-300 mt-0.5 bg-slate-950 p-1.5 rounded border border-slate-800">
                    LAT: {selectedNode.coords[1].toFixed(4)}° N, LON: {selectedNode.coords[0].toFixed(4)}° E
                  </div>
                </div>
              )}

              {/* Connected Relationships list */}
              <div>
                <div className="text-[10px] text-slate-500 mb-1">DIRECT RELATIONSHIPS</div>
                <div className="space-y-1">
                  {INITIAL_LINKS.filter(
                    (l) => l.source === selectedNode.id || l.target === selectedNode.id
                  ).map((l, i) => {
                    const otherId = l.source === selectedNode.id ? l.target : l.source;
                    return (
                      <div
                        key={i}
                        onClick={() => {
                          const other = INITIAL_NODES.find((n) => n.id === otherId);
                          if (other) handleNodeClick(other);
                        }}
                        className="flex items-center justify-between p-1.5 rounded bg-slate-950 border border-slate-800 hover:border-cyan-700 cursor-pointer transition-colors"
                      >
                        <span className="text-[10px] text-slate-400">{l.relation}</span>
                        <div className="flex items-center space-x-1 text-cyan-300 font-bold">
                          <span>{otherId}</span>
                          <ArrowRight className="h-3 w-3 text-slate-600" />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <div className="py-12 text-center text-slate-500">
              Select a graph node to inspect ontology metadata and relationships.
            </div>
          )}
        </div>

        {/* Action Button */}
        {selectedNode && (
          <button
            onClick={() => {
              const found = entities.find((e) => e.entity_id === selectedNode.id);
              if (found) {
                selectEntity(found);
              } else if (entities.length > 0) {
                selectEntity(entities[0]);
              }
            }}
            className="w-full flex items-center justify-center space-x-2 py-2 px-3 rounded bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold tracking-wider transition-colors"
          >
            <Eye className="h-3.5 w-3.5" />
            <span>OPEN 8-TAB INSPECTOR</span>
          </button>
        )}
      </div>
    </div>
  );
};

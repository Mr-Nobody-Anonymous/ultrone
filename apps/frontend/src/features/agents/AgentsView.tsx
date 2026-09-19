// Copyright (c) Ultrone Contributors. All rights reserved.
import React, { useEffect, useState } from 'react';
import { useCockpitStore } from '../../stores/cockpitStore';
import { cockpitApi } from '../../api/client';
import type { AgentCatalog, AgentRecord } from '../../api/types';
import { Cpu, ArrowRight, Share2, Shield, Activity } from 'lucide-react';
import { StatusBadge } from '../../components/ui/StatusBadge';

export const AgentsView: React.FC = () => {
  const { inspect } = useCockpitStore();
  const [catalog, setCatalog] = useState<AgentCatalog | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    cockpitApi
      .getAgents()
      .then((data) => {
        setCatalog(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-surface-400 font-mono text-sm">
        <span className="animate-pulse">Loading Swarm Agent Roster & Topology...</span>
      </div>
    );
  }

  const agents = catalog?.agents || [];
  const edges = catalog?.graph?.edges || [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-mono">
      {/* Header */}
      <div className="flex items-center justify-between bg-surface-900/90 p-4 rounded-xl border border-surface-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-950 text-blue-400 border border-blue-800/50">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-surface-100 font-sans flex items-center gap-2">
              Agent Control Center & Swarm Topology
              <StatusBadge status="ACTIVE" />
            </h2>
            <p className="text-xs text-surface-400">
              Multi-agent coordination roster, model versions, published schemas, and communication graph.
            </p>
          </div>
        </div>

        <div className="text-right text-xs">
          <span className="text-surface-500 block">ACTIVE ROSTER</span>
          <span className="text-cyan-400 font-bold">{agents.length} Registered Agents</span>
        </div>
      </div>

      {/* Agents Roster Table */}
      <div className="bg-surface-900 rounded-xl border border-surface-800 overflow-hidden shadow-xl">
        <div className="px-4 py-3 bg-surface-950 border-b border-surface-800 flex items-center justify-between">
          <span className="text-xs font-bold text-surface-300 uppercase tracking-wider">
            Agent Inventory & Capability Leases
          </span>
          <span className="text-[11px] text-surface-500">
            Click any agent to inspect memory refs, lease scopes, and recent decisions
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-surface-800 bg-surface-950/60 text-surface-400 text-[11px]">
                <th className="py-2.5 px-4">AGENT ID & NAME</th>
                <th className="py-2.5 px-4">ROLE</th>
                <th className="py-2.5 px-4">STATE</th>
                <th className="py-2.5 px-4">MODEL VERSION</th>
                <th className="py-2.5 px-4">CONFIDENCE</th>
                <th className="py-2.5 px-4">TASKS / DECISIONS</th>
                <th className="py-2.5 px-4">LATENCY</th>
                <th className="py-2.5 px-4 text-right">INSPECT</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-800/60">
              {agents.map((agent) => (
                <tr
                  key={agent.agent_id}
                  onClick={() => inspect('agent', agent.agent_id, agent)}
                  className="hover:bg-surface-800/50 cursor-pointer transition-colors"
                >
                  <td className="py-3 px-4">
                    <div className="font-bold text-surface-200">{agent.name}</div>
                    <div className="text-[10px] text-cyan-400 font-mono">{agent.agent_id}</div>
                  </td>
                  <td className="py-3 px-4 text-surface-300 uppercase">{agent.role}</td>
                  <td className="py-3 px-4">
                    <StatusBadge status={agent.state} className="text-[10px]" />
                  </td>
                  <td className="py-3 px-4 text-surface-300">{agent.model_version}</td>
                  <td className="py-3 px-4 text-cyan-400 font-bold">
                    {(agent.confidence * 100).toFixed(0)}%
                  </td>
                  <td className="py-3 px-4 text-surface-300">{agent.tasks_completed} executed</td>
                  <td className="py-3 px-4 text-surface-400">{agent.latency_ms.toFixed(1)} ms</td>
                  <td className="py-3 px-4 text-right">
                    <button className="text-xs text-cyan-400 hover:text-cyan-300 inline-flex items-center gap-1">
                      <span>Details</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Communication Graph Section */}
      <div className="bg-surface-900 rounded-xl border border-surface-800 p-4">
        <h3 className="text-xs font-bold text-surface-300 uppercase tracking-wider mb-3 flex items-center gap-2">
          <Share2 className="w-4 h-4 text-cyan-400" />
          Multi-Agent Message Bus Channels ({edges.length} Active Edges)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {edges.map((edge) => (
            <div
              key={edge.edge_id}
              className="p-3 bg-surface-950 rounded-lg border border-surface-800 hover:border-surface-700 transition-colors text-xs"
            >
              <div className="flex items-center justify-between text-surface-400 mb-1">
                <span className="text-cyan-400 font-bold">{edge.from}</span>
                <span>→</span>
                <span className="text-blue-400 font-bold">{edge.to}</span>
              </div>
              <div className="text-surface-200 font-bold text-[11px] truncate">
                {edge.message_type}
              </div>
              <div className="mt-2 pt-2 border-t border-surface-800/80 flex items-center justify-between text-[10px] text-surface-500">
                <span>Schema: {edge.schema}</span>
                <span>{edge.message_count} msgs</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Copyright (c) Ultrone Contributors. All rights reserved.
import React, { useEffect, useState } from 'react';
import { cockpitApi } from '../../api/client';
import type { McpTrafficEntry } from '../../api/types';
import { Share2, Play, Terminal, ArrowRight, CheckCircle2, XCircle } from 'lucide-react';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { JsonViewer } from '../../components/ui/JsonViewer';

export const McpInspectorView: React.FC = () => {
  const [traffic, setTraffic] = useState<McpTrafficEntry[]>([]);
  const [discovery, setDiscovery] = useState<any>(null);
  const [selectedEntry, setSelectedEntry] = useState<McpTrafficEntry | null>(null);
  const [selectedTool, setSelectedTool] = useState<string>('devices_state');
  const [toolArgs, setToolArgs] = useState<string>('{"device_id": "device-001"}');
  const [toolResult, setToolResult] = useState<any>(null);
  const [calling, setCalling] = useState(false);

  const refreshTraffic = () => {
    cockpitApi.getMcpTraffic(50).then(setTraffic).catch(() => {});
  };

  useEffect(() => {
    cockpitApi.getMcpDiscovery().then(setDiscovery).catch(() => {});
    refreshTraffic();
    const interval = setInterval(refreshTraffic, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleCallTool = async () => {
    setCalling(true);
    try {
      const parsedArgs = JSON.parse(toolArgs || '{}');
      const res = await cockpitApi.callMcpTool(selectedTool, parsedArgs);
      setToolResult(res);
      refreshTraffic();
    } catch (err: any) {
      setToolResult({ error: err.message });
    } finally {
      setCalling(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-mono">
      {/* Header */}
      <div className="flex items-center justify-between bg-surface-900/90 p-4 rounded-xl border border-surface-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-950 text-emerald-400 border border-emerald-800/50">
            <Share2 className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-surface-100 font-sans flex items-center gap-2">
              MCP Protocol 2026-07-28 Wire Inspector & Traffic DevTools
              <StatusBadge status="ACTIVE" />
            </h2>
            <p className="text-xs text-surface-400">
              Live JSON-RPC 2.0 frames, MRTR replay protection, and UDIS gateway tools.
            </p>
          </div>
        </div>

        <div className="text-right text-xs">
          <span className="text-surface-500 block">WIRE PROTOCOL VERSION</span>
          <span className="text-emerald-400 font-bold">2026-07-28 Conformance</span>
        </div>
      </div>

      {/* Main DevTools Split: Live Traffic + Tool Runner */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left: DevTools Traffic Table */}
        <div className="lg:col-span-7 bg-surface-900 rounded-xl border border-surface-800 overflow-hidden flex flex-col shadow-xl">
          <div className="px-4 py-3 bg-surface-950 border-b border-surface-800 flex items-center justify-between">
            <span className="text-xs font-bold text-surface-300 uppercase tracking-wider">
              MCP Traffic Log ({traffic.length} recent frames)
            </span>
            <button
              onClick={refreshTraffic}
              className="text-xs text-cyan-400 hover:underline"
            >
              Refresh
            </button>
          </div>

          <div className="overflow-x-auto max-h-[480px]">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-surface-800 bg-surface-950/60 text-surface-400 text-[11px]">
                  <th className="py-2 px-3">KIND</th>
                  <th className="py-2 px-3">METHOD / TOOL</th>
                  <th className="py-2 px-3">CORRELATION ID</th>
                  <th className="py-2 px-3">LATENCY</th>
                  <th className="py-2 px-3 text-right">STATUS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-800/60">
                {traffic.map((entry, idx) => (
                  <tr
                    key={idx}
                    onClick={() => setSelectedEntry(entry)}
                    className={`hover:bg-surface-800/50 cursor-pointer transition-colors ${
                      selectedEntry === entry ? 'bg-surface-800/80' : ''
                    }`}
                  >
                    <td className="py-2 px-3">
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                          entry.kind === 'REQUEST'
                            ? 'bg-blue-950 text-blue-400 border border-blue-800'
                            : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                        }`}
                      >
                        {entry.kind}
                      </span>
                    </td>
                    <td className="py-2 px-3 font-bold text-surface-200 truncate max-w-[160px]">
                      <div>{entry.method}</div>
                      {entry.tool && (
                        <div className="text-[10px] text-surface-400 font-normal truncate">
                          {entry.tool}
                        </div>
                      )}
                    </td>
                    <td className="py-2 px-3 text-surface-400 text-[11px]">
                      {entry.correlation_id}
                    </td>
                    <td className="py-2 px-3 text-surface-400">{entry.latency_ms.toFixed(2)} ms</td>
                    <td className="py-2 px-3 text-right">
                      {entry.status === 'ok' ? (
                        <span className="text-emerald-400 font-bold">200 OK</span>
                      ) : (
                        <span className="text-rose-400 font-bold">{entry.error_code || 'ERR'}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Selected frame payload viewer */}
          {selectedEntry && (
            <div className="p-3 bg-surface-950 border-t border-surface-800">
              <span className="text-[11px] text-surface-400 block mb-1">
                Payload Frame: {selectedEntry.method} ({selectedEntry.correlation_id})
              </span>
              <JsonViewer data={selectedEntry.payload} maxHeight="max-h-44" />
            </div>
          )}
        </div>

        {/* Right: Dynamic MCP Tool Execution Form */}
        <div className="lg:col-span-5 bg-surface-900 rounded-xl border border-surface-800 p-4 flex flex-col justify-between shadow-xl">
          <div className="space-y-4">
            <h3 className="text-xs font-bold text-surface-300 uppercase tracking-wider flex items-center gap-2">
              <Terminal className="w-4 h-4 text-cyan-400" />
              Dynamic Tool Runner
            </h3>

            <div>
              <label className="text-[11px] text-surface-400 block mb-1">Select Tool</label>
              <select
                value={selectedTool}
                onChange={(e) => setSelectedTool(e.target.value)}
                className="w-full bg-surface-950 border border-surface-700 text-xs font-mono rounded-lg px-3 py-2 text-surface-200 outline-none"
              >
                <option value="devices_state">devices_state (Inspect FSM State)</option>
                <option value="devices_telemetry">devices_telemetry (Fresh Channels)</option>
                <option value="device_command">device_command (Simulate Execution)</option>
                <option value="device_procedure">device_procedure (Test Sequence)</option>
              </select>
            </div>

            <div>
              <label className="text-[11px] text-surface-400 block mb-1">JSON Arguments</label>
              <textarea
                value={toolArgs}
                onChange={(e) => setToolArgs(e.target.value)}
                rows={4}
                className="w-full bg-surface-950 border border-surface-700 text-xs font-mono rounded-lg p-3 text-surface-200 outline-none resize-none leading-relaxed"
              />
            </div>

            <button
              disabled={calling}
              onClick={handleCallTool}
              className="w-full py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-black font-bold text-xs flex items-center justify-center gap-2 transition-colors shadow-lg shadow-cyan-900/20"
            >
              <Play className="w-3.5 h-3.5" />
              <span>{calling ? 'Executing tool call...' : 'Invoke MCP Tool Call'}</span>
            </button>

            {toolResult && (
              <div>
                <span className="text-[11px] text-surface-400 block mb-1">Execution Result:</span>
                <JsonViewer data={toolResult} maxHeight="max-h-48" />
              </div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-surface-800 text-[11px] text-surface-500">
            Protected by Monotonic Request Token Registry (MRTR) against wire replays.
          </div>
        </div>
      </div>
    </div>
  );
};

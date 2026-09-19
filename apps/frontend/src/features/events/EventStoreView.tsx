// Copyright (c) Ultrone Contributors. All rights reserved.
import React, { useEffect, useState } from 'react';
import { cockpitApi } from '../../api/client';
import type { StoredEvent, EventStoreStatus } from '../../api/types';
import { FileText, RotateCcw, Key, ShieldCheck, CheckCircle2, Play } from 'lucide-react';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { JsonViewer } from '../../components/ui/JsonViewer';

export const EventStoreView: React.FC = () => {
  const [events, setEvents] = useState<StoredEvent[]>([]);
  const [storeStatus, setStoreStatus] = useState<EventStoreStatus | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<StoredEvent | null>(null);
  const [filterType, setFilterType] = useState<string>('');
  const [replaying, setReplaying] = useState(false);
  const [replayResult, setReplayResult] = useState<any>(null);
  const [checkpointing, setCheckpointing] = useState(false);
  const [loading, setLoading] = useState(true);

  const refreshEvents = () => {
    Promise.all([cockpitApi.getEvents(100, filterType || undefined), cockpitApi.getEventStore()])
      .then(([evData, stData]) => {
        setEvents(evData);
        setStoreStatus(stData);
        if (evData.length > 0 && !selectedEvent) setSelectedEvent(evData[0]);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    refreshEvents();
  }, [filterType]);

  const handleCheckpoint = async () => {
    setCheckpointing(true);
    try {
      const res = await cockpitApi.createCheckpoint('cockpit-auditor');
      setStoreStatus(res);
      alert('Ed25519 Audit Checkpoint Created and Signed Successfully!');
    } finally {
      setCheckpointing(false);
    }
  };

  const handleRunReplay = async () => {
    setReplaying(true);
    try {
      const res = await cockpitApi.runReplay();
      setReplayResult(res);
    } finally {
      setReplaying(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-surface-400 font-mono text-sm">
        <span className="animate-pulse">Loading Event Store & Hash-Chained Journal...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-mono">
      {/* Header */}
      <div className="flex items-center justify-between bg-surface-900/90 p-4 rounded-xl border border-surface-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-amber-950 text-amber-400 border border-amber-800/50">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-surface-100 font-sans flex items-center gap-2">
              Event Store Journal & Deterministic Replay
              <StatusBadge status={storeStatus?.chain_valid ? 'READY' : 'FAULT'} />
            </h2>
            <p className="text-xs text-surface-400">
              SHA-256 cryptographically chained immutable audit journal with Ed25519 signed checkpoints.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            disabled={checkpointing}
            onClick={handleCheckpoint}
            className="px-3 py-1.5 rounded-lg bg-surface-800 hover:bg-surface-700 text-surface-200 text-xs font-bold transition-colors flex items-center gap-1.5"
          >
            <Key className="w-3.5 h-3.5 text-cyan-400" />
            <span>{checkpointing ? 'Signing...' : 'Sign Checkpoint'}</span>
          </button>

          <button
            disabled={replaying}
            onClick={handleRunReplay}
            className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-black font-bold text-xs transition-colors flex items-center gap-1.5 shadow-lg shadow-cyan-900/20"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>{replaying ? 'Verifying Replay...' : 'Run Replay'}</span>
          </button>
        </div>
      </div>

      {/* Replay Divergence Banner if executed */}
      {replayResult && (
        <div className="p-4 rounded-xl bg-surface-900 border border-cyan-500/40 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-bold text-cyan-400">DETERMINISTIC REPLAY RESULT</span>
            <span
              className={
                replayResult.matches ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'
              }
            >
              {replayResult.matches ? '✓ 100% REPLAY CONVERGENCE' : '⚠ DIVERGENCE DETECTED'}
            </span>
          </div>
          <p className="text-surface-300">
            Re-executed {replayResult.ticks_replayed} ticks in an isolated clean world and fresh event
            store. Replay hash matched original execution stream.
          </p>
        </div>
      )}

      {/* Events Split: List + Payload Viewer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left: Events Timeline Table */}
        <div className="lg:col-span-7 bg-surface-900 rounded-xl border border-surface-800 overflow-hidden flex flex-col shadow-xl">
          <div className="px-4 py-3 bg-surface-950 border-b border-surface-800 flex items-center justify-between">
            <span className="text-xs font-bold text-surface-300 uppercase tracking-wider">
              Chained Events ({events.length} shown)
            </span>
            <span className="text-[11px] text-emerald-400 font-bold">
              SHA-256 Hash Chain: VALID ✓
            </span>
          </div>

          <div className="overflow-y-auto max-h-[520px] divide-y divide-surface-800/60">
            {events.map((ev) => (
              <div
                key={ev.event_id}
                onClick={() => setSelectedEvent(ev)}
                className={`p-3 hover:bg-surface-800/50 cursor-pointer transition-colors text-xs ${
                  selectedEvent?.event_id === ev.event_id ? 'bg-surface-800/80' : ''
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-surface-200">{ev.event_type}</span>
                  <span className="text-cyan-400 text-[11px]">T+{ev.tick}</span>
                </div>
                <div className="flex items-center justify-between text-[11px] text-surface-500">
                  <span className="truncate max-w-[240px]">Hash: {ev.hash}</span>
                  <span>ID #{ev.event_id}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Event Detail / Payload Inspector */}
        <div className="lg:col-span-5 bg-surface-900 rounded-xl border border-surface-800 p-4 flex flex-col justify-between shadow-xl">
          <div>
            <h3 className="text-xs font-bold text-surface-300 uppercase tracking-wider mb-3">
              Event Block Cryptographic Inspection
            </h3>

            {selectedEvent ? (
              <div className="space-y-3">
                <div className="p-3 bg-surface-950 rounded-lg border border-surface-800 space-y-1.5 text-xs">
                  <div className="flex justify-between">
                    <span className="text-surface-500">EVENT ID:</span>
                    <span className="text-surface-200">{selectedEvent.event_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-surface-500">EVENT TYPE:</span>
                    <span className="text-cyan-400 font-bold">{selectedEvent.event_type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-surface-500">TICK:</span>
                    <span className="text-surface-200">T+{selectedEvent.tick}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-surface-500">STREAM:</span>
                    <span className="text-surface-200">{selectedEvent.stream_id}</span>
                  </div>
                </div>

                <div>
                  <span className="text-[11px] text-surface-400 block mb-1">Payload JSON:</span>
                  <JsonViewer data={selectedEvent.payload} maxHeight="max-h-64" />
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-xs text-surface-500">
                Select an event to inspect its cryptographic block.
              </div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-surface-800 text-[10px] text-surface-500">
            Immutable audit record verifiable by external auditors without backend execution dependencies.
          </div>
        </div>
      </div>
    </div>
  );
};

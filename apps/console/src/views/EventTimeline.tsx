import React, { useState } from 'react';
import { useWorldStore } from '../store/worldStore';
import ConfidenceBadge from '../components/ConfidenceBadge';
import EventDot from '../components/EventDot';
import { EVENT_TYPE_META } from '../types/event';
import {
  Activity,
  Filter,
  Search,
  ChevronRight,
  Play,
  Pause,
} from 'lucide-react';

export const EventTimeline: React.FC = () => {
  const events = useWorldStore((s) => s.events);
  const selectEntity = useWorldStore((s) => s.selectEntity);
  const entities = useWorldStore((s) => s.entities);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [isPaused, setIsPaused] = useState(false);

  const categories: string[] = [
    'all',
    'Entity',
    'Observation',
    'Decision',
    'Simulation',
    'Cognitive',
    'HITL',
    'System',
  ];

  const filteredEvents = events.filter((evt) => {
    const meta = EVENT_TYPE_META[evt.type];
    const category = meta ? meta.category : 'System';

    const matchesCategory = selectedCategory === 'all' || category === selectedCategory;
    const matchesSearch =
      evt.type.toLowerCase().includes(searchQuery.toLowerCase()) ||
      evt.source.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (evt.entity_id && evt.entity_id.toLowerCase().includes(searchQuery.toLowerCase()));

    return matchesCategory && matchesSearch;
  });

  const toggleExpand = (id: string) => {
    setExpandedEventId((prev) => (prev === id ? null : id));
  };

  return (
    <div className="flex h-full w-full flex-col bg-slate-950 p-6 overflow-hidden space-y-4 font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-ultrone-400" />
            <h1 className="text-xl font-bold tracking-wider text-slate-100 uppercase">
              Event Timeline
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time chronological telemetry & decision stream ({events.length} total events)
          </p>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 rounded-lg bg-slate-900 border border-slate-800 px-3 py-1.5 w-64">
            <Search className="w-3.5 h-3.5 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter events or source..."
              className="w-full bg-transparent text-xs text-slate-100 placeholder-slate-500 outline-none"
            />
          </div>

          <button
            onClick={() => setIsPaused((p) => !p)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${
              isPaused
                ? 'bg-amber-500/20 text-amber-400 border-amber-500/40'
                : 'bg-slate-900 hover:bg-slate-800 text-slate-300 border-slate-800'
            }`}
          >
            {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
            {isPaused ? 'Resume' : 'Pause'}
          </button>
        </div>
      </div>

      {/* Category Pills */}
      <div className="flex flex-wrap items-center gap-1.5">
        <Filter className="w-3.5 h-3.5 text-slate-500 mr-1" />
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-3 py-1 text-xs rounded-lg transition-colors ${
              selectedCategory === cat
                ? 'bg-ultrone-600/30 text-ultrone-300 font-semibold border border-ultrone-500/50'
                : 'bg-slate-900/80 text-slate-400 hover:bg-slate-800 hover:text-slate-200 border border-slate-800/80'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Event List */}
      <div className="flex-1 overflow-y-auto rounded-lg border border-slate-800 bg-slate-900/60 p-3 space-y-2">
        {filteredEvents.length === 0 ? (
          <div className="flex h-48 items-center justify-center text-xs text-slate-500">
            No events match the selected criteria.
          </div>
        ) : (
          filteredEvents.map((evt) => {
            const isExpanded = expandedEventId === evt.event_id;
            const meta = EVENT_TYPE_META[evt.type] || {
              category: 'System',
              color: '#94a3b8',
              icon: '●',
              severity: 'info',
            };

            return (
              <div
                key={evt.event_id}
                className="rounded-lg border border-slate-800/80 bg-slate-950/70 hover:bg-slate-900/80 transition-all p-3 space-y-2"
              >
                <div
                  onClick={() => toggleExpand(evt.event_id)}
                  className="flex items-center justify-between cursor-pointer"
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <EventDot type={evt.type} size="md" />

                    <span className="text-[11px] text-slate-400 font-mono shrink-0">
                      {new Date(evt.timestamp).toLocaleTimeString([], { hour12: false })}
                    </span>

                    <span
                      className="text-xs font-semibold px-2 py-0.5 rounded border"
                      style={{
                        borderColor: `${meta.color}40`,
                        backgroundColor: `${meta.color}15`,
                        color: meta.color,
                      }}
                    >
                      {evt.type}
                    </span>

                    {evt.entity_id && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          const ent = entities.find((x) => x.entity_id === evt.entity_id);
                          if (ent) selectEntity(ent);
                        }}
                        className="px-2 py-0.5 rounded bg-slate-800 text-cyan-300 hover:bg-slate-700 text-xs"
                      >
                        {evt.entity_id}
                      </button>
                    )}

                    <span className="text-slate-400 text-xs truncate">
                      src: {evt.source}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <ConfidenceBadge confidence={evt.confidence ?? 1.0} size="sm" />
                    <ChevronRight
                      className={`w-4 h-4 text-slate-500 transition-transform ${
                        isExpanded ? 'rotate-90' : ''
                      }`}
                    />
                  </div>
                </div>

                {/* Expanded Payload & Provenance */}
                {isExpanded && (
                  <div className="pt-3 border-t border-slate-800/80 space-y-2 text-xs">
                    {evt.changes && Object.keys(evt.changes).length > 0 && (
                      <div>
                        <span className="text-[10px] text-slate-500 uppercase block mb-1">
                          Changes & Telemetry
                        </span>
                        <pre className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-300 text-[11px] overflow-x-auto">
                          {JSON.stringify(evt.changes, null, 2)}
                        </pre>
                      </div>
                    )}

                    {evt.provenance && evt.provenance.length > 0 && (
                      <div>
                        <span className="text-[10px] text-slate-500 uppercase block mb-1">
                          Provenance Trail
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {evt.provenance.map((step, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-[11px]"
                            >
                              ↳ {step}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default EventTimeline;

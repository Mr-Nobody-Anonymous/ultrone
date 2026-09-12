import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import StatusBar from '../components/StatusBar';
import CommandBar from '../components/CommandBar';
import ConfidenceBadge from '../components/ConfidenceBadge';
import ProvenanceChain from '../components/ProvenanceChain';
import EventDot from '../components/EventDot';
import { useWorldStore } from '../store/worldStore';
import { useUIStore } from '../store/uiStore';
import {
  X,
  Radio,
  Share2,
  Activity,
  ChevronDown,
  ChevronUp,
  Target,
  Shield,
  Clock,
} from 'lucide-react';
import { clsx } from 'clsx';
import type { Entity } from '../types/entity';

export default function ConsoleLayout() {
  const selectedEntity = useWorldStore((s) => s.selectedEntity);
  const selectEntity = useWorldStore((s) => s.selectEntity);
  const events = useWorldStore((s) => s.events);
  const {
    bottomTimelineOpen,
    toggleBottomTimeline,
  } = useUIStore();

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-slate-950 text-slate-100 select-none">
      {/* Top status bar */}
      <StatusBar />

      {/* Main workspace */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Left navigation sidebar */}
        <Sidebar />

        {/* Center operational area: Route view + Collapsible bottom timeline */}
        <div className="flex flex-1 flex-col overflow-hidden relative">
          {/* Main active view */}
          <main className="flex-1 overflow-hidden relative bg-slate-950">
            <Outlet />
          </main>

          {/* Collapsible Bottom Timeline Bar */}
          <div
            className={clsx(
              'border-t border-slate-800 bg-slate-900/95 transition-all duration-300 flex flex-col z-20',
              bottomTimelineOpen ? 'h-44' : 'h-8'
            )}
          >
            {/* Header / Toggle Strip */}
            <div
              onClick={toggleBottomTimeline}
              className="flex h-8 items-center justify-between px-4 bg-slate-900 border-b border-slate-800/80 cursor-pointer hover:bg-slate-850 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Activity className="w-3.5 h-3.5 text-ultrone-400" />
                <span className="font-mono text-xs font-semibold uppercase tracking-wider text-slate-300">
                  Live Event Feed
                </span>
                <span className="rounded-full bg-slate-800 px-2 py-0.2 text-[10px] font-mono text-slate-400 border border-slate-700">
                  {events.length} events
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <span className="text-[11px] font-mono text-slate-500 hidden sm:inline">
                  {bottomTimelineOpen ? 'Click to minimize' : 'Click to expand'}
                </span>
                {bottomTimelineOpen ? (
                  <ChevronDown className="w-3.5 h-3.5" />
                ) : (
                  <ChevronUp className="w-3.5 h-3.5" />
                )}
              </div>
            </div>

            {/* Bottom Timeline Content */}
            {bottomTimelineOpen && (
              <div className="flex-1 overflow-y-auto p-2 space-y-1 font-mono text-xs">
                {events.slice(0, 15).map((evt) => (
                  <div
                    key={evt.event_id}
                    className="flex items-center justify-between p-1.5 rounded bg-slate-950/60 hover:bg-slate-800/60 border border-slate-800/60 transition-colors"
                  >
                    <div className="flex items-center gap-2.5 overflow-hidden">
                      <EventDot type={evt.type} size="sm" />
                      <span className="text-slate-400 text-[10px] shrink-0">
                        {new Date(evt.timestamp).toLocaleTimeString([], { hour12: false })}
                      </span>
                      <span className="text-ultrone-300 font-semibold uppercase text-[11px]">
                        {evt.type}
                      </span>
                      {evt.entity_id && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            const ent = useWorldStore.getState().entities.find((x) => x.entity_id === evt.entity_id);
                            if (ent) selectEntity(ent);
                          }}
                          className="px-1.5 py-0.2 rounded bg-slate-800 text-cyan-300 hover:underline text-[10px]"
                        >
                          {evt.entity_id}
                        </button>
                      )}
                      <span className="text-slate-400 truncate text-[11px]">
                        src: {evt.source}
                      </span>
                    </div>
                    <div className="shrink-0 flex items-center gap-2">
                      <ConfidenceBadge confidence={evt.confidence ?? 1.0} size="sm" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Entity Inspector Panel */}
        {selectedEntity && (
          <aside className="w-88 shrink-0 overflow-y-auto border-l border-slate-800 bg-slate-900/95 p-4 shadow-2xl z-30 transition-all">
            <EntityDetailPanel
              entity={selectedEntity}
              onClose={() => selectEntity(null)}
            />
          </aside>
        )}
      </div>

      {/* Bottom Command Bar */}
      <CommandBar />
    </div>
  );
}

/** Full operational detail panel for the selected entity */
function EntityDetailPanel({
  entity,
  onClose,
}: {
  entity: Entity;
  onClose: () => void;
}) {
  const selectEntity = useWorldStore((s) => s.selectEntity);
  const allEntities = useWorldStore((s) => s.entities);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-slate-800 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-base font-bold text-slate-100">
              {entity.entity_id}
            </span>
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
          </div>
          <span className="text-xs text-slate-400 uppercase tracking-wider font-mono">
            {entity.type.replace('_', ' ')} • {entity.status}
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-md text-slate-400 hover:bg-slate-800 hover:text-slate-100 transition-colors"
          title="Close Inspector"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Confidence and Metrics Summary */}
      <div className="grid grid-cols-2 gap-2">
        <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800">
          <span className="text-[10px] uppercase font-mono text-slate-500 block mb-1">
            System Confidence
          </span>
          <ConfidenceBadge confidence={entity.confidence} size="md" />
        </div>
        <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800">
          <span className="text-[10px] uppercase font-mono text-slate-500 block mb-1">
            Operational State
          </span>
          <span className="text-xs font-mono font-semibold text-emerald-400 uppercase">
            {entity.status}
          </span>
        </div>
      </div>

      {/* Spatial Telemetry */}
      {entity.position && (
        <section className="space-y-2 rounded-lg bg-slate-950/40 p-3 border border-slate-800/80">
          <div className="flex items-center gap-1.5 text-xs font-mono text-slate-300 font-semibold">
            <Target className="w-3.5 h-3.5 text-cyan-400" />
            <span>Position Telemetry</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
            <div>
              <span className="text-[10px] text-slate-500 uppercase block">Latitude</span>
              <span className="text-slate-200">{entity.position.lat.toFixed(4)}°</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 uppercase block">Longitude</span>
              <span className="text-slate-200">{entity.position.lng.toFixed(4)}°</span>
            </div>
            {entity.position.alt !== undefined && (
              <div>
                <span className="text-[10px] text-slate-500 uppercase block">Altitude</span>
                <span className="text-slate-200">{entity.position.alt} ft</span>
              </div>
            )}
            {entity.velocity && (
              <div>
                <span className="text-[10px] text-slate-500 uppercase block">Speed (3-Axis)</span>
                <span className="text-slate-200">
                  {Math.round(Math.sqrt(entity.velocity.x**2 + entity.velocity.y**2))} kts
                </span>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Active Sensor Feeds */}
      {entity.sensors && entity.sensors.length > 0 && (
        <section className="space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs font-mono text-slate-400 uppercase tracking-wider">
            <Radio className="w-3.5 h-3.5 text-indigo-400" />
            <span>Active Sensor Feeds</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {entity.sensors.map((sensor) => (
              <span
                key={sensor}
                className="rounded bg-slate-800 px-2 py-0.5 font-mono text-xs text-slate-300 border border-slate-700/60"
              >
                {sensor}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Observations */}
      {entity.observations && entity.observations.length > 0 && (
        <section className="space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-mono text-slate-400 uppercase tracking-wider">
            <Clock className="w-3.5 h-3.5 text-amber-400" />
            <span>Observations ({entity.observations.length})</span>
          </div>
          <div className="space-y-1.5 max-h-48 overflow-y-auto">
            {entity.observations.map((obs, i) => (
              <div
                key={i}
                className="rounded bg-slate-950/60 p-2 border border-slate-800/80 text-xs space-y-1"
              >
                <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
                  <span>{obs.source}</span>
                  <ConfidenceBadge confidence={obs.confidence} size="sm" />
                </div>
                <div className="text-slate-300 text-xs">{obs.description}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Relationships */}
      {entity.relationships && entity.relationships.length > 0 && (
        <section className="space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-mono text-slate-400 uppercase tracking-wider">
            <Share2 className="w-3.5 h-3.5 text-ultrone-400" />
            <span>Entity Relationships</span>
          </div>
          <div className="space-y-1">
            {entity.relationships.map((rel, i) => {
              const target = allEntities.find((e) => e.entity_id === rel.target_id);
              return (
                <div
                  key={i}
                  onClick={() => target && selectEntity(target)}
                  className="flex items-center justify-between p-2 rounded bg-slate-950/60 hover:bg-slate-800/60 border border-slate-800 cursor-pointer transition-colors text-xs"
                >
                  <div className="flex items-center gap-1.5 font-mono">
                    <span className="text-slate-400 text-[11px] uppercase">
                      {rel.relation} →
                    </span>
                    <span className="text-ultrone-400 font-semibold">
                      {rel.target_id}
                    </span>
                  </div>
                  <ConfidenceBadge confidence={rel.confidence} size="sm" />
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Provenance */}
      {entity.provenance && (
        <ProvenanceChain provenance={entity.provenance} />
      )}

      {/* Tactical Actions */}
      <section className="pt-2 border-t border-slate-800 space-y-2">
        <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block">
          Tactical Directives
        </span>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => alert(`Tracking directive locked for ${entity.entity_id}`)}
            className="flex items-center justify-center gap-1.5 rounded bg-ultrone-600/20 hover:bg-ultrone-600/30 border border-ultrone-500/40 p-2 text-xs font-mono text-ultrone-300 font-semibold transition-colors"
          >
            <Target className="w-3.5 h-3.5" />
            Lock Track
          </button>
          <button
            onClick={() => alert(`COA analysis triggered for ${entity.entity_id}`)}
            className="flex items-center justify-center gap-1.5 rounded bg-slate-800 hover:bg-slate-750 border border-slate-700 p-2 text-xs font-mono text-slate-200 font-semibold transition-colors"
          >
            <Shield className="w-3.5 h-3.5" />
            Analyze COA
          </button>
        </div>
      </section>
    </div>
  );
}

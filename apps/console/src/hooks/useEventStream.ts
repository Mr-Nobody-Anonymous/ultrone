import { useEffect } from 'react';
import { useWorldStore } from '../store/worldStore';
import { EventType } from '../types/event';

export function useEventStream() {
  const events = useWorldStore((s) => s.events);
  const addEvent = useWorldStore((s) => s.addEvent);

  // Periodic simulated live events when idling to make console feel alive
  useEffect(() => {
    const timer = setInterval(() => {
      const sampleEvents = [
        {
          type: EventType.SENSOR_READING,
          source: 'radar_network_station_01',
          entity_id: 'entity_001',
          changes: { confidence: 0.94, signal_strength_db: -42 },
          confidence: 0.94,
          provenance: ['sensor_station_01', 'signal_filter'],
          metadata: { frequency_ghz: 9.4 },
        },
        {
          type: EventType.SIMULATION_TICK,
          source: 'physics_engine_sim',
          changes: { tick: Date.now() },
          confidence: 1.0,
          provenance: ['simulation_core'],
          metadata: { dt: 0.016 },
        },
      ];

      const chosen = sampleEvents[Math.floor(Math.random() * sampleEvents.length)];
      addEvent({
        event_id: `evt_live_${Date.now().toString(36)}`,
        type: chosen.type,
        timestamp: new Date().toISOString(),
        source: chosen.source,
        entity_id: chosen.entity_id,
        changes: chosen.changes,
        confidence: chosen.confidence,
        provenance: chosen.provenance,
        metadata: chosen.metadata,
      });
    }, 8000);

    return () => clearInterval(timer);
  }, [addEvent]);

  return {
    events,
    addEvent,
    recentEvents: events.slice(0, 20),
  };
}

export default useEventStream;

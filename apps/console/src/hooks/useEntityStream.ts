import { useEffect } from 'react';
import { useWorldStore } from '../store/worldStore';
import type { Entity } from '../types/entity';

export function useEntityStream() {
  const entities = useWorldStore((s) => s.entities);
  const updateEntity = useWorldStore((s) => s.updateEntity);
  const selectedEntity = useWorldStore((s) => s.selectedEntity);
  const selectEntity = useWorldStore((s) => s.selectEntity);

  // Simulated live jitter for demo purposes when not connected to live backend
  useEffect(() => {
    const timer = setInterval(() => {
      if (entities.length === 0) return;
      // Slightly drift one of the active air assets to simulate live radar/telemetry
      const airAsset = entities.find((e) => e.type === 'air_asset' && e.position);
      if (airAsset && airAsset.position) {
        const deltaLat = (Math.random() - 0.5) * 0.002;
        const deltaLng = (Math.random() - 0.5) * 0.002;
        updateEntity(airAsset.entity_id, {
          position: {
            ...airAsset.position,
            lat: airAsset.position.lat + deltaLat,
            lng: airAsset.position.lng + deltaLng,
          },
        });
      }
    }, 3000);

    return () => clearInterval(timer);
  }, [entities, updateEntity]);

  return {
    entities,
    selectedEntity,
    selectEntity,
    updateEntity,
    getEntityById: (id: string): Entity | undefined => entities.find((e) => e.entity_id === id),
  };
}

export default useEntityStream;

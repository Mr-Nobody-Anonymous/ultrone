import type { FC } from 'react';
import { useRef, useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { useSimulation } from '../../contexts/SimulationContext';

interface MapLayer {
  id: string;
  name: string;
  type: 'street' | 'satellite' | 'terrain' | 'grid' | 'heatmap' | 'influence' | 'sensor' | 'comm' | 'risk' | 'resource';
  visible: boolean;
  opacity: number;
}

const DEFAULT_LAYERS: MapLayer[] = [
  { id: 'street', name: 'Street Map', type: 'street', visible: true, opacity: 1 },
  { id: 'satellite', name: 'Satellite', type: 'satellite', visible: false, opacity: 1 },
  { id: 'terrain', name: 'Terrain', type: 'terrain', visible: false, opacity: 0.7 },
  { id: 'grid', name: 'Coordinate Grid', type: 'grid', visible: true, opacity: 0.5 },
  { id: 'heatmap', name: 'Threat Heatmap', type: 'heatmap', visible: false, opacity: 0.6 },
  { id: 'influence', name: 'Influence Map', type: 'influence', visible: false, opacity: 0.5 },
  { id: 'sensor', name: 'Sensor Coverage', type: 'sensor', visible: false, opacity: 0.4 },
  { id: 'comm', name: 'Comm Range', type: 'comm', visible: false, opacity: 0.4 },
  { id: 'risk', name: 'Risk Overlay', type: 'risk', visible: false, opacity: 0.5 },
  { id: 'resource', name: 'Resource Overlay', type: 'resource', visible: false, opacity: 0.5 },
];

const MapLibreMap: FC = () => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const [layers, setLayers] = useState<MapLayer[]>(DEFAULT_LAYERS);
  const [showLayerManager, setShowLayerManager] = useState(false);
  const [showMeasure, setShowMeasure] = useState(false);
  const [coordinates, setCoordinates] = useState({ lat: 0, lng: 0, zoom: 1 });
  const { worldState } = useSimulation();

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;
    const init = async () => {
      try {
        const ml = await import('maplibre-gl');
        const map = new ml.default.Map({
          container: mapContainer.current!, style: 'https://demotiles.maplibre.org/style.json',
          center: [0, 0], zoom: 2, attributionControl: false,
        });
        map.addControl(new ml.default.NavigationControl(), 'top-right');
        map.on('move', () => {
          const c = map.getCenter();
          setCoordinates({ lat: c.lat, lng: c.lng, zoom: map.getZoom() });
        });
        map.on('load', () => {
          map.addSource('agents', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
          map.addLayer({ id: 'agent-markers', type: 'symbol', source: 'agents',
            layout: { 'icon-image': 'marker', 'icon-size': 0.8, 'text-field': ['get', 'label'], 'text-offset': [0, 1.5], 'text-size': 10 },
            paint: { 'text-color': '#ffffff' } });
          map.addSource('threats', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
          map.addLayer({ id: 'threat-heat', type: 'heatmap', source: 'threats',
            paint: { 'heatmap-radius': 30, 'heatmap-weight': ['get', 'confidence'],
              'heatmap-color': ['interpolate', ['linear'], ['heatmap-density'], 0, 'rgba(0,0,0,0)', 0.5, 'rgba(255,0,0,0.3)', 1, 'rgba(255,0,0,0.8)'] } });
        });
        mapRef.current = map;
      } catch { console.warn('MapLibre unavailable'); }
    };
    init();
    return () => { mapRef.current?.remove(); mapRef.current = null; };
  }, []);

  useEffect(() => {
    if (!mapRef.current || !worldState?.agents) return;
    const src = mapRef.current.getSource('agents');
    if (!src) return;
    src.setData({
      type: 'FeatureCollection',
      features: worldState.agents.map((a: any) => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [a.position[1], a.position[0]] },
        properties: { label: `${a.type} ${a.id.slice(0,4)}`, health: a.health, status: a.status },
      })),
    });
  }, [worldState]);

  return (
    <div className="relative h-full w-full rounded-lg overflow-hidden bg-gray-900">
      <div ref={mapContainer} className="absolute inset-0" />
      <div className="absolute top-2 left-2 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded text-xs font-mono z-10 text-white/80">
        {coordinates.lat.toFixed(4)}°N, {coordinates.lng.toFixed(4)}°E | Z: {coordinates.zoom.toFixed(1)}x
      </div>
      <div className="absolute top-2 right-2 flex gap-1 z-10">
        <button onClick={() => setShowLayerManager(v => !v)} className="bg-black/60 backdrop-blur-md px-2 py-1 rounded text-xs text-white/80 hover:bg-white/20">
          Layers ({layers.filter(l => l.visible).length})
        </button>
        <button onClick={() => setShowMeasure(v => !v)} className="bg-black/60 backdrop-blur-md px-2 py-1 rounded text-xs text-white/80 hover:bg-white/20">
          Measure
        </button>
      </div>
      {showLayerManager && (
        <div className="absolute top-12 left-2 bg-black/80 backdrop-blur-md p-3 rounded z-20 min-w-[200px]">
          {layers.map(layer => (
            <label key={layer.id} className="flex items-center gap-2 px-2 py-1 text-xs hover:bg-white/5 rounded cursor-pointer text-white/70">
              <input type="checkbox" checked={layer.visible} onChange={() => setLayers(prev => prev.map(l => l.id === layer.id ? { ...l, visible: !l.visible } : l))} className="accent-blue-500" />
              {layer.name}
            </label>
          ))}
        </div>
      )}
      {showMeasure && (
        <div className="absolute top-12 right-2 bg-black/80 backdrop-blur-md p-3 rounded z-20 min-w-[160px]">
          <div className="text-xs text-white/60 mb-2">Measurement</div>
          <button className="w-full text-left px-2 py-1 text-xs text-white/70 hover:bg-white/10 rounded">📏 Measure Distance</button>
          <button className="w-full text-left px-2 py-1 text-xs text-white/70 hover:bg-white/10 rounded">📐 Measure Area</button>
        </div>
      )}
      <div className="absolute bottom-2 left-2 right-2 bg-black/60 backdrop-blur-md px-4 py-2 rounded z-10">
        <div className="flex items-center gap-3">
          <span className="text-xs text-white/50 w-16">T+ 00:00</span>
          <input type="range" min={0} max={1000} className="flex-1 accent-blue-500 h-1" />
          <span className="text-xs text-white/50 w-16 text-right">T+ 10:00</span>
          <button className="text-xs px-2 py-1 bg-blue-600/50 hover:bg-blue-600/70 rounded text-white">▶</button>
        </div>
      </div>
    </div>
  );
};

export default MapLibreMap;


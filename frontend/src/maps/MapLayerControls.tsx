import type { FC } from 'react';
import { Layers, Eye, EyeOff, Sliders, MapPin } from 'lucide-react';

interface MapLayer {
  id: string;
  name: string;
  type: 'satellite' | 'terrain' | 'heatmap' | 'grid' | 'influence' | 'sensor' | 'comm' | 'resource';
  visible: boolean;
  opacity: number;
  description: string;
}

const DEFAULT_LAYERS: MapLayer[] = [
  { id: 'satellite', name: 'Satellite', type: 'satellite', visible: true, opacity: 1.0, description: 'Real-world satellite imagery base layer' },
  { id: 'terrain', name: 'Terrain', type: 'terrain', visible: false, opacity: 0.7, description: 'Elevation and terrain features' },
  { id: 'heatmap', name: 'Threat Heatmap', type: 'heatmap', visible: false, opacity: 0.6, description: 'Predicted threat density overlay' },
  { id: 'grid', name: 'Coordinate Grid', type: 'grid', visible: true, opacity: 0.4, description: 'MGRS-style coordinate grid' },
  { id: 'influence', name: 'Influence Map', type: 'influence', visible: false, opacity: 0.5, description: 'Blue/Red control influence zones' },
  { id: 'sensor', name: 'Sensor Coverage', type: 'sensor', visible: false, opacity: 0.4, description: 'Friendly sensor range coverage' },
  { id: 'comm', name: 'Comm Range', type: 'comm', visible: false, opacity: 0.3, description: 'Communication network coverage' },
  { id: 'resource', name: 'Resources', type: 'resource', visible: false, opacity: 0.5, description: 'Supply nodes and resource locations' },
];

const MapLayerControls: FC = () => {
  return (
    <div className="rounded-lg bg-surface-900/90 backdrop-blur-md border border-surface-700/30 p-3 min-w-[200px]">
      <div className="flex items-center gap-2 mb-3">
        <Layers size={14} className="text-primary-400" />
        <span className="text-xs font-semibold text-surface-200">Map Layers</span>
      </div>
      <div className="space-y-1">
        {DEFAULT_LAYERS.map(layer => (
          <div key={layer.id} className="group flex items-center gap-2 px-2 py-1.5 rounded hover:bg-surface-800/50 cursor-pointer">
            <div className={`w-3 h-3 rounded border ${layer.visible ? 'bg-primary-500 border-primary-500' : 'border-surface-600'}`}>
              {layer.visible && <div className="w-full h-full flex items-center justify-center text-[8px] text-white">✓</div>}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <MapPin size={10} className="text-surface-500" />
                <span className="text-[11px] text-surface-300 truncate">{layer.name}</span>
              </div>
              <div className="text-[9px] text-surface-600 truncate">{layer.description}</div>
            </div>
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button className="p-0.5 hover:bg-surface-700 rounded">
                {layer.visible ? <Eye size={10} className="text-surface-400" /> : <EyeOff size={10} className="text-surface-600" />}
              </button>
              <button className="p-0.5 hover:bg-surface-700 rounded">
                <Sliders size={10} className="text-surface-400" />
              </button>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-3 pt-2 border-t border-surface-700/30">
        <div className="flex items-center justify-between text-[10px] text-surface-500">
          <span>Layer Opacity</span>
          <span>75%</span>
        </div>
        <input type="range" min={0} max={100} defaultValue={75} className="w-full mt-1 accent-primary-500 h-1" />
      </div>
    </div>
  );
};

export default MapLayerControls;

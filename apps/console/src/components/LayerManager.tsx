import React from 'react';
import { useLayerStore } from '../store/layerStore';
import { LayerCategory } from '../types/layer';
import {
  Layers,
  Eye,
  EyeOff,
  Sliders,
  RotateCcw,
  X,
  MapPin,
  CloudRain,
  Activity,
  Globe,
} from 'lucide-react';

export const LayerManager: React.FC = () => {
  const {
    layers,
    isLayerDrawerOpen,
    setLayerDrawerOpen,
    toggleLayer,
    setLayerOpacity,
    resetLayers,
  } = useLayerStore();

  if (!isLayerDrawerOpen) return null;

  const categories: { key: LayerCategory; label: string; icon: any }[] = [
    { key: 'base_map', label: 'Base Cartography', icon: Globe },
    { key: 'objects', label: 'Tracked Entities', icon: MapPin },
    { key: 'environment', label: 'Environment & Radar', icon: CloudRain },
    { key: 'analytics', label: 'Analytics Overlays', icon: Activity },
  ];

  return (
    <div className="absolute top-16 left-4 z-40 w-80 rounded-xl border border-slate-700/80 bg-slate-900/95 backdrop-blur-md shadow-2xl p-4 font-mono select-none text-xs flex flex-col max-h-[calc(100vh-140px)] animate-in fade-in duration-150">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-ultrone-400" />
          <h3 className="font-bold text-slate-100 uppercase tracking-wider text-[11px]">
            Geospatial Layer Manager
          </h3>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={resetLayers}
            title="Reset to default layers"
            className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setLayerDrawerOpen(false)}
            className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Layer Groups */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1">
        {categories.map(({ key, label, icon: Icon }) => {
          const categoryLayers = layers.filter((l) => l.category === key);
          return (
            <div key={key} className="space-y-1.5">
              <div className="flex items-center gap-1.5 text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                <Icon className="w-3 h-3 text-cyan-400" />
                <span>{label}</span>
                <span className="text-slate-600">({categoryLayers.length})</span>
              </div>

              <div className="space-y-1">
                {categoryLayers.map((layer) => (
                  <div
                    key={layer.id}
                    className={`rounded-lg p-2 border transition-all ${
                      layer.enabled
                        ? 'bg-slate-950/70 border-slate-800'
                        : 'bg-slate-950/30 border-slate-900 opacity-60'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={layer.enabled}
                          onChange={() => toggleLayer(layer.id)}
                          className="accent-ultrone-500 rounded cursor-pointer"
                        />
                        <span
                          className={`text-xs font-semibold ${
                            layer.enabled ? 'text-slate-200' : 'text-slate-500'
                          }`}
                        >
                          {layer.name}
                        </span>
                      </label>
                      <button
                        onClick={() => toggleLayer(layer.id)}
                        className="text-slate-500 hover:text-slate-300"
                      >
                        {layer.enabled ? (
                          <Eye className="w-3.5 h-3.5 text-ultrone-400" />
                        ) : (
                          <EyeOff className="w-3.5 h-3.5 text-slate-600" />
                        )}
                      </button>
                    </div>

                    <p className="text-[10px] text-slate-500 mt-1 line-clamp-1">
                      {layer.description}
                    </p>

                    {/* Opacity Slider */}
                    {layer.enabled && (
                      <div className="mt-2 flex items-center gap-2 pt-1 border-t border-slate-900">
                        <Sliders className="w-3 h-3 text-slate-600 shrink-0" />
                        <span className="text-[10px] text-slate-500 w-7">
                          {Math.round(layer.opacity * 100)}%
                        </span>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.05"
                          value={layer.opacity}
                          onChange={(e) => setLayerOpacity(layer.id, parseFloat(e.target.value))}
                          className="w-full accent-ultrone-500 h-1 bg-slate-800 rounded cursor-pointer"
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default LayerManager;

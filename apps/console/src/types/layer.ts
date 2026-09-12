export type LayerCategory = 'base_map' | 'objects' | 'environment' | 'analytics';

export type LayerType = 'raster' | 'vector' | 'terrain_3d' | 'tiles_3d' | 'geojson' | 'heatmap';

export interface MapLayer {
  id: string;
  name: string;
  category: LayerCategory;
  type: LayerType;
  enabled: boolean;
  opacity: number;
  zIndex: number;
  description: string;
}

export const INITIAL_LAYERS: MapLayer[] = [
  // 1. Base Map
  { id: 'base-dark', name: 'Dark Vector Grid', category: 'base_map', type: 'vector', enabled: true, opacity: 1.0, zIndex: 0, description: 'High-contrast low-light tactical cartography' },
  { id: 'base-satellite', name: 'Satellite Imagery', category: 'base_map', type: 'raster', enabled: false, opacity: 1.0, zIndex: 1, description: 'High-resolution true-color orbital imagery' },
  { id: 'base-terrain', name: '3D Terrain Mesh', category: 'base_map', type: 'terrain_3d', enabled: true, opacity: 1.0, zIndex: 2, description: 'Global digital elevation model (DEM)' },

  // 2. Objects
  { id: 'ent-sensors', name: 'Sensor Nodes & Radar', category: 'objects', type: 'geojson', enabled: true, opacity: 1.0, zIndex: 10, description: 'Active & passive sensor listening posts' },
  { id: 'ent-air', name: 'Air Assets & UAVs', category: 'objects', type: 'geojson', enabled: true, opacity: 1.0, zIndex: 11, description: 'Tracked airborne contacts & telemetry' },
  { id: 'ent-ground', name: 'Ground Assets', category: 'objects', type: 'geojson', enabled: true, opacity: 1.0, zIndex: 12, description: 'Tracked vehicular ground assets' },
  { id: 'ent-sim', name: 'Simulated Swarms', category: 'objects', type: 'geojson', enabled: true, opacity: 0.85, zIndex: 13, description: 'Synthetic experimentation entities' },

  // 3. Environment
  { id: 'env-radar-cones', name: 'Radar Coverage Arcs', category: 'environment', type: 'geojson', enabled: true, opacity: 0.35, zIndex: 20, description: 'Radar field-of-view line-of-sight cones' },
  { id: 'env-weather-ecm', name: 'ECM & Weather Clouds', category: 'environment', type: 'raster', enabled: false, opacity: 0.5, zIndex: 21, description: 'Precipitation, thermal drift & electronic jamming' },

  // 4. Analytics
  { id: 'anl-density', name: 'Contact Density Heatmap', category: 'analytics', type: 'heatmap', enabled: false, opacity: 0.6, zIndex: 30, description: 'Spatial concentration of active contacts' },
  { id: 'anl-trajectories', name: 'Extrapolated Vectors', category: 'analytics', type: 'vector', enabled: true, opacity: 0.8, zIndex: 31, description: 'Kinematic trajectory extrapolation' },
  { id: 'anl-corridors', name: 'Safety & Flight Corridors', category: 'analytics', type: 'geojson', enabled: true, opacity: 0.25, zIndex: 32, description: 'Airspace separation boundaries' },
];

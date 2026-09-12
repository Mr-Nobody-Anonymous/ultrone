import { create } from 'zustand';
import type { Entity } from '../types/entity';
import type { UltroneEvent } from '../types/event';

// ─── Demo Data ──────────────────────────────────────────────────────────────

const DEMO_ENTITIES: Entity[] = [
  {
    entity_id: 'entity_001',
    type: 'air_asset',
    status: 'active',
    position: { lat: 34.0522, lng: -118.2437, alt: 8200 },
    velocity: { x: 120, y: 0, z: -5 },
    sensors: ['radar-01', 'eo-02'],
    observations: [
      { timestamp: '2024-01-15T12:40:00Z', source: 'radar-01', description: 'Initial detection, bearing 045°', confidence: 0.82, raw_data: { bearing: 45, range_nm: 12 } },
      { timestamp: '2024-01-15T12:41:00Z', source: 'eo-02', description: 'Visual confirmation, track stable', confidence: 0.91, raw_data: { track_quality: 'firm' } },
      { timestamp: '2024-01-15T12:42:30Z', source: 'sensor_fusion', description: 'Fused track — altitude 8200ft, heading 270°', confidence: 0.95, raw_data: { heading: 270 } },
    ],
    confidence: 0.87,
    provenance: ['sensor_fusion_v2', 'radar-01', 'eo-02'],
    relationships: [
      { target_id: 'entity_003', relation: 'observes', confidence: 0.92 },
      { target_id: 'entity_005', relation: 'located_in', confidence: 1.0 },
    ],
    created_at: '2024-01-15T12:40:00Z',
    updated_at: '2024-01-15T12:42:30Z',
  },
  {
    entity_id: 'entity_002',
    type: 'ground_vehicle',
    status: 'active',
    position: { lat: 34.0610, lng: -118.2380 },
    velocity: { x: 35, y: 10, z: 0 },
    sensors: ['sigint-03'],
    observations: [
      { timestamp: '2024-01-15T12:38:00Z', source: 'sigint-03', description: 'SIGINT intercept — voice comms detected', confidence: 0.78, raw_data: { frequency: '225.5MHz' } },
      { timestamp: '2024-01-15T12:41:15Z', source: 'sigint-03', description: 'Secondary intercept confirms movement', confidence: 0.85, raw_data: { direction: 'north' } },
    ],
    confidence: 0.72,
    provenance: ['sigint_processor', 'sigint-03'],
    relationships: [
      { target_id: 'entity_004', relation: 'communicates_with', confidence: 0.68 },
      { target_id: 'entity_005', relation: 'located_in', confidence: 1.0 },
    ],
    created_at: '2024-01-15T12:38:00Z',
    updated_at: '2024-01-15T12:41:15Z',
  },
  {
    entity_id: 'entity_003',
    type: 'sensor',
    status: 'active',
    position: { lat: 34.0480, lng: -118.2550 },
    sensors: [],
    observations: [
      { timestamp: '2024-01-15T12:00:00Z', source: 'system', description: 'Sensor online — radar coverage 120° arc', confidence: 1.0 },
    ],
    confidence: 0.99,
    provenance: ['system_monitor'],
    relationships: [
      { target_id: 'entity_001', relation: 'observes', confidence: 0.92 },
      { target_id: 'entity_005', relation: 'located_in', confidence: 1.0 },
    ],
    created_at: '2024-01-15T12:00:00Z',
    updated_at: '2024-01-15T12:42:30Z',
  },
  {
    entity_id: 'entity_004',
    type: 'communication_node',
    status: 'active',
    position: { lat: 34.0700, lng: -118.2300 },
    sensors: ['sigint-03', 'elint-01'],
    observations: [
      { timestamp: '2024-01-15T12:35:00Z', source: 'elint-01', description: 'Active emitter detected — 2.4GHz band', confidence: 0.65 },
    ],
    confidence: 0.65,
    provenance: ['sigint_processor', 'elint-01'],
    relationships: [
      { target_id: 'entity_002', relation: 'communicates_with', confidence: 0.68 },
    ],
    created_at: '2024-01-15T12:35:00Z',
    updated_at: '2024-01-15T12:38:00Z',
  },
  {
    entity_id: 'entity_005',
    type: 'region',
    status: 'active',
    position: { lat: 34.0550, lng: -118.2400 },
    sensors: [],
    observations: [],
    confidence: 1.0,
    provenance: ['map_data'],
    relationships: [
      { target_id: 'entity_001', relation: 'related_to', confidence: 1.0 },
      { target_id: 'entity_002', relation: 'related_to', confidence: 1.0 },
      { target_id: 'entity_003', relation: 'related_to', confidence: 1.0 },
    ],
    metadata: { name: 'Sector Alpha', area_sqkm: 45 },
    created_at: '2024-01-15T08:00:00Z',
    updated_at: '2024-01-15T08:00:00Z',
  },
  {
    entity_id: 'entity_006',
    type: 'agent',
    status: 'active',
    position: { lat: 34.0500, lng: -118.2500 },
    sensors: [],
    observations: [
      { timestamp: '2024-01-15T12:42:00Z', source: 'cognitive_loop', description: 'Running anomaly detection on Sector Alpha', confidence: 1.0 },
    ],
    confidence: 1.0,
    provenance: ['orchestrator'],
    relationships: [
      { target_id: 'entity_005', relation: 'observes', confidence: 1.0 },
    ],
    metadata: { agent_type: 'recon_analyzer', model: 'cognitive_loop_v3' },
    created_at: '2024-01-15T12:00:00Z',
    updated_at: '2024-01-15T12:42:00Z',
  },
];

const DEMO_EVENTS: UltroneEvent[] = [
  { event_id: 'evt_a1b2c3d4e5f6', type: 'ENTITY_CREATED', timestamp: '2024-01-15T12:38:00Z', source: 'sigint_processor', entity_id: 'entity_002', confidence: 0.78 },
  { event_id: 'evt_b2c3d4e5f6a7', type: 'ENTITY_UPDATED', timestamp: '2024-01-15T12:40:00Z', source: 'radar-01', entity_id: 'entity_001', changes: { position: { lat: 34.0522, lng: -118.2437 } }, confidence: 0.82 },
  { event_id: 'evt_c3d4e5f6a7b8', type: 'OBSERVATION_ADDED', timestamp: '2024-01-15T12:41:00Z', source: 'eo-02', entity_id: 'entity_001', confidence: 0.91 },
  { event_id: 'evt_d4e5f6a7b8c9', type: 'ANOMALY_DETECTED', timestamp: '2024-01-15T12:41:30Z', source: 'cognitive_loop', entity_id: 'entity_002', confidence: 0.73, severity: 'critical', metadata: { anomaly_type: 'unexpected_movement_pattern' } },
  { event_id: 'evt_e5f6a7b8c9d0', type: 'ENTITY_UPDATED', timestamp: '2024-01-15T12:41:15Z', source: 'sigint_processor', entity_id: 'entity_002', changes: { confidence: 0.85 }, confidence: 0.85 },
  { event_id: 'evt_f6a7b8c9d0e1', type: 'REASONING_COMPLETE', timestamp: '2024-01-15T12:42:00Z', source: 'cognitive_loop', entity_id: 'entity_006', confidence: 0.94, metadata: { reasoning_type: 'anomaly_correlation', entities_analyzed: 3 } },
  { event_id: 'evt_g7b8c9d0e1f2', type: 'DECISION_MADE', timestamp: '2024-01-15T12:42:15Z', source: 'planning_layer', confidence: 0.88, metadata: { decision: 'Increase surveillance on entity_002', requires_approval: true } },
  { event_id: 'evt_h8c9d0e1f2g3', type: 'ENTITY_UPDATED', timestamp: '2024-01-15T12:42:30Z', source: 'sensor_fusion', entity_id: 'entity_001', changes: { confidence: 0.95, altitude: 8200 }, confidence: 0.95 },
  { event_id: 'evt_i9d0e1f2g3h4', type: 'SENSOR_READING', timestamp: '2024-01-15T12:42:45Z', source: 'radar-01', entity_id: 'entity_003', confidence: 0.99, severity: 'debug' },
  { event_id: 'evt_j0e1f2g3h4i5', type: 'SYSTEM_HEALTH', timestamp: '2024-01-15T12:43:00Z', source: 'system_monitor', confidence: 1.0, metadata: { cpu: 0.34, memory: 0.61, uptime_hours: 14.5 }, severity: 'debug' },
  { event_id: 'evt_k1f2g3h4i5j6', type: 'PLAN_GENERATED', timestamp: '2024-01-15T12:43:15Z', source: 'planning_layer', confidence: 0.91, metadata: { plan: 'Multi-sensor correlation sweep', steps: 4 } },
  { event_id: 'evt_l2g3h4i5j6k7', type: 'HUMAN_APPROVAL', timestamp: '2024-01-15T12:43:30Z', source: 'operator_console', entity_id: 'entity_002', confidence: 1.0, metadata: { approved_by: 'operator_1', action: 'Increase surveillance' } },
];

// ─── Store ──────────────────────────────────────────────────────────────────

interface WorldState {
  entities: Entity[];
  events: UltroneEvent[];
  selectedEntity: Entity | null;
  entityFilter: {
    search: string;
    types: string[];
    statuses: string[];
    minConfidence: number;
  };

  // Entity actions
  setEntities: (entities: Entity[]) => void;
  addEntity: (entity: Entity) => void;
  updateEntity: (id: string, changes: Partial<Entity>) => void;
  removeEntity: (id: string) => void;
  selectEntity: (entity: Entity | null) => void;

  // Event actions
  addEvent: (event: UltroneEvent) => void;
  clearEvents: () => void;

  // Filter actions
  setEntityFilter: (filter: Partial<WorldState['entityFilter']>) => void;

  // Derived
  filteredEntities: () => Entity[];
}

export const useWorldStore = create<WorldState>((set, get) => ({
  entities: DEMO_ENTITIES,
  events: DEMO_EVENTS,
  selectedEntity: null,
  entityFilter: {
    search: '',
    types: [],
    statuses: [],
    minConfidence: 0,
  },

  setEntities: (entities) => set({ entities }),

  addEntity: (entity) =>
    set((s) => ({ entities: [...s.entities, entity] })),

  updateEntity: (id, changes) =>
    set((s) => ({
      entities: s.entities.map((e) =>
        e.entity_id === id ? { ...e, ...changes, updated_at: new Date().toISOString() } : e,
      ),
      selectedEntity:
        s.selectedEntity?.entity_id === id
          ? { ...s.selectedEntity, ...changes }
          : s.selectedEntity,
    })),

  removeEntity: (id) =>
    set((s) => ({
      entities: s.entities.filter((e) => e.entity_id !== id),
      selectedEntity: s.selectedEntity?.entity_id === id ? null : s.selectedEntity,
    })),

  selectEntity: (entity) => set({ selectedEntity: entity }),

  addEvent: (event) =>
    set((s) => ({ events: [event, ...s.events].slice(0, 500) })),

  clearEvents: () => set({ events: [] }),

  setEntityFilter: (filter) =>
    set((s) => ({ entityFilter: { ...s.entityFilter, ...filter } })),

  filteredEntities: () => {
    const state = get();
    const { search, types, statuses, minConfidence } = state.entityFilter;
    let result = state.entities;

    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (e) =>
          e.entity_id.toLowerCase().includes(q) ||
          e.type.toLowerCase().includes(q) ||
          e.status.toLowerCase().includes(q),
      );
    }
    if (types.length > 0) {
      result = result.filter((e) => types.includes(e.type));
    }
    if (statuses.length > 0) {
      result = result.filter((e) => statuses.includes(e.status));
    }
    if (minConfidence > 0) {
      result = result.filter((e) => e.confidence >= minConfidence);
    }

    return result;
  },
}));

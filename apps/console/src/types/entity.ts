/**
 * ULTRONE Canonical Entity Types
 *
 * These types mirror the Python-side canonical entity definitions
 * in packages/core/entities/ and packages/core/world_model/.
 *
 * Design: entity-as-components (Lattice-style)
 * - Entity is composed of state components, not a rigid class hierarchy
 * - Every entity has a stable entity_id and type
 * - Every component value carries confidence and provenance
 */

// ─── Entity Status ──────────────────────────────────────────────────────────

export type EntityStatus =
  | 'active'
  | 'inactive'
  | 'unknown'
  | 'destroyed'
  | 'pending'
  | 'degraded'
  | 'engaged';

// ─── Geometry ───────────────────────────────────────────────────────────────

export interface Position {
  lat: number;
  lng: number;
  alt?: number;
}

export interface Velocity {
  x: number;
  y: number;
  z: number;
}

// ─── Provenance ─────────────────────────────────────────────────────────────

export interface Provenance {
  source: string;           // e.g. "sensor:radar-3", "agent:recon-1"
  transformation: string;   // e.g. "sensor_fusion", "trajectory_predictor"
  model: string;            // e.g. "gru-trajectory-v2"
  observed_at: number;      // unix timestamp
  note?: string;
}

/**
 * Full provenance chain for traceable decisions.
 *
 * Every important output has:
 * Observation → Source → Transformation → Model → Reasoning →
 * Decision → Confidence → Human approval/rejection → Outcome
 */
export interface ProvenanceChain {
  observation: string;
  source: string;
  transformation: string;
  model: string;
  reasoning: string;
  decision: string;
  confidence: number;
  human_action?: 'approved' | 'rejected' | 'pending' | 'overridden';
  outcome?: string;
  alternatives?: string[];
  timestamp: string;
}

// ─── Observation ────────────────────────────────────────────────────────────

export interface Observation {
  timestamp: string;
  source: string;
  description: string;
  confidence: number;
  raw_data?: Record<string, unknown>;
}

// ─── Relationships ──────────────────────────────────────────────────────────

export type RelationType =
  | 'observes'
  | 'commands'
  | 'located_in'
  | 'related_to'
  | 'part_of'
  | 'supplies'
  | 'threatens'
  | 'supports'
  | 'communicates_with'
  | 'tracks';

export interface Relationship {
  target_id: string;
  relation: RelationType;
  confidence: number;
  metadata?: Record<string, unknown>;
}

// ─── Component (Lattice-style composable state) ─────────────────────────────

export interface Component {
  value: unknown;
  confidence: number;
  provenance: Provenance[];
}

// ─── Entity ─────────────────────────────────────────────────────────────────

export interface Entity {
  entity_id: string;
  type: string;
  status: EntityStatus;
  position?: Position;
  velocity?: Velocity;
  sensors: string[];
  observations: Observation[];
  confidence: number;
  provenance: string[];
  relationships: Relationship[];
  metadata?: Record<string, unknown>;
  components?: Record<string, Component>;
  created_at?: string;
  updated_at?: string;
}

// ─── Entity Type Categories ─────────────────────────────────────────────────

export type EntityCategory =
  | 'air_asset'
  | 'ground_vehicle'
  | 'maritime_vessel'
  | 'sensor'
  | 'region'
  | 'agent'
  | 'infrastructure'
  | 'communication_node'
  | 'unknown';

export const ENTITY_CATEGORY_COLORS: Record<EntityCategory, string> = {
  air_asset: '#60a5fa',       // blue
  ground_vehicle: '#34d399',  // green
  maritime_vessel: '#818cf8', // indigo
  sensor: '#fbbf24',         // amber
  region: '#a78bfa',         // violet
  agent: '#f472b6',          // pink
  infrastructure: '#94a3b8', // slate
  communication_node: '#22d3ee', // cyan
  unknown: '#64748b',        // gray
};

export const ENTITY_STATUS_COLORS: Record<EntityStatus, string> = {
  active: '#34d399',
  inactive: '#94a3b8',
  unknown: '#fbbf24',
  destroyed: '#f87171',
  pending: '#60a5fa',
  degraded: '#f59e0b',
  engaged: '#a855f7',
};

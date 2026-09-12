/**
 * ULTRONE Canonical Event Types
 *
 * All components communicate through a unified event bus.
 * Every event has:
 * - Type (what happened)
 * - Timestamp (when)
 * - Source (who/what generated it)
 * - Entity reference (optional)
 * - Payload (event-specific data)
 * - Confidence (how certain)
 * - Provenance (decision chain)
 *
 * The UI receives these events via WebSocket stream.
 */

// ─── Event Types ────────────────────────────────────────────────────────────

export const EventType = {
  ENTITY_CREATED: 'ENTITY_CREATED',
  ENTITY_UPDATED: 'ENTITY_UPDATED',
  ENTITY_DESTROYED: 'ENTITY_DESTROYED',
  OBSERVATION_ADDED: 'OBSERVATION_ADDED',
  SENSOR_READING: 'SENSOR_READING',
  DECISION_MADE: 'DECISION_MADE',
  PLAN_GENERATED: 'PLAN_GENERATED',
  ACTION_EXECUTED: 'ACTION_EXECUTED',
  SIMULATION_TICK: 'SIMULATION_TICK',
  SIMULATION_STARTED: 'SIMULATION_STARTED',
  SIMULATION_STOPPED: 'SIMULATION_STOPPED',
  REASONING_COMPLETE: 'REASONING_COMPLETE',
  ANOMALY_DETECTED: 'ANOMALY_DETECTED',
  CONFIDENCE_CHANGED: 'CONFIDENCE_CHANGED',
  HUMAN_APPROVAL: 'HUMAN_APPROVAL',
  HUMAN_REJECTION: 'HUMAN_REJECTION',
  HUMAN_OVERRIDE: 'HUMAN_OVERRIDE',
  SYSTEM_HEALTH: 'SYSTEM_HEALTH',
  SYSTEM_ERROR: 'SYSTEM_ERROR',
} as const;

export type EventType = (typeof EventType)[keyof typeof EventType];

// ─── Severity Levels ────────────────────────────────────────────────────────

export type EventSeverity = 'info' | 'warning' | 'critical' | 'debug';

// ─── Event ──────────────────────────────────────────────────────────────────

export interface UltroneEvent {
  event_id: string;
  type: EventType;
  timestamp: string;
  source: string;
  entity_id?: string;
  changes?: Record<string, unknown>;
  confidence?: number;
  provenance?: string[];
  metadata?: Record<string, unknown>;
  severity?: EventSeverity;
}

// ─── Event Category Mapping ─────────────────────────────────────────────────

export const EVENT_CATEGORY_MAP: Record<EventType, {
  category: string;
  color: string;
  icon: string;
  severity: EventSeverity;
}> = {
  ENTITY_CREATED: { category: 'Entity', color: '#34d399', icon: '◈', severity: 'info' },
  ENTITY_UPDATED: { category: 'Entity', color: '#60a5fa', icon: '◈', severity: 'info' },
  ENTITY_DESTROYED: { category: 'Entity', color: '#f87171', icon: '◈', severity: 'warning' },
  OBSERVATION_ADDED: { category: 'Observation', color: '#fbbf24', icon: '◉', severity: 'info' },
  SENSOR_READING: { category: 'Observation', color: '#fbbf24', icon: '◉', severity: 'debug' },
  DECISION_MADE: { category: 'Decision', color: '#a78bfa', icon: '⬡', severity: 'info' },
  PLAN_GENERATED: { category: 'Decision', color: '#a78bfa', icon: '⬡', severity: 'info' },
  ACTION_EXECUTED: { category: 'Decision', color: '#818cf8', icon: '⬡', severity: 'info' },
  SIMULATION_TICK: { category: 'Simulation', color: '#22d3ee', icon: '◎', severity: 'debug' },
  SIMULATION_STARTED: { category: 'Simulation', color: '#22d3ee', icon: '◎', severity: 'info' },
  SIMULATION_STOPPED: { category: 'Simulation', color: '#22d3ee', icon: '◎', severity: 'info' },
  REASONING_COMPLETE: { category: 'Cognitive', color: '#f472b6', icon: '◆', severity: 'info' },
  ANOMALY_DETECTED: { category: 'Cognitive', color: '#f87171', icon: '◆', severity: 'critical' },
  CONFIDENCE_CHANGED: { category: 'Cognitive', color: '#fbbf24', icon: '◆', severity: 'info' },
  HUMAN_APPROVAL: { category: 'HITL', color: '#34d399', icon: '◇', severity: 'info' },
  HUMAN_REJECTION: { category: 'HITL', color: '#f87171', icon: '◇', severity: 'warning' },
  HUMAN_OVERRIDE: { category: 'HITL', color: '#fbbf24', icon: '◇', severity: 'warning' },
  SYSTEM_HEALTH: { category: 'System', color: '#94a3b8', icon: '●', severity: 'debug' },
  SYSTEM_ERROR: { category: 'System', color: '#f87171', icon: '●', severity: 'critical' },
};

export type EventCategory =
  | 'Entity'
  | 'Observation'
  | 'Decision'
  | 'Simulation'
  | 'Cognitive'
  | 'HITL'
  | 'System';

export const EVENT_TYPE_META = EVENT_CATEGORY_MAP;

// Copyright (c) Ultrone Contributors. All rights reserved.
/**
 * Strongly-typed domain models matching the ULTRONE Cockpit backend contracts.
 */

export interface SystemTruth {
  environment: string;
  simulation_only: boolean;
  run_id: string;
  ground_truth: string;
  agent_observation: string;
  belief_taint: string;
  policy_version: string;
  model_version: string;
  dataset_version: string;
  latest_checkpoint: string;
  event_chain: string;
  event_count: number;
  mcp_protocol: string;
  udis: string;
  udis_devices: number;
  physical_actuation: string;
  safety: string;
  emergency_state: string;
  freshness_horizon_ms: number;
  notes: string[];
}

export interface CockpitRunSummary {
  run_id: string;
  scenario_id: string;
  scenario_name: string;
  environment: string;
  simulation_only: boolean;
  tick: number;
  simulation_time_s: number;
  playing: boolean;
  speed: number;
  health_percent: number;
}

export interface AlertItem {
  alert_id: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  title: string;
  component: string;
  impact: string;
  evidence: string;
  recommended_investigation: string;
  status: string;
  tick: number;
  timestamp: number;
  [key: string]: any;
}

export interface CockpitOverview {
  run: CockpitRunSummary;
  realtime: {
    stage: string;
    latest_decision: any;
    current_operation: string | null;
  };
  world: {
    entities: number;
    belief_freshness_ok: number;
    mean_error_km: number;
    mean_confidence: number;
    worst_divergence: { entity_id: string; error_km: number } | null;
  };
  devices: {
    total: number;
    ready: number;
    busy: number;
    degraded: number;
    fault: number;
    offline: number;
    emergency_stop: number;
  };
  policy: {
    version: string;
    blocked: number;
    checks_run: number;
    failed_checks: number;
    safety_status: string;
  };
  agents: {
    total: number;
    active: number;
  };
  events: {
    total: number;
    by_type: Record<string, number>;
    chain_valid: boolean;
  };
  improvement: {
    status: string;
    note: string;
  };
  alerts: AlertItem[];
  alert_counts: Record<string, number>;
  truth: SystemTruth;
}

export interface GroundTruthEntity {
  entity_id: string;
  label: string;
  domain: string;
  kind: 'friendly' | 'hostile' | 'unknown' | 'neutral';
  position: [number, number];
  heading_deg: number;
  speed_kmh: number;
  pattern: string;
  orbit_radius_km: number;
}

export interface BeliefEntity {
  entity_id: string;
  label: string;
  position: [number, number];
  uncertainty_km: number;
  confidence: number;
  ground_truth_error_km: number | null;
  age_ms: number;
  freshness_ok: boolean;
  supporting_observations: string[];
  contributing_sensors: string[];
  disagreement_km: number;
  provenance: Record<string, any>;
}

export interface WorldComparisonItem {
  entity_id: string;
  label: string;
  kind: string;
  ground_truth: [number, number];
  belief: [number, number] | null;
  error_km: number | null;
  uncertainty_km: number | null;
  confidence: number | null;
  age_ms: number | null;
  freshness_ok: boolean | null;
  disagreement_km: number | null;
  confidence_provenance: Record<string, any>;
}

export interface SensorSpec {
  sensor_id: string;
  device_id: string;
  label: string;
  modality: string;
  range_km: number;
  fov_deg: number;
  measurement_noise_sigma: number;
  rate_hz: number;
  latency_ticks: number;
}

export interface WorldSnapshot {
  tick: number;
  scenario_id: string;
  environment: string;
  simulation_only: boolean;
  bounds_km: [number, number, number, number];
  model_version: string;
  policy_version: string;
  freshness_horizon_ms: number;
  ground_truth: GroundTruthEntity[];
  belief: BeliefEntity[];
  comparison: WorldComparisonItem[];
  sensors: SensorSpec[];
  observations: any[];
  stats: Record<string, any>;
}

export interface AgentRecord {
  agent_id: string;
  name: string;
  role: string;
  model_version: string;
  capabilities: string[];
  publishes: string[];
  subscribes: string[];
  state: 'ACTIVE' | 'IDLE' | 'PAUSED';
  confidence: number;
  tasks_completed: number;
  latency_ms: number;
  errors: number;
  recent_decisions: string[];
  notes: string;
}

export interface AgentEdge {
  edge_id: string;
  from: string;
  to: string;
  message_type: string;
  message_count: number;
  schema: string;
  latency_ms: number;
  size_bytes: number;
}

export interface AgentCatalog {
  agents: AgentRecord[];
  graph: {
    nodes: string[];
    edges: AgentEdge[];
  };
}

export interface DeviceRecord {
  device_id: string;
  device_type: string;
  manufacturer: string;
  model: string;
  firmware: string;
  mode: string;
  state: string;
  is_operational: boolean;
  simulation_only: boolean;
  health: number;
  health_score: number;
  telemetry_channels: string[];
  fresh_channels: string[];
  stale_channels: string[];
  capabilities: string[];
  procedures: string[];
  lease_required: string[];
  read_only: string[];
  signature: {
    signed: boolean;
    valid: boolean;
    detail: string | null;
    scheme: string;
    author_identity: string;
    public_key_hex: string;
  };
  last_transition: {
    from_state: string;
    to_state: string;
    timestamp: number;
    reason: string;
  } | null;
  transition_count: number;
}

export interface DeviceCatalog {
  devices: DeviceRecord[];
  summary: Record<string, number>;
}

export interface DeviceDetail extends DeviceRecord {
  manifest: any;
  telemetry: Record<string, any>;
  telemetry_history: Record<string, any[]>;
  telemetry_series: any[];
  fsm: {
    current_state: string;
    allowed_transitions: string[];
    transitions: Array<{
      from_state: string;
      to_state: string;
      timestamp: number;
      reason: string;
      authorized_by: string;
    }>;
  };
  leases: any[];
  admissible_actions: any[];
}

export interface McpTrafficEntry {
  timestamp: number;
  kind: 'REQUEST' | 'RESPONSE' | 'ERROR';
  method: string;
  correlation_id: string;
  protocol_version: string;
  server: string;
  tool: string | null;
  uri: string | null;
  latency_ms: number;
  payload: any;
  status: 'ok' | 'error';
  error_code: number | null;
}

export interface StoredEvent {
  event_id: number;
  event_type: string;
  tick: number;
  stream_id: string;
  timestamp: number;
  payload: any;
  hash: string;
  prev_hash: string;
}

export interface EventStoreStatus {
  event_count: number;
  chain_valid: boolean;
  chain_detail: string | null;
  latest_checkpoint: any;
  checkpoint_valid: boolean;
}

export interface DecisionTrace {
  decision_id: string;
  tick: number;
  entity_id: string;
  confidence: number;
  latency_ms: number;
  approved: boolean;
  blocked_reason: string | null;
  observations: any[];
  belief: any;
  plan: any;
  policy_checks: Array<{
    policy_id: string;
    passed: boolean;
    reason: string;
    severity: string;
  }>;
  action: any;
  outcome: any;
  memory_refs: string[];
}

export interface WhyBlockedResult {
  decision_id: string;
  entity_id: string;
  tick: number;
  intent: string;
  overall_outcome: 'REJECTED';
  primary_block: {
    policy_id: string;
    severity: string;
    reason: string;
  };
  gates: Array<{
    name: string;
    policy_id: string;
    passed: boolean;
    reason: string;
    severity: string;
  }>;
  required_remediation: string;
}

export interface PairedMetricStatistics {
  metric: string;
  n_samples: number;
  delta_mean: number;
  delta_median: number;
  ci_lower: number;
  ci_upper: number;
  cohens_d: number;
  p_value: number;
  is_significant: boolean;
  candidate_improved: boolean;
  regression: boolean;
  lower_is_better: boolean;
}

export interface EvaluationBenchmarkResult {
  benchmark_id: string;
  baseline: {
    label: string;
    model_version: string;
    runs: any[];
  };
  candidate: {
    label: string;
    model_version: string;
    runs: any[];
  };
  environment: Record<string, any>;
  metrics: Record<string, PairedMetricStatistics>;
  regressions: string[];
  improvements: string[];
  promotion: 'ELIGIBLE' | 'BLOCKED' | 'INCONCLUSIVE';
}

export interface GovernanceCapability {
  name: string;
  level: number;
  highest_proven: number;
  target_level: number;
  status: string;
  description: string;
  unit_tests: boolean;
  integration_tests: boolean;
  benchmarked: boolean;
  evidence: string;
  next_milestone: string;
}

export interface GovernanceStatus {
  capabilities: GovernanceCapability[];
  levels: Record<string, string>;
  highest: number;
  lowest: number;
}

export interface SearchResultItem {
  category: string;
  id: string;
  title: string;
  subtitle: string;
  badge: string;
  route: string;
}

// Copyright (c) Ultrone Contributors. All rights reserved.
/**
 * Deterministic backend mock for cockpit E2E tests (brief items #48 / #69).
 * Implements the /api/cockpit REST contract served by
 * apps/api/routers/cockpit.py so the UI is testable without the Python
 * runtime, and exposes fault switches so tests can drive degraded states.
 */
import type { Plugin } from 'vite';
import type { IncomingMessage, ServerResponse } from 'http';

export type Scenario = 'standard_patrol' | 'stale_device' | 'causal_violation' | 'divergence';

const runtime = {
  scenario: 'standard_patrol' as Scenario,
  playing: false,
  tick: 42,
  speed: 1.0,
  uiActions: [] as any[],
  t0: Date.UTC(2026, 6, 28, 14, 32, 0) / 1000,
};

const now = () => runtime.t0 + runtime.tick * 0.5;

const TRUTH = {
  environment: 'simulation',
  simulation_only: true,
  run_id: 'RUN-004281',
  ground_truth: 'AVAILABLE TO EVALUATOR ONLY',
  agent_observation: 'RESTRICTED',
  belief_taint: 'none',
  policy_version: 'policy:v12',
  model_version: 'vision-v3',
  dataset_version: 'scouting-fusion:v4',
  latest_checkpoint: 'VALID',
  event_chain: 'VALID',
  event_count: 18421,
  mcp_protocol: '2026-07-28',
  udis: 'ACTIVE',
  udis_devices: 3,
  physical_actuation: 'DISABLED',
  safety: 'NORMAL',
  emergency_state: 'CLEAR',
  freshness_horizon_ms: 250,
  notes: ['Deterministic seed 12345', 'Ephemeral event store'],
};

const DEVICES = [
  {
    device_id: 'device-01',
    device_type: 'radar',
    manufacturer: 'Ultrone Labs',
    model: 'RDR-X1',
    firmware: '2.4.1',
    mode: 'simulation',
    state: 'READY',
    is_operational: true,
    simulation_only: true,
    health: 98,
    health_score: 0.98,
    telemetry_channels: ['position', 'state', 'health'],
    fresh_channels: ['position', 'state', 'health'],
    stale_channels: [],
    capabilities: ['observe.state', 'observe.telemetry', 'simulation-control'],
    procedures: ['calibration', 'diagnostic'],
    lease_required: ['simulation-control'],
    read_only: ['observe.state', 'observe.telemetry'],
    signature: { signed: true, valid: true, detail: null, scheme: 'ed25519', author_identity: 'ultrone-authority', public_key_hex: 'ab' },
    last_transition: { from_state: 'DISCOVERING', to_state: 'READY', timestamp: now(), reason: 'discovery complete' },
    transition_count: 1,
  },
  {
    device_id: 'device-04',
    device_type: 'camera',
    manufacturer: 'Ultrone Labs',
    model: 'CAM-S2',
    firmware: '1.9.0',
    mode: 'simulation',
    state: 'DEGRADED',
    is_operational: true,
    simulation_only: true,
    health: 61,
    health_score: 0.61,
    telemetry_channels: ['position', 'state', 'health'],
    fresh_channels: ['state'],
    stale_channels: ['position'],
    capabilities: ['observe.state', 'observe.telemetry'],
    procedures: ['diagnostic'],
    lease_required: [],
    read_only: ['observe.state', 'observe.telemetry'],
    signature: { signed: true, valid: true, detail: null, scheme: 'ed25519', author_identity: 'ultrone-authority', public_key_hex: 'cd' },
    last_transition: { from_state: 'READY', to_state: 'DEGRADED', timestamp: now(), reason: 'telemetry stale' },
    transition_count: 2,
  },
  {
    device_id: 'device-17',
    device_type: 'digital_twin',
    manufacturer: 'Ultrone Labs',
    model: 'TWIN-A0',
    firmware: '0.8.3',
    mode: 'simulation',
    state: 'BUSY',
    is_operational: true,
    simulation_only: true,
    health: 100,
    health_score: 1.0,
    telemetry_channels: ['state', 'health'],
    fresh_channels: ['state', 'health'],
    stale_channels: [],
    capabilities: ['observe.state', 'simulate.execute'],
    procedures: ['test-sequence'],
    lease_required: ['simulate.execute'],
    read_only: ['observe.state'],
    signature: { signed: true, valid: true, detail: null, scheme: 'ed25519', author_identity: 'ultrone-authority', public_key_hex: 'ef' },
    last_transition: { from_state: 'READY', to_state: 'BUSY', timestamp: now(), reason: 'procedure execution started' },
    transition_count: 3,
  },
];

const deviceDetail = (d: any) => ({
  ...d,
  manifest: { device_type: d.device_type, capabilities: d.capabilities, procedures: d.procedures },
  telemetry: { position: [12.4, -3.2], state: d.state, health: d.health },
  telemetry_history: { position: [[12.1, -3.0], [12.4, -3.2]], state: ['READY', d.state], health: [99, d.health] },
  telemetry_series: [{ t: now(), position: [12.4, -3.2], health: d.health }],
  fsm: {
    current_state: d.state,
    allowed_transitions: d.state === 'READY' ? ['BUSY', 'DEGRADED', 'MAINTENANCE'] : ['READY'],
    transitions: [d.last_transition],
  },
  leases: [],
  admissible_actions: [],
});

const AGENTS = [
  { agent_id: 'agent-01', name: 'Planner', role: 'Planner', model_version: 'planner-v3.1', capabilities: ['plan.generate'], publishes: ['plan'], subscribes: ['belief'], state: 'ACTIVE', confidence: 0.87, tasks_completed: 12, latency_ms: 21, errors: 0, recent_decisions: ['DEC-281'], notes: '' },
  { agent_id: 'agent-02', name: 'Perception', role: 'Perception', model_version: 'vision-v3', capabilities: ['observe.state'], publishes: ['observation'], subscribes: ['telemetry'], state: 'ACTIVE', confidence: 0.91, tasks_completed: 88, latency_ms: 8, errors: 1, recent_decisions: [], notes: '' },
  { agent_id: 'agent-03', name: 'Evaluator', role: 'Evaluator', model_version: 'eval-v2.0', capabilities: ['evaluate'], publishes: ['outcome'], subscribes: ['action'], state: 'ACTIVE', confidence: 0.94, tasks_completed: 40, latency_ms: 12, errors: 0, recent_decisions: [], notes: '' },
];

const comparison = (stale: boolean) => [
  {
    entity_id: 'OBJ-A',
    label: 'Object Alpha',
    kind: 'hostile',
    ground_truth: [12.4, -3.2],
    belief: [12.9, -3.8],
    error_km: stale ? 1.42 : 0.79,
    uncertainty_km: 0.6,
    confidence: stale ? 0.61 : 0.82,
    age_ms: stale ? 812 : 118,
    freshness_ok: !stale,
    disagreement_km: 0.4,
    confidence_provenance: { observation: 'OBS-182', model: 'vision-v3', calibration: 'cal-v8', freshness_ms: stale ? 812 : 118 },
  },
  {
    entity_id: 'OBJ-B',
    label: 'Object Bravo',
    kind: 'friendly',
    ground_truth: [-4.1, 7.7],
    belief: [-4.1, 7.7],
    error_km: 0.02,
    uncertainty_km: 0.1,
    confidence: 0.95,
    age_ms: 90,
    freshness_ok: true,
    disagreement_km: 0.0,
    confidence_provenance: { observation: 'OBS-183', model: 'vision-v3', calibration: 'cal-v8', freshness_ms: 90 },
  },
];

const TRACES = () => {
  const blocked = runtime.scenario === 'causal_violation';
  return [
    {
      decision_id: 'DEC-281',
      tick: runtime.tick,
      entity_id: 'OBJ-A',
      confidence: 0.82,
      latency_ms: 31,
      approved: !blocked,
      blocked_reason: blocked ? 'Post-action field detected: actual_outcome' : null,
      observations: [{ observation_id: 'OBS-182', sensor_id: 'sensor-04', age_ms: 118 }],
      belief: { belief_id: 'belief-state-811', confidence: 0.82 },
      plan: { plan_id: 'PLAN-441', metadata: blocked ? { actual_outcome: 'leaked' } : {} },
      policy_checks: [
        { policy_id: 'SAF-001', passed: !blocked, reason: blocked ? 'Causal boundary violation in plan.metadata' : 'ok', severity: 'CRITICAL' },
        { policy_id: 'SAF-003', passed: true, reason: 'ok', severity: 'HIGH' },
        { policy_id: 'SAF-004', passed: true, reason: 'ok', severity: 'MEDIUM' },
      ],
      action: { action_id: 'action-331', intent: 'simulate.intercept' },
      outcome: null,
      memory_refs: ['memory-102', 'memory-109'],
    },
  ];
};

const alerts = () => {
  const list: any[] = [];
  if (runtime.scenario === 'stale_device') {
    list.push({
      alert_id: 'ALRT-0001',
      severity: 'HIGH',
      title: 'Stale telemetry detected',
      component: 'device-04',
      impact: 'decision blocked for affected sensors',
      evidence: 'channel position age 812 ms > horizon 250 ms',
      recommended_investigation: 'Check simulated sensor cadence for device-04.',
      status: 'open',
      tick: runtime.tick,
      timestamp: now(),
      device_id: 'device-04',
    });
  }
  if (runtime.scenario === 'causal_violation') {
    list.push({
      alert_id: 'ALRT-0002',
      severity: 'CRITICAL',
      title: 'Causal boundary violation',
      component: 'Event Store',
      impact: 'decision blocked',
      evidence: 'post-action field actual_outcome in DEC-281 plan.metadata',
      recommended_investigation: 'Inspect decision DEC-281 trace and causal validator output.',
      status: 'open',
      tick: runtime.tick,
      timestamp: now(),
      decision_id: 'DEC-281',
    });
  }
  return list;
};

const json = (res: ServerResponse, body: unknown, status = 200) => {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json');
  res.end(JSON.stringify(body));
};

const readBody = (req: IncomingMessage): Promise<any> =>
  new Promise((resolve) => {
    let raw = '';
    req.on('data', (c) => (raw += c));
    req.on('end', () => {
      try {
        resolve(raw ? JSON.parse(raw) : {});
      } catch {
        resolve({});
      }
    });
  });

export function mockBackendPlugin(): Plugin {
  return {
    name: 'ultrone-mock-backend',
    configureServer(server: any) {
      server.middlewares.use(
        '/api/cockpit',
        (req: IncomingMessage, res: ServerResponse, next: any) => {
          void handle(req, res, next);
        }
      );
    },
  };
}

async function handle(
  req: IncomingMessage,
  res: ServerResponse,
  _next: unknown
): Promise<void> {
  const rawUrl = (req.url ?? '').split('?')[0];
  const url = rawUrl.startsWith('/api/cockpit') ? rawUrl.slice('/api/cockpit'.length) : rawUrl;
  const method = (req.method ?? 'GET').toUpperCase();

  if (url.startsWith('/__test__/scenario')) {
    const body = await readBody(req);
    runtime.scenario = body.scenario || body.scenario_id || 'standard_patrol';
    return json(res, { ok: true, scenario: runtime.scenario });
  }

  if (method !== 'GET' && method !== 'POST') return;

  const route = `${method} ${url}`;
  const post = () => readBody(req);

  try {
    switch (route) {
      case 'GET /overview':
        return json(res, {
          run: {
            run_id: 'RUN-004281',
            scenario_id: runtime.scenario,
            scenario_name: 'Standard Patrol',
            environment: 'simulation',
            simulation_only: true,
            tick: runtime.tick,
            simulation_time_s: runtime.tick * 0.5,
            playing: runtime.playing,
            speed: runtime.speed,
            health_percent: runtime.scenario === 'stale_device' ? 97.4 : 99.97,
          },
          realtime: {
            stage: 'POLICY EVALUATION',
            latest_decision: TRACES()[0],
            current_operation: 'Maintain Sensor Coverage',
          },
          world: {
            entities: 2,
            belief_freshness_ok: runtime.scenario === 'stale_device' ? 1 : 2,
            mean_error_km: runtime.scenario === 'stale_device' ? 0.72 : 0.41,
            mean_confidence: 0.885,
            worst_divergence: { entity_id: 'OBJ-A', error_km: runtime.scenario === 'stale_device' ? 1.42 : 0.79 },
          },
          devices: { total: 3, ready: 1, busy: 1, degraded: 1, fault: 0, offline: 0, emergency_stop: 0 },
          policy: {
            version: 'policy:v12',
            blocked: runtime.scenario === 'causal_violation' ? 1 : 0,
            checks_run: 7,
            failed_checks: runtime.scenario === 'causal_violation' ? 1 : 0,
            safety_status: runtime.scenario === 'causal_violation' ? 'RESTRICTED' : 'NORMAL',
          },
          agents: { total: 3, active: 3 },
          events: {
            total: 18421,
            by_type: { ObservationReceived: 4210, BeliefUpdated: 4210, PlanGenerated: 2210, PolicyChecked: 2210, ActionProposed: 1800 },
            chain_valid: true,
          },
          improvement: { status: 'MONITORING', note: 'no candidate under evaluation' },
          alerts: alerts(),
          alert_counts: alerts().reduce(
            (acc: Record<string, number>, a) => ((acc[a.severity] = (acc[a.severity] ?? 0) + 1), acc),
            {}
          ),
          truth: TRUTH,
        });

      case 'GET /truth':
        return json(res, TRUTH);

      case 'GET /health':
        return json(res, {
          run_id: 'RUN-004281',
          uptime_s: runtime.tick * 0.5,
          tick: runtime.tick,
          tick_rate_hz: 2.0,
          step_ms: 12.4,
          services: [
            { name: 'Orchestrator', status: 'ok' },
            { name: 'MCP Gateway', status: 'ok' },
            { name: 'UDIS Registry', status: 'ok' },
            { name: 'Event Store', status: 'ok' },
            { name: 'Evaluator', status: 'ok' },
            { name: 'Memory', status: 'ok' },
            { name: 'Simulator', status: 'ok' },
            { name: 'Model Runtime', status: runtime.scenario === 'stale_device' ? 'degraded' : 'ok' },
            { name: 'Cockpit API', status: 'ok' },
          ],
          degraded_services: runtime.scenario === 'stale_device' ? ['Model Runtime'] : [],
          event_rate_per_tick: 3.7,
          event_bus_ms: 3.0,
          api_ms: 4.1,
          mcp_ms: 11.2,
          queue_depth: 42,
          event_store: {
            event_count: 18421,
            chain_valid: true,
            chain_detail: null,
            latest_checkpoint: { checkpoint_id: 'CP-019', valid: true },
            checkpoint_valid: true,
          },
          devices: { ready: 1, busy: 1, degraded: 1 },
          failed_gates: runtime.scenario === 'causal_violation' ? 1 : 0,
          resources: {
            note: 'host resource sampling belongs to the deployment, not to this service',
            cpu_percent: null,
            ram_percent: null,
            gpu_percent: null,
            vram_percent: null,
          },
        });

      case 'GET /alerts':
        return json(res, alerts());

      case 'GET /world': {
        const stale = runtime.scenario === 'stale_device';
        return json(res, {
          tick: runtime.tick,
          scenario_id: runtime.scenario,
          environment: 'simulation',
          simulation_only: true,
          bounds_km: [-20, -20, 20, 20],
          model_version: 'vision-v3',
          policy_version: 'policy:v12',
          freshness_horizon_ms: 250,
          ground_truth: [
            { entity_id: 'OBJ-A', label: 'Object Alpha', domain: 'air', kind: 'hostile', position: [12.4, -3.2], heading_deg: 90, speed_kmh: 420, pattern: 'transit', orbit_radius_km: 0 },
            { entity_id: 'OBJ-B', label: 'Object Bravo', domain: 'air', kind: 'friendly', position: [-4.1, 7.7], heading_deg: 45, speed_kmh: 380, pattern: 'orbit', orbit_radius_km: 5 },
          ],
          belief: [
            { entity_id: 'OBJ-A', label: 'Object Alpha', position: [12.9, -3.8], uncertainty_km: 0.6, confidence: 0.82, ground_truth_error_km: 0.79, age_ms: stale ? 812 : 118, freshness_ok: !stale, supporting_observations: ['OBS-182'], contributing_sensors: ['sensor-04'], disagreement_km: 0.4, provenance: {} },
            { entity_id: 'OBJ-B', label: 'Object Bravo', position: [-4.1, 7.7], uncertainty_km: 0.1, confidence: 0.95, ground_truth_error_km: 0.02, age_ms: 90, freshness_ok: true, supporting_observations: ['OBS-183'], contributing_sensors: ['sensor-01'], disagreement_km: 0.0, provenance: {} },
          ],
          comparison: comparison(stale),
          sensors: [
            { sensor_id: 'sensor-01', device_id: 'device-01', label: 'Radar A', modality: 'radar', range_km: 40, fov_deg: 120, measurement_noise_sigma: 0.2, rate_hz: 2, latency_ticks: 1 },
            { sensor_id: 'sensor-04', device_id: 'device-04', label: 'Camera B', modality: 'electro_optical', range_km: 15, fov_deg: 60, measurement_noise_sigma: 0.4, rate_hz: 1, latency_ticks: 2 },
          ],
          observations: [{ observation_id: 'OBS-182', sensor_id: 'sensor-04', tick: runtime.tick, entity_id: 'OBJ-A' }],
          stats: { step_ms: 12.4, observations_total: 882, active_faults: stale ? 1 : 0 },
        });
      }

      case 'GET /agents':
        return json(res, {
          agents: AGENTS,
          graph: {
            nodes: ['perception', 'world-model', 'planner', 'evaluator', 'policy', 'udis'],
            edges: [
              { edge_id: 'MSG-18281', from: 'perception', to: 'world-model', message_type: 'BeliefUpdate', message_count: 4210, schema: 'BeliefUpdate:v4', latency_ms: 12, size_bytes: 3277 },
              { edge_id: 'MSG-18282', from: 'world-model', to: 'planner', message_type: 'BeliefSnapshot', message_count: 2210, schema: 'Belief:v2', latency_ms: 4, size_bytes: 1024 },
              { edge_id: 'MSG-18283', from: 'world-model', to: 'evaluator', message_type: 'BeliefSnapshot', message_count: 2208, schema: 'Belief:v2', latency_ms: 5, size_bytes: 1024 },
              { edge_id: 'MSG-18284', from: 'planner', to: 'policy', message_type: 'PlanProposal', message_count: 1800, schema: 'Plan:v3', latency_ms: 7, size_bytes: 2048 },
              { edge_id: 'MSG-18285', from: 'policy', to: 'udis', message_type: 'AuthorizedAction', message_count: 1790, schema: 'Action:v2', latency_ms: 3, size_bytes: 512 },
            ],
          },
        });

      case 'GET /devices':
        return json(res, {
          devices: DEVICES,
          summary: { total: 3, ready: 1, busy: 1, degraded: 1, fault: 0, offline: 0, emergency_stop: 0, maintenance: 0, discovering: 0 },
        });

      case 'GET /mcp/traffic':
        return json(res, [
          { timestamp: now(), kind: 'REQUEST', method: 'tools/call', correlation_id: 'COR-001', protocol_version: '2026-07-28', server: 'ULTRONE UDIS Gateway', tool: 'devices_state', uri: null, latency_ms: 0, payload: { name: 'devices_state', arguments: { device_id: 'device-04' } }, status: 'ok', error_code: null },
          { timestamp: now(), kind: 'RESPONSE', method: 'tools/call', correlation_id: 'COR-001', protocol_version: '2026-07-28', server: 'ULTRONE UDIS Gateway', tool: 'devices_state', uri: null, latency_ms: 11, payload: { content: [{ type: 'text', text: 'device state = DEGRADED' }] }, status: 'ok', error_code: null },
          { timestamp: now(), kind: 'REQUEST', method: 'resources/read', correlation_id: 'COR-002', protocol_version: '2026-07-28', server: 'ULTRONE UDIS Gateway', tool: null, uri: 'udis://devices', latency_ms: 0, payload: {}, status: 'ok', error_code: null },
          { timestamp: now(), kind: 'RESPONSE', method: 'resources/read', correlation_id: 'COR-002', protocol_version: '2026-07-28', server: 'ULTRONE UDIS Gateway', tool: null, uri: 'udis://devices', latency_ms: 9, payload: { contents: [{ uri: 'udis://devices', text: '3 devices' }] }, status: 'ok', error_code: null },
        ]);

      case 'GET /mcp/discovery':
        return json(res, {
          protocol_version: '2026-07-28',
          server: { name: 'ULTRONE UDIS Gateway', version: '2.0.0' },
          capabilities: { tools: { listChanged: true }, resources: { subscribe: false, listChanged: true } },
          tools: [
            { name: 'devices_state', description: 'Read UDIS device state', inputSchema: { type: 'object', properties: { device_id: { type: 'string' } } } },
            { name: 'devices_list', description: 'List registered devices', inputSchema: { type: 'object', properties: {} } },
          ],
          resources: [{ uri: 'udis://devices', name: 'Device Registry', mimeType: 'application/json' }],
        });

      case 'GET /events':
        return json(
          res,
          [18421, 18420, 18419, 18418, 18417].map((i, idx) => ({
            event_id: i,
            event_type: ['ObservationReceived', 'BeliefUpdated', 'PlanGenerated', 'PolicyChecked', 'ActionProposed'][idx],
            tick: runtime.tick - idx,
            stream_id: 'trace-004281',
            timestamp: now() - idx * 0.5,
            payload: { seq: i },
            hash: `h${i}`,
            prev_hash: `h${i - 1}`,
          }))
        );

      case 'GET /events/store':
        return json(res, {
          event_count: 18421,
          chain_valid: true,
          chain_detail: null,
          latest_checkpoint: { checkpoint_id: 'CP-019', event_id: 18000, hash: 'h18000', signature: 'VALID' },
          checkpoint_valid: true,
        });

      case 'GET /traces':
        return json(res, TRACES());

      case 'GET /safety/status':
        return json(res, {
          status: runtime.scenario === 'causal_violation' ? 'RESTRICTED' : 'NORMAL',
          emergency_state: 'CLEAR',
          active_policies: 7,
          blocked_operations: runtime.scenario === 'causal_violation' ? 1 : 0,
          causal_violations: runtime.scenario === 'causal_violation' ? 1 : 0,
          leases: {
            active: 2,
            expired: 0,
            items: [{ lease_id: 'LEASE-882', agent_id: 'agent-01', scope: 'simulate.execute', status: 'ACTIVE', issued: now(), expires: now() + 300, rate_per_min: 10 }],
          },
          freshness: {
            horizon_ms: 250,
            audit: [
              { sensor_id: 'sensor-01', device_id: 'device-01', modality: 'radar', age_ms: 92, horizon_ms: 250, fresh: true },
              { sensor_id: 'sensor-04', device_id: 'device-04', modality: 'electro_optical', age_ms: runtime.scenario === 'stale_device' ? 812 : 118, horizon_ms: 250, fresh: runtime.scenario !== 'stale_device' },
            ],
          },
        });

      case 'GET /safety/invariants':
        return json(res, [
          { id: 'SAF-001', name: 'Causal Boundary', severity: 'CRITICAL', description: 'Post-action information must never contaminate decision inputs.', implementation: 'causal_validator.py', test: 'tests/test_causal.py' },
          { id: 'SAF-003', name: 'Telemetry Freshness', severity: 'HIGH', description: 'Decisions require fresher-than-horizon telemetry.', implementation: 'freshness.py', test: 'tests/test_freshness.py' },
        ]);

      case 'GET /safety/causal-boundary':
        return json(res, {
          enforced: true,
          forbidden_fields: ['actual_outcome', 'outcome', 'post_action'],
          checks_run: runtime.tick,
          violations: runtime.scenario === 'causal_violation'
            ? [{ decision_id: 'DEC-281', field: 'actual_outcome', location: 'decision_context.plan.metadata' }]
            : [],
        });

      case 'GET /safety/why-blocked/DEC-281':
        return json(res, {
          decision_id: 'DEC-281',
          entity_id: 'OBJ-A',
          tick: runtime.tick,
          intent: 'simulate.intercept',
          overall_outcome: 'REJECTED',
          primary_block: { policy_id: 'SAF-001', severity: 'CRITICAL', reason: 'Causal boundary violation: post-action field in plan metadata' },
          gates: [
            { name: 'confidence_provenance', policy_id: 'SAF-002', passed: false, reason: 'Confidence provenance missing', severity: 'HIGH' },
            { name: 'lease_valid', policy_id: 'SAF-004', passed: true, reason: 'LEASE-882 active', severity: 'MEDIUM' },
            { name: 'device_ready', policy_id: 'SAF-005', passed: true, reason: 'device-17 BUSY but admissible', severity: 'MEDIUM' },
            { name: 'telemetry_fresh', policy_id: 'SAF-003', passed: false, reason: 'Telemetry stale (812 ms > 250 ms)', severity: 'HIGH' },
            { name: 'procedure_valid', policy_id: 'SAF-006', passed: true, reason: 'ok', severity: 'LOW' },
          ],
          required_remediation: 'Refresh telemetry and attach calibration provenance before re-proposal.',
        });

      case 'GET /evaluation':
        return json(res, {
          benchmark_id: 'BENCH-0144',
          baseline: { label: 'baseline vision-v3.2', model_version: 'vision-v3.2', runs: [{ seed: 1, accuracy: 0.81 }, { seed: 2, accuracy: 0.8 }] },
          candidate: { label: 'candidate vision-v3.4', model_version: 'vision-v3.4', runs: [{ seed: 1, accuracy: 0.86 }, { seed: 2, accuracy: 0.85 }] },
          environment: { seeds: [1, 2, 3, 4, 5], ticks: 20, dataset: 'scouting-fusion:v4' },
          metrics: {
            accuracy: { metric: 'accuracy', n_samples: 5, delta_mean: 0.05, delta_median: 0.05, ci_lower: 0.031, ci_upper: 0.069, cohens_d: 1.4, p_value: 0.002, is_significant: true, candidate_improved: true, regression: false, lower_is_better: false },
            brier: { metric: 'brier', n_samples: 5, delta_mean: -0.06, delta_median: -0.06, ci_lower: -0.082, ci_upper: -0.038, cohens_d: -1.2, p_value: 0.004, is_significant: true, candidate_improved: true, regression: false, lower_is_better: true },
            latency_ms: { metric: 'latency_ms', n_samples: 5, delta_mean: 4.0, delta_median: 4.0, ci_lower: 1.1, ci_upper: 6.9, cohens_d: 0.8, p_value: 0.041, is_significant: true, candidate_improved: false, regression: true, lower_is_better: true },
          },
          regressions: ['latency_ms'],
          improvements: ['accuracy', 'brier'],
          promotion: 'BLOCKED',
        });

      case 'GET /governance':
        return json(res, {
          capabilities: [
            { name: 'Perception', level: 4, highest_proven: 4, target_level: 5, status: 'proven', description: 'Sensor fusion with provenance', unit_tests: true, integration_tests: true, benchmarked: true, evidence: 'unit+integration+benchmark', next_milestone: 'External validation' },
            { name: 'UDIS', level: 3, highest_proven: 3, target_level: 4, status: 'proven', description: '10-state device FSM', unit_tests: true, integration_tests: true, benchmarked: false, evidence: 'unit+integration', next_milestone: 'Benchmark suite' },
            { name: 'MCP', level: 2, highest_proven: 2, target_level: 3, status: 'proven', description: '2026-07-28 gateway', unit_tests: true, integration_tests: false, benchmarked: false, evidence: 'unit', next_milestone: 'Interop matrix' },
          ],
          levels: { L0: 'concept', L1: 'prototype', L2: 'unit-tested', L3: 'integration-tested', L4: 'benchmarked', L5: 'externally validated', L6: 'operational' },
          highest: 4,
          lowest: 2,
        });

      case 'GET /models':
        return json(res, {
          models: [
            { model_id: 'vision-v3', version: 'v3.2', hash: 'sha256:abc', provider: 'ultrone', status: 'APPROVED' },
            { model_id: 'vision-v3.4', version: 'v3.4', hash: 'sha256:def', provider: 'ultrone', status: 'CANDIDATE' },
          ],
        });

      case 'GET /datasets':
        return json(res, {
          datasets: [
            { dataset_id: 'scouting-fusion', version: 'v4', hash: 'sha256:ds1', split: { train: 0.7, validation: 0.15, holdout: 0.15 }, contamination_status: 'CLEAN' },
          ],
        });

      case 'GET /policies':
        return json(res, {
          policies: [
            { policy_id: 'SAF-001', name: 'Causal Boundary', severity: 'CRITICAL' },
            { policy_id: 'SAF-003', name: 'Telemetry Freshness', severity: 'HIGH' },
          ],
        });

      case 'GET /scenarios':
        return json(res, {
          scenarios: [
            { scenario_id: 'standard_patrol', name: 'Standard Patrol', description: 'Baseline two-entity patrol', seed: 12345, entities: 2, devices: 3 },
            { scenario_id: 'contested_airspace', name: 'Contested Airspace', description: 'Denser hostile pattern', seed: 777, entities: 5, devices: 3 },
          ],
        });

      case 'GET /search':
        return json(res, [
          { category: 'device', id: 'device-17', title: 'device-17', subtitle: 'digital_twin · BUSY', badge: 'BUSY', route: '/devices' },
          { category: 'event', id: 'EVT-8821', title: 'EVT-8821', subtitle: 'BeliefUpdated · tick 42', badge: 'INFO', route: '/events' },
        ]);

      case 'GET /ui-actions':
        return json(res, runtime.uiActions);

      case 'GET /devices/device-01':
        return json(res, deviceDetail(DEVICES[0]));

      case 'GET /devices/device-04':
        return json(res, deviceDetail(DEVICES[1]));

      case 'GET /devices/device-17':
        return json(res, deviceDetail(DEVICES[2]));

      case 'GET /agents/agent-01':
        return json(res, AGENTS[0]);

      case 'GET /agents/agent-02':
        return json(res, AGENTS[1]);

      case 'GET /agents/agent-03':
        return json(res, AGENTS[2]);

      case 'GET /traces/DEC-281':
        return json(res, TRACES()[0]);

      case 'GET /export-report':
        return json(res, { report_id: 'RPT-001', format: 'json', generated_at: now(), run_id: 'RUN-004281' });

      case 'POST /control/play':
        await post();
        runtime.playing = true;
        runtime.uiActions.push({
          action_id: `UIACT-${String(runtime.uiActions.length + 1).padStart(5, '0')}`,
          actor: 'operator', timestamp: now(), page: 'cockpit', action: 'PLAY',
          target: 'simulation', run_id: 'RUN-004281', environment: 'simulation',
          authorization: 'cockpit-role', detail: {}, before: false, after: true,
        });
        return json(res, { ok: true, playing: true });

      case 'POST /control/pause':
        await post();
        runtime.playing = false;
        return json(res, { ok: true, playing: false });

      case 'POST /control/step': {
        const body = await post();
        runtime.tick += body.count ?? 1;
        return json(res, { ok: true, tick: runtime.tick });
      }

      case 'POST /control/reset':
        await post();
        runtime.tick = 0;
        runtime.playing = false;
        return json(res, { ok: true, tick: 0 });

      case 'POST /control/speed': {
        const body = await post();
        runtime.speed = body.speed ?? 1;
        return json(res, { ok: true, speed: runtime.speed });
      }

      case 'POST /replay':
        return json(res, {
          replay_id: 'REPLAY-001',
          original_vs_replay: [
            { metric: 'belief', original: 0.82, replay: 0.82, match: true },
            { metric: 'plan', original: 'P-82', replay: 'P-82', match: true },
          ],
          diverged: false,
        });

      case 'POST /events/checkpoint':
        return json(res, { checkpoint_id: 'CP-020', valid: true });

      case 'POST /scenarios/select': {
        const body = await post();
        runtime.scenario = body.scenario_id;
        return json(res, { ok: true });
      }

      case 'POST /ui-actions': {
        const body = await post();
        const entry = {
          action_id: `UIACT-${String(runtime.uiActions.length + 1).padStart(5, '0')}`,
          actor: body.actor ?? 'operator',
          timestamp: now(),
          page: body.page ?? 'cockpit',
          action: body.action,
          target: body.target,
          run_id: 'RUN-004281',
          environment: 'simulation',
          authorization: 'cockpit-role',
          detail: body.detail ?? {},
          before: body.before ?? null,
          after: body.after ?? null,
        };
        runtime.uiActions.push(entry);
        return json(res, entry);
      }

      default:
        return json(res, { detail: `mock backend: unhandled route ${route}` }, 404);
    }
  } catch (err) {
    return json(res, { detail: String(err) }, 500);
  }
}



// Copyright (c) Ultrone Contributors. All rights reserved.
/**
 * Typed API client for the ULTRONE Cockpit REST & WebSocket backend.
 */

import type {
  CockpitOverview,
  SystemTruth,
  WorldSnapshot,
  AgentCatalog,
  AgentRecord,
  DeviceCatalog,
  DeviceDetail,
  McpTrafficEntry,
  StoredEvent,
  EventStoreStatus,
  DecisionTrace,
  WhyBlockedResult,
  EvaluationBenchmarkResult,
  GovernanceStatus,
  SearchResultItem,
  AlertItem,
} from './types';

const BASE_URL = '/api/cockpit';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || JSON.stringify(errJson);
    } catch {}
    throw new Error(`API error [${response.status}] ${url}: ${errorDetail}`);
  }

  return response.json();
}

export const cockpitApi = {
  // Global status & overview
  getOverview: () => request<CockpitOverview>('/overview'),
  getTruth: () => request<SystemTruth>('/truth'),
  getHealth: () => request<any>('/health'),
  getAlerts: () => request<AlertItem[]>('/alerts'),

  // Simulation controls
  getWorld: () => request<WorldSnapshot>('/world'),
  play: (speed?: number, actor = 'operator') =>
    request<any>('/control/play', {
      method: 'POST',
      body: JSON.stringify({ speed, actor }),
    }),
  pause: (actor = 'operator') =>
    request<any>('/control/pause', {
      method: 'POST',
      body: JSON.stringify({ actor }),
    }),
  step: (count = 1, actor = 'operator') =>
    request<any>('/control/step', {
      method: 'POST',
      body: JSON.stringify({ count, actor }),
    }),
  reset: (actor = 'operator') =>
    request<any>('/control/reset', {
      method: 'POST',
      body: JSON.stringify({ actor }),
    }),
  setSpeed: (speed: number, actor = 'operator') =>
    request<any>('/control/speed', {
      method: 'POST',
      body: JSON.stringify({ speed, actor }),
    }),
  injectFaults: (config: Record<string, any>, actor = 'researcher') =>
    request<any>('/control/faults', {
      method: 'POST',
      body: JSON.stringify({ config, actor }),
    }),
  clearFaults: (actor = 'researcher') =>
    request<any>('/control/clear-faults', {
      method: 'POST',
      body: JSON.stringify({ actor }),
    }),

  // Agents
  getAgents: () => request<AgentCatalog>('/agents'),
  getAgentDetail: (agentId: string) => request<AgentRecord & Record<string, any>>(`/agents/${agentId}`),

  // Devices & FSM
  getDevices: () => request<DeviceCatalog>('/devices'),
  getDeviceDetail: (deviceId: string) => request<DeviceDetail>(`/devices/${deviceId}`),
  transitionDevice: (deviceId: string, targetState: string, reason = 'cockpit operator') =>
    request<any>(`/devices/${deviceId}/transition`, {
      method: 'POST',
      body: JSON.stringify({ target_state: targetState, reason, actor: 'operator' }),
    }),
  executeProcedure: (deviceId: string, procedureName: string, parameters: Record<string, any> = {}) =>
    request<any>(`/devices/${deviceId}/procedure`, {
      method: 'POST',
      body: JSON.stringify({ procedure_name: procedureName, parameters, actor: 'operator' }),
    }),

  // MCP 2026-07-28
  getMcpTraffic: (limit = 100, method?: string) => {
    const q = method ? `?limit=${limit}&method=${encodeURIComponent(method)}` : `?limit=${limit}`;
    return request<McpTrafficEntry[]>(`/mcp/traffic${q}`);
  },
  getMcpDiscovery: () => request<any>('/mcp/discovery'),
  callMcpTool: (tool: string, args: Record<string, any> = {}) =>
    request<any>('/mcp/tools/call', {
      method: 'POST',
      body: JSON.stringify({ tool, arguments: args }),
    }),
  readMcpResource: (uri: string) =>
    request<any>(`/mcp/resources/read?uri=${encodeURIComponent(uri)}`),

  // Events & Replay
  getEvents: (limit = 200, eventType?: string, sinceTick?: number) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (eventType) params.set('event_type', eventType);
    if (sinceTick !== undefined) params.set('since_tick', String(sinceTick));
    return request<StoredEvent[]>(`/events?${params.toString()}`);
  },
  getEventStore: () => request<EventStoreStatus>('/events/store'),
  createCheckpoint: (actor = 'auditor') =>
    request<any>('/events/checkpoint', {
      method: 'POST',
      body: JSON.stringify({ actor }),
    }),
  runReplay: (ticks?: number, actor = 'researcher') =>
    request<any>('/replay', {
      method: 'POST',
      body: JSON.stringify({ ticks, actor }),
    }),

  // Traces & Safety
  getTraces: (limit = 100) => request<DecisionTrace[]>(`/traces?limit=${limit}`),
  getTraceDetail: (decisionId: string) => request<any>(`/traces/${decisionId}`),
  getSafetyStatus: () => request<any>('/safety/status'),
  getInvariants: () => request<any[]>('/safety/invariants'),
  getWhyBlocked: (decisionId: string) => request<WhyBlockedResult>(`/safety/why-blocked/${decisionId}`),
  getCausalBoundary: () => request<any>('/safety/causal-boundary'),

  // Research & Governance
  getEvaluation: (seeds = 5, ticks = 20, candidateNoiseScale = 0.7) =>
    request<EvaluationBenchmarkResult>(
      `/evaluation?seeds=${seeds}&ticks=${ticks}&candidate_noise_scale=${candidateNoiseScale}`
    ),
  getGovernance: () => request<GovernanceStatus>('/governance'),
  getEvidence: () => request<any>('/evidence'),
  getModels: () => request<any>('/models'),
  getDatasets: () => request<any>('/datasets'),
  getPolicies: () => request<any>('/policies'),

  // Scenarios, Search & Reports
  getScenarios: () => request<any>('/scenarios'),
  selectScenario: (scenarioId: string) =>
    request<any>('/scenarios/select', {
      method: 'POST',
      body: JSON.stringify({ scenario_id: scenarioId, actor: 'researcher' }),
    }),
  search: (query: string, limit = 50) =>
    request<SearchResultItem[]>(`/search?q=${encodeURIComponent(query)}&limit=${limit}`),
  getUiActions: (limit = 100) =>
    request<any[]>(`/ui-actions?limit=${limit}`),
  exportReport: (format = 'json') => request<any>(`/export-report?format=${format}`),
  recordUiAction: (actor: string, action: string, target: string, detail?: any) =>
    request<any>('/ui-actions', {
      method: 'POST',
      body: JSON.stringify({ actor, action, target, detail }),
    }),
};

/**
 * Live WebSocket connector with automatic reconnection.
 */
export function connectCockpitWebSocket(
  onMessage: (data: any) => void,
  onStatusChange?: (status: 'connected' | 'reconnecting' | 'disconnected') => void
): () => void {
  let ws: WebSocket | null = null;
  let isClosed = false;
  let retryTimeout: any = null;

  const connect = () => {
    if (isClosed) return;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}/api/cockpit/ws`;

    try {
      ws = new WebSocket(url);
      ws.onopen = () => {
        onStatusChange?.('connected');
      };
      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          onMessage(data);
        } catch {}
      };
      ws.onclose = () => {
        if (!isClosed) {
          onStatusChange?.('reconnecting');
          retryTimeout = setTimeout(connect, 2000);
        } else {
          onStatusChange?.('disconnected');
        }
      };
      ws.onerror = () => {
        ws?.close();
      };
    } catch {
      onStatusChange?.('reconnecting');
      retryTimeout = setTimeout(connect, 3000);
    }
  };

  connect();

  return () => {
    isClosed = true;
    if (retryTimeout) clearTimeout(retryTimeout);
    ws?.close();
  };
}

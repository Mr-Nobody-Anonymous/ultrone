/**
 * ULTRONE Operational Platform API Client
 * Interfaces with FastAPI backend routers for World State, Ontology, Workflows,
 * Investigations, Scenarios, and Multi-Provider AI Copilot.
 */

const API_BASE = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

export class UltroneApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
    if (!res.ok) {
      throw new Error(`[UltroneApiClient] HTTP ${res.status}: ${res.statusText}`);
    }
    return res.json() as Promise<T>;
  }

  // World State & Entities
  public async getEntities(): Promise<any[]> {
    try {
      return await this.fetchJson<any[]>('/api/v1/entities');
    } catch {
      return [];
    }
  }

  public async getEntityById(id: string): Promise<any | null> {
    try {
      return await this.fetchJson<any>(`/api/v1/entities/${id}`);
    } catch {
      return null;
    }
  }

  // Geospatial Layers
  public async getLayers(): Promise<any[]> {
    try {
      return await this.fetchJson<any[]>('/api/v1/layers');
    } catch {
      return [];
    }
  }

  // Investigations & Cases
  public async getCases(): Promise<any[]> {
    try {
      return await this.fetchJson<any[]>('/api/v1/investigations/cases');
    } catch {
      return [];
    }
  }

  public async createCase(data: { title: string; lead_analyst: string; summary?: string }): Promise<any> {
    return await this.fetchJson<any>('/api/v1/investigations/cases', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Workflows & Actions
  public async executeAction(actionId: string, params: Record<string, any>): Promise<any> {
    return await this.fetchJson<any>(`/api/v1/workflows/actions/${actionId}/execute`, {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  // AI Inference & Models
  public async queryAI(prompt: string, provider: string = 'local_qwen', model?: string): Promise<any> {
    return await this.fetchJson<any>('/api/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ prompt, provider, model }),
    });
  }

  // Simulation & Scenarios
  public async getScenarios(): Promise<any[]> {
    try {
      return await this.fetchJson<any[]>('/api/v1/simulation/scenarios');
    } catch {
      return [];
    }
  }
}

export const apiClient = new UltroneApiClient();

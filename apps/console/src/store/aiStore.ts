import { create } from 'zustand';
import { AIProviderId, AI_PROVIDERS } from '../types/ai';

interface AIState {
  activeProvider: AIProviderId;
  selectedModel: string;
  apiKeys: Record<string, string>;
  customBaseUrls: Record<string, string>;
  temperature: number;
  maxTokens: number;
  mode: 'live' | 'simulation'; // Live LLM API or Cognitive Simulation

  // Actions
  setActiveProvider: (provider: AIProviderId) => void;
  setSelectedModel: (model: string) => void;
  setApiKey: (provider: string, key: string) => void;
  setCustomBaseUrl: (provider: string, url: string) => void;
  setTemperature: (temp: number) => void;
  setMaxTokens: (tokens: number) => void;
  setMode: (mode: 'live' | 'simulation') => void;
  getActiveConfig: () => {
    provider: AIProviderId;
    model: string;
    apiKey: string;
    baseUrl: string;
    temperature: number;
    maxTokens: number;
    isLocal: boolean;
  };
}

// Load saved config from localStorage if available
const loadSaved = (key: string, fallback: any) => {
  try {
    const saved = localStorage.getItem(`ultrone_ai_${key}`);
    return saved ? JSON.parse(saved) : fallback;
  } catch {
    return fallback;
  }
};

export const useAIStore = create<AIState>((set, get) => ({
  activeProvider: loadSaved('activeProvider', 'openrouter') as AIProviderId,
  selectedModel: loadSaved('selectedModel', 'anthropic/claude-3.5-sonnet'),
  apiKeys: loadSaved('apiKeys', {}),
  customBaseUrls: loadSaved('customBaseUrls', {}),
  temperature: loadSaved('temperature', 0.3),
  maxTokens: loadSaved('maxTokens', 1500),
  mode: loadSaved('mode', 'simulation'),

  setActiveProvider: (provider) => {
    const defaultModel = AI_PROVIDERS[provider]?.models[0]?.id || '';
    set({ activeProvider: provider, selectedModel: defaultModel });
    try {
      localStorage.setItem('ultrone_ai_activeProvider', JSON.stringify(provider));
      localStorage.setItem('ultrone_ai_selectedModel', JSON.stringify(defaultModel));
    } catch {}
  },

  setSelectedModel: (model) => {
    set({ selectedModel: model });
    try {
      localStorage.setItem('ultrone_ai_selectedModel', JSON.stringify(model));
    } catch {}
  },

  setApiKey: (provider, key) => {
    set((s) => {
      const updated = { ...s.apiKeys, [provider]: key };
      try {
        localStorage.setItem('ultrone_ai_apiKeys', JSON.stringify(updated));
      } catch {}
      return { apiKeys: updated };
    });
  },

  setCustomBaseUrl: (provider, url) => {
    set((s) => {
      const updated = { ...s.customBaseUrls, [provider]: url };
      try {
        localStorage.setItem('ultrone_ai_customBaseUrls', JSON.stringify(updated));
      } catch {}
      return { customBaseUrls: updated };
    });
  },

  setTemperature: (temp) => {
    set({ temperature: temp });
    try {
      localStorage.setItem('ultrone_ai_temperature', JSON.stringify(temp));
    } catch {}
  },

  setMaxTokens: (tokens) => {
    set({ maxTokens: tokens });
    try {
      localStorage.setItem('ultrone_ai_maxTokens', JSON.stringify(tokens));
    } catch {}
  },

  setMode: (mode) => {
    set({ mode });
    try {
      localStorage.setItem('ultrone_ai_mode', JSON.stringify(mode));
    } catch {}
  },

  getActiveConfig: () => {
    const state = get();
    const providerSpec = AI_PROVIDERS[state.activeProvider];
    return {
      provider: state.activeProvider,
      model: state.selectedModel || providerSpec.models[0].id,
      apiKey: state.apiKeys[state.activeProvider] || '',
      baseUrl: state.customBaseUrls[state.activeProvider] || providerSpec.defaultBaseUrl,
      temperature: state.temperature,
      maxTokens: state.maxTokens,
      isLocal: providerSpec.isLocal,
    };
  },
}));

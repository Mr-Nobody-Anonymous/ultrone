export type AIProviderId =
  | 'openrouter'
  | 'google'
  | 'openai'
  | 'claude'
  | 'deepseek'
  | 'ollama'
  | 'lmstudio';

export interface AIModel {
  id: string;
  name: string;
  contextWindow: number;
  description: string;
  strengths: string[];
}

export interface AIProvider {
  id: AIProviderId;
  name: string;
  description: string;
  defaultBaseUrl: string;
  isLocal: boolean;
  keyPortalUrl?: string;
  models: AIModel[];
}

export const AI_PROVIDERS: Record<AIProviderId, AIProvider> = {
  openrouter: {
    id: 'openrouter',
    name: 'OpenRouter',
    description: 'Universal model aggregator (Claude, GPT-4o, DeepSeek, Qwen)',
    defaultBaseUrl: 'https://openrouter.ai/api/v1',
    isLocal: false,
    keyPortalUrl: 'https://openrouter.ai/keys',
    models: [
      { id: 'anthropic/claude-3.5-sonnet', name: 'Claude 3.5 Sonnet', contextWindow: 200000, description: 'Top coding & reasoning', strengths: ['reasoning', 'coding'] },
      { id: 'deepseek/deepseek-r1', name: 'DeepSeek R1', contextWindow: 64000, description: 'Open reasoning frontier', strengths: ['math', 'logic'] },
      { id: 'qwen/qwen-2.5-72b-instruct', name: 'Qwen 2.5 72B', contextWindow: 131072, description: 'Flagship multilingual open weights', strengths: ['multilingual', 'knowledge'] },
      { id: 'openai/gpt-4o', name: 'GPT-4o', contextWindow: 128000, description: 'Multimodal omni model', strengths: ['general', 'vision'] },
      { id: 'google/gemini-2.0-flash-exp:free', name: 'Gemini 2.0 Flash (Free)', contextWindow: 1000000, description: 'High-speed long context', strengths: ['speed', 'free'] },
    ],
  },
  google: {
    id: 'google',
    name: 'Google Gemini',
    description: 'Google Generative AI (Gemini 1.5 Pro & Flash)',
    defaultBaseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai/',
    isLocal: false,
    keyPortalUrl: 'https://aistudio.google.com/app/apikey',
    models: [
      { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', contextWindow: 2000000, description: '2M tokens deep multimodal analysis', strengths: ['context', 'multimodal'] },
      { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash', contextWindow: 1000000, description: 'High throughput, low latency', strengths: ['speed', 'cost'] },
      { id: 'gemini-2.0-flash-exp', name: 'Gemini 2.0 Flash', contextWindow: 1000000, description: 'Next-gen experimental preview', strengths: ['next-gen'] },
    ],
  },
  openai: {
    id: 'openai',
    name: 'OpenAI',
    description: 'Direct OpenAI API (GPT-4o, o1, o3)',
    defaultBaseUrl: 'https://api.openai.com/v1',
    isLocal: false,
    keyPortalUrl: 'https://platform.openai.com/api-keys',
    models: [
      { id: 'gpt-4o', name: 'GPT-4o', contextWindow: 128000, description: 'Flagship omni model', strengths: ['general', 'coding'] },
      { id: 'gpt-4o-mini', name: 'GPT-4o Mini', contextWindow: 128000, description: 'Fast, lightweight and low cost', strengths: ['speed', 'efficiency'] },
      { id: 'o1-preview', name: 'OpenAI o1', contextWindow: 128000, description: 'Chain-of-thought deep reasoning', strengths: ['deep-reasoning'] },
    ],
  },
  claude: {
    id: 'claude',
    name: 'Anthropic Claude',
    description: 'Direct Anthropic Claude or Proxy Endpoint',
    defaultBaseUrl: 'https://api.anthropic.com/v1',
    isLocal: false,
    keyPortalUrl: 'https://console.anthropic.com/settings/keys',
    models: [
      { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', contextWindow: 200000, description: 'State of the art intelligence', strengths: ['coding', 'reasoning'] },
      { id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku', contextWindow: 200000, description: 'Rapid responses and summarization', strengths: ['speed'] },
    ],
  },
  deepseek: {
    id: 'deepseek',
    name: 'DeepSeek',
    description: 'Direct DeepSeek API (V3 and R1 reasoning)',
    defaultBaseUrl: 'https://api.deepseek.com/v1',
    isLocal: false,
    keyPortalUrl: 'https://platform.deepseek.com/api_keys',
    models: [
      { id: 'deepseek-chat', name: 'DeepSeek-V3 Chat', contextWindow: 64000, description: 'High quality general chat and coding', strengths: ['coding', 'value'] },
      { id: 'deepseek-reasoner', name: 'DeepSeek-R1 Reasoner', contextWindow: 64000, description: 'Full reasoning trace model', strengths: ['math', 'reasoning'] },
    ],
  },
  ollama: {
    id: 'ollama',
    name: 'Local AI (Ollama / Qwen)',
    description: 'Runs offline on your local GPU/CPU via Ollama',
    defaultBaseUrl: 'http://localhost:11434/v1',
    isLocal: true,
    keyPortalUrl: 'https://ollama.com/download',
    models: [
      { id: 'qwen2.5:7b', name: 'Qwen 2.5 7B (Local)', contextWindow: 32768, description: 'Alibaba Qwen 2.5 local battlefield model', strengths: ['offline', 'privacy'] },
      { id: 'qwen2.5:14b', name: 'Qwen 2.5 14B (Local)', contextWindow: 32768, description: 'High capacity local tactical planner', strengths: ['offline', 'reasoning'] },
      { id: 'qwen2.5-coder:7b', name: 'Qwen 2.5 Coder 7B (Local)', contextWindow: 32768, description: 'Specialized local code & tool agent', strengths: ['offline', 'coding'] },
      { id: 'deepseek-r1:7b', name: 'DeepSeek R1 7B Distill (Local)', contextWindow: 32768, description: 'Local chain-of-thought reasoner', strengths: ['offline', 'logic'] },
      { id: 'llama3.2:3b', name: 'Llama 3.2 3B (Local)', contextWindow: 131072, description: 'Lightweight local model', strengths: ['offline', 'speed'] },
    ],
  },
  lmstudio: {
    id: 'lmstudio',
    name: 'Local AI (LM Studio)',
    description: 'Connects to models loaded in LM Studio GUI',
    defaultBaseUrl: 'http://localhost:1234/v1',
    isLocal: true,
    keyPortalUrl: 'https://lmstudio.ai',
    models: [
      { id: 'local-model', name: 'LM Studio Active Model', contextWindow: 32768, description: 'Active model in LM Studio server', strengths: ['offline', 'local'] },
    ],
  },
};

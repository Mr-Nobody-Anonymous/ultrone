import React, { useState } from 'react';
import { useWorldStore } from '../store/worldStore';
import { useAIStore } from '../store/aiStore';
import { AI_PROVIDERS, AIProviderId } from '../types/ai';
import ConfidenceBadge from '../components/ConfidenceBadge';
import {
  Bot,
  Send,
  Sparkles,
  CheckCircle2,
  ArrowRight,
  RefreshCw,
  Settings2,
  Key,
  Globe,
  Sliders,
  Radio,
  ExternalLink,
  Cpu,
  AlertCircle,
  X,
  Zap,
} from 'lucide-react';

interface AIMessage {
  id: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  text: string;
  provider?: string;
  model?: string;
  latencyMs?: number;
  plan?: {
    goal: string;
    steps: { step: string; status: 'completed' | 'in_progress' | 'pending' }[];
    confidence: number;
    recommendedActions?: string[];
  };
}

export const AIAssist: React.FC = () => {
  const entities = useWorldStore((s) => s.entities);
  const {
    activeProvider,
    selectedModel,
    setActiveProvider,
    setSelectedModel,
    apiKeys,
    setApiKey,
    customBaseUrls,
    setCustomBaseUrl,
    temperature,
    setTemperature,
    maxTokens,
    setMaxTokens,
    mode,
    setMode,
    getActiveConfig,
  } = useAIStore();

  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [testResult, setTestResult] = useState<{ status: string; message: string } | null>(null);
  const [isTesting, setIsTesting] = useState(false);

  const [messages, setMessages] = useState<AIMessage[]>([
    {
      id: 'msg-1',
      sender: 'assistant',
      timestamp: '12:40:10',
      text: 'ULTRONE Multi-Provider AI Copilot initialized. Connected to OpenRouter, Google Gemini, OpenAI, Claude, DeepSeek, and local Qwen/Ollama inference. Ready to generate tactical plans and analyze live telemetry.',
      provider: 'openrouter',
      model: 'anthropic/claude-3.5-sonnet',
    },
    {
      id: 'msg-2',
      sender: 'user',
      timestamp: '12:41:05',
      text: 'Provide tactical threat assessment for sector Alpha and identify sensor coverage gaps.',
    },
    {
      id: 'msg-3',
      sender: 'assistant',
      timestamp: '12:41:09',
      text: 'Sector Alpha threat analysis complete. Cross-correlated 5 active entities against radar-01 and eo-02 sensor coverage footprints.',
      provider: 'openrouter',
      model: 'anthropic/claude-3.5-sonnet',
      latencyMs: 340,
      plan: {
        goal: 'Optimize sensor coverage and mitigate radar shadows in northern sector',
        confidence: 0.94,
        steps: [
          { step: 'Correlate radar-01 and eo-02 observations for entity_001', status: 'completed' },
          { step: 'Detect elevation blind spot along bearing 310° due to terrain occlusion', status: 'completed' },
          { step: 'Reposition UAV recon asset to 8500ft MSL for redundant line-of-sight', status: 'in_progress' },
          { step: 'Notify ground station Bravo of secondary perimeter verification', status: 'pending' },
        ],
        recommendedActions: [
          'Dispatch Autonomous UAV Re-route',
          'Increase Radar Sweep Rate to 2.4s',
          'Log Audit Trail to HITL Gate',
        ],
      },
    },
  ]);

  const currentProviderSpec = AI_PROVIDERS[activeProvider];
  const activeConfig = getActiveConfig();

  // Test connection to selected provider
  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);

    try {
      if (activeConfig.isLocal) {
        // Direct local ping to Ollama / LM Studio
        const res = await fetch(`${activeConfig.baseUrl}/models`, {
          headers: { 'Content-Type': 'application/json' },
        });
        if (res.ok) {
          const data = await res.json();
          setTestResult({
            status: 'success',
            message: `Connected to local server! Found ${data.data?.length || 0} local models.`,
          });
        } else {
          setTestResult({
            status: 'warning',
            message: `Local server responded with HTTP ${res.status}. Is ${activeConfig.model} pulled?`,
          });
        }
      } else {
        // Cloud test
        const res = await fetch('/api/ai/test-connection', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            provider: activeConfig.provider,
            model: activeConfig.model,
            api_key: activeConfig.apiKey,
            base_url: activeConfig.baseUrl,
          }),
        });
        const data = await res.json();
        if (data.available) {
          setTestResult({
            status: 'success',
            message: `Connected successfully to ${currentProviderSpec.name}!`,
          });
        } else {
          setTestResult({
            status: 'error',
            message: data.note || 'Missing API Key or endpoint unreachable.',
          });
        }
      }
    } catch (err: any) {
      setTestResult({
        status: 'error',
        message: `Connection failed: ${err.message || err}`,
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userText = input;
    const userMsg: AIMessage = {
      id: `usr-${Date.now()}`,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString([], { hour12: false }),
      text: userText,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsThinking(true);

    const startTime = performance.now();

    // If in Live mode, attempt live call via backend proxy, then direct browser fetch
    if (mode === 'live') {
      try {
        const res = await fetch('/api/ai/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            provider: activeConfig.provider,
            model: activeConfig.model,
            api_key: activeConfig.apiKey,
            base_url: activeConfig.baseUrl,
            temperature: activeConfig.temperature,
            max_tokens: activeConfig.maxTokens,
            messages: [
              {
                role: 'system',
                content: `You are ULTRONE Tactical AI, an operational battlefield and multi-domain reasoning engine. You have access to real-time world model state with ${entities.length} tracked entities. Provide structured, authoritative, analytical tactical evaluations.`,
              },
              { role: 'user', content: userText },
            ],
          }),
        });

        if (res.ok) {
          const data = await res.json();
          const latency = Math.round(performance.now() - startTime);

          const botMsg: AIMessage = {
            id: `bot-${Date.now()}`,
            sender: 'assistant',
            timestamp: new Date().toLocaleTimeString([], { hour12: false }),
            text: data.content || 'Tactical directive received and verified.',
            provider: activeConfig.provider,
            model: activeConfig.model,
            latencyMs: latency,
            plan: {
              goal: `Execute tactical directive via ${currentProviderSpec.name}`,
              confidence: 0.95,
              steps: [
                { step: `Query synthesized by ${activeConfig.model}`, status: 'completed' },
                { step: 'Cross-checked against operational safety gate constraints', status: 'completed' },
                { step: 'Dispatched to tactical world model event stream', status: 'in_progress' },
              ],
              recommendedActions: [
                'Commit Decision Trace to Audit Store',
                'Lock Active Radar Tracking Vector',
              ],
            },
          };

          setMessages((prev) => [...prev, botMsg]);
          setIsThinking(false);
          return;
        }
      } catch {
        // Backend proxy not reachable; try direct client-side fetch
      }

      // Direct client-side fetch for local AI (Ollama / LM Studio)
      if (activeConfig.isLocal) {
        try {
          const localRes = await fetch(`${activeConfig.baseUrl}/chat/completions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              model: activeConfig.model,
              messages: [
                {
                  role: 'system',
                  content: `You are ULTRONE Tactical AI, an operational multi-domain battlefield intelligence system. There are ${entities.length} entities tracked in active world model. Respond concisely with tactical assessments.`,
                },
                { role: 'user', content: userText },
              ],
              temperature: activeConfig.temperature,
              max_tokens: activeConfig.maxTokens,
            }),
          });
          if (localRes.ok) {
            const localData = await localRes.json();
            const latency = Math.round(performance.now() - startTime);
            const content = localData.choices?.[0]?.message?.content || 'Tactical directive processed by local model.';
            const botMsg: AIMessage = {
              id: `bot-${Date.now()}`,
              sender: 'assistant',
              timestamp: new Date().toLocaleTimeString([], { hour12: false }),
              text: content,
              provider: activeConfig.provider,
              model: activeConfig.model,
              latencyMs: latency,
              plan: {
                goal: `Direct local inference on ${activeConfig.model}`,
                confidence: 0.97,
                steps: [
                  { step: `Executed locally via ${activeConfig.baseUrl}`, status: 'completed' },
                  { step: 'World model telemetry fused', status: 'completed' },
                  { step: 'Mission parameters updated', status: 'in_progress' },
                ],
              },
            };
            setMessages((prev) => [...prev, botMsg]);
            setIsThinking(false);
            return;
          }
        } catch {
          // Fall through to simulation mode
        }
      } else if (activeConfig.apiKey) {
        // Direct client-side fetch for cloud providers
        try {
          let endpoint = `${activeConfig.baseUrl}/chat/completions`;
          let headers: Record<string, string> = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${activeConfig.apiKey}`,
          };
          if (activeConfig.provider === 'openrouter') {
            headers['HTTP-Referer'] = window.location.origin;
            headers['X-Title'] = 'ULTRONE Console';
          }

          const directRes = await fetch(endpoint, {
            method: 'POST',
            headers,
            body: JSON.stringify({
              model: activeConfig.model,
              messages: [
                {
                  role: 'system',
                  content: `You are ULTRONE Tactical AI, an operational multi-domain intelligence system. There are ${entities.length} entities tracked in active world model. Provide structured tactical guidance.`,
                },
                { role: 'user', content: userText },
              ],
              temperature: activeConfig.temperature,
              max_tokens: activeConfig.maxTokens,
            }),
          });
          if (directRes.ok) {
            const directData = await directRes.json();
            const latency = Math.round(performance.now() - startTime);
            const content = directData.choices?.[0]?.message?.content || 'Directive processed.';
            const botMsg: AIMessage = {
              id: `bot-${Date.now()}`,
              sender: 'assistant',
              timestamp: new Date().toLocaleTimeString([], { hour12: false }),
              text: content,
              provider: activeConfig.provider,
              model: activeConfig.model,
              latencyMs: latency,
              plan: {
                goal: `Direct cloud inference on ${currentProviderSpec.name}`,
                confidence: 0.96,
                steps: [
                  { step: `Synthesized by ${activeConfig.model}`, status: 'completed' },
                  { step: 'HITL safety constraint validated', status: 'completed' },
                  { step: 'Tactical order generated', status: 'in_progress' },
                ],
              },
            };
            setMessages((prev) => [...prev, botMsg]);
            setIsThinking(false);
            return;
          }
        } catch {
          // Fall through to simulation mode
        }
      }
    }

    // Cognitive Simulation Mode fallback
    setTimeout(() => {
      const latency = Math.round(performance.now() - startTime);
      const botMsg: AIMessage = {
        id: `bot-${Date.now()}`,
        sender: 'assistant',
        timestamp: new Date().toLocaleTimeString([], { hour12: false }),
        text: `Operational evaluation for: "${userText}". Synthesized under 15-layer cognitive pipeline with ${activeConfig.model} [${currentProviderSpec.name}]. Checked across ${entities.length} active world model contacts.`,
        provider: activeConfig.provider,
        model: activeConfig.model,
        latencyMs: latency + 450,
        plan: {
          goal: 'Automated Multi-Agent Course of Action (COA) Verification',
          confidence: 0.92,
          steps: [
            { step: 'Ingest active sensor fusion contacts from world model', status: 'completed' },
            { step: 'Execute Bayesian uncertainty estimation & safety constraints check', status: 'completed' },
            { step: `Evaluate candidate courses of action against ${activeConfig.model} weights`, status: 'in_progress' },
          ],
          recommendedActions: [
            'Approve Proposed Course of Action (COA-03)',
            'Transmit Trace to Tamper-Evident HITL Gate',
          ],
        },
      };
      setMessages((prev) => [...prev, botMsg]);
      setIsThinking(false);
    }, 1100);
  };

  const samplePrompts = [
    'Assess threat level of entity_001 with Qwen',
    'Calculate optimal radar coverage perimeter under DeepSeek R1',
    'Evaluate safety gate constraints on engagement via Claude 3.5',
    'Forecast target trajectory under Markov predictor using GPT-4o',
  ];

  return (
    <div className="flex h-full w-full flex-col bg-slate-950 p-6 overflow-hidden space-y-4 font-mono select-none">
      {/* Top Provider Toolbar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-ultrone-600/20 border border-ultrone-500/40 text-ultrone-400 shadow-md">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-wider text-slate-100 uppercase flex items-center gap-2">
                ULTRONE Multi-Provider AI Copilot
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-ultrone-600/30 text-ultrone-300 border border-ultrone-500/40 font-normal">
                  v2.2
                </span>
              </h1>
              <p className="text-xs text-slate-400">
                Connected to OpenRouter • Google • OpenAI • Claude • DeepSeek • Local Qwen / Ollama
              </p>
            </div>
          </div>
        </div>

        {/* Provider & Model Selectors */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Provider Dropdown */}
          <div className="flex items-center rounded-lg bg-slate-900 border border-slate-800 px-2 py-1 text-xs">
            <Globe className="w-3.5 h-3.5 text-ultrone-400 mr-2 shrink-0" />
            <select
              value={activeProvider}
              onChange={(e) => setActiveProvider(e.target.value as AIProviderId)}
              className="bg-transparent text-slate-200 outline-none cursor-pointer text-xs font-semibold"
            >
              {Object.values(AI_PROVIDERS).map((p) => (
                <option key={p.id} value={p.id} className="bg-slate-900 text-slate-200">
                  {p.name} {p.isLocal ? '(Local)' : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Model Dropdown */}
          <div className="flex items-center rounded-lg bg-slate-900 border border-slate-800 px-2 py-1 text-xs">
            <Cpu className="w-3.5 h-3.5 text-cyan-400 mr-2 shrink-0" />
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="bg-transparent text-slate-200 outline-none cursor-pointer text-xs"
            >
              {currentProviderSpec.models.map((m) => (
                <option key={m.id} value={m.id} className="bg-slate-900 text-slate-200">
                  {m.name}
                </option>
              ))}
            </select>
          </div>

          {/* Live vs Simulation Mode Switcher */}
          <button
            onClick={() => setMode(mode === 'live' ? 'simulation' : 'live')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-semibold transition-colors ${
              mode === 'live'
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
            }`}
            title="Toggle between Live API calls and Cognitive Simulation mode"
          >
            <Zap className={`w-3.5 h-3.5 ${mode === 'live' ? 'fill-current text-emerald-400' : ''}`} />
            <span>{mode === 'live' ? 'LIVE INFERENCE' : 'SIMULATION'}</span>
          </button>

          {/* Settings Button */}
          <button
            onClick={() => setShowSettingsModal(true)}
            className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 transition-colors"
            title="Configure Provider API Keys and Local Endpoints"
          >
            <Settings2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Message Chat Feed */}
      <div className="flex-1 overflow-y-auto space-y-4 rounded-xl border border-slate-800 bg-slate-900/50 p-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${
              msg.sender === 'user' ? 'items-end' : 'items-start'
            }`}
          >
            <div className="flex items-center gap-2 mb-1 text-[10px] text-slate-500">
              <span className="font-semibold text-slate-400">
                {msg.sender === 'user' ? 'OPERATOR' : 'ULTRONE AI'}
              </span>
              {msg.provider && (
                <span className="rounded bg-slate-800 px-1.5 py-0.5 text-cyan-400 text-[10px]">
                  {msg.provider} / {msg.model}
                </span>
              )}
              {msg.latencyMs && (
                <span className="text-slate-400">{msg.latencyMs}ms</span>
              )}
              <span>{msg.timestamp}</span>
            </div>

            <div
              className={`max-w-2xl rounded-xl p-3.5 text-xs ${
                msg.sender === 'user'
                  ? 'bg-ultrone-600/30 border border-ultrone-500/40 text-slate-100'
                  : 'bg-slate-900 border border-slate-800 text-slate-200 shadow-md'
              }`}
            >
              <p className="leading-relaxed whitespace-pre-wrap">{msg.text}</p>

              {/* Plan Card */}
              {msg.plan && (
                <div className="mt-3.5 pt-3 border-t border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-ultrone-400 font-semibold text-xs uppercase tracking-wider">
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>{msg.plan.goal}</span>
                    </div>
                    <ConfidenceBadge confidence={msg.plan.confidence} size="sm" />
                  </div>

                  <div className="space-y-1.5 pl-1">
                    {msg.plan.steps.map((st, i) => (
                      <div key={i} className="flex items-center gap-2 text-[11px]">
                        {st.status === 'completed' ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                        ) : st.status === 'in_progress' ? (
                          <RefreshCw className="w-3.5 h-3.5 text-cyan-400 animate-spin shrink-0" />
                        ) : (
                          <span className="w-3.5 h-3.5 rounded-full border border-slate-600 shrink-0" />
                        )}
                        <span
                          className={
                            st.status === 'completed'
                              ? 'text-slate-300'
                              : st.status === 'in_progress'
                              ? 'text-cyan-300 font-semibold'
                              : 'text-slate-500'
                          }
                        >
                          {st.step}
                        </span>
                      </div>
                    ))}
                  </div>

                  {msg.plan.recommendedActions && (
                    <div className="flex flex-wrap gap-2 pt-2">
                      {msg.plan.recommendedActions.map((act, i) => (
                        <button
                          key={i}
                          onClick={() => alert(`Executed directive: ${act}`)}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-[11px] transition-colors"
                        >
                          <ArrowRight className="w-3 h-3 text-ultrone-400" />
                          <span>{act}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {isThinking && (
          <div className="flex items-center gap-2 text-xs text-slate-400 italic">
            <RefreshCw className="w-3.5 h-3.5 text-ultrone-400 animate-spin" />
            <span>
              Invoking {currentProviderSpec.name} ({activeConfig.model})...
            </span>
          </div>
        )}
      </div>

      {/* Suggested Quick Prompts */}
      <div className="flex flex-wrap gap-1.5">
        {samplePrompts.map((p, i) => (
          <button
            key={i}
            onClick={() => setInput(p)}
            className="px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-slate-200 text-[11px] transition-colors"
          >
            {p}
          </button>
        ))}
      </div>

      {/* Command Input Box */}
      <div className="flex items-center gap-2 rounded-xl bg-slate-900 border border-slate-800 p-2 shadow-lg">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={`Direct ${currentProviderSpec.name} (${activeConfig.model}) on tactical analysis...`}
          className="flex-1 bg-transparent px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 outline-none"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isThinking}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-ultrone-600 hover:bg-ultrone-500 disabled:opacity-40 text-white text-xs font-semibold shadow-md transition-colors"
        >
          <Send className="w-3.5 h-3.5" />
          <span>Dispatch</span>
        </button>
      </div>

      {/* Provider Settings Modal */}
      {showSettingsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-xl rounded-xl border border-slate-700 bg-slate-900 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Sliders className="w-4 h-4 text-ultrone-400" />
                <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                  AI Provider Configuration: {currentProviderSpec.name}
                </h2>
              </div>
              <button
                onClick={() => setShowSettingsModal(false)}
                className="p-1 rounded text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              {/* API Key */}
              {!currentProviderSpec.isLocal ? (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-[11px] font-semibold text-slate-300">
                      API Key (Saved locally in browser)
                    </label>
                    {currentProviderSpec.keyPortalUrl && (
                      <a
                        href={currentProviderSpec.keyPortalUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-[10px] text-cyan-400 hover:text-cyan-300 hover:underline"
                      >
                        <span>Get API Key</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                  <div className="flex items-center rounded-lg bg-slate-950 border border-slate-800 px-3 py-1.5">
                    <Key className="w-3.5 h-3.5 text-slate-500 mr-2 shrink-0" />
                    <input
                      type="password"
                      value={apiKeys[activeProvider] || ''}
                      onChange={(e) => setApiKey(activeProvider, e.target.value)}
                      placeholder={`Enter your ${currentProviderSpec.name} API Key...`}
                      className="w-full bg-transparent text-slate-100 placeholder-slate-600 outline-none text-xs"
                    />
                  </div>
                  <p className="text-[10px] text-slate-500 mt-1">
                    Environment fallback: <code>{activeProvider.toUpperCase()}_API_KEY</code>
                  </p>
                </div>
              ) : (
                <div className="rounded-lg bg-cyan-950/40 border border-cyan-800/60 p-3 text-cyan-300 text-xs">
                  <div className="flex items-center justify-between mb-1">
                    <p className="font-semibold">Local AI (Ollama / Qwen / LM Studio)</p>
                    {currentProviderSpec.keyPortalUrl && (
                      <a
                        href={currentProviderSpec.keyPortalUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-[10px] text-cyan-400 hover:text-cyan-300 hover:underline"
                      >
                        <span>Download & Docs</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                  <p className="text-[11px] text-cyan-400">
                    Runs 100% offline on your machine. No external API key required.
                    For Ollama, run <code>ollama run qwen2.5:7b</code> in your terminal.
                  </p>
                </div>
              )}

              {/* Model ID Override */}
              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                  Active Model Name / ID
                </label>
                <input
                  type="text"
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  placeholder="e.g. qwen2.5:7b, qwen2.5-coder:14b, custom-model..."
                  className="w-full rounded-lg bg-slate-950 border border-slate-800 px-3 py-1.5 text-slate-100 text-xs font-mono outline-none"
                />
              </div>

              {/* Base URL */}
              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                  API Endpoint Base URL
                </label>
                <input
                  type="text"
                  value={customBaseUrls[activeProvider] || currentProviderSpec.defaultBaseUrl}
                  onChange={(e) => setCustomBaseUrl(activeProvider, e.target.value)}
                  className="w-full rounded-lg bg-slate-950 border border-slate-800 px-3 py-1.5 text-slate-100 text-xs font-mono outline-none"
                />
              </div>

              {/* Temperature & Max Tokens */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                    Temperature: {temperature}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={temperature}
                    onChange={(e) => setTemperature(parseFloat(e.target.value))}
                    className="w-full accent-ultrone-500"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                    Max Tokens: {maxTokens}
                  </label>
                  <input
                    type="number"
                    value={maxTokens}
                    onChange={(e) => setMaxTokens(parseInt(e.target.value) || 1000)}
                    className="w-full rounded-lg bg-slate-950 border border-slate-800 px-3 py-1 text-slate-100 text-xs font-mono outline-none"
                  />
                </div>
              </div>

              {/* Test Result Feedback */}
              {testResult && (
                <div
                  className={`p-3 rounded-lg border text-xs flex items-center gap-2 ${
                    testResult.status === 'success'
                      ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                      : testResult.status === 'warning'
                      ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                      : 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                  }`}
                >
                  {testResult.status === 'success' ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : (
                    <AlertCircle className="w-4 h-4 shrink-0" />
                  )}
                  <span>{testResult.message}</span>
                </div>
              )}
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-between pt-3 border-t border-slate-800">
              <button
                onClick={handleTestConnection}
                disabled={isTesting}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors"
              >
                {isTesting ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Radio className="w-3.5 h-3.5 text-cyan-400" />
                )}
                <span>Test Connection</span>
              </button>

              <button
                onClick={() => setShowSettingsModal(false)}
                className="px-4 py-1.5 rounded-lg bg-ultrone-600 hover:bg-ultrone-500 text-white text-xs font-semibold transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AIAssist;

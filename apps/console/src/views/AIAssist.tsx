import React, { useState } from 'react';
import { useWorldStore } from '../store/worldStore';
import ConfidenceBadge from '../components/ConfidenceBadge';
import {
  Bot,
  Send,
  Sparkles,
  CheckCircle2,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';

interface AIMessage {
  id: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  text: string;
  plan?: {
    goal: string;
    steps: { step: string; status: 'completed' | 'in_progress' | 'pending' }[];
    confidence: number;
    recommendedActions?: string[];
  };
}

export const AIAssist: React.FC = () => {
  const entities = useWorldStore((s) => s.entities);

  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<AIMessage[]>([
    {
      id: 'msg-1',
      sender: 'assistant',
      timestamp: '12:40:10',
      text: 'ULTRONE Cognitive Copilot online. Integrated with 15-layer reasoning pipeline, situational awareness world model, and autonomous decision gates. How can I assist your operational overview today?',
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
      text: 'Sector Alpha threat analysis complete. Evaluated 5 active entities and 3 sensor baselines using Bayesian risk estimation and predictive kill-chain forecasting.',
      plan: {
        goal: 'Optimize sensor coverage and mitigate potential radar shadows in northern sector',
        confidence: 0.93,
        steps: [
          { step: 'Cross-correlate radar-01 and eo-02 observations for entity_001', status: 'completed' },
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

  const [isThinking, setIsThinking] = useState(false);

  const handleSend = () => {
    if (!input.trim()) return;

    const userMsg: AIMessage = {
      id: `usr-${Date.now()}`,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString([], { hour12: false }),
      text: input,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsThinking(true);

    setTimeout(() => {
      const botMsg: AIMessage = {
        id: `bot-${Date.now()}`,
        sender: 'assistant',
        timestamp: new Date().toLocaleTimeString([], { hour12: false }),
        text: `Synthesized operational analysis for query: "${userMsg.text}". Evaluated against current world state (${entities.length} entities tracked).`,
        plan: {
          goal: 'Automated COA generation & Multi-Agent Constraint Verification',
          confidence: 0.91,
          steps: [
            { step: 'Ingest active sensor fusion contacts from world model', status: 'completed' },
            { step: 'Execute Bayesian uncertainty estimation & safety constraints check', status: 'completed' },
            { step: 'Evaluate candidate courses of action against operational invariants', status: 'in_progress' },
          ],
          recommendedActions: [
            'Approve Proposed Course of Action (COA-03)',
            'Export Decision Trace to Research DB',
          ],
        },
      };
      setMessages((prev) => [...prev, botMsg]);
      setIsThinking(false);
    }, 1200);
  };

  const samplePrompts = [
    'Assess threat level of entity_001',
    'Calculate optimal radar coverage perimeter',
    'Evaluate safety gate constraints on engagement',
    'Forecast target trajectory under Markov predictor',
  ];

  return (
    <div className="flex h-full w-full flex-col bg-slate-950 p-6 overflow-hidden space-y-4 font-mono">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-ultrone-600/20 border border-ultrone-500/40 text-ultrone-400">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-wider text-slate-100 uppercase">
              ULTRONE Cognitive AI Assist
            </h1>
            <p className="text-xs text-slate-400">
              Autonomous reasoning copilot • 15-layer cognitive architecture • HITL safety compliant
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            REASONER: ONLINE
          </span>
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
              <span>{msg.sender === 'user' ? 'OPERATOR' : 'ULTRONE CORE'}</span>
              <span>{msg.timestamp}</span>
            </div>

            <div
              className={`max-w-2xl rounded-xl p-3.5 text-xs ${
                msg.sender === 'user'
                  ? 'bg-ultrone-600/30 border border-ultrone-500/40 text-slate-100'
                  : 'bg-slate-900 border border-slate-800 text-slate-200 shadow-md'
              }`}
            >
              <p className="leading-relaxed">{msg.text}</p>

              {/* Plan Card if provided */}
              {msg.plan && (
                <div className="mt-3.5 pt-3 border-t border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-ultrone-400 font-semibold text-xs uppercase tracking-wider">
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>{msg.plan.goal}</span>
                    </div>
                    <ConfidenceBadge confidence={msg.plan.confidence} size="sm" />
                  </div>

                  {/* Plan Steps */}
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

                  {/* Recommended Action Buttons */}
                  {msg.plan.recommendedActions && (
                    <div className="flex flex-wrap gap-2 pt-2">
                      {msg.plan.recommendedActions.map((act, i) => (
                        <button
                          key={i}
                          onClick={() => alert(`Executed directive: ${act}`)}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-750 text-slate-200 border border-slate-700 text-[11px] transition-colors"
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
            <span>Reasoning through cognitive layers & safety constraints...</span>
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

      {/* Input Area */}
      <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 p-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask ULTRONE Copilot for tactical analysis, mission plans, or telemetry queries..."
          className="flex-1 bg-transparent px-2 text-xs text-slate-100 placeholder-slate-500 outline-none"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim()}
          className="flex items-center gap-1.5 rounded-lg bg-ultrone-600 hover:bg-ultrone-500 disabled:opacity-50 text-white px-4 py-2 text-xs font-semibold transition-colors"
        >
          <Send className="w-3.5 h-3.5" />
          <span>Dispatch</span>
        </button>
      </div>
    </div>
  );
};

export default AIAssist;

/**
 * ULTRONE Research Platform Dashboard
 * TypeScript React component for the autonomous research platform.
 *
 * Features:
 * - Research paper browser
 * - Experiment tracker
 * - Knowledge graph viewer
 * - Agent monitoring
 * - Live telemetry
 * - Self-improvement status
 */

import React, { useState, useEffect } from 'react';

interface Paper {
  paper_id: string;
  title: string;
  authors: string[];
  venue: string;
  summary: string;
  algorithms: string[];
  confidence_score: number;
}

interface Experiment {
  experiment_id: string;
  hypothesis: string;
  status: string;
  recommendation: string;
  evaluation_metrics: Record<string, number>;
}

interface AgentStats {
  agent_id: string;
  role: string;
  actions_taken: number;
  log_entries: number;
}

interface PlatformStats {
  knowledge_engine: Record<string, unknown>;
  research_db: Record<string, unknown>;
  self_improvement: Record<string, unknown>;
}

const ResearchPlatformPage: React.FC = () => {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [agents, setAgents] = useState<AgentStats[]>([]);
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [activeTab, setActiveTab] = useState<'papers' | 'experiments' | 'agents' | 'knowledge' | 'improvements'>('papers');

  useEffect(() => {
    // Fetch data from the research platform API
    fetchPapers();
    fetchExperiments();
    fetchStats();
  }, []);

  const fetchPapers = async () => {
    try {
      const response = await fetch('/api/v1/research/papers');
      if (response.ok) {
        const data = await response.json();
        setPapers(data);
      }
    } catch (error) {
      console.error('Failed to fetch papers:', error);
    }
  };

  const fetchExperiments = async () => {
    try {
      const response = await fetch('/api/v1/research/experiments');
      if (response.ok) {
        const data = await response.json();
        setExperiments(data);
      }
    } catch (error) {
      console.error('Failed to fetch experiments:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const [researchRes, knowledgeRes, impRes] = await Promise.all([
        fetch('/api/v1/research/stats'),
        fetch('/api/v1/knowledge/stats'),
        fetch('/api/v1/improvements/stats'),
      ]);
      const [research, knowledge, improvements] = await Promise.all([
        researchRes.json(),
        knowledgeRes.json(),
        impRes.json(),
      ]);
      setStats({ knowledge_engine: knowledge, research_db: research, self_improvement: improvements });
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const runImprovementCycle = async () => {
    try {
      await fetch('/api/v1/improvements/run-cycle', { method: 'POST' });
      fetchStats();
    } catch (error) {
      console.error('Failed to run improvement cycle:', error);
    }
  };

  return (
    <div className="research-platform-page">
      <div className="page-header">
        <h1>ULTRONE Research Platform</h1>
        <button onClick={runImprovementCycle} className="btn-primary">
          Run Improvement Cycle
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="tab-nav">
        <button
          className={activeTab === 'papers' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('papers')}
        >
          Papers ({papers.length})
        </button>
        <button
          className={activeTab === 'experiments' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('experiments')}
        >
          Experiments ({experiments.length})
        </button>
        <button
          className={activeTab === 'agents' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('agents')}
        >
          Agents
        </button>
        <button
          className={activeTab === 'knowledge' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('knowledge')}
        >
          Knowledge Engine
        </button>
        <button
          className={activeTab === 'improvements' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('improvements')}
        >
          Self-Improvement
        </button>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'papers' && (
          <div className="papers-list">
            {papers.length === 0 ? (
              <p>No papers discovered yet. Run the research scout to discover papers.</p>
            ) : (
              papers.map((paper) => (
                <div key={paper.paper_id} className="paper-card">
                  <h3>{paper.title}</h3>
                  <p className="authors">{paper.authors.join(', ')}</p>
                  <p className="venue">{paper.venue}</p>
                  {paper.summary && <p className="summary">{paper.summary}</p>}
                  {paper.algorithms.length > 0 && (
                    <div className="algorithms">
                      {paper.algorithms.map((algo) => (
                        <span key={algo} className="tag">{algo}</span>
                      ))}
                    </div>
                  )}
                  <div className="confidence">
                    Confidence: {(paper.confidence_score * 100).toFixed(0)}%
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'experiments' && (
          <div className="experiments-list">
            {experiments.length === 0 ? (
              <p>No experiments yet.</p>
            ) : (
              experiments.map((exp) => (
                <div key={exp.experiment_id} className="experiment-card">
                  <h3>{exp.hypothesis}</h3>
                  <span className={`status status-${exp.status}`}>{exp.status}</span>
                  {exp.recommendation && (
                    <span className={`recommendation rec-${exp.recommendation}`}>
                      {exp.recommendation}
                    </span>
                  )}
                  {Object.keys(exp.evaluation_metrics).length > 0 && (
                    <div className="metrics">
                      {Object.entries(exp.evaluation_metrics).map(([key, value]) => (
                        <div key={key} className="metric">
                          <span className="metric-name">{key}:</span>
                          <span className="metric-value">{value}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'agents' && (
          <div className="agents-grid">
            {agents.length === 0 ? (
              <p>Agent monitoring will appear here when the research division is running.</p>
            ) : (
              agents.map((agent) => (
                <div key={agent.agent_id} className="agent-card">
                  <h4>{agent.role}</h4>
                  <p>ID: {agent.agent_id}</p>
                  <p>Actions: {agent.actions_taken}</p>
                  <p>Log entries: {agent.log_entries}</p>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'knowledge' && stats && (
          <div className="knowledge-stats">
            <pre>{JSON.stringify(stats.knowledge_engine, null, 2)}</pre>
          </div>
        )}

        {activeTab === 'improvements' && stats && (
          <div className="improvement-stats">
            <pre>{JSON.stringify(stats.self_improvement, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default ResearchPlatformPage;
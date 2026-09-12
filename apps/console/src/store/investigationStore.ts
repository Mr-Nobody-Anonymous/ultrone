import { create } from 'zustand';
import { InvestigationCase, EvidenceItem } from '../types/investigation';

interface InvestigationState {
  cases: InvestigationCase[];
  activeCaseId: string;

  setActiveCase: (caseId: string) => void;
  createCase: (title: string, classification?: InvestigationCase['classification']) => InvestigationCase;
  addEvidenceToActiveCase: (evidence: Omit<EvidenceItem, 'id' | 'addedAt'>) => void;
  pinEntityToActiveCase: (entityId: string) => void;
  unpinEntityFromActiveCase: (entityId: string) => void;
  addAnnotationToActiveCase: (text: string, author?: string) => void;
  updateCaseStatus: (caseId: string, status: InvestigationCase['status']) => void;
  getActiveCase: () => InvestigationCase | undefined;
}

const INITIAL_CASES: InvestigationCase[] = [
  {
    id: 'INV-1042',
    title: 'Correlated Sensor Anomaly in Sector Alpha',
    classification: 'CONFIDENTIAL',
    status: 'active',
    leadAnalyst: 'Lead Analyst Vance',
    createdAt: new Date(Date.now() - 3600000 * 5).toISOString(),
    updatedAt: new Date(Date.now() - 1800000).toISOString(),
    summary: 'Correlated anomalous SIGINT intercept (entity_002) with radar contact (entity_001) deviating from nominal civilian flight corridors.',
    hypotheses: [
      'H1: Electronic countermeasures (ECM) spoofing sensor fusion radar-01',
      'H2: Unregistered autonomous asset operating in proximity to regional node',
    ],
    pinnedEntities: ['entity_001', 'entity_002'],
    evidence: [
      {
        id: 'ev-01',
        type: 'entity',
        title: 'Air Asset Track Stable',
        description: 'Altitude 8200ft, heading 270 degrees, detected via EO and radar fusion.',
        sourceRef: 'entity_001',
        confidence: 0.95,
        addedAt: new Date(Date.now() - 3600000 * 2).toISOString(),
      },
      {
        id: 'ev-02',
        type: 'event',
        title: 'SIGINT Intercept Spike',
        description: 'Voice and telemetry bursts on 225.5MHz band concurrent with trajectory turn.',
        sourceRef: 'entity_002',
        confidence: 0.85,
        addedAt: new Date(Date.now() - 3600000).toISOString(),
      },
      {
        id: 'ev-03',
        type: 'ai_trace',
        title: 'Bayesian Trajectory Anomaly Score: 0.73',
        description: 'Synthesized under 15-layer cognitive loop. Marked critical by HITL policy gate.',
        sourceRef: 'cognitive_loop',
        confidence: 0.88,
        addedAt: new Date(Date.now() - 1800000).toISOString(),
      },
    ],
    annotations: [
      {
        id: 'ann-1',
        author: 'Lead Analyst Vance',
        text: 'Confirm radar-01 calibration status before escalating to command loop.',
        timestamp: '12:44:10',
      },
    ],
  },
  {
    id: 'INV-1043',
    title: 'Communication Node Jamming & Signal Degradation',
    classification: 'SECRET',
    status: 'in_review',
    leadAnalyst: 'Analyst Chen',
    createdAt: new Date(Date.now() - 86400000).toISOString(),
    updatedAt: new Date(Date.now() - 3600000 * 8).toISOString(),
    summary: 'Investigation into degraded link margin between entity_004 and regional gateway.',
    hypotheses: ['H1: Atmospheric thermal ducting', 'H2: Directed carrier RF interference'],
    pinnedEntities: ['entity_004'],
    evidence: [],
    annotations: [],
  },
];

export const useInvestigationStore = create<InvestigationState>((set, get) => ({
  cases: INITIAL_CASES,
  activeCaseId: 'INV-1042',

  setActiveCase: (caseId) => set({ activeCaseId: caseId }),

  createCase: (title, classification = 'CONFIDENTIAL') => {
    const newCase: InvestigationCase = {
      id: `INV-${Math.floor(1000 + Math.random() * 9000)}`,
      title,
      classification,
      status: 'active',
      leadAnalyst: 'Current Operator',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      summary: 'New operational investigation opened.',
      hypotheses: [],
      pinnedEntities: [],
      evidence: [],
      annotations: [],
    };
    set((s) => ({ cases: [newCase, ...s.cases], activeCaseId: newCase.id }));
    return newCase;
  },

  addEvidenceToActiveCase: (evidence) => {
    const item: EvidenceItem = {
      ...evidence,
      id: `ev-${Date.now().toString(36)}`,
      addedAt: new Date().toISOString(),
    };
    set((s) => ({
      cases: s.cases.map((c) =>
        c.id === s.activeCaseId
          ? { ...c, evidence: [item, ...c.evidence], updatedAt: new Date().toISOString() }
          : c,
      ),
    }));
  },

  pinEntityToActiveCase: (entityId) => {
    set((s) => ({
      cases: s.cases.map((c) => {
        if (c.id !== s.activeCaseId) return c;
        if (c.pinnedEntities.includes(entityId)) return c;
        return {
          ...c,
          pinnedEntities: [...c.pinnedEntities, entityId],
          updatedAt: new Date().toISOString(),
        };
      }),
    }));
  },

  unpinEntityFromActiveCase: (entityId) => {
    set((s) => ({
      cases: s.cases.map((c) =>
        c.id === s.activeCaseId
          ? {
              ...c,
              pinnedEntities: c.pinnedEntities.filter((id) => id !== entityId),
              updatedAt: new Date().toISOString(),
            }
          : c,
      ),
    }));
  },

  addAnnotationToActiveCase: (text, author = 'Current Operator') => {
    const ann = {
      id: `ann-${Date.now()}`,
      author,
      text,
      timestamp: new Date().toLocaleTimeString([], { hour12: false }),
    };
    set((s) => ({
      cases: s.cases.map((c) =>
        c.id === s.activeCaseId
          ? { ...c, annotations: [...c.annotations, ann], updatedAt: new Date().toISOString() }
          : c,
      ),
    }));
  },

  updateCaseStatus: (caseId, status) => {
    set((s) => ({
      cases: s.cases.map((c) => (c.id === caseId ? { ...c, status, updatedAt: new Date().toISOString() } : c)),
    }));
  },

  getActiveCase: () => {
    const state = get();
    return state.cases.find((c) => c.id === state.activeCaseId) || state.cases[0];
  },
}));

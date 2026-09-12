export interface EvidenceItem {
  id: string;
  type: 'entity' | 'event' | 'telemetry' | 'ai_trace' | 'note';
  title: string;
  description: string;
  sourceRef: string;
  confidence: number;
  addedAt: string;
  payload?: any;
}

export interface InvestigationCase {
  id: string;
  title: string;
  classification: 'UNCLASSIFIED' | 'CONFIDENTIAL' | 'SECRET' | 'TOP SECRET';
  status: 'active' | 'in_review' | 'closed';
  leadAnalyst: string;
  createdAt: string;
  updatedAt: string;
  summary: string;
  hypotheses: string[];
  pinnedEntities: string[];
  evidence: EvidenceItem[];
  annotations: { id: string; author: string; text: string; timestamp: string }[];
}

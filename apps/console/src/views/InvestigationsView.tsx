import React, { useState } from 'react';
import { useInvestigationStore } from '../store/investigationStore';
import { useWorldStore } from '../store/worldStore';
import ConfidenceBadge from '../components/ConfidenceBadge';
import {
  FolderLock,
  Plus,
  Pin,
  MessageSquare,
  Download,
  Trash2,
  Calendar,
  User,
  Shield,
} from 'lucide-react';

export const InvestigationsView: React.FC = () => {
  const {
    cases,
    activeCaseId,
    setActiveCase,
    createCase,
    unpinEntityFromActiveCase,
    addAnnotationToActiveCase,
    getActiveCase,
  } = useInvestigationStore();

  const entities = useWorldStore((s) => s.entities);
  const selectEntity = useWorldStore((s) => s.selectEntity);

  const [newAnnotation, setNewAnnotation] = useState('');
  const [showNewCaseModal, setShowNewCaseModal] = useState(false);
  const [newCaseTitle, setNewCaseTitle] = useState('');
  const [newCaseClass, setNewCaseClass] = useState<'CONFIDENTIAL' | 'SECRET'>('CONFIDENTIAL');

  const activeCase = getActiveCase();

  const handleAddAnnotation = () => {
    if (!newAnnotation.trim()) return;
    addAnnotationToActiveCase(newAnnotation);
    setNewAnnotation('');
  };

  const handleExportReport = () => {
    if (!activeCase) return;
    const reportText = [
      `========================================================================`,
      `ULTRONE INTELLIGENCE INVESTIGATION DOSSIER`,
      `CASE ID: ${activeCase.id} — ${activeCase.title}`,
      `CLASSIFICATION: ${activeCase.classification} | STATUS: ${activeCase.status.toUpperCase()}`,
      `LEAD ANALYST: ${activeCase.leadAnalyst}`,
      `CREATED: ${activeCase.createdAt} | UPDATED: ${activeCase.updatedAt}`,
      `========================================================================\n`,
      `EXECUTIVE SUMMARY:`,
      activeCase.summary,
      `\nHYPOTHESES:`,
      activeCase.hypotheses.map((h, i) => `  ${i + 1}. ${h}`).join('\n'),
      `\nPINNED ENTITY CONTACTS (${activeCase.pinnedEntities.length}):`,
      activeCase.pinnedEntities.map((e) => `  - Entity ID: ${e}`).join('\n'),
      `\nCOLLECTED EVIDENCE (${activeCase.evidence.length} ITEMS):`,
      activeCase.evidence
        .map((ev) => `  [${ev.type.toUpperCase()}] ${ev.title} (Conf: ${ev.confidence * 100}%)\n    Details: ${ev.description}\n    Ref: ${ev.sourceRef}`)
        .join('\n\n'),
      `\nANALYST LOG & ANNOTATIONS:`,
      activeCase.annotations.map((a) => `  [${a.timestamp}] ${a.author}: ${a.text}`).join('\n'),
      `\n========================================================================`,
      `END OF DOSSIER — AUDIT HASH: SHA256-${activeCase.id.toLowerCase()}-verified`,
    ].join('\n');

    const blob = new Blob([reportText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${activeCase.id}_investigation_dossier.txt`;
    a.click();
  };

  return (
    <div className="flex h-full w-full flex-col bg-slate-950 p-6 overflow-hidden space-y-4 font-mono select-none text-xs">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-400 shadow-md">
            <FolderLock className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-wider text-slate-100 uppercase flex items-center gap-2">
              Intelligence Investigations
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-normal">
                {cases.length} Open Cases
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              Correlate entities, timeline evidence, AI inference findings, and human-in-the-loop annotations
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowNewCaseModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-ultrone-600 hover:bg-ultrone-500 text-white font-semibold transition-colors shadow-md"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Case</span>
          </button>
          <button
            onClick={handleExportReport}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-cyan-400" />
            <span>Export Dossier</span>
          </button>
        </div>
      </div>

      {/* Main Investigation Canvas */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-4 overflow-hidden">
        {/* Col 1: Case Selector Bar */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-3 space-y-2 overflow-y-auto">
          <span className="text-[10px] uppercase font-bold text-slate-500 block mb-2">
            Active Dossiers
          </span>
          {cases.map((c) => (
            <div
              key={c.id}
              onClick={() => setActiveCase(c.id)}
              className={`p-3 rounded-lg border cursor-pointer transition-all space-y-1 ${
                activeCaseId === c.id
                  ? 'bg-amber-500/10 border-amber-500/40 text-slate-100 shadow-md'
                  : 'bg-slate-950/60 border-slate-800/80 hover:bg-slate-900 text-slate-400'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-amber-300">{c.id}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                  {c.classification}
                </span>
              </div>
              <p className="font-semibold text-xs text-slate-200 line-clamp-1">{c.title}</p>
              <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1">
                <span>{c.pinnedEntities.length} Pinned</span>
                <span>{c.evidence.length} Evidence</span>
              </div>
            </div>
          ))}
        </div>

        {/* Col 2 & 3: Active Dossier & Evidence Board */}
        <div className="lg:col-span-2 rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-4 overflow-y-auto flex flex-col">
          {activeCase ? (
            <>
              {/* Dossier Header Info */}
              <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-amber-400" />
                    <h2 className="font-bold text-sm text-slate-100">{activeCase.title}</h2>
                  </div>
                  <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold uppercase text-[10px]">
                    {activeCase.status}
                  </span>
                </div>
                <p className="text-slate-400 text-xs leading-relaxed">{activeCase.summary}</p>

                <div className="flex flex-wrap items-center gap-4 text-[11px] text-slate-500 pt-1 border-t border-slate-900">
                  <span className="flex items-center gap-1">
                    <User className="w-3 h-3 text-slate-400" /> Lead: {activeCase.leadAnalyst}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3 text-slate-400" /> Updated: {new Date(activeCase.updatedAt).toLocaleTimeString()}
                  </span>
                </div>
              </div>

              {/* Pinned Contacts Strip */}
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block mb-2 flex items-center gap-1.5">
                  <Pin className="w-3 h-3 text-cyan-400" />
                  Pinned Contacts of Interest ({activeCase.pinnedEntities.length})
                </span>
                <div className="grid grid-cols-2 gap-2">
                  {activeCase.pinnedEntities.map((entId) => {
                    const ent = entities.find((e) => e.entity_id === entId);
                    return (
                      <div
                        key={entId}
                        className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between"
                      >
                        <div
                          onClick={() => ent && selectEntity(ent)}
                          className="cursor-pointer space-y-0.5"
                        >
                          <span className="font-bold text-cyan-300 block">{entId}</span>
                          <span className="text-[10px] text-slate-500">{ent?.type || 'Contact'}</span>
                        </div>
                        <button
                          onClick={() => unpinEntityFromActiveCase(entId)}
                          className="p-1 rounded text-slate-600 hover:text-rose-400"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    );
                  })}
                  {activeCase.pinnedEntities.length === 0 && (
                    <p className="text-slate-500 text-[11px]">No contacts pinned. Use Entity Inspector or World View to pin contacts.</p>
                  )}
                </div>
              </div>

              {/* Evidence Collection Items */}
              <div className="flex-1 space-y-2">
                <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                  Correlated Evidence ({activeCase.evidence.length})
                </span>
                {activeCase.evidence.map((ev) => (
                  <div
                    key={ev.id}
                    className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] px-1.5 py-0.2 bg-slate-800 text-amber-300 uppercase rounded font-semibold">
                          {ev.type}
                        </span>
                        <span className="font-bold text-slate-200">{ev.title}</span>
                      </div>
                      <ConfidenceBadge confidence={ev.confidence} size="sm" />
                    </div>
                    <p className="text-slate-300 text-xs">{ev.description}</p>
                    <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1">
                      <span>Source Ref: <code className="text-slate-400">{ev.sourceRef}</code></span>
                      <span>{new Date(ev.addedAt).toLocaleTimeString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="flex h-full items-center justify-center text-slate-500">
              Select or create a case to view dossier details.
            </div>
          )}
        </div>

        {/* Col 4: Hypotheses & Operator Annotations */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-4 overflow-y-auto flex flex-col">
          {/* Hypotheses */}
          <div className="space-y-2">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">
              Investigative Hypotheses
            </span>
            {activeCase?.hypotheses.map((h, i) => (
              <div
                key={i}
                className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 text-[11px] leading-relaxed"
              >
                {h}
              </div>
            )) || <p className="text-slate-500">None formulated.</p>}
          </div>

          {/* Annotations Log */}
          <div className="flex-1 space-y-2">
            <span className="text-[10px] uppercase font-bold text-slate-400 block flex items-center gap-1.5">
              <MessageSquare className="w-3 h-3 text-ultrone-400" />
              Analyst Notes ({activeCase?.annotations.length || 0})
            </span>
            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {activeCase?.annotations.map((ann) => (
                <div
                  key={ann.id}
                  className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 space-y-1"
                >
                  <div className="flex items-center justify-between text-[10px] text-slate-500">
                    <span className="font-bold text-slate-400">{ann.author}</span>
                    <span>{ann.timestamp}</span>
                  </div>
                  <p className="text-slate-200 text-xs">{ann.text}</p>
                </div>
              ))}
            </div>
          </div>

          {/* New Annotation Input */}
          <div className="pt-2 border-t border-slate-800 space-y-2">
            <textarea
              value={newAnnotation}
              onChange={(e) => setNewAnnotation(e.target.value)}
              placeholder="Record analytical observation or hypothesis..."
              className="w-full h-16 rounded-lg bg-slate-950 border border-slate-800 p-2 text-xs text-slate-100 placeholder-slate-600 outline-none resize-none"
            />
            <button
              onClick={handleAddAnnotation}
              disabled={!newAnnotation.trim()}
              className="w-full py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 font-semibold text-xs transition-colors"
            >
              Add Note to Case
            </button>
          </div>
        </div>
      </div>

      {/* New Case Modal */}
      {showNewCaseModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-5 space-y-4 shadow-2xl">
            <h2 className="font-bold text-slate-100 uppercase tracking-wider text-sm">
              Open New Investigation Dossier
            </h2>
            <div className="space-y-3">
              <div>
                <label className="text-[11px] text-slate-400 block mb-1">Case Title</label>
                <input
                  type="text"
                  value={newCaseTitle}
                  onChange={(e) => setNewCaseTitle(e.target.value)}
                  placeholder="e.g. Uncorrelated Radar Track near Gateway..."
                  className="w-full rounded-lg bg-slate-950 border border-slate-800 px-3 py-1.5 text-xs text-slate-100 outline-none"
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-400 block mb-1">Classification</label>
                <select
                  value={newCaseClass}
                  onChange={(e) => setNewCaseClass(e.target.value as any)}
                  className="w-full rounded-lg bg-slate-950 border border-slate-800 px-3 py-1.5 text-xs text-slate-100 outline-none"
                >
                  <option value="CONFIDENTIAL">CONFIDENTIAL</option>
                  <option value="SECRET">SECRET</option>
                </select>
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                onClick={() => setShowNewCaseModal(false)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 text-xs"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (newCaseTitle.trim()) {
                    createCase(newCaseTitle, newCaseClass);
                    setNewCaseTitle('');
                    setShowNewCaseModal(false);
                  }
                }}
                className="px-4 py-1.5 rounded-lg bg-ultrone-600 text-white font-semibold text-xs hover:bg-ultrone-500"
              >
                Create Case
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default InvestigationsView;

import React, { useState, useEffect, useRef } from 'react';
import { Search, Terminal, Sparkles, X, ArrowRight, CornerDownLeft } from 'lucide-react';
import { useWorldStore } from '../store/worldStore';
import { useNavigate } from 'react-router-dom';

export const CommandBar: React.FC = () => {
  const [input, setInput] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const entities = useWorldStore((s) => s.entities);
  const selectEntity = useWorldStore((s) => s.selectEntity);
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  // Global keydown handler for Cmd+K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Filter entities based on input
  const filteredEntities = input.trim()
    ? entities.filter(
        (e) =>
          e.entity_id.toLowerCase().includes(input.toLowerCase()) ||
          e.type.toLowerCase().includes(input.toLowerCase()) ||
          e.status.toLowerCase().includes(input.toLowerCase())
      )
    : entities.slice(0, 4);

  const handleSelect = (entityId: string) => {
    const ent = entities.find((e) => e.entity_id === entityId);
    if (ent) {
      selectEntity(ent);
      setIsOpen(false);
      setInput('');
    }
  };

  const QUICK_COMMANDS = [
    { label: 'View World Map', action: () => { navigate('/'); setIsOpen(false); } },
    { label: 'Inspect Entities Table', action: () => { navigate('/entities'); setIsOpen(false); } },
    { label: 'Open Event Feed', action: () => { navigate('/events'); setIsOpen(false); } },
    { label: 'Open AI Assistant', action: () => { navigate('/assist'); setIsOpen(false); } },
    { label: 'Run 3D Tactical Simulation', action: () => { navigate('/simulation'); setIsOpen(false); } },
  ];

  return (
    <>
      {/* Bottom bar dock */}
      <footer className="flex h-10 shrink-0 items-center justify-between border-t border-slate-800 bg-slate-900/90 px-4 z-10">
        <div
          onClick={() => setIsOpen(true)}
          className="flex flex-1 items-center gap-2.5 cursor-pointer max-w-xl rounded-md bg-slate-950/60 border border-slate-800 px-3 py-1 hover:border-slate-700 transition-colors"
        >
          <Search className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-xs text-slate-400 flex-1 truncate">
            Search entities, coordinates, commands, or ask ULTRONE...
          </span>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-400 border border-slate-700/60">
            <span>Ctrl</span><span>K</span>
          </kbd>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 text-slate-400 font-mono text-[11px]">
            <Sparkles className="w-3.5 h-3.5 text-ultrone-400" />
            <span className="hidden sm:inline">AI COPILOT READY</span>
          </div>
          <span className="h-3 w-px bg-slate-800" />
          <div className="flex items-center gap-1.5 text-emerald-400 font-mono text-[11px]">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" />
            LIVE LINK
          </div>
        </div>
      </footer>

      {/* Command Palette Modal */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl rounded-xl border border-slate-700/80 bg-slate-900 shadow-2xl shadow-black/80 overflow-hidden flex flex-col">
            {/* Input Header */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-800">
              <Terminal className="w-4 h-4 text-ultrone-400" />
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type a command, entity ID, or query..."
                className="flex-1 bg-transparent text-sm text-slate-100 placeholder-slate-500 outline-none"
              />
              {input && (
                <button
                  onClick={() => setInput('')}
                  className="p-1 text-slate-500 hover:text-slate-300 rounded"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
              <button
                onClick={() => setIsOpen(false)}
                className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-400 hover:bg-slate-700"
              >
                Esc
              </button>
            </div>

            {/* Content Results */}
            <div className="max-h-96 overflow-y-auto p-3 space-y-4">
              {/* Entity Results */}
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 px-2 block mb-1">
                  Matching Entities ({filteredEntities.length})
                </span>
                <div className="space-y-1">
                  {filteredEntities.map((entity) => (
                    <div
                      key={entity.entity_id}
                      onClick={() => handleSelect(entity.entity_id)}
                      className="flex items-center justify-between p-2 rounded-lg hover:bg-slate-800/80 border border-transparent hover:border-slate-700/60 cursor-pointer transition-colors"
                    >
                      <div className="flex items-center gap-2.5">
                        <span className="font-mono text-xs font-semibold text-ultrone-400">
                          {entity.entity_id}
                        </span>
                        <span className="text-xs text-slate-300 capitalize">
                          {entity.type.replace('_', ' ')}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                          {entity.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
                        <span>{(entity.confidence * 100).toFixed(0)}% conf</span>
                        <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Quick Navigation Commands */}
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 px-2 block mb-1">
                  Quick Navigation
                </span>
                <div className="space-y-1">
                  {QUICK_COMMANDS.map((cmd, idx) => (
                    <div
                      key={idx}
                      onClick={cmd.action}
                      className="flex items-center justify-between p-2 rounded-lg hover:bg-slate-800/80 cursor-pointer text-xs text-slate-300 transition-colors"
                    >
                      <span>{cmd.label}</span>
                      <CornerDownLeft className="w-3.5 h-3.5 text-slate-600" />
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between px-4 py-2 border-t border-slate-800/80 bg-slate-950/60 text-[11px] text-slate-500">
              <span className="font-mono">ULTRONE OPERATIONAL TELEMETRY & COMMAND</span>
              <span>Use ↑↓ to navigate, Enter to select</span>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default CommandBar;

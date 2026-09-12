import type { FC, ReactNode } from 'react';
import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Command, ArrowUpDown, Layout, Zap, Eye, BarChart3, Network, Bot, HelpCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface CommandItem {
  id: string;
  label: string;
  description: string;
  icon: ReactNode;
  action: () => void;
  shortcut?: string;
}

const CommandPalette: FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const commands: CommandItem[] = [
    { id: 'dashboard', label: 'Go to Dashboard', description: 'Open main dashboard', icon: <Layout size={16} />, action: () => navigate('/'), shortcut: '⌘1' },
    { id: 'experiments', label: 'Open Experiments', description: 'View experiment manager', icon: <BarChart3 size={16} />, action: () => navigate('/experiments'), shortcut: '⌘2' },
    { id: 'analytics', label: 'Open Analytics', description: 'View analytics dashboard', icon: <Eye size={16} />, action: () => navigate('/analytics'), shortcut: '⌘3' },
    { id: 'settings', label: 'Open Settings', description: 'Configure ULTRONE', icon: <Zap size={16} />, action: () => navigate('/settings'), shortcut: '⌘4' },
    { id: 'knowledge', label: 'Knowledge Graph', description: 'Explore knowledge graph', icon: <Network size={16} />, action: () => {}, shortcut: '⌘K' },
    { id: 'help', label: 'Help & Documentation', description: 'View documentation', icon: <HelpCircle size={16} />, action: () => {}, shortcut: '⌘H' },
  ];

  const filtered = query
    ? commands.filter(c => c.label.toLowerCase().includes(query.toLowerCase()) || c.description.toLowerCase().includes(query.toLowerCase()))
    : commands;

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(prev => !prev);
      }
      if (e.key === 'Escape') setIsOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  const handleSelect = useCallback((cmd: CommandItem) => {
    cmd.action();
    setIsOpen(false);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(i => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(i => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && filtered[selectedIndex]) {
      handleSelect(filtered[selectedIndex]);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] bg-black/60 backdrop-blur-sm"
          onClick={() => setIsOpen(false)}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0, y: -20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0, y: -20 }}
            transition={{ type: 'spring', stiffness: 400, damping: 30 }}
            className="w-[500px] glass-panel border-surface-700/50 overflow-hidden"
            onClick={e => e.stopPropagation()}
          >
            {/* Search input */}
            <div className="flex items-center gap-3 px-4 h-12 border-b border-surface-700/30">
              <Search size={16} className="text-surface-400 flex-shrink-0" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={e => { setQuery(e.target.value); setSelectedIndex(0); }}
                onKeyDown={handleKeyDown}
                placeholder="Search commands..."
                className="flex-1 bg-transparent text-sm text-surface-100 placeholder-surface-500 outline-none"
              />
              <kbd className="px-1.5 py-0.5 rounded text-xs bg-surface-700 text-surface-400 font-mono">ESC</kbd>
            </div>

            {/* Results */}
            <div className="max-h-64 overflow-y-auto p-2">
              {filtered.map((cmd, i) => (
                <button
                  key={cmd.id}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all ${
                    i === selectedIndex
                      ? 'bg-primary-500/10 text-primary-400 border border-primary-500/20'
                      : 'text-surface-300 hover:bg-surface-800/50 border border-transparent'
                  }`}
                  onClick={() => handleSelect(cmd)}
                  onMouseEnter={() => setSelectedIndex(i)}
                >
                  <span className="flex-shrink-0">{cmd.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{cmd.label}</div>
                    <div className="text-xs text-surface-500 truncate">{cmd.description}</div>
                  </div>
                  {cmd.shortcut && (
                    <kbd className="px-1.5 py-0.5 rounded text-xs bg-surface-700 text-surface-400 font-mono flex-shrink-0">{cmd.shortcut}</kbd>
                  )}
                </button>
              ))}
              {filtered.length === 0 && (
                <div className="text-center py-8 text-surface-500 text-sm">No commands found</div>
              )}
            </div>

            {/* Footer hints */}
            <div className="flex items-center gap-4 px-4 h-9 border-t border-surface-700/30 text-xs text-surface-500">
              <span className="flex items-center gap-1"><ArrowUpDown size={12} /> Navigate</span>
              <span className="flex items-center gap-1"><span className="font-mono">↵</span> Select</span>
              <span className="flex items-center gap-1"><span className="font-mono">Esc</span> Close</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default CommandPalette;

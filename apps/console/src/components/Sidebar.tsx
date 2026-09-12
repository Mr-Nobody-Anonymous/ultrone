import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Globe,
  Layers,
  Activity,
  GitFork,
  Bot,
  Box,
  BarChart3,
  Settings,
  ChevronLeft,
  ChevronRight,
  Zap,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useUIStore } from '../store/uiStore';
import { useWorldStore } from '../store/worldStore';

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
  badge?: string | number;
}

export const Sidebar: React.FC = () => {
  const { sidebarExpanded, toggleSidebar } = useUIStore();
  const entities = useWorldStore((s) => s.entities);
  const events = useWorldStore((s) => s.events);

  const NAV_ITEMS: NavItem[] = [
    { to: '/', label: 'World View', icon: <Globe className="w-4 h-4" /> },
    {
      to: '/entities',
      label: 'Entities',
      icon: <Layers className="w-4 h-4" />,
      badge: entities.length,
    },
    {
      to: '/events',
      label: 'Event Feed',
      icon: <Activity className="w-4 h-4" />,
      badge: events.length,
    },
    { to: '/ontology', label: 'Ontology Graph', icon: <GitFork className="w-4 h-4" /> },
    { to: '/assist', label: 'AI Assist', icon: <Bot className="w-4 h-4" /> },
    { to: '/simulation', label: 'Simulation', icon: <Box className="w-4 h-4" /> },
    { to: '/analytics', label: 'Analytics', icon: <BarChart3 className="w-4 h-4" /> },
    { to: '/admin', label: 'Admin & Health', icon: <Settings className="w-4 h-4" /> },
  ];

  return (
    <nav
      className={clsx(
        'flex shrink-0 flex-col border-r border-slate-800 bg-slate-900/90 transition-all duration-200 z-20',
        sidebarExpanded ? 'w-56' : 'w-16'
      )}
    >
      {/* Brand Header */}
      <div className="flex h-12 items-center justify-between px-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-ultrone-500 to-indigo-600 text-white font-bold text-xs shadow-md shadow-ultrone-900/30">
            <Zap className="w-4 h-4 fill-current" />
          </div>
          {sidebarExpanded && (
            <div className="truncate">
              <span className="font-bold text-xs tracking-wider text-slate-100 uppercase block leading-none">
                ULTRONE
              </span>
              <span className="text-[10px] text-slate-500 font-mono tracking-tighter">
                OPS CONSOLE v2
              </span>
            </div>
          )}
        </div>
        <button
          onClick={toggleSidebar}
          className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
          title={sidebarExpanded ? 'Collapse Sidebar' : 'Expand Sidebar'}
        >
          {sidebarExpanded ? (
            <ChevronLeft className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Nav items */}
      <div className="flex flex-1 flex-col gap-1 p-2 overflow-y-auto">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              clsx(
                'flex items-center rounded-lg text-xs font-medium transition-all group relative',
                sidebarExpanded ? 'px-3 py-2 gap-3' : 'h-10 w-10 justify-center mx-auto',
                isActive
                  ? 'bg-ultrone-600/20 text-ultrone-300 border border-ultrone-500/40 shadow-sm shadow-ultrone-950/40'
                  : 'text-slate-400 hover:bg-slate-800/80 hover:text-slate-200 border border-transparent'
              )
            }
            title={!sidebarExpanded ? item.label : undefined}
          >
            <span className="shrink-0">{item.icon}</span>
            {sidebarExpanded && (
              <span className="flex-1 truncate text-left">{item.label}</span>
            )}
            {item.badge !== undefined && (
              <span
                className={clsx(
                  'rounded-full font-mono text-[10px] px-1.5 py-0.2',
                  sidebarExpanded
                    ? 'bg-slate-800 text-slate-300 border border-slate-700'
                    : 'absolute -top-1 -right-1 bg-ultrone-600 text-white text-[9px] w-4 h-4 flex items-center justify-center rounded-full'
                )}
              >
                {item.badge}
              </span>
            )}
          </NavLink>
        ))}
      </div>

      {/* Bottom Status / Mode Toggle */}
      <div className="p-2 border-t border-slate-800">
        <div
          className={clsx(
            'flex items-center rounded-lg p-2 bg-slate-950/50 border border-slate-800/80 text-xs',
            sidebarExpanded ? 'justify-between' : 'justify-center'
          )}
        >
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            {sidebarExpanded && (
              <span className="text-[11px] font-mono text-emerald-400">DEFCON 4</span>
            )}
          </div>
          {sidebarExpanded && (
            <span className="text-[10px] text-slate-500 font-mono">ENCRYPTED</span>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Sidebar;

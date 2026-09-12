import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Shield,
  Globe,
  Layers,
  FolderLock,
  Activity,
  GitFork,
  Bot,
  Box,
  BarChart3,
  Microscope,
  Settings,
  ChevronLeft,
  ChevronRight,
  Zap,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useUIStore } from '../store/uiStore';
import { useWorldStore } from '../store/worldStore';
import { useInvestigationStore } from '../store/investigationStore';

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
  const cases = useInvestigationStore((s) => s.cases);

  const NAV_ITEMS: NavItem[] = [
    { to: '/', label: 'Overview', icon: <Shield className="w-4 h-4" /> },
    { to: '/world', label: 'World (COP)', icon: <Globe className="w-4 h-4" /> },
    {
      to: '/entities',
      label: 'Entities',
      icon: <Layers className="w-4 h-4" />,
      badge: entities.length,
    },
    {
      to: '/investigations',
      label: 'Investigations',
      icon: <FolderLock className="w-4 h-4" />,
      badge: cases.length,
    },
    { to: '/simulation', label: 'Simulation', icon: <Box className="w-4 h-4" /> },
    { to: '/ai', label: 'AI Workspace', icon: <Bot className="w-4 h-4" /> },
    {
      to: '/events',
      label: 'Timeline',
      icon: <Activity className="w-4 h-4" />,
      badge: events.length,
    },
    { to: '/ontology', label: 'Ontology Graph', icon: <GitFork className="w-4 h-4" /> },
    { to: '/analytics', label: 'Analytics', icon: <BarChart3 className="w-4 h-4" /> },
    { to: '/research', label: 'DARPA Lab', icon: <Microscope className="w-4 h-4" /> },
    { to: '/admin', label: 'Admin & Health', icon: <Settings className="w-4 h-4" /> },
  ];

  return (
    <nav
      className={clsx(
        'flex shrink-0 flex-col border-r border-slate-800 bg-slate-900/90 transition-all duration-200 z-20 font-mono select-none',
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
                OPS CONSOLE v2.5
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
      <div className="flex flex-1 flex-col gap-1 p-2 overflow-y-auto no-scrollbar">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              clsx(
                'flex items-center rounded-lg text-xs font-medium transition-all group relative',
                sidebarExpanded ? 'px-3 py-2 gap-3' : 'h-10 w-10 justify-center mx-auto',
                isActive
                  ? 'bg-ultrone-600/20 text-ultrone-300 font-semibold border border-ultrone-500/30 shadow-sm'
                  : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
              )
            }
          >
            <span className="shrink-0">{item.icon}</span>

            {sidebarExpanded && (
              <span className="truncate flex-1 text-left">{item.label}</span>
            )}

            {sidebarExpanded && item.badge !== undefined && (
              <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400 font-mono shrink-0">
                {item.badge}
              </span>
            )}

            {/* Tooltip for collapsed mode */}
            {!sidebarExpanded && (
              <div className="absolute left-full ml-2 z-50 hidden rounded-md bg-slate-800 px-2 py-1 text-xs text-slate-200 shadow-lg group-hover:block whitespace-nowrap border border-slate-700">
                {item.label}
              </div>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  );
};

export default Sidebar;

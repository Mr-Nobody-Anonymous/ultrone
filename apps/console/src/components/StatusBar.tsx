import React, { useState, useEffect } from 'react';
import { useWorldStore } from '../store/worldStore';
import { useConnectionStore } from '../store/connectionStore';
import { Radio, Wifi, WifiOff, Clock, Shield, Cpu, RefreshCw } from 'lucide-react';

export const StatusBar: React.FC = () => {
  const entityCount = useWorldStore((s) => s.entities.length);
  const eventCount = useWorldStore((s) => s.events.length);
  const { wsStatus, lastPing, messagesReceived } = useConnectionStore();
  const [timeStr, setTimeStr] = useState('');
  const [utcTimeStr, setUtcTimeStr] = useState('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(now.toLocaleTimeString([], { hour12: false }));
      setUtcTimeStr(now.toISOString().substring(11, 19) + ' Z');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="flex h-10 shrink-0 items-center justify-between border-b border-slate-800 bg-slate-900/90 px-4 text-xs select-none z-10">
      {/* Left items: Sector / Workspace & Status */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Shield className="w-3.5 h-3.5 text-ultrone-400" />
          <span className="font-bold tracking-widest text-slate-100 uppercase font-mono">
            SECTOR: TACTICAL-01
          </span>
          <span className="text-slate-600 font-mono">/</span>
          <span className="text-slate-400 font-mono text-[11px]">COPILOT: ACTIVE</span>
        </div>

        <div className="hidden md:flex items-center gap-2 border-l border-slate-800 pl-4">
          <span className="flex items-center gap-1.5 text-emerald-400 font-mono text-[11px]">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            CORE ONLINE
          </span>
        </div>
      </div>

      {/* Center: Live stream stats */}
      <div className="hidden lg:flex items-center gap-6 text-slate-400 font-mono text-[11px]">
        <div className="flex items-center gap-1.5">
          <Radio className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
          <span>ENTITIES:</span>
          <span className="text-slate-200 font-semibold">{entityCount}</span>
        </div>

        <div className="flex items-center gap-1.5">
          <RefreshCw className="w-3.5 h-3.5 text-indigo-400" />
          <span>EVENTS:</span>
          <span className="text-slate-200 font-semibold">{eventCount}</span>
        </div>

        <div className="flex items-center gap-1.5">
          <Cpu className="w-3.5 h-3.5 text-amber-400" />
          <span>MSG STREAM:</span>
          <span className="text-slate-200">{messagesReceived} rx</span>
        </div>
      </div>

      {/* Right: Network telemetry & Clock */}
      <div className="flex items-center gap-4 font-mono text-[11px]">
        <div className="flex items-center gap-1.5 text-slate-400">
          {wsStatus === 'connected' ? (
            <Wifi className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <WifiOff className="w-3.5 h-3.5 text-rose-400" />
          )}
          <span className="uppercase text-[10px] text-slate-400">
            {wsStatus} {lastPing !== null ? `(${lastPing}ms)` : ''}
          </span>
        </div>

        <div className="flex items-center gap-2 border-l border-slate-800 pl-3">
          <Clock className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-slate-400 hidden sm:inline">{timeStr}</span>
          <span className="text-ultrone-400 font-bold bg-slate-800/80 px-1.5 py-0.5 rounded border border-slate-700/50">
            {utcTimeStr}
          </span>
        </div>
      </div>
    </header>
  );
};

export default StatusBar;

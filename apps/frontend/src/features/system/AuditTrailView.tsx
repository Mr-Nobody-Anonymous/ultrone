// Copyright (c) Ultrone Contributors. All rights reserved.
/**
 * SYSTEM → UI Audit Trail (brief item #59).
 * Every operator control action (PLAY / PAUSE / RESET / APPROVE / CONFIGURE)
 * lands in the backend's event-sourced audit trail. This screen makes that
 * trail inspectable: actor, timestamp, page, action, target, before/after,
 * run, environment and authorization — so the UI itself is part of the
 * event-sourced audit story rather than a blind spot.
 */
import React, { useEffect, useState } from 'react';
import { cockpitApi } from '../../api/client';
import { ScrollText, RefreshCw } from 'lucide-react';
import { StatusBadge } from '../../components/ui/StatusBadge';

interface UiActionEntry {
  action_id: string;
  actor: string;
  timestamp: number;
  page: string;
  action: string;
  target: string;
  run_id: string;
  environment: string;
  authorization: string;
  detail: Record<string, any>;
  before: any;
  after: any;
}

const fmtTime = (ts: number) => new Date(ts * 1000).toLocaleTimeString('en-GB', { hour12: false });

export const AuditTrailView: React.FC = () => {
  const [entries, setEntries] = useState<UiActionEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () =>
      cockpitApi
        .getUiActions(200)
        .then((a) => alive && (setEntries(a), setError(null)))
        .catch(() => alive && setError('Audit endpoint unavailable — reconnecting...'));
    load();
    const iv = setInterval(load, 3000);
    return () => {
      alive = false;
      clearInterval(iv);
    };
  }, []);

  if (error && !entries) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-2 font-mono text-sm">
        <span className="text-rose-300">{error}</span>
        <span className="text-xs text-surface-500">Audit records unavailable until connection is restored.</span>
      </div>
    );
  }

  if (!entries) {
    return (
      <div className="flex items-center justify-center h-64 text-surface-400 font-mono text-sm">
        <span className="animate-pulse">Loading UI audit trail...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-mono" data-testid="audit-trail-view">
      <div className="flex items-center justify-between bg-surface-900/90 p-4 rounded-xl border border-surface-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-violet-950 text-violet-400 border border-violet-800/50">
            <ScrollText className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-surface-100 font-sans">UI Audit Trail</h2>
            <p className="text-xs text-surface-400">
              Every operator action from this cockpit, event-sourced on the backend. Showing the {entries.length} most recent.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-surface-500">
          <RefreshCw className="w-3.5 h-3.5" />
          polling 3s
        </div>
      </div>

      {entries.length === 0 ? (
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-8 text-center">
          <p className="text-sm text-surface-300 font-bold">NO UI ACTIONS RECORDED YET</p>
          <p className="text-xs text-surface-500 mt-1">
            Use any control (play, pause, step, reset) and the action will appear here.
          </p>
        </div>
      ) : (
        <div className="bg-surface-900 rounded-xl border border-surface-800 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-surface-800 bg-surface-950 text-surface-400 text-[11px] uppercase">
                  <th className="py-2.5 px-3">Action ID</th>
                  <th className="py-2.5 px-3">Time</th>
                  <th className="py-2.5 px-3">Actor</th>
                  <th className="py-2.5 px-3">Action</th>
                  <th className="py-2.5 px-3">Target</th>
                  <th className="py-2.5 px-3">Page</th>
                  <th className="py-2.5 px-3">Run</th>
                  <th className="py-2.5 px-3">Environment</th>
                  <th className="py-2.5 px-3">Authorization</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-800/60">
                {[...entries].reverse().map((e) => (
                  <tr key={e.action_id} className="hover:bg-surface-950/60">
                    <td className="py-2.5 px-3 font-mono text-cyan-400">{e.action_id}</td>
                    <td className="py-2.5 px-3 font-mono text-surface-400">{fmtTime(e.timestamp)}</td>
                    <td className="py-2.5 px-3 text-surface-200">{e.actor}</td>
                    <td className="py-2.5 px-3 font-bold text-surface-100">{e.action}</td>
                    <td className="py-2.5 px-3 text-surface-300 font-mono">{e.target}</td>
                    <td className="py-2.5 px-3 text-surface-400">{e.page}</td>
                    <td className="py-2.5 px-3 text-surface-400 font-mono">{e.run_id}</td>
                    <td className="py-2.5 px-3">
                      <StatusBadge status={e.environment.toUpperCase()} className="text-[10px]" />
                    </td>
                    <td className="py-2.5 px-3 text-surface-400">{e.authorization}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
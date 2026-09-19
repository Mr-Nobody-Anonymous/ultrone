// Copyright (c) Ultrone Contributors. All rights reserved.
import React from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  PauseCircle,
  PlayCircle,
  ShieldAlert,
  Radio,
  Zap,
} from 'lucide-react';

export type StatusType =
  | 'READY'
  | 'ACTIVE'
  | 'RUNNING'
  | 'PAUSED'
  | 'IDLE'
  | 'DEGRADED'
  | 'FAULT'
  | 'ERROR'
  | 'CRITICAL'
  | 'HIGH'
  | 'MEDIUM'
  | 'LOW'
  | 'INFO'
  | 'RESTRICTED'
  | 'EMERGENCY_STOP'
  | 'NORMAL'
  | 'SIMULATION'
  | 'HOLDOUT'
  | 'APPROVED'
  | 'BLOCKED';

interface StatusBadgeProps {
  status: string;
  className?: string;
  showIcon?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  className = '',
  showIcon = true,
}) => {
  const norm = (status || 'UNKNOWN').toUpperCase();

  let colorClasses = 'bg-surface-800 text-surface-300 border-surface-700';
  let Icon = Radio;
  let text = norm;

  switch (norm) {
    case 'READY':
    case 'NORMAL':
    case 'APPROVED':
    case 'LOW':
    case 'INFO':
      colorClasses = 'bg-emerald-950/80 text-emerald-400 border-emerald-600/50';
      Icon = CheckCircle2;
      text = norm === 'READY' ? '✓ READY' : norm;
      break;

    case 'ACTIVE':
    case 'RUNNING':
      colorClasses = 'bg-blue-950/80 text-blue-400 border-blue-500/50';
      Icon = norm === 'RUNNING' ? PlayCircle : Zap;
      text = norm === 'RUNNING' ? '● RUNNING' : '⚡ ACTIVE';
      break;

    case 'PAUSED':
    case 'IDLE':
      colorClasses = 'bg-slate-900/80 text-slate-400 border-slate-700';
      Icon = PauseCircle;
      text = norm === 'PAUSED' ? '⏸ PAUSED' : '— IDLE';
      break;

    case 'DEGRADED':
    case 'MEDIUM':
    case 'RESTRICTED':
      colorClasses = 'bg-amber-950/80 text-amber-400 border-amber-500/50';
      Icon = AlertTriangle;
      text = norm === 'DEGRADED' ? '⚠ DEGRADED' : norm;
      break;

    case 'FAULT':
    case 'ERROR':
    case 'CRITICAL':
    case 'HIGH':
    case 'EMERGENCY_STOP':
    case 'BLOCKED':
      colorClasses = 'bg-rose-950/80 text-rose-400 border-rose-600/50';
      Icon = norm === 'EMERGENCY_STOP' ? ShieldAlert : XCircle;
      text = norm === 'FAULT' ? '✕ FAULT' : norm;
      break;

    case 'SIMULATION':
      colorClasses = 'bg-cyan-950/80 text-cyan-400 border-cyan-500/50';
      Icon = Radio;
      text = 'SIMULATION';
      break;

    case 'HOLDOUT':
      colorClasses = 'bg-purple-950/80 text-purple-400 border-purple-500/50';
      Icon = ShieldAlert;
      text = 'SEALED HOLDOUT';
      break;
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium border ${colorClasses} ${className}`}
    >
      {showIcon && <Icon className="w-3.5 h-3.5 flex-shrink-0" />}
      <span>{text}</span>
    </span>
  );
};

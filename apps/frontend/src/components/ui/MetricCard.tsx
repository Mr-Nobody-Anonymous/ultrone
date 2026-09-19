// Copyright (c) Ultrone Contributors. All rights reserved.
import React from 'react';
import { ArrowUpRight, ArrowDownRight, Minus, HelpCircle } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string | number;
  subValue?: string;
  uncertainty?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendLabel?: string;
  status?: 'normal' | 'warning' | 'danger' | 'success';
  tooltip?: string;
  onClick?: () => void;
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subValue,
  uncertainty,
  trend,
  trendLabel,
  status = 'normal',
  tooltip,
  onClick,
  className = '',
}) => {
  let borderClass = 'border-surface-800 hover:border-surface-700';
  let valueColor = 'text-surface-100';

  if (status === 'success') {
    borderClass = 'border-emerald-900/40 hover:border-emerald-700/50';
    valueColor = 'text-emerald-400';
  } else if (status === 'warning') {
    borderClass = 'border-amber-900/40 hover:border-amber-700/50';
    valueColor = 'text-amber-400';
  } else if (status === 'danger') {
    borderClass = 'border-rose-900/40 hover:border-rose-700/50';
    valueColor = 'text-rose-400';
  }

  const clickableClass = onClick ? 'cursor-pointer transition-all hover:scale-[1.01]' : '';

  return (
    <div
      onClick={onClick}
      className={`bg-surface-900/80 backdrop-blur-md rounded-lg p-3.5 border ${borderClass} ${clickableClass} ${className} flex flex-col justify-between`}
      title={tooltip}
    >
      <div className="flex items-center justify-between text-xs text-surface-400 font-medium mb-1">
        <span className="truncate">{label}</span>
        {tooltip && <HelpCircle className="w-3.5 h-3.5 text-surface-500 flex-shrink-0" />}
      </div>

      <div className="flex items-baseline gap-2">
        <span className={`text-xl font-mono font-bold tracking-tight ${valueColor}`}>{value}</span>
        {uncertainty && (
          <span className="text-xs font-mono text-surface-400" title="95% Confidence Interval">
            {uncertainty}
          </span>
        )}
      </div>

      {(subValue || trend || trendLabel) && (
        <div className="mt-2 flex items-center justify-between text-xs text-surface-400">
          {subValue && <span className="truncate text-surface-400">{subValue}</span>}
          {trend && (
            <div className="flex items-center gap-1 font-mono text-xs ml-auto">
              {trend === 'up' && <ArrowUpRight className="w-3.5 h-3.5 text-emerald-400" />}
              {trend === 'down' && <ArrowDownRight className="w-3.5 h-3.5 text-rose-400" />}
              {trend === 'neutral' && <Minus className="w-3.5 h-3.5 text-surface-400" />}
              {trendLabel && <span>{trendLabel}</span>}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

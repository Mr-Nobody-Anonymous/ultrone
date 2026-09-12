import React from 'react';
import { clsx } from 'clsx';

interface ConfidenceBadgeProps {
  confidence: number; // 0.0 to 1.0
  showPercent?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  confidence,
  showPercent = true,
  size = 'md',
  className,
}) => {
  const percent = Math.round(confidence * 100);

  // Color mapping based on operational confidence bands
  const colorClass =
    confidence >= 0.85
      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
      : confidence >= 0.65
      ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30'
      : confidence >= 0.45
      ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
      : 'bg-rose-500/10 text-rose-400 border-rose-500/30';

  const dotColor =
    confidence >= 0.85
      ? 'bg-emerald-400'
      : confidence >= 0.65
      ? 'bg-cyan-400'
      : confidence >= 0.45
      ? 'bg-amber-400'
      : 'bg-rose-400';

  const sizeClass =
    size === 'sm'
      ? 'px-1.5 py-0.5 text-[10px]'
      : size === 'lg'
      ? 'px-3 py-1 text-sm'
      : 'px-2 py-0.5 text-xs';

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full border font-mono font-medium',
        colorClass,
        sizeClass,
        className
      )}
      title={`Confidence: ${(confidence * 100).toFixed(1)}%`}
    >
      <span className={clsx('h-1.5 w-1.5 rounded-full animate-pulse', dotColor)} />
      {showPercent ? `${percent}%` : confidence.toFixed(2)}
    </span>
  );
};

export default ConfidenceBadge;

import React from 'react';
import { EVENT_TYPE_META } from '../types/event';

interface EventDotProps {
  type: string;
  size?: 'sm' | 'md' | 'lg';
}

export const EventDot: React.FC<EventDotProps> = ({ type, size = 'md' }) => {
  const meta = (EVENT_TYPE_META as Record<string, { category: string; color: string; icon: string; severity: string }>)[type] || {
    category: 'System',
    color: '#94a3b8',
    icon: '●',
    severity: 'info',
  };

  const sizeClasses =
    size === 'sm' ? 'w-2 h-2' : size === 'lg' ? 'w-3.5 h-3.5' : 'w-2.5 h-2.5';

  return (
    <span
      className={`inline-block rounded-full shrink-0 ${sizeClasses}`}
      style={{ backgroundColor: meta.color }}
      title={`${meta.category}: ${type}`}
    />
  );
};

export default EventDot;

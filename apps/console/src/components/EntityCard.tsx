import React from 'react';
import type { Entity } from '../types/entity';
import ConfidenceBadge from './ConfidenceBadge';
import { Plane, Compass, Radio, Shield, Activity, Target } from 'lucide-react';
import { clsx } from 'clsx';

interface EntityCardProps {
  entity: Entity;
  isSelected?: boolean;
  onClick?: () => void;
  compact?: boolean;
}

export const EntityCard: React.FC<EntityCardProps> = ({
  entity,
  isSelected = false,
  onClick,
  compact = false,
}) => {
  const getIcon = (type: string) => {
    switch (type) {
      case 'air_asset':
        return <Plane className="w-4 h-4 text-cyan-400" />;
      case 'ground_unit':
        return <Shield className="w-4 h-4 text-emerald-400" />;
      case 'sensor_station':
        return <Radio className="w-4 h-4 text-indigo-400" />;
      case 'target':
        return <Target className="w-4 h-4 text-rose-400" />;
      default:
        return <Compass className="w-4 h-4 text-slate-400" />;
    }
  };

  const statusColor =
    entity.status === 'active'
      ? 'text-emerald-400'
      : entity.status === 'degraded'
      ? 'text-amber-400'
      : entity.status === 'engaged'
      ? 'text-purple-400'
      : 'text-slate-400';

  if (compact) {
    return (
      <div
        onClick={onClick}
        className={clsx(
          'flex items-center justify-between p-2 rounded cursor-pointer transition-all border text-xs',
          isSelected
            ? 'bg-ultrone-600/20 border-ultrone-500/50'
            : 'bg-slate-900/60 border-slate-800/80 hover:bg-slate-800/60 hover:border-slate-700/60'
        )}
      >
        <div className="flex items-center gap-2 overflow-hidden">
          {getIcon(entity.type)}
          <span className="font-mono font-medium text-slate-200 truncate">
            {entity.entity_id}
          </span>
          <span className="text-[10px] text-slate-400 uppercase">
            {entity.type.replace('_', ' ')}
          </span>
        </div>
        <ConfidenceBadge confidence={entity.confidence} size="sm" />
      </div>
    );
  }

  return (
    <div
      onClick={onClick}
      className={clsx(
        'p-3 rounded-lg cursor-pointer transition-all border space-y-2',
        isSelected
          ? 'bg-ultrone-600/15 border-ultrone-500/60 shadow-lg shadow-ultrone-950/50'
          : 'bg-slate-900/80 border-slate-800 hover:bg-slate-850 hover:border-slate-700'
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded bg-slate-800/80 border border-slate-700/50">
            {getIcon(entity.type)}
          </div>
          <div>
            <div className="font-mono text-sm font-semibold text-slate-100 flex items-center gap-1.5">
              {entity.entity_id}
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            </div>
            <div className="text-[11px] text-slate-400 uppercase tracking-wider">
              {entity.type.replace('_', ' ')}
            </div>
          </div>
        </div>
        <ConfidenceBadge confidence={entity.confidence} />
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs pt-1 border-t border-slate-800/80">
        <div>
          <span className="text-slate-500 text-[10px] uppercase block">Status</span>
          <span className={clsx('font-medium capitalize flex items-center gap-1', statusColor)}>
            <Activity className="w-3 h-3" />
            {entity.status}
          </span>
        </div>
        <div>
          <span className="text-slate-500 text-[10px] uppercase block">Position</span>
          <span className="font-mono text-slate-300 text-[11px] truncate block">
            {entity.position
              ? `${entity.position.lat.toFixed(2)}°, ${entity.position.lng.toFixed(2)}°`
              : 'N/A'}
          </span>
        </div>
      </div>

      {entity.sensors && entity.sensors.length > 0 && (
        <div className="flex flex-wrap gap-1 pt-1">
          {entity.sensors.map((sensor) => (
            <span
              key={sensor}
              className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/50"
            >
              {sensor}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

export default EntityCard;

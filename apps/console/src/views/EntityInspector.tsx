import React, { useState, useMemo } from 'react';
import { useWorldStore } from '../store/worldStore';
import ConfidenceBadge from '../components/ConfidenceBadge';
import {
  Search,
  Filter,
  ArrowUpDown,
  Plane,
  Shield,
  Radio,
  Target,
  Compass,
} from 'lucide-react';

type SortField = 'entity_id' | 'type' | 'status' | 'confidence';
type SortOrder = 'asc' | 'desc';

export const EntityInspector: React.FC = () => {
  const entities = useWorldStore((s) => s.entities);
  const selectedEntity = useWorldStore((s) => s.selectedEntity);
  const selectEntity = useWorldStore((s) => s.selectEntity);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('entity_id');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');

  // Filter & sort
  const filteredEntities = useMemo(() => {
    return entities
      .filter((e) => {
        const matchesSearch =
          e.entity_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
          e.type.toLowerCase().includes(searchQuery.toLowerCase()) ||
          e.status.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesType = selectedType === 'all' || e.type === selectedType;
        const matchesStatus = selectedStatus === 'all' || e.status === selectedStatus;
        return matchesSearch && matchesType && matchesStatus;
      })
      .sort((a, b) => {
        let valA = a[sortField];
        let valB = b[sortField];
        if (typeof valA === 'string' && typeof valB === 'string') {
          return sortOrder === 'asc'
            ? valA.localeCompare(valB)
            : valB.localeCompare(valA);
        }
        if (typeof valA === 'number' && typeof valB === 'number') {
          return sortOrder === 'asc' ? valA - valB : valB - valA;
        }
        return 0;
      });
  }, [entities, searchQuery, selectedType, selectedStatus, sortField, sortOrder]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  const getEntityIcon = (type: string) => {
    switch (type) {
      case 'air_asset':
        return <Plane className="w-3.5 h-3.5 text-cyan-400" />;
      case 'ground_unit':
        return <Shield className="w-3.5 h-3.5 text-emerald-400" />;
      case 'sensor_station':
        return <Radio className="w-3.5 h-3.5 text-indigo-400" />;
      case 'target':
        return <Target className="w-3.5 h-3.5 text-rose-400" />;
      default:
        return <Compass className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  const uniqueTypes = ['all', ...Array.from(new Set(entities.map((e) => e.type)))];

  return (
    <div className="flex h-full w-full flex-col bg-slate-950 p-6 overflow-hidden space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="font-mono text-xl font-bold tracking-wider text-slate-100 uppercase">
            Entity Inspector
          </h1>
          <p className="text-xs text-slate-400">
            Canonical operational database — {entities.length} total active entities in world model
          </p>
        </div>

        {/* Global Search Input */}
        <div className="flex items-center gap-2 rounded-lg bg-slate-900 border border-slate-800 px-3 py-1.5 w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search entity ID, type, status..."
            className="w-full bg-transparent text-xs text-slate-100 placeholder-slate-500 outline-none"
          />
        </div>
      </div>

      {/* Filter Tabs and Pills */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Type Filter Buttons */}
        <div className="flex items-center gap-1 rounded-lg bg-slate-900 p-1 border border-slate-800">
          {uniqueTypes.map((type) => (
            <button
              key={type}
              onClick={() => setSelectedType(type)}
              className={`px-3 py-1 text-xs font-mono rounded capitalize transition-colors ${
                selectedType === type
                  ? 'bg-ultrone-600/30 text-ultrone-300 font-semibold border border-ultrone-500/40'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {type.replace('_', ' ')}
            </button>
          ))}
        </div>

        {/* Status Filter */}
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <Filter className="w-3.5 h-3.5 text-slate-500" />
          <span>Status:</span>
          {['all', 'active', 'degraded', 'engaged'].map((st) => (
            <button
              key={st}
              onClick={() => setSelectedStatus(st)}
              className={`px-2 py-0.5 rounded text-[11px] uppercase transition-colors ${
                selectedStatus === st
                  ? 'bg-slate-800 text-slate-100 font-semibold'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Data Table */}
      <div className="flex-1 overflow-auto rounded-lg border border-slate-800 bg-slate-900/60 shadow-xl">
        <table className="w-full text-left text-xs border-collapse">
          <thead className="sticky top-0 bg-slate-900 border-b border-slate-800 font-mono text-[11px] text-slate-400 uppercase tracking-wider">
            <tr>
              <th
                onClick={() => handleSort('entity_id')}
                className="p-3 cursor-pointer hover:text-slate-200"
              >
                <div className="flex items-center gap-1.5">
                  <span>Entity ID</span>
                  <ArrowUpDown className="w-3 h-3 text-slate-500" />
                </div>
              </th>
              <th
                onClick={() => handleSort('type')}
                className="p-3 cursor-pointer hover:text-slate-200"
              >
                <div className="flex items-center gap-1.5">
                  <span>Type</span>
                  <ArrowUpDown className="w-3 h-3 text-slate-500" />
                </div>
              </th>
              <th
                onClick={() => handleSort('status')}
                className="p-3 cursor-pointer hover:text-slate-200"
              >
                <div className="flex items-center gap-1.5">
                  <span>Status</span>
                  <ArrowUpDown className="w-3 h-3 text-slate-500" />
                </div>
              </th>
              <th
                onClick={() => handleSort('confidence')}
                className="p-3 cursor-pointer hover:text-slate-200"
              >
                <div className="flex items-center gap-1.5">
                  <span>Confidence</span>
                  <ArrowUpDown className="w-3 h-3 text-slate-500" />
                </div>
              </th>
              <th className="p-3">Coordinates / Position</th>
              <th className="p-3">Sensors / Feeds</th>
              <th className="p-3">Relations</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {filteredEntities.map((entity) => {
              const isSelected = selectedEntity?.entity_id === entity.entity_id;
              return (
                <tr
                  key={entity.entity_id}
                  onClick={() => selectEntity(entity)}
                  className={`cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-ultrone-600/20 text-slate-100'
                      : 'hover:bg-slate-850/60 text-slate-300'
                  }`}
                >
                  <td className="p-3 font-semibold text-ultrone-400 flex items-center gap-2">
                    {getEntityIcon(entity.type)}
                    <span>{entity.entity_id}</span>
                  </td>
                  <td className="p-3 capitalize text-slate-300">
                    {entity.type.replace('_', ' ')}
                  </td>
                  <td className="p-3">
                    <span
                      className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] uppercase font-semibold ${
                        entity.status === 'active'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : entity.status === 'degraded'
                          ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                          : 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                      }`}
                    >
                      {entity.status}
                    </span>
                  </td>
                  <td className="p-3">
                    <ConfidenceBadge confidence={entity.confidence} size="sm" />
                  </td>
                  <td className="p-3 text-slate-400 text-[11px]">
                    {entity.position
                      ? `${entity.position.lat.toFixed(3)}°, ${entity.position.lng.toFixed(3)}°`
                      : '—'}
                  </td>
                  <td className="p-3">
                    <div className="flex flex-wrap gap-1">
                      {entity.sensors?.slice(0, 2).map((s) => (
                        <span
                          key={s}
                          className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-400 border border-slate-700/60"
                        >
                          {s}
                        </span>
                      ))}
                      {(entity.sensors?.length || 0) > 2 && (
                        <span className="text-[10px] text-slate-500">
                          +{(entity.sensors?.length || 0) - 2}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="p-3 text-slate-400 text-[11px]">
                    {entity.relationships?.length || 0} links
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default EntityInspector;

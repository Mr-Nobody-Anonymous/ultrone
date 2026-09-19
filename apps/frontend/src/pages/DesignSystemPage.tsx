// Copyright (c) Ultrone Contributors. All rights reserved.
import React from 'react';
import { Palette, CheckCircle2, AlertTriangle, XCircle, Shield, Radio, Play } from 'lucide-react';
import { StatusBadge } from '../components/ui/StatusBadge';
import { MetricCard } from '../components/ui/MetricCard';
import { JsonViewer } from '../components/ui/JsonViewer';

export const DesignSystemPage: React.FC = () => {
  return (
    <div className="space-y-8 max-w-7xl mx-auto font-mono">
      {/* Header */}
      <div className="flex items-center justify-between bg-surface-900/90 p-4 rounded-xl border border-surface-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-pink-950 text-pink-400 border border-pink-800/50">
            <Palette className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-surface-100 font-sans flex items-center gap-2">
              ULTRONE Visual Design System & Component Catalog
              <StatusBadge status="READY" />
            </h2>
            <p className="text-xs text-surface-400">
              Reusable UI tokens, status badges, metric tiles, and density-optimized primitives.
            </p>
          </div>
        </div>
      </div>

      {/* 1. Status Badges */}
      <div className="bg-surface-900 rounded-xl border border-surface-800 p-5 space-y-3">
        <h3 className="text-xs font-bold text-surface-200 uppercase tracking-wider">
          Status Badges (Color-Independent with Icons & Text)
        </h3>
        <div className="flex flex-wrap gap-2.5">
          <StatusBadge status="READY" />
          <StatusBadge status="ACTIVE" />
          <StatusBadge status="RUNNING" />
          <StatusBadge status="PAUSED" />
          <StatusBadge status="IDLE" />
          <StatusBadge status="DEGRADED" />
          <StatusBadge status="FAULT" />
          <StatusBadge status="CRITICAL" />
          <StatusBadge status="SIMULATION" />
          <StatusBadge status="HOLDOUT" />
          <StatusBadge status="APPROVED" />
          <StatusBadge status="BLOCKED" />
        </div>
      </div>

      {/* 2. Metric Cards */}
      <div className="bg-surface-900 rounded-xl border border-surface-800 p-5 space-y-3">
        <h3 className="text-xs font-bold text-surface-200 uppercase tracking-wider">
          Metric Cards (Sparklines, Uncertainties, Drill-Downs)
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="ACCURACY ESTIMATE"
            value="86.2%"
            uncertainty="±1.4%"
            status="success"
            trend="up"
            trendLabel="+5.1%"
          />
          <MetricCard
            label="CALIBRATION (ECE)"
            value="0.071"
            status="success"
            trend="down"
            trendLabel="-0.038 (better)"
          />
          <MetricCard
            label="TELEMETRY FRESHNESS"
            value="118 ms"
            uncertainty="< 250ms threshold"
            status="normal"
          />
          <MetricCard
            label="BLOCKED ACTIONS"
            value="4"
            status="danger"
            subValue="SAF-003 Freshness Violations"
          />
        </div>
      </div>

      {/* 3. Code & JSON Viewer */}
      <div className="bg-surface-900 rounded-xl border border-surface-800 p-5 space-y-3">
        <h3 className="text-xs font-bold text-surface-200 uppercase tracking-wider">
          Syntax-Highlighted JSON Inspector
        </h3>
        <JsonViewer
          data={{
            mcp_protocol: '2026-07-28',
            udis_manifest: {
              device_id: 'device-001',
              type: 'radar_sensor',
              operating_mode: 'simulation',
              simulation_only: true,
              fsm_state: 'READY',
              allowed_transitions: ['BUSY', 'DEGRADED', 'SHUTDOWN'],
            },
            causal_boundary: {
              time_t: ['observations', 'belief', 'plan', 'policy'],
              time_t_plus_1: ['outcome'],
              leakage_detected: false,
            },
          }}
        />
      </div>
    </div>
  );
};

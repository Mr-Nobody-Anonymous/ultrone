// Copyright (c) Ultrone Contributors. All rights reserved.
import React, { useEffect, useState } from 'react';
import { useCockpitStore } from '../../stores/cockpitStore';
import { cockpitApi } from '../../api/client';
import type { DeviceCatalog, DeviceRecord } from '../../api/types';
import { Sliders, Radio, ArrowRight, ShieldCheck, Zap, Activity, Check } from 'lucide-react';
import { StatusBadge } from '../../components/ui/StatusBadge';

export const DevicesView: React.FC = () => {
  const { inspect } = useCockpitStore();
  const [catalog, setCatalog] = useState<DeviceCatalog | null>(null);
  const [loading, setLoading] = useState(true);
  const [transitioning, setTransitioning] = useState<string | null>(null);

  const fetchDevices = () => {
    cockpitApi
      .getDevices()
      .then((data) => {
        setCatalog(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    fetchDevices();
  }, []);

  const handleTransition = async (deviceId: string, targetState: string) => {
    setTransitioning(deviceId);
    try {
      await cockpitApi.transitionDevice(deviceId, targetState, 'operator interactive command');
      await fetchDevices();
    } catch (err: any) {
      alert(`FSM transition blocked: ${err.message}`);
    } finally {
      setTransitioning(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-surface-400 font-mono text-sm">
        <span className="animate-pulse">Loading UDIS Device Registry & FSM States...</span>
      </div>
    );
  }

  const devices = catalog?.devices || [];
  const summary = catalog?.summary || {};

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-mono">
      {/* Header */}
      <div className="flex items-center justify-between bg-surface-900/90 p-4 rounded-xl border border-surface-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-cyan-950 text-cyan-400 border border-cyan-800/50">
            <Sliders className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-surface-100 font-sans flex items-center gap-2">
              UDIS Device Laboratory & 10-State FSM
              <StatusBadge status="SIMULATION" />
            </h2>
            <p className="text-xs text-surface-400">
              Universal Device Interface Standard: manifest validation, telemetry buffers, and state machine transitions.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <div className="bg-surface-950 px-3 py-1 rounded-lg border border-surface-800">
            <span className="text-surface-500 mr-1.5">READY:</span>
            <span className="text-emerald-400 font-bold">{summary.READY || 0}</span>
          </div>
          <div className="bg-surface-950 px-3 py-1 rounded-lg border border-surface-800">
            <span className="text-surface-500 mr-1.5">DEGRADED:</span>
            <span className="text-amber-400 font-bold">{summary.DEGRADED || 0}</span>
          </div>
          <div className="bg-surface-950 px-3 py-1 rounded-lg border border-surface-800">
            <span className="text-surface-500 mr-1.5">TOTAL:</span>
            <span className="text-surface-200 font-bold">{devices.length}</span>
          </div>
        </div>
      </div>

      {/* Device Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {devices.map((device) => {
          const isSigned = device.signature?.valid;

          return (
            <div
              key={device.device_id}
              className="bg-surface-900 rounded-xl border border-surface-800 p-4 flex flex-col justify-between hover:border-surface-700 transition-colors shadow-lg"
            >
              <div>
                {/* Device Title & State */}
                <div className="flex items-start justify-between gap-2 mb-2.5">
                  <div>
                    <h3 className="text-sm font-bold text-surface-100 font-sans">{device.model}</h3>
                    <span className="text-xs text-cyan-400 font-mono">{device.device_id}</span>
                  </div>
                  <StatusBadge status={device.state} className="text-[10px]" />
                </div>

                {/* Metadata */}
                <div className="space-y-1 text-xs text-surface-400 mb-3 border-b border-surface-800/60 pb-3">
                  <div className="flex justify-between">
                    <span className="text-surface-500">TYPE:</span>
                    <span className="text-surface-300">{device.device_type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-surface-500">FIRMWARE:</span>
                    <span className="text-surface-300">{device.firmware}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-surface-500">SIGNATURE:</span>
                    <span className={isSigned ? 'text-emerald-400' : 'text-amber-400'}>
                      {isSigned ? 'Ed25519 Verified ✓' : 'Unverified'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-surface-500">HEALTH:</span>
                    <span className="text-emerald-400 font-bold">
                      {(device.health_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>

                {/* Telemetry Channels */}
                <div className="mb-3">
                  <span className="text-[10px] text-surface-500 uppercase tracking-wider block mb-1">
                    Telemetry Channels ({device.telemetry_channels.length})
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {device.telemetry_channels.map((ch) => (
                      <span
                        key={ch}
                        className="px-1.5 py-0.5 rounded bg-surface-950 text-surface-300 border border-surface-800 text-[10px]"
                      >
                        {ch}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Procedures */}
                <div className="mb-3">
                  <span className="text-[10px] text-surface-500 uppercase tracking-wider block mb-1">
                    Procedures ({device.procedures.length})
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {device.procedures.map((proc) => (
                      <span
                        key={proc}
                        className="px-1.5 py-0.5 rounded bg-cyan-950/60 text-cyan-300 border border-cyan-800/50 text-[10px]"
                      >
                        {proc}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Bottom Actions: FSM Transition Trigger & Inspect */}
              <div className="pt-3 border-t border-surface-800/80 flex items-center justify-between gap-2">
                {device.state === 'READY' ? (
                  <button
                    disabled={transitioning === device.device_id}
                    onClick={() => handleTransition(device.device_id, 'BUSY')}
                    className="px-2.5 py-1 rounded bg-surface-800 hover:bg-surface-700 text-surface-200 text-xs transition-colors flex items-center gap-1"
                  >
                    <span>Trigger Busy</span>
                  </button>
                ) : device.state === 'BUSY' ? (
                  <button
                    disabled={transitioning === device.device_id}
                    onClick={() => handleTransition(device.device_id, 'READY')}
                    className="px-2.5 py-1 rounded bg-emerald-950 hover:bg-emerald-900 text-emerald-300 border border-emerald-800 text-xs transition-colors"
                  >
                    <span>Return Ready</span>
                  </button>
                ) : (
                  <span className="text-[11px] text-surface-500">State: {device.state}</span>
                )}

                <button
                  onClick={() => inspect('device', device.device_id, device)}
                  className="text-xs text-cyan-400 hover:underline inline-flex items-center gap-1 ml-auto"
                >
                  <span>Inspector</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

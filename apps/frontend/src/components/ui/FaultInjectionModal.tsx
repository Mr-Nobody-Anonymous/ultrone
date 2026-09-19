// Copyright (c) Ultrone Contributors. All rights reserved.
import React, { useState } from 'react';
import { useCockpitStore } from '../../stores/cockpitStore';
import { AlertTriangle, X, Zap, ShieldAlert, Check } from 'lucide-react';

export const FaultInjectionModal: React.FC = () => {
  const { faultInjectionOpen, setFaultInjectionOpen, injectFaults, clearFaults, overview } =
    useCockpitStore();

  const [sensorDropout, setSensorDropout] = useState(false);
  const [telemetryDelay, setTelemetryDelay] = useState(false);
  const [sensorDisagreement, setSensorDisagreement] = useState(false);
  const [leaseExpiry, setLeaseExpiry] = useState(false);
  const [deviceOffline, setDeviceOffline] = useState(false);
  const [latencyMs, setLatencyMs] = useState(0);

  if (!faultInjectionOpen) return null;

  const handleApply = async () => {
    const config: Record<string, any> = {
      sensor_dropout: sensorDropout ? ['sensor-01'] : [],
      telemetry_delay: telemetryDelay ? ['sensor-01', 'sensor-02'] : [],
      sensor_disagreement: sensorDisagreement ? ['sensor-01'] : [],
      device_offline: deviceOffline ? ['device-002'] : [],
      lease_expiry: leaseExpiry,
      latency_injection_ms: Number(latencyMs) || 0,
    };
    await injectFaults(config);
    setFaultInjectionOpen(false);
  };

  const handleClear = async () => {
    setSensorDropout(false);
    setTelemetryDelay(false);
    setSensorDisagreement(false);
    setLeaseExpiry(false);
    setDeviceOffline(false);
    setLatencyMs(0);
    await clearFaults();
    setFaultInjectionOpen(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-surface-900 border border-amber-900/60 rounded-xl max-w-xl w-full shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 bg-amber-950/40 border-b border-amber-900/40 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-900/50 text-amber-400 border border-amber-700/50">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-surface-100">
                Controlled Research Fault Injection
              </h2>
              <p className="text-xs text-surface-400">
                Exercise real invariant gates and fail-safe transitions in simulation
              </p>
            </div>
          </div>
          <button
            onClick={() => setFaultInjectionOpen(false)}
            className="p-1 rounded-lg text-surface-400 hover:text-surface-100 hover:bg-surface-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <div className="p-6 space-y-4 text-xs font-mono">
          <p className="text-surface-400 text-xs font-sans leading-relaxed">
            Arming fault levers updates the real world engine and drivers. Observe how SAF-001..SAF-005
            policies catch failures and block unauthorized actions.
          </p>

          <div className="space-y-2.5">
            {/* Telemetry Delay */}
            <label className="flex items-center justify-between p-3 rounded-lg border border-surface-800 bg-surface-950/70 hover:border-surface-700 cursor-pointer transition-colors">
              <div>
                <span className="font-bold text-surface-200 block">
                  Inject Telemetry Delay (Stale Frames)
                </span>
                <span className="text-[11px] text-surface-500">
                  Forces telemetry age &gt; 250ms horizon → Triggers SAF-003 policy block
                </span>
              </div>
              <input
                type="checkbox"
                checked={telemetryDelay}
                onChange={(e) => setTelemetryDelay(e.target.checked)}
                className="w-4 h-4 rounded border-surface-700 text-amber-500 focus:ring-0"
              />
            </label>

            {/* Sensor Dropout */}
            <label className="flex items-center justify-between p-3 rounded-lg border border-surface-800 bg-surface-950/70 hover:border-surface-700 cursor-pointer transition-colors">
              <div>
                <span className="font-bold text-surface-200 block">Sensor Dropout (Zero Frames)</span>
                <span className="text-[11px] text-surface-500">
                  Simulates sensor communication blackout for sensor-01
                </span>
              </div>
              <input
                type="checkbox"
                checked={sensorDropout}
                onChange={(e) => setSensorDropout(e.target.checked)}
                className="w-4 h-4 rounded border-surface-700 text-amber-500 focus:ring-0"
              />
            </label>

            {/* Sensor Disagreement */}
            <label className="flex items-center justify-between p-3 rounded-lg border border-surface-800 bg-surface-950/70 hover:border-surface-700 cursor-pointer transition-colors">
              <div>
                <span className="font-bold text-surface-200 block">
                  Sensor Spatial Disagreement
                </span>
                <span className="text-[11px] text-surface-500">
                  Injects contradictory bearing measurement between radar and optronic sensors
                </span>
              </div>
              <input
                type="checkbox"
                checked={sensorDisagreement}
                onChange={(e) => setSensorDisagreement(e.target.checked)}
                className="w-4 h-4 rounded border-surface-700 text-amber-500 focus:ring-0"
              />
            </label>

            {/* Lease Expiry */}
            <label className="flex items-center justify-between p-3 rounded-lg border border-surface-800 bg-surface-950/70 hover:border-surface-700 cursor-pointer transition-colors">
              <div>
                <span className="font-bold text-surface-200 block">
                  Simulate Expired Capability Leases
                </span>
                <span className="text-[11px] text-surface-500">
                  Revokes active actuation lease → Triggers SAF-002 rejection
                </span>
              </div>
              <input
                type="checkbox"
                checked={leaseExpiry}
                onChange={(e) => setLeaseExpiry(e.target.checked)}
                className="w-4 h-4 rounded border-surface-700 text-amber-500 focus:ring-0"
              />
            </label>

            {/* Device Offline */}
            <label className="flex items-center justify-between p-3 rounded-lg border border-surface-800 bg-surface-950/70 hover:border-surface-700 cursor-pointer transition-colors">
              <div>
                <span className="font-bold text-surface-200 block">Disconnect UDIS Device</span>
                <span className="text-[11px] text-surface-500">
                  Forces device-002 into DEGRADED/OFFLINE state
                </span>
              </div>
              <input
                type="checkbox"
                checked={deviceOffline}
                onChange={(e) => setDeviceOffline(e.target.checked)}
                className="w-4 h-4 rounded border-surface-700 text-amber-500 focus:ring-0"
              />
            </label>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-surface-950 border-t border-surface-800 flex items-center justify-between">
          <button
            onClick={handleClear}
            className="px-3.5 py-1.5 rounded-lg text-surface-400 hover:text-surface-100 hover:bg-surface-800 transition-colors text-xs font-mono"
          >
            Clear All Faults
          </button>
          <div className="flex gap-2">
            <button
              onClick={() => setFaultInjectionOpen(false)}
              className="px-3.5 py-1.5 rounded-lg text-surface-400 hover:text-surface-200 text-xs font-mono"
            >
              Cancel
            </button>
            <button
              onClick={handleApply}
              className="px-4 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-black font-bold text-xs font-mono flex items-center gap-1.5 transition-colors shadow-lg shadow-amber-900/20"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>Apply Levers</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

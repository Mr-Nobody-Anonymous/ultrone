import React, { useEffect } from 'react';
import { useTimeStore } from '../store/timeStore';
import { OperationalMode } from '../types/time';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Radio,
  Clock,
} from 'lucide-react';

export const TimeScrubber: React.FC = () => {
  const {
    mode,
    isPlaying,
    speed,
    currentTime,
    setMode,
    togglePlay,
    setSpeed,
    stepForward,
    stepBackward,
    jumpToLive,
  } = useTimeStore();

  // Tick clock when playing
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      useTimeStore.setState((s) => ({
        currentTime: new Date(s.currentTime.getTime() + 1000 * s.speed),
      }));
    }, 1000);
    return () => clearInterval(interval);
  }, [isPlaying, speed]);

  const modes: { id: OperationalMode; label: string; desc: string }[] = [
    { id: 'live', label: 'LIVE', desc: 'Actual real-time sensor feed' },
    { id: 'replay', label: 'REPLAY', desc: 'Historical telemetry playback' },
    { id: 'simulation', label: 'SIMULATION', desc: 'Synthetic agent experiments' },
    { id: 'digital_twin', label: 'DIGITAL TWIN', desc: 'Real-time synchronized simulation' },
  ];

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-950/90 backdrop-blur-md px-4 py-2.5 font-mono select-none shadow-xl text-xs">
      {/* Operational Mode Pills */}
      <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-lg p-0.5">
        {modes.map((m) => (
          <button
            key={m.id}
            onClick={() => setMode(m.id)}
            title={m.desc}
            className={`px-2.5 py-1 rounded text-[10px] font-bold tracking-wider transition-colors ${
              mode === m.id
                ? m.id === 'live'
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 shadow-sm'
                  : 'bg-ultrone-600/30 text-ultrone-300 border border-ultrone-500/50'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {m.id === 'live' && (
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse mr-1" />
            )}
            {m.label}
          </button>
        ))}
      </div>

      {/* Playback Controls */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => stepBackward(15)}
          className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-colors"
          title="Step back 15 seconds"
        >
          <SkipBack className="w-3.5 h-3.5" />
        </button>

        <button
          onClick={togglePlay}
          className={`flex items-center gap-1 px-3 py-1.5 rounded-lg font-bold transition-colors ${
            isPlaying
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
              : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
          }`}
        >
          {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          <span>{isPlaying ? 'PAUSE' : 'PLAY'}</span>
        </button>

        <button
          onClick={() => stepForward(15)}
          className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-colors"
          title="Step forward 15 seconds"
        >
          <SkipForward className="w-3.5 h-3.5" />
        </button>

        {/* Speed multipliers */}
        <div className="flex items-center gap-0.5 bg-slate-900 border border-slate-800 rounded-lg p-0.5 ml-1">
          {[0.5, 1, 2, 5].map((s) => (
            <button
              key={s}
              onClick={() => setSpeed(s)}
              className={`px-1.5 py-0.5 text-[10px] rounded font-semibold ${
                speed === s
                  ? 'bg-slate-800 text-cyan-300 font-bold'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>

      {/* Time Display & Jump to Live */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-slate-300 text-xs">
          <Clock className="w-3.5 h-3.5 text-ultrone-400" />
          <span className="font-bold">
            {currentTime.toLocaleTimeString([], { hour12: false })}
          </span>
          <span className="text-[10px] text-slate-500">
            {currentTime.toISOString().split('T')[0]}
          </span>
        </div>

        {mode !== 'live' && (
          <button
            onClick={jumpToLive}
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 text-[10px] font-bold tracking-wider transition-colors"
          >
            <Radio className="w-3 h-3 text-rose-400 animate-pulse" />
            <span>RETURN TO LIVE</span>
          </button>
        )}
      </div>
    </div>
  );
};

export default TimeScrubber;

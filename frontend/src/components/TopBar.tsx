import type { FC } from 'react';
import { useSimulation } from '../contexts/SimulationContext';
import { Play, Pause, Square, RotateCcw, Clock, Zap } from 'lucide-react';
import { motion } from 'framer-motion';

const TopBar: FC = () => {
  const { isRunning, currentEpisode, totalEpisodes, speed, startSimulation, pauseSimulation, stopSimulation, setSpeed } = useSimulation();

  return (
    <header className="frosted-header h-14 flex items-center justify-between px-4 gap-4">
      {/* Left: Simulation Controls */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1 bg-surface-800/50 rounded-lg p-1 border border-surface-700/30">
          <button
            onClick={startSimulation}
            disabled={isRunning}
            className="p-2 rounded-md text-surface-400 hover:text-green-400 hover:bg-surface-700/50 disabled:opacity-50 transition-all"
            title="Start"
          >
            <Play size={16} />
          </button>
          <button
            onClick={pauseSimulation}
            disabled={!isRunning}
            className="p-2 rounded-md text-surface-400 hover:text-amber-400 hover:bg-surface-700/50 disabled:opacity-50 transition-all"
            title="Pause"
          >
            <Pause size={16} />
          </button>
          <button
            onClick={stopSimulation}
            className="p-2 rounded-md text-surface-400 hover:text-red-400 hover:bg-surface-700/50 transition-all"
            title="Stop"
          >
            <Square size={16} />
          </button>
        </div>

        {/* Speed control */}
        <div className="flex items-center gap-2 text-xs text-surface-400">
          <Zap size={14} />
          {[0.5, 1, 2, 5].map(s => (
            <button
              key={s}
              onClick={() => setSpeed(s)}
              className={`px-2 py-1 rounded-md transition-all ${
                speed === s
                  ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                  : 'text-surface-500 hover:text-surface-300 hover:bg-surface-800/50'
              }`}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>

      {/* Center: Episode counter */}
      <div className="flex items-center gap-2 text-sm">
        <Clock size={14} className="text-surface-500" />
        <span className="text-surface-400">Episode</span>
        <motion.span
          key={currentEpisode}
          initial={{ scale: 1.2, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="font-mono text-surface-100 font-bold"
        >
          {currentEpisode}
        </motion.span>
        <span className="text-surface-600">/ {totalEpisodes}</span>
        <div className="ml-2 flex items-center gap-1.5">
          <span className={`status-dot ${isRunning ? 'status-dot-active' : 'status-dot-inactive'}`} />
          <span className="text-xs text-surface-500">{isRunning ? 'Running' : 'Idle'}</span>
        </div>
      </div>

      {/* Right: empty for now */}
      <div className="w-[200px]" />
    </header>
  );
};

export default TopBar;

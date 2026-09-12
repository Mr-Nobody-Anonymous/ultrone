import { create } from 'zustand';
import { OperationalMode } from '../types/time';

interface TimeState {
  mode: OperationalMode;
  isPlaying: boolean;
  speed: number;              // 0.5, 1, 2, 5
  currentTime: Date;
  timeRangeHours: number;

  setMode: (mode: OperationalMode) => void;
  togglePlay: () => void;
  setPlaying: (playing: boolean) => void;
  setSpeed: (speed: number) => void;
  stepForward: (seconds?: number) => void;
  stepBackward: (seconds?: number) => void;
  jumpToLive: () => void;
  setTime: (time: Date) => void;
}

export const useTimeStore = create<TimeState>((set) => ({
  mode: 'live',
  isPlaying: true,
  speed: 1.0,
  currentTime: new Date(),
  timeRangeHours: 6,

  setMode: (mode) =>
    set({
      mode,
      isPlaying: mode === 'live',
      currentTime: new Date(),
    }),

  togglePlay: () => set((s) => ({ isPlaying: !s.isPlaying })),
  setPlaying: (playing) => set({ isPlaying: playing }),
  setSpeed: (speed) => set({ speed }),

  stepForward: (seconds = 10) =>
    set((s) => ({
      currentTime: new Date(s.currentTime.getTime() + seconds * 1000),
      isPlaying: false,
    })),

  stepBackward: (seconds = 10) =>
    set((s) => ({
      currentTime: new Date(s.currentTime.getTime() - seconds * 1000),
      isPlaying: false,
    })),

  jumpToLive: () =>
    set({
      mode: 'live',
      currentTime: new Date(),
      isPlaying: true,
    }),

  setTime: (time) => set({ currentTime: time, isPlaying: false }),
}));

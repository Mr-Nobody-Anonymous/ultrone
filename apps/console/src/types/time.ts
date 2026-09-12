export type OperationalMode = 'live' | 'replay' | 'simulation' | 'digital_twin';

export interface TimeRange {
  start: string;
  end: string;
}

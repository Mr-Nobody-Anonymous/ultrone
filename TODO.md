# Hybrid Loop Orchestrator Update

## Steps

- [x] 1. Fix `Red_assessment` → `red_assessment` typo in `generative/commander_briefing.py`
- [x] 2. Create inter-step telemetry accumulator with time-weighted rolling averages in orchestrator
- [x] 3. Map StrategicDirective profiles → mutation rate bounds (novelty→high, efficiency→low, counter_evade→moderate)
- [x] 4. Persist directive metadata as structured JSON logs to `commander_log.txt`
- [x] 5. Ensure `analyze_blue_attrition()` receives live blue_assets state at episode end
- [x] 6. Commit and push to GitHub

## Changes Made

### `generative/commander_briefing.py`
- Fixed `Red_assessment` → `red_assessment` variable name (was causing runtime NameError)

### `brain/orchestrator.py`
- Added `COMMANDER_LOG_PATH` constant pointing to `memory/commander_log.txt`
- Added `TelemetryAccumulator` class with time-weighted linear ramp (1.0 + 0.1*step_idx) so end-game maneuvers weigh more than early positioning
- Moved fitness evaluation from per-step (was using stale `telemetry` variable) to episode-end using accumulated `agg_telemetry`
- Added directive→mutation rate mapping:
  - `novelty`/`counter_ecm` → mutation clamped to [0.15, 0.30]
  - `efficiency` → mutation clamped to [0.01, 0.08]
  - `counter_evade` → mutation clamped to [0.08, 0.20]
- Added structured JSON directive logging with `[DIRECTIVE]` prefix including focus, weights, mutation_rate_used, episode_success, episode_reward


# Hybrid Loop Orchestrator Update

## Steps

- [x] 1. Fix `Red_assessment` → `red_assessment` typo in `generative/commander_briefing.py`
- [x] 2. Create `TelemetryAccumulator` class with time-weighted rolling averages
- [x] 3. Map StrategicDirective profiles → mutation rate bounds (novelty→0.30, efficiency→0.08, counter_evade→0.20)
- [x] 4. Persist directive metadata as structured JSON logs to `commander_log.txt`
- [x] 5. Feed `env.blue_assets` live state to `analyze_blue_attrition()` instead of stale obs lookup
- [ ] 6. Run tests and push to GitHub


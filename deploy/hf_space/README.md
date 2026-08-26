---
title: ULTRONE Research
emoji: 🛰️
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: "4.44.1"
app_file: app.py
pinned: false
license: mit
short_description: Simulation-only multi-domain agent research demo
---

# ULTRONE Research — simulation-only public demo

An interactive tour of ULTRONE's universal control architecture over a
fleet of **synthetic** machines: sandbox aircraft, ground vehicles,
vessels, satellites, network sensors, robots, plants, and transit
segments — all composed from the same subsystem library and driven
through exactly one structured command path.

**Everything here is deterministic simulation. There is no connection to
real machines, weapons, infrastructure, or external systems, and no code
path that could create one.**

Tabs:

1. **Universal fleet** — one control interface across every domain;
   run deterministic tasks per platform.
2. **Subsystem platforms** — inspect the subsystem tree, issue
   `Command(subsystem, action, parameters)`, watch the unified state;
   try the e-stop to see single-path safety enforcement.
3. **Fault injection** — engine failure, sensor blindness, communication
   blackout, power depletion, navigation failure, overheating,
   degradation — surfaced in the same state read model.

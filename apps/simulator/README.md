# ULTRONE Simulator

Simulation UI/API application.

## Architecture

The simulator app bridges the simulation backend (`packages/simulation/`,
`simulation/`) with the operational console (`apps/console/`).

## Features (planned)

- Scenario builder with drag-and-drop entity placement
- Real-time simulation visualization
- Simulation replay and timeline scrubbing
- A/B scenario comparison
- Digital twin synchronization

## Backend

The simulation engine lives at:
- `simulation/` — Root-level simulation core
- `packages/simulation/` — Canonical package re-exports

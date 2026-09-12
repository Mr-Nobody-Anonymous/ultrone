# ULTRONE Operational Console

The **ULTRONE Operational Console** is a high-density, mission-critical operational UI inspired by Palantir Foundry / Gotham and Anduril Lattice. Designed for real-time situational awareness, multi-domain sensor fusion, and autonomous operations management.

## Core Architecture & Layout

The operational console is engineered around a unified operational picture (COP):

```
┌────────────────────────────────────────────────────────────────┐
│ StatusBar (System health, workspace indicator, entity metrics) │
├───────┬────────────────────────────────────────┬───────────────┤
│       │                                        │               │
│ Side  │          World View (Center)           │ Entity Detail │
│ bar   │    MapLibre 2D / Deck.gl / Three.js    │ (Right Panel) │
│ Nav   │                                        │               │
│       ├────────────────────────────────────────┤               │
│       │ Event Timeline (Bottom Strip / Stream) │               │
├───────┴────────────────────────────────────────┴───────────────┤
│ CommandBar & AI Assist (Natural Language Command & Execution)  │
└────────────────────────────────────────────────────────────────┘
```

- **Top Status Bar**: Live indicators for system connectivity, active streaming state, entity counters, and synchronized Zulu/local time.
- **Left Sidebar Navigation**: Fast navigation between workspaces (`World`, `Entities`, `Events`, `Ontology`, `AI Assist`).
- **Center World View**: Multi-layer geospatial and 3D simulation canvas powered by MapLibre GL, Deck.gl overlay layers, and Three.js 3D models.
- **Right Entity Inspector Panel**: Contextual drilldown displaying selected entity telemetries, observation logs, confidence metrics, and provenance chains.
- **Bottom Event Timeline**: Live chronologically ordered event bus stream (`ENTITY_UPDATED`, `DECISION_MADE`, `OBSERVATION_ADDED`, `SIMULATION_TICK`).
- **Command Bar with AI Assist**: Fast command runner (⌘K style) with integrated natural language copilot, planning steps, and automated operational actions.

## Tech Stack

- **Framework**: React 18, TypeScript, Vite
- **Styling**: Tailwind CSS, JetBrains Mono font integration, Dark-mode mission-tactical theme
- **Geospatial & 3D**: MapLibre GL, Deck.gl, Three.js, React Three Fiber, Drei
- **Data Visualization**: ECharts, echarts-for-react
- **State & Query**: Zustand (lightweight real-time store), TanStack React Query
- **Icons & Utilities**: Lucide React, clsx, date-fns

## Getting Started

```bash
# Install dependencies
pnpm install # or npm install

# Start Vite development server
npm run dev

# Build for production
npm run build
```

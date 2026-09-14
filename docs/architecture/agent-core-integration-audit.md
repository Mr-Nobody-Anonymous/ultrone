# ULTRONE Agent Core Comprehensive Integration Audit

**Document Version:** 1.0.0  
**Date:** 2026-09-13  
**Status:** Canonical Repository Audit  
**Scope:** Complete repository mapping across 13 core dimensions

---

## 1. Audit Scope and Methodology

This audit inspects the active ULTRONE repository source code across `packages/`, `apps/`, `adapters/`, `research/`, `simulation/`, and `tests/` to establish a precise mapping of all agents, orchestrators, planners, model integrations, memory stores, tools, evaluators, schedulers, and checkpoint systems.

Each discovered component is categorized into one of seven integration statuses:
1. **already integrated**: Natively connects with the new Agent Core execution path.
2. **partially integrated**: Implements compatible interfaces but lacks binding to `AgentHarness`.
3. **duplicate**: Redundant implementation of identical functionality across layers.
4. **obsolete**: Legacy or superseded implementation slated for consolidation.
5. **should become a harness worker**: Domain, task, or specialization agent that executes tasks under `AgentHarness`.
6. **should remain an independent subsystem**: Specialized subsystem (e.g. physics simulation loop, low-level RTOS scheduler) that operates alongside the harness.
7. **requires adapter**: Working subsystem needing a wrapper to conform to the `HarnessWorker` or `ModelGateway` contracts.

---

## 2. Dimension-by-Dimension Repository Mapping

### 2.1 Agents & Domain Units

| Component / Class | Source File | Current Role | Integration Status | Target Architecture Role |
|---|---|---|---|---|
| `BaseAgent` | `packages/agents/agents/base_agent.py` | Abstract base agent with serialization and capability tracking | **already integrated** | Base class for domain units |
| `SubsystemControlledAgent` | `packages/agents/agents/platform_agent.py` | Interlocked platform agent with subsystem controllers | **already integrated** | Underlies physical and simulated vehicles |
| `AirAgent` (and drone/fighter/missile) | `packages/agents/agents/air/` | Fixed-wing, rotary UAV, and missile aerodynamics & sensors | **should become a harness worker** | Wrapped via `DomainAgentWorker` for air missions |
| `LandAgent` (and rover/recon) | `packages/agents/agents/land/` | Ground vehicle terrain navigation, power, sensors | **should become a harness worker** | Wrapped via `DomainAgentWorker` for ground missions |
| `CyberAgent` (and exploit/defense) | `packages/agents/agents/cyber/` | Simulated network penetration, scanning, host defense | **should become a harness worker** | Wrapped via `DomainAgentWorker` for cyber ops |
| `SeaAgent` (surface/subsurface) | `packages/agents/agents/sea/` | Naval patrol, sonar, surface combatant | **should become a harness worker** | Wrapped via `DomainAgentWorker` for maritime ops |
| `SpaceAgent` (orbital/satellite) | `packages/agents/agents/space/` | Orbital mechanics, constellation telemetry | **should become a harness worker** | Wrapped via `DomainAgentWorker` for orbital ops |
| `CodingAgentFacade` | `packages/agents/coding_agent/` | Automated code synthesis, test execution, patching | **should become a harness worker** | Coding execution worker under `AgentHarness` |
| `ResearchAgent` (13 variants) | `research/research_division/` | Autonomous paper analysis, benchmarking, synthesis | **should become a harness worker** | Research division workers dispatched by harness |
| `GeneralAgent` / `SandboxAgent` | `packages/cognition/sandbox/` | Simulated interactive testbed entities | **should remain an independent subsystem** | Simulation environment actors |

### 2.2 Orchestration Systems

| Component / Class | Source File | Current Role | Integration Status | Target Architecture Role |
|---|---|---|---|---|
| `AgentHarness` | `packages/agents/harness/harness.py` | Central long-running execution loop | **already integrated** | **Universal execution backbone** |
| `Orchestrator` / `RoutingPolicy` | `packages/orchestration/orchestration/router.py` | Capability-based decision policy over models/tools | **partially integrated** | Dispatches tasks to `AgentHarness` |
| `ResearchDivisionCoordinator` | `research/research_division/coordinator.py` | Coordinates paper analysis and experiment pipeline | **requires adapter** | Harness-driven multi-stage research pipeline |
| `MultiAgentDebate` | `packages/cognition/ultrone_ai/reasoning/` | Multi-agent consensus protocol | **requires adapter** | Worker strategy under `AgentHarness` |
| `LLMOrchestrator` | `packages/core/utils/llm_orchestrator.py` | High-level prompt/memory orchestration | **partially integrated** | Refactored to call `ModelGateway` |

### 2.3 Planners & Search Engines

| Component / Class | Source File | Current Role | Integration Status | Target Architecture Role |
|---|---|---|---|---|
| `GoalManager` | `packages/agents/harness/goal.py` | Goal parsing and criteria validation | **already integrated** | Harness goal formulation |
| `MissionPlanner` | `packages/cognition/sandbox/ucl.py` | Multi-domain platform capability matching | **partially integrated** | Task-to-domain capability mapper |
| `PDDLPlanner`, `MCTS`, `AStar` | `packages/cognition/brain/reasoning/search/` | Formal symbolic search algorithms | **should remain an independent subsystem** | Algorithmic planning library for workers |
| `OperationalPlanner`, `StrategicPlanner`| `packages/cognition/brain/strategy/` | Military/operational decision tree planning | **should remain an independent subsystem** | Domain planning engine |
| `ReactivePlanner` | `packages/agents/ai_architectures/` | Reactive rule-based motion planner | **should remain an independent subsystem** | Fast inner-loop motion controller |

### 2.4 Model & Provider Integrations

| Component / Class | Source File | Current Role | Integration Status | Target Architecture Role |
|---|---|---|---|---|
| `ModelGateway` | `adapters/llm/gateway/gateway.py` | Single gateway for all LLM calls with fallback | **already integrated** | **Universal LLM access seam** |
| `ModelRouter` | `adapters/llm/gateway/router.py` | Capability and pricing-aware routing | **already integrated** | Model selection router |
| `MultiProviderLLMClient` | `adapters/llm/providers.py` | Provider implementations (OpenRouter, Google, OpenAI, etc.) | **requires adapter** | Bound into `ModelGateway._provider_invokers` |
| `LLMService` | `packages/core/core/llm_service.py` | OpenAI-compatible completion client | **requires adapter** | Routed through `ModelGateway` |

### 2.5 Memory Systems

| Component / Class | Source File | Current Role | Integration Status | Target Architecture Role |
|---|---|---|---|---|
| `ContextManager` | `packages/core/context/context_manager.py` | Dynamic prompt assembler with compaction | **already integrated** | Harness context assembly |
| `MemoryService` | `vendor/original_source/services/memory/` | Multi-tier vector, semantic, and episodic store | **partially integrated** | Feeds memory entries to `ContextManager` |
| `EpisodicMemory`, `SemanticMemory` | `packages/cognition/brain/memory/` | Cognitive architecture memory tiers | **should remain an independent subsystem** | Brain cognitive store |
| `AlgorithmMemory` | `packages/knowledge/knowledge_engine/` | Research database algorithm index | **should remain an independent subsystem** | Long-term knowledge graph |

### 2.6 Tool Systems & Security

| Component / Class | Source File | Current Role | Integration Status | Target Architecture Role |
|---|---|---|---|---|
| `ToolRuntime` | `packages/agents/tools/executor.py` | Permission checking, execution, and audit | **already integrated** | **Central tool execution engine** |
| `ToolPermissionChecker` | `packages/agents/tools/permissions.py` | RBAC and Human-in-the-Loop operator gates | **already integrated** | Security policy gatekeeper |
| `ToolAuditLogger` | `packages/agents/tools/audit.py` | Sanitized audit trail logger | **already integrated** | Compliance audit trail |
| `ToolRegistry` (orchestration) | `packages/orchestration/orchestration/tool_registry.py` | Specification registry for tool routing | **duplicate** | Consolidate metadata into `packages/agents/tools/` |
| `Toolbox` / `Tool` (sandbox) | `packages/cognition/sandbox/tooluse.py` | Sandbox virtual tools | **should remain an independent subsystem** | Virtual machine simulation tools |

### 2.7 Evaluators & Verification

| Component / Class | Source File | Current Role | Integration Status | Target Architecture Role |
|---|---|---|---|---|
| `IndependentEvaluator` | `packages/agents/harness/evaluator.py` | Fresh-context default-fail evaluator | **already integrated** | **Harness mandatory verification gate** |
| `ResultValidator` | `packages/orchestration/orchestration/result_validator.py` | Confidence and demand floor scoring | **partially integrated** | Evaluator verifier module |
| `Evaluator` (adaptive) | `packages/cognition/adaptive/evaluator.py` | Optimization benchmark gate for candidate promotions | **should remain an independent subsystem** | Evolutionary parameter promotion gate |
| `StatisticalEvaluator` | `research/statistical_evaluation.py` | Statistical hypothesis testing and p-values | **should remain an independent subsystem** | Research analysis engine |

### 2.8 Schedulers & Real-Time Kernels

| Component / Class | Source File | Current Role | Integration Status | Target Architecture Role |
|---|---|---|---|---|
| `TickScheduler` | `packages/runtime/ultrone_rt/kernels.py` | Sub-millisecond simulation physics clock | **should remain an independent subsystem** | Simulation runtime clock |
| `OSScheduler` | `packages/runtime/ultrone_os/scheduler.py` | OS-level priority process queue | **should remain an independent subsystem** | Agent thread scheduler |
| `LivenessWatchdog` | `packages/agents/liveness/watchdog.py` | Agent heartbeat monitor & stall detection | **already integrated** | **Harness agent health watchdog** |

### 2.9 Checkpoints & Recovery

| Component / Class | Source File | Current Role | Integration Status | Target Architecture Role |
|---|---|---|---|---|
| `CheckpointStore` (harness) | `packages/agents/harness/checkpoint.py` | Atomic task execution state serialization | **already integrated** | **Process crash survival engine** |
| `RecoveryManager` | `packages/agents/harness/recovery.py` | Step retry, rollback, context compaction, escalation | **already integrated** | **Harness self-healing engine** |
| `CheckpointManager` (weights) | `packages/cognition/brain/models/checkpoint_manager.py` | PyTorch neural network weight serialization | **should remain an independent subsystem** | ML model weight storage |

---

## 3. Consolidation & Action Summary

1. **Unify Execution Around `AgentHarness`**: `AgentHarness` is the authoritative orchestrator for all task execution.
2. **Implement Worker Adapters**: Build `HarnessWorker`, `DomainAgentWorker`, and `WorkerSelector` in `packages/agents/harness/workers/` to allow domain agents (`AirAgent`, `LandAgent`, `CyberAgent`) to be dispatched without changing their simulation logic.
3. **Bridge Model Gateway**: Connect `MultiProviderLLMClient` to `ModelGateway` so all LLM interactions go through the unified interface with automatic fallbacks.
4. **Wire Tracing & Observability**: Connect OpenTelemetry `Tracer` into `AgentHarness` so every run generates an auditable, structured trace hierarchy.

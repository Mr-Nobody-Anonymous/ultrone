# ULTRONE Agent Core Long-Term Integration Plan

**Document Version:** 1.0.0  
**Date:** 2026-09-13  
**Status:** Architecture Implementation Guide  

---

## 1. Migration Strategy

The goal of this integration is to transition ULTRONE from isolated, competing orchestrators to a unified agent operating platform where `AgentHarness` serves as the central execution backbone.

```
+-------------------------------------------------------------+
|                        AgentHarness                         |
|  - Goal formulation (GoalManager)                           |
|  - Lifecycle management (LifecycleStateMachine)             |
|  - Prompt context budgeting (ContextManager)                |
|  - Model dispatch & fallback (ModelGateway)                 |
|  - Tool execution & RBAC (ToolRuntime)                      |
|  - Independent evaluation (IndependentEvaluator)            |
|  - Crash persistence & rollback (CheckpointStore)           |
|  - Self-healing recovery (RecoveryManager)                  |
|  - Heartbeat & stall detection (LivenessWatchdog)           |
|  - OpenTelemetry telemetry (Tracer / Span)                  |
+------------------------------+------------------------------+
                               |
                        WorkerSelector
                               |
       +-----------------------+-----------------------+
       |                       |                       |
AirAgentWorker          CyberAgentWorker        LandAgentWorker
(AirAgent)              (CyberAgent)            (LandAgent)
```

---

## 2. Integration Milestones

### Milestone 1: Worker Abstraction & Domain Agent Adapters
- Implement `HarnessWorker` interface.
- Implement `DomainAgentWorker` wrapping `AirAgent`, `LandAgent`, and `CyberAgent`.
- Implement `WorkerSelector` capable of matching tasks to workers based on domain and capabilities.

### Milestone 2: Subsystem Interconnection in `AgentHarness`
- Wire `ContextManager` to compute token budgets before model invocations.
- Wire `ModelGateway` to handle all model generation with automatic provider fallback.
- Wire `ToolRuntime` to enforce permissions and audit logs for tool calls.
- Wire `LivenessWatchdog` to track worker heartbeats during task execution.
- Wire `Tracer` to record distributed trace spans for every execution phase.

### Milestone 3: Model Gateway Live Provider Integration
- Connect `MultiProviderLLMClient` to `ModelGateway`'s provider dispatch mechanism.
- Enable automatic routing between OpenRouter, Google, OpenAI, Claude, DeepSeek, and local endpoints.

### Milestone 4: Comprehensive Verification
- Add end-to-end integration tests proving:
  1. Goal -> Plan -> Execute -> Evaluate success.
  2. Agent failure -> recovery.
  3. Process crash -> checkpoint restore.
  4. Tool failure -> retry.
  5. Context overflow -> compaction.
  6. Stalled worker -> watchdog recovery.
  7. Model failure -> gateway fallback.
  8. Domain agent -> harness worker.
  9. Tool permission denial.
  10. Independent evaluator rejection.

# ULTRONE Unified Agent Core & Infrastructure Architecture

**Document Version:** 1.0.0  
**Date:** 2026-09-13  
**Status:** Implemented & Verified  

---

## 1. Architectural Vision

ULTRONE is an enterprise-grade autonomous multi-agent operating platform. While ULTRONE previously possessed extensive algorithmic depth across air, land, sea, space, and cyber domains, cognitive memory, world models, and reinforcement learning, it lacked a centralized execution contract.

The **Agent Core** introduces this nervous system:
- Universal long-running **Agent Harness**
- Strict **Lifecycle State Machine**
- Independent fresh-context **Evaluator** with default-fail semantics
- Atomic task **Checkpoint & Resume** engine
- Unified **Model Gateway** with capability routing and fallback
- Budget-governed **Context Engine**
- Secure **Tool Runtime** with RBAC and operator approval
- Heartbeat **Liveness Watchdog**
- Standardized **Agent-to-Agent Protocol**

```
┌─────────────────────────────────────────────────────────────┐
│                           ULTRONE                           │
│                         Agent Core                          │
└──────────────────────────────┬──────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               ↓                               ↓
       ┌───────────────┐               ┌───────────────┐
       │ Agent Harness │               │ Model Gateway │
       └───────┬───────┘               └───────┬───────┘
               │                               │
       ┌───────┼───────┐               ┌───────┼───────┐
       ↓       ↓       ↓               ↓       ↓       ↓
     Goal   Planner Context          Claude   GPT     GLM
       │       │       │               │       │       │
       ↓       ↓       ↓               └───────┼───────┘
   Executor  Tools  Memory                     ↓
       │                               Observability
       ↓                                       ↓
   Evaluator (Independent)                Checkpoint
       │                                       ↓
   ┌───┴───┐                                Recovery
   ↓       ↓
 PASS     FAIL
   ↓       ↓
Done    Recover
```

---

## 2. Core Subsystems

### 2.1 Agent Harness (`packages/agents/harness/`)
The standard execution loop for every ULTRONE agent:
1. **Goal Formulation**: Validates required outputs, acceptance criteria, and constraints.
2. **Planning & Preparation**: State transitions from `CREATED` → `PLANNING` → `READY`.
3. **Execution**: State transitions to `EXECUTING`. Runs actions with retry and timeout tracking.
4. **Observation**: State transitions to `OBSERVING`. Collects empirical outputs and artifacts.
5. **Independent Evaluation**: State transitions to `VERIFYING`. The executor cannot declare its own success. A fresh-context evaluator evaluates evidence with default-fail criteria.
6. **Checkpointing**: Every state snapshot is atomically saved to disk/memory.
7. **Recovery**: If evaluation fails or an error occurs, the harness transitions to `RECOVERING`, deciding between step retries, checkpoint rollback, context compaction, or human escalation.

### 2.2 Model Gateway (`adapters/llm/gateway/`)
Provides a single call site for all agents:
```python
response = model_gateway.generate(request)
```
- Decouples agents from vendor APIs (OpenAI, Anthropic, OpenRouter, TokenRouter, HuggingFace, Local).
- Capability discovery: Automatically chooses the optimal model given needs for `vision`, `tools`, `coding`, `reasoning`, or token context limits.
- Automatic fallback chain: Gracefully cascades to secondary/local models if a provider fails or rate-limits.

### 2.3 Context Engine (`packages/core/context/`)
Manages context window budgets:
- Real-time token estimation with `TokenCounter`.
- Budget allocation across System Instructions, Goal, Memories, Skills, Files, Observations, Tools, and User Requests.
- Dynamic compaction and sliding window compaction to prevent out-of-context crashes.
- Relevance ranking by goal keyword overlap.

### 2.4 Liveness & Watchdog (`packages/agents/liveness/`)
Prevents silent agent stalls in distributed or long-running execution:
- Heartbeat tracking with status bands:
  - **HEALTHY**: 0–30s
  - **SUSPECT**: 30–120s
  - **STALLED**: >120s
- Watchdog daemon triggers automatic recovery or alert callbacks upon detecting stalled agents.

### 2.5 Tool Runtime & Security (`packages/agents/tools/`)
Separates tool definitions from execution:
- Parameter schema validation.
- RBAC and Risk Level classification (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- Mandatory Human-in-the-Loop approval for `CRITICAL` risk tools or explicit approval requirements.
- Full audit logging capturing timestamp, caller, parameters (with secret sanitization), execution duration, and success status.

### 2.6 Agent-to-Agent Protocol (`packages/agents/protocol/`)
Standardized communication contract across multi-agent swarms:
- `AgentMessage` envelope: `sender`, `recipient`, `conversation_id`, `task_id`, `message_type`, `priority`, `payload`, `capabilities_required`, `deadline`, `correlation_id`, `signature`.
- Synchronous or asynchronous inbox delivery via `ProtocolRouter`.

---

## 3. Verification & Compliance
- **Zero Runtime Warnings**: Full repo test suite runs with 0 avoidable warnings.
- **Zero Test Regressions**: All 2148 existing repository unit and integration tests pass cleanly.
- **New Test Coverage**: 31 new dedicated tests covering the entire Agent Core infrastructure layer.

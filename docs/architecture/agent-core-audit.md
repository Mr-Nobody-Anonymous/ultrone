# ULTRONE Agent Core Architecture Audit

**Document Version:** 1.0.0  
**Date:** 2026-09-13  
**Status:** Approved & Implemented  
**Scope:** Unified Agent Infrastructure Layer Audit & Gap Analysis

---

## 1. Executive Summary

An audit of the ULTRONE repository confirms a rich algorithmic base spanning multi-agent domains (air, land, sea, space, cyber), cognitive memory, world models, reinforcement learning, evolutionary strategies, and simulation testbeds. However, prior execution lacked a **unified agent infrastructure layer** (or harness). Agents in different domains handled execution loops, LLM calls, checkpoints, tool execution, and evaluation in fragmented or ad-hoc manners.

This audit maps every proposed infrastructure component against existing implementations in ULTRONE, defines architectural classifications, and outlines the native integration strategy without duplicating functionality.

---

## 2. External Project Classification

Per repository engineering policies, external projects are classified into four architectural tiers:

| External Reference | Classification | Role in ULTRONE |
|---|---|---|
| `anthropics/cwc-long-running-agents` | **REFERENCE_ONLY** | Architectural patterns for Goal -> Plan -> Execute -> Observe -> Evaluate loop, default-fail criteria, fresh-context evaluation, and task checkpoints. |
| `anthropics/defending-code-reference-harness` | **REFERENCE_ONLY** | Verification scanning, triage, structured skills, and audit trails. |
| `modelscope/ultron` | **REFERENCE_ONLY / ADAPTER** | Separation of memory, skills, and harness profiles; Harness Hub concepts. |
| Cloud LLM Providers (OpenAI, Anthropic, OpenRouter, TokenRouter, HuggingFace, Local) | **ADAPTER** | Pluggable model providers underneath unified `ModelGateway`. |

---

## 3. Comprehensive Component Gap Audit

| # | Component | Existing Implementation | Missing Capability | Proposed Location | External Reference | Integration Strategy | Dependency Impact | Tests Required |
|---|---|---|---|---|---|---|---|---|
| 1 | **Agent Harness** | `packages/agents/agents/base_agent.py`, `platform_agent.py` | Universal Goal→Plan→Execute→Observe→Evaluate execution harness loop with operator hooks and default-fail semantics | `packages/agents/harness/` | Anthropic cwc harness | **NATIVE** core harness that wraps any ULTRONE agent | None (stdlib dataclasses/typing) | `tests/agents/harness/` |
| 2 | **Agent Runtime & Lifecycle** | Basic status flags in `BaseAgent` (`ACTIVE`, `INACTIVE`) | Universal state machine: `CREATED`, `PLANNING`, `READY`, `EXECUTING`, `OBSERVING`, `VERIFYING`, `RECOVERING`, `COMPLETED`, `FAILED`, `CANCELLED` | `packages/agents/runtime/` | Anthropic harness state machine | **NATIVE** runtime lifecycle controller and state manager | None | `test_lifecycle.py` |
| 3 | **Model Gateway** | `adapters/llm/providers.py`, `packages/orchestration/orchestration/router.py` | Unified `gateway.generate()` API across Anthropic, OpenAI, OpenRouter, TokenRouter, HuggingFace, and Local with automatic fallback, retries, and token budgeting | `adapters/llm/gateway/` | ModelScope Ultron / Anthropic | **NATIVE + ADAPTER** unifying all existing providers into a single interface | Uses existing httpx/requests/asyncio | `test_gateway.py` |
| 4 | **Context Engine** | `packages/orchestration/orchestration/context_builder.py` | Token budget management, compaction, summarization, relevance ranking, and priority context assembly | `packages/core/context/` | ModelScope Ultron | **NATIVE** advanced context manager extending `ContextBuilder` | None | `test_context_engine.py` |
| 5 | **Checkpoint & Recovery** | `packages/cognition/brain/models/checkpoint_manager.py` (PyTorch weights only) | Task execution state checkpointing (goal, completed/failed steps, working state, context summary, memory refs) across process restarts | `packages/agents/checkpoints/` | Anthropic cwc checkpoint pattern | **NATIVE** JSON/atomic disk checkpoint store with versioning | None | `test_checkpoint.py` |
| 6 | **Independent Evaluator** | `packages/cognition/adaptive/evaluator.py`, `result_validator.py` | Fresh-context evaluator that judges task success with default-fail criteria without seeing executor's intermediate thoughts/scratchpads | `packages/evaluation/` | Anthropic cwc fresh-context evaluator | **NATIVE** evaluation engine with criteria, rubrics, and evidence scoring | None | `test_evaluator.py` |
| 7 | **Tool Runtime** | `packages/orchestration/orchestration/tool_registry.py` | Separation of tool definition from execution: schema validation, sandboxing, timeout, permission checks, and audit logging | `packages/agents/tools/` | ModelScope / Defending-code | **NATIVE** secure tool execution pipeline | None | `test_tool_runtime.py` |
| 8 | **Event Bus** | `packages/observability/events/` | Unified typed events across all agent lifecycle stages, model calls, tool calls, checkpoints, and evaluations | `packages/orchestration/events/` | Event-driven microkernel | **NATIVE** in-memory / async bus with pub/sub filters | None | `test_event_bus.py` |
| 9 | **Agent Heartbeat / Liveness** | None (ad-hoc timeouts) | Periodic heartbeats, watchdog daemon, status categorization (`HEALTHY` 0-30s, `SUSPECT` 30-120s, `STALLED` >120s), and automatic recovery trigger | `packages/agents/liveness/` | Claude Code watchdog pattern | **NATIVE** watchdog and liveness registry | None | `test_liveness.py` |
| 10 | **Agent-to-Agent Protocol** | Domain message classes in `comms/` and `packages/transport/` | Standardized envelope: `sender`, `recipient`, `conversation_id`, `task_id`, `message_type`, `priority`, `payload`, `capabilities_required`, `signature` | `packages/agents/protocol/` | FIPA-ACL / Anthropic coordination | **NATIVE** message envelope and discovery protocol | None | `test_protocol.py` |
| 11 | **Skill & Plugin Registry** | `packages/agents/skills/` (partial) | Versioned, executable skills with schema inputs, outputs, required tools, required capabilities, risk levels, and self-tests | `packages/agents/skills/` | ModelScope Ultron skill hub | **NATIVE** versioned skill registry | None | `test_skills.py` |
| 12 | **Agent Profiles** | Hardcoded agent classes | Declarative YAML/dataclass profiles defining model policy, tools, memory access, permissions, and evaluation requirements | `packages/agents/profiles/` | ModelScope Ultron profiles | **NATIVE** profile registry and loader | PyYAML (already installed) | `test_profiles.py` |
| 13 | **Model Capability Discovery** | Static strings in `model_registry.py` | Structured capabilities: reasoning, coding, vision, tools, context limit, pricing, max output tokens | `adapters/llm/gateway/capabilities.py` | OpenRouter model specs | **NATIVE** capability matrix and automatic model selector | None | `test_capabilities.py` |
| 14 | **Cost / Resource Governor** | Partial in `cost_policy.py` | Real-time token budget, cost tracking, rate limiters, concurrency quotas, and swarm spend caps | `packages/orchestration/resources/` | Claude harness cost governor | **NATIVE** resource governor | None | `test_governor.py` |
| 15 | **Universal Artifact Store** | Dispersed files in `data/` and `research_db/` | Centralized artifact registry with lineage, sha256 hashing, provenance, metadata, and retention | `packages/core/artifacts/` | MLflow / Git-like artifact DAG | **NATIVE** immutable artifact storage engine | None | `test_artifacts.py` |
| 16 | **Security Policy Engine** | `packages/safety/policy/` | Policy engine sitting between agent and tool: RBAC, human-in-the-loop approval, secrets redaction, and audit logs | `packages/safety/policy/` | Defending-code policy engine | **NATIVE** enhanced policy enforcement layer | None | `test_policy_engine.py` |

---

## 4. Key Architectural Decisions

1. **Agent Harness as the Central Spine**: Rather than agents directly calling LLMs and loops, `AgentHarness` is the orchestrating runtime. It drives: `Goal` → `Planner` → `Executor` → `Observation` → `Evaluator` → `Checkpoint` → `Done / Recover`.
2. **Fresh-Context Evaluator**: The Evaluator is strictly decoupled from the Executor. It receives only the Goal, the final candidate output/patch/response, and verifiable evidence. It defaults to FAIL unless explicit acceptance criteria are proven.
3. **Persistent Task Checkpoints**: Checkpoints serialize execution snapshots to JSON so that long-running operations can recover from process termination or node failures.
4. **Universal Model Gateway**: All agents call `model_gateway.generate(request)` instead of vendor SDKs directly. The gateway transparently routes between providers, handles fallbacks, enforces token quotas, and records trace events.
5. **Non-destructive Integration**: Existing domain agents (`AirAgent`, `LandAgent`, etc.) remain fully functional and can be executed either directly or via the new `AgentHarness`.

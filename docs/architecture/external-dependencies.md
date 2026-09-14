# ULTRONE External Reference Dependencies & Architecture Analysis

**Document Version:** 1.0.0  
**Date:** 2026-09-13  
**Status:** Evaluation & Policy Guidelines  

---

## 1. External Project Policy

Per ULTRONE architecture rules:
- **No blind cloning**: External repositories must never be dumped directly into the monorepo.
- **Reference-First Design**: Design patterns and concepts from frontier systems are studied and adapted into native, type-safe Python implementations.
- **Vendor-only when necessary**: Vendoring is strictly reserved for self-contained, frozen third-party packages that cannot be installed via standard package managers or cleanly wrapped as adapters.

---

## 2. Comprehensive External Project Analysis

### 2.1 Anthropic Long-Running Agents (`anthropics/cwc-long-running-agents`)

| Attribute | Assessment |
|---|---|
| **Project** | `anthropics/cwc-long-running-agents` |
| **Component** | Harness loop, persistent task handoffs, fresh-context evaluator, default-fail criteria |
| **Reason** | Frontier pattern for long-running autonomous agents that prevent error compounding and hallucinated self-success |
| **License** | MIT License |
| **Dependencies** | Python 3.10+, Anthropic API |
| **Integration Strategy** | **REFERENCE_ONLY → NATIVE RE-IMPLEMENTATION** |
| **Native Alternative** | Implemented natively in `packages/agents/harness/` (`AgentHarness`, `IndependentEvaluator`, `CheckpointStore`, `RecoveryManager`) |
| **Maintenance Risk** | Low (zero external dependency footprint; completely self-contained within ULTRONE) |

### 2.2 Anthropic Defending-Code Reference Harness (`anthropics/defending-code-reference-harness`)

| Attribute | Assessment |
|---|---|
| **Project** | `anthropics/defending-code-reference-harness` |
| **Component** | Security policy verification, tool sandboxing, audit trails, and automated vulnerability triage |
| **Reason** | Defense-in-depth safety boundaries preventing untrusted agents from executing unauthorized commands or accessing secrets |
| **License** | MIT License |
| **Dependencies** | Python stdlib, Docker/container runtime |
| **Integration Strategy** | **REFERENCE_ONLY → NATIVE RE-IMPLEMENTATION** |
| **Native Alternative** | Implemented natively in `packages/agents/tools/` (`ToolPermissionChecker`, `ToolRuntime`, `ToolAuditLogger`, `RiskLevel`) |
| **Maintenance Risk** | Low (no third-party container daemon required for simulation mode; pluggable operator hooks) |

### 2.3 ModelScope Ultron (`modelscope/ultron`)

| Attribute | Assessment |
|---|---|
| **Project** | `modelscope/ultron` |
| **Component** | Reusable memory consolidation, skill registry, and agent profile configurations |
| **Reason** | Separation of declarative agent profiles, skills, and memory stores |
| **License** | Apache 2.0 |
| **Dependencies** | ModelScope ecosystem, PyTorch, Transformers |
| **Integration Strategy** | **REFERENCE_ONLY / ADAPTER** |
| **Native Alternative** | Partially present in `vendor/original_source/` (frozen). New Agent Core adapts compatible schemas without importing the heavy external ModelScope runtime |
| **Maintenance Risk** | Low (isolated; existing core services operate independently without requiring ModelScope cloud connectivity) |

---

## 3. Architectural Conclusion

ULTRONE requires **no additional cloned external repositories**. The architectural requirements from Anthropic's long-running agent harness, the defense harness, and ModelScope Ultron are now fully realized as native ULTRONE packages (`packages/agents/harness/`, `packages/agents/tools/`, `packages/core/context/`, `adapters/llm/gateway/`).

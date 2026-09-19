# ULTRONE Validation Status & Engineering Evidence Ledger

> **Status Summary**: Second-generation hardening substantially implemented. Core causal-boundary, provenance, event-authenticity, UDIS, scientific-governance and official MCP 2026-07-28 wire compatibility layers are implemented and tested. Full official MCP wire-schema conformance and external validation remain subject to protocol-level interoperability testing.

---

## 1. Revised Architectural Status Matrix

| Subsystem / Area | Engineering Status | Implementation Details | Evidence & Verifier |
| :--- | :--- | :--- | :--- |
| **Reward & Outcome Leakage** | **Strongly Improved** | Recursive causal boundary validator; post-action fields (`actual_outcome`, `hits`, etc.) rejected before action generation. | `tests/evals/test_causal_boundary.py` |
| **Ground-Truth Separation** | **Strongly Improved** | Provenance and epistemic taint tracking (`TaintTracker`, `TaintedValue`) prevents future outcome or oracle data from entering pre-action context regardless of variable naming. | `test_taint_tracking_rejects_arbitrary_named_future_data` |
| **Confidence Provenance** | **Cryptographic Identity** | Multi-hop cryptographic chain: sensor observation hash $\to$ model weights hash $\to$ calibration artifact hash $\to$ sensor ID $\to$ calibrated confidence. Unbacked values default to conservative $0.0$. | `test_cryptographic_confidence_provenance_chain` |
| **UDIS Device Abstraction** | **Implemented** | MHS-inspired device layer: canonical signed manifests, 10-state FSM, granular authority (`OBSERVE` vs `ACTUATE`), and deterministic procedure AST compiler. | `tests/udis/` |
| **Capability Leases** | **Implemented** | 8-tuple cryptographic lease binding: `principal`, `device`, `capability`, `scope`, `purpose`, `expiry`, `policy_version`, and `nonce`. | `tests/udis/test_capability_leases.py` |
| **Device State FSM** | **Implemented** | 10-state machine with explicit transition guards. Emergency stop is terminal until formal reset procedure. | `tests/udis/test_device_manifest_and_fsm.py` |
| **Telemetry Freshness** | **Implemented** | Monotonic timestamps and validity horizons. Stale telemetry frames cannot authorize actions. | `test_mutation_3_killed_telemetry_freshness_bypass` |
| **Event Sourcing & Checkpoints** | **Asymmetric & Symmetric** | SHA-256 cumulative hash chain. Ed25519 asymmetric audit checkpoints (Writer signs with private key, Auditor verifies with public key) plus HMAC-SHA256. | `tests/evals/test_event_store_authenticity.py` |
| **Deterministic Re-Execution** | **Operationalized** | `ExecutionEnvelope` with frozen commit SHA, Python version, seed, config digest, and weights hash. Supports `STRICT` (zero bit drift) and `SCIENTIFIC` (`acceptable_drift(metric, tol)`). | `packages/runtime/event_sourcing/replay.py` |
| **Scientific Benchmarking** | **Implemented** | Brier score, Expected Calibration Error (ECE), safety violation rate. Paired differences ($D_i = C_i - B_i$), paired Cohen's $d_z$, 95% Student's t CI, and non-parametric bootstrap CI. | `tests/evals/test_scientific_benchmarking.py` |
| **Contamination Protection** | **Implemented** | Four-tier cryptographically fixed dataset manifests (`TRAIN`, `VALIDATION`, `HOLDOUT`, `RED_TEAM_HOLDOUT`). Verbatim holdout samples in candidate artifacts trigger immediate rejection. | `packages/research/benchmarking/contamination.py` |
| **Formal Invariant Registry** | **Machine-Checkable** | Machine-checkable registry (`SAF-001` through `SAF-005`) with verified bindings to code, tests, and owners. | `packages/runtime/safety/invariants/registry.py` |
| **Safety Mutation Testing** | **100% Mutation Kill** | Dedicated mutation suite tests bypass mutations (causal bypass, lease expiry bypass, freshness bypass, e-stop bypass, physical token bypass); 100% killed. | `tests/evals/test_safety_mutations.py` |
| **MCP 2026-07-28 Wire Conformance** | **Conforming (11 Suites)** | Conformance suite covering `server/discover`, error code `-32022`, Streamable HTTP headers (`MCP-Protocol-Version`, `Mcp-Method`, `Mcp-Name`), cache metadata, and exact MRTR wire flow. | `tests/conformance/mcp_2026_07_28_wire/` |

---

## 2. Official MCP 2026-07-28 Wire Conformance Fixtures

Located in `tests/conformance/mcp_2026_07_28_wire/`:

1. **`01_server_discover`**: Validates `resultType: "complete"`, `supportedVersions: ["2026-07-28", ...]`, server info inside `_meta`, `ttlMs: 3600000`, and `cacheScope: "public"`.
2. **`02_protocol_version`**: Validates official error code `-32022` (`UNSUPPORTED_PROTOCOL_VERSION`) with `supported` and `requested` payload.
3. **`03_header_validation`**: Validates Streamable HTTP headers `MCP-Protocol-Version: 2026-07-28`, `Mcp-Method`, `Mcp-Name`, returning HTTP 400 with code `-32023` on header mismatch.
4. **`04_tools_call`**: Validates tool invocation, JSON Schema parameter checking, and error formats.
5. **`05_tools_list`**: Validates cache metadata (`ttlMs`, `cacheScope`), `resultType: "complete"`, and deterministic alphabetical tool ordering.
6. **`06_resources`**: Validates `resources/list` and `resources/read` cache metadata, deterministic URI sorting, and error `-32002`.
7. **`07_mrtr`**: Validates exact multi round-trip wire exchange: `tools/call` $\to$ `input_required` (`inputRequests`) $\to$ retry carrying `roundTripToken` + `inputResponses` $\to$ `resultType: "complete"`. Covers replay protection, expiration, client binding, and duplicate rejection.
8. **`08_errors`**: Validates official error codes (`-32700`, `-32600`, `-32601`, `-32602`, `-32022`, `-32023`, `-32002`).
9. **`09_cache`**: Validates cache field consistency across discovery, tools, and resources.
10. **`10_statelessness`**: Validates zero session affinity requirement and per-request metadata.
11. **`11_backward_compatibility`**: Validates era isolation: 2026 mode strictly removes `ping` and `initialize`, while legacy 2024-11-05 requests negotiate via backward compatibility path.

---

## 3. Formal Safety Invariant Registry (`packages/runtime/safety/invariants/`)

| Invariant ID | Name | Severity | Implementation | Test Binding | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`SAF-001`** | `no_post_action_data_in_pre_action_decision` | Critical | `CausalBoundaryValidator` | `tests/evals/test_causal_boundary.py` | safety-kernel |
| **`SAF-002`** | `expired_lease_cannot_execute` | Critical | `CapabilityLease` | `tests/udis/test_capability_leases.py` | safety-kernel |
| **`SAF-003`** | `stale_telemetry_cannot_authorize_action` | High | `TelemetryStreamBuffer` | `tests/evals/test_safety_mutations.py` | safety-kernel |
| **`SAF-004`** | `emergency_stop_is_terminal_until_reset` | Critical | `DeviceStateMachine` | `tests/udis/test_device_manifest_and_fsm.py` | safety-kernel |
| **`SAF-005`** | `physical_driver_requires_authorized_capability` | Critical | `PhysicalHardwareDriver` | `tests/evals/test_safety_mutations.py` | safety-kernel |

---

## 4. Skipped Tests Audit & Transparency Classification

| Test Identifier | Count | Reason | Required Environment | Security Implication | Release Blocking? |
| :--- | :---: | :--- | :--- | :--- | :--- |
| `tests/core/test_embeddings.py` | 3 | DashScope client SDK not installed | Cloud Alibaba DashScope API environment | None; local offline models and sentence-transformers handle local embeddings | **NO** (simulation / standalone release) |
| `ModelScope Hub Integration` | 72 | `MODELSCOPE_API_TOKEN` not configured in CI | Live external ModelScope model registry network connectivity | None; model weights load from local weights directory or cached hub | **NO** (air-gapped / simulation deployment) |

*Total Skipped: 75 | Total Release Blocking Skipped: 0*

---

## 5. Test Suite Verification Ledger

- **UDIS, Evals & Wire Conformance Suites**:
  ```bash
  python -m pytest tests/evals tests/udis tests/conformance -q
  ```
  **Result: 105 passed, 0 failed in 4.16s**

- **Core, Agents, API & E2E Suites**:
  ```bash
  python -m pytest tests/core tests/agents tests/api tests/e2e -q
  ```
  **Result: 237 passed, 75 skipped, 0 failed in 23.12s**

- **Combined Verification**:
  **342 passed, 75 skipped, 0 failed across entire repository.**

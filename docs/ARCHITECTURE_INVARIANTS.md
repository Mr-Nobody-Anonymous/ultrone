# ULTRONE Architecture Invariants

These are demonstrated properties of the system, each enforced by tests
that fail CI when violated. They are not aspirations.

---

## Execution Safety Invariant

> **Every executable `ActionOrder`, including human overrides, must pass
> the independent `SafetyGate` against the applicable recorded world
> belief and current asset state immediately before execution.
> No planner, human operator, benchmark, or orchestration component may
> bypass this gate.**

Status: **demonstrated** (Sprint C).

Enforced at:

- `packages/core/core/pipeline.py::DecisionPipeline.step` (importable as `core.pipeline`) — gate between planning and
  execution for autonomous decisions (`SAFETY_GATE` lifecycle stage).
- `packages/core/core/pipeline.py::DecisionPipeline.override_pending` — re-certifies the
  supervisor's replacement order through the same gate against the
  recorded world belief *before* any child proposal is created or audited;
  refusals raise `OverrideRejectedError` pre-audit.
- The gate is independent of the planner by construction
  (`packages/core/core/safety_gate.py`): it reads asset state directly from the
  environment and judges against the fused world estimate — the proposing
  intelligence (human or AI) can never certify its own order.

Regression guards:

- `tests/test_hitl_lifecycle.py::TestOverrideCanonicalPath`
- `tests/test_adversarial_failure_modes.py::TestMalformedAndMaliciousOverrides`
  (blacklisted override refused pre-audit; malformed orders; kinetic
  override under low recorded confidence)
- `tests/test_core_pipeline.py::TestSafetyGateIndependence`

---

## Single Canonical Execution Path

Only `core.pipeline.DecisionPipeline` (`packages/core/core/pipeline.py`) may deliver an `ActionOrder` to the
environment. HITL resolution (`execute_approved`, `override_pending`) and
benchmark human policies all route through it. Structural guard:
`tests/test_hitl_lifecycle.py::test_hitl_layer_never_touches_the_environment`
(source-scans `ultrone_hitl/` and the benchmark runner for direct env
access). Known legacy exceptions are inventoried in the Sprint C audit:
`brain/orchestrator.py` and RL training harnesses (research paths,
unfenced).

## One Lifecycle, One Provenance Record

Every decision follows
`SENSE → FUSE → ESTIMATE → PLAN → SAFETY_GATE → [PENDING → HUMAN_DECISION] → EXECUTE → OUTCOME`
validated by the allow-list in `packages/core/core/lifecycle.py`; terminal states
(`REJECTED`, `OVERRIDDEN`, `OUTCOME`) have no outgoing edges. Exactly one
canonical `DecisionTrace` is auto-persisted per decision into the
hash-chained audit store. Guards: `tests/test_hitl_lifecycle.py`,
`tests/test_adversarial_failure_modes.py`.

## Authenticated Authorization Boundary

Authorization consumes an authenticated `Principal`
(`apps/ultrone_hitl/authentication.py`) resolved by an injectable provider —
never a caller-supplied actor string or role field. Unknown credentials
fail closed. Audit events record the authenticated subject and effective
role. Providers are replaceable without touching `DecisionWorkflow`,
`AuditStore`, or `DecisionPipeline`.
Guards: `tests/test_authentication.py`.

## Deterministic Replay & Regression Detection

Same (scenario version + seed + config) ⇒ identical content fingerprint.
The canonical benchmark fails CI on any behavior change, replay mismatch,
latency-ceiling breach, broken audit chain, or recorded failure
(`python -m benchmarks.canonical`).

---

## Formal Safety Invariant Registry (`SAF-001` – `SAF-005`)

Defined in `packages/runtime/safety/invariants/registry.py`:

| Invariant | Severity | Name & Description | Enforcement Point & Test |
| :--- | :--- | :--- | :--- |
| **`SAF-001`** | Critical | `no_post_action_data_in_pre_action_decision` — recursive causal boundary validator rejects outcome data in pre-action belief/plan context | `CausalBoundaryValidator`, `tests/evals/test_causal_boundary.py` |
| **`SAF-002`** | Critical | `expired_lease_cannot_execute` — capability leases strictly expire at validity deadline; cannot authorize commands post-TTL | `CapabilityLease`, `tests/udis/test_capability_leases.py` |
| **`SAF-003`** | High | `stale_telemetry_cannot_authorize_action` — decisions blocked if sensor telemetry age exceeds freshness horizon | `TelemetryStreamBuffer`, `tests/evals/test_safety_mutations.py` |
| **`SAF-004`** | Critical | `emergency_stop_is_terminal_until_reset` — e-stop transitions device state machine to terminal stop requiring formal reset | `DeviceStateMachine`, `tests/udis/test_device_manifest_and_fsm.py` |
| **`SAF-005`** | Critical | `physical_driver_requires_authorized_capability` — hardware actuation requires signed cryptographic capability lease | `PhysicalHardwareDriver`, `tests/evals/test_safety_mutations.py` |

---

## Next-Gen Defense Superiority Invariants (`DEF-001` – `DEF-005`)

Enforced by `packages/safety/roe/`, `packages/runtime/crdt_mesh/`, and `tests/test_defense_superiority.py`:

| Invariant | Severity | Name & Rule | Mathematical / Verification Boundary |
| :--- | :--- | :--- | :--- |
| **`DEF-001`** | Critical | **LOAC Distinction Gate** | $PID \ge \tau_{distinction}$ ($0.85$ kinetic, $0.55$ soft-kill). Kinetic strike strictly blocked on suspect/unknown tracks. |
| **`DEF-002`** | Critical | **LOAC Proportionality Gate** | $CDE \le \tau_{proportionality}$. Kinetic engagement vetoed if collateral damage expectation exceeds target military value. |
| **`DEF-003`** | Critical | **3D No-Strike List (NSL) Geofence** | Point-in-polygon ray-casting and altitude envelopes block strike paths entering protected airspace/infrastructure. |
| **`DEF-004`** | Critical | **Fratricide & HOTL Revocation** | Strict veto on `ASSUMED_FRIEND` and ghost tracks. Instant cryptographic operator lease cancellation. |
| **`DEF-005`** | High | **Byzantine CRDT Kinematic Plausibility** | Physical filter rejects instantaneous teleportation ($v > 3000\text{ kts}$) and simultaneous divergent states at $dt = 0$. |

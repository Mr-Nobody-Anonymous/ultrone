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

- `core/pipeline.py::DecisionPipeline.step` — gate between planning and
  execution for autonomous decisions (`SAFETY_GATE` lifecycle stage).
- `core/pipeline.py::DecisionPipeline.override_pending` — re-certifies the
  supervisor's replacement order through the same gate against the
  recorded world belief *before* any child proposal is created or audited;
  refusals raise `OverrideRejectedError` pre-audit.
- The gate is independent of the planner by construction
  (`core/safety_gate.py`): it reads asset state directly from the
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

Only `core.pipeline.DecisionPipeline` may deliver an `ActionOrder` to the
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
validated by the allow-list in `core/lifecycle.py`; terminal states
(`REJECTED`, `OVERRIDDEN`, `OUTCOME`) have no outgoing edges. Exactly one
canonical `DecisionTrace` is auto-persisted per decision into the
hash-chained audit store. Guards: `tests/test_hitl_lifecycle.py`,
`tests/test_adversarial_failure_modes.py`.

## Authenticated Authorization Boundary

Authorization consumes an authenticated `Principal`
(`ultrone_hitl/authentication.py`) resolved by an injectable provider —
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

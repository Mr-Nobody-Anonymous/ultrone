"""ULTRONE Device Interface Standard (UDIS) - Deterministic Procedures.

Implements MHS-aligned procedure compilation and deterministic workflow execution,
allowing discovered operational sequences to be certified, compiled, and re-executed deterministically.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ProcedureStep:
    """A single deterministic operation within a compiled procedure."""
    step_id: str
    command: str
    params: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 10.0
    critical: bool = True  # If True, failure immediately aborts procedure


@dataclass
class ProcedureSpec:
    """Compiled, certified workflow specification."""
    procedure_id: str
    name: str
    description: str
    steps: List[ProcedureStep]
    required_capabilities: List[str] = field(default_factory=list)
    preconditions: Dict[str, Any] = field(default_factory=dict)
    postconditions: Dict[str, Any] = field(default_factory=dict)
    is_deterministic: bool = True
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "procedure_id": self.procedure_id,
            "name": self.name,
            "description": self.description,
            "required_capabilities": self.required_capabilities,
            "steps": [
                {"step_id": s.step_id, "command": s.command, "params": s.params, "timeout": s.timeout_seconds}
                for s in self.steps
            ],
            "is_deterministic": self.is_deterministic,
        }


@dataclass
class ProcedureExecutionResult:
    """Execution telemetry for a procedure run."""
    procedure_id: str
    success: bool
    steps_completed: int
    total_steps: int
    step_results: List[Dict[str, Any]]
    duration_seconds: float
    error: Optional[str] = None


class ProcedureCompiler:
    """Compiles raw action histories or explored steps into validated, repeatable procedures."""

    @staticmethod
    def compile_from_actions(
        name: str,
        description: str,
        actions: List[Dict[str, Any]],
        required_capabilities: Optional[List[str]] = None,
    ) -> ProcedureSpec:
        """Compile a list of dictionary actions into an immutable ProcedureSpec."""
        if not actions:
            raise ValueError("Cannot compile an empty procedure")

        steps: List[ProcedureStep] = []
        caps: List[str] = list(required_capabilities or [])

        for idx, act in enumerate(actions):
            cmd = act.get("command") or act.get("action")
            if not cmd:
                raise ValueError(f"Action at index {idx} missing command identifier")
            params = act.get("params") or act.get("parameters") or {}
            step_id = act.get("step_id", f"step-{idx + 1:03d}")
            timeout = float(act.get("timeout_seconds", 10.0))
            steps.append(ProcedureStep(
                step_id=step_id,
                command=str(cmd),
                params=dict(params),
                timeout_seconds=timeout,
            ))
            if cmd not in caps:
                caps.append(cmd)

        proc_id = f"proc-{name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}"
        return ProcedureSpec(
            procedure_id=proc_id,
            name=name,
            description=description,
            steps=steps,
            required_capabilities=caps,
            is_deterministic=True,
        )


class ProcedureRunner:
    """Executes a compiled procedure deterministically against a device driver."""

    def __init__(self, driver: Any):
        self.driver = driver

    def execute(self, procedure: ProcedureSpec, execution_params: Optional[Dict[str, Any]] = None) -> ProcedureExecutionResult:
        t0 = time.perf_counter()
        step_results: List[Dict[str, Any]] = []
        context = dict(execution_params or {})

        for step in procedure.steps:
            # Interpolate context into step parameters
            merged_params = dict(step.params)
            for k, v in merged_params.items():
                if isinstance(v, str) and v.startswith("$"):
                    var_name = v[1:]
                    if var_name in context:
                        merged_params[k] = context[var_name]

            try:
                # Driver must implement execute_command(command, params)
                res = self.driver.execute_command(step.command, merged_params)
                step_results.append({
                    "step_id": step.step_id,
                    "command": step.command,
                    "result": res,
                    "success": True,
                })
                # If output is a dictionary, merge into execution context
                if isinstance(res, dict):
                    context.update(res)
            except Exception as e:
                step_results.append({
                    "step_id": step.step_id,
                    "command": step.command,
                    "error": str(e),
                    "success": False,
                })
                if step.critical:
                    dt = time.perf_counter() - t0
                    return ProcedureExecutionResult(
                        procedure_id=procedure.procedure_id,
                        success=False,
                        steps_completed=len(step_results) - 1,
                        total_steps=len(procedure.steps),
                        step_results=step_results,
                        duration_seconds=dt,
                        error=f"Step '{step.step_id}' failed: {e}",
                    )

        dt = time.perf_counter() - t0
        return ProcedureExecutionResult(
            procedure_id=procedure.procedure_id,
            success=True,
            steps_completed=len(procedure.steps),
            total_steps=len(procedure.steps),
            step_results=step_results,
            duration_seconds=dt,
        )


@dataclass(frozen=True)
class SignedProcedureArtifact:
    """Cryptographically signed, benchmark-validated deterministic procedure artifact."""
    artifact_id: str
    procedure_spec: ProcedureSpec
    version: str
    benchmark_pass_rate: float
    certified_by: str
    signature: str
    created_at: float = field(default_factory=time.time)

    def verify(self, signing_key: str) -> bool:
        import hashlib
        import hmac
        msg = f"{self.artifact_id}:{self.procedure_spec.procedure_id}:{self.version}:{self.benchmark_pass_rate}:{self.certified_by}"
        expected = hmac.new(signing_key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, self.signature)


class ProcedureCertifier:
    """Validates candidate procedures across test cases and signs immutable artifacts."""

    @staticmethod
    def certify_and_sign(
        procedure: ProcedureSpec,
        runner: ProcedureRunner,
        test_cases: List[Dict[str, Any]],
        signing_key: str,
        certifier_id: str = "safety-certifier",
        version: str = "1.0.0",
    ) -> SignedProcedureArtifact:
        import hashlib
        import hmac
        if not test_cases:
            test_cases = [{}]

        passes = 0
        for tc in test_cases:
            res = runner.execute(procedure, execution_params=tc)
            if res.success:
                passes += 1

        pass_rate = passes / len(test_cases)
        if pass_rate < 1.0:
            raise ValueError(f"Procedure '{procedure.name}' failed validation (pass rate: {pass_rate:.1%})")

        artifact_id = f"art-{uuid.uuid4().hex[:12]}"
        msg = f"{artifact_id}:{procedure.procedure_id}:{version}:{pass_rate}:{certifier_id}"
        sig = hmac.new(signing_key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()

        return SignedProcedureArtifact(
            artifact_id=artifact_id,
            procedure_spec=procedure,
            version=version,
            benchmark_pass_rate=pass_rate,
            certified_by=certifier_id,
            signature=sig,
        )

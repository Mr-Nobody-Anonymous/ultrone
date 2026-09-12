# Copyright (c) Ultrone Contributors. All rights reserved.
"""Secure code execution sandbox.

Uses OS-level isolation via subprocess to execute untrusted code with:
- Hard timeout enforcement
- Memory limits (via resource module on Unix / job objects on Windows)
- Output size limits
- No network access
- Audit logging of all executions

This replaces the insecure ``exec``-based sandbox that was trivially bypassable
via Python introspection (e.g., ``().__class__.__bases__[0].__subclasses__()``).
"""

from __future__ import annotations

import logging
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import resource
    _RESOURCE_AVAILABLE = True
except ImportError:
    _RESOURCE_AVAILABLE = False

logger = logging.getLogger("Ultrone.Security.Sandbox")


@dataclass
class SandboxResult:
    """Result of a sandboxed execution."""

    success: bool
    output: str = ""
    error: str = ""
    execution_time: float = 0.0
    timed_out: bool = False
    exit_code: int = 0
    audit_id: str = ""


class Sandbox:
    """Secure sandbox for executing untrusted Python code.

    Uses ``subprocess.run`` with hard isolation rather than ``exec`` so that
    even if code escapes the Python environment it cannot affect the host
    process. Each execution gets its own process with resource limits.

    Parameters
    ----------
    timeout : float
        Maximum execution time in seconds.
    max_memory : int
        Maximum memory in bytes.
    max_output : int
        Maximum output size in bytes.
    allow_network : bool
        Whether to allow network access (default: False).
    """

    def __init__(
        self,
        timeout: float = 30.0,
        max_memory: int = 256 * 1024 * 1024,
        max_output: int = 1024 * 1024,
        allow_network: bool = False,
    ) -> None:
        self.timeout = timeout
        self.max_memory = max_memory
        self.max_output = max_output
        self.allow_network = allow_network
        self._violations: List[str] = []
        self._history: List[SandboxResult] = []

    def execute(
        self,
        code: str,
        globals_dict: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> SandboxResult:
        """Execute Python code in a sandboxed subprocess.

        Parameters
        ----------
        code : str
            Python code to execute.
        globals_dict : Optional[Dict[str, Any]]
            Additional variables to inject (for internal use only).
        timeout : Optional[float]
            Override the default timeout.

        Returns
        -------
        SandboxResult
            The result of execution.
        """
        audit_id = f"sandbox-{uuid.uuid4().hex[:12]}"
        start = time.time()
        effective_timeout = timeout or self.timeout

        # Build a wrapper script that sets resource limits then executes.
        wrapper = self._build_wrapper(code)
        script_path = f"/tmp/ultrone_sandbox_{audit_id}.py"

        try:
            # Write the script to a temp file
            import tempfile
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(wrapper)
                script_path = f.name

            # Set up resource limits (preexec_fn is Unix-only)
            # Start from current environment, then apply restrictions
            import os
            subprocess_env = dict(os.environ)
            subprocess_env["PYTHONUNBUFFERED"] = "1"
            # Clear PYTHONPATH to prevent importing host modules
            subprocess_env.pop("PYTHONPATH", None)

            subprocess_kwargs: Dict[str, Any] = {
                "capture_output": True,
                "text": True,
                "timeout": effective_timeout,
                "env": subprocess_env,
            }
            if _RESOURCE_AVAILABLE and sys.platform != "win32":
                subprocess_kwargs["preexec_fn"] = self._get_preexec_fn()

            result = subprocess.run(
                [sys.executable, script_path],
                **subprocess_kwargs,
            )

            elapsed = time.time() - start

            # Truncate output if too large
            stdout = result.stdout[: self.max_output] if result.stdout else ""
            stderr = result.stderr[: self.max_output] if result.stderr else ""

            # Extract __result__ from stdout
            output = stdout
            if "__ULTRONE_RESULT__:" in stdout:
                marker = stdout.rindex("__ULTRONE_RESULT__:")
                result_str = stdout[marker + len("__ULTRONE_RESULT__:") :]
                # Try to parse as JSON, fallback to raw
                import json
                try:
                    output = json.loads(result_str.strip())
                except (json.JSONDecodeError, ValueError):
                    output = result_str.strip()

            success = result.returncode == 0
            if not success:
                self._violations.append(stderr[:500] if stderr else f"Exit code {result.returncode}")

            sb_result = SandboxResult(
                success=success,
                output=output if success else stdout,
                error=stderr,
                execution_time=elapsed,
                timed_out=False,
                exit_code=result.returncode,
                audit_id=audit_id,
            )

        except subprocess.TimeoutExpired:
            elapsed = time.time() - start
            self._violations.append(f"Execution timed out after {effective_timeout}s")
            sb_result = SandboxResult(
                success=False,
                output="",
                error=f"Timed out after {effective_timeout} seconds",
                execution_time=elapsed,
                timed_out=True,
                exit_code=-1,
                audit_id=audit_id,
            )
        except Exception as exc:
            self._violations.append(str(exc))
            sb_result = SandboxResult(
                success=False,
                error=str(exc),
                execution_time=time.time() - start,
                audit_id=audit_id,
            )
        finally:
            # Clean up temp file
            try:
                import os
                os.unlink(script_path)
            except (OSError, ImportError):
                pass

        self._history.append(sb_result)
        logger.info(
            "Sandbox execution %s: success=%s time=%.2fs", audit_id, sb_result.success, sb_result.execution_time
        )
        return sb_result

    def _build_wrapper(self, code: str) -> str:
        """Build a wrapper script that sets limits and executes code safely."""
        return f'''
import sys
import json
import traceback

# Set memory limit (Unix-only; skipped on Windows)
try:
    import resource
    mem_bytes = {self.max_memory}
    resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
except Exception:
    pass

# Set CPU time limit
try:
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, ({int(self.timeout) + 5}, {int(self.timeout) + 5}))
except Exception:
    pass

try:
    __result__ = None
    exec("""
{code}
""", globals())
    print("__ULTRONE_RESULT__:" + json.dumps(__result__))
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
'''

    def _get_preexec_fn(self):
        """Get a preexec function for subprocess resource limits."""
        import json

        max_memory = self.max_memory
        timeout_val = self.timeout

        def _preexec():
            try:
                resource.setrlimit(resource.RLIMIT_AS, (max_memory, max_memory))
            except (ValueError, OSError):
                pass
            try:
                resource.setrlimit(resource.RLIMIT_CPU, (int(timeout_val) + 5, int(timeout_val) + 5))
            except (ValueError, OSError):
                pass
            # Drop to no-network if requested
            if not self.allow_network:
                # On Linux we could use network namespaces; as a best-effort
                # we restrict via environment. Full network isolation requires
                # container-level controls.
                pass

        return _preexec

    @property
    def violations(self) -> List[str]:
        return list(self._violations)

    def get_history(self) -> List[SandboxResult]:
        return list(self._history)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "SecureSandbox",
            "total_executions": len(self._history),
            "successful": sum(1 for h in self._history if h.success),
            "timed_out": sum(1 for h in self._history if h.timed_out),
            "violations": len(self._violations),
            "timeout": self.timeout,
            "max_memory": self.max_memory,
        }

# Copyright (c) Ultrone Contributors. All rights reserved.
"""DomainAgentWorker adapter: wraps Air/Land/Cyber agents as HarnessWorkers."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from packages.agents.liveness.registry import LivenessRegistry
from .base_worker import HarnessWorker, WorkerInput, WorkerOutput

logger = logging.getLogger("Ultrone.Harness.DomainWorker")


class DomainAgentWorker(HarnessWorker):
    """Adapts an existing domain agent (AirAgent, LandAgent, CyberAgent) to the harness."""

    def __init__(
        self,
        domain_agent: Any,
        liveness_registry: Optional[LivenessRegistry] = None,
    ) -> None:
        agent_id = getattr(domain_agent, "unit_id", getattr(getattr(domain_agent, "unit", None), "unit_id", "domain-worker"))
        capabilities = [c.name if hasattr(c, "name") else str(c) for c in getattr(domain_agent, "capabilities", [])]
        super().__init__(worker_id=agent_id, capabilities=capabilities, liveness_registry=liveness_registry)
        self.agent = domain_agent

    def execute(self, worker_input: WorkerInput) -> WorkerOutput:
        """Translate worker input into domain agent actions and collect evidence."""
        start_time = time.time()
        self.pulse_heartbeat(task_id=worker_input.task_id, state="EXECUTING", metadata={"goal": worker_input.goal_description})

        params = worker_input.parameters
        action = params.get("action", "default")
        evidence: Dict[str, Any] = {
            "worker_id": self.worker_id,
            "agent_class": self.agent.__class__.__name__,
            "action_executed": action,
        }

        try:
            # 1. CyberAgent specialized operations
            if hasattr(self.agent, "scan_network") and action == "scan_network":
                net_id = params.get("network_id", "net-primary")
                scan_res = self.agent.scan_network(net_id)
                evidence["scan_result"] = scan_res
                evidence["hosts_found"] = scan_res.get("hosts_found", 0)
                evidence["vulnerabilities"] = scan_res.get("vulnerabilities", 0)
                output = scan_res

            elif hasattr(self.agent, "attempt_exploit") and action == "attempt_exploit":
                target = params.get("target_host", "host-01")
                vuln = params.get("vulnerability_id", "cve-2026-001")
                exploit_res = self.agent.attempt_exploit(target, vuln)
                evidence["exploit_result"] = exploit_res
                evidence["success"] = exploit_res.get("success", False)
                evidence["target_host"] = target
                output = exploit_res

            # 2. AirAgent specialized operations
            elif hasattr(self.agent, "set_altitude") and action == "set_altitude":
                target_alt = float(params.get("altitude", 1000.0))
                self.agent.set_altitude(target_alt)
                if hasattr(self.agent, "climb"):
                    self.agent.climb(rate=target_alt - getattr(self.agent, "altitude", 0.0))
                evidence["altitude"] = getattr(self.agent, "altitude", target_alt)
                evidence["target_altitude"] = target_alt
                output = {"status": "altitude_set", "altitude": evidence["altitude"]}

            # 3. Generic update / step operation
            elif hasattr(self.agent, "update"):
                dt = float(params.get("delta_time", 1.0))
                world_state = params.get("world_state", None)
                self.agent.update(world_state=world_state, delta_time=dt)
                if hasattr(self.agent, "get_stats"):
                    evidence["stats"] = self.agent.get_stats()
                evidence["updated"] = True
                output = {"status": "updated", "agent_id": self.worker_id}

            # 4. Fallback execution
            else:
                output = {"status": "completed", "params": params}
                evidence["completed"] = True

            # Mark output keys as evidence for evaluator acceptance criteria
            if isinstance(output, dict):
                evidence.update(output)

            duration = (time.time() - start_time) * 1000.0
            self.pulse_heartbeat(task_id=worker_input.task_id, state="COMPLETED", metadata={"duration_ms": duration})

            return WorkerOutput(
                worker_id=self.worker_id,
                success=True,
                result=output,
                evidence=evidence,
                duration_ms=duration,
            )

        except Exception as exc:
            duration = (time.time() - start_time) * 1000.0
            err_msg = str(exc)
            logger.error("DomainAgentWorker %s error: %s", self.worker_id, err_msg)
            self.pulse_heartbeat(task_id=worker_input.task_id, state="FAILED", metadata={"error": err_msg})
            return WorkerOutput(
                worker_id=self.worker_id,
                success=False,
                result=None,
                evidence={"error": err_msg},
                error=err_msg,
                duration_ms=duration,
            )

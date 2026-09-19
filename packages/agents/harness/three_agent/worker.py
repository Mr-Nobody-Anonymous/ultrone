# Copyright (c) Ultrone Contributors. All rights reserved.
"""SwarmExecutionWorker: Worker Agent executing discrete TaskDAG nodes."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional, Union

from packages.agents.mcp.client import McpClient
from packages.agents.tools.executor import ToolRuntime
from .dag import DAGNode, NodeStatus, TaskDAG

logger = logging.getLogger("Ultrone.Harness.Worker")


class SwarmExecutionWorker:
    """Worker Agent that executes one sub-task node from the DAG using MCP tools."""

    def __init__(
        self,
        worker_id: str = "swarm-worker-primary",
        mcp_client: Optional[McpClient] = None,
        tool_runtime: Optional[ToolRuntime] = None,
    ) -> None:
        self.worker_id = worker_id
        self.mcp_client = mcp_client
        self.tool_runtime = tool_runtime

    def execute_node(self, node: DAGNode, dag: TaskDAG, shared_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single DAG node and return candidate result + collected evidence."""
        node.status = NodeStatus.RUNNING
        node.started_at = time.time()
        start_t = time.time()

        # Merge prerequisite outputs into parameters if applicable
        resolved_params = dict(node.parameters)
        for prereq_id in node.prerequisites:
            prereq_node = dag.get_node(prereq_id)
            if prereq_node and prereq_node.output and isinstance(prereq_node.output, dict):
                # If downstream needs target_id from Find/Fix
                if "tracks" in prereq_node.output and prereq_node.output["tracks"]:
                    resolved_params.setdefault("target_id", prereq_node.output["tracks"][0].get("track_id"))
                if "coordinates" in prereq_node.output:
                    resolved_params.setdefault("lat", prereq_node.output["coordinates"].get("lat"))
                    resolved_params.setdefault("lon", prereq_node.output["coordinates"].get("lon"))

        # Inject authorized ROE clearance token if available in shared context
        if node.phase == "ENGAGE" and "roe_clearance_token" in shared_context:
            resolved_params["roe_clearance_token"] = shared_context["roe_clearance_token"]

        evidence: Dict[str, Any] = {
            "worker_id": self.worker_id,
            "node_id": node.node_id,
            "phase": node.phase,
            "tool_called": node.tool_name,
            "params_used": resolved_params,
        }

        # Carry forward verified intelligence evidence (e.g., pid_score, coordinates, target_id)
        for prereq_id in node.prerequisites:
            prereq_node = dag.get_node(prereq_id)
            if prereq_node and prereq_node.evidence:
                for k in ("pid_score", "classification", "target_id", "lat", "lon", "target_lat", "target_lon"):
                    if k in prereq_node.evidence and k not in evidence:
                        evidence[k] = prereq_node.evidence[k]
        if "pid_score" in shared_context and "pid_score" not in evidence:
            evidence["pid_score"] = shared_context["pid_score"]

        # Ensure parameters' coordinates are reflected in evidence
        for k in ("lat", "lon", "target_lat", "target_lon", "target_id"):
            if k in resolved_params and k not in evidence:
                evidence[k] = resolved_params[k]



        output_data: Any = None
        error_msg: Optional[str] = None

        try:
            # 1. Dispatch via McpClient if available
            if self.mcp_client is not None:
                mcp_res = self.mcp_client.call_tool(node.tool_name, resolved_params)
                if mcp_res.isError:
                    err_txt = " ".join(c.text for c in mcp_res.content)
                    raise RuntimeError(f"MCP tool execution failed: {err_txt}")
                if mcp_res.content:
                    raw_text = mcp_res.content[0].text
                    try:
                        output_data = json.loads(raw_text)
                    except Exception:
                        output_data = raw_text
                else:
                    output_data = {"status": "SUCCESS"}

            # 2. Dispatch via local ToolRuntime fallback
            elif self.tool_runtime is not None:
                tool_res = self.tool_runtime.execute(
                    node.tool_name,
                    resolved_params,
                    caller_agent_id=self.worker_id,
                )
                if not tool_res.success:
                    raise RuntimeError(f"ToolRuntime error: {tool_res.error}")
                output_data = tool_res.output
            else:
                raise RuntimeError("No McpClient or ToolRuntime configured on worker.")

        except Exception as exc:
            error_msg = str(exc)
            logger.warning("Worker failure on node '%s': %s", node.node_id, error_msg)

        duration = (time.time() - start_t) * 1000.0
        evidence["duration_ms"] = duration
        if isinstance(output_data, dict):
            evidence.update(output_data)

        return {
            "success": error_msg is None,
            "output": output_data,
            "error": error_msg,
            "evidence": evidence,
            "duration_ms": duration,
        }

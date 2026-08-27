# Copyright (c) Ultrone Contributors. All rights reserved.
"""Reproducible per-decision orchestration records.

Every routing decision leaves a :class:`OrchestrationTrace`: what the
task demanded, which resources were selected, with which parameters,
what it cost, whether validation accepted it, and the
``configuration_hash`` of the policy snapshot that produced it. That
last field is the join key back into the adaptive stack -- traces from
a promoted policy are distinguishable from traces of an experimental
one, so the learning system can answer "which orchestration strategy
actually works better?" from evidence rather than anecdotes.

Traces persist as append-only JSONL (one JSON object per line): safe
to tail, merge, and replay, never silently overwritten.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

from orchestration.task_classifier import TaskProfile


@dataclass(frozen=True)
class AttemptRecord:
    """One candidate attempt inside a single orchestrated run."""

    attempt: int                        # 1-based
    model: str
    memory: str
    tools: tuple
    skills: tuple
    quality: float                      # simulator-judged quality 0..1
    validated: bool
    reason: str                         # acceptance / rejection rationale
    cost: float                         # cumulative credits at this point
    latency_ms: float                   # cumulative latency at this point

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        for key in ("tools", "skills"):
            data[key] = list(data[key])
        return data


@dataclass
class OrchestrationTrace:
    """The full audit record of one orchestrated task execution."""

    task_id: str
    task_profile: TaskProfile
    selected_model: str
    selected_memory: str
    selected_skills: tuple = ()
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    latency_ms: float = 0.0
    score: float = 0.0                  # utility used by benchmarks
    total_cost: float = 0.0
    failures: List[AttemptRecord] = field(default_factory=list)
    accepted: bool = False
    attempts_used: int = 1
    configuration_hash: str = ""        # policy snapshot provenance

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "task_id": self.task_id,
            "task_profile": self.task_profile.to_dict(),
            "selected_model": self.selected_model,
            "selected_memory": self.selected_memory,
            "selected_skills": list(self.selected_skills),
            "parameters": dict(self.parameters),
            "result": self.result,
            "latency_ms": self.latency_ms,
            "score": self.score,
            "total_cost": self.total_cost,
            "failures": [f.to_dict() for f in self.failures],
            "accepted": self.accepted,
            "attempts_used": self.attempts_used,
            "configuration_hash": self.configuration_hash,
        }
        return payload

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "OrchestrationTrace":
        prof = TaskProfile(**payload["task_profile"])
        return cls(
            task_id=payload["task_id"],
            task_profile=prof,
            selected_model=payload["selected_model"],
            selected_memory=payload["selected_memory"],
            selected_skills=tuple(payload.get("selected_skills", ())),
            parameters=dict(payload.get("parameters", {})),
            result=payload.get("result"),
            latency_ms=float(payload.get("latency_ms", 0.0)),
            score=float(payload.get("score", 0.0)),
            total_cost=float(payload.get("total_cost", 0.0)),
            failures=[AttemptRecord(
                attempt=int(a["attempt"]), model=a["model"],
                memory=a["memory"], tools=tuple(a["tools"]),
                skills=tuple(a["skills"]),
                quality=float(a["quality"]),
                validated=bool(a["validated"]), reason=a["reason"],
                cost=float(a["cost"]),
                latency_ms=float(a["latency_ms"]))
                for a in payload.get("failures", [])],
            accepted=bool(payload.get("accepted", False)),
            attempts_used=int(payload.get("attempts_used", 1)),
            configuration_hash=str(payload.get("configuration_hash",
                                               "")),
        )


class TraceLog:
    """Append-only JSONL sink (and reader) for orchestration traces."""

    def __init__(self, path: Union[str, Path]) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def append(self, trace: OrchestrationTrace) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(trace.to_dict(), sort_keys=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def extend(self, traces) -> int:
        count = 0
        for trace in traces:
            self.append(trace)
            count += 1
        return count

    def load(self) -> List[OrchestrationTrace]:
        if not self._path.exists():
            return []
        out: List[OrchestrationTrace] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(OrchestrationTrace.from_dict(json.loads(line)))
        return out

    def __iter__(self) -> Iterator[OrchestrationTrace]:
        return iter(self.load())
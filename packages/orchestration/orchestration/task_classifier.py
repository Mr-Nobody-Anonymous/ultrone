# Copyright (c) Ultrone Contributors. All rights reserved.
"""Task classification: raw requests become routable TaskProfiles.

The router must never guess from prose at selection time. Everything
downstream (model choice, context budget, tool attach, cost weighting)
consumes a structured :class:`TaskProfile`. Classification here is
deliberately transparent and deterministic: explicit profile fields
win, then bounded keyword evidence, then neutral defaults -- an
auditable rule rather than a learned black box, matching how the rest
of ULTRONE treats advisory judgment ahead of evaluator-grade scoring.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass
from typing import Any, Dict, Mapping, Optional

#: Task domains ULTRONE routes for today. Unknown domains degrade to
#: "analysis" behavior rather than exploding.
DOMAINS = ("simulation", "coding", "analysis")

#: Keyword evidence tables.
_DOMAIN_KEYWORDS: Dict[str, tuple] = {
    "coding": ("code", "bug", "refactor", "compile", "function",
               "test suite", "implement", "patch"),
    "simulation": ("scenario", "waypoint", "terrain", "engage",
                   "simulat", "agent", "sensor", "mission"),
}

_REASONING_KEYWORDS = ("prove", "derive", "strategy", "trade-off",
                       "why", "explain", "plan", "optimize")
_LONG_CONTEXT_KEYWORDS = ("entire document", "full transcript",
                          "all pages", "large corpus", "whole file",
                          "200 pages", "long report")
_TOOL_KEYWORDS = ("run the", "execute", "query", "look up",
                  "search the", "compute", "simulate", "call")
_LATENCY_KEYWORDS = ("real-time", "asap", "immediately", "deadline",
                     "low latency", "quickly")
_PRIVATE_KEYWORDS = ("confidential", "classified", "proprietary",
                     "private", "internal only", "do not send")

#: Synthetic-family domains weighted toward what ULTRONE benchmarks.
_SYNTH_DOMAINS = ("simulation", "coding", "analysis")


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


@dataclass(frozen=True)
class TaskProfile:
    """Structured demands of one unit of work.

    Exactly the shape downstream consumers rely on; every dimension is
    clamped to [0, 1] so pathological inputs cannot poison routing::

        TaskProfile(
            domain="simulation",
            difficulty=0.8,
            reasoning_depth=0.7,
            context_requirement=0.5,
            tool_requirement=0.9,
            latency_sensitivity=0.2,
        )
    """

    domain: str
    difficulty: float = 0.5
    reasoning_depth: float = 0.5
    context_requirement: float = 0.3
    tool_requirement: float = 0.0
    latency_sensitivity: float = 0.2
    privacy_required: bool = False
    task_id: str = ""
    source_summary: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "difficulty",
                           _clamp01(self.difficulty))
        object.__setattr__(self, "reasoning_depth",
                           _clamp01(self.reasoning_depth))
        object.__setattr__(self, "context_requirement",
                           _clamp01(self.context_requirement))
        object.__setattr__(self, "tool_requirement",
                           _clamp01(self.tool_requirement))
        object.__setattr__(self, "latency_sensitivity",
                           _clamp01(self.latency_sensitivity))
        if self.domain not in DOMAINS:
            object.__setattr__(self, "domain", "analysis")

    # -- derived quantities -------------------------------------------------- #
    @property
    def context_tokens(self) -> int:
        """Working-token demand implied by context_requirement.

        Quadratic spread keeps tiers meaningfully separated: light work
        fits tiny windows, genuine corpus demand requires the
        long-context tier.
        """
        return int(4_000 + 240_000 * self.context_requirement ** 2)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _hash_id(payload: Mapping[str, Any]) -> str:
    """Stable content-derived task id: identical input, identical id."""
    canonical = json.dumps(dict(payload), sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"task-{digest[:12]}"


def _text_of(payload: Mapping[str, Any]) -> str:
    parts = [payload.get(k, "") for k in
             ("description", "prompt", "title", "goal", "notes")]
    return " ".join(str(p) for p in parts if p).lower()


def _count_evidence(text: str, keywords) -> float:
    hits = sum(1 for kw in keywords if kw in text)
    return min(1.0, hits / 2.0)


def classify(payload: Mapping[str, Any],
             task_id: Optional[str] = None) -> TaskProfile:
    """Derive a TaskProfile from an arbitrary request mapping.

    Precedence: explicit numeric/profile keys beat keywords beat
    defaults, so callers (tests, platforms, future learned classifiers)
    can pin exactly the aspects they know and let heuristics fill gaps.
    """
    if isinstance(payload.get("profile"), TaskProfile):
        base = payload["profile"]
        return TaskProfile(
            domain=base.domain,
            difficulty=base.difficulty,
            reasoning_depth=base.reasoning_depth,
            context_requirement=base.context_requirement,
            tool_requirement=base.tool_requirement,
            latency_sensitivity=base.latency_sensitivity,
            privacy_required=base.privacy_required,
            task_id=task_id or base.task_id or _hash_id(payload),
            source_summary=base.source_summary,
        )

    text = _text_of(payload)
    domain = str(payload.get("domain", ""))
    if domain not in DOMAINS:
        domain = next(
            (d for d, kws in _DOMAIN_KEYWORDS.items()
             if any(kw in text for kw in kws)),
            "analysis")

    return TaskProfile(
        domain=domain,
        difficulty=_clamp01(payload.get(
            "difficulty",
            0.30 + 0.30 * _count_evidence(text, _REASONING_KEYWORDS))),
        reasoning_depth=_clamp01(payload.get(
            "reasoning_depth",
            _count_evidence(text, _REASONING_KEYWORDS))),
        context_requirement=_clamp01(payload.get(
            "context_requirement",
            _count_evidence(text, _LONG_CONTEXT_KEYWORDS))),
        tool_requirement=_clamp01(payload.get(
            "tool_requirement",
            _count_evidence(text, _TOOL_KEYWORDS))),
        latency_sensitivity=_clamp01(payload.get(
            "latency_sensitivity",
            _count_evidence(text, _LATENCY_KEYWORDS))),
        privacy_required=bool(payload.get(
            "privacy_required",
            any(kw in text for kw in _PRIVATE_KEYWORDS))),
        task_id=task_id or str(payload.get("id") or _hash_id(payload)),
        source_summary=str(payload.get("summary", ""))[:200],
    )


def synthetic_profile(seed: int, *,
                      name_prefix: str = "synthetic") -> TaskProfile:
    """Deterministic pseudo-random task for benchmark families.

    Same contract as ``adaptive.evaluator.scenario_from_seed``: a seed
    fully determines the instance, enabling disjoint training / holdout
    splits whose difficulty mix is comparable but whose instances never
    repeat across the split boundary.
    """
    rng = random.Random(int(seed))
    return TaskProfile(
        domain=rng.choice(_SYNTH_DOMAINS),
        difficulty=round(rng.uniform(0.05, 0.95), 4),
        reasoning_depth=round(rng.uniform(0.05, 0.95), 4),
        context_requirement=round(rng.uniform(0.02, 0.98), 4),
        tool_requirement=round(rng.choice(
            [0.0, 0.0, rng.uniform(0.2, 0.95)]), 4),
        latency_sensitivity=round(rng.uniform(0.0, 0.8), 4),
        privacy_required=rng.random() < 0.15,
        task_id=f"{name_prefix}-{int(seed)}",
        source_summary=f"synthetic task #{seed}",
    )
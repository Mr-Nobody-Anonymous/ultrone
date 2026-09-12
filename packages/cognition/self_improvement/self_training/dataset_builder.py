# Copyright (c) Ultrone Contributors. All rights reserved.
"""Dataset construction from selected experiences.

``DatasetBuilder`` turns *good* experiences into SFT-shaped training
examples::

    {
      "example_id": "...",
      "input":   {profile demand fields + summary},
      "context": {selected model/memory/skills/parameters},
      "desired_behavior": {"accepted": true, "quality": 0.82},
      "outcome_score": 0.82
    }

Exact duplicates are dropped by demand signature; uncertain/bad
experiences are counted but never written. Artifacts persist as
JSONL alongside a content hash, so any checkpoint can name the exact
bytes it was trained on (dataset_hash lineage).

``ContinualMixture`` then blends historical corpora, the freshest
cycle, and weakness-targeted resampling under configurable ratios
(default 70/20/10). Ratios describe intent; actual proportions are
reported per merge so thin history degrades gracefully instead of
silently dominating.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

#: Default continual-learning mixture (historical/recent/weakness).
DEFAULT_MIXTURE_RATIOS = (0.70, 0.20, 0.10)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def content_hash(payload: Any) -> str:
    digest = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(digest).hexdigest()[:16]


@dataclass
class TrainingExample:
    example_id: str
    input: Dict[str, Any]
    context: Dict[str, Any]
    desired_behavior: Dict[str, Any]
    outcome_score: float

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class DatasetArtifact:
    path: str
    content_hash: str
    num_examples: int
    source_counts: Dict[str, int] = field(default_factory=dict)
    duplicates_removed: int = 0

    def load(self) -> List[Dict[str, Any]]:
        lines = Path(self.path).read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


class DatasetBuilder:
    """Good-experience filter -> dedup -> JSONL artifact.

    ``desired_ceiling`` is the supervisor target: rather than training
    a candidate to reproduce the incumbent's own quality (which
    converges to itself and never improves), good experiences are
    labeled with the *achievable* outcome -- a reference ceiling the
    incumbent has not yet reached. This is the training signal that
    actually lifts capability; self-reported quality is retained for
    transparency but never used as the learning target.
    """

    DEFAULT_CEILING = 0.85

    def __init__(self, workdir: str) -> None:
        self._workdir = Path(workdir)
        self._workdir.mkdir(parents=True, exist_ok=True)

    def build_from_traces(self, good_traces, *, tag: str,
                          desired_ceiling: float = DEFAULT_CEILING
                          ) -> Optional[DatasetArtifact]:
        if not 0.0 <= desired_ceiling <= 1.0:
            raise ValueError("desired_ceiling must be within [0, 1]")
        examples: List[TrainingExample] = []
        seen = set()
        duplicates = 0
        for trace in good_traces:
            profile = trace.task_profile
            payload_input = {
                "domain": profile.domain,
                "difficulty": profile.difficulty,
                "reasoning_depth": profile.reasoning_depth,
                "context_requirement": profile.context_requirement,
                "tool_requirement": profile.tool_requirement,
                "latency_sensitivity": profile.latency_sensitivity,
                "privacy_required": profile.privacy_required,
                "summary": profile.source_summary,
            }
            # Dedup on the EXACT instance (content hash), not a coarse
            # rounded signature: two tasks that differ only in their
            # 4th-decimal difficulty are distinct learning evidence, not
            # duplicates. Only a genuinely identical payload folds.
            key = content_hash(payload_input)
            if key in seen:
                duplicates += 1
                continue
            seen.add(key)
            quality = float(trace.result.get("quality", 0.0)) \
                if trace.result else 0.0
            target = min(1.0, max(quality, desired_ceiling))
            examples.append(TrainingExample(
                example_id=f"{tag}-{content_hash(payload_input)}",
                input=payload_input,
                context={
                    "model": trace.selected_model,
                    "memory": trace.selected_memory,
                    "skills": list(trace.selected_skills),
                    "parameters": dict(trace.parameters),
                },
                desired_behavior={
                    "accepted": True,
                    "quality": round(quality, 6),
                    "target": round(target, 6),
                },
                outcome_score=round(target, 6)))

        if not examples:
            return None
        path = self._workdir / f"dataset_{tag}.jsonl"
        lines = "\n".join(json.dumps(e.to_dict(), sort_keys=True)
                          for e in sorted(examples,
                                          key=lambda e: e.example_id))
        path.write_text(lines + "\n", encoding="utf-8")
        blob = path.read_bytes()
        return DatasetArtifact(
            path=str(path),
            content_hash=hashlib.sha256(blob).hexdigest()[:16],
            num_examples=len(examples),
            source_counts={"good": len(examples)},
            duplicates_removed=duplicates)


class ContinualMixture:
    """Historical + recent + weakness-targeted blended corpus.

    Guards against catastrophic forgetting: fresh experiences never
    become the whole diet. With ratios (0.70, 0.20, 0.10) and ample
    history, seven of every ten examples come from accumulated
    corpora; when history is thin the shortfall is *reported* in
    ``source_counts`` rather than silently normalized away.
    """

    def __init__(self, ratios=(DEFAULT_MIXTURE_RATIOS[0],
                               DEFAULT_MIXTURE_RATIOS[1],
                               DEFAULT_MIXTURE_RATIOS[2])) -> None:
        if abs(sum(ratios) - 1.0) > 1e-6 or any(r < 0 for r in ratios):
            raise ValueError(
                "ratios must be non-negative and sum to 1.0")
        self.ratios = tuple(float(r) for r in ratios)

    def merge(self, historical: Optional[DatasetArtifact],
              recent: Optional[DatasetArtifact],
              synthesized: List[Dict[str, Any]],
              *, workdir: str, tag: str) -> Optional[DatasetArtifact]:
        parts = (
            historical.load() if historical else [],
            recent.load() if recent else [],
            list(synthesized))
        total_available = sum(len(p) for p in parts)
        if total_available == 0:
            return None

        picked: List[Dict[str, Any]] = []
        provenance: Dict[str, int] = {}
        labels = ("historical", "recent", "weakness_targeted")
        for label, pool, ratio in zip(labels, parts, self.ratios):
            share = min(len(pool),
                        int(round(ratio * max(total_available, 1))))
            # Deterministic take: lowest example_ids first.
            take = sorted(pool,
                          key=lambda e: e.get("example_id", ""))[:share]
            picked.extend(take)
            provenance[label] = len(take)

        # Late safety dedup across merged sources.
        unique: Dict[str, Dict[str, Any]] = {}
        removed = 0
        for example in picked:
            eid = example.get("example_id", content_hash(example))
            if eid in unique:
                removed += 1
                continue
            unique[eid] = example

        out_dir = Path(workdir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"mixture_{tag}.jsonl"
        ordered = [unique[k] for k in sorted(unique)]
        payload = "\n".join(json.dumps(e, sort_keys=True)
                            for e in ordered)
        path.write_text(payload + ("\n" if payload else ""),
                        encoding="utf-8")
        blob = path.read_bytes()
        return DatasetArtifact(
            path=str(path),
            content_hash=hashlib.sha256(blob).hexdigest()[:16],
            num_examples=len(ordered),
            source_counts={**provenance, "duplicates_removed": removed})
